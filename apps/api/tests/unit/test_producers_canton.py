"""Unit tests for the Canton, OH leaf (US-425): spatial geometry containment.

Canton registers with the live-verified Stark County Auditor Property Sales
layer (scgisa.starkcountyohio.gov Auditor/StarkCountySales/MapServer/0,
300,909 rows, TRANSFER_DATE epoch-ms watermark, WKID 3857 polygon geometry)
plus the USDA SNAP Retailer SLA slice for OH (snap_sla_spec("OH")). This test
focuses on the spatial registration contract: metro bbox sanity, division
containment, and submarket placement inside their declared division bbox.
"""

from src.spatial.cities.canton import (
    CANTON_DIVISION_BBOXES,
    CANTON_DIVISIONS,
    CANTON_METRO_BBOX,
    CANTON_SUBMARKETS,
    REGISTRATION,
    is_in_canton_metro,
)


class TestCantonSpatial:
    def test_metro_bbox_sanity(self):
        assert CANTON_METRO_BBOX["min_lat"] < CANTON_METRO_BBOX["max_lat"]
        assert CANTON_METRO_BBOX["min_lng"] < CANTON_METRO_BBOX["max_lng"]

    def test_is_in_canton_metro_rejects_missing_coordinates(self):
        assert is_in_canton_metro(None, None) is False

    def test_downtown_canton_inside_metro(self):
        assert is_in_canton_metro(40.7989, -81.3784)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in CANTON_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= CANTON_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= CANTON_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= CANTON_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= CANTON_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in CANTON_SUBMARKETS.items():
            bbox = CANTON_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in CANTON_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(CANTON_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert REGISTRATION.metro_bbox is CANTON_METRO_BBOX
        assert REGISTRATION.submarkets is CANTON_SUBMARKETS
        assert 3 <= len(CANTON_SUBMARKETS) <= 6
