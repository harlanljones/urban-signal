"""Yakima 311 from the City's YakBack requests layer (2026-10-02).

The City GIS server that serves Yakima's permits also serves ``YakBack/
PublicRequest``: the City's service requests, one point per request over a
rolling three years, 5,208 filed from 2025-10-01 to 2026-10-02 (about 14 a
day, one day without any). Its request type and status are coded values,
read as their names. The layer declares Pacific Standard Time without
daylight saving and rejects ISO date strings, as the permits layer on the
same host now does too, so the host takes ANSI literals, in each layer's
zone. The poll reads only each request's id, type, status and dates.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "requestId", "dateOpened", "dateClosed", "type", "status"]

FIELD_MAP = {
    "incident_id": ["requestId"],
    "created_date": ["dateOpened"],
    "closed_date": ["dateClosed"],
    "complaint_type": ["type"],
    "status": ["status"],
}

ORDER = "dateOpened DESC, requestId DESC"

# Part of the layer's ``type`` and ``status`` domains.
CODED_VALUES = {
    "type": {"4": "Pothole or Street Surface", "6": "Parking", "99": "Other"},
    "status": {"1": "Open", "2": "Closed"},
}


def _spec():
    return get_dataset(CityId.YAKIMA, FeedType.COMPLAINTS_311)


def _request(**changes):
    """A request as the ArcGIS client hands it on, names decoded (synthetic values)."""
    return {
        "OBJECTID": 788013,
        "requestId": 9151632,
        "dateOpened": "2026-10-02T05:49:39+00:00",
        "dateClosed": "2026-10-02T06:12:04+00:00",
        "type": "Parking",
        "status": "Closed",
        "latitude": 46.5935,
        "longitude": -120.5481,
        **changes,
    }


def test_yakima_reads_the_citys_yakback_layer():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_yakima_311_url
    assert spec.endpoint.startswith("https://gis.yakimawa.gov/arcgis/rest/services/YakBack/")
    assert spec.endpoint.endswith("/PublicRequest/MapServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    # Request ids follow the opening times over the year to 2026-10-02, but
    # for two ids from an older series and one request entered six days late.
    assert spec.watermark_col == "dateOpened"
    assert spec.order_by == ORDER
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_the_type_and_status_codes_read_as_their_names():
    # Both columns are small integers; ``Complaint311Event`` takes text.
    assert _spec().decode_domains is True


def test_the_host_takes_ansi_literals_in_each_layers_zone():
    from src.producers.watermarks import watermark_comparison

    spec = _spec()
    permits = get_dataset(CityId.YAKIMA, FeedType.PERMITS)
    # The 311 layer declares Pacific Standard Time without daylight saving.
    assert watermark_comparison(
        "dateOpened", ">", "2026-10-02T05:49:39", spec.endpoint, time_zone="Etc/GMT+8"
    ) == "dateOpened > timestamp '2026-10-01 21:49:39'"
    # The permits layer declares UTC. It took ISO strings on 2026-08-28 and
    # answered 400 to ``IssuedOnDate > '2026-09-01T00:00:00'`` on 2026-10-02.
    assert watermark_comparison(
        "IssuedOnDate", ">=", "2026-09-25T00:00:00", permits.endpoint
    ) == "IssuedOnDate >= timestamp '2026-09-25 00:00:00'"


def test_the_request_names_its_columns_and_leaves_people_and_free_text_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The requester's name, email and phone, the staff who handle it, the
    # address and the free text stay on the server.
    assert not {
        "name", "email", "phone", "address", "description", "completedNotes",
        "assignedTo", "closedBy", "updatedBy",
    } & set(select)
    assert _spec().where is None


def test_each_request_publishes_once():
    # One request appears twice among the 5,208 rows of the year to
    # 2026-10-02, once open and once closed.
    assert (_spec().id_keys, _spec().composite_id) == (["requestId"], False)


def test_every_request_is_the_citys():
    # 1,242 of the 1,243 requests filed in the 90 days to 2026-10-02 lie
    # inside the metro box; the other has no point.
    assert _spec().metro_clip is False


def test_the_poll_keeps_up_with_about_a_dozen_requests_a_day():
    spec = _spec()
    assert spec.batch_limit is None
    assert spec.interval_seconds == 1800.0
    # The longest quiet spell in the year to 2026-10-02 was 1.49 days.
    assert spec.expected_cadence_days == 1


class TestYakimaRequestParsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    @staticmethod
    def _row(geometry=None, **attributes):
        from src.producers.arcgis_client import ArcGISClient

        base = {key: value for key, value in _request().items() if key not in ("latitude", "longitude")}
        # Epoch values as the server converts them from its fixed zone.
        base.update(dateOpened=1790920179000, dateClosed=1790921524000, type=6, status=2)
        base.update(attributes)
        return ArcGISClient()._flatten_feature(
            {"attributes": base, "geometry": geometry if geometry is not None else {"x": -120.5481, "y": 46.5935}},
            date_fields={"dateOpened", "dateClosed"},
            coded_values=CODED_VALUES,
        )

    def test_a_closed_request_is_published_with_its_names(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="yakima")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("yakima", "9151632")
        assert (event.complaint_type, event.status) == ("Parking", "Closed")
        assert event.created_date.isoformat() == "2026-10-02T05:49:39+00:00"
        assert event.closed_date.isoformat() == "2026-10-02T06:12:04+00:00"
        assert event.incident_address is None
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (46.5935, -120.5481)

    def test_an_open_pothole_request_reads_as_neglect(self, complaints):
        event = complaints.parse_socrata_row(self._row(type=4, status=1, dateClosed=None), city_id="yakima")

        assert (event.complaint_type, event.status) == ("Pothole or Street Surface", "Open")
        assert event.category.value == "NEGLECT"
        assert event.closed_date is None

    def test_a_request_without_a_point_is_not_published(self, complaints):
        # One of the 1,000 requests of the live poll had no geometry.
        assert complaints.parse_socrata_row(self._row(geometry={}), city_id="yakima") is None


class TestYakimaPoll:
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

    def test_a_poll_publishes_requests_and_sends_a_fixed_zone_watermark(self, scheduler):
        producer = scheduler.producers["311"]
        rows = [
            _request(),
            _request(OBJECTID=787990, requestId=9151631, type="Other", status="Open",
                     dateOpened="2026-10-02T01:17:52+00:00", dateClosed=None,
                     latitude=46.6012, longitude=-120.5093),
            # The request with no point.
            _request(OBJECTID=787941, requestId=9151630, type="Pothole or Street Surface",
                     dateOpened="2026-10-01T22:40:15+00:00", latitude=None, longitude=None),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": "Etc/GMT+8"})

        result = scheduler.poll_job("311_yakima")

        assert (result["records_fetched"], result["records_published"]) == (3, 2)
        assert scheduler.dlq_producer.route_to_dlq.call_count == 1
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] is None
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert kwargs["decode_domains"] is True
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == ["yakima:9151632", "yakima:9151631"]
        assert [call.kwargs["payload"].status for call in calls] == ["Closed", "Open"]
        assert scheduler.metrics["311_yakima"].high_watermark == "2026-10-02T05:49:39"

        producer.arcgis.paginate = MagicMock(return_value=[[]])
        scheduler.poll_job("311_yakima")

        # 05:49:39 UTC is 21:49:39 the evening before in the layer's zone.
        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == (
            "dateOpened > timestamp '2026-10-01 21:49:39'"
        )
