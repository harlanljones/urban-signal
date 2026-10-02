"""Charleston SC permits from the City's active permits layer (2026-10-02).

The City of Charleston's GIS server publishes its active permits, a rolling 18
months (18,540 rows on 2026-10-02), each at its point with its parcel number.
Charleston reads the permits issued in the 90 days before each poll and leaves
out the permits that are not building work: engineering, short-term rental
renewals, rental registration, markets, events and the like. The issue date is
midnight on most rows and carries a time of day on the rest, so the window
runs on the server.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = [
    "OBJECTID", "PERMIT_NUMBER", "PERMIT_TYPE", "WORK_CLASS", "PERMIT_STATUS", "APPLICATION_DATE", "ISSUE_DATE",
    "VALUATION", "MAIN_PARCEL_NUMBER", "PERMIT_ADDRESS_LINE1", "ZIPCODE",
]

FIELD_MAP = {
    "job_id": ["PERMIT_NUMBER"],
    "issuance_date": ["ISSUE_DATE"],
    "filing_date": ["APPLICATION_DATE"],
    "job_type": ["WORK_CLASS", "PERMIT_TYPE"],
    "status": ["PERMIT_STATUS"],
    "cost": ["VALUATION"],
    "address_street": ["PERMIT_ADDRESS_LINE1"],
    "zipcode": ["ZIPCODE"],
    "bbl": ["MAIN_PARCEL_NUMBER"],
}

LEFT_OUT = [
    "Engineering", "Operational Permit", "Residential Rental", "Farmers Market", "Kitchen Exhaust Cleaning",
    "Fire and Life Safety - Fireworks", "Fire and Life Safety - Tent", "Tree Removal Permit", "Construction Noise",
]

WINDOW = (
    "ISSUE_DATE >= CURRENT_DATE - INTERVAL '90' DAY AND ISSUE_DATE <= CURRENT_TIMESTAMP AND PERMIT_TYPE NOT IN ("
    + ", ".join(f"'{name}'" for name in LEFT_OUT)
    + ")"
)

ORDER = "ISSUE_DATE DESC, OBJECTID DESC"


def _spec():
    return get_dataset(CityId.CHARLESTON_SC, FeedType.PERMITS)


def _permit(**changes):
    """An issued permit as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 7,
        "PERMIT_NUMBER": "SF2026-99001",
        "PERMIT_TYPE": "Single Family/Duplex Dwelling",
        "WORK_CLASS": "Addition",
        "PERMIT_STATUS": "Issued",
        "APPLICATION_DATE": "2026-07-24T14:56:14+00:00",
        "ISSUE_DATE": "2026-09-30T14:54:26+00:00",
        "VALUATION": 25000.0,
        "MAIN_PARCEL_NUMBER": "9999999001",
        "PERMIT_ADDRESS_LINE1": "100 EXAMPLE ST",
        "ZIPCODE": "29407",
        "latitude": 32.7957,
        "longitude": -79.9851,
        **changes,
    }


def test_charleston_reads_the_citys_active_permits_layer():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_charleston_sc_permits_url
    assert spec.endpoint == (
        "https://gis.charleston-sc.gov/arcgis2/rest/services/External/Applications/MapServer/20"
    )
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 5000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_the_window_holds_ninety_days_of_issued_building_permits():
    spec = _spec()
    assert spec.watermark_col == "ISSUE_DATE"
    # Certificates of occupancy, signs, demolitions and the trades stay in.
    assert spec.where == WINDOW
    assert spec.order_by == ORDER


def test_the_request_names_its_columns():
    assert _spec().select.split(",") == COLUMNS


def test_each_permit_publishes_once():
    # One permit was listed twice among the 2,363 rows in the window on
    # 2026-10-02.
    assert (_spec().id_keys, _spec().composite_id) == (["PERMIT_NUMBER"], False)


def test_the_cap_holds_the_busiest_window_and_the_box_keeps_the_placed_permits():
    spec = _spec()
    # 2,363 permits in the window on 2026-10-02; the most in the five full
    # 90-day windows the layer holds was 2,445, from July to October 2025.
    assert spec.batch_limit == 5000
    # 52 of the 2,363 had no point.
    assert spec.metro_clip is True
    # On Friday 2026-10-02 the newest permit had been issued on Wednesday
    # afternoon, 46 hours before; Thursday's had not arrived.
    assert (spec.interval_seconds, spec.expected_cadence_days) == (21600.0, 4)


class TestCharlestonPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_an_issued_permit_is_published_at_its_point_with_its_parcel(self, permits):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _permit().items() if key not in ("latitude", "longitude")}
        attributes["APPLICATION_DATE"] = 1784904974000  # 2026-07-24 14:56:14 UTC
        attributes["ISSUE_DATE"] = 1790780066000  # 2026-09-30 14:54:26 UTC
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -79.9851, "y": 32.7957}},
            date_fields={"APPLICATION_DATE", "ISSUE_DATE"},
        )

        event = permits.parse_socrata_row(row, city_id="charleston_sc")

        assert event is not None
        assert (event.city_id, event.job_id, event.status) == ("charleston_sc", "SF2026-99001", "Issued")
        assert (event.bbl, event.zipcode, event.estimated_cost) == ("9999999001", "29407", 25000.0)
        assert event.filing_date.isoformat() == "2026-07-24T14:56:14+00:00"
        assert event.issuance_date.isoformat() == "2026-09-30T14:54:26+00:00"
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (32.7957, -79.9851)
        assert event.job_type.value == "A2"

    def test_the_work_class_names_new_construction(self, permits):
        event = permits.parse_socrata_row(_permit(PERMIT_NUMBER="SF2026-99002", WORK_CLASS="New"),
                                          city_id="charleston_sc")

        assert event is not None
        assert (event.job_type.value, event.normalized_permit_type) == ("NB", "NEW_CONSTRUCTION")

    def test_a_midnight_issue_date_is_kept_as_the_day(self, permits):
        event = permits.parse_socrata_row(_permit(ISSUE_DATE="2026-09-30T00:00:00+00:00"), city_id="charleston_sc")

        assert event is not None
        assert event.issuance_date.isoformat() == "2026-09-30T00:00:00+00:00"


class TestCharlestonPoll:
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
        rows = [
            _permit(),
            _permit(OBJECTID=8, PERMIT_NUMBER="DEM2026-99003", PERMIT_TYPE="Demolition",
                    WORK_CLASS="Interior-Non-Structural", ISSUE_DATE="2026-09-30T00:00:00+00:00",
                    latitude=32.7861, longitude=-79.9387),
            # The same permit listed twice.
            _permit(OBJECTID=9),
            # No point.
            _permit(OBJECTID=10, PERMIT_NUMBER="ELE2026-99004", PERMIT_TYPE="Electrical", WORK_CLASS="Residential",
                    latitude=None, longitude=None),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("permits_charleston_sc")

        assert (result["records_fetched"], result["records_published"]) == (4, 2)
        assert (result["duplicates_skipped"], result["outside_metro"]) == (1, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert kwargs["max_records"] == 5000
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == ["charleston_sc:SF2026-99001", "charleston_sc:DEM2026-99003"]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("permits_charleston_sc")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 3)
