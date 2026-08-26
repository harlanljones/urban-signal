"""Contract tests for Sacramento's native-point permits and 311 feeds."""

from unittest.mock import patch

import pytest

from src.spatial.cities.sacramento import (
    SACRAMENTO_DIVISION_BBOXES,
    SACRAMENTO_DIVISIONS,
    SACRAMENTO_METRO_BBOX,
    SACRAMENTO_SUBMARKETS,
    is_in_sacramento_metro,
)
from src.spatial.city_registry import CityId, FeedType, get_dataset, normalize_city


SACRAMENTO_PERMITS_FIELD_MAP = {
    "job_id": ["Application", "OBJECTID"],
    "issuance_date": ["ISSUED_DATE"],
    "filing_date": ["APPLIED_DATE", "OpenDate"],
    "job_type": ["Application_Type", "Application_Subtype", "PermitCategory"],
    "cost": ["Valuation"],
    "status": ["Application_Status"],
    "address_street": ["Address"],
    "zipcode": ["ZIP", "ZipCode"],
    "bbl": ["Parcel_Number"],
}

SACRAMENTO_311_FIELD_MAP = {
    "incident_id": ["ReferenceNumber", "OBJECTID"],
    "created_date": ["DateCreated"],
    "closed_date": ["DateClosed"],
    "status": ["PublicStatus"],
    "complaint_type": ["CategoryLevel2", "CategoryLevel1", "CategoryName"],
    "incident_address": ["Address"],
    "borough": ["Neighborhood", "CouncilDistrictNumber"],
    "zipcode": ["ZIP"],
}


def test_sacramento_geometry_is_self_consistent():
    assert is_in_sacramento_metro(38.5816, -121.4944)
    assert is_in_sacramento_metro(38.6500, -121.5100)
    assert not is_in_sacramento_metro(37.7749, -122.4194)
    assert not is_in_sacramento_metro(None, None)
    for name, bbox in SACRAMENTO_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= SACRAMENTO_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= SACRAMENTO_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= SACRAMENTO_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= SACRAMENTO_METRO_BBOX["max_lng"], name
    claimed = [name for division in SACRAMENTO_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(SACRAMENTO_SUBMARKETS)
    assert {meta.city_id for meta in SACRAMENTO_SUBMARKETS.values()} == {"sacramento"}


def test_sacramento_registers_permits_and_311():
    city = CityId.SACRAMENTO
    assert normalize_city("sacramento ca") is city
    assert normalize_city("sacramento county") is city
    assert {feed for feed in (FeedType.PERMITS, FeedType.COMPLAINTS_311) if get_dataset(city, feed)} == {
        FeedType.PERMITS,
        FeedType.COMPLAINTS_311,
    }

    permits = get_dataset(city, FeedType.PERMITS)
    assert permits.platform == "arcgis"
    assert permits.endpoint.endswith("/Permits/FeatureServer/0")
    assert permits.watermark_col == "ISSUED_DATE"
    assert permits.extra["field_map"] == SACRAMENTO_PERMITS_FIELD_MAP
    assert permits.extra["needs_geocode"] is False

    complaints = get_dataset(city, FeedType.COMPLAINTS_311)
    assert complaints.platform == "arcgis"
    assert complaints.watermark_col == "DateCreated"
    assert complaints.extra["field_map"] == SACRAMENTO_311_FIELD_MAP


@pytest.fixture
def producers():
    with (
        patch("src.producers.dob_permits_producer.BaseKafkaProducer"),
        patch("src.producers.complaints_311_producer.BaseKafkaProducer"),
    ):
        from src.producers.complaints_311_producer import Complaints311Producer
        from src.producers.dob_permits_producer import DOBPermitsProducer

        yield DOBPermitsProducer(), Complaints311Producer()


def test_sacramento_permit_point_row_parses(producers):
    permits, _ = producers
    row = {
        "OBJECTID": 104030,
        "Application": "RRZR2024-02038",
        "Application_Type": "Residential",
        "Application_Subtype": "Residential Reroof",
        "Application_Status": "Issued",
        "ISSUED_DATE": "2026-08-24T00:00:00+00:00",
        "Address": "141 W ELVERTA RD, ELVERTA, CA 95626",
        "Valuation": 12130,
        "Parcel_Number": "20200600080000",
        "latitude": 38.7364,
        "longitude": -121.3831,
    }
    event = permits.parse_socrata_row(row, city_id="sacramento")
    assert event is not None
    assert event.city_id == "sacramento"
    assert event.job_id == "RRZR2024-02038"
    assert event.latitude == pytest.approx(38.7364)
    assert event.longitude == pytest.approx(-121.3831)


def test_sacramento_311_point_row_parses(producers):
    _, complaints = producers
    row = {
        "OBJECTID": 202,
        "ReferenceNumber": "SAC-311-2026-55",
        "DateCreated": "2026-08-24T10:00:00Z",
        "CategoryLevel1": "Public Works",
        "CategoryLevel2": "Street Light Out",
        "PublicStatus": "Open",
        "Address": "300 CAPITOL MALL",
        "ZIP": "95814",
        "latitude": 38.5816,
        "longitude": -121.4944,
    }
    event = complaints.parse_socrata_row(row, city_id="sacramento")
    assert event is not None
    assert event.incident_id == "SAC-311-2026-55"
    assert event.complaint_type == "Street Light Out"
    assert event.latitude == pytest.approx(38.5816)
    assert event.longitude == pytest.approx(-121.4944)
