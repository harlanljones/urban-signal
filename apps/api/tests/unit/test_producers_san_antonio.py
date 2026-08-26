"""Contract tests for San Antonio's CKAN permits and ArcGIS 311 feeds."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.spatial.cities.san_antonio import (
    SAN_ANTONIO_DIVISION_BBOXES,
    SAN_ANTONIO_DIVISIONS,
    SAN_ANTONIO_METRO_BBOX,
    SAN_ANTONIO_SUBMARKETS,
    is_in_san_antonio_metro,
)
from src.spatial.city_registry import CityId, FeedType, get_dataset, normalize_city


SAN_ANTONIO_PERMITS_FIELD_MAP = {
    "job_id": ["PERMIT NUMBER", "PERMIT_NUMBER", "RECORD_ID", "_id"],
    "issuance_date": ["DATE ISSUED"],
    "filing_date": ["DATE SUBMITTED"],
    "job_type": ["PERMIT TYPE", "PERMIT_TYPE", "WORK TYPE"],
    "cost": ["ESTIMATED COST", "ESTIMATED_COST", "TOTAL PROJECT VALUE"],
    "status": ["STATUS", "PERMIT STATUS"],
    "address_street": ["ADDRESS"],
    "zipcode": ["ZIP", "ZIP CODE", "ZIP_CODE"],
    "latitude": ["Y_COORD"],
    "longitude": ["X_COORD"],
}

SAN_ANTONIO_311_FIELD_MAP = {
    "incident_id": ["ServiceRequestNumber", "SRNumber", "REQUEST_ID", "OBJECTID"],
    "created_date": ["OpenedDateTime"],
    "closed_date": ["ClosedDateTime", "ClosedDate"],
    "status": ["Status", "STATUS"],
    "complaint_type": ["ServiceName", "RequestType", "Type"],
    "incident_address": ["Address", "StreetAddress"],
    "borough": ["CouncilDistrict", "Neighborhood"],
    "zipcode": ["ZipCode", "ZIP"],
}


def test_san_antonio_geometry_is_self_consistent():
    assert is_in_san_antonio_metro(29.4241, -98.4936)
    assert is_in_san_antonio_metro(29.5100, -98.5800)
    assert not is_in_san_antonio_metro(30.2672, -97.7431)
    assert not is_in_san_antonio_metro(None, None)
    for name, bbox in SAN_ANTONIO_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= SAN_ANTONIO_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= SAN_ANTONIO_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= SAN_ANTONIO_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= SAN_ANTONIO_METRO_BBOX["max_lng"], name
    claimed = [name for division in SAN_ANTONIO_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(SAN_ANTONIO_SUBMARKETS)
    assert {meta.city_id for meta in SAN_ANTONIO_SUBMARKETS.values()} == {"san_antonio"}


def test_san_antonio_registers_permits_and_311():
    city = CityId.SAN_ANTONIO
    assert normalize_city("san antonio tx") is city
    assert normalize_city("bexar county") is city
    assert set(get_dataset(city, feed) and feed for feed in (FeedType.PERMITS, FeedType.COMPLAINTS_311)) == {
        FeedType.PERMITS,
        FeedType.COMPLAINTS_311,
    }

    permits = get_dataset(city, FeedType.PERMITS)
    assert permits.platform == "ckan"
    assert permits.endpoint == "ckan://data.sanantonio.gov/c21106f9-3ef5-4f3a-8604-f992b4db7512"
    assert permits.watermark_col == "DATE ISSUED"
    assert permits.extra["needs_geocode"] is True
    assert permits.extra["field_map"] == SAN_ANTONIO_PERMITS_FIELD_MAP

    complaints = get_dataset(city, FeedType.COMPLAINTS_311)
    assert complaints.platform == "arcgis"
    assert complaints.watermark_col == "OpenedDateTime"
    assert complaints.extra["field_map"] == SAN_ANTONIO_311_FIELD_MAP


@pytest.fixture
def producers():
    with (
        patch("src.producers.dob_permits_producer.BaseKafkaProducer"),
        patch("src.producers.complaints_311_producer.BaseKafkaProducer"),
    ):
        from src.producers.complaints_311_producer import Complaints311Producer
        from src.producers.dob_permits_producer import DOBPermitsProducer

        yield DOBPermitsProducer(), Complaints311Producer()


def test_san_antonio_permit_row_parses_text_coordinates(producers):
    permits, _ = producers
    row = {
        "_id": 101,
        "PERMIT NUMBER": "SA-2026-00123",
        "DATE ISSUED": "2026-08-24",
        "PERMIT TYPE": "New Construction",
        "ESTIMATED COST": "1250000",
        "STATUS": "Issued",
        "ADDRESS": "100 MAIN PLAZA",
        "ZIP CODE": "78205",
        "X_COORD": "-98.4936",
        "Y_COORD": "29.4241",
    }
    event = permits.parse_socrata_row(row, city_id="san_antonio")
    assert event is not None
    assert event.city_id == "san_antonio"
    assert event.job_id == "SA-2026-00123"
    assert event.latitude == pytest.approx(29.4241)
    assert event.longitude == pytest.approx(-98.4936)


def test_san_antonio_permit_projected_coordinates_use_address_geocoder(producers):
    permits, _ = producers
    row = {
        "_id": 102,
        "DATE ISSUED": "2026-08-24",
        "ADDRESS": "200 COMMERCE ST",
        "X_COORD": "1020000",
        "Y_COORD": "837000",
    }
    geocode = SimpleNamespace(lat=29.4241, lon=-98.4936)
    with patch("src.spatial.geocoder.get_geocoder") as get_geocoder:
        get_geocoder.return_value.geocode.return_value = geocode
        event = permits.parse_socrata_row(row, city_id="san_antonio")
    assert event is not None
    assert event.latitude == pytest.approx(29.4241)
    assert event.longitude == pytest.approx(-98.4936)


def test_san_antonio_311_point_row_parses(producers):
    _, complaints = producers
    row = {
        "OBJECTID": 202,
        "ServiceRequestNumber": "SA-311-2026-55",
        "OpenedDateTime": "2026-08-24T10:00:00Z",
        "ServiceName": "Street Light Out",
        "Status": "Open",
        "Address": "300 ALAMO PLAZA",
        "ZipCode": "78205",
        "latitude": 29.4241,
        "longitude": -98.4936,
    }
    event = complaints.parse_socrata_row(row, city_id="san_antonio")
    assert event is not None
    assert event.incident_id == "SA-311-2026-55"
    assert event.complaint_type == "Street Light Out"
    assert event.latitude == pytest.approx(29.4241)
    assert event.longitude == pytest.approx(-98.4936)
