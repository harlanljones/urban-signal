"""Batch snapshot builder: precompute dashboard artifacts and emit Cloudflare KV bulk payloads.

Reuses the FastAPI router endpoint functions directly so exported schemas are guaranteed
identical to the live serving API. Output layout (per run):

    <out>/grid/{city}.json         GeoJSON FeatureCollection (res 9, k_ring 1, no SHAP)
                                   + cross-metro percentile normalization properties
    <out>/gridtiles/<parent>.json  Res-5 parent-H3 viewport tiles (lazy-load units)
    <out>/catalysts/{city}.json    Active catalyst clusters (min_lims = 84.0)
    <out>/catalysts/index.json     All metros' catalysts flattened with city attribution
    <out>/submarkets/{city}.json   Submarket catalog per city
    <out>/cells.json               Global h3_index -> prediction map (SHAP included)
    <out>/manifest.json            Run metadata (generated_at, cities, keys, counts,
                                   tile_index, metro_index, tile_resolution)
    <out>/kv-bulk.json             Single file for `wrangler kv bulk put`

Normalization: raw LIMS scores are sigmoid(z) against fixed NYC-calibrated baselines,
so equal raw scores in different metros are not distribution-comparable. Every
NORMALIZED_METRICS property gets two average-rank percentile ranks stamped per feature:
`<metric>_metro_pct` (rank within its own metro) and `<metric>_national_pct`
(rank across every exported metro). Percentiles are computed over the complete
publish before any key is written, so lazily-loaded viewport tiles stay comparable
no matter when they reach the client.
"""

import argparse
import asyncio
import json
import logging
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import h3

from src.spatial.city_registry import CityId, REGISTRY
from src.serving import router as api_router
from src.serving.engine import MultiHorizonInferenceEngine

logger = logging.getLogger(__name__)

SUPPORTED_CITIES = [city.value for city in CityId]
DEFAULT_RESOLUTION = 9
DEFAULT_K_RING = 1
CATALYST_THRESHOLD = 84.0
CATALYST_LIMIT = 50
TILE_RESOLUTION = 5
NORMALIZED_METRICS = (
    "lims_score",
    "delta_6m_p50",
    "delta_12m_spillover",
    "prob_18m_macro_outperformance",
)
CELL_FEATURE_KEYS = (
    "capex_density_decayed",
    "permit_velocity",
    "shift_ratio_311",
    "sla_new_filings_90d",
    "lims_score",
)


def _write_json(path: Path, payload: Any) -> int:
    """Serialize payload compactly to path; returns byte size."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, separators=(",", ":"))
    path.write_text(data, encoding="utf-8")
    return len(data.encode("utf-8"))


def _percentile_ranks(values: list[float]) -> list[float]:
    """Average-rank percentile per value on [0, 100]; ties share one rank."""
    count = len(values)
    if count == 0:
        return []
    if count == 1:
        return [100.0]
    order = sorted(range(count), key=lambda index: values[index])
    ranks = [0.0] * count
    start = 0
    while start < count:
        end = start
        while end + 1 < count and values[order[end + 1]] == values[order[start]]:
            end += 1
        percentile = round(((start + end) / 2) / (count - 1) * 100.0, 2)
        for position in range(start, end + 1):
            ranks[order[position]] = percentile
        start = end + 1
    return ranks


def _apply_percentile_normalization(grids: dict[str, dict[str, Any]]) -> None:
    """Stamp <metric>_metro_pct and <metric>_national_pct onto every grid feature.

    Must run after every requested city's grid exists: percentiles are computed
    against the complete publish so lazily-fetched tiles agree with each other.
    """
    features_by_city = {city: grid.get("features", []) for city, grid in grids.items()}
    all_features = [feature for feats in features_by_city.values() for feature in feats]
    for metric in NORMALIZED_METRICS:
        national_ranks = _percentile_ranks(
            [float(feature["properties"].get(metric, 0.0)) for feature in all_features]
        )
        for feature, pct in zip(all_features, national_ranks):
            feature["properties"][f"{metric}_national_pct"] = pct
        for feats in features_by_city.values():
            metro_ranks = _percentile_ranks(
                [float(feature["properties"].get(metric, 0.0)) for feature in feats]
            )
            for feature, pct in zip(feats, metro_ranks):
                feature["properties"][f"{metric}_metro_pct"] = pct


def _features_bbox(features: list[dict[str, Any]]) -> dict[str, float] | None:
    """Tight bbox over polygon coordinates; None when there are no features."""
    min_lat = min_lng = math.inf
    max_lat = max_lng = -math.inf
    for feature in features:
        for ring in feature.get("geometry", {}).get("coordinates", []):
            for lng, lat in ring:
                min_lat = min(min_lat, lat)
                max_lat = max(max_lat, lat)
                min_lng = min(min_lng, lng)
                max_lng = max(max_lng, lng)
    if math.isinf(min_lat):
        return None
    return {"min_lat": min_lat, "max_lat": max_lat, "min_lng": min_lng, "max_lng": max_lng}


def _bucket_grid_tiles(grids: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group normalized grid features under res-5 parent H3 indexes.

    Also stamps city_id/city_name server-side so merged-tile clients never need
    per-city attribution logic.
    """
    tiles: dict[str, list[dict[str, Any]]] = {}
    seen_cells: set[str] = set()
    for city, grid in grids.items():
        city_name = REGISTRY[CityId(city)].name
        for feature in grid.get("features", []):
            props = feature.setdefault("properties", {})
            cell = props.get("h3_index")
            if not cell or cell in seen_cells:
                continue
            seen_cells.add(cell)
            props.setdefault("city_id", city)
            props["city_name"] = city_name
            parent = h3.cell_to_parent(cell, TILE_RESOLUTION)
            tiles.setdefault(parent, []).append(feature)
    return tiles


def _build_metro_index(grids: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-metro camera metadata derived from the registry and actual geometry."""
    index: list[dict[str, Any]] = []
    for city, grid in grids.items():
        registration = REGISTRY[CityId(city)]
        feats = grid.get("features", [])
        bbox = _features_bbox(feats) or {
            "min_lat": registration.metro_bbox["min_lat"],
            "max_lat": registration.metro_bbox["max_lat"],
            "min_lng": registration.metro_bbox["min_lng"],
            "max_lng": registration.metro_bbox["max_lng"],
        }
        index.append(
            {
                "city_id": city,
                "name": registration.name,
                "bbox": bbox,
                "center": {
                    "lat": float(registration.center["lat"]),
                    "lng": float(registration.center["lng"]),
                },
            }
        )
    return index


def _flatten_catalysts(catalysts_by_city: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Merge every metro's catalyst payload into one attributed feed document."""
    entries: list[dict[str, Any]] = []
    for city, payload in catalysts_by_city.items():
        city_name = REGISTRY[CityId(city)].name
        for entry in payload.get("catalysts", []):
            enriched = dict(entry)
            enriched.setdefault("city_id", payload.get("city_id", city))
            enriched["city_name"] = city_name
            entries.append(enriched)
    entries.sort(key=lambda entry: (-float(entry.get("lims_score", 0.0)), str(entry.get("h3_index"))))
    return {
        "count": len(entries),
        "threshold": CATALYST_THRESHOLD,
        "cities": sorted(catalysts_by_city),
        "catalysts": entries,
    }


async def build_snapshot(
    out_dir: Path,
    engine: MultiHorizonInferenceEngine | None = None,
    cities: list[str] | None = None,
) -> dict[str, Any]:
    """Build all snapshot artifacts into out_dir and return the manifest dict."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cities = list(cities or SUPPORTED_CITIES)

    if engine is None:
        engine = MultiHorizonInferenceEngine()

    kv_entries: list[dict[str, str]] = []
    keys_index: dict[str, dict[str, Any]] = {}
    counts: dict[str, Any] = {}

    def register(key: str, path: Path, payload: Any) -> None:
        size = _write_json(path, payload)
        keys_index[key] = {"bytes": size}
        kv_entries.append({"key": key, "value": json.dumps(payload, separators=(",", ":"))})

    grids: dict[str, dict[str, Any]] = {}
    catalysts_by_city: dict[str, dict[str, Any]] = {}
    submarkets_by_city: dict[str, dict[str, Any]] = {}

    for city in cities:
        logger.info("Building snapshot artifacts for city '%s'", city)
        grids[city] = await api_router.get_grid_geojson(
            city_id=city,
            resolution=DEFAULT_RESOLUTION,
            k_ring=DEFAULT_K_RING,
            borough=None,
            submarket=None,
            include_shap=False,
            engine=engine,
        )
        catalysts_by_city[city] = await api_router.get_active_catalysts(
            city_id=city,
            min_lims=CATALYST_THRESHOLD,
            resolution=DEFAULT_RESOLUTION,
            borough=None,
            limit=CATALYST_LIMIT,
            engine=engine,
        )
        submarkets_by_city[city] = await api_router.list_submarkets(city_id=city, borough=None)

    # Percentiles must see every exported metro before anything reaches KV.
    _apply_percentile_normalization(grids)

    cells_index: dict[str, Any] = {}

    for city in cities:
        grid = grids[city]
        catalysts = catalysts_by_city[city]
        submarkets = submarkets_by_city[city]

        register(f"grid/{city}", out_dir / "grid" / f"{city}.json", grid)
        register(f"catalysts/{city}", out_dir / "catalysts" / f"{city}.json", catalysts)
        register(f"submarkets/{city}", out_dir / "submarkets" / f"{city}.json", submarkets)

        counts[city] = {
            "grid_features": len(grid.get("features", [])),
            "catalysts": catalysts.get("count", 0),
            "submarkets": submarkets.get("count", 0),
        }

        for feature in grid.get("features", []):
            props = feature.get("properties", {})
            h3_cell = props.get("h3_index")
            if not h3_cell or h3_cell in cells_index:
                continue
            feats = {k: props[k] for k in CELL_FEATURE_KEYS if k in props}
            pred = engine.predict_cell_features(
                h3_index=h3_cell, feature_dict=feats, include_shap=True
            )
            cells_index[h3_cell] = pred

    register("cells/index", out_dir / "cells.json", cells_index)

    tiles = _bucket_grid_tiles(grids)
    tile_index: dict[str, dict[str, Any]] = {}
    for parent, features in sorted(tiles.items()):
        payload = {
            "type": "FeatureCollection",
            "tile_parent": parent,
            "tile_resolution": TILE_RESOLUTION,
            "features": features,
        }
        register(f"gridtiles/{parent}", out_dir / "gridtiles" / f"{parent}.json", payload)
        tile_index[parent] = {
            "count": len(features),
            "cities": sorted({str(f["properties"]["city_id"]) for f in features}),
            "bbox": _features_bbox(features),
        }

    register("catalysts/index", out_dir / "catalysts" / "index.json", _flatten_catalysts(catalysts_by_city))

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "app_version": _app_version(),
        "cities": cities,
        "resolution": DEFAULT_RESOLUTION,
        "k_ring": DEFAULT_K_RING,
        "catalyst_threshold": CATALYST_THRESHOLD,
        "counts": counts,
        "cells": len(cells_index),
        "keys": keys_index,
        "tile_resolution": TILE_RESOLUTION,
        "tile_index": tile_index,
        "metro_index": _build_metro_index(grids),
    }
    register("manifest", out_dir / "manifest.json", manifest)

    bulk_path = out_dir / "kv-bulk.json"
    bulk_path.write_text(json.dumps(kv_entries), encoding="utf-8")

    logger.info(
        "Snapshot complete: %d KV keys (%d grid tiles), %d cells -> %s (%d bytes bulk)",
        len(kv_entries),
        len(tile_index),
        len(cells_index),
        bulk_path,
        bulk_path.stat().st_size,
    )
    return manifest


def _app_version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("urban-signal")
    except PackageNotFoundError:
        return "2.0.0"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="Build Urban Signal edge snapshot for Workers KV")
    parser.add_argument("--out", default="dist", help="Output directory for snapshot artifacts")
    parser.add_argument(
        "--cities",
        nargs="*",
        default=SUPPORTED_CITIES,
        choices=SUPPORTED_CITIES,
        help="Subset of cities to export",
    )
    args = parser.parse_args()
    asyncio.run(build_snapshot(Path(args.out), cities=args.cities))


if __name__ == "__main__":
    main()
