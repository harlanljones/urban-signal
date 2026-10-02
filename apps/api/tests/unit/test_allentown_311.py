"""Allentown 311 from the City's Survey123 problem reports (2026-10-02).

The City's ArcGIS Online org, which carries the layers Allentown's permits and
deeds come from, publishes the requests residents file through its Survey123
problem reporter as a public view: one point per request since October 2025
(713 on 2026-10-02, 266 of them in the last 90 days). The form stores its
choices as codes, "130245" for "Report a Pothole", whose names live only in
the layer's field domains, so the poll reads each code as its name. Twelve
requests sit at 0,0, and the metro clip skips them.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["objectid", "globalid", "issue", "status", "CreationDate"]

FIELD_MAP = {
    "incident_id": ["globalid"],
    "created_date": ["CreationDate"],
    "complaint_type": ["issue"],
    "status": ["status"],
}

ORDER = "CreationDate DESC, objectid DESC"

FIRST = "00000000-0000-4000-8000-000000000001"
SECOND = "00000000-0000-4000-8000-000000000002"


def _spec():
    return get_dataset(CityId.ALLENTOWN, FeedType.COMPLAINTS_311)


def _request(**changes):
    """A request as the ArcGIS client hands it on, its codes read as names
    (synthetic values)."""
    return {
        "objectid": 7,
        "globalid": FIRST,
        "issue": "Report a Pothole",
        "status": "New Request",
        "CreationDate": "2026-10-01T14:05:12.250000+00:00",
        "latitude": 40.6023,
        "longitude": -75.4714,
        **changes,
    }


def test_allentown_reads_the_citys_survey123_problem_reports():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_allentown_311_url
    assert spec.endpoint.startswith("https://services1.arcgis.com/WUqVDRuvIiIiH2Pl/")
    assert spec.endpoint.endswith("/311_Submission_Dashboard_View/FeatureServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    # The layer stamps each request with the time it arrives, so a request
    # that arrives later never carries an earlier time.
    assert spec.watermark_col == "CreationDate"
    assert spec.order_by == ORDER
    assert (spec.oid_field, spec.max_record_count) == ("objectid", 1000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_the_request_names_its_columns_and_leaves_free_text_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The form's address and cross street, the staff notes, the vegetation
    # description and the contact flag stay on the server; three of the 710
    # addresses on 2026-09-30 contained an "@".
    assert not {"address", "intersecting_street", "internal_notes", "overgrown_veg_desc", "contact_info"} & set(select)


def test_each_request_publishes_once():
    assert (_spec().id_keys, _spec().composite_id) == (["globalid"], False)


def test_the_poll_reads_each_code_as_its_name():
    assert _spec().decode_domains is True


def test_requests_at_zero_zero_are_skipped():
    # Twelve of the 713 requests on 2026-10-02 carry 0,0 for their point.
    assert _spec().metro_clip is True


def test_the_poll_suits_a_few_requests_a_day():
    spec = _spec()
    # 266 requests in the 90 days to 2026-10-02, so one poll's default cap
    # holds months of them.
    assert spec.batch_limit is None
    assert spec.interval_seconds == 900.0
    # The longest quiet spell in the 90 days to 2026-09-30 was 2.1 days, so
    # the alarm (twice the cadence) waits six.
    assert spec.expected_cadence_days == 3


class TestAllentownRequestParsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_a_request_is_published_at_its_point_under_its_named_issue(self, complaints):
        from src.producers.arcgis_client import ArcGISClient

        feature = {
            "attributes": {
                "objectid": 7, "globalid": FIRST, "issue": "130245", "status": "1",
                "CreationDate": 1790863512250,  # 2026-10-01 14:05:12.25 UTC
            },
            "geometry": {"x": -75.4714, "y": 40.6023},
        }
        coded_values = {"issue": {"130245": "Report a Pothole"}, "status": {"1": "New Request"}}
        row = ArcGISClient()._flatten_feature(feature, date_fields={"CreationDate"}, coded_values=coded_values)

        event = complaints.parse_socrata_row(row, city_id="allentown")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("allentown", FIRST)
        assert (event.complaint_type, event.status) == ("Report a Pothole", "New Request")
        assert event.category.value == "NEGLECT"
        assert event.created_date.isoformat() == "2026-10-01T14:05:12.250000+00:00"
        # The layer has no closing date, and the address stays on the server.
        assert (event.closed_date, event.incident_address) == (None, None)
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (40.6023, -75.4714)


class TestAllentownPoll:
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

    def test_a_poll_skips_requests_at_zero_zero_and_follows_the_arrival_time(self, scheduler):
        producer = scheduler.producers["311"]
        rows = [
            _request(),
            _request(objectid=8, globalid=SECOND, issue="Illegal Dumping", status="Completed",
                     CreationDate="2026-09-30T19:41:03.500000+00:00", latitude=40.5871, longitude=-75.4903),
            # A report filed without a point arrives at 0,0.
            _request(objectid=9, globalid="00000000-0000-4000-8000-000000000003", issue="Other",
                     CreationDate="2026-09-30T12:00:00+00:00", latitude=0.0, longitude=0.0),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": None})

        result = scheduler.poll_job("311_allentown")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 2, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] is None
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        # The client reads each code as its name before the rows reach the poll.
        assert kwargs["decode_domains"] is True
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == [f"allentown:{FIRST}", f"allentown:{SECOND}"]
        assert [call.kwargs["payload"].complaint_type for call in calls] == ["Report a Pothole", "Illegal Dumping"]
        assert scheduler.metrics["311_allentown"].high_watermark == "2026-10-01T14:05:12"

        producer.arcgis.paginate = MagicMock(return_value=[[]])
        scheduler.poll_job("311_allentown")

        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == "CreationDate > '2026-10-01T14:05:12'"
