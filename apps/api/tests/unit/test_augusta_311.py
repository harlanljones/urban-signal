"""Augusta 311 from the City's open Cityworks requests (2026-10-02).

Cityworks publishes the City's open service requests as an ArcGIS layer
(``augcw.augustaga.gov``, "All Open SRs" since 2016): one point per request,
12,471 open on 2026-10-02, 2,855 of them created in the 90 days before. A
request leaves the layer when it closes. More than a quarter are
utility-locate tickets from excavators, which the poll leaves out with the
subpoena queue and the crews' daily start entries.

The server ignores ``resultOffset``, takes the first ``resultRecordCount``
rows in the requested order before it applies the ``where``, and flags every
short page as truncated, so a poll is one request. It reads a zone-less date
literal as Eastern time, and its layer declares no zone, so the client lends
the layer the host's zone.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["REQUESTID", "ProblemCode", "Status", "DateTimeInit", "DateTimeClosed", "ProbDistrict"]

FIELD_MAP = {
    "incident_id": ["REQUESTID"],
    "created_date": ["DateTimeInit"],
    "closed_date": ["DateTimeClosed"],
    "complaint_type": ["ProblemCode"],
    "status": ["Status"],
    "borough": ["ProbDistrict"],
}

ORDER = "DateTimeInit DESC, REQUESTID DESC"

EXCLUSIONS = (
    "ProblemCode NOT LIKE 'LOCATE UTILITIES%' AND ProblemCode <> 'Subpoenas'"
    " AND ProblemCode NOT LIKE 'C&M%'"
)

# The layer as Augusta's server describes it: no time reference, no paging.
LAYER = {
    "fields": [
        {"name": "REQUESTID", "type": "esriFieldTypeOID"},
        {"name": "ProblemCode", "type": "esriFieldTypeString"},
        {"name": "Status", "type": "esriFieldTypeString"},
        {"name": "DateTimeInit", "type": "esriFieldTypeDate"},
        {"name": "DateTimeClosed", "type": "esriFieldTypeDate"},
        {"name": "ProbDistrict", "type": "esriFieldTypeString"},
    ],
    "objectIdField": "REQUESTID",
    "maxRecordCount": 30000,
    "advancedQueryCapabilities": {"supportsPagination": False},
}


def _spec():
    return get_dataset(CityId.AUGUSTA, FeedType.COMPLAINTS_311)


def _feature(**changes):
    """A request as the server sends it (synthetic values; epoch milliseconds)."""
    attributes = {
        "REQUESTID": 900003,
        "ProblemCode": "Pothole",
        "Status": "INITIATE",
        "DateTimeInit": 1790930282817,  # 2026-10-02T08:38:02.817Z
        "DateTimeClosed": None,
        "ProbDistrict": "C-Dist 1",
    }
    point = {"x": -81.97, "y": 33.475}
    point.update({key: changes.pop(key) for key in ("x", "y") if key in changes})
    attributes.update(changes)
    return {"attributes": attributes, "geometry": point}


def test_augusta_reads_the_open_cityworks_requests():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_augusta_311_url
    assert spec.endpoint == (
        "https://augcw.augustaga.gov/CityworksForms/gis/2/5799/rest/services/cw/FeatureServer/1"
    )
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    assert (spec.watermark_col, spec.order_by) == ("DateTimeInit", ORDER)
    assert (spec.oid_field, spec.max_record_count) == ("REQUESTID", 30000)
    assert (spec.id_keys, spec.composite_id) == (["REQUESTID"], False)
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_the_request_names_its_columns_and_leaves_people_and_addresses_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The free text, the staff who opened, closed or cancelled a request, and
    # the problem address stay on the server.
    assert not {
        "Details", "Comments", "Resolution", "InitiatedBy", "ClosedBy", "CancelledBy",
        "ProbAddress", "ProbAddrSt", "ProbCity", "ProbZip", "StreetName",
    } & set(select)


def test_the_poll_leaves_out_locate_tickets_subpoenas_and_crew_logs():
    # 811 utility-locate tickets were 29% of the 90 days to 2026-10-02.
    assert _spec().where == EXCLUSIONS


def test_points_outside_the_metro_are_skipped():
    # 2 of the newest 630 requests lay outside the box, one of them more than
    # 300 km south of it.
    assert _spec().metro_clip is True


def test_one_request_every_half_hour_and_a_daily_cadence():
    spec = _spec()
    # A poll reads at most the newest 1,000 rows of every kind: 23 days of
    # requests on 2026-10-02.
    assert spec.batch_limit is None
    assert spec.interval_seconds == 1800.0
    # The quietest day of the week to 2026-10-02, a Sunday, left three
    # requests still open.
    assert spec.expected_cadence_days == 1


class TestAugustaRequestParsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    @staticmethod
    def _row(**changes):
        from src.producers.arcgis_client import ArcGISClient

        return ArcGISClient()._flatten_feature(
            _feature(**changes), date_fields={"DateTimeInit", "DateTimeClosed"}
        )

    def test_a_request_is_published_at_its_point(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="augusta")

        assert event is not None
        assert (event.city_id, event.incident_id) == ("augusta", "900003")
        assert (event.complaint_type, event.status) == ("Pothole", "INITIATE")
        assert event.created_date.isoformat() == "2026-10-02T08:38:02.817000+00:00"
        assert event.closed_date is None
        assert event.incident_address is None
        assert (event.latitude, event.longitude) == (33.475, -81.97)


class TestAugustaPoll:
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

    def test_each_poll_is_one_request_with_an_eastern_watermark(self, scheduler):
        """Through the real client: the host lends the layer Eastern time, and
        a server that cannot page is asked once per poll."""
        client = scheduler.producers["311"].arcgis
        queries = []
        pages = [
            [
                _feature(),
                _feature(REQUESTID=900002, ProblemCode="WATER LEAK", Status="ASSIGNED",
                         DateTimeInit=1790918099000, ProbDistrict="C-Dist 7", x=-82.01, y=33.49),
                # A request placed far south of the metro.
                _feature(REQUESTID=900001, ProblemCode="Mosquito", DateTimeInit=1790892941000,
                         x=-81.87, y=29.98),
            ],
            # The next poll meets the newest request again: the watermark
            # keeps whole seconds and the server keeps milliseconds.
            [_feature()],
        ]

        def answer(url, params):
            if not url.endswith("/query"):
                return LAYER
            queries.append(params)
            # Every short page comes back flagged as truncated.
            return {"features": pages[len(queries) - 1], "exceededTransferLimit": True}

        client._request_json = answer

        result = scheduler.poll_job("311_augusta")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 2, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        assert len(queries) == 1
        assert queries[0]["where"] == f"({EXCLUSIONS})"
        assert (queries[0]["orderByFields"], queries[0]["outFields"]) == (ORDER, ",".join(COLUMNS))
        assert (queries[0]["resultOffset"], queries[0]["resultRecordCount"]) == (0, 1000)
        calls = scheduler.producers["311"].producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == ["augusta:900003", "augusta:900002"]
        assert scheduler.metrics["311_augusta"].high_watermark == "2026-10-02T08:38:02"

        result = scheduler.poll_job("311_augusta")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 1)
        assert len(queries) == 2
        # 08:38:02 UTC is 04:38:02 in Augusta in October. Read as UTC, a
        # zone-less 08:38:02 would have started the filter four hours late.
        assert queries[1]["where"] == f"({EXCLUSIONS}) AND DateTimeInit > '2026-10-02T04:38:02'"
