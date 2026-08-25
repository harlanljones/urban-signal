"""Unit tests for the Cloudflare KV snapshot builder (src/export/snapshot_builder.py)."""

import json
from pathlib import Path
from typing import Any

import pytest

from src.export.snapshot_builder import (
    CATALYST_THRESHOLD,
    DEFAULT_K_RING,
    DEFAULT_RESOLUTION,
    build_snapshot,
)
from src.spatial.city_registry import CityId


class StubEngine:
    """Deterministic stand-in for MultiHorizonInferenceEngine."""

    def predict_cell_features(
        self, h3_index: str, feature_dict: dict[str, Any], include_shap: bool = True
    ) -> dict[str, Any]:
        lims = float(feature_dict.get("lims_score", 50.0))
        pred = {
            "h3_index": h3_index,
            "resolution": DEFAULT_RESOLUTION,
            "centroid_lat": 40.7128,
            "centroid_lng": -74.006,
            "lims_score": lims,
            "delta_6m_p10": 0.01,
            "delta_6m_p50": 0.05,
            "delta_6m_p90": 0.09,
            "delta_12m_spillover": 0.12,
            "prob_18m_macro_outperformance": 0.5,
            "is_catalyst": lims >= CATALYST_THRESHOLD,
            "inference_latency_ms": 1.23,
        }
        if include_shap:
            pred["shap_attributions"] = {"capex_density_decayed": 100.0}
        return pred


@pytest.fixture
def snapshot(tmp_path: Path) -> dict[str, Any]:
    manifest = asyncio_run_build(tmp_path)
    return manifest


def asyncio_run_build(tmp_path: Path, cities=None) -> dict[str, Any]:
    import asyncio

    return asyncio.run(
        build_snapshot(tmp_path / "dist", engine=StubEngine(), cities=cities)
    )


def test_manifest_shape(snapshot: dict[str, Any]):
    assert set(snapshot["cities"]) == {city.value for city in CityId}
    assert snapshot["resolution"] == DEFAULT_RESOLUTION
    assert snapshot["k_ring"] == DEFAULT_K_RING
    assert snapshot["catalyst_threshold"] == CATALYST_THRESHOLD
    assert snapshot["generated_at"].endswith("+00:00") or "T" in snapshot["generated_at"]
    expected_keys = {"manifest"}
    for city in snapshot["cities"]:
        expected_keys |= {f"grid/{city}", f"catalysts/{city}", f"submarkets/{city}"}
    expected_keys.add("cells/index")
    assert expected_keys == set(snapshot["keys"])


def test_grid_artifact_is_feature_collection(snapshot: dict[str, Any], tmp_path: Path):
    grid = json.loads((tmp_path / "dist" / "grid" / "nyc.json").read_text())
    assert grid["type"] == "FeatureCollection"
    assert grid["city_id"] == "nyc"
    assert len(grid["features"]) > 0
    props = grid["features"][0]["properties"]
    assert "h3_index" in props
    assert "lims_score" in props
    assert "shap_attributions" not in props  # grid built with include_shap=False


def test_cells_index_covers_all_grid_hexes(snapshot: dict[str, Any], tmp_path: Path):
    cells = json.loads((tmp_path / "dist" / "cells.json").read_text())
    assert len(cells) == snapshot["cells"]
    for city in snapshot["cities"]:
        grid = json.loads((tmp_path / "dist" / "grid" / f"{city}.json").read_text())
        for feature in grid["features"]:
            h3_cell = feature["properties"]["h3_index"]
            assert h3_cell in cells
            assert "shap_attributions" in cells[h3_cell]


def test_catalysts_payload_schema(snapshot: dict[str, Any], tmp_path: Path):
    payload = json.loads((tmp_path / "dist" / "catalysts" / "chicago.json").read_text())
    assert payload["city_id"] == "chicago"
    assert payload["threshold"] == CATALYST_THRESHOLD
    assert payload["count"] == len(payload["catalysts"])
    for entry in payload["catalysts"]:
        assert entry["lims_score"] >= CATALYST_THRESHOLD
        assert "submarket" in entry and "borough" in entry


def test_kv_bulk_contains_all_keys(snapshot: dict[str, Any], tmp_path: Path):
    bulk = json.loads((tmp_path / "dist" / "kv-bulk.json").read_text())
    bulk_keys = {entry["key"] for entry in bulk}
    assert set(snapshot["keys"]) <= bulk_keys
    for entry in bulk:
        assert isinstance(entry["value"], str)
        json.loads(entry["value"])  # every value must be valid JSON


def test_subset_city_export(tmp_path: Path):
    manifest = asyncio_run_build(tmp_path, cities=["nyc"])
    assert manifest["cities"] == ["nyc"]
    bulk = json.loads((tmp_path / "dist" / "kv-bulk.json").read_text())
    assert {e["key"] for e in bulk} == {
        "manifest",
        "cells/index",
        "grid/nyc",
        "catalysts/nyc",
        "submarkets/nyc",
    }
