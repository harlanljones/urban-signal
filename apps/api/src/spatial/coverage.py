"""Metro hex coverage: density policy and LOD aggregation seam.

Owns two questions the map pipeline previously hardcoded in three places
(``router.get_grid_geojson``, ``snapshot_builder._bucket_grid_tiles``, and the
dashboard's ``res5ParentsCoveringBounds``):

1. **Which H3 cells belong to a metro's render set?** ``metro_cells`` is the
   single density policy: a bounded ``k_ring`` around each submarket center.
   The bound (``max_dist_km=1.5`` at res 9) keeps the render set continuous
   across the urban core without synthesizing values into the rural exurbs —
   the US-408 grill decision "bounded expansion", not full-bbox synthesis.

2. **Which submarket owns a cell, and is that ownership interpolated?**
   ``assign_cell`` resolves a cell to its nearest submarket and reports the
   distance + source, so a caller can build synthetic features from that
   submarket's baselines and mark the result ``k_ring_interpolated`` (honesty
   rule, see ``docs/research/map-blended-lod-honesty.md``).

3. **How do cells roll up to a coarser LOD level?** ``aggregate_values``
   averages raw metric values per parent cell. Per US-415, percentiles are
   ranked AFTER aggregation (average raw then rank), never by averaging child
   percentiles — averaging child percentiles collapses rank variance to ~21%
   at res 7 and ~52% at res 8 on the shared ramp.

This module is deliberately transport-free and engine-free: it returns H3
indexes and plain data, never running inference or touching HTTP/KV. The
caller (router / snapshot_builder) owns feature synthesis and prediction.

Seam note (US-408 horizon "Plan MVT next"): ``metro_cells``/``aggregate_values``
are the same input a future vector-tile pyramid would consume; if MVT lands,
the per-parent bucketing keys map ``gridtiles_res*/{parent}`` →
``tiles/{z}/{x}/{y}.pbf`` without touching these signatures.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass

import h3

from src.spatial.h3_indexer import H3SpatialIndexer
from src.spatial.submarkets import SubmarketMeta, find_nearest_submarket, get_submarket_by_name

# Nominal cell areas (km²) from H3SpatialIndexer.CELL_AREAS_KM2 — used only for
# documentation/expectation checks, not for any geometric decision here.
CELL_AREA_KM2 = H3SpatialIndexer.CELL_AREAS_KM2

# LOD levels the metro pyramid publishes. Kept here so the snapshot builder,
# edge worker, and dashboard agree on one source of truth (US-411/US-412/US-413).
METRO_LOD_RESOLUTIONS = (7, 8, 9)

# Bounded-expansion defaults from the US-408 grill.
DEFAULT_MAX_RING = 3
DEFAULT_MAX_DIST_KM = 1.5


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km (Earth radius 6371 km)."""
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return radius * 2 * math.asin(math.sqrt(a))


def metro_cells(
    city_id: str,
    res: int = 9,
    max_ring: int = DEFAULT_MAX_RING,
    max_dist_km: float | None = DEFAULT_MAX_DIST_KM,
) -> list[str]:
    """All H3 cells in a metro's render set at ``res``.

    Builds a bounded ``k_ring`` around every registered submarket center and
    unions them. When ``max_dist_km`` is set, a ring cell is kept only if it
    lies within that distance of *its own* submarket center (per-center
    haversine bound, deduped by set union). ``max_dist_km=None`` keeps the full
    unbounded ring.

    Deterministic: iterates ``REGISTRY[city].submarkets`` in insertion order
    and returns a sorted list.
    """
    from src.spatial.city_registry import REGISTRY, normalize_city

    cid = normalize_city(city_id)
    if cid is None or cid not in REGISTRY:
        raise ValueError(f"Unknown city_id '{city_id}' for metro_cells coverage query.")

    cells: set[str] = set()
    for meta in REGISTRY[cid].submarkets.values():
        center = H3SpatialIndexer.latlng_to_h3(meta.lat, meta.lng, resolution=res)
        ring = H3SpatialIndexer.get_k_ring(center, k=max_ring)
        if max_dist_km is None:
            cells.update(ring)
            continue
        for cell in ring:
            lat, lng = h3.cell_to_latlng(cell)
            if _haversine_km(meta.lat, meta.lng, lat, lng) <= max_dist_km:
                cells.add(cell)
    return sorted(cells)


@dataclass(frozen=True)
class CellAssignment:
    """Which submarket owns a cell, and how the value was obtained."""

    cell: str
    submarket: str
    borough: str
    distance_km: float
    # "center"  = the cell IS the submarket's own center cell (measured)
    # "bounded" = a ring cell inside max_dist_km of its center (interpolated)
    source: str


def assign_cell(
    cell: str,
    city_id: str,
    max_dist_km: float = 25.0,
) -> CellAssignment | None:
    """Resolve ``cell`` to its nearest submarket, or None if too far.

    Uses the registry's nearest-submarket resolution (the same path event rows
    use), so a cell just outside any submarket bound returns None rather than
    inventing an owner. ``source`` is ``"center"`` when the cell is within a
    tiny epsilon of the submarket center, else ``"bounded"``.
    """
    from src.spatial.city_registry import REGISTRY, normalize_city

    cid = normalize_city(city_id)
    if cid is None or cid not in REGISTRY:
        raise ValueError(f"Unknown city_id '{city_id}' for coverage assign_cell.")

    try:
        lat, lng = h3.cell_to_latlng(cell)
    except ValueError:  # malformed / invalid H3 index
        return None

    name, dist_km = find_nearest_submarket(lat, lng, city_id=cid.value, max_distance_km=max_dist_km)
    if not name:
        return None
    meta = get_submarket_by_name(name, city_id=cid.value)
    if meta is None:
        return None

    center = H3SpatialIndexer.latlng_to_h3(meta.lat, meta.lng, resolution=9)
    source = "center" if cell == center else "bounded"
    return CellAssignment(
        cell=cell,
        submarket=name,
        borough=meta.borough,
        distance_km=round(dist_km, 3),
        source=source,
    )


def assigned_features(
    cell: str,
    city_id: str,
    max_dist_km: float = 25.0,
) -> dict[str, object] | None:
    """Return feature-ready ownership metadata for ``cell``.

    This is the public seam for producers that need to synthesize a cell from
    its nearest submarket.  It intentionally returns plain data (rather than
    importing the serving router), which keeps coverage usable by snapshot and
    future vector-tile producers without creating an import cycle.
    """
    assignment = assign_cell(cell, city_id, max_dist_km=max_dist_km)
    if assignment is None:
        return None
    meta = submarket_meta(city_id, assignment.submarket)
    if meta is None:
        return None

    # Match the feature names used by the live grid endpoint.  Keep source and
    # distance beside the values so the dashboard can be honest about
    # interpolated coverage.
    permit_velocity = meta.permit_vel if meta.permit_vel <= 1.0 else meta.permit_vel / 100.0
    props: dict[str, object] = {
        "submarket": meta.name,
        "borough": meta.borough,
        "city_id": city_id,
        "capex_density_decayed": meta.capex,
        "permit_velocity": permit_velocity,
        "shift_ratio_311": meta.shift_ratio,
        "sla_new_filings_90d": int(meta.sla),
        "lims_score": meta.base_lims * 100.0 if meta.base_lims <= 1.0 else meta.base_lims,
    }
    return {
        "props": props,
        "source": "measured" if assignment.source == "center" else "k_ring_interpolated",
        "nearest_submarket": assignment.submarket,
        "dist_km": assignment.distance_km,
    }


def aggregate_values(
    cells: Iterable[str],
    value_of: Callable[[str], float | None],
    to_res: int,
) -> dict[str, float]:
    """Average a raw metric per parent cell at ``to_res``.

    US-415 policy: average RAW values, never average child percentiles. Null
    values are skipped (an absent value means "no data" — honesty rule, it
    must not drag a parent's average toward zero).
    """
    if to_res >= 9:
        raise ValueError(f"aggregate_values only rolls UP to a coarser res, got to_res={to_res}")
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for cell in cells:
        value = value_of(cell)
        if value is None:
            continue
        parent = h3.cell_to_parent(cell, to_res)
        sums[parent] = sums.get(parent, 0.0) + value
        counts[parent] = counts.get(parent, 0) + 1
    return {parent: sums[parent] / counts[parent] for parent in sums}


def aggregate(
    cells: Iterable[str],
    to_res: int,
    values: dict[str, dict[str, float | int | None]] | None = None,
) -> dict[str, dict[str, float | int]]:
    """Aggregate feature values and child counts by H3 parent.

    ``values`` is optional so callers that only have cell indexes can still
    build a useful pyramid inventory.  When supplied, each numeric field is
    averaged independently, skipping nulls; this is the raw-value-first rule
    required before percentile normalization.  The result always includes
    ``count`` and uses deterministic parent ordering.
    """
    if to_res >= 9:
        raise ValueError(f"aggregate only rolls UP to a coarser res, got to_res={to_res}")
    buckets: dict[str, list[str]] = {}
    for cell in cells:
        parent = h3.cell_to_parent(cell, to_res)
        buckets.setdefault(parent, []).append(cell)

    result: dict[str, dict[str, float | int]] = {}
    for parent in sorted(buckets):
        children = buckets[parent]
        summary: dict[str, float | int] = {"count": len(children)}
        if values is not None:
            fields = sorted({key for child in children for key in values.get(child, {})})
            for field in fields:
                numeric = [
                    float(values[child][field])
                    for child in children
                    if values.get(child, {}).get(field) is not None
                ]
                if numeric:
                    summary[f"avg_{field}"] = sum(numeric) / len(numeric)
        result[parent] = summary
    return result


def parent_cells(cell: str, parent_res: int) -> list[str]:
    """Child cells of ``cell`` at ``parent_res`` (must be finer than the cell)."""
    return H3SpatialIndexer.get_children(cell, parent_res)


def submarket_meta(city_id: str, name: str) -> SubmarketMeta | None:
    """Look up a submarket by name within one city (None when absent)."""
    return get_submarket_by_name(name, city_id=city_id)
