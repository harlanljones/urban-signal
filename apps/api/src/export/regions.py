"""Region generations and the promotion gate (ADR-0010 Stage C, HX-C1).

A *region* is the unit of build, promotion and failure isolation. Each build writes
immutable, content-addressed chunk objects and a generation manifest; a separate
promote step atomically swaps the region's ``current`` pointer. A region that fails
verification keeps its previous generation (INV-3).

Layout under ``out_dir`` mirrors the KV keys the publisher uploads::

    objects/{sha256}                      chunk bytes (shared, immutable)
    regions/{region_id}/gen/{generation}.json   RegionManifest
    regions/{region_id}/current.json            RegionPointer

``promote_region`` verifies what ``national_builder.promote_national`` only asserts today
(its ``checksum_verified`` flag is hard-coded ``True`` and it never compares a golden
count): chunk bytes are re-hashed at promote time, the cell count must equal the plan's
golden count exactly, and a sudden drop in measured cells is refused as a feed outage.
This module is transport-free: filesystem in, filesystem out.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

# A region whose measured cells fall below this share of the previous generation's is a
# feed outage, not a coverage change (spec §4.4; proposed, calibrate with real runs).
MEASURED_FLOOR_RATIO = 0.8
BUILDER_REVISION = "1"


class PromotionRefused(ValueError):
    """Raised when a staged generation fails verification. The pointer is untouched."""

    def __init__(self, region_id: str, reasons: list[str]) -> None:
        self.region_id = region_id
        self.reasons = reasons
        super().__init__(f"refusing to promote {region_id}: {reasons}")


@dataclass(frozen=True)
class RegionManifest:
    region_id: str
    generation: str  # sha256 over sorted (chunk_key, chunk_sha256)
    input_hash: str
    plan_hash: str
    golden_count: int
    measured_count: int
    rank_epoch: str | None
    chunks: dict[str, dict[str, object]]  # chunk_key -> {"sha256": str, "bytes": int}
    built_at: str
    builder_revision: str


@dataclass(frozen=True)
class RegionPointer:
    current: str
    previous: str | None
    promoted_at: str
    golden_count: int


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def region_input_hash(
    *,
    plan_hash: str,
    model_id: str,
    builder_revision: str = BUILDER_REVISION,
    feed_watermarks: Mapping[str, str] | None = None,
    context_sha: str | None = None,
    national_sha: str | None = None,
) -> str:
    """Fingerprint of everything that determines a region's output (spec §4.3).

    Equal hashes mean the previous generation is still correct and the region can be
    skipped. Feed watermarks are sorted so dict order never changes the hash.
    """
    payload = {
        "plan_hash": plan_hash,
        "model_id": model_id,
        "builder_revision": builder_revision,
        "feed_watermarks": sorted((feed_watermarks or {}).items()),
        "context_sha": context_sha,
        "national_sha": national_sha,
    }
    return _sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())


def _gen_path(out_dir: Path, region_id: str, generation: str) -> Path:
    return out_dir / "regions" / region_id / "gen" / f"{generation}.json"


def _pointer_path(out_dir: Path, region_id: str) -> Path:
    return out_dir / "regions" / region_id / "current.json"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def stage_region(
    out_dir: Path,
    *,
    region_id: str,
    chunks: Mapping[str, bytes],
    input_hash: str,
    plan_hash: str,
    golden_count: int,
    measured_count: int,
    rank_epoch: str | None = None,
    builder_revision: str = BUILDER_REVISION,
    built_at: str | None = None,
) -> RegionManifest:
    """Write chunk objects and the generation manifest. Does not touch ``current``.

    Order is fixed — objects, then manifest — so a crash here leaves an unreferenced
    generation, never a pointer at a partial one.
    """
    specs: dict[str, dict[str, object]] = {}
    for key in sorted(chunks):
        data = chunks[key]
        digest = _sha256(data)
        specs[key] = {"sha256": digest, "bytes": len(data)}
        object_path = out_dir / "objects" / digest
        if not object_path.exists():
            _atomic_write(object_path, data)
    generation = _sha256(json.dumps(sorted((k, v["sha256"]) for k, v in specs.items())).encode())
    manifest = RegionManifest(
        region_id=region_id,
        generation=generation,
        input_hash=input_hash,
        plan_hash=plan_hash,
        golden_count=golden_count,
        measured_count=measured_count,
        rank_epoch=rank_epoch,
        chunks=specs,
        built_at=built_at or datetime.now(UTC).isoformat(),
        builder_revision=builder_revision,
    )
    _atomic_write(_gen_path(out_dir, region_id, generation), json.dumps(asdict(manifest), sort_keys=True).encode())
    return manifest


def load_manifest(out_dir: Path, region_id: str, generation: str) -> RegionManifest:
    return RegionManifest(**json.loads(_gen_path(out_dir, region_id, generation).read_text()))


def load_pointer(out_dir: Path, region_id: str) -> RegionPointer | None:
    path = _pointer_path(out_dir, region_id)
    return RegionPointer(**json.loads(path.read_text())) if path.exists() else None


def _verify_chunks(out_dir: Path, manifest: RegionManifest) -> list[str]:
    problems = []
    for key, spec in sorted(manifest.chunks.items()):
        path = out_dir / "objects" / str(spec["sha256"])
        if not path.exists():
            problems.append(f"chunk {key}: object {spec['sha256']} is missing")
            continue
        data = path.read_bytes()
        if _sha256(data) != spec["sha256"]:
            problems.append(f"chunk {key}: bytes do not match recorded sha256")
        elif len(data) != spec["bytes"]:
            problems.append(f"chunk {key}: size {len(data)} != recorded {spec['bytes']}")
    return problems


def promote_region(
    out_dir: Path,
    region_id: str,
    generation: str,
    *,
    expected_golden: int,
    expected_plan_hash: str,
    rebaseline: str | None = None,
    now: str | None = None,
) -> RegionPointer:
    """Verify a staged generation and atomically make it ``current``.

    Refuses (raising :class:`PromotionRefused`, pointer untouched) when:

    1. any chunk is missing or its bytes/size differ from the manifest;
    2. the manifest's golden count differs from ``expected_golden`` (INV-2);
    3. the manifest was built from a different plan than ``expected_plan_hash``;
    4. no cell is measured;
    5. measured cells fell below ``MEASURED_FLOOR_RATIO`` of the previous generation;
    6. the golden count changed without a plan change (drift), or changed with a plan
       change but no ``rebaseline`` reason (an unannounced coverage edit).
    """
    manifest = load_manifest(out_dir, region_id, generation)
    reasons = _verify_chunks(out_dir, manifest)
    if manifest.golden_count != expected_golden:
        reasons.append(f"golden count {manifest.golden_count} != expected {expected_golden}")
    if manifest.plan_hash != expected_plan_hash:
        reasons.append("manifest was built from a different coverage plan than expected")
    if manifest.measured_count < 1:
        reasons.append("no measured cells")

    previous_pointer = load_pointer(out_dir, region_id)
    if previous_pointer is not None and previous_pointer.current != generation:
        previous = load_manifest(out_dir, region_id, previous_pointer.current)
        if manifest.measured_count < MEASURED_FLOOR_RATIO * previous.measured_count:
            reasons.append(
                f"measured cells fell {previous.measured_count} -> {manifest.measured_count} "
                f"(below {MEASURED_FLOOR_RATIO:.0%}); treated as a feed outage"
            )
        if manifest.golden_count != previous.golden_count:
            if manifest.plan_hash == previous.plan_hash:
                reasons.append(
                    f"golden count drifted {previous.golden_count} -> {manifest.golden_count} without a plan change"
                )
            elif not rebaseline:
                reasons.append(
                    f"golden count changed {previous.golden_count} -> {manifest.golden_count}; pass a rebaseline reason"
                )
    if reasons:
        raise PromotionRefused(region_id, reasons)

    same = previous_pointer is not None and previous_pointer.current == generation
    pointer = RegionPointer(
        current=generation,
        previous=previous_pointer.previous if same and previous_pointer else (previous_pointer.current if previous_pointer else None),
        promoted_at=now or datetime.now(UTC).isoformat(),
        golden_count=manifest.golden_count,
    )
    _atomic_write(_pointer_path(out_dir, region_id), json.dumps(asdict(pointer), sort_keys=True).encode())
    return pointer
