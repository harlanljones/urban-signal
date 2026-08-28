"""National hex grid: deterministic hierarchically-closed H3 pyramid over the United States.

The outline asset is the US Census Bureau cartographic boundary file
``cb_2023_us_nation_20m`` (public domain, GEOID 0100000US), simplified with a
0.004° (~440 m) tolerance and 5-decimal coordinate rounding, vendored at
``assets/us_outline_census_20m.geojson``. It covers the entire country — the
50 states, DC, and the territories present in the census file (PR, VI, Guam,
Northern Marianas, American Samoa) — including the antimeridian-crossing
Aleutian parts (each a separate polygon part, so per-part polyfill is safe).

Resolution model: ``res 4`` is the direct polyfill of the outline;
``res 5`` is the union of ``res 4`` children; ``res 6`` is the union of
``res 5`` children. A per-resolution polyfill is NOT hierarchically closed
along coastlines (a fine cell's centroid can sit inside the outline while its
coarse parent's centroid sits outside), and the LOD display layer depends on
coherent parent/child swaps, so closure is enforced by construction. Measured
cost of closure vs raw polyfill at the vendored outline: 36,757 vs 36,771
cells at res 5 (+0.04% area), identical at res 4.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import h3

OUTLINE_ASSET = Path(__file__).with_name("assets") / "us_outline_census_20m.geojson"
BASE_RESOLUTION = 4
NATIONAL_RESOLUTIONS = (4, 5, 6)
H3_CHILDREN_PER_CELL = 7

# Golden counts for the vendored outline (deterministic; asserted by tests).
# res 5/6 are exact multiples of the base count because they are built as
# children of the previous level.
NATIONAL_GOLDEN_COUNTS: dict[int, int] = {
    4: 5251,
    5: 5251 * H3_CHILDREN_PER_CELL,
    6: 5251 * H3_CHILDREN_PER_CELL**2,
}


def outline_path() -> Path:
    """Path to the vendored US outline GeoJSON asset."""
    return OUTLINE_ASSET


@lru_cache(maxsize=1)
def load_outline_geometry() -> dict:
    """Load the vendored outline as a GeoJSON geometry dict (MultiPolygon)."""
    import json

    with OUTLINE_ASSET.open(encoding="utf-8") as handle:
        feature = json.load(handle)
    geometry = feature.get("geometry")
    if geometry is None or geometry.get("type") != "MultiPolygon":
        raise ValueError(f"Unexpected outline asset structure in {OUTLINE_ASSET}")
    return geometry


@lru_cache(maxsize=1)
def _outline_latlngmultipoly() -> h3.LatLngMultiPoly:
    """Convert the GeoJSON outline to an h3 LatLngMultiPoly (GeoJSON [lng, lat] -> (lat, lng))."""
    polygons = []
    for poly in load_outline_geometry()["coordinates"]:
        rings = [[(lat, lng) for lng, lat in ring] for ring in poly]
        polygons.append(h3.LatLngPoly(rings[0], *rings[1:]))
    return h3.LatLngMultiPoly(*polygons)


@lru_cache(maxsize=1)
def base_cells(resolution: int = BASE_RESOLUTION) -> tuple[str, ...]:
    """Direct polyfill of the US outline at the base resolution (sorted, deduped)."""
    if resolution != BASE_RESOLUTION:
        raise ValueError(f"Base resolution is {BASE_RESOLUTION}, got {resolution}")
    cells = h3.polygon_to_cells(_outline_latlngmultipoly(), resolution)
    return tuple(sorted(cells))


@lru_cache(maxsize=None)
def cells_at_resolution(resolution: int) -> tuple[str, ...]:
    """All national cells at ``resolution``, hierarchically closed to the base polyfill."""
    if resolution not in NATIONAL_RESOLUTIONS:
        raise ValueError(f"Resolution {resolution} outside national set {NATIONAL_RESOLUTIONS}")
    cells: set[str] = set(base_cells(BASE_RESOLUTION))
    for level in range(BASE_RESOLUTION, resolution):
        cells = {child for parent in cells for child in h3.cell_to_children(parent, level + 1)}
    return tuple(sorted(cells))


def national_pyramid() -> dict[int, tuple[str, ...]]:
    """The full national cell pyramid {resolution: sorted cells} for all national resolutions."""
    return {res: cells_at_resolution(res) for res in NATIONAL_RESOLUTIONS}


def count_at_resolution(resolution: int) -> int:
    """Number of national cells at ``resolution`` (must match NATIONAL_GOLDEN_COUNTS)."""
    return len(cells_at_resolution(resolution))


def cell_centroid(h3_index: str) -> tuple[float, float]:
    """(lat, lng) centroid of a national cell."""
    return h3.cell_to_latlng(h3_index)


def parent_at(h3_index: str, resolution: int) -> str:
    """Parent of ``h3_index`` at a coarser national resolution."""
    return h3.cell_to_parent(h3_index, resolution)
