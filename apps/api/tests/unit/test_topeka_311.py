"""Topeka 311 from the City's Cityworks request view (2026-10-02).

The CityworksViews folder on the City's ArcGIS server, which already serves
Topeka's permits, also serves ``SCF_E311_Requests``: the City's 311 requests
as Cityworks holds them, one point per request since 2013, 8,825 in the year
to 2026-10-02 (about 24 a day, none of its days without one). The view
rejects ISO date strings, so its path takes ANSI literals. The poll reads
only each request's id, problem code, department, status and dates.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = [
    "ObjectId", "requestid", "problemcode", "reqcategory", "status",
    "datetimeinit", "datetimeclosed", "dateclosed",
]

FIELD_MAP = {
    "incident_id": ["requestid"],
    "created_date": ["datetimeinit"],
    "closed_date": ["datetimeclosed", "dateclosed"],
    "complaint_type": ["problemcode", "reqcategory"],
    "status": ["status"],
}

ORDER = "datetimeinit DESC, ObjectId DESC"


def _spec():
    return get_dataset(CityId.TOPEKA, FeedType.COMPLAINTS_311)


def _request(**changes):
    """A request as the ArcGIS client hands it on (synthetic values)."""
    return {
        "ObjectId": 70001,
        "requestid": 230001,
        "problemcode": "Pothole Repair",
        "reqcategory": "STREETS",
        "status": "CLOSED",
        "datetimeinit": "2026-10-01T13:38:18+00:00",
        "datetimeclosed": "2026-10-01T13:47:41+00:00",
        "dateclosed": None,
        "latitude": 39.0473,
        "longitude": -95.6752,
        **changes,
    }


def test_topeka_reads_the_citys_cityworks_request_view():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_topeka_311_url
    assert spec.endpoint.startswith("https://maps.topeka.gov/arcgis/rest/services/CityworksViews/")
    assert spec.endpoint.endswith("/SCF_E311_Requests/FeatureServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    # Over the year to 2026-10-02 the request times follow the view's object
    # ids and request ids without exception, so none arrives late.
    assert spec.watermark_col == "datetimeinit"
    assert spec.order_by == ORDER
    assert (spec.oid_field, spec.max_record_count) == ("ObjectId", 3000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_the_311_view_takes_ansi_literals_and_the_permits_view_keeps_iso():
    from src.producers.watermarks import ANSI_DATE_LITERAL_HOSTS, watermark_comparison

    spec = _spec()
    permits = get_dataset(CityId.TOPEKA, FeedType.PERMITS)
    assert "maps.topeka.gov" not in ANSI_DATE_LITERAL_HOSTS
    # The view declares UTC and answers 400 to ``datetimeinit > '...T...'``.
    assert watermark_comparison(
        "datetimeinit", ">", "2026-10-01T13:38:18", spec.endpoint, time_zone="Etc/UTC"
    ) == "datetimeinit > timestamp '2026-10-01 13:38:18'"
    # The permits view on the same host answers 400 to an ANSI literal.
    assert watermark_comparison(
        "Date_Issued", ">", "2026-10-01T13:38:18", permits.endpoint
    ) == "Date_Issued > '2026-10-01T13:38:18'"
    # Its dates are text ("9/4/2026"), so its poll names the days since the
    # watermark rather than comparing text.
    assert watermark_comparison(
        permits.watermark_col,
        ">=",
        "9/30/2026",
        permits.endpoint,
        watermark_type=permits.watermark_type,
        watermark_format=permits.watermark_format,
        today=date(2026, 10, 2),
    ) == "Date_Issued IN ('09/30/2026', '9/30/2026', '10/01/2026', '10/1/2026', '10/02/2026', '10/2/2026')"


def test_the_request_names_its_columns_and_leaves_free_text_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The description, details, address, initiator, assignee and Cityworks
    # link stay on the server.
    assert not {
        "description", "details", "probaddress", "initiatedby", "submitto", "cwlink",
    } & set(select)
    assert _spec().where is None


def test_each_request_publishes_once():
    # The 8,825 requests filed in the year to 2026-10-02 carry 8,825 ids.
    assert (_spec().id_keys, _spec().composite_id) == (["requestid"], False)


def test_every_request_is_the_citys():
    # All 2,925 requests filed in the 90 days to 2026-10-02 lie inside the box.
    assert _spec().metro_clip is False


def test_the_poll_keeps_up_with_about_two_dozen_requests_a_day():
    spec = _spec()
    assert spec.batch_limit is None
    assert spec.interval_seconds == 1800.0
    # Every day of the year to 2026-10-02 had a request; the longest quiet
    # spell was 0.89 days.
    assert spec.expected_cadence_days == 1


class TestTopekaRequestParsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def _row(self, **attributes):
        from src.producers.arcgis_client import ArcGISClient

        base = {key: value for key, value in _request().items() if key not in ("latitude", "longitude")}
        base.update(datetimeinit=1790861898000, datetimeclosed=1790862461000)  # 13:38:18, 13:47:41 UTC
        base.update(attributes)
        return ArcGISClient()._flatten_feature(
            {"attributes": base, "geometry": {"x": -95.6752, "y": 39.0473}},
            date_fields={"datetimeinit", "datetimeclosed", "dateclosed"},
        )

    def test_a_closed_request_is_published_at_its_point(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="topeka")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("topeka", "230001")
        assert (event.complaint_type, event.status) == ("Pothole Repair", "CLOSED")
        assert event.category.value == "NEGLECT"
        assert event.created_date.isoformat() == "2026-10-01T13:38:18+00:00"
        assert event.closed_date.isoformat() == "2026-10-01T13:47:41+00:00"
        assert event.incident_address is None
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (39.0473, -95.6752)

    def test_a_completed_request_takes_its_closing_day(self, complaints):
        # COMPLETE requests carry ``dateclosed`` only.
        row = self._row(status="COMPLETE", datetimeclosed=None, dateclosed=1790866920000)

        event = complaints.parse_socrata_row(row, city_id="topeka")

        assert event.closed_date.isoformat() == "2026-10-01T15:02:00+00:00"


class TestTopekaPoll:
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

    def test_a_poll_publishes_requests_and_sends_an_ansi_watermark(self, scheduler):
        producer = scheduler.producers["311"]
        rows = [
            _request(ObjectId=70003, requestid=230003, problemcode="Complaints-Nuisance", reqcategory="CODE",
                     status="OPEN", datetimeinit="2026-10-02T00:03:53+00:00", datetimeclosed=None),
            _request(ObjectId=70002, requestid=230002, problemcode="Tree Limb/Brush", reqcategory="FORESTRY",
                     status="INPROGRESS", datetimeinit="2026-10-01T18:20:05+00:00", datetimeclosed=None),
            _request(),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": "Etc/UTC"})

        result = scheduler.poll_job("311_topeka")

        assert (result["records_fetched"], result["records_published"]) == (3, 3)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] is None
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == ["topeka:230003", "topeka:230002", "topeka:230001"]
        assert [call.kwargs["payload"].complaint_type for call in calls] == [
            "Complaints-Nuisance", "Tree Limb/Brush", "Pothole Repair",
        ]
        assert scheduler.metrics["311_topeka"].high_watermark == "2026-10-02T00:03:53"

        producer.arcgis.paginate = MagicMock(return_value=[[]])
        scheduler.poll_job("311_topeka")

        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == (
            "datetimeinit > timestamp '2026-10-02 00:03:53'"
        )
