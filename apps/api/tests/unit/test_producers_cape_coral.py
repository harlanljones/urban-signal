"""Unit tests for the Cape Coral–Fort Myers leaf (US-285): spatial containment.

Focus: metro bbox sanity, division containment, and submarket placement inside
their declared division bbox. Dataset wiring is validated by the interlock
registry tests and end-to-end producers.
"""

from unittest.mock import patch

from src.spatial.cities.cape_coral import (
    CAPE_CORAL_CITY_ID,
    CAPE_CORAL_DIVISION_BBOXES,
    CAPE_CORAL_DIVISIONS,
    CAPE_CORAL_METRO_BBOX,
    CAPE_CORAL_SUBMARKETS,
    REGISTRATION,
    compose_permit_address,
    is_in_cape_coral_metro,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType


class TestCapeCoralSpatial:
    def test_metro_bbox_sanity(self):
        assert CAPE_CORAL_METRO_BBOX["min_lat"] < CAPE_CORAL_METRO_BBOX["max_lat"]
        assert CAPE_CORAL_METRO_BBOX["min_lng"] < CAPE_CORAL_METRO_BBOX["max_lng"]

    def test_is_in_cape_coral_metro_rejects_missing_coordinates(self):
        assert is_in_cape_coral_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in CAPE_CORAL_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= CAPE_CORAL_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= CAPE_CORAL_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= CAPE_CORAL_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= CAPE_CORAL_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in CAPE_CORAL_SUBMARKETS.items():
            bbox = CAPE_CORAL_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in CAPE_CORAL_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(CAPE_CORAL_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert CAPE_CORAL_CITY_ID == "cape_coral"
        assert REGISTRATION.metro_bbox is CAPE_CORAL_METRO_BBOX
        assert REGISTRATION.submarkets is CAPE_CORAL_SUBMARKETS
        assert 4 <= len(CAPE_CORAL_DIVISIONS) <= 8
        assert 6 <= len(CAPE_CORAL_SUBMARKETS) <= 12



# Live permit rows (2026-09-30, issuedate newest first under the future-date
# guard). Dates as ArcGISClient normalizes them; contractor columns left out.
_PERMIT_SW_15TH_PL = {
    "objectid": 740433,
    "Permit_Number": "BLDR26-000173",
    "permit_status": "Issued",
    "applydate": "2026-07-07T16:26:27.047000+00:00",
    "issuedate": "2026-09-29T15:00:58+00:00",
    "permitvalue": 93314,
    "permit_desc": "PP INSPECTIONS ONLY * RELEASED 09/22/2026 KLN * MULTITECH * New RV Garage",
    "Permit_Type": "Building Residential",
    "Work_Class": "Residential Construction",
    "Parcel": "274423C4043460500",
    "Addr1": "2025",
    "Predir": "SW",
    "Addr2": "15TH",
    "Addr3": "Parcel",
    "Street_Type": "PL",
    "Post_Dir": "",
    "Unit": "",
    "County": "Parcel",
    "City": "Cape Coral",
    "State": "FL",
    "Zip": "33991",
}

_PERMIT_BURNT_STORE_RD_N = {
    "objectid": 655930,
    "Permit_Number": "BLDC26-000364",
    "permit_status": "Issued",
    "issuedate": "2026-09-29T12:31:12+00:00",
    "permitvalue": 17500,
    "Permit_Type": "Building Commercial",
    "Work_Class": "Antenna/Tower",
    "Addr1": "3501",
    "Predir": "",
    "Addr2": "BURNT STORE",
    "Addr3": "Parcel",
    "Street_Type": "RD",
    "Post_Dir": "N",
    "City": "Cape Coral",
    "State": "FL",
    "Zip": "33993",
}


class TestCapeCoralPermitAddress:
    """``Addr1`` is only the house number. Until 2026-09-30 the field map read
    it alone as the address, the geocoder refused a four-digit query, and the
    feed published nothing (50 of 50 rows to the dead-letter queue)."""

    def test_composes_predirectional_street(self):
        assert compose_permit_address(_PERMIT_SW_15TH_PL) == "2025 SW 15TH PL, Cape Coral, FL 33991"

    def test_composes_postdirectional_street(self):
        assert compose_permit_address(_PERMIT_BURNT_STORE_RD_N) == "3501 BURNT STORE RD N, Cape Coral, FL 33993"

    def test_uses_the_row_city(self):
        row = _PERMIT_SW_15TH_PL | {"Addr1": "2800", "Predir": "NE", "Addr2": "PINE ISLAND",
                                    "Street_Type": "RD", "City": "NORTH FORT MYERS", "Zip": "33903"}
        assert compose_permit_address(row) == "2800 NE PINE ISLAND RD, NORTH FORT MYERS, FL 33903"

    def test_no_street_name_means_no_query(self):
        assert compose_permit_address(_PERMIT_SW_15TH_PL | {"Addr2": ""}) is None
        assert compose_permit_address({"Addr1": "2025"}) is None

    def test_registry_reads_the_composed_address_and_skips_future_dates(self):
        spec = REGISTRY[CityId.CAPE_CORAL].datasets[FeedType.PERMITS]
        assert spec.field_map["address_street"] == ["address_street", "Addr1"]
        assert spec.needs_geocode is True
        # 33 rows carry issue dates past 2026-10-01 (up to the year 2610).
        assert spec.where == "issuedate <= CURRENT_TIMESTAMP"

    def test_permit_parses_with_the_composed_address(self, monkeypatch):
        captured = []

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address))
            return (26.6187, -82.0037)

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            event = DOBPermitsProducer().parse_socrata_row(_PERMIT_SW_15TH_PL, city_id="cape_coral")
        assert event is not None
        assert event.job_id == "BLDR26-000173"
        assert event.address_street == "2025 SW 15TH PL, Cape Coral, FL 33991"
        assert event.zipcode == "33991"
        assert event.estimated_cost == 93314
        assert captured == [("cape_coral", "permits", "2025 SW 15TH PL, Cape Coral, FL 33991")]


def test_leaf_without_a_composer_leaves_the_row_alone():
    from src.producers.dob_permits_producer import _compose_permit_address

    assert _compose_permit_address("nyc", _PERMIT_SW_15TH_PL) is None
    assert _compose_permit_address("not_a_city", _PERMIT_SW_15TH_PL) is None
    assert _compose_permit_address("cape_coral", _PERMIT_SW_15TH_PL) == "2025 SW 15TH PL, Cape Coral, FL 33991"
