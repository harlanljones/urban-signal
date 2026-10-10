"""Publish a content-addressed snapshot plan.

Objects are immutable ``objects/<sha256>`` values. The release manifest is
``releases/<snapshot_id>``. ``snapshot/current`` is written last. Workers KV is
not a transaction: a pointer update is a logical commit, not proof that every
edge can already read every object.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Protocol

from src.export.publication import PublicationPlan

POINTER_KEY = "snapshot/current"
MAX_CHUNK_ENTRIES = 1000
MAX_CHUNK_BYTES = 10 * 1024 * 1024
MAX_OBJECT_BYTES = 20 * 1024 * 1024
_RETRY_SLEEPS = (0.01, 0.02, 0.04)


class PublishError(RuntimeError):
    """Publication stopped before the pointer moved."""


class SnapshotStore(Protocol):
    """Minimal KV surface used by the publisher."""

    def get(self, key: str) -> bytes | None: ...

    def put_many(self, entries: list[tuple[str, bytes]]) -> int: ...

    def put(self, key: str, value: bytes) -> None: ...


@dataclass(frozen=True)
class PublishReceipt:
    """Acknowledged writes. These counts are not a global KV propagation proof."""

    snapshot_id: str
    object_writes: int
    object_bytes: int
    manifest_writes: int
    pointer_writes: int
    reused_objects: int
    uploaded_objects: int


def _is_versioned(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _read_pointer(store: SnapshotStore) -> dict | None:
    raw = store.get(POINTER_KEY)
    if raw is None:
        return None
    try:
        pointer = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise PublishError("snapshot/current is not valid JSON") from exc
    if not isinstance(pointer, dict) or not isinstance(pointer.get("current"), str):
        raise PublishError("snapshot/current has no current id")
    return pointer


def _chunks(items: list[tuple[str, bytes]]) -> list[list[tuple[str, bytes]]]:
    chunks: list[list[tuple[str, bytes]]] = []
    current: list[tuple[str, bytes]] = []
    current_bytes = 0
    for key, value in items:
        size = len(value)
        if size > MAX_OBJECT_BYTES:
            raise PublishError(f"{key} is {size} bytes, over the {MAX_OBJECT_BYTES}-byte object budget")
        if size > MAX_CHUNK_BYTES:
            if current:
                chunks.append(current)
                current = []
                current_bytes = 0
            chunks.append([(key, value)])
            continue
        overflows = current and (
            len(current) >= MAX_CHUNK_ENTRIES or current_bytes + size > MAX_CHUNK_BYTES
        )
        if overflows:
            chunks.append(current)
            current = []
            current_bytes = 0
        current.append((key, value))
        current_bytes += size
    if current:
        chunks.append(current)
    return chunks


def _put_retry(store: SnapshotStore, key: str, value: bytes) -> None:
    last: Exception | None = None
    for attempt in range(3):
        try:
            store.put(key, value)
            return
        except (OSError, TimeoutError, PublishError) as exc:
            last = exc
            if attempt == 2:
                break
            time.sleep(_RETRY_SLEEPS[attempt])
    raise PublishError(f"write of {key} failed after 3 attempts") from last


def _put_many_retry(store: SnapshotStore, entries: list[tuple[str, bytes]]) -> int:
    last: Exception | None = None
    for attempt in range(3):
        try:
            acknowledged = store.put_many(entries)
        except (OSError, TimeoutError, PublishError) as exc:
            last = exc
            if attempt == 2:
                break
            time.sleep(_RETRY_SLEEPS[attempt])
            continue
        if acknowledged != len(entries):
            raise PublishError(
                f"store acknowledged {acknowledged} of {len(entries)} object writes"
            )
        return acknowledged
    raise PublishError("object upload failed after 3 attempts") from last


def _object_present(store: SnapshotStore, digest: str, payload: bytes) -> bool:
    remote = store.get(f"objects/{digest}")
    return remote == payload


def publish(
    plan: PublicationPlan,
    store: SnapshotStore,
    *,
    expected_current: str | None,
) -> PublishReceipt:
    """Upload missing objects, then the manifest, then the pointer.

    A versioned remote pointer must equal ``expected_current``. A stage-B
    pointer (not a 64-hex id) may be replaced by the first versioned release.
    Reuse candidates that are absent remotely are uploaded again.
    """
    remote = _read_pointer(store)
    remote_current = None if remote is None else remote.get("current")
    if _is_versioned(remote_current) and remote_current != expected_current:
        raise PublishError(
            f"snapshot/current is {remote_current}, expected parent {expected_current}"
        )
    if expected_current is not None and _is_versioned(expected_current) and remote_current != expected_current:
        raise PublishError(
            f"snapshot/current is {remote_current}, expected parent {expected_current}"
        )

    pending: list[tuple[str, bytes]] = []
    reused = 0
    for digest, payload in sorted(plan.objects.items()):
        if _object_present(store, digest, payload):
            reused += 1
            continue
        pending.append((f"objects/{digest}", payload))

    object_writes = 0
    object_bytes = 0
    for chunk in _chunks(pending):
        object_writes += _put_many_retry(store, chunk)
        object_bytes += sum(len(value) for _, value in chunk)

    manifest_bytes = json.dumps(plan.manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    _put_retry(store, f"releases/{plan.snapshot_id}", manifest_bytes)
    previous = remote_current if _is_versioned(remote_current) else None
    pointer = {
        "schema_version": 1,
        "current": plan.snapshot_id,
        "previous": previous,
    }
    _put_retry(store, POINTER_KEY, json.dumps(pointer, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return PublishReceipt(
        snapshot_id=plan.snapshot_id,
        object_writes=object_writes,
        object_bytes=object_bytes,
        manifest_writes=1,
        pointer_writes=1,
        reused_objects=reused,
        uploaded_objects=len(pending),
    )


def bulk_entries(plan: PublicationPlan, *, previous: str | None = None) -> list[dict[str, str]]:
    """KV bulk rows for one plan. Legacy logical keys are not included."""
    rows = [
        {"key": f"objects/{digest}", "value": payload.decode("utf-8")}
        for digest, payload in sorted(plan.objects.items())
    ]
    rows.append(
        {
            "key": f"releases/{plan.snapshot_id}",
            "value": json.dumps(plan.manifest, sort_keys=True, separators=(",", ":")),
        }
    )
    pointer = {"schema_version": 1, "current": plan.snapshot_id, "previous": previous}
    rows.append(
        {
            "key": POINTER_KEY,
            "value": json.dumps(pointer, sort_keys=True, separators=(",", ":")),
        }
    )
    return rows
