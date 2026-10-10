"""Deterministic synthetic model bundles for snapshot inference.

A bundle is the provenance authority for one seeded construction: three LightGBM
text boosters, two ONNX graphs, and a manifest of checksums. Actions cache may
only restore a directory whose fingerprint and file hashes still match.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import platform
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import torch

from src.models.dcn_v2 import MultiScaleDCNv2
from src.models.export_onnx import ONNXModelExporter
from src.models.quantile_lgbm import FEATURE_COLUMNS
from src.models.st_gnn import SpatioTemporalGNN
from src.serving.engine import SYNTHETIC_SEED, SYNTHETIC_TRAINING_ROWS, build_synthetic_baseline

BUNDLE_SEED = SYNTHETIC_SEED
DEFAULT_ESTIMATORS = 200
_DEPENDENCIES = ("lightgbm", "torch", "onnx", "onnxruntime", "numpy", "shap")
_SOURCE_FILES = (
    "models/quantile_lgbm.py",
    "models/dcn_v2.py",
    "models/st_gnn.py",
    "models/export_onnx.py",
    "serving/engine.py",
)
_SRC_ROOT = Path(__file__).resolve().parents[1]

# Incremented only when a new synthetic bundle is constructed. Tests use it to
# prove a warm load does not train.
_CONSTRUCT_COUNT = 0


class BundleError(ValueError):
    """A bundle is missing, corrupt, or the wrong provenance."""


@dataclass(frozen=True)
class ModelBundle:
    """Verified boosters and ONNX paths for one immutable model revision."""

    model_id: str
    provenance: str
    quantiles: dict[float, lgb.Booster]
    dcn_path: Path
    gnn_path: Path
    fingerprint: str
    root: Path


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dependency_versions() -> dict[str, str]:
    found: dict[str, str] = {}
    for name in _DEPENDENCIES:
        try:
            found[name] = version(name)
        except PackageNotFoundError as exc:
            raise BundleError(f"required model dependency {name} is not installed") from exc
    return found


def _source_digests() -> dict[str, str]:
    digests: dict[str, str] = {}
    for relative in _SOURCE_FILES:
        path = _SRC_ROOT / relative
        digests[relative] = _sha256(path.read_bytes())
    return digests


def bundle_fingerprint(
    *,
    rows: int = SYNTHETIC_TRAINING_ROWS,
    estimators: int = DEFAULT_ESTIMATORS,
) -> str:
    """Hash model code, features, pins, platform, and the construction seed."""
    payload = {
        "architecture": {
            "dcn": {"cross_layers": 3, "deep_hidden_dims": [64, 32], "dropout": 0.15, "in_features": 12},
            "gnn": {"in_features": 12, "num_nodes": 1, "seq_len": 4},
        },
        "dependencies": _dependency_versions(),
        "estimators": estimators,
        "features": list(FEATURE_COLUMNS),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "rows": rows,
        "seed": BUNDLE_SEED,
        "sources": _source_digests(),
        "system": platform.system(),
    }
    return _sha256(_canonical(payload))


def _file_sha(path: Path) -> str:
    return _sha256(path.read_bytes())


def _identity(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifacts": manifest["artifacts"],
        "dependencies": manifest["dependencies"],
        "estimators": manifest["estimators"],
        "features": manifest["features"],
        "fingerprint": manifest["fingerprint"],
        "provenance": manifest["provenance"],
        "rows": manifest["rows"],
        "seed": manifest["seed"],
    }


@contextmanager
def _exclusive(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _construct(dest: Path, fingerprint: str, rows: int, estimators: int) -> None:
    global _CONSTRUCT_COUNT
    _CONSTRUCT_COUNT += 1
    torch_state = torch.random.get_rng_state()
    numpy_state = np.random.get_state()
    try:
        torch.manual_seed(BUNDLE_SEED)
        np.random.seed(BUNDLE_SEED)
        predictor = build_synthetic_baseline(
            n_rows=rows,
            seed=BUNDLE_SEED,
            n_estimators=estimators,
            lgb_seed=BUNDLE_SEED,
        )
        quantiles = {
            0.1: "lgbm_p10.txt",
            0.5: "lgbm_p50.txt",
            0.9: "lgbm_p90.txt",
        }
        for alpha, name in quantiles.items():
            predictor.models[alpha].save_model(str(dest / name))
        exporter = ONNXModelExporter(output_dir=str(dest))
        exporter.export_dcn_v2(
            MultiScaleDCNv2(in_features=len(FEATURE_COLUMNS)),
            in_features=len(FEATURE_COLUMNS),
        )
        exporter.export_st_gnn(
            SpatioTemporalGNN(in_features=len(FEATURE_COLUMNS)),
            seq_len=4,
            num_nodes=1,
            in_features=len(FEATURE_COLUMNS),
        )
    finally:
        torch.random.set_rng_state(torch_state)
        np.random.set_state(numpy_state)

    artifacts = {
        name: _file_sha(dest / name)
        for name in ("lgbm_p10.txt", "lgbm_p50.txt", "lgbm_p90.txt", "dcn_v2_macro.onnx", "st_gnn_12m.onnx")
    }
    manifest: dict[str, Any] = {
        "artifacts": artifacts,
        "dependencies": _dependency_versions(),
        "estimators": estimators,
        "features": list(FEATURE_COLUMNS),
        "fingerprint": fingerprint,
        "provenance": "synthetic",
        "rows": rows,
        "schema_version": 1,
        "seed": BUNDLE_SEED,
    }
    manifest["model_id"] = _sha256(_canonical(_identity(manifest)))
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_bundle(path: Path, *, expected_provenance: str | None = None) -> ModelBundle:
    """Validate hashes, features, pins, and provenance before returning models."""
    root = Path(path)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise BundleError(f"bundle manifest is missing at {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise BundleError("bundle manifest is not valid JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise BundleError("bundle manifest schema is not supported")
    provenance = manifest.get("provenance")
    if provenance not in {"synthetic", "trained"}:
        raise BundleError(f"bundle provenance {provenance!r} is not supported")
    if expected_provenance is not None and provenance != expected_provenance:
        raise BundleError(
            f"bundle provenance is {provenance}, expected {expected_provenance}; "
            "refusing to mix model revisions"
        )
    if list(manifest.get("features") or []) != list(FEATURE_COLUMNS):
        raise BundleError("bundle feature order does not match FEATURE_COLUMNS")
    if manifest.get("dependencies") != _dependency_versions():
        raise BundleError("bundle dependency pins do not match the installed environment")
    expected_fingerprint = bundle_fingerprint(
        rows=int(manifest["rows"]),
        estimators=int(manifest["estimators"]),
    )
    if manifest.get("fingerprint") != expected_fingerprint:
        raise BundleError("bundle fingerprint does not match this code, seed, and platform")
    if provenance == "synthetic" and manifest.get("seed") != BUNDLE_SEED:
        raise BundleError("synthetic bundle seed is not 42")
    recomputed = _sha256(_canonical(_identity(manifest)))
    if manifest.get("model_id") != recomputed:
        raise BundleError("bundle model_id does not match its artifact identity")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise BundleError("bundle artifacts are missing")
    for name, digest in artifacts.items():
        file_path = root / str(name)
        if not file_path.is_file() or _file_sha(file_path) != digest:
            raise BundleError(f"bundle artifact {name} is missing or corrupt")
    quantiles = {
        0.1: lgb.Booster(model_file=str(root / "lgbm_p10.txt")),
        0.5: lgb.Booster(model_file=str(root / "lgbm_p50.txt")),
        0.9: lgb.Booster(model_file=str(root / "lgbm_p90.txt")),
    }
    return ModelBundle(
        model_id=str(manifest["model_id"]),
        provenance=str(provenance),
        quantiles=quantiles,
        dcn_path=root / "dcn_v2_macro.onnx",
        gnn_path=root / "st_gnn_12m.onnx",
        fingerprint=str(manifest["fingerprint"]),
        root=root,
    )


def load_trained_bundle(path: Path) -> ModelBundle:
    """Load a trained bundle. A missing or synthetic directory is an error."""
    root = Path(path)
    if not (root / "manifest.json").is_file():
        raise BundleError("trained bundle is missing; refusing synthetic fallback")
    return load_bundle(root, expected_provenance="trained")


def _declared_provenance(path: Path) -> str | None:
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    if isinstance(payload, dict):
        provenance = payload.get("provenance")
        return provenance if isinstance(provenance, str) else None
    return None


def ensure_synthetic_bundle(
    root: Path,
    *,
    rows: int = SYNTHETIC_TRAINING_ROWS,
    estimators: int = DEFAULT_ESTIMATORS,
) -> Path:
    """Return a verified synthetic bundle directory, building it atomically on a miss."""
    root = Path(root)
    fingerprint = bundle_fingerprint(rows=rows, estimators=estimators)
    dest = root / fingerprint
    with _exclusive(root / ".lock"):
        if _declared_provenance(dest) == "trained":
            raise BundleError("trained bundle is immutable; refusing synthetic fallback")
        try:
            loaded = load_bundle(dest, expected_provenance="synthetic")
        except BundleError:
            loaded = None
        if loaded is not None and loaded.fingerprint == fingerprint:
            return dest
        if dest.exists():
            shutil.rmtree(dest)
        temporary = root / f".tmp-{fingerprint}-{os.getpid()}"
        if temporary.exists():
            shutil.rmtree(temporary)
        temporary.mkdir(parents=True)
        try:
            _construct(temporary, fingerprint, rows, estimators)
            temporary.rename(dest)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        load_bundle(dest, expected_provenance="synthetic")
        return dest
