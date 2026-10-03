"""Waco 311 from the City's MyWaco requests layer (2026-10-02).

Waco's MyWaco app (CitySourced) is synced nightly, at about 03:00 UTC, to a
hosted layer on the City's ArcGIS Online org: one point per request since
December 2021 (22,861 on 2026-10-02). 59% of recent requests are marked
private, so the poll reads the public ones newer than its watermark, each by
its id, type, status and dates, every six hours.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "Id", "Status", "StatusTypeReadable", "RequestType", "DateCreated", "DateClosed"]

FIELD_MAP = {
    "incident_id": ["Id"],
    "created_date": ["DateCreated"],
    "closed_date": ["DateClosed"],
    "complaint_type": ["RequestType"],
    "status": ["StatusTypeReadable", "Status"],
}

ORDER = "DateCreated DESC, OBJECTID DESC"


def _spec():
    return get_dataset(CityId.WACO, FeedType.COMPLAINTS_311)


def _request(**changes):
    """A request as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 22001,
        "Id": "9900001",
        "Status": "Open",
        "StatusTypeReadable": "Work Order Created",
        "RequestType": "Pothole",
        "DateCreated": "2026-10-01T16:54:08.123000+00:00",
        "DateClosed": None,
        "latitude": 31.5493,
        "longitude": -97.1467,
        **changes,
    }


def test_waco_reads_the_mywaco_requests_layer():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_waco_311_url
    assert spec.endpoint == (
        "https://services2.arcgis.com/oUXiR7ziAPAzGw6X/arcgis/rest/services/MyWacoRequests/FeatureServer/6"
    )
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    assert (spec.watermark_col, spec.order_by) == ("DateCreated", ORDER)
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_only_public_requests_are_read():
    # 11,244 of the 22,861 requests on 2026-10-02 were public.
    assert _spec().where == "IsPrivate = 0"


def test_the_request_names_its_columns_and_leaves_the_people_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    assert not {
        "AuthorName", "AssignedUserName", "CustomerName", "CreatedByName", "Description", "FormattedAddress",
        "MobileDeviceTypeAndModel",
    } & set(select)


def test_each_request_publishes_once():
    assert (_spec().id_keys, _spec().composite_id) == (["Id"], False)


def test_the_poll_follows_the_nightly_sync():
    spec = _spec()
    # Every one of the 473 public requests in the 90 days to 2026-10-02 lay
    # inside the box; the clip guards against a misplaced point.
    assert spec.metro_clip is True
    assert spec.batch_limit is None
    assert (spec.interval_seconds, spec.expected_cadence_days) == (21600.0, 2)


class TestWacoRequestParsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_a_request_is_published_at_its_point_with_its_readable_status(self, complaints):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _request().items() if key not in ("latitude", "longitude")}
        attributes["DateCreated"] = 1790873648123  # 2026-10-01 16:54:08.123 UTC
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -97.1467, "y": 31.5493}},
            date_fields={"DateCreated", "DateClosed"},
        )

        event = complaints.parse_socrata_row(row, city_id="waco")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("waco", "9900001")
        assert (event.complaint_type, event.status) == ("Pothole", "Work Order Created")
        assert event.created_date.isoformat() == "2026-10-01T16:54:08.123000+00:00"
        assert event.closed_date is None
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (31.5493, -97.1467)

    def test_without_a_readable_status_the_open_or_closed_flag_stands_in(self, complaints):
        event = complaints.parse_socrata_row(_request(StatusTypeReadable=None, Status="Closed"), city_id="waco")

        assert event is not None
        assert event.status == "Closed"


class TestWacoPoll:
    @pytest.fixture
    def scheduler(self):
        with patch("src.producers.base_producer.BaseKafkaProducer"):
            sched = MunicipalIngestionScheduler(
                dlq_producer=MagicMock(), rate_limit_delay_seconds=0.0, dedup_capacity=1000
            )
        for producer in sched.producers.values():
            producer.producer = MagicMock()
        sched.state_file = None
        return sched

    def test_a_poll_publishes_public_requests_and_rereads_its_newest_once(self, scheduler):
        producer = scheduler.producers["311"]
        rows = [
            _request(),
            _request(OBJECTID=22000, Id="9900002", Status="Closed", StatusTypeReadable="Closed",
                     RequestType="High Grass/Weeds", DateCreated="2026-10-01T08:02:45.500000+00:00",
                     DateClosed="2026-10-01T15:30:00+00:00", latitude=31.5781, longitude=-97.1902),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": None})

        result = scheduler.poll_job("311_waco")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (2, 2, 0)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == "(IsPrivate = 0)"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert [call.kwargs["key"] for call in producer.producer.produce.call_args_list] == [
            "waco:9900001", "waco:9900002",
        ]
        assert scheduler.metrics["311_waco"].high_watermark == "2026-10-01T16:54:08"

        # The watermark keeps whole seconds, so the newest request, created
        # at .123 past them, comes back once more and is not published again.
        producer.arcgis.paginate = MagicMock(return_value=[[_request()]])
        result = scheduler.poll_job("311_waco")

        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == (
            "(IsPrivate = 0) AND DateCreated > '2026-10-01T16:54:08'"
        )
        assert (result["records_fetched"], result["records_published"], result["duplicates_skipped"]) == (1, 0, 1)
