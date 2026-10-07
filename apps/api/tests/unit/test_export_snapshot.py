"""Unit tests for the Cloudflare KV snapshot builder (src/export/snapshot_builder.py)."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import h3
import pytest

from src.export import snapshot_builder
from src.export.snapshot_builder import (
    CATALYST_THRESHOLD,
    DEFAULT_K_RING,
    DEFAULT_RESOLUTION,
    LOD_RESOLUTIONS,
    LOD_TILE_PARENT_RES,
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
    require_national: bool = False,
    context_dir: Path | None = None,
    metrics=None,
) -> dict[str, Any]:
    import asyncio

    return asyncio.run(
        build_snapshot(
            tmp_path / "dist",
            engine=StubEngine(),
            cities=cities,
            include_legacy_cells=include_legacy_cells,
            national_dir=national_dir,
            require_national=require_national,
            context_dir=context_dir,
            metrics=metrics,
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
    for res in LOD_RESOLUTIONS:
        for parent in snapshot["tile_indexes"][str(res)]:
            expected_keys.add(f"gridtiles_res{res}/{parent}")
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
    assert (
        res6["chunks"][parent_data]["sha256"]
        == hashlib.sha256(
            (tmp_path / "dist" / "national" / "6" / f"{parent_data}.json").read_bytes()
        ).hexdigest()
    )
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


def _write_national_res5_chunk(root: Path) -> None:
    """Add a one-row res-5 chunk so the fixture covers all required resolutions."""
    cell = h3.latlng_to_cell(40.7128, -74.006, 5)
    res5_dir = root / "national" / "res5"
    res5_dir.mkdir(parents=True, exist_ok=True)
    _national_fixture_frame(
        [
            {
                "h3_index": cell,
                "jobs_c000": 5000,
                "workers_c000": 4200,
                "jobs_c000_national_pct": 90.0,
                "workers_c000_national_pct": 88.0,
                "year": 2023,
                "signal_source": "census_lehd_lodes8",
            }
        ]
    ).write_parquet(res5_dir / f"{h3.cell_to_parent(cell, 3)}.parquet")


def test_require_national_rejects_metro_only(tmp_path: Path):
    """Production mode must fail, not silently publish metro-only (US-435 §24)."""
    with pytest.raises(ValueError, match="require-national"):
        asyncio_run_build(tmp_path, cities=["nyc"], require_national=True)


def test_require_national_rejects_incomplete_resolutions(tmp_path: Path):
    """The base fixture covers res-4 + res-6 only; require mode must reject it."""
    national_dir = tmp_path / "national-out"
    _write_national_fixture(national_dir)
    with pytest.raises(ValueError, match="missing resolutions"):
        asyncio_run_build(
            tmp_path, cities=["nyc"], national_dir=national_dir, require_national=True
        )


def test_require_national_accepts_complete_publish(tmp_path: Path):
    national_dir = tmp_path / "national-out"
    _write_national_fixture(national_dir)
    _write_national_res5_chunk(national_dir)
    manifest = asyncio_run_build(
        tmp_path, cities=["nyc"], national_dir=national_dir, require_national=True
    )
    assert set(manifest["national"]["resolutions"]) >= {"4", "5", "6"}


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
    lod_keys = {
        f"gridtiles_res{res}/{parent}"
        for res in LOD_RESOLUTIONS
        for parent in manifest["tile_indexes"][str(res)]
    }
    # Release-qualified twins + snapshot/current pointer are additive; the
    # logical set is unchanged and no unselected-city keys leak.
    logical = {
        "manifest",
        "cells/index",
        "cells/index_meta",
        "catalysts/index",
        "grid/nyc",
        "catalysts/nyc",
        "submarkets/nyc",
        *{f"gridtiles/{parent}" for parent in manifest["tile_index"]},
        *lod_keys,
        *cell_shards,
    }
    release_keys = {f"releases/{manifest['snapshot_id']}/{key}" for key in logical}
    assert bulk_keys == logical | release_keys | {"snapshot/current"}


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
    pcts = {
        float(f["properties"]["lims_score"]): float(f["properties"]["lims_score_metro_pct"])
        for f in features
    }
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
            if (
                feature["properties"]["lims_score_metro_pct"]
                != feature["properties"]["lims_score_national_pct"]
            ):
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


# ---------------------------------------------------------------------------
# snapshot_id + coverage block (hex-coverage Stage A)
# ---------------------------------------------------------------------------

SNAPSHOT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def test_snapshot_id_format(snapshot: dict[str, Any]):
    sid = snapshot["snapshot_id"]
    assert SNAPSHOT_ID_RE.fullmatch(sid), sid
    assert sid.startswith("r-")
    assert re.fullmatch(r"\d{8}", sid.split("-")[1]), sid
    assert re.fullmatch(r"[0-9a-f]{8}", sid.split("-")[2]), sid


def test_snapshot_id_deterministic_and_content_sensitive():
    from src.export.snapshot_builder import _manifest_snapshot_id

    manifest_a = {"generated_at": "2026-10-07T00:00:00+00:00", "cells": 10, "cities": ["nyc"]}
    manifest_b = {"generated_at": "2026-10-07T00:00:00+00:00", "cells": 11, "cities": ["nyc"]}
    id_a1 = _manifest_snapshot_id(manifest_a)
    id_a2 = _manifest_snapshot_id(manifest_a)
    assert id_a1 == id_a2
    assert id_a1 != _manifest_snapshot_id(manifest_b)
    # re-running on an id-bearing manifest is a no-op (id excluded from the hash)
    assert _manifest_snapshot_id({**manifest_a, "snapshot_id": id_a1}) == id_a1


def test_snapshot_id_recomputable_from_serialized_manifest(
    snapshot: dict[str, Any], tmp_path: Path
):
    """The published id must be derivable from the manifest it was stamped on."""
    from src.export.snapshot_builder import _manifest_snapshot_id

    sid = snapshot["snapshot_id"]
    assert _manifest_snapshot_id(snapshot) == sid
    # and stable across a byte-identical rebuild of the same content
    rebuilt = json.loads(json.dumps({k: v for k, v in snapshot.items()}, separators=(",", ":")))
    assert _manifest_snapshot_id(rebuilt) == sid


def test_coverage_block_defaults(snapshot: dict[str, Any]):
    coverage = snapshot["coverage"]
    assert coverage["schema_version"] == 1
    assert coverage["metro"]["mode"] == "sparse_registry"
    assert coverage["national"]["status"] == "unavailable"
    assert "index_key" not in coverage["national"]
    assert "resolutions" not in coverage["national"]


def test_coverage_national_available_with_data(tmp_path: Path):
    national_dir = tmp_path / "national-out"
    _write_national_fixture(national_dir)
    manifest = asyncio_run_build(tmp_path, cities=["nyc"], national_dir=national_dir)
    coverage = manifest["coverage"]["national"]
    assert coverage["status"] == "available"
    assert coverage["index_key"] == "national/index"
    assert coverage["resolutions"] == manifest["national"]["resolutions"]


def test_coverage_national_unavailable_when_all_chunks_empty(tmp_path: Path):
    """A national dir whose every chunk is null publishes no national block
    (matching _publish_national_layers) and must read unavailable."""
    cell_la = h3.latlng_to_cell(34.0522, -118.2437, 6)
    parent_null = h3.cell_to_parent(cell_la, 3)
    res6_dir = tmp_path / "national-out" / "national" / "res6"
    res6_dir.mkdir(parents=True)
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

    manifest = asyncio_run_build(tmp_path, cities=["nyc"], national_dir=tmp_path / "national-out")
    assert "national" not in manifest
    assert manifest["coverage"]["national"]["status"] == "unavailable"


def test_coverage_national_available_under_require_national(tmp_path: Path):
    """require_national's fail-closed checks are the availability source of
    truth: when they pass, the coverage block reads available."""
    national_dir = tmp_path / "national-out"
    _write_national_fixture(national_dir)
    _write_national_res5_chunk(national_dir)
    manifest = asyncio_run_build(
        tmp_path, cities=["nyc"], national_dir=national_dir, require_national=True
    )
    assert manifest["coverage"]["national"]["status"] == "available"


def test_metrics_out_written_when_flag_passed(tmp_path: Path):
    metrics_path = tmp_path / "metrics.json"
    national_dir = tmp_path / "national-out"
    _write_national_fixture(national_dir)
    asyncio_run_build(
        tmp_path,
        cities=["nyc"],
        national_dir=national_dir,
        metrics_out=metrics_path,
    )
    report = json.loads(metrics_path.read_text())
    assert report["build_seconds"] >= 0
    assert report["cells"] > 0
    assert report["national"]["resolutions"]["6"]["chunks"] == 1
    assert report["national"]["seconds"] >= 0


def test_metrics_out_absent_writes_nothing(tmp_path: Path):
    asyncio_run_build(tmp_path, cities=["nyc"])
    assert not (tmp_path / "metrics.json").exists()
    assert not (tmp_path / "dist" / "metrics.json").exists()


# ---------------------------------------------------------------------------
# Release-qualified publication + snapshot/current pointer (Stage B)
# ---------------------------------------------------------------------------

RELEASE_PREFIX = "releases/"
POINTER_KEY = "snapshot/current"


def _bulk_entries(tmp_path: Path) -> list[dict[str, Any]]:
    return json.loads((tmp_path / "dist" / "kv-bulk.json").read_text())


def _bulk_map(tmp_path: Path) -> dict[str, str]:
    return {e["key"]: e["value"] for e in _bulk_entries(tmp_path)}


def _pointer(bulk: dict[str, str] | list[dict[str, str]]) -> dict[str, Any]:
    if isinstance(bulk, list):
        bulk = {e["key"]: e["value"] for e in bulk}
    return json.loads(bulk[POINTER_KEY])


def test_release_duplicates_every_logical_key(snapshot: dict[str, Any], tmp_path: Path):
    """Every legacy bulk key gains a byte-identical releases/{id}/ twin."""
    bulk = _bulk_map(tmp_path)
    sid = snapshot["snapshot_id"]
    logical = {
        k: v for k, v in bulk.items() if not k.startswith(RELEASE_PREFIX) and k != POINTER_KEY
    }
    assert logical, "bulk must contain legacy keys"
    for key, value in logical.items():
        release_key = f"{RELEASE_PREFIX}{sid}/{key}"
        assert release_key in bulk, f"missing release twin for {key}"
        assert bulk[release_key] == value, f"release twin content mismatch for {key}"
    # release entries never leak under a different snapshot id
    stray = [
        k
        for k in bulk
        if k.startswith(RELEASE_PREFIX) and not k.startswith(f"{RELEASE_PREFIX}{sid}/")
    ]
    assert stray == []


def test_pointer_format_and_current_id(snapshot: dict[str, Any], tmp_path: Path):
    bulk = _bulk_map(tmp_path)
    assert POINTER_KEY in bulk
    pointer = _pointer(bulk)
    assert set(pointer) == {"current", "previous", "promoted_at"}
    assert pointer["current"] == snapshot["snapshot_id"]
    promoted_at = datetime.fromisoformat(pointer["promoted_at"])
    assert promoted_at.tzinfo == UTC


def test_pointer_previous_null_without_prior(snapshot: dict[str, Any], tmp_path: Path):
    pointer = _pointer(_bulk_map(tmp_path))
    assert pointer["previous"] is None


def test_over_budget_build_fails_closed_and_keeps_old_bulk(
    snapshot: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Fail-closed ordering: the MAX_BULK_BYTES check must run BEFORE the bulk
    # write, so an over-budget build leaves kv-bulk.json (and its
    # snapshot/current pointer) holding the PREVIOUS generation's bytes.
    bulk_path = tmp_path / "dist" / "kv-bulk.json"
    old_bytes = bulk_path.read_bytes()
    old_pointer = _pointer(json.loads(old_bytes))

    def rebuild() -> None:
        import asyncio

        asyncio.run(
            build_snapshot(
                tmp_path / "dist",
                engine=StubEngine(),
                include_legacy_cells=True,
            )
        )

    monkeypatch.setattr(snapshot_builder, "MAX_BULK_BYTES", 1)
    with pytest.raises(ValueError, match="byte build budget"):
        rebuild()

    # The failed build must not have replaced the bulk or promoted the pointer.
    assert bulk_path.read_bytes() == old_bytes
    assert _pointer(json.loads(bulk_path.read_bytes()))["current"] == old_pointer["current"]


def test_pointer_rollback_simulation(tmp_path: Path, monkeypatch):
    """A → B on changed content; identical rebuild keeps B coherent."""
    from src.export import snapshot_builder as sb

    # Freeze generated_at so identical content hashes to the same snapshot_id.
    fixed_dt = datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_dt

    monkeypatch.setattr(sb, "datetime", FrozenDatetime)

    first = asyncio_run_build(tmp_path, cities=["nyc"])
    pointer_a = _pointer(_bulk_map(tmp_path))
    assert pointer_a["current"] == first["snapshot_id"]

    second = asyncio_run_build(tmp_path, cities=["nyc", "chicago"])
    pointer_b = _pointer(_bulk_map(tmp_path))
    assert pointer_b["current"] == second["snapshot_id"]
    assert pointer_b["current"] != pointer_a["current"]
    assert pointer_b["previous"] == pointer_a["current"]

    # unchanged rebuild: same id, previous stays A, pointer not re-promoted
    third = asyncio_run_build(tmp_path, cities=["nyc", "chicago"])
    pointer_c = _pointer(_bulk_map(tmp_path))
    assert pointer_c["current"] == third["snapshot_id"] == pointer_b["current"]
    assert pointer_c["previous"] == pointer_a["current"]
    assert pointer_c["promoted_at"] == pointer_b["promoted_at"]


def test_pointer_promotion_fail_closed_missing_release(tmp_path: Path, monkeypatch):
    """A missing release twin must refuse promotion and leave the old bulk intact."""
    from src.export import snapshot_builder as sb

    asyncio_run_build(tmp_path, cities=["nyc"])
    before = (tmp_path / "dist" / "kv-bulk.json").read_text()
    pointer_before = _pointer(json.loads(before))

    original = sb._release_entries

    def crippled(kv_entries, snapshot_id):
        entries = original(kv_entries, snapshot_id)
        return entries[1:]  # drop the first release twin

    monkeypatch.setattr(sb, "_release_entries", crippled)
    with pytest.raises(ValueError, match="release"):
        asyncio_run_build(tmp_path, cities=["nyc", "chicago"])
    # old pointer survived untouched
    assert json.loads((tmp_path / "dist" / "kv-bulk.json").read_text()) == json.loads(before)
    assert _pointer(json.loads(before))["current"] == pointer_before["current"]


def test_national_smoke_passes_when_available(tmp_path: Path):
    national_dir = tmp_path / "national-out"
    _write_national_fixture(national_dir)
    manifest = asyncio_run_build(tmp_path, cities=["nyc"], national_dir=national_dir)
    assert manifest["coverage"]["national"]["status"] == "available"
    bulk = _bulk_map(tmp_path)
    sid = manifest["snapshot_id"]
    national_releases = [k for k in bulk if k.startswith(f"{RELEASE_PREFIX}{sid}/national/")]
    assert f"{RELEASE_PREFIX}{sid}/national/index" in national_releases
    # at least one nonempty chunk in the release set
    chunks = [
        json.loads(bulk[k])
        for k in national_releases
        if k != f"{RELEASE_PREFIX}{sid}/national/index"
    ]
    assert any(chunk["rows"] for chunk in chunks)


def test_national_smoke_fails_when_index_missing(tmp_path: Path, monkeypatch):
    from src.export import snapshot_builder as sb

    national_dir = tmp_path / "national-out"
    _write_national_fixture(national_dir)
    asyncio_run_build(tmp_path, cities=["nyc"])

    original = sb._release_entries

    def no_index(kv_entries, snapshot_id):
        return [
            e for e in original(kv_entries, snapshot_id) if not e["key"].endswith("/national/index")
        ]

    monkeypatch.setattr(sb, "_release_entries", no_index)
    with pytest.raises(ValueError, match="national"):
        asyncio_run_build(tmp_path, cities=["nyc"], national_dir=national_dir)


def test_promotion_smoke_skipped_when_national_unavailable(
    snapshot: dict[str, Any], tmp_path: Path
):
    """Metro-only builds promote without national artifacts."""
    assert snapshot["coverage"]["national"]["status"] == "unavailable"
    pointer = _pointer(_bulk_map(tmp_path))
    assert pointer["current"] == snapshot["snapshot_id"]


# ---------------------------------------------------------------------------
# LOD pyramid (US-411)
# ---------------------------------------------------------------------------


def test_manifest_has_lod_block_and_tile_indexes(snapshot: dict[str, Any]):
    assert snapshot["lod"]["resolutions"] == list(LOD_RESOLUTIONS)
    for res in LOD_RESOLUTIONS:
        assert snapshot["lod"]["tile_parent_res"][str(res)] == LOD_TILE_PARENT_RES[res]
    assert set(snapshot["tile_indexes"].keys()) == {str(res) for res in LOD_RESOLUTIONS}
    # legacy shim equals res-9 tile index
    assert snapshot["tile_index"] == snapshot["tile_indexes"]["9"]


def test_lod_tiles_recompute_to_stated_parents(snapshot: dict[str, Any], tmp_path: Path):
    """Every LOD tile's features sit under the parent named in tile_indexes."""
    seen_cells: dict[int, set[str]] = {res: set() for res in LOD_RESOLUTIONS}
    for res in LOD_RESOLUTIONS:
        tile_parent_res = LOD_TILE_PARENT_RES[res]
        for parent, meta in snapshot["tile_indexes"][str(res)].items():
            payload = json.loads(
                (tmp_path / "dist" / "gridtiles_res" / str(res) / f"{parent}.json").read_text()
            )
            assert payload["tile_parent"] == parent
            assert payload["tile_resolution"] == tile_parent_res
            assert payload["lod_resolution"] == res
            assert len(payload["features"]) == meta["count"]
            for feature in payload["features"]:
                cell = feature["properties"]["h3_index"]
                assert h3.cell_to_parent(cell, tile_parent_res) == parent
                assert cell not in seen_cells[res], "a cell must land in exactly one tile per res"
                seen_cells[res].add(cell)
                assert "city_id" in feature["properties"]


def test_lod_coarser_has_fewer_cells(snapshot: dict[str, Any]):
    """res-7 tiles hold fewer cells than res-8, which holds fewer than res-9."""

    def total(res: int) -> int:
        return sum(meta["count"] for meta in snapshot["tile_indexes"][str(res)].values())

    assert total(7) <= total(8) <= total(9)
    assert total(9) > 0


def test_lod_percentiles_ranked_per_level(snapshot: dict[str, Any], tmp_path: Path):
    """Each LOD aggregate level carries its own national/metro percentile ranks."""
    for res in (7, 8):
        parent = min(snapshot["tile_indexes"][str(res)])
        tile_path = tmp_path / "dist" / "gridtiles_res" / str(res) / f"{parent}.json"
        payload = json.loads(tile_path.read_text())
        assert payload["features"]
        for feature in payload["features"]:
            props = feature["properties"]
            assert props["resolution"] == res
            for metric in NORMALIZED_METRICS:
                assert f"{metric}_national_pct" in props
                assert f"{metric}_metro_pct" in props


def test_dense_metro_flag_renders_continuous_grid(tmp_path: Path):
    """--dense-metro path: bounded k_ring=3 coverage fills more than k_ring=1."""
    import asyncio

    manifest = asyncio.run(
        build_snapshot(
            tmp_path / "dense",
            engine=StubEngine(),
            cities=["nyc", "chicago"],
            include_legacy_cells=False,
            dense_metro=True,
        )
    )
    # Dense res-9 grid must contain more features than the k_ring=1 default would
    # (measured ~4.2× in US-409). At minimum, strictly more than 442.
    from src.spatial.city_registry import REGISTRY

    nyc_submarkets = len(REGISTRY[CityId("nyc")].submarkets)
    # k_ring=1 ≈ submarkets × 7; dense bounded ≈ submarkets × ~28
    assert manifest["counts"]["nyc"]["grid_features"] > nyc_submarkets * 10


def test_dense_grid_features_have_coverage_source(tmp_path: Path):
    """Dense-mode features carry the honesty badge (coverage_source/distance)."""
    import asyncio

    out = tmp_path / "dense"
    asyncio.run(
        build_snapshot(
            out,
            engine=StubEngine(),
            cities=["nyc"],
            include_legacy_cells=False,
            dense_metro=True,
        )
    )
    grid = json.loads((out / "grid" / "nyc.json").read_text())
    assert grid["features"]
    sources = {f["properties"].get("coverage_source") for f in grid["features"]}
    assert sources <= {"center", "bounded"}
    assert "bounded" in sources, "dense grid must contain interpolated (bounded) cells"


# --------------------------------------------------------------------------- #
# Bay Area context layers (--context-dir)                                     #
# --------------------------------------------------------------------------- #
def _write_context_for_cells(root: Path, cells: list[str]) -> Path:
    """Context table covering ``cells``: jobs on all, buildings on every other."""
    from src.export.bay_area_context import BuildConfig, build_context

    jobs = {cell: {"jobs_total": float(100 + i)} for i, cell in enumerate(cells)}
    buildings = {cell: {"building_count": float(i)} for i, cell in enumerate(cells) if i % 2 == 0}
    out = root / "context"
    build_context(
        out,
        BuildConfig(cache_dir=root / "cache", env={}),
        builders={"lodes": lambda _c: jobs, "overture": lambda _c: buildings},
    )
    return out


def _sf_cells(tmp_path: Path) -> list[str]:
    asyncio_run_build(tmp_path / "probe", cities=["san_francisco"])
    grid = json.loads((tmp_path / "probe" / "dist" / "grid" / "san_francisco.json").read_text())
    return sorted(f["properties"]["h3_index"] for f in grid["features"])


def test_context_layers_join_matching_cells_only(tmp_path: Path):
    sf_cells = _sf_cells(tmp_path)
    covered = sf_cells[: len(sf_cells) // 2]
    context_dir = _write_context_for_cells(tmp_path, covered)
    manifest = asyncio_run_build(tmp_path, cities=["nyc", "san_francisco"], context_dir=context_dir)

    features = _all_grid_features(tmp_path, ["nyc", "san_francisco"])
    for feature in features["nyc"]:
        assert "jobs_total" not in feature["properties"]
        assert "jobs_total_national_pct" not in feature["properties"]
    sf = {f["properties"]["h3_index"]: f["properties"] for f in features["san_francisco"]}
    for cell, props in sf.items():
        if cell in covered:
            assert props["jobs_total"] == 100 + covered.index(cell)
            assert 0.0 <= props["jobs_total_metro_pct"] <= 100.0
        else:
            assert "jobs_total" not in props
            assert "jobs_total_metro_pct" not in props
    # Ranks span only the covered cells, so the extremes hit 0 and 100.
    pcts = sorted(sf[c]["jobs_total_national_pct"] for c in covered)
    assert pcts[0] == 0.0 and pcts[-1] == 100.0

    block = manifest["context_layers"]
    assert [m["key"] for m in block["metrics"]] == ["jobs_total", "building_count"]
    jobs_meta = block["metrics"][0]
    assert jobs_meta["cities"] == ["san_francisco"]
    assert jobs_meta["cells"] == len(covered)
    assert jobs_meta["label"] == "Jobs (LODES)"
    assert block["layers"]["overture"]["status"] == "ok"
    assert "ODbL" in block["layers"]["overture"]["attribution"]


def test_context_layers_reach_lod_tiles(tmp_path: Path):
    sf_cells = _sf_cells(tmp_path)
    context_dir = _write_context_for_cells(tmp_path, sf_cells)
    manifest = asyncio_run_build(tmp_path, cities=["san_francisco"], context_dir=context_dir)

    for res in (8, 7):
        parents = manifest["tile_indexes"][str(res)]
        features = [
            f
            for parent in parents
            for f in json.loads(
                (tmp_path / "dist" / "gridtiles_res" / str(res) / f"{parent}.json").read_text()
            )["features"]
        ]
        with_jobs = [f for f in features if "jobs_total" in f["properties"]]
        assert with_jobs, f"res {res} carries no context metric"
        for feature in with_jobs:
            assert "jobs_total_national_pct" in feature["properties"]


def test_lod_aggregate_averages_sparse_keys_over_valued_children():
    from src.export.snapshot_builder import _aggregate_grid_to_res

    parent = h3.latlng_to_cell(37.7793, -122.4193, 8)
    children = sorted(h3.cell_to_children(parent, 9))[:3]
    grid = {
        "features": [
            {"properties": {"h3_index": children[0], "lims_score": 10.0, "jobs_total": 30.0}},
            {"properties": {"h3_index": children[1], "lims_score": 20.0, "jobs_total": None}},
            {"properties": {"h3_index": children[2], "lims_score": 30.0}},
        ]
    }
    lod = _aggregate_grid_to_res(grid, "san_francisco", 8, extra_keys=("jobs_total",))
    props = lod["features"][0]["properties"]
    assert props["lims_score"] == 20.0
    assert props["jobs_total"] == 30.0  # one valued child, not 30 / 3


def test_context_dir_without_table_publishes_unchanged(tmp_path: Path):
    manifest = asyncio_run_build(tmp_path, cities=["nyc"], context_dir=tmp_path / "missing")
    assert "context_layers" not in manifest


def test_no_context_block_by_default(snapshot: dict[str, Any]):
    assert "context_layers" not in snapshot


def test_metrics_cover_stages_without_kv_keys(tmp_path: Path):
    from src.export.snapshot_metrics import SnapshotMetrics

    metrics = SnapshotMetrics()
    manifest = asyncio_run_build(tmp_path, cities=["nyc"], metrics=metrics)

    snapshot = metrics.snapshot()
    required = {
        "model_initialization",
        "city_inference",
        "cell_inference_shap",
        "ranking_lod",
        "serialization",
        "total",
    }
    assert required <= set(snapshot["durations_seconds"])
    assert "snapshot-metrics" not in manifest["keys"]
    kv_bulk = json.loads((tmp_path / "dist" / "kv-bulk.json").read_text())
    assert all("metrics" not in entry["key"] for entry in kv_bulk)
    assert snapshot["artifacts"]["key_count"] == len(kv_bulk)


def test_failed_build_writes_incomplete_metrics_summary(tmp_path: Path):
    from src.export.snapshot_metrics import SnapshotMetrics

    class FailingEngine(StubEngine):
        def predict_cell_features(self, *args, **kwargs):
            raise RuntimeError("synthetic failure")

    import asyncio

    metrics = SnapshotMetrics()
    with pytest.raises(RuntimeError, match="synthetic failure"):
        asyncio.run(
            build_snapshot(
                tmp_path / "failed",
                engine=FailingEngine(),
                cities=["nyc"],
                metrics=metrics,
            )
        )
    summary = metrics.snapshot()
    assert summary["artifacts"]["status"] == "incomplete"
    assert summary["artifacts"]["failure"]["type"] == "RuntimeError"
