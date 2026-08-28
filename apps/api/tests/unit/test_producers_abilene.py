"""Unit tests for the Abilene, TX leaf (US-278): spatial geometry containment.

Abilene is registered initially as a SNAP-only metro (TX slice) pending a
verifiable public permits endpoint. This test focuses on the spatial
registration contract: metro bbox sanity, division containment, and
submarket placement inside their declared division bbox.
"""

from src.spatial.cities.abilene import (
    ABILENE_CITY_ID,
    ABILENE_DIVISION_BBOXES,
    ABILENE_DIVISIONS,
    ABILENE_METRO_BBOX,
    ABILENE_SUBMARKETS,
    REGISTRATION,
    is_in_abilene_metro,
)


class TestAbileneSpatial:
    def test_metro_bbox_sanity(self):
        assert ABILENE_METRO_BBOX["min_lat"] < ABILENE_METRO_BBOX["max_lat"]
        assert ABILENE_METRO_BBOX["min_lng"] < ABILENE_METRO_BBOX["max_lng"]

    def test_is_in_abilene_metro_rejects_missing_coordinates(self):
        assert is_in_abilene_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in ABILENE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= ABILENE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= ABILENE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= ABILENE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= ABILENE_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in ABILENE_SUBMARKETS.items():
            bbox = ABILENE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in ABILENE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(ABILENE_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert ABILENE_CITY_ID == "abilene"
        assert REGISTRATION.metro_bbox is ABILENE_METRO_BBOX
        assert REGISTRATION.submarkets is ABILENE_SUBMARKETS
        assert 4 <= len(ABILENE_DIVISIONS) <= 8
        assert 6 <= len(ABILENE_SUBMARKETS) <= 12

