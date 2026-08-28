"""Unit tests for the Jonesboro, AR leaf (US-283): spatial geometry containment.

Jonesboro is initially registered with SNAP-only (AR slice) pending a verifiable
public city permits endpoint. This test focuses on the spatial registration
contract: metro bbox sanity, division containment, and submarket placement inside
their declared division bbox.
"""

from src.spatial.cities.jonesboro import (
    JONESBORO_CITY_ID,
    JONESBORO_DIVISION_BBOXES,
    JONESBORO_DIVISIONS,
    JONESBORO_METRO_BBOX,
    JONESBORO_SUBMARKETS,
    REGISTRATION,
    is_in_jonesboro_metro,
)


class TestJonesboroSpatial:
    def test_metro_bbox_sanity(self):
        assert JONESBORO_METRO_BBOX["min_lat"] < JONESBORO_METRO_BBOX["max_lat"]
        assert JONESBORO_METRO_BBOX["min_lng"] < JONESBORO_METRO_BBOX["max_lng"]

    def test_is_in_jonesboro_metro_rejects_missing_coordinates(self):
        assert is_in_jonesboro_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in JONESBORO_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= JONESBORO_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= JONESBORO_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= JONESBORO_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= JONESBORO_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in JONESBORO_SUBMARKETS.items():
            bbox = JONESBORO_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in JONESBORO_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(JONESBORO_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert JONESBORO_CITY_ID == "jonesboro"
        assert REGISTRATION.metro_bbox is JONESBORO_METRO_BBOX
        assert REGISTRATION.submarkets is JONESBORO_SUBMARKETS
        assert 4 <= len(JONESBORO_DIVISIONS) <= 8
        assert 6 <= len(JONESBORO_SUBMARKETS) <= 12

