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
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import h3
import polars as pl

from src.export.bay_area_context import CONTEXT_METRIC_KEYS, load_context
from src.export.publication import FEATURE_SCHEMA_VERSION, plan_publication
from src.export.snapshot_metrics import SnapshotMetrics
from src.models.quantile_lgbm import FEATURE_COLUMNS
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
# Runaway bound on the whole bulk file. The KV bulk API caps each *request* at
# 10,000 pairs / 100 MB (not the file), and `wrangler kv bulk put` segments the
# file into batches under that cap, so this guards against a pathological
# publish rather than a hard transport limit. Raised 512 MiB -> 1 GiB when the
# dense metro hex (US-408) plus the Stage B release twins were enabled: measured
# extrapolation from the 2026-10-07 prod snapshot (64 MiB logical / 69 MiB bulk,
# 13,154 keys) is ~566 MiB once both are on.
MAX_BULK_BYTES = 1024 * 1024 * 1024
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


def _apply_context_layers(
    grids: dict[str, dict[str, Any]], context_values: dict[str, dict[str, float]]
) -> None:
    """Copy per-hex context metrics (Bay Area layers) onto matching res-9 features.

    A feature whose cell the context table does not carry gets no context
    property at all, so the dashboard renders it as "no data" rather than 0.
    """
    for grid in grids.values():
        for feature in grid.get("features", []):
            props = feature.get("properties", {})
            metrics = context_values.get(props.get("h3_index"))
            if metrics:
                props.update(metrics)


def _apply_context_percentiles(
    grids: dict[str, dict[str, Any]], metric_keys: tuple[str, ...]
) -> None:
    """Stamp <metric>_metro_pct / _national_pct for context metrics, nulls excluded.

    Unlike ``NORMALIZED_METRICS`` (present on every feature), a context metric
    exists only where its layer has coverage, so ranks are computed over the
    features that carry a value and the rest stay unranked.
    """
    for metric in metric_keys:
        by_city = {
            city: [f for f in grid.get("features", []) if f["properties"].get(metric) is not None]
            for city, grid in grids.items()
        }
        valued = [feature for feats in by_city.values() for feature in feats]
        national = _percentile_ranks([float(f["properties"][metric]) for f in valued])
        for feature, pct in zip(valued, national):
            feature["properties"][f"{metric}_national_pct"] = pct
        for feats in by_city.values():
            metro = _percentile_ranks([float(f["properties"][metric]) for f in feats])
            for feature, pct in zip(feats, metro):
                feature["properties"][f"{metric}_metro_pct"] = pct


def _context_manifest_block(
    grids: dict[str, dict[str, Any]], meta: dict[str, Any]
) -> dict[str, Any]:
    """Manifest entry telling the dashboard which context metrics it can offer."""
    metrics = []
    for spec in meta.get("metrics", []):
        key = spec["key"]
        cities = sorted(
            city
            for city, grid in grids.items()
            if any(f["properties"].get(key) is not None for f in grid.get("features", []))
        )
        if not cities:
            continue
        cells = sum(
            1
            for grid in grids.values()
            for f in grid.get("features", [])
            if f["properties"].get(key) is not None
        )
        metrics.append({**spec, "cities": cities, "cells": cells})
    return {
        "generated_at": meta.get("generated_at"),
        "layers": meta.get("layers", {}),
        "metrics": metrics,
    }


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
    grid: dict[str, Any], city: str, to_res: int, extra_keys: tuple[str, ...] = ()
) -> dict[str, Any]:
    """Roll a res-9 grid up to a coarser LOD resolution (US-411).

    US-415 method A: average the RAW metric values per parent cell, never
    average child percentiles. Features carry the averaged
    ``LOD_AGGREGATE_KEYS`` values plus a parent-boundary polygon and centroid,
    so ``_apply_percentile_normalization`` can rank the aggregate surface
    against itself (each LOD level is its own national rank space).

    Each key averages over the children that carry it, so a sparse
    ``extra_keys`` context metric is not diluted by children without coverage.
    """
    aggregate_keys = tuple(dict.fromkeys((*_lod_aggregate_keys(), *extra_keys)))
    parents: dict[str, dict[str, Any]] = {}
    for feature in grid.get("features", []):
        props = feature.get("properties", {})
        cell = props.get("h3_index")
        if not cell:
            continue
        parent = h3.cell_to_parent(cell, to_res)
        bucket = parents.setdefault(
            parent,
            {"h3_index": parent, "resolution": to_res, "_children": 0, "_acc": {}, "_n": {}},
        )
        bucket["_children"] += 1
        for key in aggregate_keys:
            value = props.get(key)
            if value is None:
                continue
            acc = bucket["_acc"]
            acc[key] = acc.get(key, 0.0) + float(value)
            bucket["_n"][key] = bucket["_n"].get(key, 0) + 1

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
                aggregate_props[key] = round(acc[key] / bucket["_n"][key], 6)
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


def _coverage_block(national_block: dict[str, Any] | None) -> dict[str, Any]:
    """Build the manifest ``coverage`` block (hex-coverage Stage A).

    ``status`` derives solely from the published national block: a block is
    present only when ``_publish_national_layers`` actually published at least
    one nonempty chunk for every declared resolution (empty chunks are skipped
    there), and ``_require_national_block`` fails the build before publication
    when require-national mode sees an absent or incomplete input. So
    ``available`` is never derivable from a stale/empty chunk set.
    """
    national: dict[str, Any] = {"status": "unavailable"}
    if national_block is not None:
        resolutions = national_block.get("resolutions", {})
        if resolutions and all(meta.get("chunks", 0) >= 1 for meta in resolutions.values()):
            national = {
                "status": "available",
                "index_key": "national/index",
                "resolutions": resolutions,
            }
    return {
        "schema_version": 1,
        "national": national,
        "metro": {"mode": "sparse_registry"},
    }


def _manifest_snapshot_id(manifest: dict[str, Any]) -> str:
    """Deterministic content id: ``r-YYYYMMDD-<first 8 hex of sha256>``.

    Canonicalization (exact, do not change without a migration): the manifest
    dict minus the ``snapshot_id`` field itself AND minus the self-referential
    ``keys["manifest"]`` size entry (that entry is the manifest's own byte size
    and is circular with the id; it is only present in the in-memory dict after
    registration — the published manifest.json never contains it) is serialized
    with ``json.dumps(..., sort_keys=True, separators=(",", ":"),
    ensure_ascii=False)`` and hashed UTF-8 with sha256; the id date is the
    first 10 chars of ``generated_at`` (ISO) with dashes stripped. Same
    manifest content → same id; the id is bounded (<~18 chars) and matches the
    path-safe ``^[A-Za-z0-9._-]{1,64}$`` adapter regex.
    """
    payload = {k: v for k, v in manifest.items() if k != "snapshot_id"}
    if isinstance(payload.get("keys"), dict) and "manifest" in payload["keys"]:
        payload["keys"] = {k: v for k, v in payload["keys"].items() if k != "manifest"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:8]
    date = str(manifest.get("generated_at", ""))[:10].replace("-", "")
    return f"r-{date}-{digest}"


RELEASES_PREFIX = "releases/"
SNAPSHOT_POINTER_KEY = "snapshot/current"


def _release_entries(kv_entries: list[dict[str, str]], snapshot_id: str) -> list[dict[str, str]]:
    """Release-qualified twins: ``releases/{snapshot_id}/{logical_key}``.

    Purely additive — the legacy logical keys stay in the bulk exactly as
    before, so old readers never break. The twins duplicate the same values so
    a whole generation can be addressed/fetched by snapshot id.
    """
    prefix = f"{RELEASES_PREFIX}{snapshot_id}/"
    return [{"key": f"{prefix}{e['key']}", "value": e["value"]} for e in kv_entries]


def _read_previous_pointer(bulk_path: Path) -> dict[str, Any] | None:
    """Read the ``snapshot/current`` pointer from the bulk being superseded."""
    try:
        existing = json.loads(bulk_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for entry in existing:
        if not isinstance(entry, dict):
            continue
        if entry.get("key") == SNAPSHOT_POINTER_KEY:
            try:
                pointer = json.loads(entry.get("value", ""))
            except ValueError:
                return None
            if isinstance(pointer, dict) and "current" in pointer:
                return pointer
            return None
    return None


def _national_smoke_required(national_block: dict[str, Any] | None) -> bool:
    """True when the build declares national coverage ``available``."""
    if national_block is None:
        return False
    return _coverage_block(national_block)["national"]["status"] == "available"


def _verify_release_integrity(
    release_entries: list[dict[str, str]],
    kv_entries: list[dict[str, str]],
    snapshot_id: str,
    national_block: dict[str, Any] | None,
) -> None:
    """Fail-closed promotion check (hex-coverage Stage B).

    Before the ``snapshot/current`` pointer may enter the bulk: every logical
    key must have a release twin under ``releases/{snapshot_id}/`` with
    byte-identical content, and — when national coverage is declared
    ``available`` — the release set must contain ``national/index`` plus at
    least one nonempty national chunk (smoke query). Mirrors the fail-closed
    conventions of ``_require_national_block``: raise in the build, never
    publish a broken pointer.
    """
    prefix = f"{RELEASES_PREFIX}{snapshot_id}/"
    legacy: dict[str, str] = {e["key"]: e["value"] for e in kv_entries}
    release: dict[str, str] = {}
    for entry in release_entries:
        key = entry["key"]
        if not key.startswith(prefix):
            raise ValueError(
                f"snapshot promotion: release key {key!r} is not under {prefix}; "
                "refusing to promote the pointer"
            )
        release[key[len(prefix) :]] = entry["value"]
    missing = sorted(set(legacy) - set(release))
    if missing:
        raise ValueError(
            f"snapshot promotion: missing release entries for {missing[:5]} "
            f"({len(missing)} total); refusing to promote the pointer"
        )
    mismatched = sorted(k for k in legacy if legacy[k] != release[k])
    if mismatched:
        raise ValueError(
            f"snapshot promotion: release twins differ from legacy content for "
            f"{mismatched[:5]}; refusing to promote the pointer"
        )
    if _national_smoke_required(national_block):
        if "national/index" not in release:
            raise ValueError(
                "snapshot promotion: national smoke check failed — "
                f"{prefix}national/index missing; refusing to promote the pointer"
            )
        nonempty = [
            k
            for k in release
            if k.startswith("national/")
            and k != "national/index"
            and bool((json.loads(release[k]) or {}).get("rows"))
        ]
        if not nonempty:
            raise ValueError(
                "snapshot promotion: national smoke check failed — no nonempty "
                "national chunk in the release set; refusing to promote the pointer"
            )


def _promote_snapshot_pointer(
    kv_entries: list[dict[str, str]],
    release_entries: list[dict[str, str]],
    snapshot_id: str,
    national_block: dict[str, Any] | None,
    previous_pointer: dict[str, Any] | None,
    promoted_at: str,
) -> dict[str, Any]:
    """Build the ``snapshot/current`` pointer or refuse (fail closed).

    Verifies the full release set first (integrity + national smoke); only
    then is the pointer handed back for the bulk. Rebuilding identical content
    is idempotent: the pointer keeps its original ``promoted_at`` and its
    ``previous`` generation — ``previous`` advances only on genuinely new
    content.
    """
    _verify_release_integrity(release_entries, kv_entries, snapshot_id, national_block)
    if previous_pointer is not None and previous_pointer.get("current") == snapshot_id:
        return {
            "current": snapshot_id,
            "previous": previous_pointer.get("previous"),
            "promoted_at": previous_pointer.get("promoted_at"),
        }
    return {
        "current": snapshot_id,
        "previous": None if previous_pointer is None else previous_pointer.get("current"),
        "promoted_at": promoted_at,
    }


async def build_snapshot(
    out_dir: Path,
    engine: MultiHorizonInferenceEngine | None = None,
    cities: list[str] | None = None,
    include_legacy_cells: bool = True,
    national_dir: Path | None = None,
    dense_metro: bool = False,
    require_national: bool = False,
    context_dir: Path | None = None,
    metrics: SnapshotMetrics | None = None,
    cache_predictions: bool = True,
    metrics_out: Path | None = None,
    model_bundle: Path | None = None,
) -> dict[str, Any]:
    """Build one snapshot, optionally collecting timings outside the KV payload."""
    total = metrics.stage("total") if metrics is not None else nullcontext()
    with total:
        try:
            if engine is None:
                initialization = (
                    metrics.stage("model_initialization") if metrics is not None else nullcontext()
                )
                with initialization:
                    engine = MultiHorizonInferenceEngine(
                        metrics=metrics,
                        cache_predictions=cache_predictions,
                        model_bundle=model_bundle,
                    )
            elif metrics is not None:
                with metrics.stage("model_initialization"):
                    pass
                # Instrument engines supplied by callers as well as the CLI's
                # default engine. Preserve and restore a caller's prior value.
                previous_metrics = getattr(engine, "metrics", None)
                engine.metrics = metrics
            else:
                previous_metrics = None
            manifest = await _build_snapshot(
                out_dir,
                engine=engine,
                cities=cities,
                include_legacy_cells=include_legacy_cells,
                national_dir=national_dir,
                dense_metro=dense_metro,
                require_national=require_national,
                context_dir=context_dir,
                metrics=metrics,
                metrics_out=metrics_out,
            )
            if metrics is not None:
                metrics.set_artifact("status", "complete")
            return manifest
        except BaseException as exc:
            if metrics is not None:
                metrics.set_artifact("status", "incomplete")
                metrics.set_artifact("failure", {"type": type(exc).__name__, "message": str(exc)})
            raise
        finally:
            if metrics is not None and engine is not None and "previous_metrics" in locals():
                engine.metrics = previous_metrics


async def _build_snapshot(
    out_dir: Path,
    engine: MultiHorizonInferenceEngine,
    cities: list[str] | None = None,
    include_legacy_cells: bool = True,
    national_dir: Path | None = None,
    dense_metro: bool = False,
    require_national: bool = False,
    context_dir: Path | None = None,
    metrics: SnapshotMetrics | None = None,
    metrics_out: Path | None = None,
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

    ``context_dir`` points at a ``src.export.bay_area_context`` output. When it
    carries a table, its per-hex metrics are joined onto matching grid cells at
    every LOD level, ranked like the model metrics, and listed in the
    manifest's ``context_layers`` block; when omitted the grid is unchanged.
    """
    out_dir = Path(out_dir)
    build_start = time.perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)
    cities = list(cities or SUPPORTED_CITIES)

    kv_entries: list[dict[str, str]] = []
    keys_index: dict[str, dict[str, Any]] = {}
    counts: dict[str, Any] = {}

    def register(key: str, path: Path, payload: Any) -> int:
        serialization = metrics.stage("serialization") if metrics is not None else nullcontext()
        with serialization:
            size = _write_json(path, payload)
        if size > MAX_KV_VALUE_BYTES:
            raise ValueError(
                f"KV value '{key}' is {size:,} bytes, over the {MAX_KV_VALUE_BYTES:,}-byte "
                f"build budget (KV hard cap 25 MiB). Shard the key before publishing."
            )
        keys_index[key] = {"bytes": size}
        kv_entries.append({"key": key, "value": json.dumps(payload, separators=(",", ":"))})
        if metrics is not None:
            family = key.split("/", 1)[0]
            metrics.increment(f"keys.{family}")
            metrics.increment(f"value_bytes.{family}", size)
        return size

    grids: dict[str, dict[str, Any]] = {}
    catalysts_by_city: dict[str, dict[str, Any]] = {}
    submarkets_by_city: dict[str, dict[str, Any]] = {}

    city_timer = metrics.stage("city_inference") if metrics is not None else nullcontext()
    with city_timer:
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

    try:
        context = load_context(context_dir) if context_dir is not None else None
    except Exception as exc:
        if metrics is not None:
            metrics.set_context_availability(False, f"load_failed: {type(exc).__name__}: {exc}")
        raise
    if metrics is not None and context_dir is not None:
        metrics.set_context_availability(
            context is not None,
            None if context is not None else "context_inputs_unavailable",
        )
    context_keys: tuple[str, ...] = ()
    if context is not None:
        _apply_context_layers(grids, context[0])
        context_keys = CONTEXT_METRIC_KEYS
    elif context_dir is not None:
        logger.warning("No context table at %s; publishing without context layers", context_dir)

    # Percentiles must see every exported metro before anything reaches KV.
    # res-9 is its own national rank space (unchanged); each LOD aggregate
    # level is ranked against ITS complete publish (US-415 method A — average
    # raw, then rank per level, never average child percentiles).
    ranking_timer = metrics.stage("ranking_lod") if metrics is not None else nullcontext()
    with ranking_timer:
        _apply_percentile_normalization(grids)
        _apply_context_percentiles(grids, context_keys)
        grids_by_res: dict[int, dict[str, dict[str, Any]]] = {DEFAULT_RESOLUTION: grids}
        for res in (8, 7):
            lod_grids = {
                city: _aggregate_grid_to_res(grids[city], city, res, extra_keys=context_keys)
                for city in cities
            }
            _apply_percentile_normalization(lod_grids)
            _apply_context_percentiles(lod_grids, context_keys)
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

    cell_timer = metrics.stage("cell_inference_shap") if metrics is not None else nullcontext()
    if metrics is not None:
        metrics.increment(
            "unique_normalized_vectors",
            len({tuple(float(feats.get(key, 0.0)) for key in FEATURE_COLUMNS) for _, feats in cells_requests}),
        )
    with cell_timer, ThreadPoolExecutor(max_workers=CELL_INFERENCE_WORKERS) as pool:
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
    national_seconds: float | None = None
    if national_dir is not None:
        national_start = time.perf_counter()
        national_block = _publish_national_layers(out_dir, national_dir, register)
        national_seconds = time.perf_counter() - national_start
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
    if context is not None:
        manifest["context_layers"] = _context_manifest_block(grids, context[1])
    # Additive Stage A fields (hex-coverage): appended after the existing
    # fields; no existing key is reordered or altered.
    manifest["coverage"] = _coverage_block(national_block)
    manifest["snapshot_id"] = _manifest_snapshot_id(manifest)
    manifest_size = _write_json(out_dir / "manifest.json", manifest)
    if manifest_size > MAX_MANIFEST_BYTES:
        raise ValueError(
            f"Manifest is {manifest_size:,} bytes, over the {MAX_MANIFEST_BYTES:,}-byte boot "
            f"budget. Slim it (split tile_indexes into their own key) before publishing."
        )
    register("manifest", out_dir / "manifest.json", manifest)

    if metrics_out is not None:
        # Build report: timing + per-resolution counts from the published
        # national summary (present only when chunks actually shipped).
        report = {
            "generated_at": manifest["generated_at"],
            "snapshot_id": manifest["snapshot_id"],
            "build_seconds": time.perf_counter() - build_start,
            "cells": len(cells_by_index),
            "national": None
            if national_block is None
            else {
                "seconds": national_seconds,
                "resolutions": national_block["resolutions"],
            },
        }
        metrics_out = Path(metrics_out)
        metrics_out.parent.mkdir(parents=True, exist_ok=True)
        metrics_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    bulk_path = out_dir / "kv-bulk.json"
    # Stage B: release-qualified twins plus the snapshot/current pointer. The
    # pointer is only built after the full release set verifies (fail closed),
    # and the size budget is checked BEFORE the write so a failed build leaves
    # the previous kv-bulk.json (and its pointer) untouched.
    snapshot_id = manifest["snapshot_id"]
    release_entries = _release_entries(kv_entries, snapshot_id)
    pointer = _promote_snapshot_pointer(
        kv_entries,
        release_entries,
        snapshot_id,
        national_block,
        _read_previous_pointer(bulk_path),
        datetime.now(UTC).isoformat(),
    )
    bulk_entries = [
        *kv_entries,
        *release_entries,
        {"key": SNAPSHOT_POINTER_KEY, "value": json.dumps(pointer, separators=(",", ":"))},
    ]
    bulk_bytes = json.dumps(bulk_entries)
    bulk_size = len(bulk_bytes.encode("utf-8"))
    if metrics is not None:
        metrics.set_artifact("key_count", len(bulk_entries))
        metrics.set_artifact("bulk_bytes", bulk_size)
        metrics.set_artifact("unique_cells", len(cells_by_index))
        metrics.set_artifact("cities", list(cities))
    if bulk_size > MAX_BULK_BYTES:
        raise ValueError(
            f"kv-bulk.json would be {bulk_size:,} bytes, over the "
            f"{MAX_BULK_BYTES:,}-byte build budget. Chunk the bulk put."
        )
    bulk_path.write_text(bulk_bytes, encoding="utf-8")

    logger.info(
        "Snapshot complete: %d KV keys (%d grid tiles, %d cells) -> %s (%d bytes bulk)",
        len(bulk_entries),
        len(tile_index),
        len(cells_by_index),
        bulk_path,
        bulk_size,
    )
    _write_publication_plan(out_dir, kv_entries, manifest, engine)
    return manifest


def _write_publication_plan(
    out_dir: Path,
    kv_entries: list[dict[str, str]],
    manifest: dict[str, Any],
    engine: MultiHorizonInferenceEngine,
) -> None:
    """Write a report-only content-addressed plan next to the legacy bulk file."""
    model_id = getattr(engine, "model_bundle_id", None) or getattr(
        engine, "model_provenance", "synthetic-default"
    )
    metadata = {
        "as_of": str(manifest.get("generated_at", ""))[:10],
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "model_id": model_id,
        "source_revisions": {
            "app_version": manifest.get("app_version"),
            "product_snapshot_id": manifest.get("snapshot_id"),
        },
    }
    plan = plan_publication(kv_entries, None, metadata)
    payload = {
        "metadata": metadata,
        "object_bytes": sum(len(value) for value in plan.objects.values()),
        "object_count": len(plan.objects),
        "reuse_candidates": list(plan.reuse_candidates),
        "snapshot_id": plan.snapshot_id,
    }
    (out_dir / "publication-plan.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
        "--context-dir",
        default=None,
        help=(
            "src.export.bay_area_context output (bay_area_context_res9.parquet + meta); "
            "omit to publish without the Bay Area context layers"
        ),
    )
    parser.add_argument(
        "--dense-metro",
        action="store_true",
        help="Use bounded k_ring=3 coverage (coverage.metro_cells) for continuous urban hexes",
    )
    parser.add_argument(
        "--metrics-out",
        default=None,
        help="Write schema-1 builder metrics JSON outside the KV payload",
    )
    parser.add_argument(
        "--no-prediction-cache",
        action="store_true",
        help="Disable bounded model prediction and SHAP caches for this build",
    )
    parser.add_argument(
        "--model-bundle",
        default=None,
        help="Verified synthetic bundle directory (manifest.json plus model artifacts)",
    )
    args = parser.parse_args()
    context_dir = Path(args.context_dir) if args.context_dir else None
    metrics = SnapshotMetrics(context_dir=context_dir) if args.metrics_out else None
    try:
        asyncio.run(
            build_snapshot(
                Path(args.out),
                cities=args.cities,
                include_legacy_cells=not args.skip_legacy_cells,
                national_dir=Path(args.national_dir) if args.national_dir else None,
                dense_metro=args.dense_metro,
                require_national=args.require_national,
                context_dir=context_dir,
                metrics=metrics,
                cache_predictions=not args.no_prediction_cache,
                model_bundle=Path(args.model_bundle) if args.model_bundle else None,
            )
        )
    finally:
        if metrics is not None:
            metrics.write(Path(args.metrics_out))


if __name__ == "__main__":
    main()
