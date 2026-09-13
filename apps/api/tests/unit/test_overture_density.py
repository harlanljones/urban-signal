"""Unit tests for Overture per-hex building/POI density metrics (US-443)."""

from __future__ import annotations

import h3
import pytest
from shapely.geometry import Point, Polygon

from src.spatial.overture_client import OvertureBuildingRow, OverturePlaceRow
from src.spatial.overture_density import (
    building_footprint_geometries,
    classify_building_subtype,
    classify_poi_category,
    compute_building_metrics,
    compute_commercial_churn,
    compute_poi_metrics,
)

RESOLUTION = 9


def _hex_polygon(lat: float, lng: float) -> Polygon:
    cell = h3.latlng_to_cell(lat, lng, RESOLUTION)
    boundary = h3.cell_to_boundary(cell)
    return Polygon([(b_lng, b_lat) for b_lat, b_lng in boundary])


def _small_poly_in_hex(lat: float, lng: float, shrink: float = 0.3):
    """A polygon fully inside the target res-9 hex, shrunk toward its centroid."""
    hex_poly = _hex_polygon(lat, lng)
    cx, cy = hex_poly.centroid.x, hex_poly.centroid.y
    coords = [(cx + (x - cx) * shrink, cy + (y - cy) * shrink) for x, y in hex_poly.exterior.coords]
    return Polygon(coords)


SF_LAT, SF_LNG = 37.7749, -122.4194
OAK_LAT, OAK_LNG = 37.8044, -122.2712


def test_classify_building_subtype_buckets():
    assert classify_building_subtype("residential") == "residential"
    assert classify_building_subtype("commercial") == "commercial"
    assert classify_building_subtype("entertainment") == "commercial"
    assert classify_building_subtype("industrial") == "industrial"
    assert classify_building_subtype("agricultural") == "industrial"
    assert classify_building_subtype("civic") == "other"
    assert classify_building_subtype(None) == "other"
    assert classify_building_subtype("something_unmapped") == "other"


def test_classify_poi_category_buckets():
    assert classify_poi_category("coffee_shop") == "restaurants"
    assert classify_poi_category("fast_food_restaurant") == "restaurants"
    assert classify_poi_category("night_club") == "nightlife"
    assert classify_poi_category("hospital") == "healthcare"
    assert classify_poi_category("elementary_school") == "education"
    assert classify_poi_category("clothing_store") == "retail"
    assert classify_poi_category("hair_salon") == "services"
    assert classify_poi_category(None) == "other"
    assert classify_poi_category("totally_unknown_xyz") == "other"


def test_compute_building_metrics_single_hex():
    poly = _small_poly_in_hex(SF_LAT, SF_LNG)
    cell = h3.latlng_to_cell(poly.centroid.y, poly.centroid.x, RESOLUTION)

    rows = [
        OvertureBuildingRow(
            id="b1", name="A", subtype="residential", building_class="sfr", height=10.0,
            num_floors=2, geometry=poly,
        ),
        OvertureBuildingRow(
            id="b2", name="B", subtype="commercial", building_class="office", height=30.0,
            num_floors=8, geometry=poly,
        ),
        OvertureBuildingRow(
            id="b3", name=None, subtype=None, building_class=None, height=None,
            num_floors=None, geometry=poly,
        ),
    ]

    metrics = compute_building_metrics(rows, resolution=RESOLUTION)
    assert len(metrics) == 1
    m = metrics[0]
    assert m.h3_index == cell
    assert m.building_count == 3
    assert m.total_footprint_area_m2 > 0
    # avg_height only over the two buildings that reported a height
    assert m.avg_height_m == pytest.approx(20.0)
    assert m.class_mix["residential"] == pytest.approx(1 / 3)
    assert m.class_mix["commercial"] == pytest.approx(1 / 3)
    assert m.class_mix["other"] == pytest.approx(1 / 3)
    assert sum(m.class_mix.values()) == pytest.approx(1.0)
    # Single hex in the batch -> weight is 1.0 (all buildings live here)
    assert m.building_density_weight == pytest.approx(1.0)


def test_compute_building_metrics_weight_normalizes_across_hexes():
    poly_sf = _small_poly_in_hex(SF_LAT, SF_LNG)
    poly_oak = _small_poly_in_hex(OAK_LAT, OAK_LNG)

    rows = [
        OvertureBuildingRow(id="b1", name=None, subtype="residential", building_class=None,
                             height=None, num_floors=None, geometry=poly_sf),
        OvertureBuildingRow(id="b2", name=None, subtype="residential", building_class=None,
                             height=None, num_floors=None, geometry=poly_sf),
        OvertureBuildingRow(id="b3", name=None, subtype="residential", building_class=None,
                             height=None, num_floors=None, geometry=poly_sf),
        OvertureBuildingRow(id="b4", name=None, subtype="residential", building_class=None,
                             height=None, num_floors=None, geometry=poly_oak),
    ]

    metrics = {m.h3_index: m for m in compute_building_metrics(rows, resolution=RESOLUTION)}
    assert len(metrics) == 2
    weights = sorted(m.building_density_weight for m in metrics.values())
    assert weights == pytest.approx([0.25, 0.75])
    assert sum(m.building_density_weight for m in metrics.values()) == pytest.approx(1.0)


def test_compute_building_metrics_empty_input():
    assert compute_building_metrics([], resolution=RESOLUTION) == []


def test_compute_poi_metrics_category_mix():
    point = Point(SF_LNG, SF_LAT)
    rows = [
        OverturePlaceRow(id="p1", name="Cafe", category_primary="coffee_shop", confidence=0.9, geometry=point),
        OverturePlaceRow(id="p2", name="Bar", category_primary="night_club", confidence=0.8, geometry=point),
        OverturePlaceRow(id="p3", name="Shop", category_primary="clothing_store", confidence=0.7, geometry=point),
        OverturePlaceRow(id="p4", name="???", category_primary=None, confidence=None, geometry=point),
    ]

    metrics = compute_poi_metrics(rows, resolution=RESOLUTION)
    assert len(metrics) == 1
    m = metrics[0]
    assert m.poi_density == 4
    assert m.poi_category_mix["restaurants"] == pytest.approx(0.25)
    assert m.poi_category_mix["nightlife"] == pytest.approx(0.25)
    assert m.poi_category_mix["retail"] == pytest.approx(0.25)
    assert m.poi_category_mix["other"] == pytest.approx(0.25)
    assert sum(m.poi_category_mix.values()) == pytest.approx(1.0)


def test_compute_commercial_churn_appearances_and_disappearances():
    point = Point(SF_LNG, SF_LAT)
    release_a = [
        OverturePlaceRow(id="p1", name="Stays", category_primary="retail", confidence=0.9, geometry=point),
        OverturePlaceRow(id="p2", name="Closes", category_primary="retail", confidence=0.9, geometry=point),
    ]
    release_b = [
        OverturePlaceRow(id="p1", name="Stays", category_primary="retail", confidence=0.9, geometry=point),
        OverturePlaceRow(id="p3", name="Opens", category_primary="retail", confidence=0.9, geometry=point),
        OverturePlaceRow(id="p4", name="Also opens", category_primary="retail", confidence=0.9, geometry=point),
    ]

    churn = compute_commercial_churn(release_a, release_b, resolution=RESOLUTION)
    cell = h3.latlng_to_cell(SF_LAT, SF_LNG, RESOLUTION)
    # 2 appearances (p3, p4) minus 1 disappearance (p2) == +1
    assert churn[cell] == 1


def test_compute_commercial_churn_hex_only_in_one_release():
    point_a = Point(SF_LNG, SF_LAT)
    point_b = Point(OAK_LNG, OAK_LAT)
    release_a = [OverturePlaceRow(id="p1", name=None, category_primary=None, confidence=None, geometry=point_a)]
    release_b = [OverturePlaceRow(id="p2", name=None, category_primary=None, confidence=None, geometry=point_b)]

    churn = compute_commercial_churn(release_a, release_b, resolution=RESOLUTION)
    cell_a = h3.latlng_to_cell(SF_LAT, SF_LNG, RESOLUTION)
    cell_b = h3.latlng_to_cell(OAK_LAT, OAK_LNG, RESOLUTION)
    assert churn[cell_a] == -1  # p1 disappeared, hex only existed in A
    assert churn[cell_b] == 1  # p2 appeared, hex only existed in B


def test_building_footprint_geometries_filters_empty():
    poly = _small_poly_in_hex(SF_LAT, SF_LNG)
    rows = [
        OvertureBuildingRow(id="b1", name=None, subtype=None, building_class=None, height=None,
                             num_floors=None, geometry=poly),
    ]
    geoms = building_footprint_geometries(rows)
    assert len(geoms) == 1
    assert geoms[0] is poly
