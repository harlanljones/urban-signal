"""Materialize a content-addressed snapshot bulk from a publication plan.

Dry-run is the default: it recomputes the plan from the legacy bulk and prints
object counts. ``--publish`` writes ``kv-versioned.json`` for ``wrangler kv bulk
put``. It does not contact Cloudflare by itself. Legacy logical keys are left
in the stage-B bulk; this file adds ``objects/<sha256>``, ``releases/<id>``,
and the versioned ``snapshot/current`` pointer.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.export.publication import plan_publication
from src.export.publish import bulk_entries

POINTER_KEY = "snapshot/current"


def logical_entries(bulk_path: Path) -> list[dict[str, str]]:
    """Legacy logical keys only. Release twins and the pointer are not republished."""
    entries = json.loads(bulk_path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise TypeError(f"{bulk_path} is not a KV bulk array")
    logical: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        if not isinstance(key, str) or key == POINTER_KEY or key.startswith("releases/"):
            continue
        value = entry.get("value")
        if not isinstance(value, str):
            raise TypeError(f"{key} has a non-string value")
        logical.append({"key": key, "value": value})
    return logical


def load_plan(plan_path: Path, bulk_path: Path):
    sidecar = json.loads(plan_path.read_text(encoding="utf-8"))
    metadata = sidecar["metadata"]
    plan = plan_publication(logical_entries(bulk_path), None, metadata)
    if plan.snapshot_id != sidecar["snapshot_id"]:
        raise ValueError(
            "publication plan does not match the legacy bulk "
            f"({sidecar['snapshot_id']} != {plan.snapshot_id})"
        )
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize a versioned snapshot bulk")
    parser.add_argument("--plan", required=True, help="publication-plan.json from the snapshot builder")
    parser.add_argument("--bulk", default="dist/kv-bulk.json", help="Legacy KV bulk used to recompute objects")
    parser.add_argument("--out", default="dist/kv-versioned.json", help="Versioned bulk written with --publish")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Write the versioned bulk. Without this flag the command only reports the plan.",
    )
    args = parser.parse_args()
    plan = load_plan(Path(args.plan), Path(args.bulk))
    rows = bulk_entries(plan)
    payload_bytes = sum(len(row["value"].encode("utf-8")) for row in rows)
    print(
        json.dumps(
            {
                "snapshot_id": plan.snapshot_id,
                "objects": len(plan.objects),
                "reuse_candidates": len(plan.reuse_candidates),
                "bulk_entries": len(rows),
                "payload_bytes": payload_bytes,
                "published": bool(args.publish),
            },
            sort_keys=True,
        )
    )
    if not args.publish:
        return
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print(f"publish_snapshot: {exc}", file=sys.stderr)
        sys.exit(1)
