from __future__ import annotations

import hashlib
import multiprocessing
import os
import threading
from io import BytesIO

import pytest

from src.ingestion.store import (
    CheckpointConflict,
    IntegrityError,
    LocalObjectStore,
    S3ObjectStore,
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _first_writer(store_root: str, barrier: multiprocessing.synchronize.Barrier, value: int, result) -> None:
    store = LocalObjectStore(store_root)
    barrier.wait()
    try:
        result.put(("ok", store.compare_and_swap_checkpoint("checkpoint.json", None, {"v": value})))
    except CheckpointConflict:
        result.put(("conflict", None))


def test_local_store_writes_and_verifies_immutable_bytes(tmp_path):
    store = LocalObjectStore(tmp_path)
    payload = b"projected page"

    store.put_immutable("pages/one.json", payload, digest(payload))

    assert store.get_verified("pages/one.json", digest(payload)) == payload
    with pytest.raises(IntegrityError):
        store.get_verified("pages/one.json", "0" * 64)
    with pytest.raises(IntegrityError):
        store.put_immutable("pages/one.json", b"different", digest(b"different"))


@pytest.mark.parametrize("key", ["../escape", "/absolute", "a/../../escape", "", "a\\b"])
def test_local_store_rejects_unsafe_keys(tmp_path, key):
    store = LocalObjectStore(tmp_path)
    with pytest.raises(ValueError, match="key"):
        store.put_immutable(key, b"x", digest(b"x"))


def test_local_store_rejects_symlinked_parent(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "store"
    root.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        LocalObjectStore(root).put_immutable("linked/object", b"x", digest(b"x"))
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("mode", [0o770, 0o707])
def test_local_store_rejects_group_or_other_writable_root_without_creating_files(tmp_path, mode):
    root = tmp_path / "shared-root"
    root.mkdir()
    root.chmod(mode)

    with pytest.raises(ValueError, match="private and owned"):
        LocalObjectStore(root)

    assert list(root.iterdir()) == []


def test_local_store_creates_missing_root_with_private_permissions(tmp_path):
    root = tmp_path / "new" / "store"

    LocalObjectStore(root)

    assert root.stat().st_mode & 0o777 == 0o700


def test_checkpoint_cas_uses_opaque_versions_and_deterministic_json(tmp_path):
    store = LocalObjectStore(tmp_path)
    assert store.read_checkpoint("state/checkpoint.json") == (None, None)

    first = store.compare_and_swap_checkpoint("state/checkpoint.json", None, {"b": 2, "a": 1})
    body, version = store.read_checkpoint("state/checkpoint.json")
    assert body == {"a": 1, "b": 2}
    assert version == first
    second = store.compare_and_swap_checkpoint("state/checkpoint.json", first, {"run": "next"})
    assert second != first
    with pytest.raises(CheckpointConflict):
        store.compare_and_swap_checkpoint("state/checkpoint.json", first, {"run": "stale"})


def test_checkpoint_json_rejects_non_finite_numbers(tmp_path):
    store = LocalObjectStore(tmp_path)

    with pytest.raises(ValueError, match="JSON values"):
        store.compare_and_swap_checkpoint("checkpoint", None, {"value": float("nan")})

    assert store.read_checkpoint("checkpoint") == (None, None)


def test_two_processes_cannot_both_create_absent_checkpoint(tmp_path):
    context = multiprocessing.get_context("fork")
    barrier = context.Barrier(2)
    results = context.Queue()
    processes = [
        context.Process(target=_first_writer, args=(str(tmp_path), barrier, value, results))
        for value in (1, 2)
    ]
    for process in processes:
        process.start()
    outcomes = [results.get(timeout=10)[0] for _ in processes]
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0
    assert sorted(outcomes) == ["conflict", "ok"]


class FakeS3:
    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.calls: list[tuple[str, dict]] = []
        self.mismatch_after_put = False

    def put_object(self, **kwargs):
        self.calls.append(("put", kwargs))
        key = kwargs["Key"]
        prior = self.objects.get(key)
        if kwargs.get("IfNoneMatch") == "*" and prior is not None:
            raise ClientError("412", "PreconditionFailed")
        if "IfMatch" in kwargs and (prior is None or prior[1] != kwargs["IfMatch"]):
            raise ClientError("412", "PreconditionFailed")
        body = kwargs["Body"]
        if hasattr(body, "read"):
            body = body.read()
        version = f'"{len(self.calls)}"'
        self.objects[key] = (body, version)
        if self.mismatch_after_put:
            self.objects[key] = (b"tampered", version)
        return {"ETag": version}

    def get_object(self, **kwargs):
        self.calls.append(("get", kwargs))
        try:
            body, version = self.objects[kwargs["Key"]]
        except KeyError as error:
            raise ClientError("404", "NoSuchKey") from error
        return {"Body": BytesIO(body), "ETag": version}


class ClientError(Exception):
    def __init__(self, status, code):
        self.response = {"ResponseMetadata": {"HTTPStatusCode": int(status)}, "Error": {"Code": code}}
        super().__init__(code)


def test_s3_immutable_put_is_conditional_and_verified_after_ack():
    client = FakeS3()
    store = S3ObjectStore(client, "bucket", "shadow/v1")
    payload = b"page"

    store.put_immutable("pages/one", payload, digest(payload))

    assert client.calls[0][1]["IfNoneMatch"] == "*"
    assert client.calls[1][0] == "get"
    assert store.get_verified("pages/one", digest(payload)) == payload
    with pytest.raises(IntegrityError):
        store.put_immutable("pages/one", b"changed", digest(b"changed"))


def test_s3_checkpoint_cas_uses_create_and_update_conditionals():
    client = FakeS3()
    store = S3ObjectStore(client, "bucket", "shadow/v1")
    first = store.compare_and_swap_checkpoint("checkpoint", None, {"x": 1})
    second = store.compare_and_swap_checkpoint("checkpoint", first, {"x": 2})

    puts = [kwargs for op, kwargs in client.calls if op == "put"]
    assert puts[0]["IfNoneMatch"] == "*"
    assert puts[1]["IfMatch"] == first
    assert second != first
    assert store.read_checkpoint("checkpoint") == ({"x": 2}, second)
    with pytest.raises(CheckpointConflict):
        store.compare_and_swap_checkpoint("checkpoint", first, {"x": 3})


def test_s3_store_fails_if_acknowledged_write_cannot_be_verified():
    client = FakeS3()
    client.mismatch_after_put = True
    store = S3ObjectStore(client, "bucket", "shadow/v1")

    with pytest.raises(IntegrityError):
        store.put_immutable("pages/one", b"page", digest(b"page"))


def test_s3_store_translates_conditional_conflict_without_unconditional_retry():
    client = FakeS3()
    store = S3ObjectStore(client, "bucket", "shadow/v1")
    store.compare_and_swap_checkpoint("checkpoint", None, {"v": 1})
    before = len(client.calls)

    with pytest.raises(CheckpointConflict):
        store.compare_and_swap_checkpoint("checkpoint", None, {"v": 2})

    assert len(client.calls) == before + 1
    assert client.calls[-1][1].get("IfNoneMatch") == "*"


def test_local_threads_have_single_winner_for_absent_checkpoint(tmp_path):
    store = LocalObjectStore(tmp_path)
    start = threading.Barrier(2)
    results = []

    def write(value):
        start.wait()
        try:
            results.append(store.compare_and_swap_checkpoint("checkpoint", None, {"v": value}))
        except CheckpointConflict:
            results.append(None)

    threads = [threading.Thread(target=write, args=(value,)) for value in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert sum(result is not None for result in results) == 1


def test_local_interrupted_checkpoint_replace_preserves_previous_commit(tmp_path, monkeypatch):
    import src.ingestion.store as module

    store = LocalObjectStore(tmp_path)
    version = store.compare_and_swap_checkpoint("checkpoint", None, {"run": "committed"})

    def interrupt(*args, **kwargs):
        raise OSError("simulated disk interruption before rename")

    monkeypatch.setattr(module.os, "replace", interrupt)
    with pytest.raises(OSError, match="interruption"):
        store.compare_and_swap_checkpoint("checkpoint", version, {"run": "partial"})

    assert store.read_checkpoint("checkpoint") == ({"run": "committed"}, version)


def test_local_store_rejects_symlinked_object_file(tmp_path):
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    root = tmp_path / "store"
    root.mkdir()
    (root / "object").symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        LocalObjectStore(root).get_verified("object", digest(b"outside"))


def test_local_store_rejects_non_regular_object_without_blocking(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    os.mkfifo(root / "pipe")

    with pytest.raises(IntegrityError, match="regular file"):
        LocalObjectStore(root).get_verified("pipe", digest(b"x"))


def test_s3_checkpoint_rejects_malformed_payload_as_integrity_error():
    client = FakeS3()
    store = S3ObjectStore(client, "bucket", "shadow/v1")
    client.objects["shadow/v1/checkpoint"] = (b"{}", '"etag"')

    with pytest.raises(IntegrityError):
        store.read_checkpoint("checkpoint")


def test_s3_authorization_failure_propagates_without_retry_or_fallback():
    class UnauthorizedClient(FakeS3):
        def put_object(self, **kwargs):
            self.calls.append(("put", kwargs))
            raise ClientError("403", "AccessDenied")

    client = UnauthorizedClient()
    store = S3ObjectStore(client, "bucket", "shadow/v1")
    with pytest.raises(ClientError):
        store.compare_and_swap_checkpoint("checkpoint", None, {"v": 1})
    assert len(client.calls) == 1
    assert client.calls[0][1].get("IfNoneMatch") == "*"


def test_s3_rejects_unsafe_keys_and_prefixes():
    with pytest.raises(ValueError, match="key"):
        S3ObjectStore(FakeS3(), "bucket", "../unsafe")
    store = S3ObjectStore(FakeS3(), "bucket", "shadow/v1")
    with pytest.raises(ValueError, match="key"):
        store.read_checkpoint("../../outside")
