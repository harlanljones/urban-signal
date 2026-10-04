import json
from pathlib import Path

import pytest
from scripts.run_shadow_ingestion import (
    load_source_contract,
    parse_as_of,
    validate_provider_receipt,
)

from src.ingestion.source import SourceNotReady


def test_as_of_requires_explicit_utc():
    assert parse_as_of("2026-10-03T00:00:00Z").utcoffset().total_seconds() == 0
    with pytest.raises(ValueError, match="UTC"):
        parse_as_of("2026-10-03T00:00:00-04:00")


def test_local_fixture_contract_does_not_require_remote_readiness(tmp_path: Path):
    path = tmp_path / "contract.json"
    path.write_text(
        json.dumps(
            {
                "source_id": "test",
                "endpoint": "https://example.test/x",
                "dataset_id": "x",
                "version": "v1",
                "fields": ["id", "updated", "issued"],
                "identity_fields": ["id"],
                "source_row_id_field": "id",
                "event_time_field": "issued",
                "update_time_field": "updated",
                "page_size_max": 5,
                "query_contract": {
                    "pagination": "keyset",
                    "ordering_fields": ["updated", "id"],
                    "timestamp_precision": "millisecond",
                    "status": "unverified",
                },
                "guarantees": {},
            }
        )
    )
    contract = load_source_contract(path, local_fixture=True)
    assert contract.source_id == "test"
    with pytest.raises(SourceNotReady):
        contract.assert_ready()


def test_live_provider_receipt_must_match_target_and_be_fresh():
    receipt = {
        "bucket": "b",
        "endpoint": "https://r2.example",
        "base_prefix": "ingestion/v1/nyc/permits/ipu4-2q9a/shadow",
        "probe_prefix": "ingestion/v1/nyc/permits/ipu4-2q9a/shadow/probes/probe-id/",
        "probe_id": "probe-id",
        "object_key": "proof.json",
        "checkpoint_key": "checkpoint.json",
        "created_at": "2026-10-03T00:00:00Z",
        "verified": True,
        "object_sha256": "a" * 64,
        "checkpoint_sha256": "b" * 64,
        "checks": {
            name: "passed"
            for name in (
                "absent_cas",
                "if_match_update",
                "stale_cas_conflict",
                "immutable_overwrite_rejected",
                "immutable_integrity_read",
                "two_client_absent_race",
                "fresh_client_restore",
            )
        },
    }
    validate_provider_receipt(
        receipt,
        bucket="b",
        endpoint="https://r2.example",
        run_prefix="ingestion/v1/nyc/permits/ipu4-2q9a/shadow/data",
        now="2026-10-03T01:00:00Z",
    )
    with pytest.raises(ValueError, match="bucket"):
        validate_provider_receipt(
            receipt,
            bucket="other",
            endpoint="https://r2.example",
            run_prefix="ingestion/v1/nyc/permits/ipu4-2q9a/shadow/data",
            now="2026-10-03T01:00:00Z",
        )
    with pytest.raises(ValueError, match="fresh"):
        validate_provider_receipt(
            receipt,
            bucket="b",
            endpoint="https://r2.example",
            run_prefix="ingestion/v1/nyc/permits/ipu4-2q9a/shadow/data",
            now="2026-10-05T01:00:00Z",
        )


class _FakeS3Error(Exception):
    def __init__(self, status=412, code="PreconditionFailed"):
        self.response = {"ResponseMetadata": {"HTTPStatusCode": status}, "Error": {"Code": code}}


class _FakeS3:
    def __init__(self):
        import hashlib
        import threading

        self.hashlib = hashlib
        self.objects = {}
        self.lock = threading.Lock()

    def put_object(self, *, Bucket, Key, Body, IfNoneMatch=None, IfMatch=None):
        with self.lock:
            current = self.objects.get((Bucket, Key))
            if IfNoneMatch == "*" and current is not None:
                raise _FakeS3Error()
            if IfMatch is not None and (current is None or current[1] != IfMatch):
                raise _FakeS3Error()
            data = bytes(Body)
            etag = self.hashlib.sha256(data).hexdigest()
            self.objects[(Bucket, Key)] = (data, etag)
            return {"ETag": etag}

    def get_object(self, *, Bucket, Key):
        from io import BytesIO

        if (Bucket, Key) not in self.objects:
            raise _FakeS3Error(404, "NoSuchKey")
        data, etag = self.objects[(Bucket, Key)]
        return {"Body": BytesIO(data), "ETag": etag}


def test_store_probe_exercises_conditional_writes_and_restore():
    from scripts.probe_ingestion_store import probe

    clients = []

    def make_client(_endpoint):
        if not clients:
            clients.append(_FakeS3())
        return clients[0]

    receipt = probe(
        make_client,
        bucket="isolated-test",
        endpoint="https://storage.example",
        base_prefix="ingestion/v1/nyc/permits/ipu4-2q9a/shadow/",
    )
    assert receipt["verified"] is True
    assert receipt["checks"]["if_match_update"] == "passed"
    assert receipt["checks"]["stale_cas_conflict"] == "passed"
    assert receipt["checks"]["two_client_absent_race"] == "passed"
    assert receipt["checks"]["fresh_client_restore"] == "passed"


def test_live_provider_receipt_requires_all_conditional_write_checks():
    receipt = {
        "bucket": "b",
        "endpoint": "https://r2.example",
        "base_prefix": "shadow/",
        "probe_prefix": "shadow/probes/probe-id/",
        "probe_id": "probe-id",
        "object_key": "proof.json",
        "checkpoint_key": "checkpoint.json",
        "created_at": "2026-10-03T00:00:00Z",
        "verified": True,
        "object_sha256": "a" * 64,
        "checkpoint_sha256": "b" * 64,
    }
    with pytest.raises(ValueError, match="conditional"):
        validate_provider_receipt(
            receipt,
            bucket="b",
            endpoint="https://r2.example",
            run_prefix="shadow/data/",
            now="2026-10-03T01:00:00Z",
        )
