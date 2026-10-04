from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from src.ingestion.source import (
    SocrataPermitSource,
    SourceContract,
    SourceNotReady,
    SourceProtocolError,
)

FIELDS = [":id", ":updated_at", "permit_si_no", "job__", "issuance_date", "borough", "gis_latitude", "gis_longitude"]


def contract_data(**overrides):
    data = {
        "source_id": "nyc/permits",
        "endpoint": "https://data.cityofnewyork.us/resource/ipu4-2q9a.json",
        "dataset_id": "ipu4-2q9a",
        "version": "1",
        "fields": FIELDS,
        "identity_fields": ["permit_si_no"],
        "source_row_id_field": ":id",
        "event_time_field": "issuance_date",
        "update_time_field": ":updated_at",
        "page_size_max": 1000,
        "query_contract": {
            "pagination": "keyset",
            "ordering_fields": [":updated_at", ":id"],
            "timestamp_precision": "millisecond",
            "upper_bound_inclusive": True,
            "status": "verified",
        },
        "guarantees": {
            name: {"status": "verified", "evidence": "test evidence"}
            for name in (
                "identity_unique_nonnull",
                "row_id_persistent",
                "update_timestamp_semantics",
                "deterministic_keyset_pagination",
                "bounded_snapshot_consistency",
                "complete_reconciliation",
                "replacement_detection",
                "request_limits_known",
            )
        },
    }
    data.update(overrides)
    return data


def row(row_id, updated, permit):
    return {":id": row_id, ":updated_at": updated, "permit_si_no": permit}


def test_contract_rejects_unverified_required_guarantees():
    data = contract_data()
    data["guarantees"]["identity_unique_nonnull"] = {"status": "unverified", "evidence": "small sample"}
    contract = SourceContract.from_dict(data)
    with pytest.raises(SourceNotReady, match="identity_unique_nonnull"):
        contract.assert_ready()


def test_contract_serialization_round_trip():
    original = SourceContract.from_dict(contract_data())
    assert SourceContract.from_dict(original.to_dict()).to_dict() == original.to_dict()


def test_contract_rejects_unsafe_projection_and_identity():
    with pytest.raises(ValueError, match="project"):
        SourceContract.from_dict(contract_data(fields=["*"]))
    with pytest.raises(ValueError, match="identity"):
        SourceContract.from_dict(contract_data(identity_fields=["job__"]))


def test_equal_timestamp_boundary_continues_by_row_id_without_skips():
    responses = [
        [row("a", "2026-01-01T00:00:00.000Z", "p1"), row("b", "2026-01-01T00:00:00.000Z", "p2")],
        [row("c", "2026-01-01T00:00:00.000Z", "p3")],
    ]
    requests = []

    def handler(request):
        requests.append(dict(request.url.params))
        return httpx.Response(200, json=responses.pop(0))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    pages = list(SocrataPermitSource(SourceContract.from_dict(contract_data()), client, page_size=2).iter_pages())
    assert [r["permit_si_no"] for p in pages for r in p.records] == ["p1", "p2", "p3"]
    assert pages[-1].exhausted and pages[-1].complete
    assert requests[1]["$where"] == "(:updated_at > '2026-01-01T00:00:00.000Z' OR (:updated_at = '2026-01-01T00:00:00.000Z' AND :id > 'b'))"
    assert requests[0]["$select"] == ",".join(FIELDS)
    assert "*" not in requests[0]["$select"]


def test_cross_page_identity_collision_fails_closed():
    responses = [[row("a", "2026-01-01T00:00:00.000Z", "same")], [row("b", "2026-01-02T00:00:00.000Z", "same")]]
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=responses.pop(0))))
    source = SocrataPermitSource(SourceContract.from_dict(contract_data()), client, page_size=1)
    with pytest.raises(SourceProtocolError, match="identity collision"):
        list(source.iter_pages())


def test_retries_are_bounded_and_then_succeed():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(429 if attempts < 3 else 200, json=[])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    pages = list(SocrataPermitSource(SourceContract.from_dict(contract_data()), client, max_attempts=3).iter_pages())
    assert attempts == 3
    assert len(pages) == 1 and pages[0].complete


def test_retry_exhaustion_and_missing_identity_do_not_claim_complete():
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(503)))
    with pytest.raises(SourceProtocolError, match="after 2 attempts"):
        list(SocrataPermitSource(SourceContract.from_dict(contract_data()), client, max_attempts=2).iter_pages())
    client.close()
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[{":id": "r"}])))
    with pytest.raises(SourceProtocolError, match="missing identity"):
        list(SocrataPermitSource(SourceContract.from_dict(contract_data()), client).iter_pages())


def test_upper_bound_is_applied_and_short_page_is_exhaustion_evidence():
    seen = []
    client = httpx.Client(transport=httpx.MockTransport(lambda req: (seen.append(dict(req.url.params)) or httpx.Response(200, json=[]))))
    pages = list(SocrataPermitSource(SourceContract.from_dict(contract_data()), client).iter_pages(upper_bound="2026-01-02T00:00:00.000Z"))
    assert ":updated_at <= '2026-01-02T00:00:00.000Z'" in seen[0]["$where"]
    assert pages[0].complete and pages[0].row_count == 0


def test_full_page_requires_a_followup_to_prove_exhaustion():
    responses = [[row("a", "2026-01-01T00:00:00.000Z", "p")], []]
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=responses.pop(0))))
    pages = list(SocrataPermitSource(SourceContract.from_dict(contract_data()), client, page_size=1).iter_pages())
    assert len(pages) == 2
    assert pages[0].next_cursor is not None and not pages[0].complete
    assert pages[1].exhausted and pages[1].complete
    assert pages[1].reconciliation_complete


def test_unready_contract_does_not_issue_network_request():
    data = contract_data()
    data["guarantees"]["complete_reconciliation"] = {"status": "unverified", "evidence": "not proven"}
    calls = []
    client = httpx.Client(transport=httpx.MockTransport(lambda req: (calls.append(req) or httpx.Response(200, json=[]))))
    source = SocrataPermitSource(SourceContract.from_dict(data), client)
    with pytest.raises(SourceNotReady):
        list(source.iter_pages())
    assert calls == []


def test_adapter_discards_unprojected_response_columns():
    record = row("a", "2026-01-01T00:00:00.000Z", "p")
    record["owner_phone"] = "555-0100"
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[record])))
    page = next(SocrataPermitSource(SourceContract.from_dict(contract_data()), client).iter_pages())
    assert "owner_phone" not in page.records[0]


def test_contract_rejects_coercive_or_unsafe_contract_values():
    with pytest.raises(ValueError, match="fields must be a list"):
        SourceContract.from_dict(contract_data(fields=":id"))
    with pytest.raises(ValueError, match="source_id must be a non-empty string"):
        SourceContract.from_dict(contract_data(source_id=None))
    with pytest.raises(ValueError, match="safe SoQL field"):
        SourceContract.from_dict(contract_data(fields=[*FIELDS[:-2], "gis_latitude OR 1=1", "gis_longitude"]))
    with pytest.raises(ValueError, match="positive integer"):
        SourceContract.from_dict(contract_data(page_size_max=True))


def test_query_contract_status_also_gates_readiness():
    data = contract_data(query_contract={**contract_data()["query_contract"], "status": "unverified"})
    contract = SourceContract.from_dict(data)
    with pytest.raises(SourceNotReady, match="query_contract"):
        contract.assert_ready()


def test_live_contract_preserves_actual_gis_fields_and_remains_unready():
    path = Path(__file__).parents[2] / ".." / ".." / "docs" / "research" / "nyc-permit-source-contract.json"
    data = json.loads(path.resolve().read_text())
    contract = SourceContract.from_dict(data)
    assert "gis_latitude" in contract.fields and "gis_longitude" in contract.fields
    with pytest.raises(SourceNotReady):
        contract.assert_ready()


def test_adapter_rejects_rows_above_upper_bound_even_if_server_ignores_filter():
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[row("a", "2026-01-03T00:00:00.000Z", "p")])))
    source = SocrataPermitSource(SourceContract.from_dict(contract_data()), client)
    with pytest.raises(SourceProtocolError, match="exceeds declared upper bound"):
        list(source.iter_pages(upper_bound="2026-01-02T00:00:00.000Z"))


def test_adapter_rejects_response_larger_than_requested_page():
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[
        row("a", "2026-01-01T00:00:00.000Z", "p1"), row("b", "2026-01-02T00:00:00.000Z", "p2")
    ])))
    source = SocrataPermitSource(SourceContract.from_dict(contract_data()), client, page_size=1)
    with pytest.raises(SourceProtocolError, match="exceeded requested page size"):
        list(source.iter_pages())


@pytest.mark.parametrize("timestamp", ["2026-01-01", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00.000+00:00", "2026-01-01T00:00:00.00Z", "2026-99-99T00:00:00.000Z"])
def test_update_timestamps_must_match_declared_utc_millisecond_format(timestamp):
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[row("a", timestamp, "p")])))
    with pytest.raises(SourceProtocolError, match="UTC millisecond timestamp"):
        list(SocrataPermitSource(SourceContract.from_dict(contract_data()), client).iter_pages())


def test_cursor_and_upper_bound_must_be_canonical_utc_timestamps():
    source = SocrataPermitSource(SourceContract.from_dict(contract_data()), httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[]))))
    with pytest.raises(ValueError, match="UTC millisecond timestamp"):
        list(source.iter_pages(upper_bound="2026-01-02"))
    with pytest.raises(ValueError, match="UTC millisecond timestamp"):
        list(source.iter_pages(cursor={":updated_at": "2026-01-02", ":id": "a"}))


def test_terminal_empty_page_retains_last_emitted_cursor():
    responses = [[row("a", "2026-01-01T00:00:00.000Z", "p")], []]
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=responses.pop(0))))
    pages = list(SocrataPermitSource(SourceContract.from_dict(contract_data()), client, page_size=1).iter_pages())
    assert pages[-1].records == []
    assert pages[-1].next_cursor == {":updated_at": "2026-01-01T00:00:00.000Z", ":id": "a"}


def test_initial_empty_page_retains_supplied_cursor():
    cursor = {":updated_at": "2026-01-01T00:00:00.000Z", ":id": "checkpoint-row"}
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[])))
    page = next(SocrataPermitSource(SourceContract.from_dict(contract_data()), client).iter_pages(cursor=cursor))
    assert page.next_cursor == cursor


def test_initial_empty_page_without_cursor_has_no_cursor():
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[])))
    page = next(SocrataPermitSource(SourceContract.from_dict(contract_data()), client).iter_pages())
    assert page.next_cursor is None
