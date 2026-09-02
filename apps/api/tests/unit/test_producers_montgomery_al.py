"""Unit tests for the Montgomery, AL leaf (US-424): spatial geometry containment.

Montgomery registers with live-verified ArcGIS Construction Permits
(All_Permit_viewlayer, services7.arcgis.com/xNUwUjOJqYE54USz, 87.7k rows,
IssuedDate date watermark) and the 311 Service Requests layer
(Received_311_Service_Request, gis.montgomeryal.gov, 228.6k rows,
Create_Date date watermark). This test focuses on the spatial registration
contract: metro bbox sanity, division containment, and submarket placement
inside their declared division bbox.
"""

from src.spatial.cities.montgomery_al import (
    MONTGOMERY_AL_CITY_ID,
    MONTGOMERY_AL_DIVISION_BBOXES,
    MONTGOMERY_AL_DIVISIONS,
    MONTGOMERY_AL_METRO_BBOX,
    MONTGOMERY_AL_SUBMARKETS,
    REGISTRATION,
    is_in_montgomery_al_metro,
)


class TestMontgomeryALSpatial:
    def test_metro_bbox_sanity(self):
        assert MONTGOMERY_AL_METRO_BBOX["min_lat"] < MONTGOMERY_AL_METRO_BBOX["max_lat"]
        assert MONTGOMERY_AL_METRO_BBOX["min_lng"] < MONTGOMERY_AL_METRO_BBOX["max_lng"]

    def test_is_in_montgomery_al_metro_rejects_missing_coordinates(self):
        assert is_in_montgomery_al_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in MONTGOMERY_AL_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= MONTGOMERY_AL_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= MONTGOMERY_AL_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= MONTGOMERY_AL_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= MONTGOMERY_AL_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in MONTGOMERY_AL_SUBMARKETS.items():
            bbox = MONTGOMERY_AL_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in MONTGOMERY_AL_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(MONTGOMERY_AL_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert MONTGOMERY_AL_CITY_ID == "montgomery_al"
        assert REGISTRATION.metro_bbox is MONTGOMERY_AL_METRO_BBOX
        assert REGISTRATION.submarkets is MONTGOMERY_AL_SUBMARKETS
        assert 4 <= len(MONTGOMERY_AL_DIVISIONS) <= 8
        assert 6 <= len(MONTGOMERY_AL_SUBMARKETS) <= 10