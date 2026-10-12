"""Tests for snapshot metrics and benchmark output comparison."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.benchmark_snapshot import compare_snapshot_outputs

from src.export.snapshot_metrics import SnapshotMetrics


def test_stage_durations_and_schema_are_written(tmp_path: Path):
    metrics = SnapshotMetrics(provenance={"model_mode": "synthetic-default"})
    with metrics.stage("city_inference"):
        metrics.increment("inference_calls", 2)

    path = tmp_path / "snapshot-metrics.json"
    metrics.write(path)

    payload = json.loads(path.read_text())
    assert payload["schema_version"] == 1
    assert payload["durations_seconds"]["city_inference"] >= 0
    assert payload["counters"]["inference_calls"] == 2
    assert payload["provenance"]["model_mode"] == "synthetic-default"
    assert set(payload) == {
        "schema_version", "durations_seconds", "counters", "artifacts", "provenance"
    }


def test_counters_are_thread_safe():
    metrics = SnapshotMetrics()
    with ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(lambda _: metrics.increment("calls"), range(100)))
    assert metrics.snapshot()["counters"]["calls"] == 100


def test_missing_context_is_explicit():
    metrics = SnapshotMetrics(context_dir=Path("/context/that/does/not/exist"))
    assert metrics.snapshot()["provenance"]["context"]["available"] is False


def test_comparator_ignores_only_run_noise_and_detects_semantic_changes():
    baseline = {
        "manifest": {"generated_at": "2026-01-01", "cities": ["nyc"]},
        "cells/index_meta": {"generated_at": "2026-01-01", "total": 2},
        "national/index": {"generated_at": "2026-01-01", "year": 2023},
        "cells/a": {"prediction": 0.2, "inference_latency_ms": 2.0},
        "grid/nyc": {"properties": {"rank": 50.0}},
    }
    latency_only = {
        "manifest": {"generated_at": "2026-01-02", "cities": ["nyc"]},
        "cells/index_meta": {"generated_at": "2026-01-02", "total": 2},
        "national/index": {"generated_at": "2026-01-02", "year": 2023},
        "cells/a": {"prediction": 0.2, "inference_latency_ms": 5.0},
        "grid/nyc": {"properties": {"rank": 50.0}},
    }
    assert compare_snapshot_outputs(baseline, latency_only)["equal"] is True

    changed_source_date = {
        **latency_only,
        "national/index": {"generated_at": "2026-01-02", "year": 2024},
    }
    assert compare_snapshot_outputs(baseline, changed_source_date)["equal"] is False

    for altered in (
        {**baseline, "cells/a": {"prediction": 0.3, "inference_latency_ms": 2.0}},
        {**baseline, "grid/nyc": {"properties": {"rank": 51.0}}},
        {"manifest": baseline["manifest"], "grid/nyc": baseline["grid/nyc"]},
    ):
        result = compare_snapshot_outputs(baseline, altered)
        assert result["equal"] is False
        assert result["differences"]


def test_comparator_detects_prediction_rank_or_coverage_change():
    baseline = {
        "cells/a": {"delta_6m_p50": 0.1},
        "grid/nyc": {"features": [{"properties": {"lims_score_national_pct": 70.0}}]},
    }
    changed_prediction = {
        "cells/a": {"delta_6m_p50": 0.2},
        "grid/nyc": baseline["grid/nyc"],
    }
    changed_rank = {
        "cells/a": baseline["cells/a"],
        "grid/nyc": {"features": [{"properties": {"lims_score_national_pct": 71.0}}]},
    }
    changed_coverage = {"cells/a": baseline["cells/a"]}
    for candidate in (changed_prediction, changed_rank, changed_coverage):
        assert compare_snapshot_outputs(baseline, candidate)["equal"] is False


def test_comparator_validates_derived_bytes_for_grid_and_catalyst_latency():
    from copy import deepcopy

    baseline = {
        "grid/nyc": {"features": [{"inference_latency_ms": 12.34, "score": 0.2}]},
        "catalysts/nyc": {"items": [{"inference_latency_ms": 12.34, "score": 0.2}]},
    }
    candidate = deepcopy(baseline)
    candidate["grid/nyc"]["features"][0]["inference_latency_ms"] = 0.0
    candidate["catalysts/nyc"]["items"][0]["inference_latency_ms"] = 0.0
    for output in (baseline, candidate):
        output["manifest"] = {"keys": {
            key: {"bytes": len(json.dumps(value, separators=(",", ":")).encode())}
            for key, value in output.items()
        }}
    assert compare_snapshot_outputs(baseline, candidate)["equal"]
    candidate["manifest"]["keys"]["grid/nyc"]["bytes"] += 1
    assert not compare_snapshot_outputs(baseline, candidate)["equal"]


def test_snapshot_builder_tracks_regions_rebuilt_and_skipped(tmp_path: Path):
    import asyncio

    from src.export.snapshot_builder import build_snapshot
    from tests.unit.test_export_snapshot import StubEngine

    out_1 = tmp_path / "snap-1"
    metrics_1 = tmp_path / "metrics-1.json"
    manifest_1 = asyncio.run(
        build_snapshot(
            out_1,
            engine=StubEngine(),
            cities=["nyc", "chicago"],
            dense_metro=True,
            include_legacy_cells=False,
            metrics_out=metrics_1,
        )
    )
    report_1 = json.loads(metrics_1.read_text())
    assert report_1["regions_rebuilt"] == 2
    assert report_1["regions_skipped"] == 0
    assert report_1["regions_failed"] == 0
    assert "regions" in manifest_1
    assert "rank_epoch" in manifest_1

    out_2 = tmp_path / "snap-2"
    metrics_2 = tmp_path / "metrics-2.json"
    manifest_2 = asyncio.run(
        build_snapshot(
            out_2,
            engine=StubEngine(),
            cities=["nyc", "chicago"],
            dense_metro=True,
            include_legacy_cells=False,
            metrics_out=metrics_2,
            previous_regions=out_1,
        )
    )
    report_2 = json.loads(metrics_2.read_text())
    assert report_2["regions_rebuilt"] == 0
    assert report_2["regions_skipped"] == 2
    assert report_2["regions_failed"] == 0
    assert manifest_2["regions"] == manifest_1["regions"]
