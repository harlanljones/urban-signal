"""Cape Coral 311 from the City's 311 issues table (2026-10-02).

The server that serves Cape Coral's permits also serves ``311 Issues
NonSpatial``, the City's own requests since 2020-12-17: one row per request
with WGS84 ``X``/``Y`` columns and no geometry, 6,953 created in the 90 days
to 2026-10-02, loaded in one overnight cut. Some rows repeat a request
exactly. The table's dates are Eastern with daylight saving, and the host
takes ANSI literals. The poll reads only each request's id, type, category,
status, dates and point.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "Issue_id", "Nature_Type", "Category", "Status", "CreateDate", "ResolvedDate", "X", "Y"]

FIELD_MAP = {
    "incident_id": ["Issue_id"],
    "created_date": ["CreateDate"],
    "closed_date": ["ResolvedDate"],
    "complaint_type": ["Nature_Type", "Category"],
    "status": ["Status"],
    "latitude": ["Y"],
    "longitude": ["X"],
}

ORDER = "CreateDate DESC, OBJECTID DESC"


def _spec():
    return get_dataset(CityId.CAPE_CORAL, FeedType.COMPLAINTS_311)


def _request(**changes):
    """A request as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 110827,
        "Issue_id": "PW-90340",
        "Nature_Type": "Pothole Repair Request",
        "Category": "PW-Maintenance Transportation",
        "Status": "Investigating",
        "CreateDate": "2026-10-01T06:09:26+00:00",
        "ResolvedDate": None,
        "X": -81.991355,
        "Y": 26.630032,
        **changes,
    }


def test_cape_coral_reads_the_citys_311_table():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_cape_coral_311_url
    # The permits are layer 1 of the same service.
    assert spec.endpoint.startswith("https://capeims.capecoral.gov/arcgis/rest/services/OpenData/OpenData/")
    assert spec.endpoint.endswith("/MapServer/4")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    assert (spec.watermark_col, spec.order_by) == ("CreateDate", ORDER)
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)
    assert spec.field_map == FIELD_MAP
    # The table has no geometry; its X and Y columns are longitude and latitude.
    assert spec.needs_geocode is False


def test_the_watermark_is_an_eastern_ansi_literal():
    from src.producers.watermarks import watermark_comparison

    # The table declares Eastern time with daylight saving.
    assert watermark_comparison(
        "CreateDate", ">", "2026-10-01T06:09:26", _spec().endpoint, time_zone="America/New_York"
    ) == "CreateDate > timestamp '2026-10-01 02:09:26'"


def test_the_request_names_its_columns_and_leaves_addresses_and_free_text_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The site address and its parts, the title and both descriptions stay
    # on the server.
    assert not {
        "Site_Address", "Title", "Description", "EventDescription", "site_number",
        "NumberSuffix", "site_st_name", "Unit", "predir", "STType", "Postdir", "Suffix",
    } & set(select)
    assert _spec().where is None


def test_a_repeated_request_publishes_once():
    # 435 of the 6,953 rows created in the 90 days to 2026-10-02 repeat a
    # request in every column the poll reads.
    assert (_spec().id_keys, _spec().composite_id) == (["Issue_id"], False)


def test_points_outside_the_metro_are_skipped():
    # Every request of those 90 days lies inside the box; the clip keeps a
    # stray point from publishing.
    assert _spec().metro_clip is True


def test_the_poll_allows_for_an_overnight_load():
    spec = _spec()
    assert spec.batch_limit is None
    assert spec.interval_seconds == 1800.0
    # One cut a night: at 09:05Z on 2026-10-02 the newest request was still
    # the one created at 02:09 EDT the day before.
    assert spec.expected_cadence_days == 2


class TestCapeCoralRequestParsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    @staticmethod
    def _row(**attributes):
        from src.producers.arcgis_client import ArcGISClient

        base = _request()
        # Epoch values as the server converts them from Eastern time.
        base.update(CreateDate=1790834966907, ResolvedDate=None)
        base.update(attributes)
        return ArcGISClient()._flatten_feature(
            {"attributes": base}, date_fields={"CreateDate", "ResolvedDate"}
        )

    def test_a_request_is_published_at_its_xy_point(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="cape_coral")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("cape_coral", "PW-90340")
        assert (event.complaint_type, event.status) == ("Pothole Repair Request", "Investigating")
        assert event.category.value == "NEGLECT"
        assert event.created_date.isoformat() == "2026-10-01T06:09:26.907000+00:00"
        assert event.closed_date is None
        assert event.incident_address is None
        assert (event.latitude, event.longitude) == (26.630032, -81.991355)

    def test_a_resolved_request_carries_its_resolution_date(self, complaints):
        event = complaints.parse_socrata_row(
            self._row(Nature_Type="Waste Pro USA", Category="PW-Solid Waste", Status="Closed",
                      CreateDate=1790786531000, ResolvedDate=1790798882000),
            city_id="cape_coral",
        )

        assert (event.complaint_type, event.status) == ("Waste Pro USA", "Closed")
        assert event.closed_date.isoformat() == "2026-09-30T20:08:02+00:00"

    def test_the_category_stands_in_for_a_missing_type(self, complaints):
        event = complaints.parse_socrata_row(self._row(Nature_Type=None), city_id="cape_coral")

        assert event.complaint_type == "PW-Maintenance Transportation"


class TestCapeCoralPoll:
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

    def test_a_poll_publishes_each_request_once_and_sends_an_eastern_watermark(self, scheduler):
        producer = scheduler.producers["311"]
        rows = [
            _request(),
            # The same request again, as the table repeats it.
            _request(OBJECTID=110826),
            _request(OBJECTID=110790, Issue_id="CC-90202", Nature_Type="Misc/Code Compliance Questions",
                     Category="DS-Code Compliance", Status="Closed", CreateDate="2026-09-30T20:41:07+00:00",
                     ResolvedDate="2026-09-30T21:02:44+00:00", X=-81.942387, Y=26.647397),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": "America/New_York"})

        result = scheduler.poll_job("311_cape_coral")

        assert (result["records_fetched"], result["records_published"], result["duplicates_skipped"]) == (3, 2, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] is None
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == ["cape_coral:PW-90340", "cape_coral:CC-90202"]
        assert scheduler.metrics["311_cape_coral"].high_watermark == "2026-10-01T06:09:26"

        producer.arcgis.paginate = MagicMock(return_value=[[]])
        scheduler.poll_job("311_cape_coral")

        # 06:09:26 UTC is 02:09:26 in Cape Coral in October.
        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == (
            "CreateDate > timestamp '2026-10-01 02:09:26'"
        )
