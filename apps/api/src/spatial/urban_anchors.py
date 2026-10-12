"""Urban Anchors: Census 2020 Urban Area geometry that bounds detail coverage (ADR-0010).

The asset is the Census Bureau cartographic boundary file ``cb_2020_us_ua20_500k``
(public domain), simplified and vendored by ``scripts/vendor_urban_anchors.py`` at
``assets/us_urban_areas_2020.geojson``. Every feature is a MultiPolygon so per-part
polyfill is safe across the antimeridian (same pattern as ``national_grid``).

Cell sets are hierarchically closed: the res-7 polyfill is the base and res 8/9 are
the union of children, so parent/child LOD swaps stay coherent along boundaries.
This module is transport-free: no engine, serving, or HTTP imports (INV-5).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import h3
from shapely.geometry import box, shape
from shapely.strtree import STRtree

ANCHOR_ASSET = Path(__file__).with_name("assets") / "us_urban_areas_2020.geojson"
# Pinned at vendoring (scripts/vendor_urban_anchors.py): the Census 2020 UA count in
# the 500k cartographic boundary file, including Puerto Rico and Island Areas.
ANCHOR_GOLDEN_COUNT = 2645
BASE_DETAIL_RESOLUTION = 7
DETAIL_RESOLUTIONS = (7, 8, 9)

# Detail-resolution class thresholds (spec §3.2; proposed, calibrate via DG-3).
LARGE_POPULATION = 1_000_000
LARGE_LAND_KM2 = 1_000.0
MID_POPULATION = 100_000
MID_LAND_KM2 = 100.0


@dataclass(frozen=True)
class UrbanAnchor:
    anchor_id: str  # UACE20
    name: str
    land_km2: float
    population: int | None
    geometry: dict  # GeoJSON MultiPolygon, [lng, lat]


@lru_cache(maxsize=1)
def load_anchors() -> dict[str, UrbanAnchor]:
    """All vendored anchors keyed by id. Raises if the asset drifts from the golden count."""
    with ANCHOR_ASSET.open(encoding="utf-8") as handle:
        collection = json.load(handle)
    anchors: dict[str, UrbanAnchor] = {}
    for feature in collection["features"]:
        props = feature["properties"]
        anchor = UrbanAnchor(
            anchor_id=props["anchor_id"],
            name=props["name"],
            land_km2=float(props["land_km2"]),
            population=props.get("population"),
            geometry=feature["geometry"],
        )
        if anchor.anchor_id in anchors:
            raise ValueError(f"duplicate urban anchor id {anchor.anchor_id!r}")
        anchors[anchor.anchor_id] = anchor
    if len(anchors) != ANCHOR_GOLDEN_COUNT:
        raise ValueError(
            f"urban anchor asset has {len(anchors)} features, expected {ANCHOR_GOLDEN_COUNT}; "
            "rebaseline ANCHOR_GOLDEN_COUNT explicitly after re-vendoring"
        )
    return anchors


def _latlng_multipoly(geometry: dict) -> h3.LatLngMultiPoly:
    polygons = []
    for poly in geometry["coordinates"]:
        rings = [[(lat, lng) for lng, lat in ring] for ring in poly]
        polygons.append(h3.LatLngPoly(rings[0], *rings[1:]))
    return h3.LatLngMultiPoly(*polygons)


@lru_cache(maxsize=512)
def _base_cells(anchor_id: str) -> tuple[str, ...]:
    """Res-7 cells whose centers fall inside the anchor; never empty.

    An anchor smaller than one res-7 cell can contain no cell center, so it falls back to
    the cell containing its representative point: every anchor owns at least one cell.
    """
    anchor = load_anchors()[anchor_id]
    cells = set(h3.polygon_to_cells(_latlng_multipoly(anchor.geometry), BASE_DETAIL_RESOLUTION))
    if not cells:
        point = shape(anchor.geometry).representative_point()
        cells = {h3.latlng_to_cell(point.y, point.x, BASE_DETAIL_RESOLUTION)}
    return tuple(sorted(cells))


@lru_cache(maxsize=256)
def anchor_cells(anchor_id: str, res: int) -> tuple[str, ...]:
    """Sorted, deduped cells covering the anchor at ``res`` (7, 8, or 9), hierarchically closed."""
    if res not in DETAIL_RESOLUTIONS:
        raise ValueError(f"resolution {res} outside detail set {DETAIL_RESOLUTIONS}")
    if anchor_id not in load_anchors():
        raise KeyError(f"unknown urban anchor {anchor_id!r}")
    cells: set[str] = set(_base_cells(anchor_id))
    for level in range(BASE_DETAIL_RESOLUTION + 1, res + 1):
        cells = {child for cell in cells for child in h3.cell_to_children(cell, level)}
    return tuple(sorted(cells))


@lru_cache(maxsize=1)
def _index() -> tuple[STRtree, tuple[str, ...]]:
    ids = tuple(load_anchors())
    geoms = [shape(load_anchors()[anchor_id].geometry) for anchor_id in ids]
    return STRtree(geoms), ids


def anchors_intersecting(bbox: dict[str, float]) -> tuple[str, ...]:
    """Anchor ids whose geometry (not merely bbox) intersects ``bbox``; sorted."""
    tree, ids = _index()
    window = box(bbox["min_lng"], bbox["min_lat"], bbox["max_lng"], bbox["max_lat"])
    hits = tree.query(window, predicate="intersects")
    return tuple(sorted(ids[i] for i in hits))


def detail_resolution(anchor: UrbanAnchor) -> int:
    """Detail resolution for an anchor's size class: large 9, mid 8, small 7 (spec §3.2)."""
    pop = anchor.population or 0
    if pop >= LARGE_POPULATION or anchor.land_km2 >= LARGE_LAND_KM2:
        return 9
    if pop >= MID_POPULATION or anchor.land_km2 >= MID_LAND_KM2:
        return 8
    return 7
