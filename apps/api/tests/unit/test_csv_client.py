"""Tests for static CSV normalization and typed watermark handling."""

import httpx

from src.producers.csv_client import CSVClient


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
