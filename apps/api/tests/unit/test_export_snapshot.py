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


def asyncio_run_build(
    tmp_path: Path,
    cities=None,
    include_legacy_cells: bool = True,
    national_dir: Path | None = None,
) -> dict[str, Any]:
    import asyncio

    return asyncio.run(
        build_snapshot(
            tmp_path / "dist",
            engine=StubEngine(),
            cities=cities,
            include_legacy_cells=include_legacy_cells,
            national_dir=national_dir,
        )
    )


def test_manifest_shape(snapshot: dict[str, Any]):
    assert set(snapshot["cities"]) == {city.value for city in CityId}
    assert snapshot["resolution"] == DEFAULT_RESOLUTION
    assert snapshot["k_ring"] == DEFAULT_K_RING
    assert snapshot["catalyst_threshold"] == CATALYST_THRESHOLD
    assert snapshot["generated_at"].endswith("+00:00") or "T" in snapshot["generated_at"]
    assert snapshot["cells_sharded"] is True
    expected_keys = {"manifest", "cells/index", "cells/index_meta", "catalysts/index"}
    for city in snapshot["cities"]:
        expected_keys |= {f"grid/{city}", f"catalysts/{city}", f"submarkets/{city}"}
    for parent in snapshot["tile_index"]:
        expected_keys.add(f"gridtiles/{parent}")
    keys = set(snapshot["keys"])
    cell_shards = {key for key in keys if key.startswith("cells/") and key != "cells/index_meta"}
    assert expected_keys | cell_shards == keys


def test_per_cell_shards_match_legacy_cells(snapshot: dict[str, Any], tmp_path: Path):
    """During the compat window every per-cell shard must exist in legacy cells/index."""
    legacy = json.loads((tmp_path / "dist" / "cells.json").read_text())
    keys = set(snapshot["keys"])
    cell_shards = {
        key.removeprefix("cells/")
        for key in keys
        if key.startswith("cells/") and key not in ("cells/index", "cells/index_meta")
    }
    assert cell_shards == set(legacy)
    meta = json.loads((tmp_path / "dist" / "cells" / "index_meta.json").read_text())
    assert meta["sharded"] is True
    assert meta["total"] == len(legacy)
    for cell, pred in legacy.items():
        shard = json.loads((tmp_path / "dist" / "cells" / f"{cell}.json").read_text())
        assert shard == pred


def test_skip_legacy_cells_omits_single_key(tmp_path: Path):
    manifest = asyncio_run_build(tmp_path, cities=["nyc"], include_legacy_cells=False)
    keys = set(manifest["keys"])
    assert "cells/index" not in keys
    assert "cells/index_meta" in keys
    cell_shards = {key for key in keys if key.startswith("cells/") and key != "cells/index_meta"}
    assert cell_shards


# ---------------------------------------------------------------------------
# National layer publishing (US-383)
# ---------------------------------------------------------------------------

NATIONAL_FIXTURE_COLUMNS = (
    "h3_index",
    "jobs_c000",
    "workers_c000",
    "jobs_c000_national_pct",
    "workers_c000_national_pct",
    "year",
    "signal_source",
)


def _national_fixture_frame(rows: list[dict[str, Any]]):
    import polars as pl

    return pl.DataFrame(
        rows,
        schema={
            "h3_index": pl.String,
            "jobs_c000": pl.Int64,
            "workers_c000": pl.Int64,
            "jobs_c000_national_pct": pl.Float64,
            "workers_c000_national_pct": pl.Float64,
            "year": pl.Int64,
            "signal_source": pl.String,
        },
    )


def _write_national_fixture(root: Path) -> tuple[str, str]:
    """Two res-6 res-3 chunks (one with data, one all-null) + one res-4 chunk.

    Returns (parent_with_data, parent_all_null).
    """
    cell_nyc = h3.latlng_to_cell(40.7128, -74.006, 6)
    cell_la = h3.latlng_to_cell(34.0522, -118.2437, 6)
    parent_data = h3.cell_to_parent(cell_nyc, 3)
    parent_null = h3.cell_to_parent(cell_la, 3)
    assert parent_data != parent_null

    res6_dir = root / "national" / "res6"
    res6_dir.mkdir(parents=True, exist_ok=True)
    _national_fixture_frame(
        [
            {
                "h3_index": cell_nyc,
                "jobs_c000": 1200,
                "workers_c000": 900,
                "jobs_c000_national_pct": 71.5,
                "workers_c000_national_pct": 66.25,
                "year": 2023,
                "signal_source": "census_lehd_lodes8",
            },
            {
                "h3_index": h3.latlng_to_cell(40.7135, -74.005, 6),
                "jobs_c000": 300,
                "workers_c000": None,
                "jobs_c000_national_pct": 40.0,
                "workers_c000_national_pct": None,
                "year": 2023,
                "signal_source": "census_lehd_lodes8",
            },
            {
                # all-null row: must be dropped from the published chunk
                "h3_index": h3.latlng_to_cell(40.714, -74.004, 6),
                "jobs_c000": None,
                "workers_c000": None,
                "jobs_c000_national_pct": None,
                "workers_c000_national_pct": None,
                "year": 2023,
                "signal_source": "census_lehd_lodes8",
            },
        ]
    ).write_parquet(res6_dir / f"{parent_data}.parquet")
    _national_fixture_frame(
        [
            {
                "h3_index": cell_la,
                "jobs_c000": None,
                "workers_c000": None,
                "jobs_c000_national_pct": None,
                "workers_c000_national_pct": None,
                "year": 2023,
                "signal_source": "census_lehd_lodes8",
            }
        ]
    ).write_parquet(res6_dir / f"{parent_null}.parquet")

    res4_dir = root / "national" / "res4"
    res4_dir.mkdir(parents=True, exist_ok=True)
    _national_fixture_frame(
        [
            {
                "h3_index": h3.cell_to_parent(cell_nyc, 4),
                "jobs_c000": 1500,
                "workers_c000": 950,
                "jobs_c000_national_pct": 88.0,
                "workers_c000_national_pct": 80.5,
                "year": 2023,
                "signal_source": "census_lehd_lodes8",
            }
        ]
    ).write_parquet(res4_dir / f"{h3.cell_to_parent(cell_nyc, 3)}.parquet")
    return parent_data, parent_null


def test_national_layers_published_from_national_dir(tmp_path: Path):
    import hashlib

    national_dir = tmp_path / "national-out"
    parent_data, parent_null = _write_national_fixture(national_dir)

    manifest = asyncio_run_build(tmp_path, cities=["nyc"], national_dir=national_dir)

    assert "national" in manifest
    block = manifest["national"]["resolutions"]
    assert block["6"] == {"count": 2, "chunks": 1}
    assert block["4"] == {"count": 1, "chunks": 1}

    keys = set(manifest["keys"])
    assert f"national/6/{parent_data}" in keys
    assert "national/index" in keys
    # all-null chunk is skipped — absent key means "no data" on the route
    assert f"national/6/{parent_null}" not in keys

    chunk = json.loads((tmp_path / "dist" / "national" / "6" / f"{parent_data}.json").read_text())
    assert chunk["cols"] == ["h3", "jobs", "workers", "jobs_pct", "workers_pct"]
    assert chunk["year"] == 2023
    assert chunk["signal_source"] == "census_lehd_lodes8"
    assert [row[0] for row in chunk["rows"]] == sorted(row[0] for row in chunk["rows"])
    assert len(chunk["rows"]) == 2
    for row in chunk["rows"]:
        assert row[1] is not None or row[2] is not None

    index = json.loads((tmp_path / "dist" / "national" / "index.json").read_text())
    res6 = index["resolutions"]["6"]
    assert res6["parents"] == [parent_data]
    assert res6["count"] == 2
    assert res6["chunks"][parent_data]["rows"] == 2
    assert res6["chunks"][parent_data]["sha256"] == hashlib.sha256(
        (tmp_path / "dist" / "national" / "6" / f"{parent_data}.json").read_bytes()
    ).hexdigest()
    assert res6["byte_size"] == res6["chunks"][parent_data]["bytes"]


def test_national_absent_by_default(snapshot: dict[str, Any]):
    assert "national" not in snapshot
    assert not [key for key in snapshot["keys"] if key.startswith("national/")]


def test_national_chunk_over_budget_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.export import snapshot_builder as sb

    monkeypatch.setattr(sb, "NATIONAL_MAX_CHUNK_BYTES", 10)
    national_dir = tmp_path / "national-out"
    _write_national_fixture(national_dir)
    with pytest.raises(ValueError, match="US-383 budget"):
        asyncio_run_build(tmp_path, cities=["nyc"], national_dir=national_dir)


def test_manifest_boot_payload_national_regression(tmp_path: Path):
    """Acceptance: national block must not bloat the boot manifest by >10%."""
    national_dir = tmp_path / "national-out"
    _write_national_fixture(national_dir)

    before = asyncio_run_build(tmp_path / "b", cities=["nyc"])
    after = asyncio_run_build(tmp_path / "a", cities=["nyc"], national_dir=national_dir)

    size_before = len(json.dumps(before, separators=(",", ":")))
    size_after = len(json.dumps(after, separators=(",", ":")))
    regression = (size_after - size_before) / size_before
    assert regression < 0.10, (
        f"national manifest block grew the boot payload by {regression:.1%} "
        f"({size_before} -> {size_after} bytes); move detail into national/index"
    )


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
    bulk_keys = {e["key"] for e in bulk}
    cell_shards = {
        key for key in bulk_keys if key.startswith("cells/") and key != "cells/index_meta"
    }
    # No keys from unselected cities may leak; cell shards are exactly nyc's cells.
    assert bulk_keys == {
        "manifest",
        "cells/index",
        "cells/index_meta",
        "catalysts/index",
        "grid/nyc",
        "catalysts/nyc",
        "submarkets/nyc",
        *{f"gridtiles/{parent}" for parent in manifest["tile_index"]},
        *cell_shards,
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
    for features in _all_grid_features(tmp_path, snapshot["cities"]).values():
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
