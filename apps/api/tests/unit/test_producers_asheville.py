"""Unit tests for the Asheville, NC leaf (US-291): spatial geometry containment.

Asheville is initially registered with verified geometry; feed registration
lands via the spine (city_registry). This test focuses on the spatial
registration contract: metro bbox sanity, division containment, and
submarket placement inside their declared division bbox.
"""

from src.spatial.cities.asheville import (
    ASHEVILLE_CITY_ID,
    ASHEVILLE_DIVISION_BBOXES,
    ASHEVILLE_DIVISIONS,
    ASHEVILLE_METRO_BBOX,
    ASHEVILLE_SUBMARKETS,
    REGISTRATION,
    is_in_asheville_metro,
)


class TestAshevilleSpatial:
    def test_metro_bbox_sanity(self):
        assert ASHEVILLE_METRO_BBOX["min_lat"] < ASHEVILLE_METRO_BBOX["max_lat"]
        assert ASHEVILLE_METRO_BBOX["min_lng"] < ASHEVILLE_METRO_BBOX["max_lng"]

    def test_is_in_asheville_metro_rejects_missing_coordinates(self):
        assert is_in_asheville_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in ASHEVILLE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= ASHEVILLE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= ASHEVILLE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= ASHEVILLE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= ASHEVILLE_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in ASHEVILLE_SUBMARKETS.items():
            bbox = ASHEVILLE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in ASHEVILLE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(ASHEVILLE_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert ASHEVILLE_CITY_ID == "asheville"
        assert REGISTRATION.metro_bbox is ASHEVILLE_METRO_BBOX
        assert REGISTRATION.submarkets is ASHEVILLE_SUBMARKETS
        assert 5 <= len(ASHEVILLE_DIVISIONS) <= 8
        assert 6 <= len(ASHEVILLE_SUBMARKETS) <= 12

