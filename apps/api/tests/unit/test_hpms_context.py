"""Tests for the HPMS validation leaf helper (apps/api/src/spatial/hpms_context.py)."""

from src.spatial.hpms_context import (
    DEFAULT_CONTEXT_RESOLUTION,
    DEFAULT_ROLLUP_RESOLUTION,
    attribute_completeness,
    coverage_fraction,
    release_lag_years,
    rollup_segments_to_h3,
    segment_midpoint_to_h3,
)


def test_attribute_completeness_basic():
    records = [{"AADT": 12000}, {"AADT": None}, {"AADT": 0}, {"AADT": 8000}]
    # 2 of 4 have non-null, non-zero AADT
    assert attribute_completeness(records, "AADT") == 0.5


def test_attribute_completeness_empty():
    assert attribute_completeness([], "AADT") == 0.0


def test_attribute_completeness_string_zero():
    records = [{"AADT": "0"}, {"AADT": "5000"}, {"AADT": ""}]
    assert attribute_completeness(records, "AADT") == 1 / 3


def test_attribute_completeness_all_present():
    records = [{"F_SYSTEM": 1}, {"F_SYSTEM": 2}, {"F_SYSTEM": 3}]
    assert attribute_completeness(records, "F_SYSTEM") == 1.0


def test_release_lag_years_both():
    out = release_lag_years(reporting_year=2018, publication_year=2022, now_year=2026)
    assert out["publication_lag"] == 4
    assert out["age_vs_now"] == 8


def test_release_lag_years_public_only():
    # Memo: 2018 release vs. Sep 2022 page modification → lag 4, age vs 2026 = 8
    out = release_lag_years(reporting_year=2010, publication_year=2018, now_year=None)
    assert out["publication_lag"] == 8
    assert out["age_vs_now"] is None


def test_release_lag_years_none_publication():
    out = release_lag_years(reporting_year=2018, publication_year=None, now_year=2026)
    assert out["publication_lag"] is None
    assert out["age_vs_now"] == 8


def test_coverage_fraction_basic():
    metro = {"a", "b", "c", "d"}
    with_hpms = {"a", "b"}
    assert coverage_fraction(with_hpms, metro) == 0.5


def test_coverage_fraction_empty_metro():
    assert coverage_fraction({"a"}, set()) == 0.0


def test_coverage_fraction_no_overlap():
    assert coverage_fraction({"x"}, {"a", "b"}) == 0.0


def test_segment_midpoint_to_h3():
    # San Francisco midpoint should map deterministically; just check non-empty.
    cell = segment_midpoint_to_h3(37.7749, -122.4194, resolution=DEFAULT_ROLLUP_RESOLUTION)
    assert isinstance(cell, str) and len(cell) > 0
    # Same point at context res 5 is a parent of the res-7 cell.
    parent5 = segment_midpoint_to_h3(37.7749, -122.4194, resolution=DEFAULT_CONTEXT_RESOLUTION)
    assert isinstance(parent5, str) and len(parent5) > 0
    assert cell != parent5


def test_rollup_segments_to_h3_basic():
    segments = [
        {"mid_lat": 40.7128, "mid_lng": -74.006, "AADT": 15000, "THROUGH_LANES": 4},
        {"mid_lat": 40.7129, "mid_lng": -74.0061, "AADT": 12000, "THROUGH_LANES": 2},
        {"mid_lat": 41.8781, "mid_lng": -87.6298, "AADT": 20000, "THROUGH_LANES": 6},
    ]
    # First two are essentially co-located (NYC), third is Chicago.
    cells = rollup_segments_to_h3(segments, resolution=7)
    # At least 2 cells (NYC cluster + Chicago); allow 1 if h3 res 7 merges them — but NYC vs Chicago are far apart.
    assert len(cells) >= 2
    # Every cell should have segment_count and aadt_mean
    for bucket in cells.values():
        assert "segment_count" in bucket
        assert "aadt_mean" in bucket
    # Total segment count across cells should be 3.
    assert sum(int(v["segment_count"]) for v in cells.values()) == 3


def test_rollup_segments_skips_bad_rows():
    segments = [
        {"mid_lat": None, "mid_lng": -74.0, "AADT": 1000},  # bad lat
        {"mid_lat": 40.7, "mid_lng": -74.0, "AADT": 1000},  # good
    ]
    cells = rollup_segments_to_h3(segments, resolution=7)
    assert sum(int(v["segment_count"]) for v in cells.values()) == 1
