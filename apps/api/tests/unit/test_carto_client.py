"""Unit tests for CartoClient (CARTO SQL API) against live-captured payload shapes.

Fixtures below were captured 2026-08-23 via real GET requests to
``https://phl.carto.com/api/v2/sql`` with ``LIMIT 2`` queries against the
permits, public_cases_fc, rtt_summary, and business_licenses tables, then
trimmed to representative fields.
"""

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.producers.carto_client import CartoClient

PERMITS_TABLE = "permits"
PHL_DOMAIN = "phl.carto.com"
CARTO_URI = f"carto://{PHL_DOMAIN}/{PERMITS_TABLE}"

# --- Live-captured fixture payloads (trimmed) -------------------------------

PERMITS_PAYLOAD = {
    "rows": [
        {
            "cartodb_id": 817,
            "permitnumber": "ZP-2021-009944",
            "permittype": "Zoning",
            "status": "Refused",
            "permitissuedate": None,
            "address": "247 N GROSS ST",
            "zip": "19139-1017",
            "geocode_x": 2670099.77752919,
            "geocode_y": 240753.50171251,
        },
        {
            "cartodb_id": 936,
            "permitnumber": "1054072",
            "permittype": "Zoning",
            "status": "Refused",
            "permitissuedate": None,
            "address": "4801 S 12TH ST",
            "zip": "19112",
            "geocode_x": 2688380.0,
            "geocode_y": 236510.0,
        },
    ],
    "time": 0.082,
    "fields": {
        "cartodb_id": {"type": "number", "pgtype": "int8"},
        "permitissuedate": {"type": "date", "pgtype": "timestamptz"},
    },
}

PUBLIC_CASES_FC_PAYLOAD = {
    "rows": [
        {
            "cartodb_id": 5908560,
            "service_request_id": 19901846,
            "status": "Open",
            "service_name": "Miscellaneous",
            "service_code": "SR-MI01",
            "requested_datetime": "2026-08-23T04:07:41Z",
            "lat": None,
            "lon": None,
        },
        {
            "cartodb_id": 5908559,
            "service_request_id": 19901825,
            "status": "Open",
            "requested_datetime": "2026-08-23T02:32:17Z",
            "lat": 39.952583,
            "lon": -75.165222,
        },
    ],
    "time": 0.597,
    "total_rows": 2,
}

RTT_SUMMARY_PAYLOAD = {
    "rows": [
        {
            "cartodb_id": 1,
            "document_id": 18,
            "document_type": "MORTGAGE",
            "display_date": "2024-06-26T18:22:03Z",
            "document_date": None,
            "street_address": "1928 S LAMBERT ST",
            "grantors": "DESIMONE JAMES",
        },
        {
            "cartodb_id": 2,
            "document_id": 2999998,
            "document_type": "DEED",
            "display_date": "1986-12-10T10:00:00Z",
            "document_date": None,
            "street_address": "109 PLEASANT ST",
        },
    ],
    "time": 0.11,
}

BUSINESS_LICENSES_PAYLOAD = {
    # Captured row demonstrates the year-3200 sentinel in mostrecentissuedate.
    "rows": [
        {
            "cartodb_id": 304425,
            "licensenum": 379773,
            "licensetype": "Motor Vehicle Repair / Fuel Dispensing",
            "licensestatus": "Inactive",
            "initialissuedate": "2006-08-02T14:11:00Z",
            "mostrecentissuedate": "3200-12-31T05:00:00Z",
            "expirationdate": "2009-12-31T05:00:00Z",
            "business_name": "JOHN EVANS (DBA: 3007 INC)",
        }
    ],
    "time": 0.1,
}


# --- Mock transport ----------------------------------------------------------


def _mock_response(payload):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def _patch_http(pages, status_codes=None):
    """Patch httpx.Client so successive GETs return `pages` in order.

    The last page repeats once exhausted. Returns (patcher, calls) where
    calls["urls"] / calls["params"] record every request made.
    """
    calls = {"urls": [], "params": [], "n": 0}

    def _get(url, params=None):
        idx = min(calls["n"], len(pages) - 1)
        code = (status_codes or [200] * len(pages))[min(calls["n"], len(status_codes or []) - 1)]
        calls["n"] += 1
        calls["urls"].append(url)
        calls["params"].append(params)
        if code != 200:
            resp = MagicMock()
            resp.status_code = code
            if code == 429:
                return resp
            error = httpx.HTTPStatusError(
                f"HTTP {code}", request=MagicMock(), response=resp
            )
            raise error
        resp = _mock_response(pages[idx])
        # Honour a trailing LIMIT clause so max_records clamping behaves like
        # the real SQL API (which truncates rows to the requested limit).
        q = (params or {}).get("q", "")
        if " LIMIT " in q and isinstance(pages[idx].get("rows"), list):
            limit = int(q.rsplit(" LIMIT ", 1)[1])
            resp.json.return_value = {
                **pages[idx],
                "rows": pages[idx]["rows"][:limit],
            }
        return resp

    client = MagicMock()
    client.__enter__.return_value.get.side_effect = _get
    client.__exit__.return_value = False
    return patch("httpx.Client", return_value=client), calls


def _page(rows):
    return {"rows": rows, "time": 0.01}


def _row(cartodb_id, issuedate=None):
    return {"cartodb_id": cartodb_id, "permitissuedate": issuedate}


class TestEndpointParsing:
    def test_carto_uri_parses_domain_and_table(self):
        base, table = CartoClient._parse_endpoint(CARTO_URI, None)
        assert base == f"https://{PHL_DOMAIN}/api/v2/sql"
        assert table == PERMITS_TABLE

    def test_full_sql_url_accepted(self):
        base, table = CartoClient._parse_endpoint(
            f"https://{PHL_DOMAIN}/api/v2/sql", "permits"
        )
        assert base == f"https://{PHL_DOMAIN}/api/v2/sql"
        assert table == "permits"

    def test_bare_domain_gets_https_sql_path(self):
        base, table = CartoClient._parse_endpoint(PHL_DOMAIN, "permits")
        assert base == f"https://{PHL_DOMAIN}/api/v2/sql"

    def test_missing_table_raises(self):
        with pytest.raises(ValueError, match="table name required"):
            CartoClient._parse_endpoint(PHL_DOMAIN, None)

    def test_conflicting_table_raises(self):
        with pytest.raises(ValueError, match="Conflicting tables"):
            CartoClient._parse_endpoint(CARTO_URI, "other_table")


class TestSentinelFilter:
    def test_emits_exact_filter_text_for_date_column(self):
        client = CartoClient()
        assert client._sentinel_filter("mostrecentissuedate", None) == (
            "mostrecentissuedate IS NOT NULL "
            "AND mostrecentissuedate >= '1900-01-01' "
            "AND mostrecentissuedate < '2101-01-01'"
        )

    def test_auto_detects_date_named_columns(self):
        client = CartoClient()
        assert client._sentinel_filter("requested_datetime", None) == (
            "requested_datetime IS NOT NULL "
            "AND requested_datetime >= '1900-01-01' "
            "AND requested_datetime < '2101-01-01'"
        )

    def test_non_date_columns_are_not_filtered_by_default(self):
        client = CartoClient()
        assert client._sentinel_filter("cartodb_id", None) is None

    def test_explicit_override_wins(self):
        client = CartoClient()
        assert client._sentinel_filter("cartodb_id", True) is not None
        assert client._sentinel_filter("document_date", False) is None

    def test_sentinel_filter_present_in_page_query(self):
        ctx, calls = _patch_http([PUBLIC_CASES_FC_PAYLOAD])
        with ctx:
            list(
                CartoClient().paginate(
                    CARTO_URI.replace(PERMITS_TABLE, "public_cases_fc"),
                    order_by="requested_datetime",
                    batch_size=10,
                )
            )
        q = calls["params"][0]["q"]
        assert "requested_datetime >= '1900-01-01'" in q
        assert "requested_datetime < '2101-01-01'" in q

    def test_sentinel_filter_excluded_when_disabled(self):
        ctx, calls = _patch_http([_page([])])
        with ctx:
            list(
                CartoClient().paginate(
                    CARTO_URI,
                    order_by="cartodb_id",
                    batch_size=10,
                )
            )
        assert ">= '1900-01-01'" not in calls["params"][0]["q"]


class TestKeysetPaging:
    def _three_pages(self, batch_size=2, **kwargs):
        pages = [
            _page([_row(1), _row(2)]),
            _page([_row(3), _row(4)]),
            _page([_row(5)]),
        ]
        ctx, calls = _patch_http(pages)
        with ctx:
            batches = list(
                CartoClient().paginate(
                    CARTO_URI, order_by="cartodb_id", batch_size=batch_size, **kwargs
                )
            )
        return batches, calls

    def test_continues_across_three_pages(self):
        batches, _ = self._three_pages()
        ids = [r["cartodb_id"] for b in batches for r in b]
        assert ids == [1, 2, 3, 4, 5]

    def test_each_page_carries_keyset_predicate_from_previous_tail(self):
        _, calls = self._three_pages()
        assert "(cartodb_id, cartodb_id) > ('2', '2')" in calls["params"][1]["q"]
        assert "(cartodb_id, cartodb_id) > ('4', '4')" in calls["params"][2]["q"]
        # First page has no keyset predicate.
        assert ") > (" not in calls["params"][0]["q"]

    def test_order_and_limit_in_query(self):
        _, calls = self._three_pages()
        q0 = calls["params"][0]["q"]
        assert f"FROM {PERMITS_TABLE}" in q0
        assert "ORDER BY cartodb_id ASC, cartodb_id ASC" in q0
        assert "LIMIT 2" in q0

    def test_descending_order_uses_descending_keyset_cursor(self):
        pages = [
            _page([_row(5, "2026-08-23"), _row(4, "2026-08-22")]),
            _page([_row(3, "2026-08-21")]),
        ]
        ctx, calls = _patch_http(pages)
        with ctx:
            list(
                CartoClient().paginate(
                    CARTO_URI,
                    order_by="permitissuedate DESC",
                    batch_size=2,
                )
            )
        assert "ORDER BY permitissuedate DESC, cartodb_id DESC" in calls["params"][0]["q"]
        assert "(permitissuedate, cartodb_id) < ('2026-08-22', '4')" in calls["params"][1]["q"]

    def test_stops_on_empty_result(self):
        ctx, _ = _patch_http([_page([])])
        with ctx:
            batches = list(
                CartoClient().paginate(CARTO_URI, order_by="cartodb_id")
            )
        assert batches == []

    def test_stops_on_short_final_page(self):
        batches, _ = self._three_pages(batch_size=10)
        assert len(batches) == 1

    def test_honours_max_records_exactly(self):
        batches, calls = self._three_pages(batch_size=2, max_records=3)
        ids = [r["cartodb_id"] for b in batches for r in b]
        assert ids == [1, 2, 3]
        # Second page was clamped to LIMIT 1, not 2.
        assert "LIMIT 1" in calls["params"][1]["q"]


class TestRowHandling:
    def test_yields_flat_row_dicts(self):
        ctx, _ = _patch_http([PUBLIC_CASES_FC_PAYLOAD])
        with ctx:
            batches = list(
                CartoClient().paginate(
                    "carto://phl.carto.com/public_cases_fc",
                    order_by="requested_datetime",
                    exclude_sentinel_dates=False,
                )
            )
        row = batches[0][0]
        assert isinstance(row, dict)
        assert row["service_request_id"] == 19901846
        assert "fields" not in row
        assert "time" not in row

    def test_malformed_rows_are_dropped(self):
        payload = {
            "rows": [_row(1), "not-a-dict", None, _row(2)],
        }
        ctx, _ = _patch_http([payload])
        with ctx:
            batches = list(
                CartoClient().paginate(CARTO_URI, order_by="cartodb_id")
            )
        assert [r["cartodb_id"] for b in batches for r in b] == [1, 2]

    def test_payload_without_rows_array_is_tolerated(self):
        ctx, _ = _patch_http([{"error": ["boom"]}])
        with ctx:
            batches = list(
                CartoClient().paginate(CARTO_URI, order_by="cartodb_id")
            )
        assert batches == []


class TestRetryAndBackoff:
    def test_retries_on_429_then_succeeds(self, monkeypatch):
        monkeypatch.setattr("src.producers.carto_client.time.sleep", lambda s: None)
        ctx, calls = _patch_http(
            [_page([_row(1)])], status_codes=[429, 200]
        )
        with ctx:
            batches = list(
                CartoClient().paginate(CARTO_URI, order_by="cartodb_id")
            )
        assert batches == [[_row(1)]]
        assert calls["n"] == 2

    def test_gives_up_after_max_retries_on_500(self, monkeypatch):
        monkeypatch.setattr("src.producers.carto_client.time.sleep", lambda s: None)
        ctx, _ = _patch_http([_page([])], status_codes=[500])
        with pytest.raises(RuntimeError, match="after"):
            with ctx:
                list(
                    CartoClient(max_retries=2).paginate(CARTO_URI, order_by="cartodb_id")
                )


class TestCapturedPayloadContract:
    """The embedded fixtures must keep their live-captured shape."""

    @pytest.mark.parametrize(
        "payload,min_keys",
        [
            (PERMITS_PAYLOAD, {"cartodb_id", "permitnumber", "permittype"}),
            (PUBLIC_CASES_FC_PAYLOAD, {"cartodb_id", "service_request_id", "requested_datetime"}),
            (RTT_SUMMARY_PAYLOAD, {"cartodb_id", "document_type", "document_date"}),
            (BUSINESS_LICENSES_PAYLOAD, {"cartodb_id", "licensenum", "mostrecentissuedate"}),
        ],
    )
    def test_fixture_shape(self, payload, min_keys):
        assert isinstance(payload["rows"], list)
        assert set(payload["rows"][0]) >= min_keys

    def test_business_licenses_sentinel_year_is_captured(self):
        date = BUSINESS_LICENSES_PAYLOAD["rows"][0]["mostrecentissuedate"]
        assert int(date[:4]) > 2100, "fixture must demonstrate the year-3200 sentinel"


class TestLiveProbe:
    """End-to-end pull against phl.carto.com. Opt-in only:

        URBAN_LIVE_PROBE=1 pytest tests/unit/test_carto_client.py -k live
    """

    @pytest.mark.skipif(
        os.environ.get("URBAN_LIVE_PROBE") != "1",
        reason="live probe disabled; set URBAN_LIVE_PROBE=1",
    )
    def test_live_permits_keyset_pull(self):
        rows = []
        for batch in CartoClient(max_retries=2).paginate(
            "carto://phl.carto.com/public_cases_fc",
            order_by="requested_datetime",
            batch_size=5,
            max_records=10,
        ):
            rows.extend(batch)
        assert 0 < len(rows) <= 10
        assert all("cartodb_id" in r for r in rows)
