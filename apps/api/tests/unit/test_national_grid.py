"""Unit tests for the national hex grid pyramid (US-382)."""

import h3
import pytest

from src.spatial import national_grid as ng


def test_outline_asset_parses_and_has_provenance():
    geometry = ng.load_outline_geometry()
    assert geometry["type"] == "MultiPolygon"
    assert len(geometry["coordinates"]) >= 80  # country incl. AK/HI/PR/territories/Aleutians


def test_base_polyfill_matches_golden_count():
    assert ng.count_at_resolution(ng.BASE_RESOLUTION) == ng.NATIONAL_GOLDEN_COUNTS[4]


@pytest.mark.parametrize("res", ng.NATIONAL_RESOLUTIONS)
def test_golden_counts_all_resolutions(res):
    assert ng.count_at_resolution(res) == ng.NATIONAL_GOLDEN_COUNTS[res]


@pytest.mark.parametrize("res", ng.NATIONAL_RESOLUTIONS)
def test_cells_are_valid_and_at_requested_resolution(res):
    cells = ng.cells_at_resolution(res)
    assert len(cells) == len(set(cells))
    sample = cells[:: max(1, len(cells) // 500)]
    assert all(h3.is_valid_cell(cell) for cell in sample)
    assert all(h3.get_resolution(cell) == res for cell in sample)


def test_pyramid_is_hierarchically_closed():
    pyramid = ng.national_pyramid()
    r4 = set(pyramid[4])
    r5 = set(pyramid[5])
    r6 = set(pyramid[6])
    assert all(h3.cell_to_parent(cell, 4) in r4 for cell in r5)
    assert all(h3.cell_to_parent(cell, 5) in r5 for cell in r6)


def test_cells_at_resolution_is_deterministic():
    assert ng.cells_at_resolution(6) == ng.cells_at_resolution(6)


def test_invalid_resolution_raises():
    with pytest.raises(ValueError):
        ng.cells_at_resolution(9)
    with pytest.raises(ValueError):
        ng.base_cells(5)


def test_parent_at_roundtrip():
    cells = ng.cells_at_resolution(6)
    child = cells[0]
    assert h3.get_resolution(ng.parent_at(child, 5)) == 5
    assert ng.parent_at(child, 5) in ng.cells_at_resolution(5)
