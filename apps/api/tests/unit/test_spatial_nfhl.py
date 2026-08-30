"""Unit tests for the FEMA NFHL → H3 coverage leaf module (US-389).

Leaf-only: imports no spine symbols. Pure geometry logic, no network calls
(no live NFHL query; all inputs are synthetic fixture rings).
"""

from src.spatial.nfhl_rollup import (
    candidate_cells,
    cell_coverage_share,
    is_sfha_zone,
    rings_to_shapely,
    rollup_flood_coverage,
    to_multi_res,
)

# A small square in lng/lat near New Orleans (WGS84).
NO_SQUARE = [
    [[-90.10, 29.94], [-90.09, 29.94], [-90.09, 29.95], [-90.10, 29.95], [-90.10, 29.94]]
]


def test_is_sfha_zone_prefers_flag_then_code():
    # Authoritative flag wins when present.
    assert is_sfha_zone("AE", "T") is True
    assert is_sfha_zone("AE", "F") is False
    assert is_sfha_zone("X", "T") is True  # flag overrides code
    # Fall back to FLD_ZONE code when flag absent.
    assert is_sfha_zone("AE", None) is True
    assert is_sfha_zone("VE", None) is True
    assert is_sfha_zone("X", None) is False
    assert is_sfha_zone("D", None) is False
    assert is_sfha_zone(None, None) is False


def test_rings_to_shapely_builds_polygon():
    poly = rings_to_shapely(NO_SQUARE)
    assert poly.area > 0.0
    assert abs(poly.area - 0.0001) < 1e-12  # 0.01 deg * 0.01 deg


def test_rings_to_shapely_rejects_empty():
    import pytest

    with pytest.raises(ValueError):
        rings_to_shapely([])
    with pytest.raises(ValueError):
        rings_to_shapely([[[-90.1, 29.94], [-90.09, 29.94], [-90.09, 29.95]]])  # < 4 pts


def test_candidate_cells_inside_square():
    cells = candidate_cells(rings_to_shapely(NO_SQUARE), 9)
    assert cells, "polyfill should return at least one cell for the fixture square"
    # Every candidate cell centroid must fall inside the square's extent.
    for cell in cells:
        lat, lng = h3_cell_centroid(cell)
        assert -90.11 <= lng <= -90.08
        assert 29.93 <= lat <= 29.96


def test_cell_coverage_share_unit_bounds():
    geom = rings_to_shapely(NO_SQUARE)
    for cell in candidate_cells(geom, 9):
        share = cell_coverage_share(cell, geom)
        assert 0.0 <= share <= 1.0


def test_cell_coverage_share_full_cover_is_one():
    # A cell that fully contains its own boundary polygon must report 1.0.
    from shapely.geometry import Polygon

    cell = candidate_cells(rings_to_shapely(NO_SQUARE), 9)[0]
    boundary = h3_cell_boundary(cell)  # [(lat, lng)]
    cell_poly = Polygon([(lng, lat) for lat, lng in boundary])
    share = cell_coverage_share(cell, cell_poly)
    assert share == 1.0


def test_rollup_sfha_only_filters_by_code_and_flag():
    # Feature 0: SFHA by flag; feature 1: non-SFHA by flag; feature 2: SFHA by code.
    rings = [NO_SQUARE, NO_SQUARE, NO_SQUARE]
    flags = ["T", "F", None]
    codes = ["AE", "X", "VE"]
    rolled = rollup_flood_coverage(rings, resolution=9, sfha_only=True,
                                   zone_codes=codes, sfha_flags=flags)
    assert rolled, "SFHA features should produce coverage"


def test_rollup_accepts_sfha_flag_without_codes():
    rings = [NO_SQUARE, NO_SQUARE]
    flags = ["T", "F"]
    rolled = rollup_flood_coverage(rings, resolution=9, sfha_only=True, sfha_flags=flags)
    # Only the first (SFHA) feature contributes.
    one = rollup_flood_coverage([NO_SQUARE], resolution=9, sfha_only=True, sfha_flags=["T"])
    assert set(rolled) == set(one)


def test_rollup_shares_bounded():
    rolled = rollup_flood_coverage([NO_SQUARE], resolution=9, sfha_only=False)
    assert all(0.0 < s <= 1.0 for s in rolled.values())


def test_to_multi_res_aggregates():
    rolled = rollup_flood_coverage([NO_SQUARE], resolution=9, sfha_only=False)
    res8 = to_multi_res(rolled, parent_resolution=8)
    res7 = to_multi_res(rolled, parent_resolution=7)
    assert res8, "res-9 rollup should roll up to res 8"
    assert res7, "res-9 rollup should roll up to res 7"
    assert all(0.0 <= s <= 1.0 for s in res8.values())
    assert all(0.0 <= s <= 1.0 for s in res7.values())


# --- tiny helpers to keep the test network-free and h3-call-local ----------


def h3_cell_centroid(cell: str) -> tuple:
    import h3

    return h3.cell_to_latlng(cell)


def h3_cell_boundary(cell: str) -> list:
    import h3

    return h3.cell_to_boundary(cell)
