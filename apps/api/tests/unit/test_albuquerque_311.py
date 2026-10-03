"""Albuquerque 311 from the City's ABQ311 CRM layer (2026-10-02).

The City GIS server publishes its CRM requests joined to assessor parcels,
one point per request and parcel: 288,000 rows in the year to 2026-10-02,
about 790 a day. Unbounded queries on the layer time out, so the poll reads
at most the last day, and a request joined to several parcels repeats with
the same id, so the poll publishes it once. It reads only each request's id,
type, status, ZIP code and dates.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["CRM_ID", "STATUSID", "CREATEDTIME", "CLOSEDTIME", "QUICK_CODE", "ZIP_CODE"]

FIELD_MAP = {
    "incident_id": ["CRM_ID"],
    "created_date": ["CREATEDTIME"],
    "closed_date": ["CLOSEDTIME"],
    "complaint_type": ["QUICK_CODE"],
    "status": ["STATUSID"],
    "zipcode": ["ZIP_CODE"],
}

FLOOR = "CREATEDTIME >= CURRENT_TIMESTAMP - INTERVAL '1' DAY"

ORDER = "CREATEDTIME DESC, CRM_ID DESC"


def _spec():
    return get_dataset(CityId.ALBUQUERQUE, FeedType.COMPLAINTS_311)


def _request(**changes):
    """A request as the ArcGIS client hands it on (synthetic values)."""
    return {
        "CRM_ID": 7700001,
        "STATUSID": "Closed",
        "CREATEDTIME": "2026-10-02T05:54:22+00:00",
        "CLOSEDTIME": "2026-10-02T06:41:09+00:00",
        "QUICK_CODE": "Solid Waste - Missed Trash Pickup",
        "ZIP_CODE": "87106",
        "latitude": 35.0781,
        "longitude": -106.6189,
        **changes,
    }


def test_albuquerque_reads_the_citys_crm_layer():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_albuquerque_311_url
    assert spec.endpoint.startswith("https://coageo.cabq.gov/cabqgeo/rest/services/")
    assert spec.endpoint.endswith("/CRM_Service_Requests_MIL1/MapServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    # Request ids follow the creation times without exception among the 1,814
    # requests filed in the day to 2026-10-02 06:13Z, so none arrives late.
    assert spec.watermark_col == "CREATEDTIME"
    assert spec.order_by == ORDER
    assert (spec.oid_field, spec.max_record_count) == ("CRM_ID", 2000)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_the_poll_reads_a_day_back_at_most():
    # Unbounded queries did not answer within 60 seconds; one bounded to the
    # last day answers in two to four. The server's clock is local, so the
    # day is about 30 hours. A row the server cannot read empties every window
    # that holds it (one in the year to 2026-10-02), and the floor lets the
    # poll move on a day later.
    assert _spec().where == FLOOR


def test_the_request_names_its_columns_and_leaves_free_text_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The address, subject, description, notes, staff accounts and named
    # officials stay on the server.
    assert not {
        "ADDRESS", "ADDRESS_LINE2", "SUBJECT", "DESCRIPTION", "ADDITIONAL_NOTES",
        "ASSIGNEDTOACCOUNT", "CREATEDBYACCOUNT", "COUNCILOR_NAME", "ZONING_INSPECTOR",
    } & set(select)


def test_each_request_publishes_once():
    # A request joined to several parcels repeats with the same CRM_ID: 73 of
    # the 1,897 rows of the live poll on 2026-10-02 were repeats.
    assert (_spec().id_keys, _spec().composite_id) == (["CRM_ID"], False)


def test_requests_outside_the_metro_box_are_kept():
    # One of the 1,824 requests of the live poll lay outside the box; every
    # row on the layer is a City request.
    assert _spec().metro_clip is False


def test_the_poll_keeps_up_with_about_eight_hundred_rows_a_day():
    spec = _spec()
    # The day-long window held 1,897 rows on 2026-10-02, so a first poll
    # reads all of it.
    assert spec.batch_limit == 3000
    assert spec.interval_seconds == 900.0
    assert spec.expected_cadence_days == 1


class TestAlbuquerqueRequestParsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_a_closed_request_is_published_at_its_point(self, complaints):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _request().items() if key not in ("latitude", "longitude")}
        attributes["CREATEDTIME"] = 1790920462000  # 2026-10-02 05:54:22 UTC
        attributes["CLOSEDTIME"] = 1790923269000  # 2026-10-02 06:41:09 UTC
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -106.6189, "y": 35.0781}},
            date_fields={"CREATEDTIME", "CLOSEDTIME"},
        )

        event = complaints.parse_socrata_row(row, city_id="albuquerque")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("albuquerque", "7700001")
        assert (event.complaint_type, event.status) == ("Solid Waste - Missed Trash Pickup", "Closed")
        assert event.created_date.isoformat() == "2026-10-02T05:54:22+00:00"
        assert event.closed_date.isoformat() == "2026-10-02T06:41:09+00:00"
        assert event.zipcode == "87106"
        assert event.incident_address is None
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (35.0781, -106.6189)


class TestAlbuquerquePoll:
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

    def test_a_poll_publishes_each_request_once_and_keeps_its_floor(self, scheduler):
        producer = scheduler.producers["311"]
        rows = [
            _request(),
            # The same request joined to a second parcel.
            _request(latitude=35.0779, longitude=-106.6192),
            _request(CRM_ID=7700000, STATUSID="Open_New", QUICK_CODE="Solid Waste - Large Item Pick Up",
                     CREATEDTIME="2026-10-02T05:17:47+00:00", CLOSEDTIME=None, ZIP_CODE="87112"),
            # East of the metro box: still a City request.
            _request(CRM_ID=7699998, STATUSID="Pending", QUICK_CODE="Animal Welfare Field Dispatch",
                     CREATEDTIME="2026-10-02T04:02:10+00:00", CLOSEDTIME=None, latitude=35.152,
                     longitude=-106.4650),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": None})

        result = scheduler.poll_job("311_albuquerque")

        assert (result["records_fetched"], result["records_published"]) == (4, 3)
        assert result["duplicates_skipped"] == 1
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({FLOOR})"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert kwargs["max_records"] == 3000
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == [
            "albuquerque:7700001", "albuquerque:7700000", "albuquerque:7699998",
        ]
        assert [call.kwargs["payload"].zipcode for call in calls] == ["87106", "87112", "87106"]
        assert scheduler.metrics["311_albuquerque"].high_watermark == "2026-10-02T05:54:22"

        producer.arcgis.paginate = MagicMock(return_value=[[]])
        scheduler.poll_job("311_albuquerque")

        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == (
            f"({FLOOR}) AND CREATEDTIME > '2026-10-02T05:54:22'"
        )
