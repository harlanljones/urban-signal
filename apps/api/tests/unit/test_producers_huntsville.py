"""Unit tests for the Huntsville, AL leaf (US-424): spatial geometry containment.

Huntsville registers with live-verified ArcGIS BuildingPermits feed
(maps.huntsvilleal.gov Licenses/BuildingPermits/MapServer/0, 18.4k rows,
Permit_Issue_DateTime date watermark, US-424 re-probe 2026-08-30) plus the
USDA SNAP Retailer SLA slice for AL (snap_sla_spec("AL")). This test focuses
on the spatial registration contract: metro bbox sanity, division
containment, and submarket placement inside their declared division bbox.
"""

from src.spatial.cities.huntsville import (
    HUNTSVILLE_CITY_ID,
    HUNTSVILLE_DIVISION_BBOXES,
    HUNTSVILLE_DIVISIONS,
    HUNTSVILLE_METRO_BBOX,
    HUNTSVILLE_SUBMARKETS,
    REGISTRATION,
    is_in_huntsville_metro,
)


class TestHuntsvilleSpatial:
    def test_metro_bbox_sanity(self):
        assert HUNTSVILLE_METRO_BBOX["min_lat"] < HUNTSVILLE_METRO_BBOX["max_lat"]
        assert HUNTSVILLE_METRO_BBOX["min_lng"] < HUNTSVILLE_METRO_BBOX["max_lng"]

    def test_is_in_huntsville_metro_rejects_missing_coordinates(self):
        assert is_in_huntsville_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in HUNTSVILLE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= HUNTSVILLE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= HUNTSVILLE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= HUNTSVILLE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= HUNTSVILLE_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in HUNTSVILLE_SUBMARKETS.items():
            bbox = HUNTSVILLE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in HUNTSVILLE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(HUNTSVILLE_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert HUNTSVILLE_CITY_ID == "huntsville"
        assert REGISTRATION.metro_bbox is HUNTSVILLE_METRO_BBOX
        assert REGISTRATION.submarkets is HUNTSVILLE_SUBMARKETS
        assert 4 <= len(HUNTSVILLE_DIVISIONS) <= 8
        assert 8 <= len(HUNTSVILLE_SUBMARKETS) <= 14
