"""Contract tests for Raleigh / Wake County's three live signal feeds."""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.spatial.cities.raleigh import (
    RALEIGH_DIVISION_BBOXES,
    RALEIGH_DIVISIONS,
    RALEIGH_METRO_BBOX,
    RALEIGH_SUBMARKETS,
    is_in_raleigh_metro,
)
from src.spatial.city_registry import CityId, FeedType, get_dataset, normalize_city


RALEIGH_PERMITS_FIELD_MAP = {
    "job_id": ["permitnum", "permitnumber"],
    "issuance_date": ["issueddate"],
    "filing_date": ["submitteddate", "applicationdate"],
    "job_type": ["permittypemapped", "permittype", "permitclass"],
    "cost": ["estprojectcost", "estimatedcost"],
    "status": ["statuscurrent", "status"],
    "address_street": ["originaladdress1", "address"],
    "zipcode": ["originalzip", "zip", "zip_code"],
    "bbl": ["pin", "parcelid"],
    "latitude": ["latitude_perm"],
    "longitude": ["longitude_perm"],
}

RALEIGH_311_FIELD_MAP = {
    "incident_id": ["REQUEST_ID", "SR_NUMBER", "OBJECTID"],
    "created_date": ["APPLIED_DATE"],
    "closed_date": ["RESOLVED_DATE", "CLOSED_DATE"],
    "status": ["STATUS", "Status"],
    "complaint_type": ["CATEGORY", "SERVICE", "REQUEST_TYPE"],
    "incident_address": ["ADDRESS", "FULL_ADDRESS"],
    "borough": ["DISTRICT", "NEIGHBORHOOD"],
    "zipcode": ["ZIP_CODE", "ZIP"],
}

RALEIGH_DEEDS_FIELD_MAP = {
    "doc_id": ["OBJECTID", "PIN", "PARCELID"],
    "recorded_date": ["SALE_DATE"],
    "document_amount": ["TOTSALPRICE", "SALE_PRICE"],
    "bbl": ["PIN", "PARCELID"],
    "party2_grantee": ["OWNER_NAME", "OWNERNAME"],
    "doc_type": ["DEED_TYPE", "SALE_TYPE"],
    "borough": ["MUNICIPALITY", "CITY"],
}


def test_raleigh_geometry_is_self_consistent():
    assert is_in_raleigh_metro(35.7796, -78.6382)
    assert is_in_raleigh_metro(35.9132, -78.6510)
    assert not is_in_raleigh_metro(36.1627, -86.7816)
    assert not is_in_raleigh_metro(None, None)
    for name, bbox in RALEIGH_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= RALEIGH_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= RALEIGH_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= RALEIGH_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= RALEIGH_METRO_BBOX["max_lng"], name
    claimed = [name for division in RALEIGH_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(RALEIGH_SUBMARKETS)
    assert {meta.city_id for meta in RALEIGH_SUBMARKETS.values()} == {"raleigh"}


def test_raleigh_registers_permits_311_and_deeds():
    city = CityId.RALEIGH
    assert normalize_city("raleigh nc") is city
    assert normalize_city("wake county") is city
    assert set(city for city in [FeedType.PERMITS, FeedType.COMPLAINTS_311, FeedType.DEEDS]) == set(
        get_dataset(city, feed) and feed for feed in (FeedType.PERMITS, FeedType.COMPLAINTS_311, FeedType.DEEDS)
    )

    permits = get_dataset(city, FeedType.PERMITS)
    assert permits.platform == "arcgis"
    assert permits.watermark_col == "issueddate"
    assert permits.id_keys == ["permitnum", "OBJECTID"]
    assert permits.extra["field_map"] == RALEIGH_PERMITS_FIELD_MAP

    complaints = get_dataset(city, FeedType.COMPLAINTS_311)
    assert complaints.platform == "arcgis"
    assert complaints.watermark_col == "APPLIED_DATE"
    assert complaints.extra["field_map"] == RALEIGH_311_FIELD_MAP

    deeds = get_dataset(city, FeedType.DEEDS)
    assert deeds.platform == "arcgis"
    assert deeds.watermark_col == "SALE_DATE"
    assert deeds.extra["ingestion_mode"] == "snapshot"
    assert deeds.extra["field_map"] == RALEIGH_DEEDS_FIELD_MAP


@pytest.fixture
def producers():
    with (
        patch("src.producers.dob_permits_producer.BaseKafkaProducer"),
        patch("src.producers.complaints_311_producer.BaseKafkaProducer"),
        patch("src.producers.deeds_acris_producer.BaseKafkaProducer"),
    ):
        from src.producers.complaints_311_producer import Complaints311Producer
        from src.producers.deeds_acris_producer import DeedsACRISProducer
        from src.producers.dob_permits_producer import DOBPermitsProducer

        yield DOBPermitsProducer(), Complaints311Producer(), DeedsACRISProducer()


def test_raleigh_permit_row_parses_native_coordinates(producers):
    permits, _, _ = producers
    row = {
        "OBJECTID": 1001,
        "permitnum": "R-2026-00123",
        "issueddate": "2026-08-24",
        "permittypemapped": "New Building",
        "estprojectcost": "1250000",
        "statuscurrent": "Issued",
        "originaladdress1": "123 FAYETTEVILLE ST",
        "originalzip": "27601",
        "pin": "0794567890",
        "latitude_perm": 35.7796,
        "longitude_perm": -78.6382,
    }
    event = permits.parse_socrata_row(row, city_id="raleigh")
    assert event is not None
    assert event.city_id == "raleigh"
    assert event.job_id == "R-2026-00123"
    assert event.estimated_cost == 1250000.0
    assert event.latitude == pytest.approx(35.7796)
    assert event.longitude == pytest.approx(-78.6382)
    assert event.issuance_date == datetime.fromisoformat("2026-08-24")


def test_raleigh_311_point_row_parses(producers):
    _, complaints, _ = producers
    row = {
        "OBJECTID": 2002,
        "REQUEST_ID": "REQ-2026-0099",
        "APPLIED_DATE": "2026-08-24",
        "CATEGORY": "Street Maintenance",
        "SERVICE": "Pothole",
        "STATUS": "Open",
        "ADDRESS": "200 HILLSBOROUGH ST",
        "ZIP_CODE": "27603",
        "latitude": 35.7796,
        "longitude": -78.6382,
    }
    event = complaints.parse_socrata_row(row, city_id="raleigh")
    assert event is not None
    assert event.incident_id == "REQ-2026-0099"
    assert event.complaint_type == "Street Maintenance"
    assert event.latitude == pytest.approx(35.7796)
    assert event.longitude == pytest.approx(-78.6382)


def test_raleigh_deed_row_parses(producers):
    _, _, deeds = producers
    row = {
        "OBJECTID": 3003,
        "PIN": "0794567890",
        "SALE_DATE": "2026-08-10T00:00:00+00:00",
        "TOTSALPRICE": 475000,
        "OWNER_NAME": "RALEIGH HOLDINGS LLC",
        "DEED_TYPE": "WD",
        "MUNICIPALITY": "RALEIGH",
        "latitude": 35.7796,
        "longitude": -78.6382,
    }
    event = deeds.parse_socrata_row(row, city_id="raleigh")
    assert event is not None
    assert event.city_id == "raleigh"
    assert event.doc_id == "3003"
    assert event.document_amount == 475000.0
    assert event.recorded_date == datetime.fromisoformat("2026-08-10T00:00:00+00:00")
    assert event.party2_grantee == "RALEIGH HOLDINGS LLC"
