"""End-to-end tests for the Bay Area ACS Dasymetric ETL pipeline (US-438)."""

import h3
from shapely.geometry import Point, Polygon

from src.spatial.acs_dasymetric_pipeline import (
    ACSDasymetricPipelineConfig,
    run_bay_area_acs_dasymetric_pipeline,
)


def test_run_bay_area_acs_dasymetric_pipeline_offline():
    lat, lng = 37.7749, -122.4194
    cell = h3.latlng_to_cell(lat, lng, 9)
    boundary = h3.cell_to_boundary(cell)
    hex_poly = Polygon([(b_lng, b_lat) for b_lat, b_lng in boundary])

    bg_fips = "060750101001"
    bg_poly = Point(hex_poly.centroid.x, hex_poly.centroid.y).buffer(0.0004)

    # Mock Census API rows
    mock_rows = [
        {
            "state": "06",
            "county": "075",
            "tract": "010100",
            "block group": "1",
            "B01003_001E": "750",
            "B01003_001M": "60",
            "B25002_001E": "300",
            "B25002_001M": "30",
            "B25002_002E": "270",
            "B25002_002M": "25",
            "B25002_003E": "30",
            "B25002_003M": "10",
            "B19013_001E": "135000",
            "B19013_001M": "7500",
            "B25077_001E": "1100000",
            "B25077_001M": "50000",
            "B25064_001E": "2800",
            "B25064_001M": "150",
            "B08301_001E": "400",
            "B08301_001M": "35",
            "B08301_021E": "180",
            "B08301_021M": "20",
        }
    ]

    # Geometries dict
    geoms = {bg_fips: bg_poly}

    # Buildings
    buildings = [Point(hex_poly.centroid.x, hex_poly.centroid.y) for _ in range(12)]

    cfg = ACSDasymetricPipelineConfig(vintage=2023, h3_resolution=9)
    records = run_bay_area_acs_dasymetric_pipeline(
        acs_rows=mock_rows,
        tiger_geometries=geoms,
        buildings=buildings,
        config=cfg,
    )

    assert len(records) == 1
    rec = records[0]
    assert rec.h3_index == cell
    assert rec.vintage == 2023
    assert rec.building_count == 12.0
    assert rec.county_fips == ["075"]

    # Verify extensive variable values
    pop_est, pop_moe = rec.features["total_population"]
    assert abs(pop_est - 750.0) < 1e-6
    assert abs(pop_moe - 60.0) < 1e-6

    # Verify intensive variable values
    inc_est, _ = rec.features["median_household_income"]
    assert abs(inc_est - 135000.0) < 1e-6

    val_est, _ = rec.features["median_home_value"]
    assert abs(val_est - 1100000.0) < 1e-6

    rent_est, _ = rec.features["median_gross_rent"]
    assert abs(rent_est - 2800.0) < 1e-6
