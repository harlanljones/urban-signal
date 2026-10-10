#!/usr/bin/env python3
"""Probe conditional S3-compatible writes in a unique isolated shadow prefix."""

from __future__ import annotations

# ruff: noqa: I001

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "apps/api") not in sys.path:
    sys.path.insert(0, str(REPO / "apps/api"))
from src.ingestion.store import CheckpointConflict, IntegrityError, S3ObjectStore

DEFAULT_BASE = "ingestion/v1/nyc/permits/ipu4-2q9a/shadow/"


def _client(endpoint: str) -> Any:
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError(
            "store probe requires the optional boto3 dependency"
        ) from exc
    access = os.environ.get("INGESTION_R2_ACCESS_KEY_ID")
    secret = os.environ.get("INGESTION_R2_SECRET_ACCESS_KEY")
    if not access or not secret:
        raise RuntimeError("R2 probe credentials are not configured")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name="auto",
    )


def probe(
    client_factory, *, bucket: str, endpoint: str, base_prefix: str
) -> dict[str, Any]:
    base = base_prefix.strip("/")
    if not base or any(p in {"", ".", ".."} for p in base.split("/")):
        raise ValueError("invalid base prefix")
    probe_id = str(uuid.uuid4())
    probe_prefix = f"{base}/probes/{probe_id}/"
    object_key, checkpoint_key = "immutable/probe.json", "checkpoints/cas.json"
    payload = json.dumps(
        {"probe_id": probe_id, "purpose": "isolated conditional write verification"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    object_hash = hashlib.sha256(payload).hexdigest()
    client = client_factory(endpoint)
    store = S3ObjectStore(client, bucket, probe_prefix.rstrip("/"))
    store.put_immutable(object_key, payload, object_hash)
    if store.get_verified(object_key, object_hash) != payload:
        raise RuntimeError("immutable object readback failed")
    if store.read_checkpoint(checkpoint_key) != (None, None):
        raise RuntimeError("probe checkpoint prefix was not new")
    body = {"probe_id": probe_id, "writer": "initial"}
    first_version = store.compare_and_swap_checkpoint(checkpoint_key, None, body)
    try:
        store.compare_and_swap_checkpoint(
            checkpoint_key, None, {"probe_id": probe_id, "writer": "stale-absent"}
        )
    except CheckpointConflict:
        pass
    else:
        raise RuntimeError("provider accepted a stale absent-checkpoint CAS")
    updated_body = {"probe_id": probe_id, "writer": "updated"}
    updated_version = store.compare_and_swap_checkpoint(
        checkpoint_key, first_version, updated_body
    )
    if updated_version == first_version:
        raise RuntimeError(
            "provider did not return a new checkpoint version after IfMatch update"
        )
    try:
        store.compare_and_swap_checkpoint(
            checkpoint_key,
            first_version,
            {"probe_id": probe_id, "writer": "stale-match"},
        )
    except CheckpointConflict:
        pass
    else:
        raise RuntimeError("provider accepted a stale IfMatch checkpoint CAS")
    actual_body, actual_version = store.read_checkpoint(checkpoint_key)
    if actual_body != updated_body or actual_version != updated_version:
        raise RuntimeError("checkpoint changed after stale CAS or failed readback")
    try:
        store.put_immutable(
            object_key,
            b"different bytes",
            hashlib.sha256(b"different bytes").hexdigest(),
        )
    except IntegrityError:
        pass
    else:
        raise RuntimeError("provider allowed an immutable object overwrite")

    # Two independent clients race to create an absent checkpoint; conditional
    # writes must elect exactly one winner without a read-then-write window.
    race_key = "checkpoints/race.json"
    import concurrent.futures
    import threading

    barrier = threading.Barrier(2)

    def race_write(writer: str) -> str:
        race_store = S3ObjectStore(
            client_factory(endpoint), bucket, probe_prefix.rstrip("/")
        )
        barrier.wait(timeout=15)
        try:
            race_store.compare_and_swap_checkpoint(
                race_key, None, {"probe_id": probe_id, "writer": writer}
            )
            return "won"
        except CheckpointConflict:
            return "conflict"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        race_results = list(executor.map(race_write, ("left", "right")))
    if sorted(race_results) != ["conflict", "won"]:
        raise RuntimeError(
            f"absent-checkpoint race did not elect exactly one writer: {race_results}"
        )

    fresh = client_factory(endpoint)
    fresh_store = S3ObjectStore(fresh, bucket, probe_prefix.rstrip("/"))
    if fresh_store.get_verified(object_key, object_hash) != payload:
        raise RuntimeError("fresh-client immutable restore failed")
    if fresh_store.read_checkpoint(checkpoint_key) != (updated_body, updated_version):
        raise RuntimeError("fresh-client checkpoint restore failed")
    if (
        hashlib.sha256(fresh_store.get_verified(object_key, object_hash)).hexdigest()
        != object_hash
    ):
        raise RuntimeError("immutable hash changed after overwrite attempt")
    response = fresh.get_object(Bucket=bucket, Key=f"{probe_prefix}{checkpoint_key}")
    checkpoint_bytes = response["Body"].read()
    receipt = {
        "verified": True,
        "bucket": bucket,
        "endpoint": endpoint.rstrip("/"),
        "base_prefix": base + "/",
        "probe_prefix": probe_prefix,
        "probe_id": probe_id,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "object_key": object_key,
        "object_sha256": object_hash,
        "checkpoint_key": checkpoint_key,
        "checkpoint_sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
        "checkpoint_version": updated_version,
        "checks": {
            "absent_cas": "passed",
            "if_match_update": "passed",
            "stale_cas_conflict": "passed",
            "immutable_overwrite_rejected": "passed",
            "immutable_integrity_read": "passed",
            "two_client_absent_race": "passed",
            "fresh_client_restore": "passed",
        },
    }
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--prefix", default=DEFAULT_BASE)
    parser.add_argument("--receipt-output", type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = probe(
            _client, bucket=args.bucket, endpoint=args.endpoint, base_prefix=args.prefix
        )
        encoded = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
        if args.receipt_output:
            args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
            args.receipt_output.write_text(encoded, encoding="utf-8")
        print(encoded, end="")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"verified": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
