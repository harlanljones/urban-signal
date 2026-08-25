"""Batch snapshot builder: precompute dashboard artifacts and emit Cloudflare KV bulk payloads.

Reuses the FastAPI router endpoint functions directly so exported schemas are guaranteed
identical to the live serving API. Output layout (per run):

    <out>/grid/{city}.json         GeoJSON FeatureCollection (res 9, k_ring 1, no SHAP)
    <out>/catalysts/{city}.json    Active catalyst clusters (min_lims = 85.0)
    <out>/submarkets/{city}.json   Submarket catalog per city
    <out>/cells.json               Global h3_index -> prediction map (SHAP included)
    <out>/manifest.json            Run metadata (generated_at, cities, keys, counts)
    <out>/kv-bulk.json             Single file for `wrangler kv bulk put`
"""

import argparse
import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.spatial.city_registry import CityId
from src.serving import router as api_router
from src.serving.engine import MultiHorizonInferenceEngine

logger = logging.getLogger(__name__)

SUPPORTED_CITIES = [city.value for city in CityId]
DEFAULT_RESOLUTION = 9
DEFAULT_K_RING = 1
CATALYST_THRESHOLD = 85.0
CATALYST_LIMIT = 50
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

    cells_index: dict[str, Any] = {}

    for city in cities:
        logger.info("Building snapshot artifacts for city '%s'", city)

        grid = await api_router.get_grid_geojson(
            city_id=city,
            resolution=DEFAULT_RESOLUTION,
            k_ring=DEFAULT_K_RING,
            borough=None,
            submarket=None,
            include_shap=False,
            engine=engine,
        )
        catalysts = await api_router.get_active_catalysts(
            city_id=city,
            min_lims=CATALYST_THRESHOLD,
            resolution=DEFAULT_RESOLUTION,
            borough=None,
            limit=CATALYST_LIMIT,
            engine=engine,
        )
        submarkets = await api_router.list_submarkets(city_id=city, borough=None)

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
    }
    register("manifest", out_dir / "manifest.json", manifest)

    bulk_path = out_dir / "kv-bulk.json"
    bulk_path.write_text(json.dumps(kv_entries), encoding="utf-8")

    logger.info(
        "Snapshot complete: %d KV keys, %d cells -> %s (%d bytes bulk)",
        len(kv_entries),
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
