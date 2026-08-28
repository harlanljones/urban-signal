"""Unit tests for the Waco, TX leaf (US-272): spatial geometry containment.

Waco is registered initially as a SNAP-only metro (TX slice) pending a
verifiable public permits endpoint. This test focuses on the spatial
registration contract: metro bbox sanity, division containment, and
submarket placement inside their declared division bbox.
"""

from src.spatial.cities.waco import (
    WACO_CITY_ID,
    WACO_DIVISION_BBOXES,
    WACO_DIVISIONS,
    WACO_METRO_BBOX,
    WACO_SUBMARKETS,
    REGISTRATION,
    is_in_waco_metro,
)


class TestWacoSpatial:
    def test_metro_bbox_sanity(self):
        assert WACO_METRO_BBOX["min_lat"] < WACO_METRO_BBOX["max_lat"]
        assert WACO_METRO_BBOX["min_lng"] < WACO_METRO_BBOX["max_lng"]

    def test_is_in_waco_metro_rejects_missing_coordinates(self):
        assert is_in_waco_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in WACO_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= WACO_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= WACO_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= WACO_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= WACO_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in WACO_SUBMARKETS.items():
            bbox = WACO_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in WACO_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(WACO_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert WACO_CITY_ID == "waco"
        assert REGISTRATION.metro_bbox is WACO_METRO_BBOX
        assert REGISTRATION.submarkets is WACO_SUBMARKETS
        assert 4 <= len(WACO_DIVISIONS) <= 8
        assert 6 <= len(WACO_SUBMARKETS) <= 12

