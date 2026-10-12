"""Per-region golden counts: coverage cannot change without an announced rebaseline (HX-B2)."""

import json
from pathlib import Path

import pytest

from src.spatial.coverage_plan import plan_all

GOLDEN = Path(__file__).resolve().parents[2] / "src/spatial/assets/region_golden_counts.json"
REBASELINE = "regenerate with scripts/measure_region_golden.py and commit the diff with the reason"


@pytest.fixture(scope="module")
def golden():
    return json.loads(GOLDEN.read_text())


def test_every_region_matches_its_pinned_counts(golden):
    plans = plan_all()
    assert set(plans) == {r.split("/", 1)[1] for r in golden["regions"]}, f"region set drifted; {REBASELINE}"
    for plan in plans.values():
        pinned = golden["regions"][plan.region_id]
        actual = {
            "golden": plan.golden_count,
            "owned": plan.owned_count,
            "measured": plan.measured_count,
            "in_anchor": plan.in_anchor_count,
        }
        assert actual == pinned, f"{plan.region_id} drifted from {pinned} to {actual}; {REBASELINE}"


def test_pinned_owned_total_is_the_published_unique_cell_count(golden):
    assert golden["total_owned"] == 53_799 == sum(r["owned"] for r in golden["regions"].values())


def test_a_registry_shrink_is_caught(golden, monkeypatch):
    """A tighter interpolation bound removes cells; the pin must notice, not shrink silently."""
    tighter = plan_all(max_dist_km=0.8)
    shrunk = [p.region_id for p in tighter.values() if p.golden_count != golden["regions"][p.region_id]["golden"]]
    assert "metro/nyc" in shrunk
    plan_all.cache_clear()
