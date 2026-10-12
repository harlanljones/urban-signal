"""Upload snapshot bulk JSON in bounded Wrangler files, promoting the pointer last.

Wrangler reads each entire file into a Node string before its own request
batching. Keep input files below that limit as well as KV's bulk request limits.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

MAX_BATCH_ENTRIES = 10_000
MAX_BATCH_BYTES = 50 * 1024 * 1024
POINTER_KEY = "snapshot/current"


def prepare_batches(
    bulk: Path,
    directory: Path,
    *,
    max_entries: int = MAX_BATCH_ENTRIES,
    max_bytes: int = MAX_BATCH_BYTES,
) -> tuple[list[Path], int]:
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
        encoded = json.dumps(entry, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if len(encoded) + 2 > max_bytes:
            raise ValueError(f"Entry {entry['key']!r} exceeds the upload batch byte limit")
        total += 1
        if entry["key"] == POINTER_KEY:
            if pointer is not None:
                raise ValueError("Snapshot bulk contains multiple promotion pointers")
            pointer = encoded
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
    return paths, total


def upload_bulk(bulk: Path, binding: str, *, dry_run: bool = False) -> dict[str, int]:
    with tempfile.TemporaryDirectory(prefix="snapshot-upload-") as temporary:
        paths, entries = prepare_batches(bulk, Path(temporary))
        uploaded = 0
        for index, path in enumerate(paths):
            print(f"Snapshot batch {index + 1}/{len(paths)}: {path.stat().st_size} bytes", flush=True)
            if not dry_run:
                subprocess.run(
                    ["bunx", "wrangler", "kv", "bulk", "put", str(path), "--binding", binding, "--remote"],
                    check=True,
                )
                uploaded += 1
        return {"entries": entries, "batches": len(paths), "uploaded_batches": uploaded}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bulk", type=Path, required=True)
    parser.add_argument("--binding", default="SNAPSHOT")
    parser.add_argument("--dry-run", action="store_true", help="Validate and stage batches without remote writes")
    args = parser.parse_args()
    print(json.dumps(upload_bulk(args.bulk, args.binding, dry_run=args.dry_run), sort_keys=True))


if __name__ == "__main__":
    main()
