from datetime import UTC, datetime

from scripts.validate_shadow_cycles import validate_cycles


def evidence(day: int, *, event: str = "schedule", status: str = "complete") -> dict:
    at = datetime(2026, 9, day, 3, tzinfo=UTC).isoformat()
    return {
        "cycle_id": f"cycle-{day}", "event": event,
        "scheduled_at": at if event == "schedule" else None,
        "started_at": at, "completed_at": at, "as_of": at,
        "status": status, "complete": status == "complete",
        "source_contract_status": "verified", "source_contract_hash": "a" * 64,
        "source_age_seconds": 3600, "acquisition_manifest_hash": "b" * 64,
        "feature_manifest_hash": "c" * 64, "feature_output_hash": "d" * 64,
        "checkpoint_before": "v1", "checkpoint_after": "v2",
        "query_bounds": {"lower": None, "upper": at},
        "independent_rebuild": {
            "input_manifest_hash": "b" * 64, "output_hash": "d" * 64,
            "dimensions": {"identity": "match", "counts": "match", "window_membership": "match", "affected_cells": "match"},
        },
        "provider_receipt": {
            "verified": True, "bucket": "shadow", "endpoint": "https://r2.example",
            "base_prefix": "shadow/", "probe_prefix": "shadow/probes/id/", "probe_id": "id",
            "created_at": at, "object_sha256": "f" * 64, "checkpoint_sha256": "1" * 64,
            "checks": {"absent_cas": "passed", "if_match_update": "passed", "stale_cas_conflict": "passed",
                       "immutable_overwrite_rejected": "passed", "immutable_integrity_read": "passed",
                       "two_client_absent_race": "passed", "fresh_client_restore": "passed"},
        },
        "metrics": {"rows": 1, "requests": 1, "bytes": 2, "storage_operations": 3, "duration_seconds": 4},
    }


def test_requires_seven_consecutive_scheduled_utc_cycles():
    cycles = [evidence(day) for day in range(1, 8)]
    result = validate_cycles(cycles, cadence_hours=24)
    assert result["qualified"] is True
    assert result["scheduled_successes"] == 7
    assert result["consecutive_scheduled_cycles"] == 7


def test_manual_run_does_not_count_or_break_scheduled_streak():
    cycles = [evidence(day) for day in range(1, 5)]
    cycles.insert(2, evidence(3, event="manual"))
    cycles.extend(evidence(day) for day in range(5, 8))
    result = validate_cycles(cycles, cadence_hours=24)
    assert result["qualified"] is True
    assert result["scheduled_successes"] == 7
    assert result["manual_cycles"] == 1


def test_failed_scheduled_cycle_resets_streak_and_missing_evidence_fails():
    cycles = [evidence(day) for day in range(1, 5)] + [evidence(5, status="failed")]
    cycles += [evidence(day) for day in range(6, 12)]
    del cycles[-1]["provider_receipt"]
    result = validate_cycles(cycles, cadence_hours=24)
    assert result["qualified"] is False
    assert result["consecutive_scheduled_cycles"] == 0
    assert any("provider_receipt" in reason for reason in result["failures"])


def test_missing_parity_or_stale_source_rejects_cycle():
    cycle = evidence(1)
    cycle["source_age_seconds"] = 90000
    cycle["independent_rebuild"]["output_hash"] = "e" * 64
    result = validate_cycles([cycle], cadence_hours=24)
    assert result["qualified"] is False
    assert any("source_age" in reason for reason in result["failures"])
    assert any("parity" in reason for reason in result["failures"])


def test_boolean_scheduled_flag_does_not_create_scheduled_evidence():
    cycle = evidence(1)
    cycle["event"] = None
    cycle["scheduled"] = True
    result = validate_cycles([cycle], cadence_hours=24)
    assert result["scheduled_cycles"] == 0
    assert result["manual_cycles"] == 1
    assert result["qualified"] is False


def test_cycle_requires_same_input_and_matching_independent_output():
    cycle = evidence(1)
    cycle["independent_rebuild"]["input_manifest_hash"] = "e" * 64
    result = validate_cycles([cycle], cadence_hours=24)
    assert any("committed input" in reason for reason in result["failures"])


def test_duplicate_scheduled_day_and_invalid_numeric_evidence_reject():
    first, duplicate = evidence(1), evidence(1)
    duplicate["metrics"]["bytes"] = float("nan")
    result = validate_cycles([first, duplicate], cadence_hours=24)
    assert result["qualified"] is False
    assert any("multiple scheduled records" in reason for reason in result["failures"])
    assert any("metrics" in reason for reason in result["failures"])
