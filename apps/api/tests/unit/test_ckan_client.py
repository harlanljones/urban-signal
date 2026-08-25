"""Unit tests for the CKAN datastore client.

Fixtures are recorded from live probes of data.boston.gov (2026-08-23):
Approved Building Permits resource ``6ddcd912-32a0-43df-9908-63574f8c7e77``
(datastore-active, total 660839) and the non-datastore PDF companion resource
``65032067-580e-4167-9a5c-94fa8ac2d9a7``. Live end-to-end tests are gated
behind ``URBAN_LIVE_PROBE=1``.
"""

import json
import os
from datetime import date

import httpx
import pytest

from src.producers.ckan_client import (
    CkanClient,
    CkanError,
    NonDatastoreResourceError,
    _parse_where_terms,
    _quote_order_by,
)

PERMITS_URI = "ckan://data.boston.gov/6ddcd912-32a0-43df-9908-63574f8c7e77"

# --- Recorded live fixtures (trimmed to the fields the tests assert on). -----

# datastore_search?resource_id=6ddcd912...&limit=N — result envelope incl. total.
SEARCH_PAGE_1 = {
    "success": True,
    "result": {
        "records": [
            {
                "_id": 1,
                "permitnumber": "A1000569",
                "issued_date": "2021-01-28T16:29:26",
                "status": "Closed",
                "y_latitude": 42.35919000001041,
                "x_longitude": -71.05292400062602,
            },
            {
                "_id": 2,
                "permitnumber": "A1000570",
                "issued_date": "2021-01-28T16:31:02",
                "status": "Open",
                "y_latitude": 42.3,
                "x_longitude": -71.06,
            },
        ],
        "total": 3,
        "fields": [
            {"id": "_id", "type": "int"},
            {"id": "permitnumber", "type": "text"},
            {"id": "issued_date", "type": "timestamp"},
        ],
    },
}

SEARCH_PAGE_2 = {
    "success": True,
    "result": {
        "records": [
            {
                "_id": 3,
                "permitnumber": "A1000571",
                "issued_date": "2021-01-29T09:00:00",
                "status": "Open",
                "y_latitude": 42.31,
                "x_longitude": -71.05,
            }
        ],
        "total": 3,
    },
}

# Recorded live probe of datastore_search against the non-datastore PDF resource.
NON_DATASTORE_BODY = {
    "help": "https://data.boston.gov/api/3/action/help_show?name=datastore_search",
    "error": {
        "__type": "Not Found Error",
        "message": 'Not found: Resource "65032067-580e-4167-9a5c-94fa8ac2d9a7" was not found.',
    },
    "success": False,
}

# Recorded live datastore_search_sql watermark query (permits, issued_date >).
SQL_WATERMARK_RESULT = {
    "success": True,
    "result": {
        "sql": (
            'SELECT * FROM "6ddcd912-32a0-43df-9908-63574f8c7e77" '
            "WHERE \"issued_date\" > '2026-08-20T00:00:00' "
            'ORDER BY "_id" LIMIT 1000 OFFSET 0'
        ),
        "records": [
            {"_id": 559113, "permitnumber": "SF1888557", "issued_date": "2026-08-20T00:05:48"},
            {"_id": 419629, "permitnumber": "PL1880118", "issued_date": "2026-08-20T00:36:29"},
        ],
        "fields": [
            {"id": "_id", "type": "int4"},
            {"id": "permitnumber", "type": "text"},
            {"id": "issued_date", "type": "timestamp"},
        ],
    },
}


class _FakeTransport(httpx.Client):
    """Stub httpx.Client whose .get returns canned responses by URL substring."""

    def __init__(self, responses, **kwargs):
        self.responses = responses
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append((url, params))
        for matcher, response in self.responses:
            if matcher(url, params or {}):
                return response
        raise AssertionError(f"No canned response for {url} {params}")


@pytest.fixture
def client():
    return CkanClient(max_retries=2)


def _respond(payload, status_code=200):
    return httpx.Response(status_code=status_code, json=payload, request=httpx.Request("GET", "http://x"))


def _patch(monkeypatch, responses):
    def factory(**kwargs):
        return _FakeTransport(responses)
    monkeypatch.setattr(httpx, "Client", factory)
    return lambda: None


# ---------------------------------------------------------------- URI parsing


def test_parse_endpoint(client):
    base, res, params = client.parse_endpoint(PERMITS_URI)
    assert base == "https://data.boston.gov/api/3/action"
    assert res == "6ddcd912-32a0-43df-9908-63574f8c7e77"
    assert params == {}


def test_parse_endpoint_rejects_non_ckan_scheme(client):
    with pytest.raises(ValueError, match="ckan://"):
        client.parse_endpoint("https://data.boston.gov/dataset/x")


# ------------------------------------------------------------ where-clause translation


def test_parse_where_terms_equality_and_range():
    terms = _parse_where_terms("status = 'Open' AND issued_date > '2026-08-20T00:00:00'")
    assert terms == [("status", "=", "Open"), ("issued_date", ">", "2026-08-20T00:00:00")]


def test_parse_where_terms_passthrough_on_complex_sql():
    assert _parse_where_terms("issued_date IS NOT NULL") is None


def test_range_clause_routes_to_search_sql(client, monkeypatch):
    seen = {}

    def fake_request_json(url, params):
        seen["url"] = url
        seen["sql"] = params["sql"]
        return SQL_WATERMARK_RESULT

    monkeypatch.setattr(client, "_request_json", fake_request_json)
    records = client.fetch_records(
        PERMITS_URI,
        where_clause="issued_date > '2026-08-20T00:00:00'",
    )
    assert "/datastore_search_sql" in seen["url"]
    assert 'WHERE "issued_date" > \'2026-08-20T00:00:00\'' in seen["sql"]
    assert 'ORDER BY "_id"' in seen["sql"]
    assert len(records) == 2


def test_desc_order_by_quotes_column_not_direction(client, monkeypatch):
    """US-109: datastore_search_sql must not quote ``issued_date DESC`` as one
    identifier (Boston permits/311 409). The direction stays outside quotes."""
    seen = {}

    def fake_request_json(url, params):
        seen["sql"] = params["sql"]
        return SQL_WATERMARK_RESULT

    monkeypatch.setattr(client, "_request_json", fake_request_json)
    client.fetch_records(
        PERMITS_URI,
        where_clause="issued_date > '2026-08-20T00:00:00'",
        order_by="issued_date DESC",
    )
    assert 'ORDER BY "issued_date" DESC' in seen["sql"]


def test_quote_order_by_variants():
    assert _quote_order_by("issued_date DESC") == '"issued_date" DESC'
    assert _quote_order_by("issued_date") == '"issued_date"'
    assert _quote_order_by("issued_date ASC, recorded_date DESC") == (
        '"issued_date" ASC, "recorded_date" DESC'
    )
    assert _quote_order_by('"_id"') == '"_id"'
    assert _quote_order_by("") == '"_id"'


def test_equality_clause_uses_search_filters_param(client, monkeypatch):
    seen = {}

    def fake_request_json(url, params):
        seen["url"] = url
        seen["params"] = params
        return SEARCH_PAGE_1

    monkeypatch.setattr(client, "_request_json", fake_request_json)
    client.fetch_records(
        PERMITS_URI,
        where_clause="status = 'Open'",
        order_by=":id",
    )
    assert seen["url"].endswith("/datastore_search")
    assert json.loads(seen["params"]["filters"]) == {"status": "Open"}
    # Socrata-style ":id" is normalized to the CKAN _id key.
    assert seen["params"]["sort"] == "_id"


# ------------------------------------------------------------------- pagination


def test_offset_paging_across_pages_then_total_stop(client, monkeypatch):
    calls = []

    def fake_request_json(url, params):
        calls.append((url.split("/")[-1], dict(params)))
        if params.get("limit") == 0:
            return {"success": True, "result": {"records": [], "total": 3}}
        if params.get("offset", 0) == 0:
            return SEARCH_PAGE_1
        return SEARCH_PAGE_2

    monkeypatch.setattr(client, "_request_json", fake_request_json)
    batches = list(client.paginate(PERMITS_URI, batch_size=2))

    assert [len(b) for b in batches] == [2, 1]
    all_records = [r for b in batches for r in b]
    assert [r["_id"] for r in all_records] == [1, 2, 3]
    offsets = [p.get("offset") for _, p in calls if p.get("limit")]
    assert offsets == [0, 2]


def test_max_records_exact_stop(client, monkeypatch):
    def fake_request_json(url, params):
        if params.get("limit") == 0:
            return {"success": True, "result": {"records": [], "total": 3}}
        assert params["limit"] == 1, f"expected clamped limit=1, got {params}"
        return {
            "success": True,
            "result": {"records": [SEARCH_PAGE_1["result"]["records"][0]], "total": 3},
        }

    monkeypatch.setattr(client, "_request_json", fake_request_json)
    batches = list(client.paginate(PERMITS_URI, batch_size=5, max_records=1))
    assert sum(len(b) for b in batches) == 1


def test_paginate_normalizes_socrata_order_by(client, monkeypatch):
    def fake_request_json(url, params):
        if params.get("limit") == 0:
            return {"success": True, "result": {"records": [], "total": 0}}
        assert params.get("sort") == "_id"
        return {"success": True, "result": {"records": [], "total": 0}}

    monkeypatch.setattr(client, "_request_json", fake_request_json)
    assert list(client.paginate(PERMITS_URI, order_by=":id")) == []


# ------------------------------------------------------- non-datastore rejection


def test_non_datastore_resource_raises_readable_error(client, monkeypatch):
    def handler(request):
        return httpx.Response(200, json=NON_DATASTORE_BODY)

    transport = httpx.MockTransport(handler)

    class _PatchedClient(httpx.Client):
        def __init__(self, **kwargs):
            super().__init__(transport=transport)

    monkeypatch.setattr(httpx, "Client", _PatchedClient)
    with pytest.raises(NonDatastoreResourceError) as excinfo:
        client.paginate(
            "ckan://data.boston.gov/65032067-580e-4167-9a5c-94fa8ac2d9a7",
            max_records=10,
        ).__next__()
    msg = str(excinfo.value)
    assert "not datastore-active" in msg
    assert "file dump" in msg
    assert "no streaming path" in msg


# ------------------------------------------------------------------ year rollover


def test_resolve_resource_current_year(client):
    client.resource_by_year = {2025: "res-2025", 2026: "res-2026"}
    assert client.resolve_resource(date(2026, 8, 23)) == "res-2026"


def test_resolve_resource_falls_back_to_newest_past_year(client):
    client.resource_by_year = {2024: "res-2024", 2025: "res-2025"}
    assert client.resolve_resource(date(2026, 8, 23)) == "res-2025"


def test_resolve_resource_future_years_never_chosen(client):
    client.resource_by_year = {2027: "res-future"}
    assert client.resolve_resource(date(2026, 8, 23)) == "res-future"


# ---------------------------------------------------------------- retry/backoff


def test_retry_on_500_then_success(client, monkeypatch):
    attempts = []
    sleeps = []
    state = {"n": 0}

    class FlakyClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, params=None, headers=None):
            state["n"] += 1
            attempts.append(state["n"])
            if state["n"] < 2:
                return httpx.Response(500, request=httpx.Request("GET", url))
            return httpx.Response(
                200, json={"success": True, "result": {"records": []}}, request=httpx.Request("GET", url)
            )

    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(httpx, "Client", FlakyClient)
    records = client.fetch_records(PERMITS_URI)
    assert records == []
    assert attempts == [1, 2]
    assert sleeps == [1.0]


def test_gives_up_after_max_retries(client, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)

    class DeadClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, params=None, headers=None):
            raise httpx.ConnectError("no route")

    monkeypatch.setattr(httpx, "Client", DeadClient)
    with pytest.raises(CkanError, match="after 2 attempts"):
        client.fetch_records(PERMITS_URI)


# ------------------------------------------------------------- live (opt-in)


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("URBAN_LIVE_PROBE") != "1", reason="live probe disabled")
def test_live_permits_end_to_end(client):
    batches = list(client.paginate(PERMITS_URI, batch_size=5, max_records=10))
    rows = [r for b in batches for r in b]
    assert 0 < len(rows) <= 10
    sample = rows[0]
    assert "issued_date" in sample and "y_latitude" in sample and "x_longitude" in sample


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("URBAN_LIVE_PROBE") != "1", reason="live probe disabled")
def test_live_watermark_query(client):
    rows = client.fetch_records(
        PERMITS_URI,
        where_clause="issued_date > '2026-01-01T00:00:00'",
        limit=10,
    )
    assert len(rows) == 10
    assert all(r["issued_date"] >= "2026-01-01" for r in rows)
