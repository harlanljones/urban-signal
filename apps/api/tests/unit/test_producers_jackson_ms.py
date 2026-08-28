"""Unit tests for the Jackson, MS leaf (US-288): spatial geometry containment.

Jackson initially registers with SNAP-only SLA (MS slice) pending a verifiable
public permits/311 endpoint. This test focuses on the spatial registration
contract: metro bbox sanity, division containment, and submarket placement
inside their declared division bbox.
"""

from src.spatial.cities.jackson_ms import (
    JACKSON_MS_CITY_ID,
    JACKSON_MS_DIVISION_BBOXES,
    JACKSON_MS_DIVISIONS,
    JACKSON_MS_METRO_BBOX,
    JACKSON_MS_SUBMARKETS,
    REGISTRATION,
    is_in_jackson_ms_metro,
)


class TestJacksonMSSpatial:
    def test_metro_bbox_sanity(self):
        assert JACKSON_MS_METRO_BBOX["min_lat"] < JACKSON_MS_METRO_BBOX["max_lat"]
        assert JACKSON_MS_METRO_BBOX["min_lng"] < JACKSON_MS_METRO_BBOX["max_lng"]

    def test_is_in_metro_rejects_missing_coordinates(self):
        assert is_in_jackson_ms_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in JACKSON_MS_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= JACKSON_MS_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= JACKSON_MS_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= JACKSON_MS_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= JACKSON_MS_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in JACKSON_MS_SUBMARKETS.items():
            bbox = JACKSON_MS_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in JACKSON_MS_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(JACKSON_MS_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert JACKSON_MS_CITY_ID == "jackson_ms"
        assert REGISTRATION.metro_bbox is JACKSON_MS_METRO_BBOX
        assert REGISTRATION.submarkets is JACKSON_MS_SUBMARKETS
        assert 4 <= len(JACKSON_MS_DIVISIONS) <= 8
        assert 6 <= len(JACKSON_MS_SUBMARKETS) <= 12

