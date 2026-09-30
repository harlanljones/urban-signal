"""ExcelClient on .xlsx workbooks: the monthly link, the rolling window, the
columns that leave the client, and the 304 that skips an unchanged file."""

import io
import zipfile
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest

from src.producers.csv_client import resolve_relative_dates
from src.producers.excel_client import ExcelClient

PAGE = "https://www.example.test/media/53946"
FILE = "https://www.example.test/sites/default/files/2026-09/Assessor_Transfers_2026-09-23.xlsx"
PATTERN = r"Assessor_Transfers_[0-9-]+\.xlsx$"
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _workbook(rows_xml: str) -> bytes:
    """A one-sheet .xlsx whose style 1 is the built-in m/d/yyyy date format."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{MAIN}" xmlns:r="{REL}"><sheets><sheet name="T" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{REL}/worksheet" Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="rId2" Type="{REL}/styles" Target="styles.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/styles.xml",
            f'<styleSheet xmlns="{MAIN}"><cellXfs><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>',
        )
        archive.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{MAIN}"><sheetData>{rows_xml}</sheetData></worksheet>')
    return buf.getvalue()


def _serial(day: datetime) -> int:
    return (day - datetime.fromisoformat("1899-12-30")).days


def _transfers() -> bytes:
    """Three synthetic transfers: 10 days old, 20 days old, and 400 days old."""
    today = datetime.now(UTC).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
    header = (
        '<row r="1"><c r="A1" t="inlineStr"><is><t>PIN</t></is></c>'
        '<c r="B1" t="inlineStr"><is><t>TRANSFER_DATE</t></is></c>'
        '<c r="C1" t="inlineStr"><is><t>CONSIDERATION</t></is></c>'
        '<c r="D1" t="inlineStr"><is><t>GRANTEE</t></is></c></row>'
    )
    rows = "".join(
        f'<row r="{n}"><c r="A{n}" t="inlineStr"><is><t>{pin}</t></is></c>'
        f'<c r="B{n}" s="1"><v>{_serial(today - timedelta(days=age))}</v></c>'
        f'<c r="C{n}"><v>{amount}</v></c>'
        f'<c r="D{n}" t="inlineStr"><is><t>BUYER {n}</t></is></c></row>'
        for n, pin, age, amount in ((2, "W0000000001", 20, 1000), (3, "W0000000002", 10, 0), (4, "W0000000003", 400, 5))
    )
    return _workbook(header + rows)


class Server:
    """A media page linking last month's and this month's workbooks."""

    def __init__(self, etag: str | None = '"v1"'):
        self.etag = etag
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if str(request.url) == PAGE:
            body = (
                '<a href="/sites/default/files/2026-08/Assessor_Transfers_2026-08-19.xlsx">August</a>'
                '<a href="/sites/default/files/2026-09/Assessor_Transfers_2026-09-23.xlsx?a=1&amp;b=2">x</a>'
                '<a href="/sites/default/files/2026-09/Assessor_Transfers_2026-09-23.xlsx">September</a>'
                '<a href="/sites/default/files/other.pdf">Guide</a>'
            )
            return httpx.Response(200, text=body)
        if str(request.url) == FILE:
            if self.etag and request.headers.get("If-None-Match") == self.etag:
                return httpx.Response(304)
            headers = {"ETag": self.etag} if self.etag else {}
            return httpx.Response(200, content=_transfers(), headers=headers)
        return httpx.Response(404)


def _client(server: Server) -> ExcelClient:
    return ExcelClient(httpx.Client(transport=httpx.MockTransport(server)))


def _poll(client: ExcelClient, **kwargs) -> list[dict]:
    return [
        row
        for batch in client.paginate(
            PAGE,
            where_clause="TRANSFER_DATE >= CURRENT_DATE - INTERVAL '365' DAY",
            order_by="transfer_date DESC",
            select="pin,transfer_date,consideration",
            link_pattern=PATTERN,
            **kwargs,
        )
        for row in batch
    ]


def test_the_newest_linked_workbook_is_read_through_its_window():
    server = Server()
    rows = _poll(_client(server))

    assert [row["pin"] for row in rows] == ["W0000000002", "W0000000001"]
    assert set(rows[0]) == {"pin", "transfer_date", "consideration"}
    assert rows[0]["transfer_date"].endswith("T00:00:00")
    assert str(server.requests[1].url) == FILE


def test_the_link_is_the_greatest_matching_name():
    server = Server()
    client = _client(server)
    assert client.resolve_link(PAGE, PATTERN) == FILE
    with pytest.raises(ValueError, match="links no file"):
        client.resolve_link(PAGE, r"Assessor_Sales_.*\.csv$")


def test_an_unchanged_workbook_is_not_read_again():
    server = Server()
    client = _client(server)
    assert len(_poll(client)) == 2

    assert _poll(client) == []
    assert server.requests[-1].headers["If-None-Match"] == '"v1"'


def test_a_capped_or_abandoned_read_is_read_again():
    server = Server()
    client = _client(server)
    assert len(_poll(client, max_records=1)) == 1
    assert len(_poll(client)) == 2

    fresh = _client(Server())
    batches = fresh.paginate(PAGE, batch_size=1, link_pattern=PATTERN)
    next(batches)
    batches.close()
    assert fresh._validators == {}


def test_a_workbook_without_validators_is_always_read():
    client = _client(Server(etag=None))
    assert len(_poll(client)) == 2
    assert len(_poll(client)) == 2


def test_relative_dates_resolve_to_a_quoted_day():
    today = date(2026, 9, 30)
    assert resolve_relative_dates("d >= CURRENT_DATE - INTERVAL '365' DAY", today) == "d >= '2025-09-30'"
    assert resolve_relative_dates("d >= current_date - interval '7' day AND x = 'A'", today) == (
        "d >= '2026-09-23' AND x = 'A'"
    )
    assert resolve_relative_dates(None) is None
