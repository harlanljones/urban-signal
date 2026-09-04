"""Unit tests for the EIA electricity leaf module (US-423).

Leaf-only: imports no spine symbols (config / city_registry / geo_utils /
submarkets / producers). Network calls are stubbed via a fake httpx.Client
stand-in; no real HTTP is performed.
"""

import pytest

from src.spatial.eia_electricity import (
    COMMERCIAL_SECTOR,
    INDUSTRIAL_SECTOR,
    EiaElectricityClient,
    cents_to_dollars_per_kwh,
    commercial_industrial_rate_index,
    parse_retail_sales_row,
    parse_retail_sales_rows,
)


def test_cents_to_dollars_per_kwh_basic():
    assert cents_to_dollars_per_kwh(12.5) == 0.125


def test_cents_to_dollars_per_kwh_none_passthrough():
    assert cents_to_dollars_per_kwh(None) is None


def test_parse_retail_sales_row_basic():
    row = {
        "period": "2026-06",
        "stateid": "tx",
        "sectorid": "com",
        "price": "11.2",
        "revenue": "154302.5",
        "sales": "1378211.0",
        "customers": "612345",
    }
    rec = parse_retail_sales_row(row)
    assert rec.period == "2026-06"
    assert rec.state_id == "TX"
    assert rec.sector_id == "COM"
    assert rec.price_per_kwh == pytest.approx(0.112)
    assert rec.revenue_thousand_usd == 154302.5
    assert rec.sales_mwh == 1378211.0
    assert rec.customers == 612345


def test_parse_retail_sales_row_missing_fields_returns_none():
    row = {"period": "2026-06", "stateid": "TX", "sectorid": "COM"}
    rec = parse_retail_sales_row(row)
    assert rec.price_per_kwh is None
    assert rec.revenue_thousand_usd is None
    assert rec.sales_mwh is None
    assert rec.customers is None


def test_parse_retail_sales_rows_batch():
    rows = [
        {"period": "2026-06", "stateid": "TX", "sectorid": "COM", "price": "11.2"},
        {"period": "2026-06", "stateid": "TX", "sectorid": "IND", "price": "7.5"},
    ]
    recs = parse_retail_sales_rows(rows)
    assert len(recs) == 2
    assert recs[0].sector_id == "COM"
    assert recs[1].sector_id == "IND"


def test_commercial_industrial_rate_index_latest_period_wins():
    rows = [
        {"period": "2026-05", "stateid": "TX", "sectorid": "COM", "price": "10.0"},
        {"period": "2026-06", "stateid": "TX", "sectorid": "COM", "price": "11.2"},
        {"period": "2026-06", "stateid": "TX", "sectorid": "IND", "price": "7.5"},
        {"period": "2026-06", "stateid": "TX", "sectorid": "RES", "price": "13.0"},
    ]
    recs = parse_retail_sales_rows(rows)
    index = commercial_industrial_rate_index(recs)
    assert index["TX"]["commercial"] == pytest.approx(0.112)
    assert index["TX"]["industrial"] == pytest.approx(0.075)
    # RES sector is not indexed (only COM/IND are the ticket's operating-cost axis).
    assert "residential" not in index["TX"]


def test_commercial_industrial_rate_index_skips_missing_price():
    rows = [
        {"period": "2026-05", "stateid": "TX", "sectorid": "COM", "price": "10.0"},
        {"period": "2026-06", "stateid": "TX", "sectorid": "COM", "price": None},
    ]
    recs = parse_retail_sales_rows(rows)
    index = commercial_industrial_rate_index(recs)
    # Later period has no price, so the earlier known rate is kept, not clobbered.
    assert index["TX"]["commercial"] == pytest.approx(0.10)


def test_commercial_industrial_rate_index_empty():
    assert commercial_industrial_rate_index([]) == {}


def test_client_requires_api_key():
    with pytest.raises(ValueError):
        EiaElectricityClient(api_key="")


def test_client_build_params_shape():
    client = EiaElectricityClient(api_key="test-key", page_length=100)
    params = client.build_params(
        frequency="monthly",
        state="tx",
        sectorid=[COMMERCIAL_SECTOR, INDUSTRIAL_SECTOR],
        start="2025-01",
        end="2026-06",
        offset=200,
    )
    assert params["api_key"] == "test-key"
    assert params["frequency"] == "monthly"
    assert params["facets[stateid][]"] == "TX"
    assert params["facets[sectorid][0]"] == "COM"
    assert params["facets[sectorid][1]"] == "IND"
    assert params["start"] == "2025-01"
    assert params["end"] == "2026-06"
    assert params["offset"] == 200
    assert params["length"] == 100


def test_client_page_length_capped():
    client = EiaElectricityClient(api_key="k", page_length=999999)
    assert client.page_length == EiaElectricityClient.MAX_PAGE_LENGTH


def test_client_rows_and_total_parse_v2_envelope():
    payload = {
        "response": {
            "total": "2",
            "data": [
                {"period": "2026-06", "stateid": "TX", "sectorid": "COM", "price": "11.2"},
                {"period": "2026-06", "stateid": "TX", "sectorid": "IND", "price": "7.5"},
            ],
        }
    }
    assert EiaElectricityClient.total(payload) == 2
    assert len(EiaElectricityClient.rows(payload)) == 2


def test_client_rows_missing_envelope_returns_empty():
    assert EiaElectricityClient.rows({}) == []
    assert EiaElectricityClient.total({}) == 0


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeHttpClient:
    """Stand-in for httpx.Client that records calls and returns fixed pages."""

    def __init__(self, pages):
        self._pages = pages
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        page = self._pages[len(self.calls) - 1]
        return _FakeResponse({"response": {"total": str(len(page)), "data": page}})

    def close(self):
        pass


def test_retail_sales_pages_until_short_page():
    page1 = [
        {"period": "2026-06", "stateid": "TX", "sectorid": "COM", "price": "11.2"}
        for _ in range(2)
    ]
    page2 = [{"period": "2026-06", "stateid": "TX", "sectorid": "IND", "price": "7.5"}]
    fake = _FakeHttpClient([page1, page2])
    client = EiaElectricityClient(api_key="k", page_length=2, http_client=fake)
    records = client.retail_sales(state="TX")
    assert len(records) == 3
    assert len(fake.calls) == 2


def test_retail_sales_stops_on_empty_page():
    fake = _FakeHttpClient([[]])
    client = EiaElectricityClient(api_key="k", page_length=2, http_client=fake)
    records = client.retail_sales(state="TX")
    assert records == []
    assert len(fake.calls) == 1


def test_retail_sales_respects_max_records():
    page1 = [{"period": "2026-06", "stateid": "TX", "sectorid": "COM", "price": "11.2"}]
    fake = _FakeHttpClient([page1])
    client = EiaElectricityClient(api_key="k", page_length=2, http_client=fake)
    records = client.retail_sales(state="TX", max_records=1)
    # length param for the single request should have been capped to max_records.
    assert fake.calls[0][1]["length"] == 1
    assert len(records) == 1
    # Exactly one call: after hitting max_records, no further page is fetched.
    assert len(fake.calls) == 1
