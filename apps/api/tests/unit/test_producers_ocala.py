"""Unit tests for the Ocala, FL leaf (US-297).

Leaf-only geometry and containment checks. Producer feed specs are wired in
the spine; this suite exercises only the city module.
"""

from src.spatial.cities.ocala import (
    OCALA_DIVISION_BBOXES,
    OCALA_DIVISIONS,
    OCALA_METRO_BBOX,
    OCALA_SUBMARKETS,
    is_in_ocala_metro,
)


class TestOcalaSpatial:
    def test_metro_bbox_is_sane(self):
        assert OCALA_METRO_BBOX["min_lat"] < OCALA_METRO_BBOX["max_lat"]
        assert OCALA_METRO_BBOX["min_lng"] < OCALA_METRO_BBOX["max_lng"]

    def test_is_in_ocala_metro_accepts_core(self):
        # Downtown Ocala
        assert is_in_ocala_metro(29.1872, -82.1401)
        # Silver Springs
        assert is_in_ocala_metro(29.2160, -82.0590)
        # Southeast Ocala
        assert is_in_ocala_metro(29.1500, -82.1200)

    def test_is_in_ocala_metro_rejects_missing(self):
        assert is_in_ocala_metro(None, None) is False

    def test_is_in_ocala_metro_rejects_other_cities(self):
        assert is_in_ocala_metro(40.7128, -74.0060) is False  # NYC
        assert is_in_ocala_metro(28.5383, -81.3792) is False  # Orlando

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in OCALA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= OCALA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= OCALA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= OCALA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= OCALA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in OCALA_SUBMARKETS.items():
            bbox = OCALA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in OCALA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(OCALA_SUBMARKETS)

    def test_submarkets_carry_the_ocala_city_id(self):
        assert {m.city_id for m in OCALA_SUBMARKETS.values()} == {"ocala"}

