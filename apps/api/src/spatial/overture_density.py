"""Per-H3-res-9 Overture building stock and POI density metrics (US-443).

Pure, network-free aggregation: given already-fetched
``OvertureBuildingRow``/``OverturePlaceRow`` sequences (from
``src.spatial.overture_client``), assigns each feature to an H3 res-9 cell and
rolls up:

* **Building stock** — ``building_count``, ``total_footprint_area_m2``
  (geodesic footprint area via ``pyproj.Geod``), ``avg_height_m``,
  ``class_mix`` (residential/commercial/industrial/other fractions), and a
  ``building_density_weight`` normalized so the returned hex set's weights sum
  to 1.0 — a proper dasymetric weight distribution, not just a per-cell count.
* **POI density** — ``poi_density`` (POI count per hex, per the ticket's own
  definition), ``poi_category_mix`` (restaurants/retail/services/nightlife/
  healthcare/education/other fractions).
* **Commercial churn** — net POI change between two consecutive releases,
  computed from stable Overture (GERS) id set differences per hex rather than
  a naive count delta, per the prior research finding
  (``docs/research/overture-maps-evaluation.md``) that release-over-release
  count deltas over-state real openings/closures because of matcher churn.

Buildings are assigned to a hex by **polygon centroid** (the ticket allows
centroid or intersection); centroid assignment is O(1) per building and never
double-counts a building split across a hex boundary, at the cost of shifting
a small footprint area rounding at the hex edge.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

import h3
from pyproj import Geod

from src.spatial.overture_client import OvertureBuildingRow, OverturePlaceRow

logger = logging.getLogger(__name__)

DEFAULT_H3_RESOLUTION = 9

_GEOD = Geod(ellps="WGS84")

# Overture BuildingSubtype -> the ticket's four class_mix buckets.
BUILDING_CLASS_BUCKETS: dict[str, str] = {
    "residential": "residential",
    "commercial": "commercial",
    "entertainment": "commercial",
    "service": "commercial",
    "industrial": "industrial",
    "agricultural": "industrial",
    "civic": "other",
    "education": "other",
    "medical": "other",
    "military": "other",
    "outbuilding": "other",
    "religious": "other",
    "transportation": "other",
}
BUILDING_CLASS_MIX_KEYS: tuple[str, ...] = ("residential", "commercial", "industrial", "other")

# Overture places `categories.primary` keyword -> the ticket's six
# poi_category_mix buckets. Overture's basic-category taxonomy has hundreds of
# leaf values (see https://docs.overturemaps.org/guides/places/); this is a
# deliberately coarse substring classifier, checked in bucket order so the
# most specific match wins first.
POI_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "restaurants": ("restaurant", "cafe", "coffee", "bakery", "food_truck", "diner", "pizzeria", "fast_food"),
    "nightlife": ("bar", "night_club", "pub", "lounge", "brewery", "winery", "distillery"),
    "healthcare": ("hospital", "clinic", "pharmacy", "doctor", "dentist", "medical", "urgent_care", "health"),
    "education": ("school", "college", "university", "education", "tutor", "academy", "library"),
    "retail": ("shop", "store", "retail", "supermarket", "grocery", "market", "boutique", "mall"),
    "services": ("service", "salon", "spa", "bank", "insurance", "repair", "laundry", "agency", "office"),
}
POI_CATEGORY_MIX_KEYS: tuple[str, ...] = (
    "restaurants",
    "retail",
    "services",
    "nightlife",
    "healthcare",
    "education",
    "other",
)


@dataclass(frozen=True)
class H3BuildingMetrics:
    """Per-hex building stock rollup, res-9 by default."""

    h3_index: str
    building_count: int
    total_footprint_area_m2: float
    avg_height_m: float | None  # None when no building in the hex reports a height
    class_mix: dict[str, float]  # residential/commercial/industrial/other fractions, sum to 1.0
    building_density_weight: float  # normalized weight; sums to 1.0 across the returned batch


@dataclass(frozen=True)
class H3PoiMetrics:
    """Per-hex POI density rollup, res-9 by default."""

    h3_index: str
    poi_density: int  # total POI count in the hex (ticket's own definition)
    poi_category_mix: dict[str, float]  # fractions, sum to 1.0


def classify_building_subtype(subtype: str | None) -> str:
    """Bucket a raw BuildingSubtype into residential/commercial/industrial/other."""
    return BUILDING_CLASS_BUCKETS.get((subtype or "").lower(), "other")


def classify_poi_category(category_primary: str | None) -> str:
    """Bucket a raw Overture basic category into one of the six POI buckets, else 'other'."""
    category = (category_primary or "").lower()
    for bucket, keywords in POI_CATEGORY_KEYWORDS.items():
        if any(keyword in category for keyword in keywords):
            return bucket
    return "other"


def _building_centroid_cell(row: OvertureBuildingRow, resolution: int) -> str | None:
    if row.geometry is None or row.geometry.is_empty:
        return None
    centroid = row.geometry.centroid
    try:
        return h3.latlng_to_cell(centroid.y, centroid.x, resolution)
    except (ValueError, TypeError) as exc:
        logger.debug("Failed to index building %s to H3: %s", row.id, exc)
        return None


def _place_point_cell(row: OverturePlaceRow, resolution: int) -> str | None:
    if row.geometry is None or row.geometry.is_empty:
        return None
    point = row.geometry.centroid  # places are already points; centroid is a no-op identity
    try:
        return h3.latlng_to_cell(point.y, point.x, resolution)
    except (ValueError, TypeError) as exc:
        logger.debug("Failed to index place %s to H3: %s", row.id, exc)
        return None


def _footprint_area_m2(row: OvertureBuildingRow) -> float:
    if row.geometry is None or row.geometry.is_empty:
        return 0.0
    try:
        area, _perimeter = _GEOD.geometry_area_perimeter(row.geometry)
        return abs(area)
    except (ValueError, TypeError) as exc:
        logger.debug("Failed to compute footprint area for building %s: %s", row.id, exc)
        return 0.0


def assign_buildings_to_h3(
    buildings: Sequence[OvertureBuildingRow],
    resolution: int = DEFAULT_H3_RESOLUTION,
) -> dict[str, list[OvertureBuildingRow]]:
    """Group buildings by the H3 cell containing their footprint centroid."""
    grouped: dict[str, list[OvertureBuildingRow]] = {}
    for row in buildings:
        cell = _building_centroid_cell(row, resolution)
        if cell is None:
            continue
        grouped.setdefault(cell, []).append(row)
    return grouped


def assign_places_to_h3(
    places: Sequence[OverturePlaceRow],
    resolution: int = DEFAULT_H3_RESOLUTION,
) -> dict[str, list[OverturePlaceRow]]:
    """Group places by the H3 cell containing their point geometry."""
    grouped: dict[str, list[OverturePlaceRow]] = {}
    for row in places:
        cell = _place_point_cell(row, resolution)
        if cell is None:
            continue
        grouped.setdefault(cell, []).append(row)
    return grouped


def compute_building_metrics(
    buildings: Sequence[OvertureBuildingRow],
    resolution: int = DEFAULT_H3_RESOLUTION,
) -> list[H3BuildingMetrics]:
    """Compute per-hex building_count, footprint area, avg height, class_mix, and weight.

    ``building_density_weight`` is normalized so the weights across the
    returned list sum to 1.0 (a fraction-of-total-stock weight), which is the
    form ``acs_dasymetric.DasymetricInterpolator`` already consumes for
    proportional allocation.
    """
    grouped = assign_buildings_to_h3(buildings, resolution)
    total_buildings = sum(len(rows) for rows in grouped.values())

    records: list[H3BuildingMetrics] = []
    for cell in sorted(grouped):
        rows = grouped[cell]
        count = len(rows)
        total_area = sum(_footprint_area_m2(r) for r in rows)

        heights = [r.height for r in rows if r.height is not None and r.height > 0]
        avg_height = (sum(heights) / len(heights)) if heights else None

        bucket_counts = dict.fromkeys(BUILDING_CLASS_MIX_KEYS, 0)
        for r in rows:
            bucket_counts[classify_building_subtype(r.subtype)] += 1
        class_mix = (
            {k: v / count for k, v in bucket_counts.items()}
            if count > 0
            else dict.fromkeys(BUILDING_CLASS_MIX_KEYS, 0.0)
        )

        weight = (count / total_buildings) if total_buildings > 0 else 0.0

        records.append(
            H3BuildingMetrics(
                h3_index=cell,
                building_count=count,
                total_footprint_area_m2=total_area,
                avg_height_m=avg_height,
                class_mix=class_mix,
                building_density_weight=weight,
            )
        )
    return records


def compute_poi_metrics(
    places: Sequence[OverturePlaceRow],
    resolution: int = DEFAULT_H3_RESOLUTION,
) -> list[H3PoiMetrics]:
    """Compute per-hex POI count and category mix."""
    grouped = assign_places_to_h3(places, resolution)

    records: list[H3PoiMetrics] = []
    for cell in sorted(grouped):
        rows = grouped[cell]
        count = len(rows)
        bucket_counts = dict.fromkeys(POI_CATEGORY_MIX_KEYS, 0)
        for r in rows:
            bucket_counts[classify_poi_category(r.category_primary)] += 1
        category_mix = (
            {k: v / count for k, v in bucket_counts.items()}
            if count > 0
            else dict.fromkeys(POI_CATEGORY_MIX_KEYS, 0.0)
        )
        records.append(H3PoiMetrics(h3_index=cell, poi_density=count, poi_category_mix=category_mix))
    return records


def compute_commercial_churn(
    places_release_a: Sequence[OverturePlaceRow],
    places_release_b: Sequence[OverturePlaceRow],
    resolution: int = DEFAULT_H3_RESOLUTION,
) -> dict[str, int]:
    """Net per-hex POI change between two releases: new appearances minus disappearances.

    Uses stable Overture (GERS) place ids rather than a naive count delta:
    an id present in release B but not A is an appearance, one present in A
    but not B is a disappearance. This avoids the count-delta inflation the
    prior research documented (matcher re-runs churn ids without any real
    open/close event).
    """
    ids_a_by_cell: dict[str, set[str]] = {
        cell: {r.id for r in rows} for cell, rows in assign_places_to_h3(places_release_a, resolution).items()
    }
    ids_b_by_cell: dict[str, set[str]] = {
        cell: {r.id for r in rows} for cell, rows in assign_places_to_h3(places_release_b, resolution).items()
    }

    churn: dict[str, int] = {}
    for cell in sorted(set(ids_a_by_cell) | set(ids_b_by_cell)):
        ids_a = ids_a_by_cell.get(cell, set())
        ids_b = ids_b_by_cell.get(cell, set())
        appeared = ids_b - ids_a
        disappeared = ids_a - ids_b
        churn[cell] = len(appeared) - len(disappeared)
    return churn


def building_footprint_geometries(buildings: Sequence[OvertureBuildingRow]) -> list:
    """Raw footprint geometries, ready to pass as the ``buildings=`` dasymetric mask.

    This is the Ticket-3 (US-438) integration point: ``DasymetricInterpolator``
    / ``run_bay_area_acs_dasymetric_pipeline`` already accept a bare sequence of
    building geometries via ``BuildingIndex`` — Overture footprints need no
    extra adaptation to serve as that weighting mask.
    """
    return [row.geometry for row in buildings if row.geometry is not None and not row.geometry.is_empty]
