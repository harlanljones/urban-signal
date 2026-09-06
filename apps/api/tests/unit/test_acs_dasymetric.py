"""Unit tests for ACS Block-Group Dasymetric H3 Interpolation (US-438).

Covers:
- Full-coverage block group
- Split block group
- Water-only intersection (zero weight)
- Fallback to area-weighted interpolation when no buildings exist
- Intensive variable density-weighted averages
- High-MOE flagging (CV > 0.30)
- Vintage year tagging
- Determinism and idempotency
"""

import h3
from shapely.geometry import Point, Polygon

from src.spatial.acs_baseline import BGRow
from src.spatial.acs_dasymetric import (
    DasymetricInterpolator,
    compute_cv,
)


def _h3_hex_polygon(cell: str) -> Polygon:
    boundary = h3.cell_to_boundary(cell)
    return Polygon([(lng, lat) for lat, lng in boundary])


def test_full_coverage_block_group():
    """A block group that falls entirely within a single H3 res-9 cell."""
    # Pick an H3 cell in San Francisco and get its exact centroid
    lat, lng = 37.7749, -122.4194
    cell = h3.latlng_to_cell(lat, lng, 9)
    c_lat, c_lng = h3.cell_to_latlng(cell)
    hex_poly = _h3_hex_polygon(cell)

    # Create a small block group polygon inside this cell
    bg_poly = Point(c_lng, c_lat).buffer(0.0002)
    assert hex_poly.contains(bg_poly)

    bg_fips = "060750101001"
    row = BGRow(
        bg_fips12=bg_fips,
        values={
            "B01003_001E": (500.0, 50.0),  # total population
            "B25002_001E": (200.0, 20.0),  # total housing units
            "B19013_001E": (120000.0, 6000.0),  # median household income
        },
    )

    # 10 buildings located inside the block group
    buildings = [Point(c_lng, c_lat) for _ in range(10)]

    interpolator = DasymetricInterpolator(h3_resolution=9)
    records = interpolator.interpolate(
        bg_rows=[row],
        bg_geometries={bg_fips: bg_poly},
        buildings=buildings,
        vintage=2023,
    )

    assert len(records) == 1
    rec = records[0]
    assert rec.h3_index == cell
    assert rec.vintage == 2023
    assert rec.building_count == 10.0

    # 100% of population and housing units allocated to this cell
    pop_est, pop_moe = rec.features["total_population"]
    assert abs(pop_est - 500.0) < 1e-6
    assert abs(pop_moe - 50.0) < 1e-6

    units_est, units_moe = rec.features["housing_units_total"]
    assert abs(units_est - 200.0) < 1e-6
    assert abs(units_moe - 20.0) < 1e-6

    # Intensive median income transferred directly
    inc_est, _inc_moe = rec.features["median_household_income"]
    assert abs(inc_est - 120000.0) < 1e-6


def test_split_block_group():
    """A block group spanning two adjacent H3 cells with unequal building counts."""
    lat1, lng1 = 37.7749, -122.4194
    cell_a = h3.latlng_to_cell(lat1, lng1, 9)
    neighbors = list(h3.grid_ring(cell_a, 1))
    cell_b = neighbors[0]

    poly_a = _h3_hex_polygon(cell_a)
    poly_b = _h3_hex_polygon(cell_b)

    # Create a block group polygon that spans both cells
    pt_a = Point(poly_a.centroid.x, poly_a.centroid.y)
    pt_b = Point(poly_b.centroid.x, poly_b.centroid.y)
    bg_poly = pt_a.buffer(0.0002).union(pt_b.buffer(0.0002))

    bg_fips = "060750102001"
    row = BGRow(
        bg_fips12=bg_fips,
        values={
            "B01003_001E": (1000.0, 100.0),  # total pop = 1000, MOE = 100
            "B25002_001E": (400.0, 40.0),
            "B19013_001E": (90000.0, 5000.0),
        },
    )

    # Place 30 buildings in cell_a and 70 buildings in cell_b
    buildings_a = [Point(pt_a.x, pt_a.y) for _ in range(30)]
    buildings_b = [Point(pt_b.x, pt_b.y) for _ in range(70)]
    all_buildings = buildings_a + buildings_b

    interpolator = DasymetricInterpolator(h3_resolution=9)
    records = interpolator.interpolate(
        bg_rows=[row],
        bg_geometries={bg_fips: bg_poly},
        buildings=all_buildings,
        vintage=2023,
    )

    assert len(records) == 2
    rec_a = next(r for r in records if r.h3_index == cell_a)
    rec_b = next(r for r in records if r.h3_index == cell_b)

    # Cell A should get 30% (30/100) of population and units
    pop_a, moe_a = rec_a.features["total_population"]
    assert abs(pop_a - 300.0) < 1e-6
    assert abs(moe_a - 30.0) < 1e-6
    assert rec_a.building_count == 30.0

    # Cell B should get 70% (70/100) of population and units
    pop_b, moe_b = rec_b.features["total_population"]
    assert abs(pop_b - 700.0) < 1e-6
    assert abs(moe_b - 70.0) < 1e-6
    assert rec_b.building_count == 70.0

    # Total conservation: 300 + 700 == 1000
    assert abs((pop_a + pop_b) - 1000.0) < 1e-6


def test_water_only_intersection_zero_weight():
    """A coastal block group intersecting a land cell (with buildings) and a water cell (zero buildings).

    The dasymetric interpolation must assign 100% of population/units to the land cell
    and 0% to the water cell.
    """
    lat, lng = 37.8080, -122.4100  # North SF waterfront
    cell_land = h3.latlng_to_cell(lat, lng, 9)
    neighbors = list(h3.grid_ring(cell_land, 1))
    cell_water = neighbors[0]

    poly_land = _h3_hex_polygon(cell_land)
    poly_water = _h3_hex_polygon(cell_water)

    # BG polygon spans both cells
    pt_land = Point(poly_land.centroid.x, poly_land.centroid.y)
    pt_water = Point(poly_water.centroid.x, poly_water.centroid.y)
    bg_poly = pt_land.buffer(0.0002).union(pt_water.buffer(0.0002))

    bg_fips = "060750103001"
    row = BGRow(
        bg_fips12=bg_fips,
        values={
            "B01003_001E": (600.0, 60.0),
            "B25002_001E": (250.0, 25.0),
            "B19013_001E": (110000.0, 8000.0),
        },
    )

    # 50 buildings in the land cell, 0 buildings in the water cell
    buildings_land = [Point(pt_land.x, pt_land.y) for _ in range(50)]

    interpolator = DasymetricInterpolator(h3_resolution=9)
    records = interpolator.interpolate(
        bg_rows=[row],
        bg_geometries={bg_fips: bg_poly},
        buildings=buildings_land,
        vintage=2023,
    )

    rec_land = next(r for r in records if r.h3_index == cell_land)
    rec_water = next(r for r in records if r.h3_index == cell_water)

    # Land cell gets 100% of population (50/50)
    pop_land, moe_land = rec_land.features["total_population"]
    assert abs(pop_land - 600.0) < 1e-6
    assert abs(moe_land - 60.0) < 1e-6
    assert rec_land.building_count == 50.0

    # Water cell gets 0% of population (0/50)
    pop_water, moe_water = rec_water.features["total_population"]
    assert abs(pop_water - 0.0) < 1e-6
    assert abs(moe_water - 0.0) < 1e-6
    assert rec_water.building_count == 0.0


def test_zero_buildings_fallback_to_area_weighting():
    """When a block group has 0 buildings total, dasymetric falls back to area weighting."""
    lat, lng = 37.7749, -122.4194
    cell_a = h3.latlng_to_cell(lat, lng, 9)
    cell_b = next(iter(h3.grid_ring(cell_a, 1)))

    poly_a = _h3_hex_polygon(cell_a)
    poly_b = _h3_hex_polygon(cell_b)

    pt_a = Point(poly_a.centroid.x, poly_a.centroid.y)
    pt_b = Point(poly_b.centroid.x, poly_b.centroid.y)

    # Area in A is larger than area in B
    bg_poly = pt_a.buffer(0.0003).union(pt_b.buffer(0.00015))

    bg_fips = "060750104001"
    row = BGRow(
        bg_fips12=bg_fips,
        values={
            "B01003_001E": (300.0, 30.0),
        },
    )

    # Empty building index
    interpolator = DasymetricInterpolator(h3_resolution=9)
    records = interpolator.interpolate(
        bg_rows=[row],
        bg_geometries={bg_fips: bg_poly},
        buildings=[],
        vintage=2023,
    )

    assert len(records) == 2
    rec_a = next(r for r in records if r.h3_index == cell_a)
    rec_b = next(r for r in records if r.h3_index == cell_b)

    pop_a, _ = rec_a.features["total_population"]
    pop_b, _ = rec_b.features["total_population"]

    assert pop_a > 0.0 and pop_b > 0.0
    assert abs((pop_a + pop_b) - 300.0) < 1e-6
    # Larger area in A receives proportionally more population
    assert pop_a > pop_b


def test_intensive_variable_density_weighted_average():
    """Multiple block groups contributing to the same H3 cell with different incomes."""
    lat, lng = 37.7749, -122.4194
    cell = h3.latlng_to_cell(lat, lng, 9)
    c_lat, c_lng = h3.cell_to_latlng(cell)

    # Two distinct BGs intersecting this same cell
    bg1_poly = Point(c_lng - 0.0001, c_lat).buffer(0.0001)
    bg2_poly = Point(c_lng + 0.0001, c_lat).buffer(0.0001)

    bg1_fips = "060750105001"
    bg2_fips = "060750105002"

    row1 = BGRow(
        bg_fips12=bg1_fips,
        values={"B19013_001E": (60000.0, 3000.0), "B01003_001E": (100.0, 10.0)},
    )
    row2 = BGRow(
        bg_fips12=bg2_fips,
        values={"B19013_001E": (120000.0, 6000.0), "B01003_001E": (300.0, 30.0)},
    )

    # 20 buildings in BG1, 80 buildings in BG2 inside this cell
    b1 = [Point(bg1_poly.centroid.x, bg1_poly.centroid.y) for _ in range(20)]
    b2 = [Point(bg2_poly.centroid.x, bg2_poly.centroid.y) for _ in range(80)]

    interpolator = DasymetricInterpolator(h3_resolution=9)
    records = interpolator.interpolate(
        bg_rows=[row1, row2],
        bg_geometries={bg1_fips: bg1_poly, bg2_fips: bg2_poly},
        buildings=b1 + b2,
        vintage=2023,
    )

    assert len(records) == 1
    rec = records[0]
    # Weighted income: (60000*20 + 120000*80) / (20 + 80) = (1200000 + 9600000) / 100 = 108000
    inc_est, _inc_moe = rec.features["median_household_income"]
    assert abs(inc_est - 108000.0) < 1e-6


def test_high_moe_cv_flagging():
    """Cells where CV > 0.30 are flagged for multi-resolution fallback."""
    # Test compute_cv helper
    # Estimate = 100, MOE = 60 -> SE = 60 / 1.645 = 36.47 -> CV = 0.3647 > 0.30 (flagged)
    cv_high = compute_cv(estimate=100.0, moe=60.0)
    assert cv_high > 0.30

    # Estimate = 1000, MOE = 50 -> SE = 50 / 1.645 = 30.39 -> CV = 0.0304 <= 0.30 (not flagged)
    cv_low = compute_cv(estimate=1000.0, moe=50.0)
    assert cv_low < 0.30

    lat, lng = 37.7749, -122.4194
    cell = h3.latlng_to_cell(lat, lng, 9)
    c_lat, c_lng = h3.cell_to_latlng(cell)
    bg_poly = Point(c_lng, c_lat).buffer(0.0002)

    bg_fips = "060750106001"
    row = BGRow(
        bg_fips12=bg_fips,
        values={
            "B01003_001E": (100.0, 60.0),  # CV ~ 0.36 > 0.30 -> high MOE
            "B19013_001E": (50000.0, 2000.0),  # CV ~ 0.024 <= 0.30
        },
    )

    interpolator = DasymetricInterpolator(h3_resolution=9, cv_threshold=0.30)
    records = interpolator.interpolate(
        bg_rows=[row],
        bg_geometries={bg_fips: bg_poly},
        buildings=[Point(c_lng, c_lat)],
        vintage=2023,
    )

    assert len(records) == 1
    rec = records[0]
    assert rec.high_moe_flag is True
    assert rec.high_moe_variables["total_population"] is True
    assert rec.high_moe_variables["median_household_income"] is False


def test_idempotency_and_vintage_tag():
    """Re-runs produce identical output and tag vintage year."""
    lat, lng = 37.7749, -122.4194
    cell = h3.latlng_to_cell(lat, lng, 9)
    c_lat, c_lng = h3.cell_to_latlng(cell)
    bg_poly = Point(c_lng, c_lat).buffer(0.0002)

    bg_fips = "060750107001"
    row = BGRow(
        bg_fips12=bg_fips,
        values={"B01003_001E": (450.0, 45.0), "B19013_001E": (95000.0, 4000.0)},
    )
    buildings = [Point(c_lng, c_lat) for _ in range(5)]

    interpolator = DasymetricInterpolator(h3_resolution=9)
    run1 = interpolator.interpolate([row], {bg_fips: bg_poly}, buildings, vintage=2023)
    run2 = interpolator.interpolate([row], {bg_fips: bg_poly}, buildings, vintage=2023)

    assert len(run1) == len(run2) == 1
    assert run1[0].h3_index == run2[0].h3_index == cell
    assert run1[0].vintage == run2[0].vintage == 2023
    assert run1[0].features == run2[0].features
    assert run1[0].cv_scores == run2[0].cv_scores
    assert run1[0].high_moe_flag == run2[0].high_moe_flag
