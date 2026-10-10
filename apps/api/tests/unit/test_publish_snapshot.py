"""Versioned publication writes the pointer last and reuploads missing objects."""

from __future__ import annotations

import json

import pytest

from src.export.publication import plan_publication
from src.export.publish import (
    MAX_CHUNK_BYTES,
    MAX_CHUNK_ENTRIES,
    POINTER_KEY,
    PublishError,
    bulk_entries,
    publish,
)


def _plan(entries: list[dict[str, str]], **metadata: object):
    meta = {
        "as_of": "2026-10-10",
        "feature_schema_version": "features-v1",
        "model_id": "synthetic-default",
        "source_revisions": {},
    }
    meta.update(metadata)
    return plan_publication(entries, None, meta)


def _entry(key: str, payload: dict) -> dict[str, str]:
    return {"key": key, "value": json.dumps(payload)}


class MemoryStore:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}
        self.fail_after: int | None = None
        self.failures_left = 0
        self.puts = 0
        self.chunk_sizes: list[int] = []

    def get(self, key: str) -> bytes | None:
        return self.data.get(key)

    def put_many(self, entries: list[tuple[str, bytes]]) -> int:
        self.chunk_sizes.append(len(entries))
        self._advance(len(entries))
        for key, value in entries:
            self.data[key] = value
        return len(entries)

    def put(self, key: str, value: bytes) -> None:
        self._advance(1)
        self.data[key] = value

    def _advance(self, count: int) -> None:
        for _ in range(count):
            self.puts += 1
            if self.failures_left:
                self.failures_left -= 1
                raise TimeoutError("injected")
            if self.fail_after is not None and self.puts > self.fail_after:
                raise TimeoutError("injected")


def _pointer(store: MemoryStore) -> dict | None:
    raw = store.get(POINTER_KEY)
    if raw is None:
        return None
    return json.loads(raw.decode())


def test_pointer_waits_for_objects_and_manifest(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.export.publish._RETRY_SLEEPS", (0, 0, 0))
    plan = _plan([_entry("grid/nyc", {"lims": 1}), _entry("grid/la", {"lims": 2})])

    before_manifest = MemoryStore()
    before_manifest.data["manifest"] = b'{"legacy":true}'
    before_manifest.fail_after = len(plan.objects)
    with pytest.raises(PublishError, match="3 attempts"):
        publish(plan, before_manifest, expected_current=None)
    assert _pointer(before_manifest) is None
    assert f"releases/{plan.snapshot_id}" not in before_manifest.data
    assert before_manifest.get("manifest") == b'{"legacy":true}'

    before_pointer = MemoryStore()
    before_pointer.fail_after = len(plan.objects) + 1
    with pytest.raises(PublishError, match="3 attempts"):
        publish(plan, before_pointer, expected_current=None)
    assert _pointer(before_pointer) is None
    assert f"releases/{plan.snapshot_id}" in before_pointer.data


def test_retry_is_idempotent_and_missing_reuse_candidates_upload():
    plan = _plan([_entry("grid/nyc", {"lims": 1})])
    store = MemoryStore()
    store.failures_left = 2
    first = publish(plan, store, expected_current=None)
    assert first.uploaded_objects == 1
    assert _pointer(store)["current"] == plan.snapshot_id
    assert _pointer(store)["previous"] is None
    digest = next(iter(plan.objects))
    del store.data[f"objects/{digest}"]
    second = publish(plan, store, expected_current=plan.snapshot_id)
    assert second.uploaded_objects == 1
    assert store.get(f"objects/{digest}") == plan.objects[digest]
    assert _pointer(store)["current"] == plan.snapshot_id


def test_stale_versioned_parent_aborts_without_writes():
    plan = _plan([_entry("grid/nyc", {"lims": 1})])
    store = MemoryStore()
    publish(plan, store, expected_current=None)
    other = _plan([_entry("grid/nyc", {"lims": 2})])
    before = dict(store.data)
    with pytest.raises(PublishError, match="expected parent"):
        publish(other, store, expected_current="ab" * 32)
    assert store.data == before


def test_rollback_selects_an_existing_release_and_keeps_legacy_bytes():
    first = _plan([_entry("grid/nyc", {"lims": 1})])
    second = _plan([_entry("grid/nyc", {"lims": 2})])
    store = MemoryStore()
    store.data["cells/index"] = b'{"legacy":true}'
    publish(first, store, expected_current=None)
    publish(second, store, expected_current=first.snapshot_id)
    assert _pointer(store)["current"] == second.snapshot_id
    assert _pointer(store)["previous"] == first.snapshot_id
    publish(first, store, expected_current=second.snapshot_id)
    assert _pointer(store)["current"] == first.snapshot_id
    assert _pointer(store)["previous"] == second.snapshot_id
    assert store.get("cells/index") == b'{"legacy":true}'
    assert f"objects/{next(iter(second.objects))}" in store.data


def test_removed_logical_key_is_absent_from_the_new_manifest():
    first = _plan([_entry("grid/nyc", {"lims": 1}), _entry("grid/la", {"lims": 2})])
    second = _plan([_entry("grid/nyc", {"lims": 1})])
    store = MemoryStore()
    publish(first, store, expected_current=None)
    publish(second, store, expected_current=first.snapshot_id)
    manifest = json.loads(store.get(f"releases/{second.snapshot_id}").decode())
    assert "grid/la" not in manifest["keys"]


def test_chunks_respect_entry_and_byte_budgets(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.export.publish.MAX_CHUNK_ENTRIES", 2)
    monkeypatch.setattr("src.export.publish.MAX_CHUNK_BYTES", 24)
    entries = [_entry(f"grid/{index}", {"lims": index, "pad": "x" * 8}) for index in range(3)]
    plan = _plan(entries)
    store = MemoryStore()
    publish(plan, store, expected_current=None)
    assert store.chunk_sizes
    assert max(store.chunk_sizes) <= 2
    oversized = _plan([_entry("grid/huge", {"pad": "x" * 40})])
    monkeypatch.setattr("src.export.publish.MAX_OBJECT_BYTES", 30)
    with pytest.raises(PublishError, match="object budget"):
        publish(oversized, MemoryStore(), expected_current=None)
    assert MAX_CHUNK_ENTRIES == 1000
    assert MAX_CHUNK_BYTES == 10 * 1024 * 1024


def test_stage_b_pointer_can_be_replaced_by_the_first_versioned_release():
    plan = _plan([_entry("grid/nyc", {"lims": 1})])
    store = MemoryStore()
    store.data[POINTER_KEY] = json.dumps(
        {"current": "r-20261010-abcd1234", "previous": None, "promoted_at": "2026-10-10T00:00:00+00:00"}
    ).encode()
    receipt = publish(plan, store, expected_current=None)
    assert receipt.pointer_writes == 1
    assert _pointer(store)["current"] == plan.snapshot_id
    assert _pointer(store)["previous"] is None
    rows = bulk_entries(plan)
    assert {row["key"] for row in rows} == {
        f"objects/{next(iter(plan.objects))}",
        f"releases/{plan.snapshot_id}",
        POINTER_KEY,
    }
