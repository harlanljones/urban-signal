"""Tests for static CSV normalization, typed watermarks, and zip members."""

import io
import zipfile

import httpx
import pytest

from src.producers.csv_client import CSVClient, _read_zip_member, _strip_preamble


def _zip_bytes(members: dict[str, str]) -> bytes:
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
