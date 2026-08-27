"""Contract tests for Fort Worth's ArcGIS PERMITS feed.

Fort Worth's "CFW Development Permits Points" layer returns point geometry in
WGS84, so the shared ArcGIS client's ``SHAPE__Y``/``SHAPE__X`` slots carry real
degrees and are used directly for H3 indexing (no address geocode required). The
ADR-0004 geocoder is retained only as a fallback for geometry-less rows.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.producers.field_maps_fort_worth import FIELD_MAP as FORT_WORTH_PERMITS_FIELD_MAP
from src.spatial.cities.fort_worth import (
    FORT_WORTH_DIVISION_BBOXES,
    FORT_WORTH_DIVISIONS,
    FORT_WORTH_METRO_BBOX,
    FORT_WORTH_SUBMARKETS,
    is_in_fort_worth_metro,
)
from src.producers.field_maps import first_mapped
from src.spatial.city_registry import FeedType


# --- Geometry self-consistency (no spine registration required) --------------


def test_fort_worth_geometry_is_self_consistent():
    assert is_in_fort_worth_metro(32.7550, -97.3300)
    assert not is_in_fort_worth_metro(40.7128, -74.0060)
    assert not is_in_fort_worth_metro(None, None)
    for name, bbox in FORT_WORTH_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= FORT_WORTH_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= FORT_WORTH_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= FORT_WORTH_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= FORT_WORTH_METRO_BBOX["max_lng"], name
    claimed = [name for division in FORT_WORTH_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(FORT_WORTH_SUBMARKETS)
    assert {m.city_id for m in FORT_WORTH_SUBMARKETS.values()} == {"fort_worth"}


# --- field_map round-trips through first_mapped -------------------------------


def test_fort_worth_field_map_resolves_spellings():
    row = {
        "Unique_ID": "24TMP-037244",
        "Permit_No": "24TMP-037244",
        "Permit_Type": "Design Review",
        "JobValue": "2200",
        "Current_Status": "Pending",
        "File_Date": "4/28/2024, 12:00 AM",
        "Zip_Code": "76104",
        "SHAPE__X": -97.34097226394697,  # WGS84 longitude (real degree)
        "SHAPE__Y": 32.72750774164953,   # WGS84 latitude (real degree)
    }
    assert first_mapped(row, FORT_WORTH_PERMITS_FIELD_MAP, "job_id") == "24TMP-037244"
    assert first_mapped(row, FORT_WORTH_PERMITS_FIELD_MAP, "job_type") == "Design Review"
    assert first_mapped(row, FORT_WORTH_PERMITS_FIELD_MAP, "cost") == "2200"
    assert first_mapped(row, FORT_WORTH_PERMITS_FIELD_MAP, "status") == "Pending"
    assert first_mapped(row, FORT_WORTH_PERMITS_FIELD_MAP, "latitude") == 32.72750774164953
    assert first_mapped(row, FORT_WORTH_PERMITS_FIELD_MAP, "longitude") == -97.34097226394697


# --- Producer integration: WGS84 point geometry is used directly -------------


@pytest.fixture
def permits_producer():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        yield DOBPermitsProducer()


@patch(
    "src.producers.field_maps.resolve_field_map",
    lambda city, feed: FORT_WORTH_PERMITS_FIELD_MAP if (city == "fort_worth" and feed == FeedType.PERMITS) else {},
)
def test_fort_worth_permit_uses_wgs84_point_geometry(permits_producer):
    row = {
        "OBJECTID": 123456,
        "Unique_ID": "24TMP-037244",
        "Permit_No": "24TMP-037244",
        "Permit_Type": "Design Review",
        "JobValue": "2200",
        "Current_Status": "Pending",
        "File_Date": "4/28/2024, 12:00 AM",
        "Zip_Code": "76104",
        "SHAPE__X": -97.34097226394697,  # real WGS84 longitude
        "SHAPE__Y": 32.72750774164953,   # real WGS84 latitude
    }
    with patch(
        "src.spatial.geocoder.geocode_row_if_declared",
        return_value=(0.0, 0.0),
    ) as geocode:
        event = permits_producer.parse_socrata_row(row, city_id="fort_worth")
    assert event is not None
    assert event.city_id == "fort_worth"
    assert event.job_id == "24TMP-037244"
    # Coordinates are the WGS84 point geometry, NOT the (zeroed) geocoder result.
    assert event.latitude == pytest.approx(32.72750774164953)
    assert event.longitude == pytest.approx(-97.34097226394697)
    geocode.assert_not_called()


@patch(
    "src.producers.field_maps.resolve_field_map",
    lambda city, feed: FORT_WORTH_PERMITS_FIELD_MAP if (city == "fort_worth" and feed == FeedType.PERMITS) else {},
)
def test_fort_worth_permit_without_geometry_geocodes_address(permits_producer):
    row = {
        "OBJECTID": 123457,
        "Unique_ID": "CG18-00105",
        "Permit_No": "CG18-00105",
        "Permit_Type": "Commercial Grading Permit",
        "JobValue": "3589",
        "Current_Status": "Issued",
        "File_Date": "5/14/2018, 12:00 AM",
        "Addr_No": "3589",
        "Street_Name": "BELLAIRE",
        # No SHAPE__X/SHAPE__Y -> geocode fallback must supply coordinates.
    }
    with patch(
        "src.spatial.geocoder.geocode_row_if_declared",
        lambda *a, **k: (32.735, -97.36),
    ):
        event = permits_producer.parse_socrata_row(row, city_id="fort_worth")
    assert event is not None
    assert event.latitude == pytest.approx(32.735)
    assert event.longitude == pytest.approx(-97.36)
