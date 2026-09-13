"""Unit tests for the Overture density pipeline orchestration (US-443)."""

from __future__ import annotations

import h3
from shapely.geometry import Point, Polygon

from src.spatial.overture_client import OvertureBuildingRow, OverturePlaceRow
from src.spatial.overture_pipeline import (
    OverturePipelineConfig,
    run_commercial_churn_pipeline,
    run_overture_density_pipeline,
)

RESOLUTION = 9
SF_LAT, SF_LNG = 37.7749, -122.4194


def _hex_polygon(lat: float, lng: float) -> Polygon:
    cell = h3.latlng_to_cell(lat, lng, RESOLUTION)
    boundary = h3.cell_to_boundary(cell)
    hex_poly = Polygon([(b_lng, b_lat) for b_lat, b_lng in boundary])
    cx, cy = hex_poly.centroid.x, hex_poly.centroid.y
    coords = [(cx + (x - cx) * 0.3, cy + (y - cy) * 0.3) for x, y in hex_poly.exterior.coords]
    return Polygon(coords)


def test_run_overture_density_pipeline_with_prefetched_rows():
    poly = _hex_polygon(SF_LAT, SF_LNG)
    point = Point(poly.centroid.x, poly.centroid.y)

    buildings = [
        OvertureBuildingRow(
            id="b1", name="Loft", subtype="residential", building_class="apartment",
            height=15.0, num_floors=4, geometry=poly,
        ),
    ]
    places = [
        OverturePlaceRow(id="p1", name="Cafe", category_primary="coffee_shop", confidence=0.9, geometry=point),
    ]

    result = run_overture_density_pipeline(
        buildings=buildings,
        places=places,
        config=OverturePipelineConfig(release="2026-08-19.0", h3_resolution=RESOLUTION),
    )

    assert result.release == "2026-08-19.0"
    assert result.h3_resolution == RESOLUTION
    assert len(result.building_metrics) == 1
    assert result.building_metrics[0].building_count == 1
    assert len(result.poi_metrics) == 1
    assert result.poi_metrics[0].poi_density == 1
    assert len(result.building_footprints) == 1
    assert result.building_footprints[0] is poly
    assert "ODbL" in result.buildings_attribution
    assert "CDLA" in result.places_attribution


def test_run_overture_density_pipeline_empty_rows():
    result = run_overture_density_pipeline(buildings=[], places=[])
    assert result.building_metrics == []
    assert result.poi_metrics == []
    assert result.building_footprints == []


def test_run_commercial_churn_pipeline_delegates_to_id_diff():
    point = Point(SF_LNG, SF_LAT)
    release_a = [OverturePlaceRow(id="p1", name=None, category_primary=None, confidence=None, geometry=point)]
    release_b = [
        OverturePlaceRow(id="p1", name=None, category_primary=None, confidence=None, geometry=point),
        OverturePlaceRow(id="p2", name=None, category_primary=None, confidence=None, geometry=point),
    ]
    churn = run_commercial_churn_pipeline(release_a, release_b, resolution=RESOLUTION)
    cell = h3.latlng_to_cell(SF_LAT, SF_LNG, RESOLUTION)
    assert churn[cell] == 1
