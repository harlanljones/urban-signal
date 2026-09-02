"""Unit tests for the Evansville, IN leaf (US-425): spatial geometry containment.

Evansville registers with the live-verified Building Commission Permits layer
(maps.evansvillegis.com BC/BUILDING_COMMISSION_PERMITS/MapServer/0, 154,760
rows, USER_Application_Recv_d epoch-ms watermark, WKID 102100 point geometry)
plus the USDA SNAP Retailer SLA slice for IN (snap_sla_spec("IN")). This test
focuses on the spatial registration contract: metro bbox sanity, division
containment, and submarket placement inside their declared division bbox.
"""

from src.spatial.cities.evansville import (
    EVANSVILLE_DIVISION_BBOXES,
    EVANSVILLE_DIVISIONS,
    EVANSVILLE_METRO_BBOX,
    EVANSVILLE_SUBMARKETS,
    REGISTRATION,
    is_in_evansville_metro,
)


class TestEvansvilleSpatial:
    def test_metro_bbox_sanity(self):
        assert EVANSVILLE_METRO_BBOX["min_lat"] < EVANSVILLE_METRO_BBOX["max_lat"]
        assert EVANSVILLE_METRO_BBOX["min_lng"] < EVANSVILLE_METRO_BBOX["max_lng"]

    def test_is_in_evansville_metro_rejects_missing_coordinates(self):
        assert is_in_evansville_metro(None, None) is False

    def test_downtown_evansville_inside_metro(self):
        assert is_in_evansville_metro(37.9716, -87.5711)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in EVANSVILLE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= EVANSVILLE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= EVANSVILLE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= EVANSVILLE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= EVANSVILLE_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in EVANSVILLE_SUBMARKETS.items():
            bbox = EVANSVILLE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in EVANSVILLE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(EVANSVILLE_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert REGISTRATION.metro_bbox is EVANSVILLE_METRO_BBOX
        assert REGISTRATION.submarkets is EVANSVILLE_SUBMARKETS
        assert 3 <= len(EVANSVILLE_SUBMARKETS) <= 6
