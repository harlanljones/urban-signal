"""Abilene permits from the City's monthly MyGov workbook (2026-10-02).

MyGov builds Abilene's "TCADBuildingPermitsWithProjInfo" workbook once a
month, around the 28th: the building permits issued in the previous calendar
month (652 for August on 2026-10-02, built on 2026-09-28), each with its
permit number, template, status, start and issue times written as
``MM/DD/YYYY at H:MM AM``, project address and ZIP code, and its point as one
``lng, lat`` column. The workbook's 71 columns also name the people a permit
was issued to and by, its managers and contacts; the request keeps nine.
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

JOB = "permits_abilene"

COLUMNS = [
    "permit_number", "template_name", "status_project", "date_time_started", "permit_issued_date_time",
    "project_valuation", "project_address", "zip", "coordinates",
]

FIELD_MAP = {
    "job_id": ["permit_number"],
    "issuance_date": ["permit_issued_date_time"],
    "filing_date": ["date_time_started"],
    "job_type": ["template_name"],
    "status": ["status_project"],
    "cost": ["project_valuation"],
    "address_street": ["project_address"],
    "zipcode": ["zip"],
}

WHERE = "template_name NOT IN ('Certificate of Occupancy Permit (C)', 'Itinerant Business')"

ENDPOINT = "https://public.mygov.us/tx_abilene/downloadReport?moduleName=pi&id=371"
HEADERS = (
    "Permit Number", "Template Name", "Issued By", "Date Time Started", "Project Valuation", "Issued To",
    "Permit Description", "Project Address", "Status (Project)", "Property Contacts", "Permit Issued Date Time",
    "Zip", "Coordinates",
)
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _spec():
    return get_dataset(CityId.ABILENE, FeedType.PERMITS)


def _permit(number, template, issued, coordinates, started="08/03/2026 at 9:11 AM", status="active",
            valuation="0", address="100 EXAMPLE ST", zipcode="79601"):
    """One workbook row in the report's column order (synthetic values)."""
    return (number, template, "Example Inspector", started, valuation, "Example Owner", "Synthetic description",
            address, status, "Example Contact", issued, zipcode, coordinates)


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


AUGUST = [
    _permit("26-990001", "Roof Permit (R)", "08/31/2026 at 4:31 PM", "-99.733100, 32.448700", status="complete",
            valuation="12500"),
    _permit("26-990002", "Building Permit - Plumbing Permit", "08/05/2026 at 10:01 AM", "-99.765896, 32.367721"),
    # The vendor placed some new houses in Houston, Arizona and Colorado.
    _permit("26-990003", "New Single Family Residence", "08/24/2026 at 8:35 AM", "-95.489600, 29.955900"),
    _permit("26-990004", "New Single Family Residence", "08/20/2026 at 9:35 AM", ""),
    _permit("26-990005", "Certificate of Occupancy Permit (C)", "08/12/2026 at 8:57 AM", "-99.740000, 32.450000"),
]


@pytest.fixture
def scheduler():
    with patch("src.producers.base_producer.BaseKafkaProducer"):
        sched = MunicipalIngestionScheduler(dlq_producer=MagicMock(), rate_limit_delay_seconds=0.0, dedup_capacity=1000)
    for producer in sched.producers.values():
        producer.producer = MagicMock()
    sched.state_file = None
    return sched


def test_abilene_reads_the_citys_mygov_workbook():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.excel_abilene_permits_url == ENDPOINT
    assert (spec.platform, spec.ingestion_mode) == ("excel", "incremental")
    assert spec.field_map == FIELD_MAP
    # Every one of the 652 permits on 2026-10-02 had its own number.
    assert (spec.id_keys, spec.composite_id) == (["permit_number"], False)


def test_the_issue_time_is_text_and_compared_as_a_time():
    spec = _spec()
    assert (spec.watermark_col, spec.watermark_type) == ("permit_issued_date_time", "text")
    assert spec.watermark_format == "%m/%d/%Y at %I:%M %p"
    assert spec.order_by == "permit_issued_date_time DESC"


def test_the_request_keeps_nine_of_seventy_one_columns():
    # Who a permit was issued to and by, who created and manages it, its
    # contacts and its description stay in the client.
    assert _spec().select.split(",") == COLUMNS


def test_the_filter_leaves_out_occupancy_certificates_and_itinerant_businesses():
    assert _spec().where == WHERE


def test_each_point_is_one_lon_lat_column_and_the_box_clips_misplaced_ones():
    spec = _spec()
    assert (spec.point_col, spec.point_lon_first) == ("coordinates", True)
    assert spec.needs_geocode is False
    # 35 of the 652 points on 2026-10-02 lay in Houston, Flagstaff or
    # western Colorado, and 3 permits had none: the clip drops them.
    assert spec.metro_clip is True


def test_the_cadence_allows_a_monthly_workbook_a_month_behind():
    spec = _spec()
    # The newest permit was 32 days old on 2026-10-02 and is about 58 days
    # old when the next workbook comes, as Richmond's monthly transfers are.
    assert (spec.interval_seconds, spec.expected_cadence_days) == (86400.0, 45)


def test_the_cap_holds_a_month_of_storm_repairs():
    # August's 636 building permits held 152 roofs. A newest-first poll that
    # fills its cap never reads the month's older permits, and the workbook
    # is read whole either way, so the cap leaves room for a hail month.
    assert _spec().batch_limit == 2500


def test_the_permits_producer_reads_mygov_times(scheduler):
    row = dict(zip(COLUMNS, ("26-990001", "Roof Permit (R)", "complete", "08/03/2026 at 9:11 AM",
                             "08/31/2026 at 4:31 PM", "12500", "100 EXAMPLE ST", "79601", "-99.7331, 32.4487")))
    row.update(latitude=32.4487, longitude=-99.7331)

    event = scheduler.producers["permits"].parse_socrata_row(row, city_id="abilene")

    assert event is not None
    assert event.issuance_date.isoformat() == "2026-08-31T16:31:00+00:00"
    assert event.filing_date.isoformat() == "2026-08-03T09:11:00+00:00"
    assert (event.job_id, event.status, event.zipcode, event.estimated_cost) == ("26-990001", "complete", "79601", 12500.0)


def test_a_new_house_is_new_construction(scheduler):
    # 114 of August's 636 permits were new single-family homes and townhouses.
    row = dict(zip(COLUMNS, ("26-990003", "New Single Family Residence", "active", "08/03/2026 at 9:11 AM",
                             "08/24/2026 at 8:35 AM", "0", "100 EXAMPLE ST", "79601", "-99.7331, 32.4487")))
    row.update(latitude=32.4487, longitude=-99.7331)

    event = scheduler.producers["permits"].parse_socrata_row(row, city_id="abilene")

    assert event is not None
    assert (event.job_type.value, event.normalized_permit_type) == ("NB", "NEW_CONSTRUCTION")


class TestAbilenePoll:
    def test_a_month_publishes_once_and_the_next_workbook_follows(self, scheduler):
        september = [
            _permit("26-991001", "Building Permit - Electrical", "09/01/2026 at 8:02 AM", "-99.7400, 32.4600"),
        ]
        files = iter([_workbook(AUGUST), _workbook(AUGUST), _workbook(september)])
        client = ExcelClient(httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=next(files)))))
        client.paginate = MagicMock(side_effect=client.paginate)
        scheduler.producers["permits"].excel = client

        result = scheduler.poll_job(JOB)

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (4, 2, 2)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        events = [call.kwargs["payload"] for call in scheduler.producers["permits"].producer.produce.call_args_list]
        assert [(event.job_id, event.latitude, event.longitude) for event in events] == [
            ("26-990001", 32.4487, -99.7331), ("26-990002", 32.367721, -99.765896),
        ]
        assert scheduler.metrics[JOB].high_watermark == "08/31/2026 at 4:31 PM"
        kwargs = client.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WHERE})"
        assert (kwargs["point_col"], kwargs["point_lon_first"], kwargs["select"]) == ("coordinates", True, ",".join(COLUMNS))

        # The same workbook: nothing was issued after the newest time.
        result = scheduler.poll_job(JOB)

        assert client.paginate.call_args.kwargs["where_clause"] == (
            f"({WHERE}) AND permit_issued_date_time > '08/31/2026 at 4:31 PM'"
        )
        assert (result["records_fetched"], result["records_published"]) == (0, 0)

        # September's workbook replaces August's.
        result = scheduler.poll_job(JOB)

        assert (result["records_fetched"], result["records_published"]) == (1, 1)
        assert scheduler.metrics[JOB].high_watermark == "09/01/2026 at 8:02 AM"
