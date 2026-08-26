"""Tests for the HMDA validation leaf helper (apps/api/src/spatial/hmda_metrics.py)."""

from src.spatial.hmda_metrics import (
    DEFAULT_ROLLUP_RESOLUTION,
    denial_rate,
    government_backed_share,
    investor_purchase_share,
    rollup_tract_to_h7,
    rollup_tract_to_h3,
)


def test_investor_purchase_share_basic():
    assert investor_purchase_share(30, 120) == 0.25


def test_investor_purchase_share_zero_total():
    assert investor_purchase_share(0, 0) == 0.0
    assert investor_purchase_share(5, 0) == 0.0


def test_denial_rate_basic():
    assert denial_rate(40, 200) == 0.20


def test_denial_rate_zero_decisions():
    assert denial_rate(0, 0) == 0.0


def test_government_backed_share_basic():
    assert government_backed_share(50, 200) == 0.25


def test_government_backed_share_zero_total():
    assert government_backed_share(10, 0) == 0.0


def test_rollup_tract_to_h3_assigns_and_sums():
    # Two tracts whose centroids land in the same res-7 cell should sum.
    tract_metrics = {
        "22071000100": {"purchase": 120, "investor_purchase": 30, "decided": 200, "denied": 40},
        "22071000200": {"purchase": 80, "investor_purchase": 10, "decided": 150, "denied": 25},
    }
    # Use a known New Orleans-area coordinate for both (tiny offset -> same res-7).
    tract_centroids = {
        "22071000100": (29.951, -90.075),
        "22071000200": (29.952, -90.076),
    }
    cells = rollup_tract_to_h3(tract_metrics, tract_centroids, resolution=7)
    assert len(cells) == 1
    cell = next(iter(cells.values()))
    assert cell["purchase"] == 200
    assert cell["investor_purchase"] == 40
    assert cell["decided"] == 350
    assert cell["denied"] == 65


def test_rollup_tract_to_h3_split_across_cells():
    tract_metrics = {
        "A": {"purchase": 100},
        "B": {"purchase": 50},
    }
    # Far-apart coordinates -> different res-7 cells.
    tract_centroids = {"A": (29.95, -90.07), "B": (40.71, -74.00)}
    cells = rollup_tract_to_h3(tract_metrics, tract_centroids, resolution=7)
    assert len(cells) == 2
    total = sum(c["purchase"] for c in cells.values())
    assert total == 150


def test_rollup_tract_to_h3_key_mismatch_raises():
    # Same length but different keys -> ValueError (validated before delegation).
    with __import__("pytest").raises(ValueError):
        rollup_tract_to_h3({"A": {"purchase": 1}}, {"B": (0.0, 0.0)})


def test_rollup_tract_to_h3_empty_centroids_mismatch_raises():
    # Length/key mismatch (metrics present, centroids empty) -> ValueError.
    with __import__("pytest").raises(ValueError):
        rollup_tract_to_h3({"A": {"purchase": 1}}, {})


def test_rollup_tract_to_h3_empty():
    assert rollup_tract_to_h3({}, {}) == {}


def test_default_rollup_resolution_is_res7():
    assert DEFAULT_ROLLUP_RESOLUTION == 7


def test_rollup_tract_to_h7_alias():
    # rollup_tract_to_h7 is the documented res-7 convenience alias.
    tract_metrics = {"A": {"purchase": 10}}
    tract_centroids = {"A": (29.95, -90.07)}
    cells = rollup_tract_to_h7(tract_metrics, tract_centroids)
    assert len(cells) == 1
    assert next(iter(cells.values()))["purchase"] == 10
