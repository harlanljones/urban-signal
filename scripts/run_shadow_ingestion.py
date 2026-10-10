#!/usr/bin/env python3
"""Run a local fixture or gated shadow acquisition against durable storage."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
API_ROOT = REPO / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from src.ingestion.runner import commit_run, replay_committed
from src.ingestion.source import SocrataPermitSource, SourceContract
from src.ingestion.store import LocalObjectStore, S3ObjectStore

DEFAULT_CONTRACT = REPO / "docs/research/nyc-permit-source-contract.json"
DEFAULT_FIXTURE = REPO / "apps/api/tests/fixtures/ingestion/shadow-permits.json"
DEFAULT_NAMESPACE = "ingestion/v1/nyc/permits/ipu4-2q9a/shadow/"
MAX_RECORD_CAP = 4_000_000
DEFAULT_RECORD_CAP = 250_000
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def parse_as_of(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("as-of must be an explicit UTC ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(
            "as-of must be an explicit UTC timestamp ending in Z or +00:00"
        )
    return parsed.astimezone(UTC)


def load_source_contract(
    path: str | Path = DEFAULT_CONTRACT, *, local_fixture: bool = False
) -> SourceContract:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load source contract {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise TypeError("source contract must be a JSON object")
    contract = SourceContract.from_dict(payload)
    if not local_fixture:
        contract.assert_ready()
    return contract


def _normal_prefix(prefix: str) -> str:
    normalized = prefix.strip("/")
    parts = normalized.split("/") if normalized else []
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("invalid shadow prefix")
    return "/".join(parts) + "/"


def validate_provider_receipt(
    receipt: dict[str, Any],
    *,
    bucket: str,
    endpoint: str,
    run_prefix: str,
    now: str | datetime,
    max_age: timedelta = timedelta(hours=24),
) -> None:
    if receipt.get("bucket") != bucket:
        raise ValueError("provider receipt bucket does not match configured bucket")
    if receipt.get("endpoint", "").rstrip("/") != endpoint.rstrip("/"):
        raise ValueError("provider receipt endpoint does not match configured endpoint")
    base_prefix = _normal_prefix(str(receipt.get("base_prefix", "")))
    if (
        not run_prefix.startswith(base_prefix)
        or run_prefix[len(base_prefix) :].split("/", 1)[0] != "data"
    ):
        raise ValueError(
            "provider receipt prefix does not authorize this shadow data prefix"
        )
    if receipt.get("verified") is not True:
        raise ValueError("provider receipt is not marked verified")
    required_checks = (
        "absent_cas",
        "if_match_update",
        "stale_cas_conflict",
        "immutable_overwrite_rejected",
        "immutable_integrity_read",
        "two_client_absent_race",
        "fresh_client_restore",
    )
    checks = receipt.get("checks")
    if not isinstance(checks, dict) or any(
        checks.get(name) != "passed" for name in required_checks
    ):
        raise ValueError("provider receipt lacks complete conditional-write checks")
    for key in ("object_sha256", "checkpoint_sha256"):
        if not isinstance(receipt.get(key), str) or not _DIGEST.fullmatch(receipt[key]):
            raise ValueError(f"provider receipt {key} is missing or invalid")
    if (
        not receipt.get("probe_prefix")
        or not receipt.get("object_key")
        or not receipt.get("checkpoint_key")
    ):
        raise ValueError("provider receipt probe keys are missing")
    now_dt = parse_as_of(now) if isinstance(now, str) else now.astimezone(UTC)
    created = parse_as_of(str(receipt.get("created_at", "")))
    age = now_dt - created
    if age < timedelta(0) or age > max_age:
        raise ValueError("provider receipt is outside the allowed freshness window")


def _verify_provider_receipt(
    receipt: dict[str, Any],
    client: Any,
    *,
    bucket: str,
    endpoint: str,
    prefix: str,
    now: datetime | None = None,
) -> None:
    validate_provider_receipt(
        receipt,
        bucket=bucket,
        endpoint=endpoint,
        run_prefix=prefix + "data/",
        now=now or datetime.now(UTC),
    )
    proof_store = S3ObjectStore(client, bucket, receipt["probe_prefix"].rstrip("/"))
    proof_store.get_verified(receipt["object_key"], receipt["object_sha256"])
    checkpoint_bytes = proof_store.get_verified(
        receipt["checkpoint_key"], receipt["checkpoint_sha256"]
    )
    body, version = proof_store.read_checkpoint(receipt["checkpoint_key"])
    if (
        not version
        or not body
        or hashlib.sha256(checkpoint_bytes).hexdigest() != receipt["checkpoint_sha256"]
    ):
        raise ValueError(
            "provider receipt checkpoint proof could not be restored and verified"
        )
    if body.get("probe_id") != receipt.get("probe_id"):
        raise ValueError("provider receipt checkpoint identity does not match")


def _s3_client(endpoint: str) -> Any:
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError(
            "live storage requires the optional boto3 dependency"
        ) from exc
    access = os.environ.get("INGESTION_R2_ACCESS_KEY_ID")
    secret = os.environ.get("INGESTION_R2_SECRET_ACCESS_KEY")
    if not access or not secret:
        raise RuntimeError("live storage credentials are not configured")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name="auto",
    )


def _collect_pages(
    source: SocrataPermitSource,
    *,
    mode: str,
    upper_bound: str | None,
    cursor: dict[str, str] | None,
    cap: int,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, bool, bool, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    last_cursor = cursor
    last_bounds: dict[str, Any] = {}
    exhausted = False
    recon_complete = False
    for page in source.iter_pages(cursor=cursor, upper_bound=upper_bound):
        if len(rows) + len(page.records) > cap:
            raise RuntimeError(
                f"record cap {cap} exceeded; run aborted without committing a cursor"
            )
        rows.extend(page.records)
        last_cursor = page.next_cursor or last_cursor
        last_bounds = page.query_bounds
        exhausted = page.exhausted
        recon_complete = page.reconciliation_complete
    return rows, last_cursor, exhausted, recon_complete, last_bounds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", required=True, choices=("bootstrap", "daily", "reconcile", "replay")
    )
    parser.add_argument(
        "--as-of", required=True, help="explicit UTC ISO-8601 timestamp"
    )
    parser.add_argument("--source-contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--local-root", type=Path, help="local-only store; selects fixture acquisition"
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--bucket", help="dedicated shadow R2 bucket")
    parser.add_argument("--endpoint", help="S3-compatible endpoint URL")
    parser.add_argument(
        "--provider-receipt", type=Path, help="fresh output of probe_ingestion_store.py"
    )
    parser.add_argument(
        "--prefix", default=DEFAULT_NAMESPACE, help="authorized shadow namespace"
    )
    parser.add_argument("--record-cap", type=int, default=DEFAULT_RECORD_CAP)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        as_of = parse_as_of(args.as_of)
        if args.record_cap < 1 or args.record_cap > MAX_RECORD_CAP:
            raise ValueError(f"record-cap must be between 1 and {MAX_RECORD_CAP}")
        prefix = _normal_prefix(args.prefix)
        local = args.local_root is not None
        if local == bool(args.bucket or args.endpoint or args.provider_receipt):
            raise ValueError(
                "choose either --local-root for a local fixture or all live storage options"
            )
        contract = load_source_contract(args.source_contract, local_fixture=local)
        if args.mode == "replay":
            if local:
                store = LocalObjectStore(args.local_root)
            else:
                if not all((args.bucket, args.endpoint, args.provider_receipt)):
                    raise ValueError(
                        "live replay requires bucket, endpoint, and provider receipt"
                    )
                client = _s3_client(args.endpoint)
                receipt = json.loads(args.provider_receipt.read_text(encoding="utf-8"))
                _verify_provider_receipt(
                    receipt,
                    client,
                    bucket=args.bucket,
                    endpoint=args.endpoint,
                    prefix=prefix,
                    now=datetime.now(UTC),
                )
                store = S3ObjectStore(client, args.bucket, prefix + "data")
            output = replay_committed(store, contract, as_of)
            output["mode"] = "replay"
            output["source_provenance"] = (
                "local_fixture" if local else "committed_source_manifests"
            )
        elif local:
            fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
            if isinstance(fixture, dict):
                if fixture.get("evidence_type") != "synthetic_local_test_fixture":
                    raise ValueError(
                        "local fixture envelope must identify itself as a synthetic local test fixture"
                    )
                fixture = fixture.get("records")
            if not isinstance(fixture, list) or any(
                not isinstance(row, dict) for row in fixture
            ):
                raise ValueError(
                    "local fixture must be a JSON array of projected records"
                )
            if len(fixture) > args.record_cap:
                raise RuntimeError("record cap exceeded; no run committed")
            output = commit_run(
                LocalObjectStore(args.local_root),
                contract,
                fixture,
                as_of,
                complete=True,
                reconciliation=args.mode in {"bootstrap", "reconcile"},
                full_scope=args.mode in {"bootstrap", "reconcile"},
                input_mode="local_fixture",
                run_id=f"fixture-{as_of.strftime('%Y%m%dT%H%M%SZ')}",
            )
            output.update(
                {
                    "mode": args.mode,
                    "source_provenance": "local_fixture",
                    "complete": True,
                    "fixture_path": str(args.fixture),
                    "record_cap": args.record_cap,
                }
            )
        else:
            if not all((args.bucket, args.endpoint, args.provider_receipt)):
                raise ValueError(
                    "live acquisition requires bucket, endpoint, and provider receipt"
                )
            client = _s3_client(args.endpoint)
            receipt = json.loads(args.provider_receipt.read_text(encoding="utf-8"))
            _verify_provider_receipt(
                receipt,
                client,
                bucket=args.bucket,
                endpoint=args.endpoint,
                prefix=prefix,
                now=datetime.now(UTC),
            )
            store = S3ObjectStore(client, args.bucket, prefix + "data")
            source = SocrataPermitSource(contract)
            try:
                old_checkpoint, _ = store.read_checkpoint(
                    "checkpoints/acquisition.json"
                )
                start_cursor = (
                    old_checkpoint.get("cursor")
                    if old_checkpoint and args.mode == "daily"
                    else None
                )
                upper_bound = (
                    None
                    if args.mode in {"bootstrap", "reconcile"}
                    else as_of.isoformat(timespec="milliseconds").replace("+00:00", "Z")
                )
                rows, cursor, exhausted, reconciliation_complete, query_bounds = (
                    _collect_pages(
                        source,
                        mode=args.mode,
                        upper_bound=upper_bound,
                        cursor=start_cursor,
                        cap=args.record_cap,
                    )
                )
            finally:
                source.close()
            complete = exhausted and (
                args.mode not in {"bootstrap", "reconcile"} or reconciliation_complete
            )
            output = commit_run(
                store,
                contract,
                rows,
                as_of,
                cursor=cursor,
                complete=complete,
                reconciliation=args.mode in {"bootstrap", "reconcile"},
                full_scope=reconciliation_complete,
                query_bounds=query_bounds,
                input_mode="live",
                metrics={"row_count": len(rows), "record_cap": args.record_cap},
            )
            output.update(
                {
                    "mode": args.mode,
                    "source_provenance": "live_source",
                    "complete": complete,
                    "query_bounds": query_bounds,
                    "record_cap": args.record_cap,
                    "provider_receipt_created_at": receipt["created_at"],
                }
            )
        print(json.dumps(output, sort_keys=True, default=str))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "complete": False,
                    "error": str(exc),
                    "mode": getattr(args, "mode", None),
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
