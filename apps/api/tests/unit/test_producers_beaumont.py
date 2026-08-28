"""Unit tests for the Beaumont, TX leaf (US-271).

Leaf-only geometry and containment checks. Producer feed specs are wired in
the spine; this suite exercises only the city module.
"""

from src.spatial.cities.beaumont import (
    BEAUMONT_DIVISION_BBOXES,
    BEAUMONT_DIVISIONS,
    BEAUMONT_METRO_BBOX,
    BEAUMONT_SUBMARKETS,
    is_in_beaumont_metro,
)


class TestBeaumontSpatial:
    def test_metro_bbox_is_sane(self):
        assert BEAUMONT_METRO_BBOX["min_lat"] < BEAUMONT_METRO_BBOX["max_lat"]
        assert BEAUMONT_METRO_BBOX["min_lng"] < BEAUMONT_METRO_BBOX["max_lng"]

    def test_is_in_beaumont_metro_accepts_core(self):
        # Downtown Beaumont
        assert is_in_beaumont_metro(30.0840, -94.1010)
        # West End
        assert is_in_beaumont_metro(30.1000, -94.1660)
        # South Park
        assert is_in_beaumont_metro(30.0410, -94.1220)

    def test_is_in_beaumont_metro_rejects_missing(self):
        assert is_in_beaumont_metro(None, None) is False

    def test_is_in_beaumont_metro_rejects_other_cities(self):
        assert is_in_beaumont_metro(40.7128, -74.0060) is False  # NYC
        assert is_in_beaumont_metro(30.2672, -97.7431) is False  # Austin

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in BEAUMONT_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= BEAUMONT_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= BEAUMONT_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= BEAUMONT_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= BEAUMONT_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in BEAUMONT_SUBMARKETS.items():
            bbox = BEAUMONT_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in BEAUMONT_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(BEAUMONT_SUBMARKETS)

    def test_submarkets_carry_the_beaumont_city_id(self):
        assert {m.city_id for m in BEAUMONT_SUBMARKETS.values()} == {"beaumont"}

