"""Unit tests for the NTD transit / GTFS leaf helpers (Linear US-172)."""

import pytest

from src.spatial.ntd_transit import (
    _to_float,
    monthly_series_delta,
    parse_gtfs_stops,
    rollup_stops_to_h3,
)


def test_to_float_normalizes():
    assert _to_float(None) is None
    assert _to_float("") is None
    assert _to_float("0") == 0.0
    assert _to_float(42) == 42.0
    assert _to_float("9876543") == 9876543.0
    assert _to_float(98.5) == 98.5
    assert _to_float("abc") is None


def test_parse_gtfs_stops_returns_list():
    # Parse a real GTFS zip to verify stop extraction works
    import os
    import tempfile
    import zipfile
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        fname = f.name
        with zipfile.ZipFile(fname, "w") as zf:
            zf.writestr("stops.txt", "stop_id,stop_name,stop_lat,stop_lon\nS1,Test,42.3,-71.1\nS2,Test2,42.4,-71.2\n")
        try:
            stops = parse_gtfs_stops(fname)
            assert len(stops) == 2
            assert stops[0] == ("S1", 42.3, -71.1, "Test")
            assert stops[1] == ("S2", 42.4, -71.2, "Test2")
        finally:
            os.unlink(fname)


def test_parse_gtfs_stops_skips_bad_coords():
    import os
    import tempfile
    import zipfile
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        fname = f.name
        with zipfile.ZipFile(fname, "w") as zf:
            zf.writestr("stops.txt", "stop_id,stop_name,stop_lat,stop_lon\nS1,Good,42.3,-71.1\nS2,BadLng,42.3,not_a_number\n")
        try:
            stops = parse_gtfs_stops(fname)
            assert len(stops) == 1
            assert stops[0][0] == "S1"
        finally:
            os.unlink(fname)


def test_parse_gtfs_stops_missing_stops_txt():
    import os
    import tempfile
    import zipfile
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        fname = f.name
        with zipfile.ZipFile(fname, "w") as zf:
            zf.writestr("agency.txt", "agency_id,agency_name\n1,Test")
        try:
            stops = parse_gtfs_stops(fname)
            assert stops == []
        finally:
            os.unlink(fname)


def test_rollup_stops_to_h3_agg():
    # Boston-area stops: all in same res-9 cell
    stops = [("S1", 42.355, -71.065, "Stop A"), ("S2", 42.356, -71.066, "Stop B")]
    rolled = rollup_stops_to_h3(stops)
    assert len(rolled) >= 1
    # Should be a single cell with 2 stops
    total = sum(r["stop_count"] for r in rolled)
    assert total == 2
    for r in rolled:
        assert r["effective_h3"]
        assert r["h3_res7"]
        assert r["h3_res8"]
        assert r["h3_res9"]


def test_rollup_stops_to_h3_sparse_fallback():
    # A single stop in a sparse area -> falls back to res 7
    stops = [("S1", 42.355, -71.065, "Lone Stop")]
    rolled = rollup_stops_to_h3(stops, min_density=5)
    assert len(rolled) == 1
    # With 1 stop and min_density=5, dynamic_spatial_fallback returns res 7
    # (since 1 < 5, parent_8 used; 1 >= 1 threshold for res 8, actually)
    # Actually: dynamic_spatial_fallback: count=1 < 5 -> parent_8, count=1 >= 1 -> returns (parent_8, 8)
    assert rolled[0]["effective_resolution"] == 8


def test_monthly_series_delta_yoy():
    # 13 months so the 12-month-lag window is reachable for the last record.
    months = [f"2025-{m:02d}-01" for m in range(1, 13)] + ["2026-01-01"]
    records = [
        {"agency": "WMATA", "mode": "MB", "date": d, "upt": str(9000000 + i * 100000)}
        for i, d in enumerate(months)
    ]
    deltas = monthly_series_delta(records, lag_months=12)
    assert len(deltas) == 13
    # First 12 records have no 12-month-prior.
    for d in deltas[:12]:
        assert d["upt_delta_abs"] is None
    # Last record (2026-01 = 10,200,000) compares against 2025-01 = 9,000,000.
    assert deltas[12]["upt_delta_abs"] == 1200000.0
    assert deltas[12]["upt_delta_rel"] == pytest.approx(1200000.0 / 9000000.0)
    assert deltas[12]["latest"] is True
    assert deltas[11]["latest"] is False


def test_monthly_series_delta_skips_missing():
    records = [
        {"agency": "X", "mode": "MB", "date": "2026-01-01", "upt": "100"},
        {"agency": "X", "mode": "MB", "date": "2026-02-01", "upt": None},
        {"agency": "X", "mode": "MB", "date": "2026-03-01", "upt": "120"},
    ]
    deltas = monthly_series_delta(records, lag_months=1)
    # Feb 2026 skipped (None)
    assert len(deltas) == 2
    assert deltas[0]["date"] == "2026-01-01"
    assert deltas[0]["upt_delta_abs"] is None  # no prior
    assert deltas[1]["date"] == "2026-03-01"
    assert deltas[1]["upt_delta_abs"] == 20.0  # delta from 2026-01 (skipped Feb)


def test_monthly_series_delta_lag_must_be_positive():
    with pytest.raises(ValueError, match="lag_months must be >= 1"):
        monthly_series_delta([], lag_months=0)