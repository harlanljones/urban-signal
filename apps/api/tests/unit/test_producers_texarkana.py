"""Unit tests for the Texarkana, TX-AR leaf (US-282): spatial geometry containment.

Bi-state metro registered initially as SNAP-only (TX slice) pending verifiable
municipal permits endpoints on both sides. This test focuses on the spatial
registration contract: metro bbox sanity, division containment, and submarket
placement inside their declared division bbox.
"""

from src.spatial.cities.texarkana import (
    TEXARKANA_CITY_ID,
    TEXARKANA_DIVISION_BBOXES,
    TEXARKANA_DIVISIONS,
    TEXARKANA_METRO_BBOX,
    TEXARKANA_SUBMARKETS,
    REGISTRATION,
    is_in_texarkana_metro,
)


class TestTexarkanaSpatial:
    def test_metro_bbox_sanity(self):
        assert TEXARKANA_METRO_BBOX["min_lat"] < TEXARKANA_METRO_BBOX["max_lat"]
        assert TEXARKANA_METRO_BBOX["min_lng"] < TEXARKANA_METRO_BBOX["max_lng"]

    def test_is_in_metro_rejects_missing_coordinates(self):
        assert is_in_texarkana_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in TEXARKANA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= TEXARKANA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= TEXARKANA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= TEXARKANA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= TEXARKANA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in TEXARKANA_SUBMARKETS.items():
            bbox = TEXARKANA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in TEXARKANA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(TEXARKANA_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert TEXARKANA_CITY_ID == "texarkana"
        assert REGISTRATION.metro_bbox is TEXARKANA_METRO_BBOX
        assert REGISTRATION.submarkets is TEXARKANA_SUBMARKETS
        assert 4 <= len(TEXARKANA_DIVISIONS) <= 8
        assert 6 <= len(TEXARKANA_SUBMARKETS) <= 12

