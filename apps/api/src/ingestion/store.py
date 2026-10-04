"""Durable immutable objects and compare-and-swap checkpoints for shadow ingestion."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class CheckpointConflict(Exception):
    """The checkpoint changed since the caller read its expected version."""


class IntegrityError(Exception):
    """Stored or acknowledged bytes do not match their declared content."""


_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _validate_key(key: str) -> tuple[str, ...]:
    if not isinstance(key, str) or not key or "\\" in key or "\x00" in key:
        raise ValueError("invalid object key")
    path = Path(key)
    parts = key.split("/")
    if path.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("invalid object key")
    return tuple(parts)


def _validate_digest(sha256: str) -> None:
    if not isinstance(sha256, str) or not _DIGEST_RE.fullmatch(sha256):
        raise ValueError("sha256 must be a lowercase hexadecimal SHA-256 digest")


def _canonical_json(body: dict[str, Any]) -> bytes:
    if not isinstance(body, dict):
        raise TypeError("checkpoint body must be a dictionary")
    try:
        return json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("checkpoint body must contain JSON values") from error


def _read_stream(stream: Any) -> bytes:
    if hasattr(stream, "read"):
        try:
            body = stream.read()
        finally:
            close = getattr(stream, "close", None)
            if close is not None:
                close()
    else:
        body = stream
    if not isinstance(body, bytes):
        raise IntegrityError("object response body was not bytes")
    return body


def _error_details(error: Exception) -> tuple[int | None, str | None]:
    response = getattr(error, "response", {})
    metadata = response.get("ResponseMetadata", {}) if isinstance(response, dict) else {}
    info = response.get("Error", {}) if isinstance(response, dict) else {}
    try:
        status = int(metadata["HTTPStatusCode"])
    except (KeyError, TypeError, ValueError):
        status = None
    code = str(info.get("Code")) if info.get("Code") is not None else None
    return status, code


def _is_missing(error: Exception) -> bool:
    status, code = _error_details(error)
    return status == 404 or code in {"NoSuchKey", "NotFound", "404"}


def _is_precondition_failure(error: Exception) -> bool:
    status, code = _error_details(error)
    return status in {409, 412} or code in {"ConditionalRequestConflict", "PreconditionFailed"}


class LocalObjectStore:
    """Filesystem store rooted in a trusted directory owned by the current user.

    The root and its contents must only be changed through this store or by its
    trusted owner. ``flock`` coordinates cooperating processes; it does not
    protect against another process running as the same user.
    """

    def __init__(self, root: str | os.PathLike[str]):
        requested_root = Path(root)
        requested_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if requested_root.is_symlink():
            raise ValueError("store root cannot be a symlink")
        root_stat = requested_root.stat()
        if (
            not stat.S_ISDIR(root_stat.st_mode)
            or root_stat.st_uid != os.geteuid()
            or root_stat.st_mode & 0o022
        ):
            raise ValueError("store root must be private and owned by the current user")
        self.root = requested_root.resolve(strict=True)
        self._lock_path = self.root / ".ingestion-store.lock"
        if self._lock_path.is_symlink():
            raise ValueError("store lock cannot be a symlink")

    @contextmanager
    def _locked(self) -> Iterator[None]:
        descriptor = os.open(self._lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _path(self, key: str, *, create_parents: bool = False) -> Path:
        parts = _validate_key(key)
        current = self.root
        for part in parts[:-1]:
            current = current / part
            try:
                current.lstat()
            except FileNotFoundError:
                if not create_parents:
                    return current.joinpath(*parts[parts.index(part) + 1 :])
                current.mkdir()
            if os.path.islink(current) or not os.path.isdir(current):
                raise ValueError("object key resolves through a symlink or non-directory")
        result = current / parts[-1]
        try:
            if os.path.islink(result):
                raise ValueError("object key resolves to a symlink")
        except OSError as error:
            raise ValueError("object key is outside the store root") from error
        return result

    def _read_bytes(self, path: Path) -> bytes:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError:
            raise
        except OSError as error:
            raise ValueError("object key resolves to an unsafe path") from error
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise IntegrityError("stored object is not a regular file")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                return stream.read()
        finally:
            os.close(descriptor)

    def _atomic_write(self, path: Path, data: bytes, *, replace: bool) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent.is_symlink():
            raise ValueError("object key resolves through a symlink")
        descriptor, temp_name = tempfile.mkstemp(prefix=".ingestion-tmp-", dir=path.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if not replace and path.exists():
                raise FileExistsError(path)
            os.replace(temp_path, path)
            parent_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        finally:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass

    def put_immutable(self, key: str, data: bytes, sha256: str) -> None:
        _validate_digest(sha256)
        if not isinstance(data, bytes):
            raise TypeError("immutable object data must be bytes")
        if hashlib.sha256(data).hexdigest() != sha256:
            raise IntegrityError("provided immutable object digest does not match bytes")
        with self._locked():
            path = self._path(key, create_parents=True)
            try:
                existing = self._read_bytes(path)
            except FileNotFoundError:
                existing = None
            if existing is not None:
                if hashlib.sha256(existing).hexdigest() != sha256 or existing != data:
                    raise IntegrityError("immutable object key already contains different bytes")
                return
            self._atomic_write(path, data, replace=False)
            written = self._read_bytes(path)
            if hashlib.sha256(written).hexdigest() != sha256 or len(written) != len(data):
                raise IntegrityError("immutable object failed post-write verification")

    def get_verified(self, key: str, sha256: str) -> bytes:
        _validate_digest(sha256)
        path = self._path(key)
        try:
            data = self._read_bytes(path)
        except FileNotFoundError as error:
            raise IntegrityError("immutable object is missing") from error
        if hashlib.sha256(data).hexdigest() != sha256:
            raise IntegrityError("immutable object digest does not match")
        return data

    def read_checkpoint(self, key: str) -> tuple[dict[str, Any] | None, str | None]:
        path = self._path(key)
        try:
            encoded = self._read_bytes(path)
        except FileNotFoundError:
            return None, None
        try:
            envelope = json.loads(encoded)
            body = envelope["body"]
            version = envelope["version"]
            if not isinstance(body, dict) or not isinstance(version, str) or not version:
                raise ValueError("invalid checkpoint envelope")
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise IntegrityError("checkpoint is not a valid stored document") from error
        return body, version

    def compare_and_swap_checkpoint(
        self, key: str, expected_version: str | None, body: dict[str, Any]
    ) -> str:
        encoded_body = _canonical_json(body)
        with self._locked():
            _, current_version = self.read_checkpoint(key)
            if current_version != expected_version:
                raise CheckpointConflict("checkpoint version changed")
            version = uuid.uuid4().hex
            envelope = _canonical_json({"body": json.loads(encoded_body), "version": version})
            path = self._path(key, create_parents=True)
            self._atomic_write(path, envelope, replace=True)
            read_body, read_version = self.read_checkpoint(key)
            if read_body != body or read_version != version:
                raise IntegrityError("checkpoint failed post-write verification")
            return version


class S3ObjectStore:
    """Injected S3-compatible client using only server-side conditional writes."""

    def __init__(self, client: Any, bucket: str, prefix: str):
        if not bucket:
            raise ValueError("bucket is required")
        self.client = client
        self.bucket = bucket
        self.prefix = "/".join(_validate_key(prefix)) if prefix else ""

    def _key(self, key: str) -> str:
        suffix = "/".join(_validate_key(key))
        return f"{self.prefix}/{suffix}" if self.prefix else suffix

    def _get(self, key: str) -> tuple[bytes, str | None]:
        response = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
        return _read_stream(response.get("Body")), response.get("ETag")

    def get_verified(self, key: str, sha256: str) -> bytes:
        _validate_digest(sha256)
        try:
            data, _ = self._get(key)
        except Exception as error:
            if _is_missing(error):
                raise IntegrityError("immutable object is missing") from error
            raise
        if hashlib.sha256(data).hexdigest() != sha256:
            raise IntegrityError("immutable object digest does not match")
        return data

    def put_immutable(self, key: str, data: bytes, sha256: str) -> None:
        _validate_digest(sha256)
        if not isinstance(data, bytes):
            raise TypeError("immutable object data must be bytes")
        if hashlib.sha256(data).hexdigest() != sha256:
            raise IntegrityError("provided immutable object digest does not match bytes")
        args = {
            "Bucket": self.bucket,
            "Key": self._key(key),
            "Body": data,
            "IfNoneMatch": "*",
        }
        try:
            self.client.put_object(**args)
        except Exception as error:
            if not _is_precondition_failure(error):
                raise
            try:
                existing = self.get_verified(key, sha256)
            except IntegrityError as verification_error:
                raise IntegrityError("immutable object key already contains different or missing bytes") from verification_error
            if existing != data:
                raise IntegrityError("immutable object key already contains different bytes") from error
            return
        stored = self.get_verified(key, sha256)
        if len(stored) != len(data) or stored != data:
            raise IntegrityError("immutable object failed post-write verification")

    def read_checkpoint(self, key: str) -> tuple[dict[str, Any] | None, str | None]:
        try:
            encoded, version = self._get(key)
        except Exception as error:
            if _is_missing(error):
                return None, None
            raise
        if not version:
            raise IntegrityError("checkpoint response omitted an opaque version")
        try:
            envelope = json.loads(encoded)
            body = envelope["body"]
            if not isinstance(body, dict):
                raise TypeError("invalid checkpoint body")
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise IntegrityError("checkpoint is not a valid stored document") from error
        return body, version

    def compare_and_swap_checkpoint(
        self, key: str, expected_version: str | None, body: dict[str, Any]
    ) -> str:
        encoded_body = _canonical_json(body)
        args: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": self._key(key),
            "Body": b"",  # replaced after the unique version is selected
        }
        version_token = uuid.uuid4().hex
        args["Body"] = _canonical_json({"body": json.loads(encoded_body), "version": version_token})
        if expected_version is None:
            args["IfNoneMatch"] = "*"
        else:
            args["IfMatch"] = expected_version
        try:
            response = self.client.put_object(**args)
        except Exception as error:
            if _is_precondition_failure(error):
                raise CheckpointConflict("checkpoint version changed") from error
            raise
        acknowledged_version = response.get("ETag") if isinstance(response, dict) else None
        if not acknowledged_version:
            raise IntegrityError("checkpoint write acknowledgement omitted an opaque version")
        actual_body, actual_version = self.read_checkpoint(key)
        if actual_body != body or actual_version != acknowledged_version:
            raise CheckpointConflict("checkpoint changed or failed verification after write")
        return acknowledged_version
