"""Tucson permits from the City's residential building permits (2026-10-02).

The City GIS server publishes its EnerGov residential building permits
(20,003 on 2026-10-02, the oldest issued in 1997), each at its point with its
parcel, work class, value and dates, refreshed daily. Tucson reads the
permits issued in the 90 days before each poll (1,290 on 2026-10-02, the
newest issued that day). The issue date is midnight on most rows and carries
a time of day on a few, so the window runs on the server. The permits archive
the August probe found stopped in 2022; the City's map items for this layer
were last changed in September 2026.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "NUMBER", "ADDRESS", "PARCEL", "STATUS", "TYPE", "WORKCLASS", "APPLYDATE", "ISSUEDATE", "VALUE"]

FIELD_MAP = {
    "job_id": ["NUMBER"],
    "issuance_date": ["ISSUEDATE"],
    "filing_date": ["APPLYDATE"],
    "job_type": ["WORKCLASS", "TYPE"],
    "status": ["STATUS"],
    "cost": ["VALUE"],
    "address_street": ["ADDRESS"],
    "bbl": ["PARCEL"],
}

WINDOW = "ISSUEDATE >= CURRENT_DATE - INTERVAL '90' DAY AND ISSUEDATE <= CURRENT_TIMESTAMP"

ORDER = "ISSUEDATE DESC, OBJECTID DESC"


def _spec():
    return get_dataset(CityId.TUCSON, FeedType.PERMITS)


def _permit(**changes):
    """An issued permit as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 90001,
        "NUMBER": "TC-RES-0926-99001",
        "ADDRESS": "100 E EXAMPLE ST",
        "PARCEL": "199990010",
        "STATUS": "Issued",
        "TYPE": "Residential Building - One or Two Family",
        "WORKCLASS": "Residential Addition/Alteration Permit",
        "APPLYDATE": "2026-09-21T00:00:00+00:00",
        "ISSUEDATE": "2026-10-01T00:00:00+00:00",
        "VALUE": 23700.0,
        "latitude": 32.2501,
        "longitude": -110.9102,
        **changes,
    }


def test_tucson_reads_the_citys_residential_permits_layer():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_tucson_permits_url
    assert spec.endpoint == (
        "https://gis.tucsonaz.gov/public/rest/services/PublicMaps/PermitsCode/MapServer/85"
    )
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_the_window_holds_ninety_days_of_issued_permits():
    spec = _spec()
    assert spec.watermark_col == "ISSUEDATE"
    # Trade, solar, pool and fence permits stay in with the building work.
    assert spec.where == WINDOW
    assert spec.order_by == ORDER


def test_the_request_names_its_columns():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The project name, the free-text description and the portal links stay
    # on the server.
    assert not {"PROJECTNAME", "DESCRIPTION", "CSS_URL", "ENGOV_URL", "PRO_URL"} & set(select)


def test_each_permit_publishes_once():
    # Every one of the 1,290 permits in the window on 2026-10-02 had its own
    # number.
    assert (_spec().id_keys, _spec().composite_id) == (["NUMBER"], False)


def test_the_cap_holds_the_busiest_window_and_the_box_keeps_the_city():
    spec = _spec()
    # 1,290 permits in the window on 2026-10-02; the 90 days from 2025-08-17
    # held 1,329, the most in the two years before.
    assert spec.batch_limit == 2500
    # 274 of the 1,290 lie south or east of the metro box, in the City's
    # southern and south-eastern annexations.
    assert spec.metro_clip is True
    assert (spec.interval_seconds, spec.expected_cadence_days) == (21600.0, 3)


class TestTucsonPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_an_issued_permit_is_published_at_its_point_with_its_parcel(self, permits):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _permit().items() if key not in ("latitude", "longitude")}
        attributes["APPLYDATE"] = 1789948800000  # 2026-09-21 00:00 UTC
        attributes["ISSUEDATE"] = 1790812800000  # 2026-10-01 00:00 UTC
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -110.9102, "y": 32.2501}},
            date_fields={"APPLYDATE", "ISSUEDATE"},
        )

        event = permits.parse_socrata_row(row, city_id="tucson")

        assert event is not None
        assert (event.city_id, event.job_id, event.status) == ("tucson", "TC-RES-0926-99001", "Issued")
        assert (event.bbl, event.estimated_cost) == ("199990010", 23700.0)
        assert event.filing_date.isoformat() == "2026-09-21T00:00:00+00:00"
        assert event.issuance_date.isoformat() == "2026-10-01T00:00:00+00:00"
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (32.2501, -110.9102)
        assert (event.job_type.value, event.normalized_permit_type) == ("A2", "MAJOR_RENOVATION")

    def test_a_new_dwelling_reads_as_new_construction_in_the_normalized_type(self, permits):
        event = permits.parse_socrata_row(
            _permit(NUMBER="TC-RES-0926-99002", WORKCLASS="New Dwelling Permit", VALUE=244600.0), city_id="tucson"
        )

        assert event is not None
        # The job type codes know no "new dwelling"; the normalized type does.
        assert (event.job_type.value, event.normalized_permit_type) == ("OT", "NEW_CONSTRUCTION")

    def test_a_model_permit_takes_the_catch_all_type(self, permits):
        # A home built from a plan the City approved once (141 in the window
        # on 2026-10-02, averaging 2,331 square feet): neither type reads the
        # name as new construction.
        event = permits.parse_socrata_row(
            _permit(NUMBER="TC-RES-0926-99003", TYPE="Model Building Permit", WORKCLASS="Residential Model Permit",
                    VALUE=288800.0),
            city_id="tucson",
        )

        assert event is not None
        assert (event.job_type.value, event.normalized_permit_type) == ("OT", "MINOR_ALTERATION")


class TestTucsonPoll:
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

    def test_a_poll_publishes_each_permit_inside_the_metro_once(self, scheduler):
        producer = scheduler.producers["permits"]
        rows = [
            _permit(),
            _permit(OBJECTID=90002, NUMBER="TC-RES-0926-99004", TYPE="Demolition Permit",
                    WORKCLASS="Residential Demolition Permit", ISSUEDATE="2026-09-30T17:22:05+00:00",
                    latitude=32.2210, longitude=-110.9705),
            # A permit in the south-eastern annexation, below the metro box.
            _permit(OBJECTID=90003, NUMBER="TC-RES-0926-99005", WORKCLASS="Residential Trade Permit", VALUE=0.0,
                    latitude=32.1104, longitude=-110.8085),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("permits_tucson")

        assert (result["records_fetched"], result["records_published"]) == (3, 2)
        assert (result["duplicates_skipped"], result["outside_metro"]) == (0, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert kwargs["max_records"] == 2500
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == ["tucson:TC-RES-0926-99001", "tucson:TC-RES-0926-99004"]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("permits_tucson")

        assert (result["records_published"], result["duplicates_skipped"], result["outside_metro"]) == (0, 2, 1)
