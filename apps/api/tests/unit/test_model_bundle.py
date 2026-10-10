"""Deterministic synthetic bundle construction and refusal paths."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Barrier, Thread

import pytest

from src.models import bundle as bundle_module
from src.models.bundle import (
    BundleError,
    bundle_fingerprint,
    ensure_synthetic_bundle,
    load_bundle,
    load_trained_bundle,
)
from src.models.quantile_lgbm import FEATURE_COLUMNS
from src.serving.engine import MultiHorizonInferenceEngine

ROWS = 40
ESTIMATORS = 5


def _vector() -> dict[str, float]:
    return {name: float(index) for index, name in enumerate(FEATURE_COLUMNS)}


def test_cold_and_warm_bundles_match_and_warm_does_not_rebuild(tmp_path: Path):
    before = bundle_module._CONSTRUCT_COUNT
    first = ensure_synthetic_bundle(tmp_path, rows=ROWS, estimators=ESTIMATORS)
    built = bundle_module._CONSTRUCT_COUNT
    second = ensure_synthetic_bundle(tmp_path, rows=ROWS, estimators=ESTIMATORS)
    assert first == second
    assert bundle_module._CONSTRUCT_COUNT == built
    assert built == before + 1

    cold = load_bundle(first, expected_provenance="synthetic")
    warm = load_bundle(second, expected_provenance="synthetic")
    row = [[float(index) for index in range(len(FEATURE_COLUMNS))]]
    for alpha in (0.1, 0.5, 0.9):
        assert cold.quantiles[alpha].predict(row) == pytest.approx(warm.quantiles[alpha].predict(row))
    assert cold.model_id == warm.model_id
    assert cold.fingerprint == bundle_fingerprint(rows=ROWS, estimators=ESTIMATORS)


def test_loading_a_valid_bundle_does_not_train_or_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = ensure_synthetic_bundle(tmp_path, rows=ROWS, estimators=ESTIMATORS)

    def fail(*_args, **_kwargs):
        raise AssertionError("bundle load must not construct models")

    monkeypatch.setattr(bundle_module, "build_synthetic_baseline", fail)
    monkeypatch.setattr(bundle_module.ONNXModelExporter, "export_dcn_v2", fail)
    monkeypatch.setattr(bundle_module.ONNXModelExporter, "export_st_gnn", fail)
    loaded = load_bundle(path)
    assert loaded.provenance == "synthetic"
    engine = MultiHorizonInferenceEngine(model_bundle=path, cache_predictions=False)
    prediction = engine.predict_cell_features("892a10708b7ffff", _vector(), include_shap=False)
    assert prediction["h3_index"] == "892a10708b7ffff"
    assert engine.model_provenance == "synthetic"
    assert engine.model_bundle_id == loaded.model_id


def test_partial_bundle_is_rebuilt(tmp_path: Path):
    path = ensure_synthetic_bundle(tmp_path, rows=ROWS, estimators=ESTIMATORS)
    (path / "lgbm_p50.txt").unlink()
    with pytest.raises(BundleError, match="missing or corrupt"):
        load_bundle(path)
    before = bundle_module._CONSTRUCT_COUNT
    rebuilt = ensure_synthetic_bundle(tmp_path, rows=ROWS, estimators=ESTIMATORS)
    assert rebuilt == path
    assert bundle_module._CONSTRUCT_COUNT == before + 1
    load_bundle(rebuilt, expected_provenance="synthetic")


def test_corrupt_checksum_is_rejected(tmp_path: Path):
    path = ensure_synthetic_bundle(tmp_path, rows=ROWS, estimators=ESTIMATORS)
    manifest_path = path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"]["dcn_v2_macro.onnx"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(BundleError, match="model_id|corrupt"):
        load_bundle(path)


def test_feature_dependency_and_seed_changes_are_rejected(tmp_path: Path):
    path = ensure_synthetic_bundle(tmp_path, rows=ROWS, estimators=ESTIMATORS)
    manifest_path = path / "manifest.json"
    original = manifest_path.read_text()

    def rewrite(**updates: object) -> None:
        manifest = json.loads(original)
        manifest.update(updates)
        manifest_path.write_text(json.dumps(manifest))

    rewrite(features=["not-a-feature"])
    with pytest.raises(BundleError, match="feature order"):
        load_bundle(path)

    rewrite(dependencies={"lightgbm": "0"})
    with pytest.raises(BundleError, match="dependency"):
        load_bundle(path)

    rewrite(seed=7)
    with pytest.raises(BundleError, match="seed|fingerprint|model_id"):
        load_bundle(path)


def test_fingerprint_changes_when_construction_settings_change():
    assert bundle_fingerprint(rows=ROWS, estimators=ESTIMATORS) != bundle_fingerprint(
        rows=ROWS + 1,
        estimators=ESTIMATORS,
    )


def test_concurrent_ensure_builds_once(tmp_path: Path):
    barrier = Barrier(4)
    found: list[Path] = []

    def worker() -> None:
        barrier.wait()
        found.append(ensure_synthetic_bundle(tmp_path, rows=ROWS, estimators=ESTIMATORS))

    before = bundle_module._CONSTRUCT_COUNT
    threads = [Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(found) == 4
    assert len(set(found)) == 1
    assert bundle_module._CONSTRUCT_COUNT == before + 1
    load_bundle(found[0], expected_provenance="synthetic")


def test_trained_bundle_is_not_replaced_by_synthetic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    fingerprint = bundle_fingerprint(rows=ROWS, estimators=ESTIMATORS)
    trained = tmp_path / fingerprint
    trained.mkdir()
    (trained / "manifest.json").write_text(json.dumps({"provenance": "trained"}))

    def fail(*_args, **_kwargs):
        raise AssertionError("synthetic construction must not run")

    monkeypatch.setattr(bundle_module, "_construct", fail)
    with pytest.raises(BundleError, match="refusing synthetic fallback"):
        ensure_synthetic_bundle(tmp_path, rows=ROWS, estimators=ESTIMATORS)
    with pytest.raises(BundleError, match="refusing synthetic fallback"):
        load_trained_bundle(tmp_path / "missing-trained")
