"""CoveragePlan invariants: k-ring equivalence (INV-6), one owner per cell (INV-9), honest labels."""

import json
from collections import Counter
from pathlib import Path

import h3
import pytest

from src.spatial import coverage_plan
from src.spatial.coverage_plan import plan_all, plan_region, roll_up

FIXTURE = Path(__file__).resolve().parents[4] / "scripts" / "autoresearch_coverage.json"


@pytest.fixture(scope="module")
def plans():
    return plan_all()


def test_every_metro_publishes_exactly_its_pinned_k_ring_cells(plans):
    """INV-6: planning must not change coverage — per-metro sets equal the pinned fixture."""
    pinned = json.loads(FIXTURE.read_text())
    assert set(plans) == set(pinned)
    for city, cells in pinned.items():
        assert {c.cell for c in plans[city].cells} == set(cells), city
    assert len({c.cell for p in plans.values() for c in p.cells}) == 53_799


def test_each_cell_has_exactly_one_owning_region_and_it_is_the_nearest(plans):
    """INV-9, seeded with the cells two metros publish today."""
    claimed: dict[str, list[tuple[float, str, bool]]] = {}
    for city, plan in plans.items():
        for c in plan.cells:
            claimed.setdefault(c.cell, []).append((c.distance_km, city, c.owned))
    contested = {cell: rows for cell, rows in claimed.items() if len(rows) > 1}
    assert len(contested) == 373  # measured from the pinned fixture at HX-B1
    for cell, rows in claimed.items():
        owners = [city for _, city, owned in rows if owned]
        assert len(owners) == 1, cell
        assert owners[0] == min((d, city) for d, city, _ in rows)[1], cell
    pairs = Counter(tuple(sorted(city for _, city, _ in rows)) for rows in contested.values())
    assert pairs[("oakland", "san_francisco")] == 123
    assert len(pairs) == 8


def test_counts_are_consistent_with_cells(plans):
    for plan in plans.values():
        assert plan.golden_count == len(plan.cells)
        assert plan.owned_count == sum(c.owned for c in plan.cells)
        assert plan.owned_count <= plan.golden_count
        assert [c.cell for c in plan.cells] == sorted(c.cell for c in plan.cells)
    assert sum(p.owned_count for p in plans.values()) == 53_799


def test_measured_cells_are_exactly_their_owner_submarket_center_cell(plans):
    from src.spatial.city_registry import REGISTRY, CityId

    for city, plan in plans.items():
        by_name = {m.name: m for m in REGISTRY[CityId(city)].submarkets.values()}
        for c in plan.cells:
            center_cell = h3.latlng_to_cell(by_name[c.owner].lat, by_name[c.owner].lng, 9)
            assert (c.label == "measured") == (c.cell == center_cell), (city, c)
        assert plan.measured_count >= 1, city


def test_no_cell_is_planned_beyond_the_interpolation_bound(plans):
    for plan in plans.values():
        assert all(c.distance_km <= coverage_plan.INTERPOLATION_BOUND_KM for c in plan.cells)


def test_in_anchor_follows_urban_geometry_not_distance(plans):
    nyc = plans["nyc"]
    times_square = h3.latlng_to_cell(40.758, -73.9855, 9)
    assert next(c for c in nyc.cells if c.cell == times_square).in_anchor
    # Small southern metros keep far more cells outside their anchors than a dense core metro.
    assert 0 < plans["bowling_green"].in_anchor_count < plans["bowling_green"].golden_count
    assert plans["nyc"].in_anchor_count / plans["nyc"].golden_count > 0.9


def test_plan_is_deterministic_and_hash_tracks_inputs():
    plan_all.cache_clear()
    first = plan_all()
    plan_all.cache_clear()
    again = plan_all()
    assert {k: v.plan_hash for k, v in first.items()} == {k: v.plan_hash for k, v in again.items()}
    assert len({p.plan_hash for p in first.values()}) == len(first)
    tighter = plan_all(max_dist_km=0.8)
    assert tighter["nyc"].golden_count < first["nyc"].golden_count
    assert tighter["nyc"].plan_hash != first["nyc"].plan_hash
    plan_all.cache_clear()


def test_region_lookup_and_roll_up(plans):
    plan = plan_region("metro/seattle")
    assert plan == plans["seattle"]
    parents = roll_up(plan, 7)
    assert parents and all(h3.get_resolution(p) == 7 for p in parents)
    assert {h3.cell_to_parent(c.cell, 7) for c in plan.cells} == set(parents)
    with pytest.raises(ValueError):
        roll_up(plan, 9)
    with pytest.raises(KeyError):
        plan_region("metro/not_a_city")
    with pytest.raises(KeyError):
        plan_region("anchor/00000")


def test_metro_less_anchors_returns_dg6_ordered_candidates():
    uncovered = coverage_plan.metro_less_anchors()
    assert len(uncovered) > 2000
    # Top anchor by land area in DG-6 ranking is Atlanta, GA
    assert uncovered[0].anchor_id == "03817"
    assert "Atlanta" in uncovered[0].name


def test_plan_anchor_region_emits_lodes_measured_and_null_lims():
    plan = coverage_plan.plan_anchor_region("03817")
    assert plan.region_id == "anchor/03817"
    assert plan.authority == "anchor"
    assert plan.detail_res == 9
    assert plan.golden_count == len(plan.cells)
    assert plan.golden_count > 60_000
    # US-408 honesty rule: no fabricated LIMS momentum owner outside metros
    assert all(c.owner is None for c in plan.cells)
    assert all(c.distance_km is None for c in plan.cells)
    assert all(c.label == "measured" for c in plan.cells)
    assert all(c.in_anchor is True for c in plan.cells)
    assert all(c.owned is True for c in plan.cells)
    assert coverage_plan.plan_region("anchor/03817") == plan
