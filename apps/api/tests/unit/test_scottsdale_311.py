"""Scottsdale 311 from the city's ScottsdaleEZ table (2026-09-30).

``OpenData_Tabular/MapServer/28`` lists the city's customer service requests
once each one closes (240,985 rows since 2019), at the hundred block and on
the street centreline. A request appears only when it closes, so the feed
follows ``ClosedDate``: a filter on the filing date would pass over a request
filed before the watermark that closes after it. About one row in twenty has
no location (its address reads "Data Not Available", mostly staff equipment
requests), and ``metro_clip`` skips those before they reach the parser.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = [
    "Requests", "Workgroup", "RequestType", "RequestStatus", "Address",
    "Latitude", "Longitude", "CreatedDate", "ClosedDate",
]

FIELD_MAP = {
    "incident_id": ["Requests"],
    "created_date": ["CreatedDate"],
    "closed_date": ["ClosedDate"],
    "complaint_type": ["RequestType", "Workgroup"],
    "status": ["RequestStatus"],
    "incident_address": ["Address"],
    "latitude": ["Latitude"],
    "longitude": ["Longitude"],
}


def _spec():
    return get_dataset(CityId.SCOTTSDALE, FeedType.COMPLAINTS_311)


def _request(**changes):
    """A closed request as the ArcGIS client hands it on."""
    return {
        "Requests": 999001,
        "Workgroup": "Solid Waste",
        "RequestType": "Container Repair-Residential",
        "RequestStatus": "Closed",
        "Address": "7200 E STARLA DR",
        "Latitude": 33.4942,
        "Longitude": -111.9261,
        "CreatedDate": "2026-09-25T08:14:00+00:00",
        "ClosedDate": "2026-09-26T22:56:27+00:00",
        **changes,
    }


def test_scottsdale_reads_the_citys_closed_service_requests():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.scottsdale_311_endpoint
    assert spec.endpoint.endswith("/OpenData_Tabular/MapServer/28")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    # A request is published when it closes, so its close date is the one
    # every new row passes.
    assert spec.watermark_col == "ClosedDate"
    assert spec.order_by == "ClosedDate DESC, Requests DESC"
    assert (spec.id_keys, spec.oid_field) == (["Requests"], "Requests")
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_the_request_names_its_columns_and_sends_no_filter_of_its_own():
    spec = _spec()
    assert spec.select.split(",") == COLUMNS
    # The poll's only filter is the watermark comparison, the shape the
    # host's permits feed already sends; rows without a location are left to
    # the clip.
    assert spec.where is None
    assert spec.metro_clip is True


def test_a_weekly_refresh_fits_one_poll():
    spec = _spec()
    # About 1,100 requests close in a week (1,088 from 2026-09-20 to the
    # newest, late on 2026-09-26): the cap holds two missed refreshes.
    assert spec.batch_limit == 3000
    # The table is refreshed about once a week. Four polls a day read it
    # soon after, and a poll that reads three pages runs at most every half
    # hour.
    assert spec.interval_seconds == 21600.0
    assert spec.expected_cadence_days == 7


class TestScottsdaleRequestParsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_a_closed_request_is_published_at_its_hundred_block(self, complaints):
        event = complaints.parse_socrata_row(_request(), city_id="scottsdale")
        assert event is not None
        assert (event.city_id, event.incident_id) == ("scottsdale", "999001")
        assert event.complaint_type == "Container Repair-Residential"
        assert (event.status, event.incident_address) == ("Closed", "7200 E STARLA DR")
        assert event.created_date.isoformat() == "2026-09-25T08:14:00+00:00"
        assert event.closed_date.isoformat() == "2026-09-26T22:56:27+00:00"
        assert (event.latitude, event.longitude) == (33.4942, -111.9261)
        assert event.h3_res9 is not None

    def test_a_request_without_a_type_takes_its_workgroup(self, complaints):
        event = complaints.parse_socrata_row(_request(RequestType=None), city_id="scottsdale")
        assert event is not None
        assert event.complaint_type == "Solid Waste"


class TestScottsdalePoll:
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

    def test_a_poll_skips_requests_without_a_location_and_follows_the_close_date(self, scheduler):
        producer = scheduler.producers["311"]
        rows = [
            _request(),
            _request(Requests=999002, Workgroup="Police Department",
                     RequestType="Uniform & Equipment Replacement",
                     Address="Data Not Available", Latitude=None, Longitude=None,
                     ClosedDate="2026-09-26T21:07:07+00:00"),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": None})

        result = scheduler.poll_job("311_scottsdale")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (2, 1, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] is None
        assert (kwargs["max_records"], kwargs["order_by"]) == (3000, "ClosedDate DESC, Requests DESC")
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [event.incident_id for event in events] == ["999001"]
        assert scheduler.metrics["311_scottsdale"].high_watermark == "2026-09-26T22:56:27"

        producer.arcgis.paginate = MagicMock(return_value=[[]])
        scheduler.poll_job("311_scottsdale")

        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == "ClosedDate > '2026-09-26T22:56:27'"
