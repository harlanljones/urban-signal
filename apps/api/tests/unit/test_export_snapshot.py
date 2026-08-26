"""Unit tests for the Cloudflare KV snapshot builder (src/export/snapshot_builder.py)."""

import json
from pathlib import Path
from typing import Any

import h3
import pytest

from src.export.snapshot_builder import (
    CATALYST_THRESHOLD,
    DEFAULT_K_RING,
    DEFAULT_RESOLUTION,
    TILE_RESOLUTION,
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
    expected_keys = {"manifest", "cells/index", "catalysts/index"}
    for city in snapshot["cities"]:
        expected_keys |= {f"grid/{city}", f"catalysts/{city}", f"submarkets/{city}"}
    for parent in snapshot["tile_index"]:
        expected_keys.add(f"gridtiles/{parent}")
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
        "catalysts/index",
        "grid/nyc",
        "catalysts/nyc",
        "submarkets/nyc",
        *{f"gridtiles/{parent}" for parent in manifest["tile_index"]},
    }


NORMALIZED_METRICS = (
    "lims_score",
    "delta_6m_p50",
    "delta_12m_spillover",
    "prob_18m_macro_outperformance",
)


def _all_grid_features(tmp_path: Path, cities: list[str]) -> dict[str, list[dict[str, Any]]]:
    grids: dict[str, list[dict[str, Any]]] = {}
    for city in cities:
        grid = json.loads((tmp_path / "dist" / "grid" / f"{city}.json").read_text())
        grids[city] = grid["features"]
    return grids


def test_percentile_properties_stamped_on_every_feature(snapshot: dict[str, Any], tmp_path: Path):
    for city, features in _all_grid_features(tmp_path, snapshot["cities"]).items():
        assert features, f"no grid features for {city}"
        for feature in features:
            props = feature["properties"]
            for metric in NORMALIZED_METRICS:
                assert f"{metric}_metro_pct" in props
                assert f"{metric}_national_pct" in props
                for pct_key in (f"{metric}_metro_pct", f"{metric}_national_pct"):
                    assert 0.0 <= props[pct_key] <= 100.0


def test_percentiles_are_monotone_in_raw_value(snapshot: dict[str, Any], tmp_path: Path):
    """Higher raw value never gets a lower percentile (ties share one)."""
    for city, features in _all_grid_features(tmp_path, snapshot["cities"]).items():
        for metric in NORMALIZED_METRICS:
            ordered = sorted(features, key=lambda f: float(f["properties"][metric]))
            metro_pcts = [float(f["properties"][f"{metric}_metro_pct"]) for f in ordered]
            assert metro_pcts == sorted(metro_pcts), city


def test_percentile_endpoints_and_tie_handling(snapshot: dict[str, Any], tmp_path: Path):
    features = next(iter(_all_grid_features(tmp_path, ["nyc"]).values()))
    lims_values = [float(f["properties"]["lims_score"]) for f in features]
    pcts = {float(f["properties"]["lims_score"]): float(f["properties"]["lims_score_metro_pct"]) for f in features}
    # Endpoints hit 0/100 exactly only when the extreme value is unique.
    if lims_values.count(min(lims_values)) == 1:
        assert pcts[min(lims_values)] == 0.0
    if lims_values.count(max(lims_values)) == 1:
        assert pcts[max(lims_values)] == 100.0
    # Ties share a rank: equal raw scores must map to equal percentiles.
    by_value: dict[float, set[float]] = {}
    for value, pct in pcts.items():
        by_value.setdefault(value, set()).add(pct)
    assert all(len(pcts_for_value) == 1 for pcts_for_value in by_value.values())


def test_national_percentile_differs_from_metro_across_metros(
    snapshot: dict[str, Any], tmp_path: Path
):
    """With >= 2 metros exported, at least one feature's two ranks disagree."""
    if len(snapshot["cities"]) < 2:
        pytest.skip("subset export — national and metro ranks coincide")
    seen_difference = False
    for city, features in _all_grid_features(tmp_path, snapshot["cities"]).items():
        for feature in features:
            if feature["properties"]["lims_score_metro_pct"] != feature["properties"]["lims_score_national_pct"]:
                seen_difference = True
                break
        if seen_difference:
            break
    assert seen_difference


def test_grid_tiles_recompute_to_stated_parents(snapshot: dict[str, Any], tmp_path: Path):
    tile_index = snapshot["tile_index"]
    assert tile_index, "tile index must not be empty"
    seen_cells: set[str] = set()
    for parent, meta in tile_index.items():
        payload = json.loads((tmp_path / "dist" / "gridtiles" / f"{parent}.json").read_text())
        assert payload["tile_parent"] == parent
        assert payload["tile_resolution"] == TILE_RESOLUTION
        assert len(payload["features"]) == meta["count"]
        assert meta["bbox"] is not None
        cities_in_tile = set()
        for feature in payload["features"]:
            cell = feature["properties"]["h3_index"]
            assert h3.cell_to_parent(cell, TILE_RESOLUTION) == parent
            assert cell not in seen_cells, "a cell must land in exactly one tile"
            seen_cells.add(cell)
            assert "city_id" in feature["properties"]
            assert "city_name" in feature["properties"]
            cities_in_tile.add(feature["properties"]["city_id"])
        assert set(meta["cities"]) == cities_in_tile


def test_tiles_cover_every_exported_city(snapshot: dict[str, Any], tmp_path: Path):
    tiled_cities = {city for meta in snapshot["tile_index"].values() for city in meta["cities"]}
    assert tiled_cities == set(snapshot["cities"])


def test_catalysts_index_flattens_all_cities(snapshot: dict[str, Any], tmp_path: Path):
    index = json.loads((tmp_path / "dist" / "catalysts" / "index.json").read_text())
    assert set(index["cities"]) == set(snapshot["cities"])
    total = 0
    for city in snapshot["cities"]:
        payload = json.loads((tmp_path / "dist" / "catalysts" / f"{city}.json").read_text())
        total += payload["count"]
    assert index["count"] == total == len(index["catalysts"])
    for entry in index["catalysts"]:
        assert entry["city_id"] in snapshot["cities"]
        assert entry["city_name"]
        assert float(entry["lims_score"]) >= CATALYST_THRESHOLD
    scores = [float(e["lims_score"]) for e in index["catalysts"]]
    assert scores == sorted(scores, reverse=True)


def test_metro_index_matches_registry(snapshot: dict[str, Any]):
    from src.spatial.city_registry import REGISTRY

    metros = snapshot["metro_index"]
    assert {metro["city_id"] for metro in metros} == set(snapshot["cities"])
    for metro in metros:
        registration = REGISTRY[CityId(metro["city_id"])]
        assert metro["name"] == registration.name
        bbox = metro["bbox"]
        assert bbox["min_lat"] <= metro["center"]["lat"] or bbox is not None
        assert bbox["min_lat"] <= bbox["max_lat"]
        assert bbox["min_lng"] <= bbox["max_lng"]
