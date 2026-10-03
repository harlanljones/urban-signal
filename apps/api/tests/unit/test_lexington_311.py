"""Lexington 311 from LFUCG's LexCall requests layer (2026-10-02).

LFUCG publishes its LexCall requests, from its Salesforce CRM, as a hosted
layer on its ArcGIS Online org: a rolling 30 days (8,455 requests on
2026-10-02), refreshed about every 30 minutes, each at its point. The poll
reads the requests newer than its watermark. The layer has no status or
closed date.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = [
    "OBJECTID", "CaseNumber", "Problem_Code__c", "Problem_text__c", "Division__c", "LOCATION__LATITUDE__S",
    "LOCATION__LONGITUDE__S", "CreatedDate", "zip__c",
]

FIELD_MAP = {
    "incident_id": ["CaseNumber"],
    "created_date": ["CreatedDate"],
    "complaint_type": ["Problem_text__c", "Problem_Code__c", "Division__c"],
    "latitude": ["LOCATION__LATITUDE__S"],
    "longitude": ["LOCATION__LONGITUDE__S"],
    "zipcode": ["zip__c"],
}

ORDER = "CreatedDate DESC, OBJECTID DESC"


def _spec():
    return get_dataset(CityId.LEXINGTON, FeedType.COMPLAINTS_311)


def _request(**changes):
    """A request as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 8001,
        "CaseNumber": "9900001",
        "Problem_Code__c": "361TS018",
        "Problem_text__c": "Signal malfunction (OAC)",
        "Division__c": "Traffic Engineering",
        "LOCATION__LATITUDE__S": 38.0462,
        "LOCATION__LONGITUDE__S": -84.4970,
        "CreatedDate": "2026-10-02T14:25:59+00:00",
        "zip__c": "40507",
        "latitude": 38.0462,
        "longitude": -84.4970,
        **changes,
    }


def test_lexington_reads_the_lexcall_requests_layer():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_lexington_311_url
    assert spec.endpoint == (
        "https://services1.arcgis.com/Mg7DLdfYcSWIaDnu/arcgis/rest/services/CitizenRequests_public/FeatureServer/0"
    )
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    assert (spec.watermark_col, spec.order_by) == ("CreatedDate", ORDER)
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_the_layer_is_a_rolling_thirty_days():
    spec = _spec()
    assert (spec.rolling_window_days, spec.retention_days) == (30, 30)
    # No request is dated ahead of the clock; the filter keeps one that is
    # from pinning the watermark.
    assert spec.where == "CreatedDate <= CURRENT_TIMESTAMP"


def test_the_request_names_its_columns_and_leaves_the_address_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    assert "Address__c" not in select


def test_each_request_publishes_once():
    # One case number repeated among the 8,455 rows on 2026-10-02.
    assert (_spec().id_keys, _spec().composite_id) == (["CaseNumber"], False)


def test_the_poll_keeps_up_with_about_three_hundred_requests_a_day():
    spec = _spec()
    # 8,447 of the 8,455 points lay inside the box.
    assert spec.metro_clip is True
    assert spec.batch_limit is None
    assert (spec.interval_seconds, spec.expected_cadence_days) == (900.0, 1)


class TestLexingtonRequestParsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_a_request_is_published_at_its_point_with_its_problem(self, complaints):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _request().items() if key not in ("latitude", "longitude")}
        attributes["CreatedDate"] = 1790951159000  # 2026-10-02 14:25:59 UTC
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -84.4970, "y": 38.0462}},
            date_fields={"CreatedDate"},
        )

        event = complaints.parse_socrata_row(row, city_id="lexington")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("lexington", "9900001")
        assert (event.complaint_type, event.zipcode) == ("Signal malfunction (OAC)", "40507")
        assert event.created_date.isoformat() == "2026-10-02T14:25:59+00:00"
        assert (event.closed_date, event.incident_address) == (None, None)
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (38.0462, -84.4970)

    def test_a_code_enforcement_request_is_a_residents_request(self, complaints):
        event = complaints.parse_socrata_row(
            _request(CaseNumber="9900002", Problem_Code__c="581N", Problem_text__c="Nuisance - Code Enforcement",
                     Division__c="Code Enforcement"),
            city_id="lexington",
        )

        assert event is not None
        assert event.complaint_type == "Nuisance - Code Enforcement"

    def test_a_request_without_a_problem_or_division_is_unknown(self, complaints):
        event = complaints.parse_socrata_row(
            _request(CaseNumber="9900003", Problem_Code__c=None, Problem_text__c=None, Division__c=None),
            city_id="lexington",
        )

        assert event is not None
        assert event.complaint_type == "Unknown"


class TestLexingtonPoll:
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

    def test_a_poll_publishes_the_requests_and_follows_the_filing_time(self, scheduler):
        producer = scheduler.producers["311"]
        rows = [
            _request(),
            _request(OBJECTID=8000, CaseNumber="9900004", Problem_Code__c="351H2",
                     Problem_text__c="Missed Bulky Pickup", Division__c="Waste Management",
                     CreatedDate="2026-10-02T13:58:18+00:00", LOCATION__LATITUDE__S=38.0912,
                     LOCATION__LONGITUDE__S=-84.5496, latitude=38.0912, longitude=-84.5496),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": None})

        result = scheduler.poll_job("311_lexington")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (2, 2, 0)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == "(CreatedDate <= CURRENT_TIMESTAMP)"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert [call.kwargs["key"] for call in producer.producer.produce.call_args_list] == [
            "lexington:9900001", "lexington:9900004",
        ]
        assert scheduler.metrics["311_lexington"].high_watermark == "2026-10-02T14:25:59"

        producer.arcgis.paginate = MagicMock(return_value=[[]])
        scheduler.poll_job("311_lexington")

        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == (
            "(CreatedDate <= CURRENT_TIMESTAMP) AND CreatedDate > '2026-10-02T14:25:59'"
        )
