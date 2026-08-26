"""Unit tests for the ZBP → H3 leaf projection helpers (Linear US-167)."""

import pytest

from src.spatial.zbp_signal import (
    normalize_zbp_flag,
    rollup_zbp_to_h3,
    zip_to_h3_record,
)


def test_normalize_zbp_flag_withheld_returns_none():
    for flag in ("D", "S", "N", "X", "V", "Z", "", None):
        assert normalize_zbp_flag(flag) is None


def test_normalize_zbp_flag_keeps_real_values():
    assert normalize_zbp_flag(0) == 0.0
    assert normalize_zbp_flag("42") == 42.0
    assert normalize_zbp_flag("1,234") == 1234.0
    assert normalize_zbp_flag(98.5) == 98.5


def test_zip_to_h3_record_hierarchy_and_fallback():
    # Manhattan-ish point; dense enough to stay at res 9 (establishments > threshold).
    rec = zip_to_h3_record("10001", estab=120, emp=850, payroll=4200, lat=40.7505, lng=-73.9965)
    assert rec["h3_res7"] and rec["h3_res8"] and rec["h3_res9"]
    assert rec["effective_resolution"] == 9
    assert rec["establishments"] == 120.0
    assert rec["employment"] == 850.0
    assert rec["payroll_annual"] == 4200.0


def test_zip_to_h3_record_sparse_falls_back():
    # Zero establishments -> falls back to res 7 (repo dynamic_spatial_fallback:
    # density < 1 has no coarser-than-8 parent to stay on, so it drops to res 7).
    rec_zero = zip_to_h3_record("00000", estab=0, emp=0, payroll=0, lat=40.7505, lng=-73.9965)
    assert rec_zero["effective_resolution"] == 7
    assert rec_zero["h3_res7"] == rec_zero["effective_h3"]
    # Low-but-present establishment count (1..4) stays at res 8.
    rec_low = zip_to_h3_record("10003", estab=3, emp=12, payroll=90, lat=40.7300, lng=-73.9900)
    assert rec_low["effective_resolution"] == 8
    assert rec_low["h3_res8"] == rec_low["effective_h3"]


def test_zip_to_h3_record_withheld_not_zero():
    rec = zip_to_h3_record("10002", estab=5, emp="D", payroll="S", lat=40.7100, lng=-73.9800)
    assert rec["establishments"] == 5.0
    assert rec["employment"] is None
    assert rec["payroll_annual"] is None


def test_rollup_aggregates_and_tracks_suppression():
    records = [
        zip_to_h3_record("10001", estab=120, emp=850, payroll=4200, lat=40.7505, lng=-73.9965),
        zip_to_h3_record("10002", estab=5, emp="D", payroll=10, lat=40.7100, lng=-73.9800),
    ]
    rolled = rollup_zbp_to_h3(records)
    assert len(rolled) == 2  # two distinct effective cells here
    by_cell = {r["effective_h3"]: r for r in rolled}
    cell_10002 = by_cell[records[1]["effective_h3"]]
    assert cell_10002["establishments"] == 5.0
    assert cell_10002["employment"] == 0.0
    assert cell_10002["suppressed_emp"] == 1
    assert cell_10002["suppressed_payroll"] == 0
