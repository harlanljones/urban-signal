"""Long Beach 311 from the City's Go Long Beach requests (2026-10-02).

The City's OpenDataSoft portal publishes every Go Long Beach request since
September 2020 (353,242 on 2026-10-02), each with its case number, type,
status, dates, ZIP code and point, and no requester or description fields.
Its CSV export takes the columns, a filter and the delimiter as parameters,
so the poll downloads the requests created in the last seven days (1,314 on
2026-10-02) and keeps the ones newer than its watermark. The export writes
each point as one ``lat, lon`` column, which the CSV client splits.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.producers.csv_client import CSVClient
from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["casenumber", "type", "status", "createddate", "closeddate", "zipcode_c", "geolocation"]

FIELD_MAP = {
    "incident_id": ["casenumber"],
    "created_date": ["createddate"],
    "closed_date": ["closeddate"],
    "complaint_type": ["type"],
    "status": ["status"],
    "zipcode": ["zipcode_c"],
}

HEADER = ",".join(COLUMNS)

# Synthetic requests in the export's form: two in the city and one placed in
# the harbour south of the metro box.
REQUESTS = [
    '00399001,Graffiti,In Progress,2026-10-02T13:31:45+00:00,,90802,"33.7703059453627, -118.1865287460327"',
    '00399002,Dumped Items,Closed,2026-10-02T09:12:30+00:00,2026-10-02T11:40:02+00:00,90813,"33.7896, -118.189"',
    '00399003,E-Scooter,New,2026-10-01T22:05:10+00:00,,90802,"33.7105, -118.1528"',
]


def _spec():
    return get_dataset(CityId.LONG_BEACH, FeedType.COMPLAINTS_311)


def _export(*lines: str) -> str:
    return "\r\n".join([HEADER, *lines]) + "\r\n"


def test_long_beach_reads_the_citys_request_export():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.csv_long_beach_311_endpoint
    assert spec.endpoint.startswith(
        "https://data.longbeach.gov/api/explore/v2.1/catalog/datasets/service-requests/exports/csv?"
    )
    assert (spec.platform, spec.ingestion_mode) == ("csv", "incremental")
    assert (spec.zip_member, spec.delimiter, spec.columns) == (None, None, [])
    assert spec.field_map == FIELD_MAP
    # Each point is in the file; nothing is geocoded.
    assert (spec.point_col, spec.needs_geocode) == ("geolocation", False)


def test_the_export_names_its_columns_its_week_and_its_comma():
    params = httpx.URL(_spec().endpoint).params
    assert params["select"] == ",".join(COLUMNS)
    assert params["where"] == "createddate >= now(days=-7)"
    # The export's default delimiter is a semicolon and its default header
    # the field labels.
    assert (params["delimiter"], params["use_labels"]) == (",", "false")
    assert _spec().select.split(",") == COLUMNS


def test_each_request_publishes_once_newest_first():
    spec = _spec()
    # Every one of the 19,090 requests created in the 90 days to 2026-10-02
    # had its own case number.
    assert (spec.id_keys, spec.composite_id) == (["casenumber"], False)
    assert (spec.watermark_col, spec.order_by) == ("createddate", "createddate DESC")


def test_the_cap_holds_the_exports_week_and_the_cadence_is_two_days():
    spec = _spec()
    # 1,314 requests in the week to 2026-10-02: a first poll, or one after a
    # missed week, reads them all.
    assert spec.batch_limit == 2000
    # The export was rebuilt at 14:00 UTC on 2026-10-02 and not again by 17:10.
    assert (spec.interval_seconds, spec.expected_cadence_days) == (3600.0, 2)
    # 2 of the 19,090 requests in the 90 days lay outside the metro box.
    assert spec.metro_clip is True


class TestLongBeachRequestParsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    @staticmethod
    def _read(*lines: str) -> list[dict]:
        spec = _spec()
        client = CSVClient(httpx.Client(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=_export(*lines), request=request)
        )))
        return [
            row
            for batch in client.paginate(
                spec.endpoint, order_by=spec.order_by, select=spec.select, point_col=spec.point_col
            )
            for row in batch
        ]

    def test_an_open_request_is_published_at_its_point(self, complaints):
        (row,) = self._read(REQUESTS[0])

        event = complaints.parse_socrata_row(row, city_id="long_beach")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("long_beach", "00399001")
        assert (event.complaint_type, event.status, event.zipcode) == ("Graffiti", "In Progress", "90802")
        assert event.created_date.isoformat() == "2026-10-02T13:31:45+00:00"
        assert event.closed_date is None
        assert (event.latitude, event.longitude) == (33.7703059453627, -118.1865287460327)
        assert event.h3_res9 is not None

    def test_a_closed_request_carries_its_closing_time(self, complaints):
        (row,) = self._read(REQUESTS[1])

        event = complaints.parse_socrata_row(row, city_id="long_beach")

        assert event is not None
        assert (event.complaint_type, event.status) == ("Dumped Items", "Closed")
        assert event.closed_date.isoformat() == "2026-10-02T11:40:02+00:00"


class TestLongBeachPoll:
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

    def test_a_poll_publishes_the_week_inside_the_box_and_rereads_its_newest_once(self, scheduler):
        producer = scheduler.producers["311"]
        requested: list[httpx.URL] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requested.append(request.url)
            return httpx.Response(200, text=_export(*REQUESTS), request=request)

        producer.csv.http = httpx.Client(transport=httpx.MockTransport(handler))
        producer.csv.paginate = MagicMock(wraps=producer.csv.paginate)

        result = scheduler.poll_job("311_long_beach")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 2, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        assert [url.params["where"] for url in requested] == ["createddate >= now(days=-7)"]
        kwargs = producer.csv.paginate.call_args.kwargs
        assert (kwargs["point_col"], kwargs["max_records"]) == ("geolocation", 2000)
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [(event.incident_id, event.latitude, event.longitude) for event in events] == [
            ("00399001", 33.7703059453627, -118.1865287460327), ("00399002", 33.7896, -118.189),
        ]
        assert scheduler.metrics["311_long_beach"].high_watermark == "2026-10-02T13:31:45"

        # The watermark drops the offset, so the newest request reads as
        # newer than it, comes back once more and is not published again.
        result = scheduler.poll_job("311_long_beach")

        assert producer.csv.paginate.call_args.kwargs["where_clause"] == "createddate > '2026-10-02T13:31:45'"
        assert (result["records_fetched"], result["records_published"], result["duplicates_skipped"]) == (1, 0, 1)
