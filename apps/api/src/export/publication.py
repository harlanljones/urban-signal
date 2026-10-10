"""Report-only content-addressed publication plans.

Live legacy KV keys stay untouched. A plan hashes canonical payloads, records
which objects a later publisher may reuse, and never claims those objects exist
remotely.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

from src.models.quantile_lgbm import FEATURE_COLUMNS

FEATURE_SCHEMA_VERSION = hashlib.sha256("\n".join(FEATURE_COLUMNS).encode("utf-8")).hexdigest()[:16]


class NonFiniteNumber(ValueError):
    """Canonical snapshot JSON rejects NaN and infinities."""


@dataclass(frozen=True)
class PublicationPlan:
    """One immutable release plan. ``reuse_candidates`` still need a remote check."""

    snapshot_id: str
    manifest: dict[str, Any]
    objects: dict[str, bytes]
    reuse_candidates: tuple[str, ...]


def canonical_bytes(payload: Any) -> bytes:
    """Sorted-key compact JSON. Array order is preserved. Non-finite numbers fail."""
    _reject_non_finite(payload)
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except ValueError as exc:
        raise NonFiniteNumber("canonical JSON rejected a non-finite number") from exc
    return encoded.encode("utf-8")


def _reject_non_finite(payload: Any) -> None:
    if isinstance(payload, float):
        if not math.isfinite(payload):
            raise NonFiniteNumber("canonical JSON rejected a non-finite number")
        return
    if isinstance(payload, dict):
        for value in payload.values():
            _reject_non_finite(value)
        return
    if isinstance(payload, list):
        for value in payload:
            _reject_non_finite(value)


def _zero_latency(payload: Any) -> None:
    """Versioned payloads keep the latency field and pin it at the documented sentinel."""
    if isinstance(payload, dict):
        if "inference_latency_ms" in payload:
            payload["inference_latency_ms"] = 0.0
        for value in payload.values():
            _zero_latency(value)
        return
    if isinstance(payload, list):
        for value in payload:
            _zero_latency(value)


def _planned_payload(raw: str) -> Any:
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise ValueError("publication entry is not JSON") from exc
    _zero_latency(payload)
    return payload


def _object_hashes(manifest: dict[str, Any] | None) -> set[str]:
    if not manifest:
        return set()
    keys = manifest.get("keys")
    if not isinstance(keys, dict):
        return set()
    found: set[str] = set()
    for spec in keys.values():
        if isinstance(spec, dict) and isinstance(spec.get("sha256"), str):
            found.add(spec["sha256"])
    return found


def plan_publication(
    entries: list[dict[str, str]],
    previous: dict[str, Any] | None,
    metadata: dict[str, Any],
) -> PublicationPlan:
    """Hash logical payloads into a release manifest.

    The publication manifest is not one of its own ``keys``. Product objects,
    including the product ``manifest`` entry, are. ``inference_latency_ms`` is
    forced to ``0.0`` only in this plan; callers keep their original strings.
    """
    objects: dict[str, bytes] = {}
    keys: dict[str, dict[str, Any]] = {}
    for entry in entries:
        logical = entry["key"]
        payload = _planned_payload(entry["value"])
        raw = canonical_bytes(payload)
        digest = hashlib.sha256(raw).hexdigest()
        objects[digest] = raw
        keys[logical] = {"sha256": digest, "bytes": len(raw)}

    body = {
        "as_of": metadata["as_of"],
        "feature_schema_version": metadata.get("feature_schema_version", FEATURE_SCHEMA_VERSION),
        "keys": keys,
        "model_id": metadata["model_id"],
        "parent": None if previous is None else previous.get("snapshot_id"),
        "schema_version": 1,
        "source_revisions": metadata.get("source_revisions", {}),
    }
    snapshot_id = hashlib.sha256(canonical_bytes(body)).hexdigest()
    manifest = {"snapshot_id": snapshot_id, **body}
    previous_hashes = _object_hashes(previous)
    reuse = tuple(sorted(digest for digest in objects if digest in previous_hashes))
    return PublicationPlan(
        snapshot_id=snapshot_id,
        manifest=manifest,
        objects=objects,
        reuse_candidates=reuse,
    )
