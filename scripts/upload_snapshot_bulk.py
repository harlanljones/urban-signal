"""Upload snapshot bulk JSON in bounded Wrangler files, promoting the pointer last.

Wrangler reads each entire file into a Node string before its own request
batching. Keep input files below that limit as well as KV's bulk request limits.

KV bills every pair written, unchanged or not. Each entry carries a sha256 of
its value in KV metadata, and entries whose live key already has that hash are
skipped. The listing is taken from the namespace itself, so keys deleted by the
pruner are always rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

MAX_BATCH_ENTRIES = 10_000
MAX_BATCH_BYTES = 50 * 1024 * 1024
POINTER_KEY = "snapshot/current"
HASH_FIELD = "sha256"


def value_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def list_live_hashes(binding: str) -> dict[str, str]:
    """Key -> stored value hash for every key in the namespace (one paginated list)."""
    listing = subprocess.run(
        ["bunx", "wrangler", "kv", "key", "list", "--binding", binding, "--remote"],
        check=True, capture_output=True, text=True,
    ).stdout
    hashes = {}
    for row in json.loads(listing):
        metadata = row.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get(HASH_FIELD), str):
            hashes[row["name"]] = metadata[HASH_FIELD]
    return hashes


def prepare_batches(
    bulk: Path,
    directory: Path,
    *,
    max_entries: int = MAX_BATCH_ENTRIES,
    max_bytes: int = MAX_BATCH_BYTES,
    live: dict[str, str] | None = None,
) -> tuple[list[Path], int, int]:
    """Validate and stage all batches before any remote write can occur."""
    if max_entries < 1 or max_bytes < 2:
        raise ValueError("Batch limits must allow at least one entry and a JSON array")
    with bulk.open(encoding="utf-8") as source:
        entries = json.load(source)
    if not isinstance(entries, list):
        raise TypeError("Snapshot bulk must be a JSON array")
    pointer = None
    paths: list[Path] = []
    current: list[bytes] = []
    size = 2  # Array brackets; commas counted below.
    total = 0
    skipped = 0
    live = live or {}
    directory.mkdir(parents=True, exist_ok=True)

    def flush() -> None:
        nonlocal current, size
        if not current:
            return
        path = directory / f"batch-{len(paths):05d}.json"
        path.write_bytes(b"[" + b",".join(current) + b"]")
        paths.append(path)
        current = []
        size = 2

    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("key"), str) or not isinstance(entry.get("value"), str):
            raise TypeError("Each snapshot entry must have string key and value fields")
        digest = value_hash(entry["value"])
        metadata = entry.get("metadata")
        entry = {**entry, "metadata": {**(metadata if isinstance(metadata, dict) else {}), HASH_FIELD: digest}}
        encoded = json.dumps(entry, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if len(encoded) + 2 > max_bytes:
            raise ValueError(f"Entry {entry['key']!r} exceeds the upload batch byte limit")
        total += 1
        if entry["key"] == POINTER_KEY:
            if pointer is not None:
                raise ValueError("Snapshot bulk contains multiple promotion pointers")
            pointer = encoded
            continue
        if live.get(entry["key"]) == digest:
            skipped += 1
            continue
        addition = len(encoded) + bool(current)
        if len(current) >= max_entries or size + addition > max_bytes:
            flush()
            addition = len(encoded)
        current.append(encoded)
        size += addition
    flush()
    if pointer is not None:
        path = directory / "pointer.json"
        path.write_bytes(b"[" + pointer + b"]")
        paths.append(path)
    return paths, total, skipped


def upload_bulk(bulk: Path, binding: str, *, dry_run: bool = False, full: bool = False) -> dict[str, int]:
    with tempfile.TemporaryDirectory(prefix="snapshot-upload-") as temporary:
        paths, entries, skipped = prepare_batches(bulk, Path(temporary))
        if not (dry_run or full):
            paths, entries, skipped = prepare_batches(bulk, Path(temporary) / "delta", live=list_live_hashes(binding))
        uploaded = 0
        for index, path in enumerate(paths):
            print(f"Snapshot batch {index + 1}/{len(paths)}: {path.stat().st_size} bytes", flush=True)
            if not dry_run:
                subprocess.run(
                    ["bunx", "wrangler", "kv", "bulk", "put", str(path), "--binding", binding, "--remote"],
                    check=True,
                )
                uploaded += 1
        return {"entries": entries, "skipped_unchanged": skipped, "batches": len(paths), "uploaded_batches": uploaded}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bulk", type=Path, required=True)
    parser.add_argument("--binding", default="SNAPSHOT")
    parser.add_argument("--dry-run", action="store_true", help="Validate and stage batches without remote writes")
    parser.add_argument("--full", action="store_true", help="Rewrite every entry, ignoring live value hashes")
    args = parser.parse_args()
    print(json.dumps(upload_bulk(args.bulk, args.binding, dry_run=args.dry_run, full=args.full), sort_keys=True))


if __name__ == "__main__":
    main()
