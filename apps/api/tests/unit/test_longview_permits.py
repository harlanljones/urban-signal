"""Longview permits from the City's Cityworks permit dashboard layer (2026-10-02).

The City's own ArcGIS Server publishes the permits behind its building permit
dashboard, fed from Cityworks: a row per permit and review period since April
2023 (19,548 rows on 2026-10-02), so a permit with several review periods
repeats. Longview keeps the first period, reads the permits issued in the 90
days before each poll and leaves out the rows that are not permits.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = [
    "OBJECTID", "PERMIT_NUMBER", "PERMIT_TYPE", "PRJ_TYPE", "STATUS", "DATE_CREATED", "DATE_ISSUED", "LOCATION",
    "VALUATION", "PERIOD_NUMBER",
]

FIELD_MAP = {
    "job_id": ["PERMIT_NUMBER"],
    "issuance_date": ["DATE_ISSUED"],
    "filing_date": ["DATE_CREATED"],
    "job_type": ["PRJ_TYPE", "PERMIT_TYPE"],
    "status": ["STATUS"],
    "cost": ["VALUATION"],
    "address_street": ["LOCATION"],
}

WINDOW = (
    "DATE_ISSUED >= CURRENT_DATE - INTERVAL '90' DAY AND DATE_ISSUED <= CURRENT_TIMESTAMP AND PERIOD_NUMBER <= 1 "
    "AND PERMIT_TYPE NOT IN ('CONTREGIST', 'ROWCONST', 'PRESUBPRP#', 'BDGPLNREV#', 'SITREV#')"
)

ORDER = "DATE_ISSUED DESC, OBJECTID DESC"


def _spec():
    return get_dataset(CityId.LONGVIEW, FeedType.PERMITS)


def _permit(**changes):
    """A permit's first review period as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 7,
        "PERMIT_NUMBER": "BLD2026-99001",
        "PERMIT_TYPE": "RESBLDG#",
        "PRJ_TYPE": "SINGLE FAMILY",
        "STATUS": "ISSUED",
        "DATE_CREATED": "2026-09-24T14:10:05+00:00",
        "DATE_ISSUED": "2026-10-01T21:57:59+00:00",
        "LOCATION": "100 EXAMPLE DR",
        "VALUATION": 285000.0,
        "PERIOD_NUMBER": 0,
        "latitude": 32.5007,
        "longitude": -94.7405,
        **changes,
    }


def test_longview_reads_the_citys_permit_dashboard_layer():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_longview_permits_url
    assert spec.endpoint == (
        "https://cloud.longviewtexas.gov/arcgis/rest/services/AGOL/Building_Permit_Dashboard/MapServer/2"
    )
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 1000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_the_window_holds_ninety_days_of_issued_permits_once_each():
    spec = _spec()
    assert spec.watermark_col == "DATE_ISSUED"
    # The first review period is one row per permit; contractor
    # registrations (placed at the contractor's address), right-of-way work
    # and the pre-submittal, plan and site reviews are not permits.
    assert spec.where == WINDOW
    assert spec.order_by == ORDER


def test_the_request_names_its_columns():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The applicant, the work description, the case name and the project
    # detail stay on the server.
    assert not {"APPLICANT", "WORK_DESCRIPTION", "CASE_NAME", "PRJ_DETAIL"} & set(select)


def test_each_permit_publishes_once():
    assert (_spec().id_keys, _spec().composite_id) == (["PERMIT_NUMBER"], False)


def test_the_cap_holds_the_busiest_window_and_the_box_keeps_longviews():
    spec = _spec()
    # 1,027 permits in the window on 2026-10-02; the most in eight 90-day
    # windows back to October 2024 was 1,136.
    assert spec.batch_limit == 2500
    # 25 of the 1,027 lay south or west of the box.
    assert spec.metro_clip is True
    # The layer carried permits to the close of business the day before.
    assert (spec.interval_seconds, spec.expected_cadence_days) == (21600.0, 3)


class TestLongviewPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_an_issued_permit_is_published_at_its_point(self, permits):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _permit().items() if key not in ("latitude", "longitude")}
        attributes["DATE_CREATED"] = 1790259005000  # 2026-09-24 14:10:05 UTC
        attributes["DATE_ISSUED"] = 1790891879000  # 2026-10-01 21:57:59 UTC
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -94.7405, "y": 32.5007}},
            date_fields={"DATE_CREATED", "DATE_ISSUED"},
        )

        event = permits.parse_socrata_row(row, city_id="longview")

        assert event is not None
        assert (event.city_id, event.job_id, event.status) == ("longview", "BLD2026-99001", "ISSUED")
        assert (event.address_street, event.estimated_cost) == ("100 EXAMPLE DR", 285000.0)
        assert event.filing_date.isoformat() == "2026-09-24T14:10:05+00:00"
        assert event.issuance_date.isoformat() == "2026-10-01T21:57:59+00:00"
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (32.5007, -94.7405)
        # The project type names the building, not the work.
        assert event.job_type.value == "OT"

    def test_a_trade_permit_without_a_project_type_takes_its_code(self, permits):
        event = permits.parse_socrata_row(
            _permit(PERMIT_NUMBER="ROOF2026-99002", PERMIT_TYPE="RSREROOF#", PRJ_TYPE="", VALUATION=0.0),
            city_id="longview",
        )

        assert event is not None
        assert (event.job_type.value, event.estimated_cost) == ("OT", 0.0)


class TestLongviewPoll:
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

    def test_a_poll_publishes_each_permit_once_and_keeps_longviews(self, scheduler):
        producer = scheduler.producers["permits"]
        rows = [
            _permit(),
            _permit(OBJECTID=8, PERMIT_NUMBER="ELC2026-99003", PERMIT_TYPE="ELECPMT#", PRJ_TYPE="RESIDENTIAL",
                    VALUATION=None, latitude=32.5210, longitude=-94.7731),
            # South of the box, in Kilgore's direction.
            _permit(OBJECTID=9, PERMIT_NUMBER="PLM2026-99004", PERMIT_TYPE="PLUMBPMT#", PRJ_TYPE="COMMERCIAL",
                    latitude=32.3860, longitude=-94.8702),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("permits_longview")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 2, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert kwargs["max_records"] == 2500
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == ["longview:BLD2026-99001", "longview:ELC2026-99003"]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("permits_longview")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 2)
