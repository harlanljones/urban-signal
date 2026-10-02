"""New Haven 311 from SeeClickFix's public view of the City's requests (2026-10-02).

New Haven runs its 311 service on SeeClickFix, and SeeClickFix publishes the
City's requests as a public view on its own ArcGIS Online org: one point per
request since 2007, about forty a day (3,536 in the 90 days to 2026-09-30,
every one of them public). The poll keeps to attribute filters, since a
spatial filter on the view times out, and reads only each request's id,
category, status and dates.
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
    return get_dataset(CityId.NEW_HAVEN, FeedType.COMPLAINTS_311)


def _request(**changes):
    """A request as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 9600001,
        "id": 99000001,
        "status": "closed",
        "category": "Potholes",
        "created_at": "2026-10-01T22:15:40+00:00",
        "closed_at": "2026-10-01T23:02:11+00:00",
        "latitude": 41.3083,
        "longitude": -72.9279,
        **changes,
    }


def test_new_haven_reads_seeclickfixs_public_view():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_new_haven_311_url
    assert spec.endpoint.startswith("https://services8.arcgis.com/fz3KpsKgK9InMjh8/")
    assert spec.endpoint.endswith("/Public_SCF_Requests_New_Haven_CT/FeatureServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    # Of the 500 rows the view added last, two reached it after a request
    # filed later than they were, by two minutes at most.
    assert spec.watermark_col == "created_at"
    assert spec.order_by == ORDER
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_only_public_requests_are_read():
    # Every request in the 90 days to 2026-09-30 was public; the filter keeps
    # a private one on the server if it ever reaches the view.
    assert _spec().where == "private = '0'"


def test_the_request_names_its_columns_and_leaves_free_text_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The summary, description, address, assignee and photo and page links
    # stay on the server.
    assert not {
        "summary", "description", "address", "assignee_name", "image_url", "image_square_url", "url",
    } & set(select)


def test_each_request_publishes_once():
    # SeeClickFix's own request id, not the view's object id, which a
    # rebuild of the view would reassign.
    assert (_spec().id_keys, _spec().composite_id) == (["id"], False)


def test_requests_south_of_the_metro_box_are_kept():
    # 33 of the 1,000 newest requests on 2026-10-02 lie between 41.253 and
    # 41.27, at longitude -72.89 to -72.90: the City's Morris Cove shore,
    # south of the metro box.
    assert _spec().metro_clip is False


def test_the_poll_keeps_up_with_about_forty_requests_a_day():
    spec = _spec()
    assert spec.batch_limit is None
    assert spec.interval_seconds == 900.0
    assert spec.expected_cadence_days == 1


class TestNewHavenRequestParsing:
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
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -72.9279, "y": 41.3083}},
            date_fields={"created_at", "closed_at"},
        )

        event = complaints.parse_socrata_row(row, city_id="new_haven")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("new_haven", "99000001")
        assert (event.complaint_type, event.status) == ("Potholes", "closed")
        assert event.category.value == "NEGLECT"
        assert event.created_date.isoformat() == "2026-10-01T22:15:40+00:00"
        assert event.closed_date.isoformat() == "2026-10-01T23:02:11+00:00"
        assert event.incident_address is None
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (41.3083, -72.9279)


class TestNewHavenPoll:
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

    def test_a_poll_publishes_public_requests_and_follows_the_filing_time(self, scheduler):
        producer = scheduler.producers["311"]
        rows = [
            _request(OBJECTID=9600003, id=99000002, status="open", category="Illegal Dumping",
                     created_at="2026-10-01T23:40:05+00:00", closed_at=None),
            _request(),
            # On the Morris Cove shore, south of the metro box: still the City's.
            _request(OBJECTID=9600002, id=99000003, status="acknowledged", category="Tree Requests",
                     created_at="2026-10-01T21:00:00+00:00", closed_at=None, latitude=41.2580, longitude=-72.8950),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": None})

        result = scheduler.poll_job("311_new_haven")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 3, 0)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == "(private = '0')"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert "decode_domains" not in kwargs
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == [
            "new_haven:99000002", "new_haven:99000001", "new_haven:99000003",
        ]
        assert [call.kwargs["payload"].closed_date is not None for call in calls] == [False, True, False]
        assert scheduler.metrics["311_new_haven"].high_watermark == "2026-10-01T23:40:05"

        producer.arcgis.paginate = MagicMock(return_value=[[]])
        scheduler.poll_job("311_new_haven")

        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == (
            "(private = '0') AND created_at > '2026-10-01T23:40:05'"
        )
