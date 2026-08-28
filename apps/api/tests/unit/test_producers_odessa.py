"""Unit tests for the Odessa, TX leaf (US-280): spatial geometry containment.

Odessa is registered initially as a SNAP-only metro (TX slice) pending a
verifiable public permits endpoint. This test focuses on the spatial
registration contract: metro bbox sanity, division containment, and
submarket placement inside their declared division bbox.
"""

from src.spatial.cities.odessa import (
    ODESSA_CITY_ID,
    ODESSA_DIVISION_BBOXES,
    ODESSA_DIVISIONS,
    ODESSA_METRO_BBOX,
    ODESSA_SUBMARKETS,
    REGISTRATION,
    is_in_odessa_metro,
)


class TestOdessaSpatial:
    def test_metro_bbox_sanity(self):
        assert ODESSA_METRO_BBOX["min_lat"] < ODESSA_METRO_BBOX["max_lat"]
        assert ODESSA_METRO_BBOX["min_lng"] < ODESSA_METRO_BBOX["max_lng"]

    def test_is_in_odessa_metro_rejects_missing_coordinates(self):
        assert is_in_odessa_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in ODESSA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= ODESSA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= ODESSA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= ODESSA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= ODESSA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in ODESSA_SUBMARKETS.items():
            bbox = ODESSA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in ODESSA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(ODESSA_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert ODESSA_CITY_ID == "odessa"
        assert REGISTRATION.metro_bbox is ODESSA_METRO_BBOX
        assert REGISTRATION.submarkets is ODESSA_SUBMARKETS
        assert 4 <= len(ODESSA_DIVISIONS) <= 8
        assert 6 <= len(ODESSA_SUBMARKETS) <= 12

