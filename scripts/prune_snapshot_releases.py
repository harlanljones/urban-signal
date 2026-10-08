"""Bounded retention for release-qualified snapshot generations.

Hex-coverage Stage B publishes every logical snapshot key twice: the legacy
logical key plus a release-qualified twin under ``releases/{snapshot_id}/``. The
snapshot id hashes the manifest (including ``generated_at``), so it changes on
every build — without pruning, the namespace accumulates a full generation per
daily publish (measured ~138 MiB/day, ~566 MiB/day once dense metro hex is on).

This runs after the new bulk has been pushed and keeps only the two generations
the reader can address: the ``snapshot/current`` pointer's ``current`` and
``previous`` ids. Everything under ``releases/{other-id}/`` is deleted through
the Workers KV bulk-delete API (10,000 keys per request). It fails safe: if the
pointer cannot be read, nothing is deleted.

Usage::

    python scripts/prune_snapshot_releases.py \
        --account-id "$CLOUDFLARE_ACCOUNT_ID" \
        --namespace-id "$SNAPSHOT_NAMESPACE_ID" \
        --pointer dist/kv-bulk.json \
        [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path

import httpx

CF_API_BASE = "https://api.cloudflare.com/client/v4"
RELEASES_PREFIX = "releases/"
DELETE_BATCH = 10_000
LIST_LIMIT = 1_000


class PruneError(RuntimeError):
    """Raised when the prune cannot complete safely."""


def read_pointer_from_bulk(bulk_path: Path) -> dict:
    """Return the ``snapshot/current`` pointer from a written ``kv-bulk.json``.

    Raises :class:`PruneError` when the file is missing/unreadable or carries no
    pointer, so the caller can abort without deleting anything.
    """
    bulk_path = Path(bulk_path)
    try:
        entries = json.loads(bulk_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PruneError(f"cannot read {bulk_path}: {exc}") from exc
    if not isinstance(entries, list):
        raise PruneError(f"{bulk_path}: expected a JSON array of KV entries")
    for entry in entries:
        if isinstance(entry, dict) and entry.get("key") == "snapshot/current":
            try:
                pointer = json.loads(entry.get("value", ""))
            except ValueError as exc:
                raise PruneError(f"snapshot/current is not valid JSON: {exc}") from exc
            if not isinstance(pointer, dict) or "current" not in pointer:
                raise PruneError("snapshot/current has no 'current' id")
            return pointer
    raise PruneError("no snapshot/current pointer in the bulk; refusing to prune")


def keep_ids(pointer: dict) -> set[str]:
    """The generation ids the reader can still address: current + previous."""
    keep = {pointer.get("current"), pointer.get("previous")}
    keep.discard(None)
    keep.discard("")
    if not keep:
        raise PruneError("pointer has neither current nor previous id")
    return {str(item) for item in keep}


def release_id(key: str) -> str | None:
    """The generation id of a ``releases/{id}/{logical}`` key, or None."""
    if not key.startswith(RELEASES_PREFIX):
        return None
    rest = key[len(RELEASES_PREFIX) :]
    if "/" not in rest:
        return None
    generation, _, logical = rest.partition("/")
    return generation if generation and logical else None


def stale_release_keys(keys: Iterable[str], keep: set[str]) -> list[str]:
    """Keys under ``releases/`` whose generation is not in ``keep``.

    Keys that do not parse as a release key are left alone (never delete what we
    do not understand).
    """
    stale: list[str] = []
    for key in keys:
        generation = release_id(key)
        if generation is not None and generation not in keep:
            stale.append(key)
    return stale


def list_release_keys(
    client: httpx.Client,
    account_id: str,
    namespace_id: str,
    prefix: str = RELEASES_PREFIX,
) -> list[str]:
    """List every KV key under ``prefix``, following the API's cursor."""
    url = f"{CF_API_BASE}/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/keys"
    names: list[str] = []
    cursor: str | None = None
    while True:
        params: dict[str, str] = {"prefix": prefix, "limit": str(LIST_LIMIT)}
        if cursor:
            params["cursor"] = cursor
        response = client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success", True):
            raise PruneError(f"KV key list failed: {payload.get('errors')}")
        for item in payload.get("result", []):
            name = item.get("name") if isinstance(item, dict) else item
            if name:
                names.append(str(name))
        cursor = (payload.get("result_info") or {}).get("cursor")
        if not cursor:
            return names


def delete_keys(
    client: httpx.Client,
    account_id: str,
    namespace_id: str,
    keys: list[str],
    batch: int = DELETE_BATCH,
) -> dict:
    """Delete ``keys`` in batches; return successful/unsuccessful counts."""
    url = (
        f"{CF_API_BASE}/accounts/{account_id}/storage/kv/namespaces/"
        f"{namespace_id}/bulk/delete"
    )
    successful = 0
    unsuccessful: list[str] = []
    for start in range(0, len(keys), batch):
        chunk = keys[start : start + batch]
        response = client.post(url, json=chunk)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success", True):
            raise PruneError(f"KV bulk delete failed: {payload.get('errors')}")
        result = payload.get("result") or {}
        successful += int(result.get("successful_key_count") or 0)
        unsuccessful.extend(str(k) for k in (result.get("unsuccessful_keys") or []))
    return {"successful": successful, "unsuccessful": unsuccessful}


def prune(
    client: httpx.Client,
    account_id: str,
    namespace_id: str,
    keep: set[str],
    *,
    dry_run: bool = False,
) -> dict:
    """Delete every release generation outside ``keep``."""
    keys = list_release_keys(client, account_id, namespace_id)
    stale = stale_release_keys(keys, keep)
    summary = {
        "scanned": len(keys),
        "kept": len(keys) - len(stale),
        "stale": len(stale),
        "deleted": 0,
        "dry_run": dry_run,
    }
    if dry_run or not stale:
        return summary
    outcome = delete_keys(client, account_id, namespace_id, stale)
    summary["deleted"] = outcome["successful"]
    summary["unsuccessful"] = outcome["unsuccessful"]
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Delete release-qualified snapshot generations outside {current, previous}"
    )
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--namespace-id", required=True)
    parser.add_argument("--pointer", required=True, help="Path to the built kv-bulk.json")
    parser.add_argument("--token", default=None, help="Defaults to CLOUDFLARE_API_TOKEN")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    import os

    token = args.token or os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token:
        print("PRUNE_ERROR: no Cloudflare API token (--token or CLOUDFLARE_API_TOKEN)", file=sys.stderr)
        return 1

    try:
        pointer = read_pointer_from_bulk(Path(args.pointer))
        keep = keep_ids(pointer)
    except PruneError as exc:
        print(f"PRUNE_ERROR: {exc}", file=sys.stderr)
        return 1

    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(headers=headers, timeout=60.0) as client:
        try:
            summary = prune(client, args.account_id, args.namespace_id, keep, dry_run=args.dry_run)
        except (httpx.HTTPError, PruneError) as exc:
            print(f"PRUNE_ERROR: {exc}", file=sys.stderr)
            return 1

    print(
        "PRUNE_OK "
        f"keep={sorted(keep)} scanned={summary['scanned']} stale={summary['stale']} "
        f"deleted={summary['deleted']} dry_run={summary['dry_run']}"
    )
    unsuccessful = summary.get("unsuccessful") or []
    if unsuccessful:
        print(f"PRUNE_ERROR: {len(unsuccessful)} keys failed to delete", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
