"""Unit tests for the Longview, TX leaf (US-276): spatial geometry containment.

Longview is registered initially as a SNAP-only metro (TX slice) pending a
verifiable public permits endpoint. This test focuses on the spatial
registration contract: metro bbox sanity, division containment, and
submarket placement inside their declared division bbox.
"""

from src.spatial.cities.longview import (
    LONGVIEW_CITY_ID,
    LONGVIEW_DIVISION_BBOXES,
    LONGVIEW_DIVISIONS,
    LONGVIEW_METRO_BBOX,
    LONGVIEW_SUBMARKETS,
    REGISTRATION,
    is_in_longview_metro,
)


class TestLongviewSpatial:
    def test_metro_bbox_sanity(self):
        assert LONGVIEW_METRO_BBOX["min_lat"] < LONGVIEW_METRO_BBOX["max_lat"]
        assert LONGVIEW_METRO_BBOX["min_lng"] < LONGVIEW_METRO_BBOX["max_lng"]

    def test_is_in_longview_metro_rejects_missing_coordinates(self):
        assert is_in_longview_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in LONGVIEW_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= LONGVIEW_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= LONGVIEW_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= LONGVIEW_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= LONGVIEW_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in LONGVIEW_SUBMARKETS.items():
            bbox = LONGVIEW_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in LONGVIEW_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(LONGVIEW_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert LONGVIEW_CITY_ID == "longview"
        assert REGISTRATION.metro_bbox is LONGVIEW_METRO_BBOX
        assert REGISTRATION.submarkets is LONGVIEW_SUBMARKETS
        assert 4 <= len(LONGVIEW_DIVISIONS) <= 8
        assert 6 <= len(LONGVIEW_SUBMARKETS) <= 12

