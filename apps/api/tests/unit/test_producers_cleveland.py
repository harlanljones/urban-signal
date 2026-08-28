"""Contract tests for Cleveland's ArcGIS permits, 311, and deeds feeds."""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.spatial.cities.cleveland import (
    CLEVELAND_DIVISION_BBOXES,
    CLEVELAND_DIVISIONS,
    CLEVELAND_METRO_BBOX,
    CLEVELAND_SUBMARKETS,
    is_in_cleveland_metro,
)
from src.spatial.city_registry import CityId, FeedType

CLEVELAND_PERMITS_FIELD_MAP = {
    "job_id": ["PERMIT_NUMBER"],
    "issuance_date": ["ISSUE_DATE"],
    "filing_date": ["FILE_DATE"],
    "job_type": ["PERMIT_TYPE", "PERMIT_SUBTYPE"],
    "cost": ["JOB_VALUE"],
    "status": ["STATUS", "PERMIT_STATUS"],
    "address_street": ["ADDRESS"],
    "zipcode": ["ZIP", "ZIP_CODE"],
    "bbl": ["PARCEL_NUMBER"],
}

CLEVELAND_311_FIELD_MAP = {
    "incident_id": ["SR_NUMBER", "SERVICE_REQUEST_ID", "REQUEST_ID"],
    "created_date": ["requested_datetime"],
    "closed_date": ["closed_datetime", "closed_date"],
    "status": ["status"],
    "complaint_type": ["service_name"],
    "incident_address": ["address"],
    "borough": ["ward", "neighborhood"],
    "zipcode": ["zip", "zipcode"],
    "latitude": ["lat"],
    "longitude": ["long"],
}

CLEVELAND_DEEDS_FIELD_MAP = {
    "doc_id": ["PARCEL_ID", "PARCEL_NUMBER", "OBJECTID"],
    "recorded_date": ["last_transfer_date"],
    "document_amount": ["sale_price", "transfer_amount"],
    "bbl": ["parcel_number", "PARCEL_NUMBER", "PARCEL_ID"],
    "party1_grantor": ["grantor"],
    "party2_grantee": ["grantee"],
    "doc_type": ["document_type", "deed_type"],
    "borough": ["ward", "neighborhood"],
}


def test_cleveland_geometry_is_self_consistent():
    assert is_in_cleveland_metro(41.4993, -81.6944)
    assert is_in_cleveland_metro(41.5088, -81.6045)
    assert not is_in_cleveland_metro(39.9612, -83.0007)  # Columbus
    assert not is_in_cleveland_metro(None, None)
    for name, bbox in CLEVELAND_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= CLEVELAND_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= CLEVELAND_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= CLEVELAND_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= CLEVELAND_METRO_BBOX["max_lng"], name
    claimed = [name for division in CLEVELAND_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(CLEVELAND_SUBMARKETS)
    assert {m.city_id for m in CLEVELAND_SUBMARKETS.values()} == {"cleveland"}


def test_cleveland_registers_three_verified_feeds_and_snap_sla():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.CLEVELAND
    assert normalize_city("cleveland") is city
    assert normalize_city("cleveland oh") is city
    assert normalize_city("cuyahoga county") is city
    assert REGISTRY[city].job_suffix == "cleveland"
    assert set(REGISTRY[city].datasets) == {
        FeedType.PERMITS,
        FeedType.COMPLAINTS_311,
        FeedType.DEEDS,
        FeedType.SLA,
    }

    permits = get_dataset(city, FeedType.PERMITS)
    assert permits.platform == "arcgis"
    assert permits.watermark_col == "ISSUE_DATE"
    assert permits.id_keys == ["PERMIT_NUMBER", "OBJECTID"]
    assert permits.field_map == CLEVELAND_PERMITS_FIELD_MAP

    complaints = get_dataset(city, FeedType.COMPLAINTS_311)
    assert complaints.platform == "arcgis"
    assert complaints.watermark_col == "requested_datetime"
    assert complaints.id_keys == ["SR_NUMBER", "OBJECTID"]
    assert complaints.field_map == CLEVELAND_311_FIELD_MAP

    deeds = get_dataset(city, FeedType.DEEDS)
    assert deeds.platform == "arcgis"
    assert deeds.watermark_col == "last_transfer_date"
    assert deeds.id_keys == ["PARCEL_ID", "OBJECTID"]
    assert deeds.field_map == CLEVELAND_DEEDS_FIELD_MAP


PERMIT_ROW = {
    "OBJECTID": 99123,
    "PERMIT_NUMBER": "B2026-00123",
    "ADDRESS": "123 EUCLID AVE",
    "FILE_DATE": "2026-08-14T00:00:00+00:00",
    "ISSUE_DATE": "2026-08-14T00:00:00+00:00",
    "PERMIT_TYPE": "New Construction",
    "JOB_VALUE": 1250000,
    "STATUS": "Issued",
    "PARCEL_NUMBER": "007-01-001",
    "latitude": 41.4993,
    "longitude": -81.6944,
}

COMPLAINT_ROW = {
    "OBJECTID": 882211,
    "SR_NUMBER": "26-123456",
    "service_name": "Pothole",
    "agency_responsible": "Public Works",
    "requested_datetime": "2026-08-24T23:54:00+00:00",
    "closed_datetime": None,
    "status": "Open",
    "address": "4500 DETROIT AVE",
    "parcelpin": "006-22-004",
    "zip": "44102",
    "lat": 41.4504,
    "long": -81.7843,
}

DEED_ROW = {
    "OBJECTID": 77110,
    "PARCEL_ID": "123-45-678",
    "parcel_number": "123-45-678",
    "last_transfer_date": "2026-08-21T00:00:00+00:00",
    "sale_price": 27200,
    "grantor": "DSV SPV3 LLC",
    "grantee": "3S FUND I LLC",
    "book_page": "B 138 P 24",
    "document_type": "DEED",
    "latitude": 41.4839,
    "longitude": -81.7049,
}


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


def test_cleveland_permit_row_parses(producers):
    permits, _, _ = producers
    event = permits.parse_socrata_row(dict(PERMIT_ROW), city_id="cleveland")
    assert event is not None
    assert event.city_id == "cleveland"
    assert event.job_id == "B2026-00123"
    assert event.estimated_cost == 1250000.0
    assert event.issuance_date == datetime.fromisoformat("2026-08-14T00:00:00+00:00")
    assert event.borough == "CLEVELAND_CORE"


def test_cleveland_311_row_parses(producers):
    _, complaints, _ = producers
    event = complaints.parse_socrata_row(dict(COMPLAINT_ROW), city_id="cleveland")
    assert event is not None
    assert event.city_id == "cleveland"
    assert event.incident_id == "26-123456"
    assert event.complaint_type == "Pothole"
    assert event.created_date == datetime.fromisoformat("2026-08-24T23:54:00+00:00")
    assert event.latitude == pytest.approx(41.4504)
    assert event.longitude == pytest.approx(-81.7843)
    assert event.borough == "CLEVELAND_CORE"


def test_cleveland_deed_row_parses(producers):
    _, _, deeds = producers
    event = deeds.parse_socrata_row(dict(DEED_ROW), city_id="cleveland")
    assert event is not None
    assert event.city_id == "cleveland"
    assert event.doc_id == "123-45-678"
    assert event.document_amount == 27200.0
    assert event.recorded_date == datetime.fromisoformat("2026-08-21T00:00:00+00:00")
    assert event.party1_grantor == "DSV SPV3 LLC"
    assert event.party2_grantee == "3S FUND I LLC"
    assert event.borough == "CLEVELAND_CORE"


def test_cleveland_arcgis_epoch_ms_dates_flatten_to_iso():
    from src.producers.arcgis_client import ArcGISClient

    row = ArcGISClient()._flatten_feature(
        {
            "attributes": {"ISSUE_DATE": 1786665600000},
            "geometry": {"x": -81.6944, "y": 41.4993},
        },
        date_fields={"ISSUE_DATE"},
    )
    assert row["ISSUE_DATE"].startswith("2026-08-14")
    assert row["latitude"] == pytest.approx(41.4993)
    assert row["longitude"] == pytest.approx(-81.6944)
