"""Crash-safe commit, replay, normalization and permit-only feature aggregation."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime, timedelta
from datetime import time as day_time
from typing import Any

import h3

from src.ingestion.store import CheckpointConflict, IntegrityError

RAW_PREFIX = "raw/pages/"
MANIFEST_PREFIX = "manifests/"
FEATURE_PREFIX = "features/"
ACQUISITION_CHECKPOINT = "checkpoints/acquisition.json"
FEATURE_CHECKPOINT = "checkpoints/features.json"
_FEATURE_WINDOWS = (60, 90, 180, 360)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CHECKPOINT_UNSET = object()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _as_utc(value: datetime | str | date) -> datetime:
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, day_time.min, tzinfo=UTC)
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValueError("event time is empty")
        try:
            value = datetime.fromisoformat(raw)
        except ValueError:
            try:
                value = datetime.strptime(raw, "%m/%d/%Y").replace(tzinfo=UTC)
            except ValueError as exc:
                raise ValueError(f"invalid event time {raw!r}") from exc
    if not isinstance(value, datetime):
        raise TypeError("event time must be a date or datetime")
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _fixed_as_of(value: datetime | str) -> datetime:
    """Require a caller-supplied UTC instant with an explicit offset."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("as_of must be a timezone-aware datetime") from exc
    else:
        raise TypeError("as_of must be a timezone-aware datetime")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("as_of must be a timezone-aware datetime")
    return parsed.astimezone(UTC)


def _contract_fields(contract: Any, field: str, default: Any = None) -> Any:
    return getattr(contract, field, default)


def _scope(contract: Any, record: Mapping[str, Any]) -> tuple[str, str]:
    city = str(_contract_fields(contract, "city_id", "nyc"))
    feed = str(_contract_fields(contract, "feed_id", "permits"))
    # A projected row may carry scope columns, but it cannot move data outside
    # the contract scope selected by the caller.
    if record.get("city_id") not in (None, "", city) or record.get("feed_id") not in (
        None,
        "",
        feed,
    ):
        raise ValueError("record city/feed is outside the validated source scope")
    return city, feed


def _coordinates(record: Mapping[str, Any]) -> tuple[float | None, float | None]:
    lat_value = record.get("gis_latitude", record.get("latitude", record.get("lat")))
    lon_value = record.get(
        "gis_longitude", record.get("longitude", record.get("lon", record.get("lng")))
    )
    location = record.get("location")
    if isinstance(location, Mapping):
        lat_value = location.get("latitude", lat_value)
        lon_value = location.get("longitude", lon_value)
    if lat_value in (None, "") and lon_value in (None, ""):
        return None, None
    try:
        lat, lon = float(lat_value), float(lon_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid coordinate pair") from exc
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("coordinate outside valid latitude/longitude bounds")
    return lat, lon


def _jsonable_records(records: Mapping[tuple[str, ...], Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(records[key]) for key in sorted(records)]


def _record_key(contract: Any, row: Mapping[str, Any]) -> tuple[str, ...]:
    identity_fields = tuple(_contract_fields(contract, "identity_fields", ()))
    if not identity_fields:
        raise ValueError("validated contract must declare identity_fields")
    city, feed = _scope(contract, row)
    missing = [field for field in identity_fields if row.get(field) in (None, "")]
    if missing:
        raise ValueError("missing identity fields: " + ", ".join(missing))
    identity: list[str] = []
    for field in identity_fields:
        value = row[field]
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise TypeError(f"identity field {field!r} must be a non-empty string or integer")
        normalized = str(value).strip()
        if not normalized:
            raise ValueError(f"identity field {field!r} cannot be empty")
        identity.append(normalized)
    return (city, feed, *identity)


def normalize_records(
    records: Iterable[Mapping[str, Any]],
    contract: Any,
    as_of: datetime | str,
    prior_records: Mapping[tuple[str, ...], Mapping[str, Any]] | None = None,
    *,
    reconciliation_complete: bool = False,
    acquired_at: datetime | str | None = None,
) -> dict[tuple[str, ...], dict[str, Any]]:
    """Validate rows and content-hash upsert them under scoped contract identity."""
    fixed_as_of = _fixed_as_of(as_of)
    acquired_time = _fixed_as_of(acquired_at) if acquired_at is not None else datetime.now(UTC)
    identity_fields = tuple(_contract_fields(contract, "identity_fields", ()))
    event_field = str(_contract_fields(contract, "event_time_field", ""))
    update_field = str(_contract_fields(contract, "update_time_field", ""))
    row_id_field = str(_contract_fields(contract, "source_row_id_field", ""))
    if not identity_fields or not event_field or not update_field:
        raise ValueError("contract identity and time fields are required")
    state = (
        {}
        if reconciliation_complete
        else {key: dict(value) for key, value in (prior_records or {}).items()}
    )
    seen: dict[tuple[str, ...], str] = {}
    for raw in records:
        if not isinstance(raw, Mapping):
            raise TypeError("source record must be an object")
        row = dict(raw)
        projected_fields = _contract_fields(contract, "fields", None)
        if projected_fields is not None:
            unexpected = set(row) - set(projected_fields)
            if unexpected:
                raise ValueError(
                    "record contains fields outside the source contract schema: "
                    + ", ".join(sorted(unexpected))
                )
        key = _record_key(contract, row)
        event_time = _as_utc(row.get(event_field))
        update_time = _as_utc(row.get(update_field))
        latitude, longitude = _coordinates(row)
        content = _canonical(row)
        content_hash = _digest(content)
        if key in seen:
            if seen[key] != content_hash:
                raise ValueError(f"duplicate identity has conflicting rows: {key}")
            continue
        seen[key] = content_hash
        prior = state.get(key)
        if prior is not None:
            prior_updated = _as_utc(prior["source_update_time"])
            if update_time < prior_updated:
                continue
            if update_time == prior_updated and content_hash != prior["content_hash"]:
                raise ValueError(f"ambiguous update timestamp for identity: {key}")
            if content_hash == prior["content_hash"]:
                continue
        h3_index = h3.latlng_to_cell(latitude, longitude, 9) if latitude is not None else None
        normalized = {
            "city_id": key[0],
            "feed_id": key[1],
            "identity": list(key[2:]),
            "source_id": str(_contract_fields(contract, "source_id", "")),
            "dataset_id": str(_contract_fields(contract, "dataset_id", "")),
            "source_version": str(_contract_fields(contract, "version", "")),
            "source_row_id": row.get(row_id_field) if row_id_field else None,
            "source_event_time": event_time.isoformat(),
            "source_update_time": update_time.isoformat(),
            "acquired_at": acquired_time.isoformat(),
            "as_of": fixed_as_of.isoformat(),
            "content_hash": content_hash,
            "parser_version": "permit-normalizer-v1",
            "latitude": latitude,
            "longitude": longitude,
            "h3": h3_index,
            "validation_status": "valid" if h3_index else "valid_missing_geometry",
            "cost_status": "missing",
            "estimated_cost": None,
            "source_record": row,
        }
        state[key] = normalized
    return state


def aggregate_features(
    records: Mapping[tuple[str, ...], Mapping[str, Any]], as_of: datetime | str
) -> dict[str, dict[str, Any]]:
    """Build permit count and velocity baseline at a single inclusive UTC as-of."""
    fixed_as_of = _fixed_as_of(as_of)
    grouped: dict[str, list[datetime]] = defaultdict(list)
    for record in records.values():
        cell = record.get("h3")
        if cell:
            event_time = _as_utc(record["source_event_time"])
            if event_time <= fixed_as_of:
                grouped[str(cell)].append(event_time)
    output: dict[str, dict[str, Any]] = {}
    for cell, event_times in grouped.items():
        counts = {
            days: sum(
                fixed_as_of - timedelta(days=days) <= event <= fixed_as_of for event in event_times
            )
            for days in _FEATURE_WINDOWS
        }
        baseline = counts[180] / 3.0 if counts[180] > 0 else 0.1
        velocity_60 = (counts[60] - baseline) / baseline
        output[cell] = {
            **{f"permits_{days}d": counts[days] for days in _FEATURE_WINDOWS},
            "permits_60d_velocity": round(velocity_60, 4),
            "cost_status": "unavailable_missing_cost_data",
            "estimated_cost": None,
            "predictions": None,
            "alerts_enabled": False,
            "as_of": fixed_as_of.isoformat(),
        }
    return dict(sorted(output.items()))


def _contract_identity(contract: Any) -> dict[str, Any]:
    semantic_fields = (
        "endpoint",
        "dataset_id",
        "version",
        "fields",
        "identity_fields",
        "source_row_id_field",
        "event_time_field",
        "update_time_field",
    )
    semantic_contract = {
        field: _contract_fields(contract, field, None) for field in semantic_fields
    }
    to_dict = _contract_fields(contract, "to_dict", None)
    if callable(to_dict):
        semantic_contract["declared_contract"] = to_dict()
    return {
        "source_id": str(_contract_fields(contract, "source_id", "")),
        "dataset_id": str(_contract_fields(contract, "dataset_id", "")),
        "source_version": str(_contract_fields(contract, "version", "")),
        "identity_fields": list(_contract_fields(contract, "identity_fields", ())),
        "city_id": str(_contract_fields(contract, "city_id", "nyc")),
        "feed_id": str(_contract_fields(contract, "feed_id", "permits")),
        "contract_hash": _digest(_canonical(semantic_contract)),
    }


def _read_manifest(
    store: Any, key: str, expected_hash: str, expected_contract: dict[str, Any]
) -> dict[str, Any]:
    if not _SHA256.fullmatch(expected_hash):
        raise IntegrityError("manifest lineage has invalid sha256")
    body = store.get_verified(key, expected_hash)
    try:
        manifest = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("manifest is not valid JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("contract") != expected_contract:
        raise IntegrityError("manifest contract does not match requested source")
    return manifest


def _lineage(
    store: Any, contract: Any, *, checkpoint_override: Any = _CHECKPOINT_UNSET
) -> list[tuple[str, str, dict[str, Any]]]:
    if checkpoint_override is _CHECKPOINT_UNSET:
        checkpoint, _ = store.read_checkpoint(ACQUISITION_CHECKPOINT)
    else:
        checkpoint = checkpoint_override
    if checkpoint is None:
        return []
    expected_contract = _contract_identity(contract)
    key, digest = checkpoint.get("manifest_key"), checkpoint.get("manifest_hash")
    if not isinstance(key, str) or not isinstance(digest, str):
        raise IntegrityError("acquisition checkpoint has no committed manifest identity")
    chain: list[tuple[str, str, dict[str, Any]]] = []
    visited: set[str] = set()
    while key is not None:
        if key in visited:
            raise IntegrityError("manifest lineage contains a cycle")
        visited.add(key)
        manifest = _read_manifest(store, key, digest, expected_contract)
        chain.append((key, digest, manifest))
        parent = manifest.get("parent")
        if parent is None:
            break
        if not isinstance(parent, dict):
            raise IntegrityError("manifest parent reference is malformed")
        key, digest = parent.get("manifest_key"), parent.get("manifest_hash")
        if not isinstance(key, str) or not isinstance(digest, str):
            raise IntegrityError("manifest parent is missing its hash-linked identity")
    chain.reverse()
    return chain


def _restore_state(
    store: Any, contract: Any, *, checkpoint_override: Any = _CHECKPOINT_UNSET
) -> dict[tuple[str, ...], dict[str, Any]]:
    state: dict[tuple[str, ...], dict[str, Any]] = {}
    for _key, _manifest_hash, manifest in _lineage(
        store, contract, checkpoint_override=checkpoint_override
    ):
        if not manifest.get("complete"):
            raise IntegrityError("committed lineage contains an incomplete run")
        if not isinstance(manifest.get("pages"), list):
            raise IntegrityError("manifest page list is missing")
        rows: list[dict[str, Any]] = []
        for page in manifest["pages"]:
            if (
                not isinstance(page, dict)
                or not isinstance(page.get("key"), str)
                or not isinstance(page.get("sha256"), str)
            ):
                raise IntegrityError("manifest page reference is malformed")
            page_bytes = store.get_verified(page["key"], page["sha256"])
            try:
                page_rows = json.loads(page_bytes)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise IntegrityError("page is not valid JSON") from exc
            if not isinstance(page_rows, list) or len(page_rows) != page.get("row_count"):
                raise IntegrityError("page row count is inconsistent")
            if not all(isinstance(row, dict) for row in page_rows):
                raise IntegrityError("page contains a non-object row")
            rows.extend(page_rows)
        if manifest.get("reconciliation_complete"):
            state = {}
        state = normalize_records(
            rows, contract, manifest["as_of"], state, acquired_at=manifest["acquired_at"]
        )
    return state


def commit_run(
    store: Any,
    contract: Any,
    records: Iterable[Mapping[str, Any]],
    as_of: datetime | str,
    *,
    cursor: Mapping[str, Any] | None = None,
    complete: bool = False,
    reconciliation: bool = False,
    full_scope: bool = False,
    query_bounds: Mapping[str, Any] | None = None,
    metrics: Mapping[str, Any] | None = None,
    run_id: str | None = None,
    input_mode: str = "local_fixture",
    acquired_at: datetime | str | None = None,
) -> dict[str, Any]:
    """Durably commit one fully acquired projected batch, then publish features."""
    if input_mode not in {"local_fixture", "live"}:
        raise ValueError("input_mode must be local_fixture or live")
    if not complete:
        raise ValueError("incomplete acquisition cannot be committed")
    if reconciliation and not full_scope:
        raise ValueError("reconciliation requires an explicitly complete full scope")
    fixed_as_of = _fixed_as_of(as_of)
    acquired_time = _fixed_as_of(acquired_at) if acquired_at is not None else datetime.now(UTC)
    started = time.monotonic()
    old_checkpoint, old_version = store.read_checkpoint(ACQUISITION_CHECKPOINT)
    materialized = [dict(row) for row in records]
    # Pin restoration to the checkpoint version that this run will conditionally replace.
    # A concurrent writer after this read therefore causes CAS failure, never lost updates.
    prior = _restore_state(store, contract, checkpoint_override=old_checkpoint)
    next_state = normalize_records(
        materialized,
        contract,
        fixed_as_of,
        prior,
        reconciliation_complete=reconciliation,
        acquired_at=acquired_time,
    )
    page_bytes = _canonical(materialized)
    page_hash = _digest(page_bytes)
    page_key = f"{RAW_PREFIX}{page_hash}.json"
    request_count = 0
    store.put_immutable(page_key, page_bytes, page_hash)
    request_count += 1
    request_count += 1
    parent = None
    if old_checkpoint is not None:
        parent = {
            "manifest_key": old_checkpoint.get("manifest_key"),
            "manifest_hash": old_checkpoint.get("manifest_hash"),
        }
        if not all(parent.values()):
            raise IntegrityError("current acquisition checkpoint is malformed")
    manifest_body = {
        "schema_version": "shadow-run-v1",
        "contract": _contract_identity(contract),
        "run_id": run_id,
        "input_mode": input_mode,
        "as_of": fixed_as_of.isoformat(),
        "acquired_at": acquired_time.isoformat(),
        "complete": True,
        "reconciliation_complete": bool(reconciliation and full_scope),
        "query_bounds": dict(query_bounds or {}),
        "cursor": dict(cursor or {}),
        "parent": parent,
        "pages": [
            {
                "key": page_key,
                "sha256": page_hash,
                "byte_count": len(page_bytes),
                "row_count": len(materialized),
            }
        ],
        "row_count": len(materialized),
        "record_count": len(next_state),
        "metrics": dict(metrics or {}),
    }
    manifest_bytes = _canonical(manifest_body)
    manifest_hash = _digest(manifest_bytes)
    manifest_key = f"{MANIFEST_PREFIX}{manifest_hash}.json"
    store.put_immutable(manifest_key, manifest_bytes, manifest_hash)
    request_count += 1
    acquisition_body = {
        "manifest_key": manifest_key,
        "manifest_hash": manifest_hash,
        "cursor": dict(cursor or {}),
        "generation": int((old_checkpoint or {}).get("generation", 0)) + 1,
        "source_id": manifest_body["contract"]["source_id"],
        "dataset_id": manifest_body["contract"]["dataset_id"],
        "source_version": manifest_body["contract"]["source_version"],
        "complete": True,
        "as_of": fixed_as_of.isoformat(),
    }
    store.compare_and_swap_checkpoint(ACQUISITION_CHECKPOINT, old_version, acquisition_body)
    request_count += 1

    # Acquisition stays committed if feature generation fails; this separate
    # pointer can be rebuilt from the immutable manifests later.
    features_started = time.monotonic()
    features = aggregate_features(next_state, fixed_as_of)
    feature_body = {
        "schema_version": "shadow-features-v1",
        "manifest_key": manifest_key,
        "manifest_hash": manifest_hash,
        "source_manifest_hash": manifest_hash,
        "as_of": fixed_as_of.isoformat(),
        "record_count": len(next_state),
        "features": features,
        "missing_geometry_count": sum(record["h3"] is None for record in next_state.values()),
        "cost_status": "unavailable_missing_cost_data",
        "predictions": None,
        "alerts_enabled": False,
    }
    feature_bytes = _canonical(feature_body)
    feature_hash = _digest(feature_bytes)
    feature_key = f"{FEATURE_PREFIX}{feature_hash}.json"
    store.put_immutable(feature_key, feature_bytes, feature_hash)
    request_count += 1
    current_acquisition, _ = store.read_checkpoint(ACQUISITION_CHECKPOINT)
    request_count += 1
    if current_acquisition != acquisition_body:
        raise CheckpointConflict("acquisition head changed before feature pointer publication")
    previous_features, feature_version = store.read_checkpoint(FEATURE_CHECKPOINT)
    request_count += 1
    generation = acquisition_body["generation"]
    previous_generation = int((previous_features or {}).get("generation", 0))
    if previous_generation >= generation:
        raise CheckpointConflict("a newer or equal-generation feature pointer already exists")
    feature_pointer = {
        "manifest_key": feature_key,
        "manifest_hash": feature_hash,
        "source_manifest_key": manifest_key,
        "source_manifest_hash": manifest_hash,
        "as_of": fixed_as_of.isoformat(),
        "acquired_at": acquired_time.isoformat(),
        "generation": generation,
        "complete": True,
    }
    store.compare_and_swap_checkpoint(FEATURE_CHECKPOINT, feature_version, feature_pointer)
    request_count += 1
    latest_acquisition, _ = store.read_checkpoint(ACQUISITION_CHECKPOINT)
    request_count += 1
    if latest_acquisition != acquisition_body:
        raise CheckpointConflict("acquisition head changed during feature pointer publication")
    elapsed = time.monotonic() - started
    update_times = [_as_utc(record["source_update_time"]) for record in next_state.values()]
    event_times = [_as_utc(record["source_event_time"]) for record in next_state.values()]
    receipt_metrics = {
        **dict(metrics or {}),
        "storage_requests": None,
        "storage_operations": request_count,
        "storage_bytes_written": len(page_bytes) + len(manifest_bytes) + len(feature_bytes),
        "duration_seconds": elapsed,
        "feature_duration_seconds": time.monotonic() - features_started,
        "feature_as_of": fixed_as_of.isoformat(),
        "newest_source_update_time": max(update_times).isoformat() if update_times else None,
        "event_time_coverage_start": min(event_times).isoformat() if event_times else None,
        "event_time_coverage_end": max(event_times).isoformat() if event_times else None,
    }
    return {
        "manifest_key": manifest_key,
        "manifest_hash": manifest_hash,
        "feature_manifest_key": feature_key,
        "feature_manifest_hash": feature_hash,
        "records": _jsonable_records(next_state),
        "record_count": len(next_state),
        "features": features,
        "feature_cells": len(features),
        "as_of": fixed_as_of.isoformat(),
        "acquired_at": acquired_time.isoformat(),
        "complete": True,
        "input_mode": input_mode,
        "metrics": receipt_metrics,
    }


def replay_committed(
    store: Any, contract: Any, as_of: datetime | str | None = None
) -> dict[str, Any]:
    """Verify and restore committed history without contacting a changing source."""
    started = time.monotonic()
    checkpoint, _ = store.read_checkpoint(ACQUISITION_CHECKPOINT)
    chain = _lineage(store, contract, checkpoint_override=checkpoint)
    if not chain:
        return {
            "records": {},
            "record_count": 0,
            "features": {},
            "feature_cells": 0,
            "as_of": _fixed_as_of(as_of).isoformat() if as_of is not None else None,
            "complete": False,
            "manifest_key": None,
            "manifest_hash": None,
            "metrics": {"replay_runs": 0, "duration_seconds": time.monotonic() - started},
        }
    state = _restore_state(store, contract, checkpoint_override=checkpoint)
    fixed_as_of = _fixed_as_of(as_of) if as_of is not None else _as_utc(chain[-1][2]["as_of"])
    # Keep future history replayable; aggregation alone excludes future events.
    features = aggregate_features(state, fixed_as_of)
    manifest_key, manifest_hash, manifest = chain[-1]
    feature_manifest_key = None
    feature_manifest_hash = None
    feature_pointer_current = False
    feature_checkpoint, _ = store.read_checkpoint(FEATURE_CHECKPOINT)
    if (
        feature_checkpoint
        and feature_checkpoint.get("source_manifest_hash") == manifest_hash
        and feature_checkpoint.get("as_of") == fixed_as_of.isoformat()
    ):
        candidate_key = feature_checkpoint.get("manifest_key")
        candidate_hash = feature_checkpoint.get("manifest_hash")
        if isinstance(candidate_key, str) and isinstance(candidate_hash, str):
            feature_bytes = store.get_verified(candidate_key, candidate_hash)
            try:
                feature_manifest = json.loads(feature_bytes)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise IntegrityError("feature manifest is not valid JSON") from exc
            if feature_manifest.get("source_manifest_hash") != manifest_hash:
                raise IntegrityError("feature manifest points at different source lineage")
            features = feature_manifest["features"]
            feature_manifest_key, feature_manifest_hash = candidate_key, candidate_hash
            feature_pointer_current = True
    return {
        "manifest_key": manifest_key,
        "manifest_hash": manifest_hash,
        "feature_manifest_key": feature_manifest_key,
        "feature_manifest_hash": feature_manifest_hash,
        "records": _jsonable_records(state),
        "record_count": len(state),
        "features": features,
        "feature_cells": len(features),
        "as_of": fixed_as_of.isoformat(),
        "complete": bool(manifest.get("complete")),
        "feature_pointer_current": feature_pointer_current,
        "input_mode": manifest.get("input_mode", "unknown"),
        "metrics": {
            "replay_runs": len(chain),
            "replay_pages": sum(len(item[2].get("pages", [])) for item in chain),
            "duration_seconds": time.monotonic() - started,
        },
    }
