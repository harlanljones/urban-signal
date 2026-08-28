"""Unit tests for the Alexandria, LA leaf (US-281): spatial geometry containment.

Alexandria registers initially as SNAP-only (LA slice) pending a verifiable
public permits endpoint. This test focuses on the spatial registration
contract: metro bbox sanity, division containment, and submarket placement
inside their declared division bbox.
"""

from src.spatial.cities.alexandria import (
    ALEXANDRIA_CITY_ID,
    ALEXANDRIA_DIVISION_BBOXES,
    ALEXANDRIA_DIVISIONS,
    ALEXANDRIA_METRO_BBOX,
    ALEXANDRIA_SUBMARKETS,
    REGISTRATION,
    is_in_alexandria_metro,
)


class TestAlexandriaSpatial:
    def test_metro_bbox_sanity(self):
        assert ALEXANDRIA_METRO_BBOX["min_lat"] < ALEXANDRIA_METRO_BBOX["max_lat"]
        assert ALEXANDRIA_METRO_BBOX["min_lng"] < ALEXANDRIA_METRO_BBOX["max_lng"]

    def test_is_in_metro_rejects_missing_coordinates(self):
        assert is_in_alexandria_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in ALEXANDRIA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= ALEXANDRIA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= ALEXANDRIA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= ALEXANDRIA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= ALEXANDRIA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in ALEXANDRIA_SUBMARKETS.items():
            bbox = ALEXANDRIA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in ALEXANDRIA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(ALEXANDRIA_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert ALEXANDRIA_CITY_ID == "alexandria"
        assert REGISTRATION.metro_bbox is ALEXANDRIA_METRO_BBOX
        assert REGISTRATION.submarkets is ALEXANDRIA_SUBMARKETS
        assert 4 <= len(ALEXANDRIA_DIVISIONS) <= 8
        assert 6 <= len(ALEXANDRIA_SUBMARKETS) <= 12

