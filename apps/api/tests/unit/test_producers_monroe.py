"""Unit tests for the Monroe, LA leaf (US-277): spatial geometry containment.

Monroe is registered initially as a SNAP-only metro (LA slice) pending a
verifiable public permits endpoint. This test focuses on the spatial
registration contract: metro bbox sanity, division containment, and
submarket placement inside their declared division bbox.
"""

from src.spatial.cities.monroe import (
    MONROE_CITY_ID,
    MONROE_DIVISION_BBOXES,
    MONROE_DIVISIONS,
    MONROE_METRO_BBOX,
    MONROE_SUBMARKETS,
    REGISTRATION,
    is_in_monroe_metro,
)


class TestMonroeSpatial:
    def test_metro_bbox_sanity(self):
        assert MONROE_METRO_BBOX["min_lat"] < MONROE_METRO_BBOX["max_lat"]
        assert MONROE_METRO_BBOX["min_lng"] < MONROE_METRO_BBOX["max_lng"]

    def test_is_in_monroe_metro_rejects_missing_coordinates(self):
        assert is_in_monroe_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in MONROE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= MONROE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= MONROE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= MONROE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= MONROE_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in MONROE_SUBMARKETS.items():
            bbox = MONROE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in MONROE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(MONROE_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert MONROE_CITY_ID == "monroe"
        assert REGISTRATION.metro_bbox is MONROE_METRO_BBOX
        assert REGISTRATION.submarkets is MONROE_SUBMARKETS
        assert 4 <= len(MONROE_DIVISIONS) <= 8
        assert 6 <= len(MONROE_SUBMARKETS) <= 12

