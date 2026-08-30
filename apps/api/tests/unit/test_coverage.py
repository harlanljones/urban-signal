"""Tests for src/spatial/coverage.py — density policy + LOD aggregation seam.

US-410: leaf module, no spine imports.
"""

from __future__ import annotations

import pytest

from src.spatial import coverage
from src.spatial.city_registry import REGISTRY, CityId
from src.spatial.h3_indexer import H3SpatialIndexer


class TestMetroCells:
    """metro_cells density policy — bounded k_ring."""

    def test_nyc_k1_returns_known_count(self):
        """k_ring=1, no bound: NYC 65 submarkets × ~7 cells each ≈ 455, deduped ~442."""
        cells = coverage.metro_cells("nyc", res=9, max_ring=1, max_dist_km=None)
        assert 420 <= len(cells) <= 480
        assert all(isinstance(c, str) for c in cells)
        # sorted, deterministic
        assert cells == sorted(cells)

    def test_nyc_k3_bounded_less_than_unbounded(self):
        """1.5 km bound prunes the k_ring=3 fringe."""
        bounded = coverage.metro_cells("nyc", res=9, max_ring=3, max_dist_km=1.5)
        unbounded = coverage.metro_cells("nyc", res=9, max_ring=3, max_dist_km=None)
        assert len(bounded) <= len(unbounded)
        assert len(bounded) > 0

    def test_nyc_k3_bounded_coverage_grows(self):
        """k_ring=3+bound yields more cells than k_ring=1."""
        k1 = coverage.metro_cells("nyc", res=9, max_ring=1, max_dist_km=None)
        k3b = coverage.metro_cells("nyc", res=9, max_ring=3, max_dist_km=1.5)
        assert len(k3b) > len(k1) * 2  # measured ~4.2× in US-409

    def test_unknown_city_raises(self):
        with pytest.raises(ValueError, match="Unknown city_id"):
            coverage.metro_cells("nonexistent_city")

    def test_res7_k1_returns_fewer_cells(self):
        """Coarser resolution means fewer cells for same coverage."""
        res9 = coverage.metro_cells("chicago", res=9, max_ring=1, max_dist_km=None)
        res7 = coverage.metro_cells("chicago", res=7, max_ring=1, max_dist_km=None)
        assert len(res7) < len(res9)

    def test_honesty_no_cell_outside_1_5km(self):
        """Every bounded cell is within 1.5 km of its own submarket center."""
        cells = coverage.metro_cells("nyc", res=9, max_ring=3, max_dist_km=1.5)
        # check each cell against its nearest submarket
        for cell in cells:
            assign = coverage.assign_cell(cell, "nyc", max_dist_km=1.5)
            assert assign is not None, f"cell {cell} has no assigned submarket"
            assert assign.distance_km <= 1.5 + 0.01, f"cell {cell} dist={assign.distance_km} > 1.5km"


class TestAssignCell:
    """Cell -> nearest-submarket resolution."""

    def test_nyc_center_cell_resolves_to_center(self):
        """A submarket's own center cell has source='center'."""
        reg = REGISTRY[CityId("nyc")]
        nyc_first = next(iter(reg.submarkets.values()))
        center = H3SpatialIndexer.latlng_to_h3(nyc_first.lat, nyc_first.lng, resolution=9)
        assign = coverage.assign_cell(center, "nyc")
        assert assign is not None
        assert assign.source == "center"
        assert assign.submarket == nyc_first.name
        assert assign.borough == nyc_first.borough

    def test_nyc_ring_cell_resolves_to_bounded(self):
        """A cell within 1.5 km of a submarket has source='bounded'."""
        cells = coverage.metro_cells("nyc", res=9, max_ring=3, max_dist_km=1.5)
        # pick a cell that is NOT a center cell
        reg = REGISTRY[CityId("nyc")]
        centers = {
            H3SpatialIndexer.latlng_to_h3(meta.lat, meta.lng, resolution=9)
            for meta in reg.submarkets.values()
        }
        ring_cells = [c for c in cells if c not in centers]
        assert len(ring_cells) > 0, "should have at least one ring cell"
        assign = coverage.assign_cell(ring_cells[0], "nyc", max_dist_km=1.5)
        assert assign is not None
        assert assign.source == "bounded"

    def test_outside_city_returns_none(self):
        """A bogus cell returns None."""
        # Use a cell in the middle of the Atlantic
        atlantic = H3SpatialIndexer.latlng_to_h3(0, -30, resolution=9)
        assign = coverage.assign_cell(atlantic, "nyc", max_dist_km=25.0)
        assert assign is None

    def test_chicago_assign(self):
        """Chicago submarket resolution works."""
        reg = REGISTRY[CityId("chicago")]
        meta = next(iter(reg.submarkets.values()))
        center = H3SpatialIndexer.latlng_to_h3(meta.lat, meta.lng, resolution=9)
        assign = coverage.assign_cell(center, "chicago")
        assert assign is not None
        assert assign.submarket == meta.name
        assert assign.source == "center"

    def test_source_center_is_its_own_center(self):
        """source='center' iff cell == submarket center at res9."""
        reg = REGISTRY[CityId("nyc")]
        for meta in list(reg.submarkets.values())[:3]:
            center = H3SpatialIndexer.latlng_to_h3(meta.lat, meta.lng, resolution=9)
            assign = coverage.assign_cell(center, "nyc")
            assert assign is not None
            assert assign.source == "center", f"{meta.name}: center cell should be 'center'"
            # declared lat/lng maps into this cell, so the cell centroid is
            # within one res9 cell (~0.17 km half-width) of the declared point.
            assert assign.distance_km < 1.0


class TestAggregateValues:
    """Metric aggregation for LOD — method A (average raw, then rank)."""

    def test_aggregate_res9_to_res8(self):
        """Aggregate raw values to res8 parent, average is correct."""
        # Use a small set of cells: res9 children of a known res8 cell
        res8_nyc = H3SpatialIndexer.latlng_to_h3(40.7580, -73.9855, resolution=8)
        children = coverage.parent_cells(res8_nyc, 9)
        assert len(children) == 7
        # synthetic values: 10, 20, 30, 40, 50, 60, 70
        vals = {c: i * 10 + 10 for i, c in enumerate(children)}
        result = coverage.aggregate_values(children, lambda c: vals[c], to_res=8)
        assert res8_nyc in result
        # average of 10..70 = 40
        assert result[res8_nyc] == pytest.approx(40.0, abs=0.01)

    def test_aggregate_skips_none(self):
        """Null values are skipped; average is over non-null only."""
        res8 = H3SpatialIndexer.latlng_to_h3(40.7580, -73.9855, resolution=8)
        children = coverage.parent_cells(res8, 9)
        vals = {c: (i * 10 + 10) if i % 2 == 0 else None for i, c in enumerate(children)}
        result = coverage.aggregate_values(children, lambda c: vals[c], to_res=8)
        assert res8 in result
        # non-null: 10, 30, 50, 70 — avg = 40
        assert result[res8] == pytest.approx(40.0, abs=0.01)

    def test_aggregate_all_none_is_empty(self):
        """When all values are None, the parent is absent from the result."""
        res8 = H3SpatialIndexer.latlng_to_h3(40.7580, -73.9855, resolution=8)
        children = coverage.parent_cells(res8, 9)
        result = coverage.aggregate_values(children, lambda c: None, to_res=8)
        assert res8 not in result

    def test_aggregate_res9_to_res7(self):
        """Aggregate to res7 — fewer parents, larger area."""
        cells = coverage.metro_cells("chicago", res=9, max_ring=1, max_dist_km=None)
        get_score = lambda c: 80.0  # uniform
        result = coverage.aggregate_values(cells, get_score, to_res=7)
        assert len(result) > 0
        for parent, avg in result.items():
            assert avg == pytest.approx(80.0, abs=0.01)
            assert isinstance(parent, str)
            assert len(parent) == 15  # H3 hex

    def test_aggregate_maintains_ordering(self):
        """Aggregate results are deterministic (same input → same output)."""
        cells = coverage.metro_cells("nyc", res=9, max_ring=1, max_dist_km=None)
        r1 = coverage.aggregate_values(cells, lambda c: 50.0, to_res=8)
        r2 = coverage.aggregate_values(cells, lambda c: 50.0, to_res=8)
        assert r1 == r2


class TestParentCells:
    """H3 parent/child helpers."""

    def test_res9_to_res8_has_7_children(self):
        cell = H3SpatialIndexer.latlng_to_h3(40.7580, -73.9855, resolution=8)
        children = coverage.parent_cells(cell, 9)
        assert len(children) == 7

    def test_res8_to_res7_has_7_children(self):
        cell = H3SpatialIndexer.latlng_to_h3(40.7580, -73.9855, resolution=7)
        children = coverage.parent_cells(cell, 8)
        assert len(children) == 7


class TestModulePolicy:
    """Module constants and docstring-encoded policy."""

    def test_lod_resolutions(self):
        assert coverage.METRO_LOD_RESOLUTIONS == (7, 8, 9)

    def test_default_max_ring(self):
        assert coverage.DEFAULT_MAX_RING == 3

    def test_default_max_dist_km(self):
        assert coverage.DEFAULT_MAX_DIST_KM == 1.5