"""Batch snapshot builder: precompute dashboard artifacts and emit Cloudflare KV bulk payloads.

Reuses the FastAPI router endpoint functions directly so exported schemas are guaranteed
identical to the live serving API. Output layout (per run):

    <out>/grid/{city}.json         GeoJSON FeatureCollection (res 9, k_ring 1, no SHAP)
                                   + cross-metro percentile normalization properties
    <out>/gridtiles/<parent>.json  Res-5 parent-H3 viewport tiles (lazy-load units)
    <out>/catalysts/{city}.json    Active catalyst clusters (min_lims = 84.0)
    <out>/catalysts/index.json     All metros' catalysts flattened with city attribution
    <out>/submarkets/{city}.json   Submarket catalog per city
    <out>/cells.json               Global h3_index -> prediction map (SHAP included);
                                   legacy single-key format, written only during the
                                   per-cell compat window (--skip-legacy-cells to omit)
    <out>/cells/{h3}.json          Per-cell prediction shards (one KV key per cell —
                                   point lookups read exactly one key, and no single
                                   value can approach the 25 MiB KV cap)
    <out>/cells/index_meta.json    Sharding metadata {sharded, total, generated_at}
    <out>/national/{res}/{p}.json  National hex chunk per res-3 parent (rows =
                                   hexes with data; absent hex means no data)
    <out>/national/index.json      Per-res {count, byte_size, sha256, parents,
                                   chunks{parent:{bytes,sha256,rows}}}
    <out>/manifest.json            Run metadata (generated_at, cities, keys, counts,
                                   tile_index, metro_index, tile_resolution,
                                   national summary when national data published)
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
import hashlib
import json
import logging
import math
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import h3
import polars as pl

from src.serving import router as api_router
from src.serving.engine import MultiHorizonInferenceEngine
from src.spatial import coverage
from src.spatial.city_registry import REGISTRY, CityId
from src.spatial.h3_indexer import H3SpatialIndexer
from src.spatial.national_grid import NATIONAL_RESOLUTIONS

logger = logging.getLogger(__name__)

SUPPORTED_CITIES = [city.value for city in CityId]
DEFAULT_RESOLUTION = 9
DEFAULT_K_RING = 1
CATALYST_THRESHOLD = 84.0
CATALYST_LIMIT = 50
TILE_RESOLUTION = 5
# Metro LOD pyramid (US-411): res 9 is the dense grid, res 8/7 are coarser
# aggregates published as their own tile sets so zoomed-out views show metro
# LIMS (blended with national LODES elsewhere) instead of a dead zone.
LOD_RESOLUTIONS = coverage.METRO_LOD_RESOLUTIONS  # (7, 8, 9)
# Tile parent resolution per LOD level: coarse LOD needs coarser parents so a
# metro spans only a handful of chunks and each stays under the 5 MiB budget.
LOD_TILE_PARENT_RES = {7: 4, 8: 4, 9: TILE_RESOLUTION}
# LOD aggregate features carry the averaged raw metric values (US-415 method A:
# average raw, THEN rank). These are the averaged CELL_FEATURE_KEYS +
# NORMALIZED_METRICS, deduped — built lazily below once both tuples exist.
def _lod_aggregate_keys() -> tuple[str, ...]:
    return tuple(dict.fromkeys((*CELL_FEATURE_KEYS, *NORMALIZED_METRICS)))
# Size budgets (US-385): a publish that would exceed Workers KV limits must fail
# the build here, not inside `wrangler kv bulk put` at 2 AM.
MAX_KV_VALUE_BYTES = 20 * 1024 * 1024  # KV hard cap is 25 MiB per value
MAX_MANIFEST_BYTES = 10 * 1024 * 1024  # boot manifest fetched by every visitor
MAX_BULK_BYTES = 512 * 1024 * 1024
# National chunks (US-383): ticket budget per key — tighter than the KV cap by
# design so a res-6 shard (~254 KB measured) can never silently creep toward it.
NATIONAL_MAX_CHUNK_BYTES = 5 * 1024 * 1024
NATIONAL_COLS = ("h3", "jobs", "workers", "jobs_pct", "workers_pct")
# Cells inference is the dominant build cost; ONNX sessions are thread-safe for
# concurrent run() calls, and pool.map preserves submission order so the publish
# stays deterministic.
CELL_INFERENCE_WORKERS = min(8, os.cpu_count() or 4)
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


def _bucket_grid_tiles(
    grids: dict[str, dict[str, Any]], tile_res: int = TILE_RESOLUTION
) -> dict[str, list[dict[str, Any]]]:
    """Group normalized grid features under parent H3 indexes at ``tile_res``.

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
            parent = h3.cell_to_parent(cell, tile_res)
            tiles.setdefault(parent, []).append(feature)
    return tiles


def _aggregate_grid_to_res(
    grid: dict[str, Any], city: str, to_res: int
) -> dict[str, Any]:
    """Roll a res-9 grid up to a coarser LOD resolution (US-411).

    US-415 method A: average the RAW metric values per parent cell, never
    average child percentiles. Features carry the averaged
    ``LOD_AGGREGATE_KEYS`` values plus a parent-boundary polygon and centroid,
    so ``_apply_percentile_normalization`` can rank the aggregate surface
    against itself (each LOD level is its own national rank space).
    """
    aggregate_keys = _lod_aggregate_keys()
    parents: dict[str, dict[str, Any]] = {}
    for feature in grid.get("features", []):
        props = feature.get("properties", {})
        cell = props.get("h3_index")
        if not cell:
            continue
        parent = h3.cell_to_parent(cell, to_res)
        bucket = parents.setdefault(
            parent,
            {"h3_index": parent, "resolution": to_res, "_children": 0, "_acc": {}},
        )
        bucket["_children"] += 1
        for key in aggregate_keys:
            value = props.get(key)
            if value is None:
                continue
            acc = bucket["_acc"]
            acc[key] = acc.get(key, 0.0) + float(value)

    features: list[dict[str, Any]] = []
    for parent, bucket in parents.items():
        acc = bucket["_acc"]
        aggregate_props: dict[str, Any] = {
            "h3_index": parent,
            "resolution": to_res,
            "city_id": city,
            "submarket": None,
            "borough": None,
            "source": "lod_aggregate",
            "_child_cells": bucket["_children"],
        }
        for key in aggregate_keys:
            if key in acc:
                aggregate_props[key] = round(acc[key] / bucket["_children"], 6)
        centroid = h3.cell_to_latlng(parent)
        aggregate_props["centroid_lat"] = centroid[0]
        aggregate_props["centroid_lng"] = centroid[1]
        boundary = H3SpatialIndexer.h3_to_boundary(parent, geojson_format=True)
        if boundary and boundary[0] != boundary[-1]:
            boundary.append(boundary[0])
        features.append(
            {
                "type": "Feature",
                "id": parent,
                "geometry": {"type": "Polygon", "coordinates": [boundary]},
                "properties": aggregate_props,
            }
        )
    return {"type": "FeatureCollection", "city_id": city, "features": features}


def _dense_metro_grid(
    city: str,
    engine: MultiHorizonInferenceEngine,
    max_ring: int = coverage.DEFAULT_MAX_RING,
    max_dist_km: float | None = coverage.DEFAULT_MAX_DIST_KM,
) -> dict[str, Any]:
    """Build a dense res-9 grid for one metro (US-411 ``--dense-metro``).

    Uses the coverage seam to render every bounded k-ring cell around the
    metro's submarket centers, assigning each cell to its nearest submarket so
    synthetic features mirror ``router.get_grid_geojson``. Cells outside any
    submarket's ``max_dist_km`` bound are omitted (honesty rule).
    """
    cells = coverage.metro_cells(city, res=9, max_ring=max_ring, max_dist_km=max_dist_km)
    features: list[dict[str, Any]] = []
    for cell in cells:
        assignment = coverage.assign_cell(cell, city, max_dist_km=max_dist_km)
        if assignment is None:
            continue
        meta = coverage.submarket_meta(city, assignment.submarket)
        if meta is None:
            continue
        meta_dict = api_router._submarket_to_dict(meta)
        synthetic_feats = {
            "capex_density_decayed": meta_dict["capex"],
            "permit_velocity": (
                meta_dict["permit_vel"]
                if meta_dict["permit_vel"] <= 1.0
                else meta_dict["permit_vel"] / 100.0
            ),
            "shift_ratio_311": meta_dict["shift_ratio"],
            "sla_new_filings_90d": int(meta_dict["sla"]),
            "lims_score": meta_dict["base_lims"],
        }
        pred = engine.predict_cell_features(cell, synthetic_feats, include_shap=False)
        boundary = H3SpatialIndexer.h3_to_boundary(cell, geojson_format=True)
        if boundary and boundary[0] != boundary[-1]:
            boundary.append(boundary[0])
        features.append(
            {
                "type": "Feature",
                "id": cell,
                "geometry": {"type": "Polygon", "coordinates": [boundary]},
                "properties": {
                    "submarket": meta_dict["name"],
                    "borough": meta_dict["borough"],
                    "city_id": city,
                    "coverage_source": assignment.source,
                    "coverage_distance_km": assignment.distance_km,
                    **synthetic_feats,
                    **pred,
                },
            }
        )
    return {"type": "FeatureCollection", "city_id": city, "features": features}


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
    entries.sort(
        key=lambda entry: (-float(entry.get("lims_score", 0.0)), str(entry.get("h3_index")))
    )
    return {
        "count": len(entries),
        "threshold": CATALYST_THRESHOLD,
        "cities": sorted(catalysts_by_city),
        "catalysts": entries,
    }


def _publish_national_layers(
    out_dir: Path,
    national_dir: Path,
    register: Callable[[str, Path, Any], int],
) -> dict[str, Any] | None:
    """Publish national hex chunk JSONs + the ``national/index`` key.

    Reads the national builder's output tree (``<national_dir>/national/res*/
    {res3_parent}.parquet``, one chunk per res-3 parent) and emits one KV key
    per non-empty chunk (``national/{res}/{parent}``) plus a single
    ``national/index`` integrity key. Returns the manifest ``national`` summary
    block, or None when ``national_dir`` carries no national data (the caller
    then omits the block — backward compatible).

    Chunks publish only rows with at least one non-null metric: an absent hex
    means "no data" (honesty rule) and an absent chunk key surfaces as
    ``missing[]`` on the route. Format measured 2026-08-28 (US-383): compact
    JSON rows-of-arrays costs ~254 KB per res-6 res-3 chunk vs ~201 KB
    base64-packed binary (0.79x) — the 21% saving does not justify a bespoke
    binary codec in both runtimes, so chunks stay plain JSON.
    """
    national_root = Path(national_dir) / "national"
    if not national_root.is_dir():
        logger.info("No national layers at %s; publishing metro-only snapshot", national_root)
        return None

    generated_at = datetime.now(UTC).isoformat()
    index_block: dict[str, dict[str, Any]] = {}
    summary_block: dict[str, dict[str, Any]] = {}
    for res in NATIONAL_RESOLUTIONS:
        res_dir = national_root / f"res{res}"
        if not res_dir.is_dir():
            continue
        chunk_meta: dict[str, dict[str, Any]] = {}
        total_rows = 0
        total_bytes = 0
        for parquet_path in sorted(res_dir.glob("*.parquet")):
            parent = parquet_path.stem
            frame = pl.read_parquet(parquet_path)
            if frame.is_empty():
                continue
            payload = {
                "res": res,
                "parent": parent,
                "year": int(frame["year"][0]),
                "signal_source": str(frame["signal_source"][0]),
                "cols": list(NATIONAL_COLS),
                "rows": frame.filter(
                    pl.col("jobs_c000").is_not_null() | pl.col("workers_c000").is_not_null()
                )
                .sort("h3_index")
                .select(
                    pl.col("h3_index"),
                    pl.col("jobs_c000").alias("jobs"),
                    pl.col("workers_c000").alias("workers"),
                    pl.col("jobs_c000_national_pct").alias("jobs_pct"),
                    pl.col("workers_c000_national_pct").alias("workers_pct"),
                )
                .rows(),
            }
            key = f"national/{res}/{parent}"
            blob = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            if not payload["rows"]:
                logger.info("National chunk %s has no data rows; no key published", key)
                continue
            if len(blob) > NATIONAL_MAX_CHUNK_BYTES:
                raise ValueError(
                    f"National chunk '{key}' is {len(blob):,} bytes, over the "
                    f"{NATIONAL_MAX_CHUNK_BYTES:,}-byte US-383 budget. Shard it further "
                    f"(res-2 parents) before publishing."
                )
            register(key, out_dir / "national" / str(res) / f"{parent}.json", payload)
            chunk_meta[parent] = {
                "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "rows": len(payload["rows"]),
            }
            total_rows += len(payload["rows"])
            total_bytes += len(blob)
        if not chunk_meta:
            logger.warning("National res%d carried no data rows; skipped from publish", res)
            continue
        rolling = hashlib.sha256(
            "\n".join(
                f"{parent} {chunk_meta[parent]['sha256']}" for parent in sorted(chunk_meta)
            ).encode("utf-8")
        ).hexdigest()
        index_block[str(res)] = {
            "count": total_rows,
            "byte_size": total_bytes,
            "sha256": rolling,
            "parents": sorted(chunk_meta),
            "chunks": chunk_meta,
            "generated_at": generated_at,
        }
        summary_block[str(res)] = {"count": total_rows, "chunks": len(chunk_meta)}

    if not index_block:
        return None
    register(
        "national/index",
        out_dir / "national" / "index.json",
        {"generated_at": generated_at, "resolutions": index_block},
    )
    return {"generated_at": generated_at, "resolutions": summary_block}


def _require_national_block(
    national_block: dict[str, Any] | None, national_dir: Path | None
) -> None:
    """Fail closed when production require-national mode has no valid national input.

    A production release must never silently regress to metro-only coverage:
    absent input, an empty publish, or a publish missing any of
    ``NATIONAL_RESOLUTIONS`` raises here, in the build, not at 2 AM in KV.
    """
    if national_block is None:
        raise ValueError(
            "require-national: no national layers published "
            f"(national_dir={national_dir}); refusing a metro-only production snapshot"
        )
    published = set(national_block.get("resolutions", {}))
    required = {str(res) for res in NATIONAL_RESOLUTIONS}
    missing = sorted(required - published)
    if missing:
        raise ValueError(
            f"require-national: national publish is missing resolutions {missing} "
            f"(published: {sorted(published)}); refusing an incomplete production snapshot"
        )


async def build_snapshot(
    out_dir: Path,
    engine: MultiHorizonInferenceEngine | None = None,
    cities: list[str] | None = None,
    include_legacy_cells: bool = True,
    national_dir: Path | None = None,
    dense_metro: bool = False,
    require_national: bool = False,
) -> dict[str, Any]:
    """Build all snapshot artifacts into out_dir and return the manifest dict.

    ``include_legacy_cells`` keeps writing the monolithic ``cells/index`` value
    during the compat window so an already-deployed worker (which reads the
    single key) keeps serving while ``cells/{h3}`` shards roll out. Flip to
    False once the worker's per-cell lookup path is live everywhere.

    ``national_dir`` points at a national-builder output root
    (``<national_dir>/national/res*/{res3_parent}.parquet``). When given (and
    data exists), national hex chunks + ``national/index`` are published and the
    manifest gains a ``national`` summary block; when omitted the snapshot is
    metro-only and the manifest carries no national block.

    ``require_national`` is the production mode (US-435 §24): the build fails
    instead of silently publishing a metro-only snapshot when the national
    artifact is absent, corrupt, or missing a required resolution.

    ``dense_metro`` switches the res-9 grid from ``router.get_grid_geojson``'s
    k_ring=1 render set to the bounded k_ring=3 coverage seam
    (``coverage.metro_cells``, 1.5 km bound) so urban cores are continuous.
    LOD aggregates (res 8/7) are always built regardless; ``dense_metro`` only
    changes the leaf-level density (US-411).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cities = list(cities or SUPPORTED_CITIES)

    if engine is None:
        engine = MultiHorizonInferenceEngine()

    kv_entries: list[dict[str, str]] = []
    keys_index: dict[str, dict[str, Any]] = {}
    counts: dict[str, Any] = {}

    def register(key: str, path: Path, payload: Any) -> int:
        size = _write_json(path, payload)
        if size > MAX_KV_VALUE_BYTES:
            raise ValueError(
                f"KV value '{key}' is {size:,} bytes, over the {MAX_KV_VALUE_BYTES:,}-byte "
                f"build budget (KV hard cap 25 MiB). Shard the key before publishing."
            )
        keys_index[key] = {"bytes": size}
        kv_entries.append({"key": key, "value": json.dumps(payload, separators=(",", ":"))})
        return size

    grids: dict[str, dict[str, Any]] = {}
    catalysts_by_city: dict[str, dict[str, Any]] = {}
    submarkets_by_city: dict[str, dict[str, Any]] = {}

    for city in cities:
        logger.info("Building snapshot artifacts for city '%s'", city)
        if dense_metro:
            grids[city] = _dense_metro_grid(city, engine)
        else:
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
    # res-9 is its own national rank space (unchanged); each LOD aggregate
    # level is ranked against ITS complete publish (US-415 method A — average
    # raw, then rank per level, never average child percentiles).
    _apply_percentile_normalization(grids)
    grids_by_res: dict[int, dict[str, dict[str, Any]]] = {DEFAULT_RESOLUTION: grids}
    for res in (8, 7):
        lod_grids = {city: _aggregate_grid_to_res(grids[city], city, res) for city in cities}
        _apply_percentile_normalization(lod_grids)
        grids_by_res[res] = lod_grids

    cells_requests: list[tuple[str, dict[str, Any]]] = []
    seen_cells: set[str] = set()

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
            if not h3_cell or h3_cell in seen_cells:
                continue
            seen_cells.add(h3_cell)
            feats = {k: props[k] for k in CELL_FEATURE_KEYS if k in props}
            cells_requests.append((h3_cell, feats))

    # Inference runs on a thread pool (ONNX sessions are thread-safe); results
    # are consumed in submission order so the publish is deterministic.
    def _predict(request: tuple[str, dict[str, Any]]) -> dict[str, Any]:
        h3_cell, feats = request
        return engine.predict_cell_features(h3_index=h3_cell, feature_dict=feats, include_shap=True)

    with ThreadPoolExecutor(max_workers=CELL_INFERENCE_WORKERS) as pool:
        predictions = list(pool.map(_predict, cells_requests))
    cells_by_index = {request[0]: pred for request, pred in zip(cells_requests, predictions)}

    for h3_cell, pred in cells_by_index.items():
        register(f"cells/{h3_cell}", out_dir / "cells" / f"{h3_cell}.json", pred)

    cells_meta = {
        "sharded": True,
        "total": len(cells_by_index),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    register("cells/index_meta", out_dir / "cells" / "index_meta.json", cells_meta)
    if include_legacy_cells:
        register("cells/index", out_dir / "cells.json", cells_by_index)

    # LOD pyramid tiles (US-411): each resolution is bucketed under its own
    # tile-parent resolution and published as gridtiles_res{res}/{parent}.
    # res-9 also keeps the legacy `gridtiles/{parent}` + `tile_index` shim for
    # the deployed edge worker during the compat window (same pattern as
    # cells/index → cells/{h3}).
    tile_indexes: dict[str, dict[str, dict[str, Any]]] = {}
    tile_index: dict[str, dict[str, Any]] = {}
    for res in LOD_RESOLUTIONS:
        res_grids = grids_by_res[res]
        tile_parent_res = LOD_TILE_PARENT_RES[res]
        tiles = _bucket_grid_tiles(res_grids, tile_res=tile_parent_res)
        res_index: dict[str, dict[str, Any]] = {}
        for parent, features in sorted(tiles.items()):
            payload = {
                "type": "FeatureCollection",
                "tile_parent": parent,
                "tile_resolution": tile_parent_res,
                "lod_resolution": res,
                "features": features,
            }
            register(
                f"gridtiles_res{res}/{parent}",
                out_dir / "gridtiles_res" / str(res) / f"{parent}.json",
                payload,
            )
            res_index[parent] = {
                "count": len(features),
                "cities": sorted({str(f["properties"]["city_id"]) for f in features}),
                "bbox": _features_bbox(features),
            }
            if res == DEFAULT_RESOLUTION:
                # legacy shim mirrors res-9 exactly
                register(f"gridtiles/{parent}", out_dir / "gridtiles" / f"{parent}.json", payload)
        tile_indexes[str(res)] = res_index
        if res == DEFAULT_RESOLUTION:
            tile_index = res_index

    register(
        "catalysts/index",
        out_dir / "catalysts" / "index.json",
        _flatten_catalysts(catalysts_by_city),
    )

    national_block: dict[str, Any] | None = None
    if national_dir is not None:
        national_block = _publish_national_layers(out_dir, national_dir, register)
    if require_national:
        _require_national_block(national_block, national_dir)

    manifest: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "app_version": _app_version(),
        "cities": cities,
        "resolution": DEFAULT_RESOLUTION,
        "k_ring": DEFAULT_K_RING,
        "catalyst_threshold": CATALYST_THRESHOLD,
        "counts": counts,
        "cells": len(cells_by_index),
        "cells_sharded": True,
        "keys": keys_index,
        "tile_resolution": TILE_RESOLUTION,
        "tile_index": tile_index,
        "tile_indexes": tile_indexes,
        "lod": {
            "resolutions": list(LOD_RESOLUTIONS),
            "tile_parent_res": {str(r): LOD_TILE_PARENT_RES[r] for r in LOD_RESOLUTIONS},
        },
        "metro_index": _build_metro_index(grids),
    }
    if national_block is not None:
        manifest["national"] = national_block
    manifest_size = _write_json(out_dir / "manifest.json", manifest)
    if manifest_size > MAX_MANIFEST_BYTES:
        raise ValueError(
            f"Manifest is {manifest_size:,} bytes, over the {MAX_MANIFEST_BYTES:,}-byte boot "
            f"budget. Slim it (split tile_indexes into their own key) before publishing."
        )
    register("manifest", out_dir / "manifest.json", manifest)

    bulk_path = out_dir / "kv-bulk.json"
    bulk_path.write_text(json.dumps(kv_entries), encoding="utf-8")
    if bulk_path.stat().st_size > MAX_BULK_BYTES:
        raise ValueError(
            f"kv-bulk.json is {bulk_path.stat().st_size:,} bytes, over the "
            f"{MAX_BULK_BYTES:,}-byte build budget. Chunk the bulk put."
        )

    logger.info(
        "Snapshot complete: %d KV keys (%d grid tiles, %d cells) -> %s (%d bytes bulk)",
        len(kv_entries),
        len(tile_index),
        len(cells_by_index),
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
    parser.add_argument(
        "--skip-legacy-cells",
        action="store_true",
        help="Do not write the monolithic cells/index value (per-cell shards only)",
    )
    parser.add_argument(
        "--national-dir",
        default=None,
        help=(
            "National-builder output root (contains national/res*/ res-3 parquet "
            "chunks); omit to publish a metro-only snapshot"
        ),
    )
    parser.add_argument(
        "--require-national",
        action="store_true",
        help=(
            "Production mode: fail instead of publishing a metro-only or "
            "resolution-incomplete snapshot when national input is missing"
        ),
    )
    parser.add_argument(
        "--dense-metro",
        action="store_true",
        help="Use bounded k_ring=3 coverage (coverage.metro_cells) for continuous urban hexes",
    )
    args = parser.parse_args()
    asyncio.run(
        build_snapshot(
            Path(args.out),
            cities=args.cities,
            include_legacy_cells=not args.skip_legacy_cells,
            national_dir=Path(args.national_dir) if args.national_dir else None,
            dense_metro=args.dense_metro,
            require_national=args.require_national,
        )
    )


if __name__ == "__main__":
    main()
