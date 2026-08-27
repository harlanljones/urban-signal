"""Tests for static CSV normalization, typed watermarks, and zip members."""

import io
import zipfile

import httpx
import pytest

from src.producers.csv_client import CSVClient, _read_zip_member


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
