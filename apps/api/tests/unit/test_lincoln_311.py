"""Lincoln 311 from SeeClickFix's public view of the City's requests (2026-10-02).

Lincoln's requests reach SeeClickFix, which publishes them as a public view on
its own ArcGIS Online org, as it does New Haven's: one point per request since
2011, about forty-five a day (4,211 in the 90 days to 2026-10-02, every one of
them public and the City's). The view stamps each request with the time it
arrived, and those times follow the view's object ids without exception, so
the poll follows the arrival time rather than the filing time. It reads only
each request's id, category, status and dates.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "id", "status", "category", "created_at", "closed_at", "CreationDate"]

FIELD_MAP = {
    "incident_id": ["id"],
    "created_date": ["created_at"],
    "closed_date": ["closed_at"],
    "complaint_type": ["category"],
    "status": ["status"],
}

ORDER = "CreationDate DESC, id DESC"


def _spec():
    return get_dataset(CityId.LINCOLN, FeedType.COMPLAINTS_311)


def _request(**changes):
    """A request as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 9700001,
        "id": 88000001,
        "status": "closed",
        "category": "Pothole",
        "created_at": "2026-10-01T22:15:40+00:00",
        "closed_at": "2026-10-01T23:02:11+00:00",
        "CreationDate": "2026-10-01T22:15:41.250000+00:00",
        "latitude": 40.8136,
        "longitude": -96.7026,
        **changes,
    }


def test_lincoln_reads_seeclickfixs_public_view():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_lincoln_311_url
    assert spec.endpoint.startswith("https://services8.arcgis.com/fz3KpsKgK9InMjh8/")
    assert spec.endpoint.endswith("/SCF_Requests_Public_Lincoln_NE/FeatureServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    # Of the 1,000 rows the view received last, two arrived after a request
    # filed 14 minutes later than they were; the arrival times follow the
    # object ids, so a poll that follows them passes over none.
    assert spec.watermark_col == "CreationDate"
    assert spec.order_by == ORDER
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_only_public_requests_are_read():
    # Every request in the 90 days to 2026-10-02 was public; the filter keeps
    # a private one on the server if it ever reaches the view.
    assert _spec().where == "private = '0'"


def test_the_request_names_its_columns_and_leaves_free_text_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The address, assignee, photo and page links and the editing accounts
    # stay on the server.
    assert not {
        "address", "assignee_name", "image_url", "image_square_url", "url", "Creator", "Editor",
    } & set(select)


def test_each_request_publishes_once():
    # SeeClickFix's own request id: the 11,858 requests filed in the year to
    # 2026-10-02 carry 11,858 ids.
    assert (_spec().id_keys, _spec().composite_id) == (["id"], False)


def test_requests_outside_the_metro_box_are_kept():
    # 23 of the 1,000 newest requests on 2026-10-02 lie outside the box, 19 of
    # them just south of it (40.69 to 40.72), and every request in the 90 days
    # to that date names the City of Lincoln as its agency.
    assert _spec().metro_clip is False


def test_the_poll_keeps_up_with_about_forty_five_requests_a_day():
    spec = _spec()
    assert spec.batch_limit is None
    assert spec.interval_seconds == 900.0
    # The longest quiet spell in the year to 2026-10-02 was just over a day.
    assert spec.expected_cadence_days == 1


class TestLincolnRequestParsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_a_closed_request_is_published_at_its_point(self, complaints):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _request().items() if key not in ("latitude", "longitude")}
        attributes["created_at"] = 1790892940000  # 2026-10-01 22:15:40 UTC
        attributes["closed_at"] = 1790895731000  # 2026-10-01 23:02:11 UTC
        attributes["CreationDate"] = 1790892941250  # 2026-10-01 22:15:41.25 UTC
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -96.7026, "y": 40.8136}},
            date_fields={"created_at", "closed_at", "CreationDate"},
        )

        event = complaints.parse_socrata_row(row, city_id="lincoln")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("lincoln", "88000001")
        assert (event.complaint_type, event.status) == ("Pothole", "closed")
        assert event.category.value == "NEGLECT"
        assert event.created_date.isoformat() == "2026-10-01T22:15:40+00:00"
        assert event.closed_date.isoformat() == "2026-10-01T23:02:11+00:00"
        assert event.incident_address is None
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (40.8136, -96.7026)


class TestLincolnPoll:
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

    def test_a_poll_publishes_public_requests_and_follows_the_arrival_time(self, scheduler):
        producer = scheduler.producers["311"]
        rows = [
            # Filed at 22:01 but received at 22:15:50, after a request filed
            # later: the watermark takes its arrival.
            _request(OBJECTID=9700003, id=88000002, status="open", category="Tree Issue",
                     created_at="2026-10-01T22:01:00+00:00", closed_at=None,
                     CreationDate="2026-10-01T22:15:50.500000+00:00"),
            _request(),
            # Just south of the metro box: still the City's.
            _request(OBJECTID=9700002, id=88000003, status="accepted", category="Sidewalk Obstruction",
                     created_at="2026-10-01T21:00:00+00:00", closed_at=None,
                     CreationDate="2026-10-01T21:00:00.900000+00:00", latitude=40.7050, longitude=-96.6900),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": None})

        result = scheduler.poll_job("311_lincoln")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 3, 0)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == "(private = '0')"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert "decode_domains" not in kwargs
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == [
            "lincoln:88000002", "lincoln:88000001", "lincoln:88000003",
        ]
        # Each event carries its filing time; only the watermark follows the
        # arrival.
        assert calls[0].kwargs["payload"].created_date.isoformat() == "2026-10-01T22:01:00+00:00"
        assert [call.kwargs["payload"].closed_date is not None for call in calls] == [False, True, False]
        assert scheduler.metrics["311_lincoln"].high_watermark == "2026-10-01T22:15:50"

        producer.arcgis.paginate = MagicMock(return_value=[[]])
        scheduler.poll_job("311_lincoln")

        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == (
            "(private = '0') AND CreationDate > '2026-10-01T22:15:50'"
        )
