"""Asheville permits from the City's Accela permits view (2026-09-30).

The City's own ArcGIS Server publishes its Accela permits as points, one row
per permit (66,072 since January 2014), refreshed overnight. The City's open
data hub does not list the layer, which is why earlier probes missed it.
``date_opened`` holds the day alone at midnight Eastern, but some rows carry
it a second later, so a watermark on it could step past the rest of its own
day. Asheville therefore reads the permits opened in the 90 days before each
poll (697 on 2026-09-30), less right-of-way, event, vendor, over-the-counter
and home-business records.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = [
    "objectid", "record_id", "date_opened", "record_type", "record_type_subtype",
    "record_status", "address", "apn",
]

FIELD_MAP = {
    "job_id": ["record_id"],
    "issuance_date": ["date_opened"],
    "filing_date": ["date_opened"],
    "job_type": ["record_type_subtype", "record_type"],
    "status": ["record_status"],
    "address_street": ["address"],
    "bbl": ["apn"],
}

WHERE = (
    "date_opened >= CURRENT_DATE - INTERVAL '90' DAY AND date_opened <= CURRENT_TIMESTAMP"
    " AND record_type_type NOT IN ('Right of Way', 'Event-Temporary Use', 'Outdoor Vendor', 'Over The Counter')"
    " AND record_type_subtype NOT IN ('Home Occupation', 'Occupational')"
)

ORDER = "date_opened DESC, objectid DESC"


def _spec():
    return get_dataset(CityId.ASHEVILLE, FeedType.PERMITS)


def _permit(**changes):
    """A permit as the ArcGIS client hands it on (synthetic values)."""
    return {
        "objectid": 1,
        "record_id": "26-99001",
        "date_opened": "2026-09-29T04:00:00+00:00",
        "record_type": "Res: New SFD",
        "record_type_subtype": "New Building",
        "record_status": "Plan Check",
        "address": "100 EXAMPLE ST, ASHEVILLE, NC 28806",
        "apn": "999001",
        "latitude": 35.5790,
        "longitude": -82.5930,
        **changes,
    }


def test_asheville_reads_the_citys_accela_permits_view():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_asheville_permits_url
    assert spec.endpoint.startswith("https://gis.ashevillenc.gov/server/")
    assert spec.endpoint.endswith("/Permits/AccelaPermitsView/MapServer/2")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert spec.watermark_col == "date_opened"
    assert (spec.oid_field, spec.max_record_count) == ("objectid", 2000)
    assert spec.field_map == FIELD_MAP
    # Every placed row is a point; the client lifts it onto latitude/longitude.
    assert spec.needs_geocode is False


def test_the_window_holds_ninety_days_of_building_permits():
    spec = _spec()
    assert spec.where == WHERE
    assert spec.order_by == ORDER


def test_the_request_names_its_columns_and_leaves_names_and_free_text_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The layer also carries the permit's name, description, notes and
    # comments, a licence number and a business name.
    assert not {
        "record_name", "description", "short_notes", "license_number", "business_name", "record_comments",
    } & set(select)
    # Three of the 66,072 rows carry a job value, none in the past year.
    assert "job_value" not in select and "cost" not in _spec().field_map


def test_each_permit_publishes_once():
    # One row per permit: record_id never repeats.
    assert (_spec().id_keys, _spec().composite_id) == (["record_id"], False)


def test_the_window_fits_the_cap_and_a_nightly_refresh():
    spec = _spec()
    # 697 permits in the window on 2026-09-30, and 1,047 in the busiest 90
    # days of the past year (August to October 2025).
    assert spec.batch_limit == 1500
    # On a Wednesday afternoon the newest permit was Tuesday's, so the layer
    # is refreshed overnight; nothing is opened at weekends, so the alarm
    # (twice the cadence) waits six days.
    assert spec.interval_seconds == 21600.0
    assert spec.expected_cadence_days == 3


def test_permits_without_a_point_are_skipped():
    # Seven of the window's 697 permits carry no point on 2026-09-30.
    assert _spec().metro_clip is True


def test_the_city_server_takes_ansi_literals_in_eastern_time():
    from src.producers.watermarks import ANSI_DATE_LITERAL_HOSTS, watermark_comparison

    assert "gis.ashevillenc.gov" in ANSI_DATE_LITERAL_HOSTS
    assert watermark_comparison(
        "date_opened", ">=", "2026-09-29T04:00:00", _spec().endpoint, time_zone="America/New_York"
    ) == "date_opened >= timestamp '2026-09-29 00:00:00'"


class TestAshevillePermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_a_new_house_is_published_at_its_point(self, permits):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _permit().items() if key not in ("latitude", "longitude")}
        attributes["date_opened"] = 1790654400000  # 2026-09-29 at midnight Eastern
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -82.5930, "y": 35.5790}}, date_fields={"date_opened"}
        )

        event = permits.parse_socrata_row(row, city_id="asheville")

        assert event is not None
        assert (event.city_id, event.job_id) == ("asheville", "26-99001")
        assert (event.job_type.value, event.normalized_permit_type) == ("NB", "NEW_CONSTRUCTION")
        # The layer has no issue date: both dates are the day the permit was
        # opened, and the status says whether it has been issued.
        assert event.issuance_date.isoformat() == event.filing_date.isoformat() == "2026-09-29T04:00:00+00:00"
        assert (event.status, event.bbl, event.estimated_cost) == ("Plan Check", "999001", 0.0)
        assert event.address_street == "100 EXAMPLE ST, ASHEVILLE, NC 28806"
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (35.5790, -82.5930)
        assert event.borough == "WEST_ASHEVILLE"

    def test_a_demolition_is_named_by_its_subtype(self, permits):
        event = permits.parse_socrata_row(
            _permit(record_type="Com: Demo", record_type_subtype="Demolition"), city_id="asheville"
        )
        assert (event.job_type.value, event.normalized_permit_type) == ("DM", "DEMOLITION")

    def test_work_on_an_existing_building_is_a_minor_alteration(self, permits):
        event = permits.parse_socrata_row(
            _permit(record_type="Res: Alterations", record_type_subtype="Existing Building", record_status="Issued"),
            city_id="asheville",
        )
        assert (event.job_type.value, event.normalized_permit_type) == ("OT", "MINOR_ALTERATION")
        assert event.status == "Issued"


class TestAshevillePoll:
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

    def test_a_poll_publishes_each_placed_permit_once(self, scheduler):
        producer = scheduler.producers["permits"]
        unplaced = {key: value for key, value in _permit(objectid=3, record_id="26-99003").items()
                    if key not in ("latitude", "longitude")}
        rows = [
            _permit(),
            # Opened the same day and stored a second later.
            _permit(objectid=2, record_id="26-99002", record_type="Com: Demo", record_type_subtype="Demolition",
                    date_opened="2026-09-29T04:00:01+00:00", latitude=35.5960, longitude=-82.4810),
            unplaced,
            _permit(objectid=4, record_id="26-99004", record_type="Res: Alterations",
                    record_type_subtype="Existing Building", record_status="Issued",
                    date_opened="2026-09-28T04:00:00+00:00", latitude=35.6260, longitude=-82.5420),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("permits_avl")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (4, 3, 1)
        assert result["duplicates_skipped"] == 0
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WHERE})"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert kwargs["max_records"] == 1500
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == ["asheville:26-99001", "asheville:26-99002", "asheville:26-99004"]
        assert [call.kwargs["payload"].job_type.value for call in calls] == ["NB", "DM", "OT"]

        # The next poll reads the same window, and the day's later second
        # costs nothing: none of it is published again.
        result = scheduler.poll_job("permits_avl")

        assert (result["records_published"], result["duplicates_skipped"], result["outside_metro"]) == (0, 3, 1)
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WHERE})"
