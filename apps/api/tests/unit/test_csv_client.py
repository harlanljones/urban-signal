"""Tests for static CSV normalization, typed watermarks, and zip members."""

import io
import zipfile
from datetime import date
from itertools import cycle

import httpx
import pytest

from src.producers import csv_client
from src.producers.csv_client import (
    CSVClient,
    _body_lines,
    _decode_csv_bytes,
    _lines,
    _read_zip_member,
    _strip_preamble,
    _zip_member_lines,
    resolve_relative_dates,
)


def _zip_bytes(members: dict[str, str | bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, text in members.items():
            archive.writestr(name, text)
    return buf.getvalue()



def test_csv_client_normalizes_headers_and_sorts_typed_dates():
    payload = (
        "PropertyID,Sale_date,Sale_price\n"
        "old,12/31/2024,100\n"
        "newest,11/30/2025,300\n"
        "middle,01/02/2025,200\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=payload, request=request)

    client = CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))
    batches = list(
        client.paginate(
            "https://example.test/sales.csv",
            where_clause="sale_date > '12/31/2024'",
            order_by="sale_date DESC",
            batch_size=10,
            watermark_col="sale_date",
            watermark_format="%m/%d/%Y",
        )
    )

    assert [row["propertyid"] for row in batches[0]] == ["newest", "middle"]
    assert batches[0][0]["sale_price"] == "300"


def test_csv_client_applies_text_watermark_exclusions():
    payload = "Record ID,Date Issued\nA,2025-01-01\nB,9999-12-31\n"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=payload, request=request)

    client = CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))
    batches = list(
        client.paginate(
            "https://example.test/permits.csv",
            where_clause="date_issued > '2024-01-01'",
            watermark_col="date_issued",
            watermark_format="%Y-%m-%d",
            watermark_exclude=["9999-12-31"],
        )
    )

    assert [row["record_id"] for row in batches[0]] == ["A"]


def test_csv_client_reads_named_zip_member_year_file():
    payload = _zip_bytes(
        {
            "2025.csv": "REQUESTID,DATETIMEINIT\nold,2025-12-31 23:59:00\n",
            "2026.csv": "REQUESTID,DATETIMEINIT\n2121679,2026-08-27 05:54:02.043\n",
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, request=request)

    client = CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))
    batches = list(
        client.paginate(
            "https://example.test/csb.zip",
            zip_member="2026.csv",
            batch_size=10,
        )
    )

    assert len(batches) == 1
    assert batches[0][0]["requestid"] == "2121679"
    assert batches[0][0]["datetimeinit"] == "2026-08-27 05:54:02.043"


def test_csv_client_zip_member_matches_nested_basename():
    payload = _zip_bytes({"csb/2026.csv": "REQUESTID\n99\n"})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, request=request)

    client = CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))
    batches = list(
        client.paginate("https://example.test/csb.zip", zip_member="2026.csv")
    )
    assert batches[0][0]["requestid"] == "99"


def test_csv_client_zip_member_missing_raises():
    payload = _zip_bytes({"2025.csv": "REQUESTID\n1\n"})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, request=request)

    client = CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(FileNotFoundError, match="2026.csv"):
        list(client.paginate("https://example.test/csb.zip", zip_member="2026.csv"))


def test_read_zip_member_rejects_boolean_flag():
    with pytest.raises(ValueError, match="member filename"):
        _read_zip_member(b"PK\x03\x04not-a-real-zip", True)


def test_csv_client_reads_pipe_delimited_rows():
    """Maricopa sales affidavits are pipe-delimited (US-392)."""
    payload = (
        "PARCELNUMBER|SALEPRICE|DEEDNUMBER|SITUSADDRESS\n"
        "20904027B|210000|000000267|22026 N 24TH AVE\n"
        "11234567C|180000|000000268|123 MAIN ST\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=payload, request=request)

    client = CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))
    batches = list(client.paginate("https://example.test/sales.txt", delimiter="|"))
    assert len(batches) == 1
    assert batches[0][0]["parcelnumber"] == "20904027B"
    assert batches[0][0]["saleprice"] == "210000"
    assert batches[0][1]["deednumber"] == "000000268"


def test_csv_client_strips_single_field_preamble_line():
    """ABC DailyExport-CSV leads the real header with a one-field metadata line."""
    payload = (
        '"Updated Wednesday 2nd of September 2026 03:50:26 AM"\n'
        '"License Type","File Number","Lic or App","Type Status",'
        '"Type Orig Iss Date","Expir Date","Primary Name","Prem Addr 1",'
        '"Prem City","Prem Zip","Prem County","DBA Name"\n'
        "17,00505492,APP,ACTIVE,18-MAY-2022,30-APR-2027,"
        "PELOTON IMPORTS LLC,755 SKYWAY CT,NAPA,94558,NAPA,PELOTON IMPORTS LLC\n"
        "47,00361506,LIC,ACTIVE,01-FEB-1988,30-JUN-2027,"
        "SAMPLE BAR,100 MAIN ST,SONOMA,95404,SONOMA,SAMPLE BAR\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=payload, request=request)

    client = CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))
    batches = list(
        client.paginate(
            "https://www.abc.ca.gov/export.zip",
            where_clause="prem_county = 'SONOMA'",
        )
    )
    assert len(batches) == 1
    rows = batches[0]
    assert [r["file_number"] for r in rows] == ["00361506"]
    assert rows[0]["license_type"] == "47"
    assert rows[0]["prem_city"] == "SONOMA"


def test_csv_client_where_clause_supports_or():
    """inland_empire ABC slice covers two counties via an OR clause."""
    payload = (
        "File Number,License Type,Prem County\n"
        "1,41,RIVERSIDE\n"
        "2,20,SAN BERNARDINO\n"
        "3,47,SAN DIEGO\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=payload, request=request)

    client = CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))
    batches = list(
        client.paginate(
            "https://example.test/abc.csv",
            where_clause="prem_county = 'RIVERSIDE' OR prem_county = 'SAN BERNARDINO'",
        )
    )
    assert [r["file_number"] for r in batches[0]] == ["1", "2"]


@pytest.mark.parametrize("eol", ["\r", "\n", "\r\n"], ids=["cr", "lf", "crlf"])
def test_csv_client_reads_any_line_ending(eol):
    """Milwaukee's permits export ends every row with a bare carriage return;
    parsing it as one line raised "new-line character seen in unquoted field"
    on every poll."""
    lines = [
        '"Date Opened","Address","Record ID","Permit Type","Date Issued"',
        '"2026-02-03 00:00:00","100 N MAIN ST","COM-ALT-26-00001","Commercial Alteration Permit","2026-06-15 00:00:00"',
        '"2026-04-23 00:00:00","200 W WELLS ST","RES-ALT-26-00002","Residential Alteration Permit","2026-06-12 00:00:00"',
        '"2026-05-01 00:00:00","300 E OAK ST","RES-NEW-26-00003","Residential New Construction Permit","2026-06-15 00:00:00"',
    ]
    payload = eol.join(lines) + eol

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=payload, request=request)

    client = CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))
    batches = list(
        client.paginate(
            "https://example.test/buildingpermits.csv",
            where_clause="date_issued > '2026-06-13T00:00:00'",
            order_by="date_issued ASC",
        )
    )

    rows = [row for batch in batches for row in batch]
    assert [row["record_id"] for row in rows] == ["COM-ALT-26-00001", "RES-NEW-26-00003"]
    assert rows[0]["address"] == "100 N MAIN ST"


def test_strip_preamble_reads_bare_carriage_returns():
    payload = '"Updated 2026-09-29"\r"A","B"\r"1","2"\r'
    assert _strip_preamble(payload) == "A,B\n1,2\n"


def test_strip_preamble_parses_only_the_rows_that_decide(monkeypatch):
    """A file with a header comes back untouched after two rows: parsing all
    510,000 lines of Alachua County's sales took more memory than the text."""
    lines_read = []
    real_lines = csv_client._lines

    def counting(text):
        for line in real_lines(text):
            lines_read.append(line)
            yield line

    monkeypatch.setattr(csv_client, "_lines", counting)
    text = "Parcel\tSale_Date\r\n" + "".join(f"{n:05d}\t2026-09-28\r\n" for n in range(1000))

    assert _strip_preamble(text, delimiter="\t") is text
    assert len(lines_read) == 2


def test_a_window_closes_at_today():
    """``CURRENT_DATE`` alone resolves too: Alachua County's sales list holds
    one sale keyed for 2079, which only an upper bound keeps out."""
    today = date(2026, 10, 2)
    assert resolve_relative_dates(
        "sale_date >= CURRENT_DATE - INTERVAL '90' DAY AND sale_date <= CURRENT_DATE", today
    ) == "sale_date >= '2026-07-04' AND sale_date <= '2026-10-02'"
    assert resolve_relative_dates("d <= current_date", today) == "d <= '2026-10-02'"


def test_csv_client_names_the_columns_of_a_file_without_a_header_row():
    """Pierce County's sales file starts with its first sale: the spec names
    the columns, and select drops the parties from each row as it is read."""
    payload = _zip_bytes({
        "sale.txt": (
            "9999901|1|0000000001|09/11/2026|451000.00|Statutory Warranty Deed|GRANTOR A|GRANTEE B\r\n"
            "9999902|2|0000000002|02/03/2026|389000.00|Quit Claim Deed|GRANTOR C|GRANTEE D\r\n"
            "9999903|1|0000000003|09/14/2026|512000.00|Bargain & Sale Deed|GRANTOR E|GRANTEE F\r\n"
        )
    })

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, request=request)

    client = CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))
    rows = [
        row
        for batch in client.paginate(
            "https://example.test/sale.zip",
            where_clause="sale_date >= '2026-09-01'",
            order_by="sale_date DESC",
            select="etn,parcel_number,sale_date,sale_price,deed_type",
            watermark_col="sale_date",
            watermark_format="%m/%d/%Y",
            zip_member="sale.txt",
            delimiter="|",
            columns=["ETN", "Parcel Count", "Parcel Number", "Sale Date", "Sale Price", "Deed Type", "Grantor",
                     "Grantee"],
        )
        for row in batch
    ]

    assert [row["etn"] for row in rows] == ["9999903", "9999901"]
    assert rows[1] == {
        "etn": "9999901", "parcel_number": "0000000001", "sale_date": "09/11/2026", "sale_price": "451000.00",
        "deed_type": "Statutory Warranty Deed",
    }


def test_csv_client_keeps_a_quoted_line_break_inside_its_field():
    payload = 'id,note,issued\r\n1,"two\r\nlines",2026-09-01\r\n2,"bare\rreturn",2026-09-02\r\n'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=payload, request=request)

    client = CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))
    rows = [row for batch in client.paginate("https://example.test/notes.csv") for row in batch]

    assert [(row["id"], row["note"], row["issued"]) for row in rows] == [
        ("1", "two\r\nlines", "2026-09-01"),
        ("2", "bare\rreturn", "2026-09-02"),
    ]


def _zip_client(payload: bytes) -> CSVClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, request=request)

    return CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))


def test_a_zip_member_is_read_as_its_rows_are(monkeypatch):
    """Polk County's sales member unpacks to 518 MB: the client decompresses
    and decodes it as the rows are read instead of holding it whole, and
    closes the archive once they are."""
    payload = _zip_bytes({
        "ftp_sales.txt": "PARCEL_ID,SALEDT,PRICE\r\n"
        + "".join(f"{n:018d},09/{n % 28 + 1:02d}/2026,{n}00\r\n" for n in range(2000))
    })

    def whole(*args, **kwargs):
        raise AssertionError("the member was read whole")

    monkeypatch.setattr(zipfile.ZipFile, "read", whole)
    monkeypatch.setattr(csv_client, "_decode_csv_bytes", whole)
    archives = []

    class Recorded(zipfile.ZipFile):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            archives.append(self)

    monkeypatch.setattr(zipfile, "ZipFile", Recorded)

    rows = [
        row
        for batch in _zip_client(payload).paginate(
            "https://example.test/ftp_sales.zip",
            where_clause="saledt >= '2026-09-27'",
            order_by="saledt DESC",
            watermark_col="saledt",
            watermark_format="%m/%d/%Y",
            zip_member="ftp_sales.txt",
        )
        for row in batch
    ]

    # Days 27 and 28 of each of the 71 whole 28-row cycles.
    assert len(rows) == 142
    assert {row["saledt"] for row in rows} == {"09/27/2026", "09/28/2026"}
    assert len(archives) == 1
    assert archives[0].fp is None


@pytest.mark.parametrize(
    "raw",
    [
        "Parcel,Street\n1,Zoë Ct\n".encode(),
        "\ufeffParcel,Street\n1,Zoë Ct\n".encode(),
        "Parcel,Street\n1,Zoë Ct\n".encode("cp1252"),
        b"Parcel,Street\n1,Zo\x81\xff Ct\n",
        b"Parcel,Street\n1,Zo\xc3",
    ],
    ids=["utf-8", "utf-8-bom", "cp1252", "neither", "cut-short"],
)
def test_a_zip_member_decodes_as_its_whole_bytes_did(raw, monkeypatch):
    """The member is decoded a piece at a time, in the encoding its whole
    bytes chose: UTF-8 (without a byte-order mark) when every byte decodes,
    else cp1252, else UTF-8 with replacement characters. One-byte pieces
    split every multibyte character."""
    monkeypatch.setattr(csv_client, "_CHUNK", 1)
    assert _read_zip_member(_zip_bytes({"sales.txt": raw}), "sales.txt") == _decode_csv_bytes(raw)


def test_a_zip_member_splits_lines_as_text_does():
    """Every ending (\\r\\n, bare \\r, \\n) ends a line, as it does for a
    downloaded text, wherever the reader's buffer boundaries fall."""
    text = "".join(
        f"{n},{'x' * (n % 97)}{ending}" for n, ending in zip(range(6000), cycle(["\r\n", "\r", "\n"]))
    )

    lines = list(_zip_member_lines(_zip_bytes({"sale.txt": text}), "sale.txt"))

    assert lines == list(_lines(text))


def test_a_zip_member_with_a_title_line_streams_without_it():
    payload = _zip_bytes({
        "export.csv": (
            '"Updated Friday 2nd of October 2026 05:35:00 AM"\r\n'
            '"File Number","Prem County"\r\n'
            '1,"POLK\r\nCOUNTY"\r\n'
            "\r\n"
            "2,LAKE\r\n"
        )
    })

    rows = [row for batch in _zip_client(payload).paginate("https://example.test/export.zip", zip_member="export.csv")
            for row in batch]

    assert rows == [
        {"file_number": "1", "prem_county": "POLK\r\nCOUNTY"},
        {"file_number": "2", "prem_county": "LAKE"},
    ]


def _body_client(body: bytes) -> CSVClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": "text/csv"}, request=request)

    return CSVClient(httpx.Client(transport=httpx.MockTransport(handler)))


def test_a_plain_body_is_read_without_its_text(monkeypatch):
    """Larimer County's sales file is 101 MB, and its text held whole added
    385 MB to the peak: the client decodes the body as its rows are read."""
    body = "PARCELNO,SALEDATE,SALEPRICE\r\n" + "".join(
        f"{n:010d},2026-09-{n % 28 + 1:02d} 00:00:00,{n}00\r\n" for n in range(2000)
    )

    def whole(self):
        raise AssertionError("the body was read as text")

    monkeypatch.setattr(httpx.Response, "text", property(whole))

    rows = [
        row
        for batch in _body_client(body.encode()).paginate(
            "https://example.test/assessor-public-sales.csv",
            where_clause="saledate >= '2026-09-27'",
            order_by="saledate DESC",
            watermark_col="saledate",
            watermark_format="%Y-%m-%d %H:%M:%S",
        )
        for row in batch
    ]

    # Days 27 and 28 of each of the 71 whole 28-row cycles.
    assert len(rows) == 142
    assert {row["saledate"] for row in rows} == {"2026-09-27 00:00:00", "2026-09-28 00:00:00"}


@pytest.mark.parametrize(
    ("raw", "content_type"),
    [
        ("Parcel,Street\n1,Zoë Ct\n".encode(), "text/csv"),
        ("﻿Parcel,Street\n1,Zoë Ct\n".encode(), "text/csv"),
        ("Parcel,Street\n1,Zoë Ct\n".encode("cp1252"), "text/csv; charset=windows-1252"),
        ("Parcel,Street\n1,Zoë Ct\n".encode("cp1252"), "application/octet-stream"),
        (b"Parcel,Street\n1,Zo\xc3", "text/csv"),
        (("Parcel,Street\n" + "".join(f"{n},{'€' * (1000 + 37 * n)}\n" for n in range(40))).encode(), "text/csv"),
    ],
    ids=["utf-8", "utf-8-bom", "declared-cp1252", "undeclared-cp1252", "cut-short", "split-characters"],
)
def test_a_plain_body_decodes_as_its_text_did(raw, content_type):
    """The body decodes as httpx decodes its text: in the declared charset,
    else UTF-8, with httpx's replacement characters, wherever the reader's
    pieces split a character."""
    response = httpx.Response(200, content=raw, headers={"content-type": content_type})

    assert list(_body_lines(response)) == list(_lines(response.text))


def test_a_plain_body_splits_lines_as_its_text_did():
    """Every ending (\\r\\n, bare \\r, \\n) ends a line, as it does in the
    downloaded text, including a \\r\\n split between the reader's pieces."""
    text = "x" * 8191 + "\r\n" + "".join(
        f"{n},{'x' * (n % 97)}{ending}" for n, ending in zip(range(6000), cycle(["\r\n", "\r", "\n"]))
    )
    response = httpx.Response(200, content=text.encode())

    assert list(_body_lines(response)) == list(_lines(text))
