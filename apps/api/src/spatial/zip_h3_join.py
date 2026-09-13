"""ZIP (ZCTA) -> H3 res-9 area-weighted join (US-440).

The centroid-only crosswalk (`geography_crosswalk.zip_to_h3`) tags exactly
one hex per ZIP — correct for a ZIP that is smaller than a hex, wrong the
moment a ZCTA spans dozens of them (every Bay Area ZCTA does at res-9: a
res-9 cell averages ~0.1 km^2, a ZCTA is typically several km^2). This module
computes the actual overlap between each ZCTA polygon and every H3 res-9 cell
it touches, and uses that overlap to allocate ZIP-level market values onto
hexes two different ways, per the ticket's acceptance criteria:

* **Intensive** variables (a price, a rent, a day-on-market count — a level
  that doesn't sum) are **area-weighted**: a hex's value is the average of
  every overlapping ZCTA's value, weighted by how much of the *hex's* area
  that ZCTA covers.
* **Extensive** variables (homes sold, inventory — a count that does sum) are
  **proportionally allocated**: a hex's share of a ZCTA's total is the
  fraction of the *ZCTA's* area that falls in that hex.

Both weights come from the same intersection; only the denominator differs
(hex area vs. ZCTA area), so :func:`build_weights` computes both at once per
``(zcta, hex)`` pair touched.

**Why EPSG:3310.** Shapely's default planar area on WGS84 degrees is not
area-preserving — a degree of longitude shrinks with latitude — so ratios
computed directly from lat/lng coordinates are subtly wrong even over a
single metro. NAD83 / California Albers (EPSG:3310) is an equal-area
projection built for exactly this: California-scoped area comparisons.
``pyproj`` is already a dependency (geopandas/fiona are not), so
reprojection costs one ``Transformer`` call, not a new dependency.

**Missing data fallback.** A ZCTA can have no market observation for a given
period (rural, PO-Box-only, or too few transactions for Redfin/Zillow to
publish that month — see ``redfin_client``'s "All Residential" NA handling).
The aggregation functions here simply drop that ZCTA's contribution to a hex
rather than raising or defaulting to zero, so a hex touched by an
under-observed ZIP alongside a well-observed one still gets a value from the
one that reported.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import h3
from pyproj import Transformer
from shapely.geometry import Polygon
from shapely.ops import transform as shapely_transform

logger = logging.getLogger(__name__)

DEFAULT_RESOLUTION = 9

# WGS84 (lat/lng, what every polygon in this codebase is expressed in) ->
# NAD83 / California Albers (an equal-area CRS). always_xy=True so the
# transformer takes (lng, lat) in that order, matching shapely's (x, y).
_TO_EQUAL_AREA = Transformer.from_crs("EPSG:4326", "EPSG:3310", always_xy=True)


def _equal_area(polygon: Polygon) -> Polygon:
    """Reproject a WGS84 polygon to CA Albers for area-accurate math."""
    return shapely_transform(_TO_EQUAL_AREA.transform, polygon)


def _hex_polygon(h3_cell: str) -> Polygon:
    """Build a WGS84 Polygon for one H3 cell, reusing this repo's (lat, lng) convention."""
    from src.spatial.geo_utils import create_shapely_polygon

    boundary = h3.cell_to_boundary(h3_cell)
    return create_shapely_polygon(list(boundary))


@dataclass(frozen=True)
class ZipHexWeight:
    """One ZCTA's overlap with one H3 cell.

    ``hex_fraction``: share of the hex's area this ZCTA covers — the weight
    for intensive (area-weighted average) aggregation.
    ``zcta_fraction``: share of the ZCTA's area that falls in this hex — the
    weight for extensive (proportional allocation) aggregation.
    """

    hex_fraction: float
    zcta_fraction: float


def build_weights(
    polygons: Mapping[str, Polygon], resolution: int = DEFAULT_RESOLUTION
) -> dict[str, dict[str, ZipHexWeight]]:
    """Polyfill each ZCTA polygon to H3 cells and compute area-overlap weights.

    Returns ``{h3_cell: {zcta: ZipHexWeight}}``. A ZCTA with degenerate or
    empty geometry (invalid ring, zero area) is skipped rather than raising —
    the same "missing data fallback" posture as a ZCTA with no market
    observation, just at the geometry stage instead of the value stage.
    """
    weights: dict[str, dict[str, ZipHexWeight]] = {}
    for zcta, polygon in polygons.items():
        if polygon is None or polygon.is_empty:
            continue
        try:
            zcta_area = _equal_area(polygon).area
        except Exception:  # noqa: BLE001 — one bad ZCTA geometry must not kill the whole join
            logger.warning("zcta %s: failed to reproject for area calc", zcta)
            continue
        if zcta_area <= 0:
            continue

        try:
            h3_shape = h3.LatLngPoly([(lat, lng) for lng, lat in polygon.exterior.coords])
            cells = h3.polygon_to_cells(h3_shape, resolution)
        except Exception:  # noqa: BLE001 — degenerate polygon (self-intersecting ring) skips, not raises
            logger.warning("zcta %s: failed to polyfill to H3 res %s", zcta, resolution)
            continue

        for cell in cells:
            hex_poly = _hex_polygon(cell)
            hex_area_ea = _equal_area(hex_poly).area
            if hex_area_ea <= 0:
                continue
            try:
                intersection = polygon.intersection(hex_poly)
            except Exception:  # noqa: BLE001, S112 — topology errors from shapely are skipped, not raised
                continue
            if intersection.is_empty:
                continue
            intersection_area = _equal_area_geom_area(intersection)
            if intersection_area <= 0:
                continue
            weights.setdefault(cell, {})[zcta] = ZipHexWeight(
                hex_fraction=intersection_area / hex_area_ea,
                zcta_fraction=intersection_area / zcta_area,
            )
    return weights


def _equal_area_geom_area(geom) -> float:
    """Reproject any shapely geometry (a Polygon.intersection() result can be
    a GeometryCollection at a shared edge) to CA Albers and sum its area."""
    if geom.is_empty:
        return 0.0
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return _equal_area(geom).area if geom.geom_type == "Polygon" else sum(
            _equal_area(part).area for part in geom.geoms
        )
    # Points/lines from a boundary-only touch contribute no area.
    if hasattr(geom, "geoms"):
        return sum(
            _equal_area(part).area
            for part in geom.geoms
            if part.geom_type == "Polygon"
        )
    return 0.0


def aggregate_intensive(
    hex_weights: Mapping[str, ZipHexWeight], zcta_values: Mapping[str, float]
) -> float | None:
    """Area-weighted average of a level metric across a hex's contributing ZCTAs.

    Weighted by ``hex_fraction`` (share of the *hex* each ZCTA covers) and
    renormalized over only the ZCTAs that actually reported a value, so a
    ZCTA missing this period doesn't silently zero out its share of the hex
    (the "missing data fallback" acceptance criterion) — the remaining
    ZCTA(s) simply carry the full weight.
    """
    total_weight = 0.0
    total_value = 0.0
    for zcta, weight in hex_weights.items():
        value = zcta_values.get(zcta)
        if value is None:
            continue
        total_weight += weight.hex_fraction
        total_value += value * weight.hex_fraction
    if total_weight <= 0:
        return None
    return total_value / total_weight


def aggregate_extensive(
    hex_weights: Mapping[str, ZipHexWeight], zcta_values: Mapping[str, float]
) -> float | None:
    """Proportional allocation of a count metric onto one hex.

    Each contributing ZCTA's total is split across every hex it touches in
    proportion to ``zcta_fraction`` (share of the *ZCTA's* area in this hex),
    and a hex's value is the sum of its allocated shares. A ZCTA with no
    value this period contributes nothing (not a zero) — consistent with
    :func:`aggregate_intensive`.
    """
    total = 0.0
    any_contribution = False
    for zcta, weight in hex_weights.items():
        value = zcta_values.get(zcta)
        if value is None:
            continue
        total += value * weight.zcta_fraction
        any_contribution = True
    return total if any_contribution else None


def hexes_for_zctas(
    weights: Mapping[str, Mapping[str, ZipHexWeight]], zctas: Iterable[str]
) -> dict[str, dict[str, ZipHexWeight]]:
    """Filter a weight table down to hexes touched by a given set of ZCTAs."""
    wanted = set(zctas)
    return {
        cell: contributors
        for cell, contributors in weights.items()
        if wanted & contributors.keys()
    }
