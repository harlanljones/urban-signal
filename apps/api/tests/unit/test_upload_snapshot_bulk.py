"""Batch limits and fail-closed snapshot promotion at the Wrangler boundary."""
import json
import subprocess
from pathlib import Path

import pytest
from scripts.upload_snapshot_bulk import prepare_batches, upload_bulk, value_hash


@pytest.mark.parametrize(("max_entries", "max_bytes"), [(2, 10_000), (100, 280)])
def test_byte_and_entry_limits_preserve_payloads_and_promote_last(tmp_path: Path, max_entries: int, max_bytes: int):
    entries = [
        {"key": "grid/a", "value": "München 🏙" * 3},
        {"key": "snapshot/current", "value": '{"current":"release-a"}'},
        {"key": "cells/a", "value": "x" * 70},
        {"key": "cells/b", "value": "y" * 70},
        {"key": "cells/c", "value": "z" * 70},
    ]
    bulk = tmp_path / "bulk.json"
    bulk.write_text(json.dumps(entries))
    paths, total, _ = prepare_batches(bulk, tmp_path / "batches", max_entries=max_entries, max_bytes=max_bytes)
    decoded = [[{k: e[k] for k in ("key", "value")} for e in json.loads(path.read_text())] for path in paths]
    assert total == len(entries)
    assert all(path.stat().st_size <= max_bytes for path in paths)
    assert all(len(batch) <= max_entries for batch in decoded)
    assert [entry for batch in decoded[:-1] for entry in batch] == [entries[0], *entries[2:]]
    assert decoded[-1] == [entries[1]]


def test_failed_data_upload_never_promotes_pointer(tmp_path: Path, monkeypatch):
    bulk = tmp_path / "bulk.json"
    bulk.write_text(json.dumps([
        {"key": "snapshot/current", "value": '{"current":"release-a"}'},
        {"key": "objects/a", "value": "data"},
    ]))
    attempted = []

    def fail(command, **kwargs):
        if command[3:5] == ["key", "list"]:
            return subprocess.CompletedProcess(command, 0, stdout="[]")
        attempted.extend(json.loads(Path(command[5]).read_text()))
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr("scripts.upload_snapshot_bulk.subprocess.run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        upload_bulk(bulk, "SNAPSHOT")
    assert [entry["key"] for entry in attempted] == ["objects/a"]


@pytest.mark.parametrize("entries", [
    [{"key": "snapshot/current", "value": "a"}, {"key": "snapshot/current", "value": "b"}],
    [{"key": "a", "value": 42}],
    {"key": "a", "value": "b"},
])
def test_invalid_publication_fails_before_upload(tmp_path: Path, monkeypatch, entries):
    bulk = tmp_path / "bulk.json"
    bulk.write_text(json.dumps(entries))
    attempted = []
    monkeypatch.setattr("scripts.upload_snapshot_bulk.subprocess.run", lambda *args, **kwargs: attempted.append(args))
    with pytest.raises((ValueError, TypeError)):
        upload_bulk(bulk, "SNAPSHOT")
    assert attempted == []


def test_entry_larger_than_batch_budget_is_rejected(tmp_path: Path):
    bulk = tmp_path / "bulk.json"
    bulk.write_text(json.dumps([{"key": "cells/a", "value": "x" * 200}]))
    with pytest.raises(ValueError, match="exceeds the upload batch byte limit"):
        prepare_batches(bulk, tmp_path / "batches", max_bytes=100)


def test_unchanged_live_keys_are_skipped_but_pointer_always_written(tmp_path: Path, monkeypatch):
    bulk = tmp_path / "bulk.json"
    bulk.write_text(json.dumps([
        {"key": "objects/same", "value": "a"},
        {"key": "objects/changed", "value": "b"},
        {"key": "objects/new", "value": "c"},
        {"key": "snapshot/current", "value": "p"},
    ]))
    live = [
        {"name": "objects/same", "metadata": {"sha256": value_hash("a")}},
        {"name": "objects/changed", "metadata": {"sha256": value_hash("old")}},
        {"name": "snapshot/current", "metadata": {"sha256": value_hash("p")}},
    ]
    written = []

    def run(command, **kwargs):
        if command[3:5] == ["key", "list"]:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(live))
        written.extend(json.loads(Path(command[5]).read_text()))

    monkeypatch.setattr("scripts.upload_snapshot_bulk.subprocess.run", run)
    result = upload_bulk(bulk, "SNAPSHOT")
    assert [e["key"] for e in written] == ["objects/changed", "objects/new", "snapshot/current"]
    assert all(e["metadata"]["sha256"] == value_hash(e["value"]) for e in written)
    assert result["skipped_unchanged"] == 1
