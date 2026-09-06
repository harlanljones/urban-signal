"""San Francisco Bay Area 9-county boundary and H3 res-5 tessellation (US-436).

Canonical boundary for the full 9-county Bay Area (FIPS 06001, 06013, 06041,
06055, 06075, 06081, 06085, 06095, 06097), dissolved from Census TIGER/Line
county shapefiles, plus the deterministic H3 res-5 polyfill covering all land
and bay-adjacent shoreline.

Water-body masking flags bay/ocean hexes (``is_water=True``) so downstream
scoring can exclude them; shoreline hexes whose centroid sits on land still
score. Everything here is offline and deterministic: the committed GeoJSON
assets under ``src/spatial/assets/`` are the only input, so the same asset
always yields the same hex set.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import h3
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

ASSET_DIR = Path(__file__).resolve().parent / "assets"
BOUNDARY_ASSET = ASSET_DIR / "sf_bay_area_9county.geojson"
COUNTIES_ASSET = ASSET_DIR / "sf_bay_area_counties.geojson"
WATER_ASSET = ASSET_DIR / "sf_bay_area_9county_water.geojson"

# Resolution of the parent viewport tiles published to the snapshot manifest.
RES5_PARENT_RESOLUTION = 5

# The 9 Bay Area counties: TIGER GEOID (state+county FIPS) -> county name.
BAY_AREA_COUNTY_FIPS: dict[str, str] = {
    "06001": "Alameda County",
    "06013": "Contra Costa County",
    "06041": "Marin County",
    "06055": "Napa County",
    "06075": "San Francisco County",
    "06081": "San Mateo County",
    "06085": "Santa Clara County",
    "06095": "Solano County",
    "06097": "Sonoma County",
}

# Full 9-county envelope, rounded outward from the dissolved boundary
# (lng -123.6325..-121.2082, lat 36.8930..38.8643). This intentionally differs
# from the US-436 ticket's approximate values on two sides: -123.53 would clip
# ~9 km of the Sonoma coast (use -123.64) and 38.86 would clip the Napa tip
# (use 38.87). The ticket's min_lat 36.89 and max_lng -121.20 already contain
# the boundary and are kept as-is.
BAY_AREA_METRO_BBOX: dict[str, float] = {
    "min_lat": 36.89,
    "max_lat": 38.87,
    "min_lng": -123.64,
    "max_lng": -121.20,
}

# Exact res-5 polyfill size of the committed dissolved asset (boundary-
# intersecting mode). Pinned so a silently regenerated asset fails loudly.
EXPECTED_RES5_COUNT = 78
# Hexes whose centroid falls in bay/ocean water (SF Bay system + Pacific).
EXPECTED_RES5_WATER_COUNT = 12


def _load_feature_geometries(path: Path) -> list[tuple[dict[str, Any], BaseGeometry]]:
    """Read a GeoJSON FeatureCollection asset into (properties, geometry) pairs."""
    with open(path, encoding="utf-8") as handle:
        collection = json.load(handle)
    return [
        (feature.get("properties", {}), shape(feature["geometry"]))
        for feature in collection["features"]
    ]


@lru_cache(maxsize=1)
def load_boundary_geometry() -> BaseGeometry:
    """Dissolved 9-county multipolygon (single feature in the boundary asset)."""
    features = _load_feature_geometries(BOUNDARY_ASSET)
    assert len(features) == 1, f"{BOUNDARY_ASSET} must hold exactly one dissolved feature"
    return features[0][1]


@lru_cache(maxsize=1)
def load_county_geometries() -> dict[str, BaseGeometry]:
    """Per-county polygons keyed by GEOID (coverage-test input)."""
    geometries = {
        props["GEOID"]: geometry
        for props, geometry in _load_feature_geometries(COUNTIES_ASSET)
    }
    missing = sorted(set(BAY_AREA_COUNTY_FIPS) - set(geometries))
    assert not missing, f"county asset missing FIPS entries: {missing}"
    return geometries


@lru_cache(maxsize=1)
def load_water_geometry() -> BaseGeometry:
    """Union of bay/estuary + ocean/sea water polygons clipped to the metro bbox."""
    from shapely.ops import unary_union

    geometries = [geometry for _, geometry in _load_feature_geometries(WATER_ASSET)]
    assert geometries, f"{WATER_ASSET} holds no water polygons"
    return unary_union(geometries)


def _to_latlng_polys(geometry: BaseGeometry) -> list[h3.LatLngPoly]:
    """Convert a (Multi)Polygon from lng/lat to H3 LatLngPoly in lat/lng order."""
    polys = [geometry] if geometry.geom_type == "Polygon" else list(geometry.geoms)
    out: list[h3.LatLngPoly] = []
    for poly in polys:
        outer = tuple((lat, lng) for lng, lat in poly.exterior.coords)
        holes = [tuple((lat, lng) for lng, lat in ring.coords) for ring in poly.interiors]
        out.append(h3.LatLngPoly(outer, *holes))
    return out


def res5_polyfill(geometry: BaseGeometry | None = None) -> list[str]:
    """Deterministic H3 res-5 polyfill of the 9-county boundary.

    Uses ``h3.polygon_to_cells`` in boundary-intersecting mode so shoreline
    parcels are covered. Iterates dissolved parts in asset order and returns a
    sorted cell list, so the same asset always yields the same hex set.
    """
    geometry = load_boundary_geometry() if geometry is None else geometry
    cells: set[str] = set()
    for part in _to_latlng_polys(geometry):
        cells.update(h3.polygon_to_cells(part, RES5_PARENT_RESOLUTION))
    return sorted(cells)


def classify_res5_tiles(
    cells: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Flag every res-5 tile with ``is_water`` (centroid-in-water rule).

    A tile whose centroid falls inside the bay/ocean mask is water and must be
    excluded from scoring; shoreline tiles whose centroid sits on land still
    score. Sorted by H3 index for determinism.
    """
    cells = res5_polyfill() if cells is None else sorted(cells)
    water = load_water_geometry()
    tiles: list[dict[str, Any]] = []
    for cell in cells:
        lat, lng = h3.cell_to_latlng(cell)
        tiles.append({"h3_index": cell, "is_water": bool(water.intersects(Point(lng, lat)))})
    return tiles


def scorable_res5_tiles() -> list[str]:
    """Res-5 tiles eligible for scoring (water tiles excluded), sorted."""
    return sorted(tile["h3_index"] for tile in classify_res5_tiles() if not tile["is_water"])


def county_res5_coverage() -> dict[str, list[str]]:
    """Res-5 polyfill per county FIPS (each a subset of the dissolved polyfill)."""
    counties = load_county_geometries()
    return {
        fips: res5_polyfill(counties[fips]) for fips in sorted(BAY_AREA_COUNTY_FIPS)
    }
