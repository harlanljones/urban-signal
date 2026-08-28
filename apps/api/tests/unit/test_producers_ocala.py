"""Unit tests for the Ocala / Marion County, FL leaf (US-297).

Containment-only checks: metro bbox sanity, division containment, and
submarket placement inside their declared division bbox. Leaf tests run
without spine registration.
"""

from src.spatial.cities.ocala import (
    OCALA_DIVISION_BBOXES,
    OCALA_DIVISIONS,
    OCALA_METRO_BBOX,
    OCALA_SUBMARKETS,
    REGISTRATION,
    is_in_ocala_metro,
)


class TestOcalaSpatial:
    def test_metro_bbox_sanity(self):
        assert OCALA_METRO_BBOX["min_lat"] < OCALA_METRO_BBOX["max_lat"]
        assert OCALA_METRO_BBOX["min_lng"] < OCALA_METRO_BBOX["max_lng"]

    def test_is_in_ocala_metro_rejects_missing_coordinates(self):
        assert is_in_ocala_metro(None, None) is False

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

    def test_expected_registry_shape(self):
        # Single core division; five submarkets
        assert len(OCALA_DIVISIONS) == 1
        assert len(OCALA_SUBMARKETS) == 5
        # Registration object wires the live structures
        assert REGISTRATION.metro_bbox is OCALA_METRO_BBOX
        assert REGISTRATION.submarkets is OCALA_SUBMARKETS

