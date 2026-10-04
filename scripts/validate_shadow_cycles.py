#!/usr/bin/env python3
"""Validate seven consecutive daily UTC shadow cycles and their evidence."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_PROBE_CHECKS = (
    "absent_cas",
    "if_match_update",
    "stale_cas_conflict",
    "immutable_overwrite_rejected",
    "immutable_integrity_read",
    "two_client_absent_race",
    "fresh_client_restore",
)
_REQUIRED_PARITY_DIMENSIONS = (
    "identity",
    "counts",
    "window_membership",
    "affected_cells",
)


def _timestamp(value: Any, field: str, failures: list[str]) -> datetime | None:
    if not isinstance(value, str):
        failures.append(f"{field} missing")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        failures.append(f"{field} invalid")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        failures.append(f"{field} must be UTC")
        return None
    return parsed.astimezone(timezone.utc)


def _hash(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def _measure(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def _cycle_failures(cycle: dict[str, Any], max_source_age_seconds: int) -> list[str]:
    failures: list[str] = []
    started = _timestamp(cycle.get("started_at"), "started_at", failures)
    completed = _timestamp(cycle.get("completed_at"), "completed_at", failures)
    as_of = _timestamp(cycle.get("as_of"), "as_of", failures)
    if started and completed and completed < started:
        failures.append("completed_at precedes started_at")
    if completed and as_of and as_of > completed:
        failures.append("as_of is after completed_at")
    if cycle.get("status") != "complete" or cycle.get("complete") is not True:
        failures.append("cycle incomplete")
    if cycle.get("source_contract_status") != "verified":
        failures.append("source contract is not verified")
    for field in (
        "source_contract_hash",
        "acquisition_manifest_hash",
        "feature_manifest_hash",
        "feature_output_hash",
    ):
        if not _hash(cycle.get(field)):
            failures.append(f"{field} missing or invalid")
    age = cycle.get("source_age_seconds")
    if not _measure(age) or age > max_source_age_seconds:
        failures.append("source_age exceeds configured cadence or is missing")
    if not cycle.get("checkpoint_before") or not cycle.get("checkpoint_after"):
        failures.append("checkpoint lineage missing")
    if not isinstance(cycle.get("query_bounds"), dict) or not cycle["query_bounds"]:
        failures.append("query_bounds missing")

    rebuild = cycle.get("independent_rebuild")
    if not isinstance(rebuild, dict):
        failures.append("independent parity missing")
    else:
        if rebuild.get("input_manifest_hash") != cycle.get("acquisition_manifest_hash"):
            failures.append(
                "independent parity did not use the cycle's committed input"
            )
        if rebuild.get("output_hash") != cycle.get("feature_output_hash"):
            failures.append("independent parity output hash does not match the cycle")
        if not _hash(rebuild.get("output_hash")):
            failures.append("independent parity output hash missing or invalid")
        dimensions = rebuild.get("dimensions")
        if not isinstance(dimensions, dict) or any(
            dimensions.get(key) != "match" for key in _REQUIRED_PARITY_DIMENSIONS
        ):
            failures.append("independent parity dimensions missing or mismatched")

    receipt = cycle.get("provider_receipt")
    if not isinstance(receipt, dict) or receipt.get("verified") is not True:
        failures.append("provider_receipt missing or unverified")
    else:
        for field in ("object_sha256", "checkpoint_sha256"):
            if not _hash(receipt.get(field)):
                failures.append(f"provider_receipt {field} missing or invalid")
        if not all(
            receipt.get(field)
            for field in (
                "bucket",
                "endpoint",
                "base_prefix",
                "probe_prefix",
                "probe_id",
            )
        ):
            failures.append("provider_receipt target or identity missing")
        checks = receipt.get("checks")
        if not isinstance(checks, dict) or any(
            checks.get(key) != "passed" for key in _REQUIRED_PROBE_CHECKS
        ):
            failures.append("provider_receipt conditional-write checks missing")
        receipt_at = _timestamp(
            receipt.get("created_at"), "provider_receipt.created_at", failures
        )
        if (
            receipt_at
            and started
            and (receipt_at > started or started - receipt_at > timedelta(hours=24))
        ):
            failures.append("provider_receipt is stale or from the future")

    metrics = cycle.get("metrics")
    names = ("rows", "requests", "bytes", "storage_operations", "duration_seconds")
    if not isinstance(metrics, dict) or any(
        not _measure(metrics.get(name)) for name in names
    ):
        failures.append("measured cost and usage metrics missing or invalid")
    return failures


def validate_cycles(
    cycles: Iterable[dict[str, Any]],
    *,
    cadence_hours: int,
    max_source_age_seconds: int = 86400,
) -> dict[str, Any]:
    if cadence_hours != 24:
        raise ValueError("M4 requires one scheduled cycle every 24 UTC hours")
    if max_source_age_seconds <= 0:
        raise ValueError("max_source_age_seconds must be positive")
    scheduled: list[tuple[datetime | None, list[str]]] = []
    manual_count = 0
    input_failures: list[str] = []
    for index, cycle in enumerate(cycles):
        if not isinstance(cycle, dict):
            input_failures.append(f"cycle[{index}] is not an object")
            continue
        if cycle.get("event") != "schedule":
            manual_count += 1
            continue
        failures = _cycle_failures(cycle, max_source_age_seconds)
        at = _timestamp(cycle.get("scheduled_at"), "scheduled_at", failures)
        scheduled.append((at, failures))

    scheduled.sort(
        key=lambda item: item[0] or datetime.min.replace(tzinfo=timezone.utc)
    )
    all_failures = list(input_failures)
    by_date: dict[str, int] = {}
    for at, _ in scheduled:
        if at:
            by_date[at.date().isoformat()] = by_date.get(at.date().isoformat(), 0) + 1
    duplicate_dates = {day for day, count in by_date.items() if count != 1}
    if duplicate_dates:
        all_failures.append(
            "multiple scheduled records exist for a UTC date: "
            + ", ".join(sorted(duplicate_dates))
        )

    streak = max_streak = 0
    prior: datetime | None = None
    for at, failures in scheduled:
        if at and at.date().isoformat() in duplicate_dates:
            failures.append("scheduled UTC date is duplicated")
        if failures or at is None:
            streak = 0
            prior = None
            continue
        if prior is not None and at - prior != timedelta(hours=24):
            streak = 0
        streak += 1
        prior = at
        max_streak = max(max_streak, streak)
    for index, (_, failures) in enumerate(scheduled):
        all_failures.extend(
            f"scheduled cycle {index + 1}: {reason}" for reason in failures
        )
    if len(scheduled) < 7:
        all_failures.append(
            f"only {len(scheduled)} scheduled cycles supplied; seven required"
        )
    if streak < 7:
        all_failures.append(
            f"latest consecutive scheduled streak is {streak}; seven required"
        )
    return {
        "qualified": len(scheduled) >= 7 and streak >= 7 and not duplicate_dates,
        "scheduled_cycles": len(scheduled),
        "scheduled_successes": sum(
            not failures and at is not None for at, failures in scheduled
        ),
        "manual_cycles": manual_count,
        "consecutive_scheduled_cycles": streak,
        "max_consecutive_scheduled_cycles": max_streak,
        "cadence_hours": cadence_hours,
        "max_source_age_seconds": max_source_age_seconds,
        "failures": all_failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "evidence", type=Path, help="JSON list of recorded cycle evidence"
    )
    parser.add_argument(
        "--cadence-hours",
        type=int,
        required=True,
        help="M4 accepts a daily 24-hour schedule",
    )
    parser.add_argument(
        "--max-source-age-seconds",
        type=int,
        required=True,
        help="source freshness limit from M1 cadence",
    )
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.evidence.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise TypeError("evidence file must contain a JSON list")
        report = validate_cycles(
            payload,
            cadence_hours=args.cadence_hours,
            max_source_age_seconds=args.max_source_age_seconds,
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"qualified": False, "failures": [str(exc)]}, indent=2))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["qualified"] else 1


if __name__ == "__main__":
    sys.exit(main())
