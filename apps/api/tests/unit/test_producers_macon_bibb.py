"""Unit tests for the Macon-Bibb, GA leaf: spatial geometry containment.

This test focuses on the spatial registration contract: metro bbox sanity,
division containment, and submarket placement inside their declared division
bbox. Leaf tests run without spine registration.
"""

from src.spatial.cities.macon_bibb import (
    MACON_BIBB_CITY_ID,
    MACON_BIBB_DIVISION_BBOXES,
    MACON_BIBB_DIVISIONS,
    MACON_BIBB_METRO_BBOX,
    MACON_BIBB_SUBMARKETS,
    REGISTRATION,
    is_in_macon_bibb_metro,
)


class TestMaconBibbSpatial:
    def test_metro_bbox_sanity(self):
        assert MACON_BIBB_METRO_BBOX["min_lat"] < MACON_BIBB_METRO_BBOX["max_lat"]
        assert MACON_BIBB_METRO_BBOX["min_lng"] < MACON_BIBB_METRO_BBOX["max_lng"]

    def test_is_in_macon_bibb_metro_rejects_missing_coordinates(self):
        assert is_in_macon_bibb_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in MACON_BIBB_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= MACON_BIBB_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= MACON_BIBB_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= MACON_BIBB_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= MACON_BIBB_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in MACON_BIBB_SUBMARKETS.items():
            bbox = MACON_BIBB_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in MACON_BIBB_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(MACON_BIBB_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert MACON_BIBB_CITY_ID == "macon_bibb"
        assert REGISTRATION.metro_bbox is MACON_BIBB_METRO_BBOX
        assert REGISTRATION.submarkets is MACON_BIBB_SUBMARKETS
        assert 4 <= len(MACON_BIBB_DIVISIONS) <= 8
        assert 6 <= len(MACON_BIBB_SUBMARKETS) <= 12

