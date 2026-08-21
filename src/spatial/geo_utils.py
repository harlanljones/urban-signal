"""Geographic utility functions, NYC/Chicago/San Francisco borough & division bounding boxes, and PostGIS geometry formatting."""

from typing import Dict, List, Optional, Tuple
import h3
from shapely.geometry import Point, Polygon

from src.spatial.cities.chicago import (
    CHICAGO_DIVISION_BBOXES,
    CHICAGO_METRO_BBOX,
    is_in_chicago_metro,
)
from src.spatial.cities.san_francisco import (
    SAN_FRANCISCO_DIVISION_BBOXES,
    SAN_FRANCISCO_METRO_BBOX,
    SF_DIVISION_BBOXES,
    SF_METRO_BBOX,
    is_in_san_francisco_metro,
    is_in_sf_metro,
)
from src.spatial.city_registry import (
    NYC_BOROUGH_BBOXES,
    NYC_METRO_BBOX,
    REGISTRY,
    CityId,
    normalize_city,
)


def is_in_nyc_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the NYC Metropolitan bounds."""
    return (
        NYC_METRO_BBOX["min_lat"] <= lat <= NYC_METRO_BBOX["max_lat"]
        and NYC_METRO_BBOX["min_lng"] <= lng <= NYC_METRO_BBOX["max_lng"]
    )


def get_city_for_coordinate(lat: float, lng: float) -> Optional[str]:
    """Determine the city identifier ('nyc', 'chicago', or 'san_francisco') for a given coordinate."""
    for cid, reg in REGISTRY.items():
        bbox = reg.metro_bbox
        if (
            bbox["min_lat"] <= lat <= bbox["max_lat"]
            and bbox["min_lng"] <= lng <= bbox["max_lng"]
        ):
            return cid.value
    return None


def point_to_wkt(lat: float, lng: float) -> str:
    """Convert lat/lng to WKT POINT representation (Longitude Latitude in WGS84)."""
    return f"POINT({lng:.6f} {lat:.6f})"


def point_to_postgis_sql(lat: float, lng: float, srid: int = 4326) -> str:
    """Generate PostGIS ST_SetSRID(ST_MakePoint(...), srid) SQL snippet."""
    return f"ST_SetSRID(ST_MakePoint({lng:.6f}, {lat:.6f}), {srid})"


def h3_boundary_to_polygon_wkt(boundary_latlng: List[Tuple[float, float]]) -> str:
    """Convert H3 cell boundary [(lat, lng), ...] to PostGIS WKT POLYGON representation."""
    coords = [f"{lng:.6f} {lat:.6f}" for lat, lng in boundary_latlng]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return f"POLYGON(({', '.join(coords)}))"


def create_shapely_polygon(boundary_latlng: List[Tuple[float, float]]) -> Polygon:
    """Create a Shapely Polygon from (lat, lng) coordinates."""
    coords = [(lng, lat) for lat, lng in boundary_latlng]
    return Polygon(coords)


def get_borough_for_coordinate(lat: float, lng: float) -> Optional[str]:
    """Determine the NYC Borough name for a given lat/lng coordinate.

    Returns:
        One of 'MANHATTAN', 'BROOKLYN', 'QUEENS', 'BRONX', 'STATEN_ISLAND', or None if outside NYC.
    """
    return get_division_for_coordinate(lat, lng, city_id="nyc")


def get_division_for_coordinate(
    lat: float, lng: float, city_id: str = "nyc", max_distance_km: float = 25.0
) -> Optional[str]:
    """Determine the borough/division name for a coordinate in the specified city.

    Args:
        lat: Latitude
        lng: Longitude
        city_id: 'nyc', 'chicago', or 'san_francisco' / 'sf' (case-insensitive, default 'nyc')
        max_distance_km: Maximum distance in km to snap to a nearest submarket (default 25.0)

    Returns:
        NYC Borough name, Chicago Division name, or SF Division name, or None if outside city bounds.
    """
    norm_city = normalize_city(city_id)
    if not norm_city or norm_city not in REGISTRY:
        return None

    reg = REGISTRY[norm_city]
    bbox = reg.metro_bbox
    if not (bbox["min_lat"] <= lat <= bbox["max_lat"] and bbox["min_lng"] <= lng <= bbox["max_lng"]):
        return None

    from src.spatial.submarkets import find_nearest_submarket, get_submarket_by_name

    submarket_name, dist_km = find_nearest_submarket(
        lat, lng, city_id=norm_city.value, max_distance_km=max_distance_km
    )
    if submarket_name and dist_km <= max_distance_km:
        meta = get_submarket_by_name(submarket_name, city_id=norm_city.value)
        if meta:
            return meta.borough

    for division, d_bbox in reg.division_bboxes.items():
        if (
            d_bbox["min_lat"] <= lat <= d_bbox["max_lat"]
            and d_bbox["min_lng"] <= lng <= d_bbox["max_lng"]
        ):
            return division

    return None


def get_borough_for_h3(h3_index: str) -> Optional[str]:
    """Determine the NYC Borough name for an Uber H3 cell index.

    Returns:
        One of 'MANHATTAN', 'BROOKLYN', 'QUEENS', 'BRONX', 'STATEN_ISLAND', or None if invalid/outside NYC.
    """
    try:
        lat, lng = h3.cell_to_latlng(h3_index)
        return get_borough_for_coordinate(lat, lng)
    except Exception:
        return None


def get_division_for_h3(h3_index: str, city_id: str = "nyc") -> Optional[str]:
    """Determine the borough/division name for an Uber H3 cell index in the specified city.

    Returns:
        Division name or None if invalid/outside bounds.
    """
    try:
        lat, lng = h3.cell_to_latlng(h3_index)
        return get_division_for_coordinate(lat, lng, city_id=city_id)
    except Exception:
        return None
