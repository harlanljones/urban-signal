"""Tests for src/spatial/bay_area_boundary.py — 9-county boundary + res-5 tessellation.

US-436: canonical TIGER/Line boundary, deterministic H3 res-5 polyfill with
water-body masking, and the expanded SF metro bbox. All inputs are committed
GeoJSON assets, so every test runs offline.
"""

from __future__ import annotations

import pytest

from src.spatial import bay_area_boundary as bab
from src.spatial.cities.san_francisco import SF_METRO_BBOX


@pytest.mark.interlock
class TestBoundaryAsset:
    def test_dissolved_multipolygon_is_valid(self):
        geom = bab.load_boundary_geometry()
        assert geom.geom_type == "MultiPolygon"
        assert not geom.is_empty
        assert geom.is_valid

    def test_all_nine_fips_present(self):
        counties = bab.load_county_geometries()
        assert sorted(counties) == sorted(bab.BAY_AREA_COUNTY_FIPS)
        for fips, geom in counties.items():
            assert not geom.is_empty, fips
            assert geom.is_valid, fips

    def test_metro_bbox_envelopes_the_boundary(self):
        min_lng, min_lat, max_lng, max_lat = bab.load_boundary_geometry().bounds
        bbox = bab.BAY_AREA_METRO_BBOX
        assert bbox["min_lat"] <= min_lat
        assert bbox["max_lat"] >= max_lat
        assert bbox["min_lng"] <= min_lng
        assert bbox["max_lng"] >= max_lng

    def test_leaf_metro_bbox_matches_canonical(self):
        """san_francisco.py must stay == BAY_AREA_METRO_BBOX (spine sync)."""
        assert SF_METRO_BBOX == bab.BAY_AREA_METRO_BBOX


@pytest.mark.interlock
class TestRes5Polyfill:
    def test_count_matches_expected(self):
        assert len(bab.res5_polyfill()) == bab.EXPECTED_RES5_COUNT == 78

    def test_deterministic_across_runs(self):
        first = bab.res5_polyfill()
        second = bab.res5_polyfill()
        assert first == second
        assert first == sorted(first)

    def test_every_county_has_coverage_and_nests_in_global(self):
        cells = set(bab.res5_polyfill())
        coverage = bab.county_res5_coverage()
        assert sorted(coverage) == sorted(bab.BAY_AREA_COUNTY_FIPS)
        for fips, county_cells in coverage.items():
            assert len(county_cells) >= 1, f"{fips} has no res-5 hexes"
            assert set(county_cells) <= cells, f"{fips} polyfill escapes the dissolved set"


@pytest.mark.interlock
class TestWaterMask:
    def test_water_count_matches_expected(self):
        tiles = bab.classify_res5_tiles()
        assert len(tiles) == bab.EXPECTED_RES5_COUNT
        wet = [t for t in tiles if t["is_water"]]
        assert len(wet) == bab.EXPECTED_RES5_WATER_COUNT == 12

    def test_central_bay_hex_is_water(self):
        """85283083fffffff centroids in central SF Bay (37.79, -122.345)."""
        by_index = {t["h3_index"]: t["is_water"] for t in bab.classify_res5_tiles()}
        assert by_index["85283083fffffff"] is True

    def test_scorable_tiles_exclude_water(self):
        tiles = bab.classify_res5_tiles()
        scorable = bab.scorable_res5_tiles()
        wet = {t["h3_index"] for t in tiles if t["is_water"]}
        dry = {t["h3_index"] for t in tiles if not t["is_water"]}
        assert scorable == sorted(dry)
        assert not (set(scorable) & wet)
        assert len(scorable) == bab.EXPECTED_RES5_COUNT - bab.EXPECTED_RES5_WATER_COUNT
        assert all(isinstance(t["is_water"], bool) for t in tiles)
