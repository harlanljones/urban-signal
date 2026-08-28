"""Unit tests for the Cape Coral–Fort Myers leaf (US-285): spatial containment.

Focus: metro bbox sanity, division containment, and submarket placement inside
their declared division bbox. Dataset wiring is validated by the interlock
registry tests and end-to-end producers.
"""

from src.spatial.cities.cape_coral import (
    CAPE_CORAL_CITY_ID,
    CAPE_CORAL_DIVISION_BBOXES,
    CAPE_CORAL_DIVISIONS,
    CAPE_CORAL_METRO_BBOX,
    CAPE_CORAL_SUBMARKETS,
    REGISTRATION,
    is_in_cape_coral_metro,
)


class TestCapeCoralSpatial:
    def test_metro_bbox_sanity(self):
        assert CAPE_CORAL_METRO_BBOX["min_lat"] < CAPE_CORAL_METRO_BBOX["max_lat"]
        assert CAPE_CORAL_METRO_BBOX["min_lng"] < CAPE_CORAL_METRO_BBOX["max_lng"]

    def test_is_in_cape_coral_metro_rejects_missing_coordinates(self):
        assert is_in_cape_coral_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in CAPE_CORAL_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= CAPE_CORAL_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= CAPE_CORAL_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= CAPE_CORAL_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= CAPE_CORAL_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in CAPE_CORAL_SUBMARKETS.items():
            bbox = CAPE_CORAL_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in CAPE_CORAL_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(CAPE_CORAL_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert CAPE_CORAL_CITY_ID == "cape_coral"
        assert REGISTRATION.metro_bbox is CAPE_CORAL_METRO_BBOX
        assert REGISTRATION.submarkets is CAPE_CORAL_SUBMARKETS
        assert 4 <= len(CAPE_CORAL_DIVISIONS) <= 8
        assert 6 <= len(CAPE_CORAL_SUBMARKETS) <= 12

