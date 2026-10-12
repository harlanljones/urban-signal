"""Report-only content-addressed publication plans.

Live legacy KV keys stay untouched. A plan hashes canonical payloads, records
which objects a later publisher may reuse, and never claims those objects exist
remotely.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
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
    regions: dict[str, str] = field(default_factory=dict)
    region_manifests: dict[str, dict[str, Any]] = field(default_factory=dict)
    region_pointers: dict[str, dict[str, Any]] = field(default_factory=dict)


def canonical_bytes(payload: Any) -> bytes:
    """Sorted-key compact JSON. Array order is preserved. Non-finite numbers fail."""
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


def _zero_latency(payload: dict[str, Any]) -> dict[str, Any]:
    """Decode hook: pin latency as each JSON object is materialized."""
    if "inference_latency_ms" in payload:
        payload["inference_latency_ms"] = 0.0
    return payload


def _planned_payload(raw: str) -> Any:
    try:
        payload = json.loads(raw, object_hook=_zero_latency)
    except ValueError as exc:
        raise ValueError("publication entry is not JSON") from exc
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
    canonical_by_value: dict[str, tuple[str, bytes]] = {}
    for entry in entries:
        logical = entry["key"]
        value = entry["value"]
        cached = canonical_by_value.get(value)
        if cached is None:
            payload = _planned_payload(value)
            raw = canonical_bytes(payload)
            digest = hashlib.sha256(raw).hexdigest()
            objects[digest] = raw
            canonical_by_value[value] = (digest, raw)
        else:
            digest, raw = cached
        keys[logical] = {"sha256": digest, "bytes": len(raw)}

    regions_map: dict[str, str] = {}
    region_manifests: dict[str, dict[str, Any]] = {}
    region_pointers: dict[str, dict[str, Any]] = {}
    raw_regions = metadata.get("regions")
    if isinstance(raw_regions, dict):
        for rid, rdata in sorted(raw_regions.items()):
            if isinstance(rdata, str):
                regions_map[rid] = rdata
            elif isinstance(rdata, dict):
                gen = rdata.get("generation")
                if isinstance(gen, str):
                    regions_map[rid] = gen
                    region_manifests[f"regions/{rid}/gen/{gen}"] = rdata
                    prev_gen = rdata.get("previous_generation")
                    region_pointers[f"regions/{rid}/current"] = {
                        "current": gen,
                        "previous": prev_gen,
                        "golden_count": rdata.get("golden_count", 0),
                        "promoted_at": rdata.get("built_at", metadata.get("as_of", "")),
                    }

    body = {
        "as_of": metadata["as_of"],
        "feature_schema_version": metadata.get("feature_schema_version", FEATURE_SCHEMA_VERSION),
        "keys": keys,
        "model_id": metadata["model_id"],
        "parent": None if previous is None else previous.get("snapshot_id"),
        "schema_version": 1,
        "source_revisions": metadata.get("source_revisions", {}),
    }
    if regions_map:
        projected = canonical_bytes({**body, "regions": regions_map})
        if len(projected) > 8 * 1024 * 1024:
            region_index_raw = canonical_bytes(regions_map)
            region_index_digest = hashlib.sha256(region_index_raw).hexdigest()
            objects[region_index_digest] = region_index_raw
            keys["manifest/regions"] = {"sha256": region_index_digest, "bytes": len(region_index_raw)}
            body["region_index_key"] = "manifest/regions"
        else:
            body["regions"] = regions_map

    snapshot_id = hashlib.sha256(canonical_bytes(body)).hexdigest()
    manifest = {"snapshot_id": snapshot_id, **body}
    previous_hashes = _object_hashes(previous)
    reuse = tuple(sorted(digest for digest in objects if digest in previous_hashes))
    return PublicationPlan(
        snapshot_id=snapshot_id,
        manifest=manifest,
        objects=objects,
        reuse_candidates=reuse,
        regions=regions_map,
        region_manifests=region_manifests,
        region_pointers=region_pointers,
    )
