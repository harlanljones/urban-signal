"""Texarkana permits from the City's MyGov workbook (2026-10-02).

MyGov rebuilds the Texas city's "Permits Issued in the last month" workbook
each morning: the permits started in the previous calendar month (289 for
September on 2026-10-02), each with its permit number, title, project
address, status, and start and issue dates written as ``MM/DD/YYYY`` text,
and no coordinates. The spec reads the building permits, leaving out health
inspections, occupancy certificates, zoning, platting, street cuts and the
City's other non-building permits, and geocodes each project address in
Texarkana, TX. A permit is published once, when it is first read, so most
reach the stream when their month's workbook appears early the next month.
"""

import io
import zipfile
from unittest.mock import MagicMock, patch
from xml.sax.saxutils import escape

import httpx
import pytest

from src.producers.excel_client import ExcelClient
from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset
from src.spatial.geocoder import GeoPoint

JOB = "permits_texarkana"

COLUMNS = [
    "permit_number", "permit_title", "status_permit", "date_started", "permit_issued_date", "project_valuation",
    "project_address",
]

FIELD_MAP = {
    "job_id": ["permit_number"],
    "issuance_date": ["permit_issued_date"],
    "filing_date": ["date_started"],
    "job_type": ["permit_title"],
    "status": ["status_permit"],
    "cost": ["project_valuation"],
    "address_street": ["project_address"],
}

# The titles Texarkana used in the year to 2026-10-02 that are not permits
# to build: inspections, mobile vendors, occupancy, zoning, platting, plan
# reviews, street cuts, events, banners and tents, and notices.
NOT_BUILDING = [
    "Health Inspection", "Environmental Sanitation Inspection", "Pool Inspection", "Pool Permit and Inspection",
    "Mobile Unit", "Mobile Unit 3 Days or less", "Occupancy", "Occupancy - Re-Issue", "Certificate of Occupancy",
    "Zoning", "Zoning Verification Letter", "Specific Use Permit - Zoning", "Request Zoning Change", "Variances",
    "Platting - Replat", "Platting - Amendment", "Platting - Minor", "Platting -Preliminary and Final",
    "Platting - Reapproval", "Civil Plan Review Only", "Non-Residential Plan Re-Review",
    "Floodplain Development Application", "Street Cut", "Right of Way Permit", "Special Event Permit",
    "Banner - 90 days", "Banner - Monthly", "Tent - Temporary", "Seasonal Permit - NO Certificate Required",
    "Courtesy Inspection", "Stop Work Notice",
]

ENDPOINT = "https://public.mygov.us/tx_texarkana/downloadReport?moduleName=pi&id=370"
HEADERS = (
    "Permit Title", "Permit Description", "Project Address", "Status (Permit)", "Collaborators", "Date Started",
    "Permit Issued Date", "CO Issued Date", "Project Valuation", "Project Square Feet", "Permit Number",
)
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _spec():
    return get_dataset(CityId.TEXARKANA, FeedType.PERMITS)


def _permit(number, title, started, issued="", status="Permit Issued", valuation="0", address="100 Example St."):
    """One workbook row in the report's column order (synthetic values)."""
    return (title, "Synthetic description", address, status, "Example Contractor LLC", started, issued, "", valuation,
            "0", number)


def _workbook(permits) -> bytes:
    """The report as an .xlsx whose cells are all text, as MyGov writes them."""

    def row(n, values):
        cells = "".join(
            f'<c r="{chr(65 + i)}{n}" t="inlineStr"><is><t>{escape(value)}</t></is></c>' for i, value in enumerate(values) if value
        )
        return f'<row r="{n}">{cells}</row>'

    sheet = row(1, HEADERS) + "".join(row(n, permit) for n, permit in enumerate(permits, start=2))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{MAIN}" xmlns:r="{REL}"><sheets><sheet name="R" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{REL}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        archive.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{MAIN}"><sheetData>{sheet}</sheetData></worksheet>')
    return buf.getvalue()


SEPTEMBER = [
    _permit("26-990001", "Residential - New Construction", "09/30/2026", "10/01/2026", valuation="185000",
            address="100 Example St."),
    _permit("26-990002", "Residential - Re-Roofing or Repair", "09/30/2026", status="In Review",
            address="200 Sample Ave."),
    _permit("26-990003", "Electrical Permit (New construction & remodels for commercial and residential)",
            "09/02/2026", "09/03/2026", address="300 Placeholder Dr."),
    _permit("26-990004", "Health Inspection", "09/15/2026", "09/15/2026", address="400 Example St."),
    _permit("26-990005", "Certificate of Occupancy", "09/29/2026", "09/30/2026", address="500 Sample Ave."),
    _permit("26-990006", "Platting -Preliminary and Final", "09/10/2026", address="600 Placeholder Dr."),
    _permit("26-990007", "Street Cut", "09/30/2026", "09/30/2026", address="700 Example St."),
]


class _Geocoder:
    """Places every query near Texarkana's City Hall and records it."""

    def __init__(self):
        self.queries: list[str] = []

    def geocode(self, query):
        self.queries.append(query)
        return GeoPoint(33.4251 + len(self.queries) / 10000, -94.0477, 1.0, "census:tiger")


@pytest.fixture
def geocoder():
    stub = _Geocoder()
    with patch("src.spatial.geocoder.get_geocoder", return_value=stub):
        yield stub


@pytest.fixture
def scheduler():
    with patch("src.producers.base_producer.BaseKafkaProducer"):
        sched = MunicipalIngestionScheduler(dlq_producer=MagicMock(), rate_limit_delay_seconds=0.0, dedup_capacity=1000)
    for producer in sched.producers.values():
        producer.producer = MagicMock()
    sched.state_file = None
    return sched


def _serve(scheduler, workbooks):
    """Point the permits producer's Excel client at a server answering each
    request with the next workbook, and record each paginate call."""
    files = iter(workbooks)
    requests: list[httpx.Request] = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, content=next(files))

    client = ExcelClient(httpx.Client(transport=httpx.MockTransport(handler)))
    client.paginate = MagicMock(side_effect=client.paginate)
    scheduler.producers["permits"].excel = client
    return client, requests


def test_texarkana_reads_the_citys_mygov_workbook():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.excel_texarkana_permits_url == ENDPOINT
    assert (spec.platform, spec.ingestion_mode) == ("excel", "incremental")
    assert spec.field_map == FIELD_MAP
    assert spec.id_keys == ["permit_number"]
    # Every one of the 289 permits on 2026-10-02 had its own number.
    assert spec.composite_id is False


def test_the_dates_are_text_and_compared_as_dates():
    spec = _spec()
    assert (spec.watermark_col, spec.watermark_type, spec.watermark_format) == ("date_started", "text", "%m/%d/%Y")
    assert spec.order_by == "date_started DESC"


def test_the_request_keeps_its_columns():
    # The description is free text and the collaborators are people and
    # firms: neither leaves the client.
    assert _spec().select.split(",") == COLUMNS


def test_the_filter_leaves_out_permits_that_are_not_for_building():
    spec = _spec()
    assert spec.where == "permit_title NOT IN (" + ", ".join(f"'{title}'" for title in NOT_BUILDING) + ")"

    client = ExcelClient(httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=_workbook(SEPTEMBER)))))
    rows = [row for batch in client.paginate(ENDPOINT, where_clause=f"({spec.where})", select=spec.select) for row in batch]

    assert [row["permit_number"] for row in rows] == ["26-990001", "26-990002", "26-990003"]
    assert set(rows[0]) == set(COLUMNS)


def test_each_address_is_geocoded_in_texarkana():
    spec = _spec()
    assert (spec.needs_geocode, spec.geocode_context) == (True, "Texarkana, TX")
    # Rows are placed when parsed, so the metro clip, which drops unplaced
    # rows, stays off.
    assert spec.metro_clip is False


def test_the_cadence_allows_a_month_between_workbooks():
    spec = _spec()
    # The newest start date is a month old on the last day before the next
    # month's workbook replaces it.
    assert (spec.interval_seconds, spec.expected_cadence_days) == (21600.0, 35)
    # A month's workbook held 289 permits; the default cap of 1,000 holds it.
    assert spec.batch_limit is None


class TestTexarkanaPermitParsing:
    def _row(self, permit):
        return dict(zip(COLUMNS, (permit[10], permit[0], permit[3], permit[5], permit[6], permit[8], permit[2])))

    def test_a_new_house_is_new_construction_at_its_geocoded_address(self, scheduler, geocoder):
        event = scheduler.producers["permits"].parse_socrata_row(self._row(SEPTEMBER[0]), city_id="texarkana")

        assert event is not None
        assert (event.city_id, event.job_id, event.status) == ("texarkana", "26-990001", "Permit Issued")
        assert (event.job_type.value, event.normalized_permit_type) == ("NB", "NEW_CONSTRUCTION")
        assert event.filing_date.date().isoformat() == "2026-09-30"
        assert event.issuance_date.date().isoformat() == "2026-10-01"
        assert event.estimated_cost == 185000.0
        assert geocoder.queries == ["100 Example St., Texarkana, TX"]
        assert event.latitude == pytest.approx(33.4252)

    def test_a_trade_permit_for_new_construction_is_a_trade_permit(self, scheduler, geocoder):
        # 56 of the 201 permits on 2026-10-02 were plumbing, electrical and
        # HVAC permits whose titles name the new construction they serve.
        event = scheduler.producers["permits"].parse_socrata_row(self._row(SEPTEMBER[2]), city_id="texarkana")

        assert event is not None
        assert (event.job_type.value, event.normalized_permit_type) == ("A2", "MECHANICAL_ELECTRICAL_PLUMBING")

    def test_a_permit_in_review_has_no_issue_date(self, scheduler, geocoder):
        event = scheduler.producers["permits"].parse_socrata_row(self._row(SEPTEMBER[1]), city_id="texarkana")

        assert event is not None
        assert event.status == "In Review"
        assert event.issuance_date is None
        assert event.filing_date.date().isoformat() == "2026-09-30"

    def test_an_address_the_geocoder_cannot_place_is_not_published(self, scheduler):
        miss = MagicMock()
        miss.geocode.return_value = None
        with patch("src.spatial.geocoder.get_geocoder", return_value=miss):
            assert scheduler.producers["permits"].parse_socrata_row(self._row(SEPTEMBER[2]), city_id="texarkana") is None


class TestTexarkanaPoll:
    def test_a_month_publishes_once_and_the_next_months_workbook_follows(self, scheduler, geocoder):
        october = [
            _permit("26-991001", "Solar Panels", "10/01/2026", "10/02/2026", address="800 Example St."),
            _permit("26-991002", "Health Inspection", "10/05/2026", "10/05/2026", address="900 Sample Ave."),
        ]
        client, requests = _serve(scheduler, [_workbook(SEPTEMBER), _workbook(SEPTEMBER), _workbook(october)])

        result = scheduler.poll_job(JOB)

        assert (result["records_fetched"], result["records_published"]) == (3, 3)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        produced = scheduler.producers["permits"].producer.produce.call_args_list
        # Newest start first, compared as dates.
        assert [call.kwargs["payload"].job_id for call in produced] == ["26-990001", "26-990002", "26-990003"]
        assert all(query.endswith(", Texarkana, TX") for query in geocoder.queries)
        assert scheduler.metrics[JOB].high_watermark == "09/30/2026"
        kwargs = client.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({_spec().where})"
        assert (kwargs["watermark_col"], kwargs["watermark_format"]) == ("date_started", "%m/%d/%Y")

        # The day is whole, so the next poll reads it again; the dedup drops
        # what was published.
        result = scheduler.poll_job(JOB)

        assert client.paginate.call_args.kwargs["where_clause"] == f"({_spec().where}) AND date_started >= '09/30/2026'"
        assert (result["records_fetched"], result["records_published"], result["duplicates_skipped"]) == (2, 0, 2)

        # October's workbook replaces September's on the 1st.
        result = scheduler.poll_job(JOB)

        assert (result["records_fetched"], result["records_published"]) == (1, 1)
        assert produced[-1].kwargs["payload"].job_id == "26-991001"
        assert scheduler.metrics[JOB].high_watermark == "10/01/2026"
        assert len(requests) == 3
