"""Worcester 311 from the City's Customer Service Request System (2026-10-02).

The City publishes every work order its Customer Service Request System has
logged since 2021 (382,882 on 2026-10-02), from 311 calls and SeeClickFix,
as a hosted table it updates weekly: each with its request id, type,
division, status and dates, and no requester or description columns. The
table has no geometry. Each row's point is two columns of Massachusetts
State Plane feet, which the scheduler converts. The dates are whole days, so
each poll reads the newest day again and the dedup drops what it published.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = [
    "ObjectId", "Service_Request_ID", "Date_Logged", "Request_Type", "Division", "Status", "Closed_Date",
    "X_Coordinate", "Y_coordinate",
]

FIELD_MAP = {
    "incident_id": ["Service_Request_ID"],
    "created_date": ["Date_Logged"],
    "closed_date": ["Closed_Date"],
    "complaint_type": ["Request_Type", "Division"],
    "status": ["Status"],
}

WHERE = (
    "X_Coordinate IS NOT NULL AND Y_coordinate IS NOT NULL"
    " AND Request_Type <> 'Water Mains / Street Light Mark Outs'"
)

ORDER = "Date_Logged DESC, ObjectId DESC"


def _spec():
    return get_dataset(CityId.WORCESTER, FeedType.COMPLAINTS_311)


def _work_order(**changes):
    """A work order as the ArcGIS client hands on a table row (synthetic values)."""
    return {
        "ObjectId": 382001,
        "Service_Request_ID": 9900001,
        "Date_Logged": "2026-09-30",
        "Request_Type": "Pothole",
        "Division": "DPW&P Streets",
        "Status": "Open",
        "Closed_Date": None,
        # Outside City Hall (42.26259, -71.80229), in State Plane feet.
        "X_Coordinate": 574340.05,
        "Y_coordinate": 2920859.95,
        **changes,
    }


@pytest.fixture
def scheduler():
    with patch("src.producers.base_producer.BaseKafkaProducer"):
        sched = MunicipalIngestionScheduler(dlq_producer=MagicMock(), rate_limit_delay_seconds=0.0, dedup_capacity=1000)
    for producer in sched.producers.values():
        producer.producer = MagicMock()
    sched.state_file = None
    return sched


def test_worcester_reads_the_citys_work_order_table():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_worcester_311_url
    assert spec.endpoint == (
        "https://services1.arcgis.com/j8dqo2DJE7mVUBU1/arcgis/rest/services/CsrsWorkOrders_TEST/FeatureServer/0"
    )
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    assert (spec.oid_field, spec.max_record_count) == ("ObjectId", 1000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_each_point_is_two_columns_of_state_plane_feet():
    spec = _spec()
    # NAD83 Massachusetts Mainland, US survey feet.
    assert (spec.state_plane_crs, spec.state_plane_units) == ("EPSG:2249", "ftUS")
    assert (spec.state_plane_x_col, spec.state_plane_y_col) == ("X_Coordinate", "Y_coordinate")


def test_the_window_leaves_out_unplaceable_rows_and_utility_mark_outs():
    # Of the 15,926 requests logged in the 90 days to 2026-10-02, 15 had no
    # coordinates, and 1,502 asked Water Engineering to mark out its mains
    # and street light cables before an excavation, most of them through
    # SeeClickFix: contractors' notices, not residents' requests. The other
    # 14,414 are read.
    assert _spec().where == WHERE


def test_the_request_names_its_columns():
    # The table holds no requester or description; the poll also leaves the
    # street, cross street, source, priority and time of day on the server.
    assert _spec().select.split(",") == COLUMNS


def test_each_request_publishes_once_newest_first():
    spec = _spec()
    # Every one of the 15,926 requests in the 90 days had its own id.
    assert (spec.id_keys, spec.composite_id) == (["Service_Request_ID"], False)
    assert (spec.watermark_col, spec.order_by) == ("Date_Logged", ORDER)


def test_the_cap_holds_a_missed_weekly_update():
    spec = _spec()
    # The busiest 16 days of the year to 2026-09-30 logged 6,660 requests
    # besides mark-outs, from 2026-01-20.
    assert spec.batch_limit == 10000
    # The table is updated weekly, its newest day two days old on
    # 2026-10-02.
    assert (spec.interval_seconds, spec.expected_cadence_days) == (21600.0, 7)
    # The City's own requests, all in the city: 907 of the 10,000 published
    # on 2026-10-02 lay at its north, east and south edges, past the metro box, and
    # are kept, as Worcester's other feeds keep theirs.
    assert spec.metro_clip is False


class TestWorcesterRequestParsing:
    def test_an_open_request_is_published_at_its_converted_point(self, scheduler):
        (row,) = scheduler._place_state_plane_rows("311_worcester", [_work_order()])

        event = scheduler.producers["311"].parse_socrata_row(row, city_id="worcester")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("worcester", "9900001")
        assert (event.complaint_type, event.status) == ("Pothole", "Open")
        assert event.created_date.date().isoformat() == "2026-09-30"
        assert event.closed_date is None
        assert event.latitude == pytest.approx(42.26259, abs=1e-6)
        assert event.longitude == pytest.approx(-71.80229, abs=1e-6)
        assert event.h3_res9 is not None

    def test_a_closed_request_carries_its_closing_day(self, scheduler):
        (row,) = scheduler._place_state_plane_rows(
            "311_worcester",
            [_work_order(Request_Type="Dead Animal", Division="DPW&P Sanitation", Status="Closed",
                         Closed_Date="2026-10-01")],
        )

        event = scheduler.producers["311"].parse_socrata_row(row, city_id="worcester")

        assert event is not None
        assert (event.complaint_type, event.status) == ("Dead Animal", "Closed")
        assert event.closed_date.date().isoformat() == "2026-10-01"

    def test_a_request_with_a_blank_type_takes_its_division(self, scheduler):
        (row,) = scheduler._place_state_plane_rows(
            "311_worcester", [_work_order(Request_Type="", Division="DPW&P Parks / Forestry")]
        )

        event = scheduler.producers["311"].parse_socrata_row(row, city_id="worcester")

        assert event is not None
        assert event.complaint_type == "DPW&P Parks / Forestry"


class TestWorcesterPoll:
    def test_a_poll_places_each_request_and_reads_the_newest_day_again(self, scheduler):
        producer = scheduler.producers["311"]
        rows = [
            _work_order(),
            _work_order(ObjectId=382000, Service_Request_ID=9900002, Request_Type="Trash Bag Not Collected",
                        Division="DPW&P Sanitation", Status="Closed", Closed_Date="2026-10-01",
                        X_Coordinate=568823.51, Y_coordinate=2915891.26),
            # At the city's north end, past the metro box.
            _work_order(ObjectId=381990, Service_Request_ID=9899990, Date_Logged="2026-09-29",
                        Request_Type="Tree Inspection", Division="DPW&P Parks / Forestry",
                        X_Coordinate=572315.55, Y_coordinate=2945505.78),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": None})

        result = scheduler.poll_job("311_worcester")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 3, 0)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WHERE})"
        assert (kwargs["order_by"], kwargs["select"], kwargs["max_records"]) == (ORDER, ",".join(COLUMNS), 10000)
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [(event.incident_id, round(event.latitude, 4), round(event.longitude, 4)) for event in events] == [
            ("9900001", 42.2626, -71.8023), ("9900002", 42.2489, -71.8226), ("9899990", 42.3302, -71.8101),
        ]
        assert scheduler.metrics["311_worcester"].high_watermark == "2026-09-30T00:00:00"

        # The day is whole, so the next poll reads it again and publishes
        # none of it twice.
        producer.arcgis.paginate = MagicMock(return_value=[rows[:2]])

        result = scheduler.poll_job("311_worcester")

        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == (
            f"({WHERE}) AND Date_Logged >= '2026-09-30T00:00:00'"
        )
        assert (result["records_fetched"], result["records_published"], result["duplicates_skipped"]) == (2, 0, 2)
