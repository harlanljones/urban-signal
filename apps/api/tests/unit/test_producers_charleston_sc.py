"""Unit tests for the Charleston, SC leaf (US-284): spatial geometry containment.

Charleston is registered initially as a SNAP-only metro (SC slice) pending a
verifiable public permits endpoint. This test focuses on the spatial
registration contract: metro bbox sanity, division containment, and
submarket placement inside their declared division bbox.
"""

from src.spatial.cities.charleston_sc import (
    CHARLESTON_SC_CITY_ID,
    CHARLESTON_SC_DIVISION_BBOXES,
    CHARLESTON_SC_DIVISIONS,
    CHARLESTON_SC_METRO_BBOX,
    CHARLESTON_SC_SUBMARKETS,
    REGISTRATION,
    is_in_charleston_sc_metro,
)


class TestCharlestonSpatial:
    def test_metro_bbox_sanity(self):
        assert CHARLESTON_SC_METRO_BBOX["min_lat"] < CHARLESTON_SC_METRO_BBOX["max_lat"]
        assert CHARLESTON_SC_METRO_BBOX["min_lng"] < CHARLESTON_SC_METRO_BBOX["max_lng"]

    def test_is_in_metro_rejects_missing_coordinates(self):
        assert is_in_charleston_sc_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in CHARLESTON_SC_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= CHARLESTON_SC_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= CHARLESTON_SC_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= CHARLESTON_SC_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= CHARLESTON_SC_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in CHARLESTON_SC_SUBMARKETS.items():
            bbox = CHARLESTON_SC_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in CHARLESTON_SC_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(CHARLESTON_SC_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert CHARLESTON_SC_CITY_ID == "charleston_sc"
        assert REGISTRATION.metro_bbox is CHARLESTON_SC_METRO_BBOX
        assert REGISTRATION.submarkets is CHARLESTON_SC_SUBMARKETS
        assert 4 <= len(CHARLESTON_SC_DIVISIONS) <= 8
        assert 6 <= len(CHARLESTON_SC_SUBMARKETS) <= 12

