"""Tests for the national artifact validation gate (presentation of US-435 §24)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from scripts.validate_national_artifact import (
    NationalArtifactError,
    validate_national_artifact,
)

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_artifact(
    root,
    *,
    resolutions=(4, 5, 6),
    year: int = 2023,
    generated_at: datetime = NOW,
    hexes_with_jobs: int = 42,
    total_jobs: int = 1000,
    pointer_sha: str | None = None,
) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    aggregate = b""
    manifest: dict = {
        "generated_at": generated_at.isoformat(),
        "signal_source": "census_lehd_lodes8",
        "builder_revision": "1",
        "year": year,
        "resolutions": list(resolutions),
        "checksum_verified": True,
        "lodes_version": "v8",
    }
    for res in resolutions:
        res_dir = root / f"res{res}"
        res_dir.mkdir(parents=True, exist_ok=True)
        name = f"8{res}parent.parquet"
        data = f"res{res}-chunk-bytes".encode()
        (res_dir / name).write_bytes(data)
        aggregate += data
        report = {
            "generated_at": generated_at.isoformat(),
            "signal_source": "census_lehd_lodes8",
            "builder_revision": "1",
            "year": year,
            "resolution": res,
            "cells": 10,
            "hexes_with_jobs": hexes_with_jobs,
            "hexes_with_workers": 0,
            "total_jobs": total_jobs,
            "total_workers": 0,
            "chunks": {name: len(data)},
            "chunks_sha256": {name: _sha(data)},
        }
        (res_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")

    manifest["sha256"] = _sha(aggregate)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    pointer = {
        "artifact_key": f"national/census_lehd_lodes8/{year}/{manifest['sha256']}",
        "sha256": pointer_sha or manifest["sha256"],
        "signal_source": "census_lehd_lodes8",
        "builder_revision": "1",
        "lodes_version": "v8",
        "year": year,
        "resolutions": list(resolutions),
        "promoted_at": generated_at.isoformat(),
    }
    (root / "current.json").write_text(json.dumps(pointer), encoding="utf-8")
    return manifest


def test_valid_artifact_passes(tmp_path):
    _write_artifact(tmp_path)
    summary = validate_national_artifact(tmp_path, now=NOW)
    assert summary["year"] == 2023
    assert summary["resolutions"] == [4, 5, 6]
    assert summary["chunks"] == 3


def test_expected_year_is_enforced(tmp_path):
    _write_artifact(tmp_path)
    with pytest.raises(NationalArtifactError) as exc:
        validate_national_artifact(tmp_path, expected_year=2022, now=NOW)
    assert "year" in str(exc.value)


def test_missing_manifest_fails(tmp_path):
    (tmp_path / "res4").mkdir(parents=True)
    with pytest.raises(NationalArtifactError):
        validate_national_artifact(tmp_path, now=NOW)


def test_checksum_not_verified_fails(tmp_path):
    _write_artifact(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    manifest["checksum_verified"] = False
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(NationalArtifactError) as exc:
        validate_national_artifact(tmp_path, now=NOW)
    assert "checksum_verified" in str(exc.value)


def test_missing_resolution_fails(tmp_path):
    _write_artifact(tmp_path, resolutions=(4, 5))
    with pytest.raises(NationalArtifactError) as exc:
        validate_national_artifact(tmp_path, now=NOW)
    assert "missing required resolutions" in str(exc.value)


def test_empty_resolution_fails(tmp_path):
    _write_artifact(tmp_path)
    report_path = tmp_path / "res5" / "report.json"
    report = json.loads(report_path.read_text())
    report["chunks"] = {}
    report["hexes_with_jobs"] = 0
    report["total_jobs"] = 0
    report_path.write_text(json.dumps(report))
    with pytest.raises(NationalArtifactError) as exc:
        validate_national_artifact(tmp_path, now=NOW)
    assert "no data chunks" in str(exc.value)


def test_chunk_sha_mismatch_fails(tmp_path):
    _write_artifact(tmp_path)
    (tmp_path / "res6" / "86parent.parquet").write_bytes(b"tampered")
    with pytest.raises(NationalArtifactError) as exc:
        validate_national_artifact(tmp_path, now=NOW)
    assert "sha256 mismatch" in str(exc.value)


def test_aggregate_sha_mismatch_fails(tmp_path):
    _write_artifact(tmp_path)
    # Tamper a chunk and fix its per-chunk hash so only the aggregate catches it.
    name = "84parent.parquet"
    path = tmp_path / "res4" / name
    path.write_bytes(b"replaced-with-different-length")
    report_path = tmp_path / "res4" / "report.json"
    report = json.loads(report_path.read_text())
    report["chunks_sha256"][name] = _sha(path.read_bytes())
    report_path.write_text(json.dumps(report))
    with pytest.raises(NationalArtifactError) as exc:
        validate_national_artifact(tmp_path, now=NOW)
    assert "aggregate sha256" in str(exc.value)


def test_pointer_sha_mismatch_fails(tmp_path):
    _write_artifact(tmp_path, pointer_sha="0" * 64)
    with pytest.raises(NationalArtifactError) as exc:
        validate_national_artifact(tmp_path, now=NOW)
    assert "current pointer" in str(exc.value)


def test_stale_artifact_fails(tmp_path):
    _write_artifact(tmp_path, generated_at=NOW - timedelta(days=500))
    with pytest.raises(NationalArtifactError) as exc:
        validate_national_artifact(tmp_path, max_age_days=400, now=NOW)
    assert "age" in str(exc.value)


def test_zero_totals_fail(tmp_path):
    _write_artifact(tmp_path, hexes_with_jobs=0, total_jobs=0)
    with pytest.raises(NationalArtifactError) as exc:
        validate_national_artifact(tmp_path, now=NOW)
    assert "no measured hexes" in str(exc.value)
