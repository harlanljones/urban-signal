"""Odessa 311 from the City's SeeClickFix requests layer (2026-10-02).

Odessa runs its 311 service ("Team Odessa") on SeeClickFix, which publishes
the City's requests to the City's ArcGIS Online org through a federated server
proxy: one point per request since June 2025 (5,366 on 2026-10-02), about ten
a day. The poll reads the public requests newer than its watermark, each by
its id, category, status and dates.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "id", "status", "category", "created_at", "closed_at"]

FIELD_MAP = {
    "incident_id": ["id"],
    "created_date": ["created_at"],
    "closed_date": ["closed_at"],
    "complaint_type": ["category"],
    "status": ["status"],
}

ORDER = "created_at DESC, id DESC"


def _spec():
    return get_dataset(CityId.ODESSA, FeedType.COMPLAINTS_311)


def _request(**changes):
    """A request as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 5001,
        "id": 99000001,
        "status": "closed",
        "category": "Traffic Signal Out",
        "created_at": "2026-10-02T13:42:53+00:00",
        "closed_at": "2026-10-02T14:15:37+00:00",
        "latitude": 31.8457,
        "longitude": -102.3676,
        **changes,
    }


def test_odessa_reads_its_seeclickfix_requests_layer():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_odessa_311_url
    assert spec.endpoint.startswith("https://utility.arcgis.com/usrsvcs/servers/d29bb427c9bc497fae24cbd89f5b8b6d/")
    assert spec.endpoint.endswith("/ServiceRequests_OdessaTX/FeatureServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    assert (spec.watermark_col, spec.order_by) == ("created_at", ORDER)
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 1000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_only_public_requests_are_read():
    # 13 of the 5,366 requests on 2026-10-02 were private.
    assert _spec().where == "private = '0'"


def test_the_request_names_its_columns_and_leaves_the_reporter_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    assert not {
        "reporter_name", "reporter_email", "summary", "description", "address", "assignee_name",
    } & set(select)


def test_each_request_publishes_once():
    assert (_spec().id_keys, _spec().composite_id) == (["id"], False)


def test_requests_north_of_the_metro_box_are_clipped():
    # 137 of the 1,000 newest public requests on 2026-10-02 lay in north
    # Odessa, above latitude 31.94.
    assert _spec().metro_clip is True


def test_the_poll_keeps_up_with_about_ten_requests_a_day():
    spec = _spec()
    assert spec.batch_limit is None
    assert (spec.interval_seconds, spec.expected_cadence_days) == (900.0, 2)


class TestOdessaRequestParsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_a_closed_request_is_published_at_its_point(self, complaints):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _request().items() if key not in ("latitude", "longitude")}
        attributes["created_at"] = 1790948573000  # 2026-10-02 13:42:53 UTC
        attributes["closed_at"] = 1790950537000  # 2026-10-02 14:15:37 UTC
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -102.3676, "y": 31.8457}},
            date_fields={"created_at", "closed_at"},
        )

        event = complaints.parse_socrata_row(row, city_id="odessa")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("odessa", "99000001")
        assert (event.complaint_type, event.status) == ("Traffic Signal Out", "closed")
        assert event.created_date.isoformat() == "2026-10-02T13:42:53+00:00"
        assert event.closed_date.isoformat() == "2026-10-02T14:15:37+00:00"
        assert event.incident_address is None
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (31.8457, -102.3676)


class TestOdessaPoll:
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

    def test_a_poll_publishes_the_metros_public_requests_and_follows_the_filing_time(self, scheduler):
        producer = scheduler.producers["311"]
        rows = [
            _request(),
            _request(OBJECTID=5000, id=99000002, status="open", category="High Weeds or Grass",
                     created_at="2026-10-02T12:10:00+00:00", closed_at=None, latitude=31.8611, longitude=-102.4012),
            # North Odessa, above the box.
            _request(OBJECTID=4999, id=99000003, status="accepted", category="Pothole",
                     created_at="2026-10-02T11:05:00+00:00", closed_at=None, latitude=31.9502, longitude=-102.3301),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": None})

        result = scheduler.poll_job("311_odessa")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 2, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == "(private = '0')"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == ["odessa:99000001", "odessa:99000002"]
        assert scheduler.metrics["311_odessa"].high_watermark == "2026-10-02T13:42:53"

        producer.arcgis.paginate = MagicMock(return_value=[[]])
        scheduler.poll_job("311_odessa")

        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == (
            "(private = '0') AND created_at > '2026-10-02T13:42:53'"
        )
