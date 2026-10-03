"""Midland permits from the City's EnerGov permits layer (2026-10-02).

The City publishes its EnerGov permits as points on ArcGIS Online, one row per
application since 2000 (88,614 on 2026-10-02), with new rows added daily. A row
keeps the issue date and status it had when it was added: the layer dates 10
residential building permits issued in September 2026, against 73 to 101 a
month from October 2025 to May 2026, while applications held at 89 to 140 a
month. Midland reads the applications made in the 90 days before each poll,
which every row dates, and leaves out the permit names that are not building
work.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = [
    "OBJECTID", "PermitNumber", "Name", "PermitStatus", "ApplyDate", "DateIssued", "Address", "ZIPCODE",
    "CouncilDistrict",
]

FIELD_MAP = {
    "job_id": ["PermitNumber"],
    "issuance_date": ["DateIssued"],
    "filing_date": ["ApplyDate"],
    "job_type": ["Name"],
    "status": ["PermitStatus"],
    "address_street": ["Address"],
    "zipcode": ["ZIPCODE"],
    "borough": ["CouncilDistrict"],
}

# The names as the layer spells them: three end in a space.
LEFT_OUT = [
    "Driveway/Sidewalk", "Driveway/Sidewalk Standalone", "Franchise Utility Construction", "Oil And Gas ",
    "Water & Sewer Taps / Water Meters ", "Right of Way ", "Water Well", "Special Events",
    "Specific Use Designation - With Term", "Specific Use Designation - Without Term", "Vendor",
    "Parking Lot - Standalone", "Traffic Control", "Salt Water Disposal Well", "Cash Access Business",
]

WINDOW = (
    "ApplyDate >= CURRENT_DATE - INTERVAL '90' DAY AND ApplyDate <= CURRENT_TIMESTAMP AND Name NOT IN ("
    + ", ".join(f"'{name}'" for name in LEFT_OUT)
    + ")"
)

ORDER = "ApplyDate DESC, OBJECTID DESC"


def _spec():
    return get_dataset(CityId.MIDLAND, FeedType.PERMITS)


def _permit(**changes):
    """An application as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 7,
        "PermitNumber": "PLB-999001-2026",
        "Name": "Plumbing - Construction",
        "PermitStatus": "Issued",
        "ApplyDate": "2026-10-01T16:56:29+00:00",
        "DateIssued": "2026-10-01T16:56:39+00:00",
        "Address": "100 EXAMPLE ST",
        "ZIPCODE": "79701",
        "CouncilDistrict": "2",
        "latitude": 31.9973,
        "longitude": -102.0779,
        **changes,
    }


def test_midland_reads_the_citys_energov_permits_layer():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_midland_permits_url
    assert spec.endpoint == "https://services.arcgis.com/0H6bQdxd9223gQB5/arcgis/rest/services/Permits/FeatureServer/0"
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_the_window_holds_ninety_days_of_applications():
    spec = _spec()
    # The issue date stopped following permits issued after they were added,
    # so the window runs on the application date, which every row carries.
    assert spec.watermark_col == "ApplyDate"
    assert spec.where == WINDOW
    assert spec.order_by == ORDER


def test_the_request_names_its_columns():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The free-text description and the phone and contact columns stay on
    # the server.
    assert not {"Description1", "PHONE", "CONTACT"} & set(select)


def test_each_permit_publishes_once():
    # Four permit numbers repeated among the 2,622 rows in the window on
    # 2026-10-02.
    assert (_spec().id_keys, _spec().composite_id) == (["PermitNumber"], False)


def test_the_cap_holds_the_busiest_window_and_the_box_keeps_midlands():
    spec = _spec()
    # 2,622 rows in the window on 2026-10-02; the most in eight 90-day
    # windows back to October 2024 was 3,786, from April to July 2025.
    assert spec.batch_limit == 5000
    # 10 of the 2,622 had no point and 2 lay west of the box.
    assert spec.metro_clip is True
    # Rows were a day old at most on 2026-10-02, and none is added at
    # weekends.
    assert (spec.interval_seconds, spec.expected_cadence_days) == (21600.0, 3)


class TestMidlandPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_an_application_is_published_at_its_point(self, permits):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _permit().items() if key not in ("latitude", "longitude")}
        attributes["ApplyDate"] = 1790873789000  # 2026-10-01 16:56:29 UTC
        attributes["DateIssued"] = 1790873799000  # ten seconds later
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -102.0779, "y": 31.9973}},
            date_fields={"ApplyDate", "DateIssued"},
        )

        event = permits.parse_socrata_row(row, city_id="midland")

        assert event is not None
        assert (event.city_id, event.job_id, event.status) == ("midland", "PLB-999001-2026", "Issued")
        assert (event.address_street, event.zipcode) == ("100 EXAMPLE ST", "79701")
        assert event.filing_date.isoformat() == "2026-10-01T16:56:29+00:00"
        assert event.issuance_date.isoformat() == "2026-10-01T16:56:39+00:00"
        assert (event.job_type.value, event.normalized_permit_type) == ("A2", "MECHANICAL_ELECTRICAL_PLUMBING")
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (31.9973, -102.0779)
        assert event.borough == "CENTRAL_CORE"
        # The layer carries no cost.
        assert event.estimated_cost == 0.0

    def test_an_application_under_review_has_no_issue_date(self, permits):
        row = _permit(PermitNumber="RES-999002-2026", Name="Residential - Building", PermitStatus="Under Review",
                      DateIssued=None)

        event = permits.parse_socrata_row(row, city_id="midland")

        assert event is not None
        assert (event.status, event.issuance_date) == ("Under Review", None)
        assert event.filing_date.isoformat() == "2026-10-01T16:56:29+00:00"


class TestMidlandPoll:
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

    def test_a_poll_publishes_each_application_once_and_keeps_midlands(self, scheduler):
        producer = scheduler.producers["permits"]
        rows = [
            _permit(),
            # The same permit number twice in one read.
            _permit(OBJECTID=8),
            _permit(OBJECTID=9, PermitNumber="RES-999002-2026", Name="Residential - Building",
                    PermitStatus="Under Review", DateIssued=None, latitude=32.0412, longitude=-102.1501),
            # No point.
            _permit(OBJECTID=10, PermitNumber="ELC-999003-2026", latitude=None, longitude=None),
            # West of the box.
            _permit(OBJECTID=11, PermitNumber="ELC-999004-2026", latitude=31.9501, longitude=-102.3105),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("permits_midland")

        assert (result["records_fetched"], result["records_published"]) == (5, 2)
        assert (result["duplicates_skipped"], result["outside_metro"]) == (1, 2)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert kwargs["max_records"] == 5000
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == ["midland:PLB-999001-2026", "midland:RES-999002-2026"]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("permits_midland")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 3)
        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == f"({WINDOW})"
