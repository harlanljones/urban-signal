"""Contract tests for Hartford's ArcGIS 311/permits and CT SLA feeds."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.producers.ct_liquor_specs import CT_LIQUOR_SLA_FIELD_MAP, ct_liquor_where
from src.spatial.cities.hartford import (
    HARTFORD_DIVISION_BBOXES,
    HARTFORD_DIVISIONS,
    HARTFORD_METRO_BBOX,
    HARTFORD_SUBMARKETS,
    is_in_hartford_metro,
)
from src.spatial.city_registry import (
    CityId,
    FeedType,
    get_dataset,
    normalize_city,
    resolve_endpoint,
)

HARTFORD_PERMITS_FIELD_MAP = {
    "job_id": ["RECORD_ID"],
    "issuance_date": ["DateIssued"],
    "job_type": ["PermitType", "PERMIT_TYPE", "WorkDescription"],
    "cost": ["EstimatedCost", "COST", "ProjectCost"],
    "status": ["Status", "STATUS"],
    "address_street": ["PROPERTY_ADDRESS", "Location"],
    "zipcode": ["ZIP", "ZipCode", "POSTAL_CODE"],
    "bbl": ["PARCEL_ID", "ParcelID"],
}

HARTFORD_311_FIELD_MAP = {
    "incident_id": ["SR_Number", "SRM_Number", "OBJECTID"],
    "created_date": ["USER_Opened_Date"],
    "closed_date": ["USER_Closed_Date", "Closed_Date"],
    "status": ["Status", "STATUS"],
    "complaint_type": ["SR_Type", "Request_Type", "Service_Name"],
    "incident_address": ["Match_addr", "Location", "Address"],
    "borough": ["Neighborhood", "Council_District"],
    "zipcode": ["ZIP", "ZipCode", "PostalCode"],
}


def test_hartford_geometry_is_self_consistent():
    assert is_in_hartford_metro(41.7637, -72.6734)
    assert not is_in_hartford_metro(40.7128, -74.0060)
    assert not is_in_hartford_metro(None, None)
    for name, bbox in HARTFORD_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= HARTFORD_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= HARTFORD_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= HARTFORD_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= HARTFORD_METRO_BBOX["max_lng"], name
    claimed = [name for division in HARTFORD_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(HARTFORD_SUBMARKETS)
    assert {m.city_id for m in HARTFORD_SUBMARKETS.values()} == {"hartford"}


def test_hartford_registers_311_permits_and_sla():
    city = CityId.HARTFORD
    assert normalize_city("hartford") is city
    assert normalize_city("hartford ct") is city
    assert normalize_city("hartford county") is city
    permits = get_dataset(city, FeedType.PERMITS)
    assert permits.platform == "arcgis"
    assert permits.watermark_col == "DateIssued"
    assert permits.id_keys == ["RECORD_ID", "OBJECTID"]
    assert permits.field_map == HARTFORD_PERMITS_FIELD_MAP
    assert permits.needs_geocode is True

    complaints = get_dataset(city, FeedType.COMPLAINTS_311)
    assert complaints.platform == "arcgis"
    assert complaints.watermark_col == "USER_Opened_Date"
    assert complaints.endpoint_by_year["2026"] == complaints.endpoint
    assert complaints.field_map == HARTFORD_311_FIELD_MAP
    assert resolve_endpoint(complaints, datetime(2026, 8, 26, tzinfo=UTC).date()) == complaints.endpoint

    sla = get_dataset(city, FeedType.SLA)
    assert sla.platform == "socrata"
    assert sla.watermark_col == "recordrefreshedon"
    assert sla.where == ct_liquor_where("HARTFORD")
    assert sla.id_keys == ["credentialid"]
    assert sla.field_map == CT_LIQUOR_SLA_FIELD_MAP


@pytest.fixture
def producers():
    with (
        patch("src.producers.dob_permits_producer.BaseKafkaProducer"),
        patch("src.producers.complaints_311_producer.BaseKafkaProducer"),
        patch("src.producers.sla_licenses_producer.BaseKafkaProducer"),
    ):
        from src.producers.complaints_311_producer import Complaints311Producer
        from src.producers.dob_permits_producer import DOBPermitsProducer
        from src.producers.sla_licenses_producer import SLALicensesProducer

        yield DOBPermitsProducer(), Complaints311Producer(), SLALicensesProducer()


def _geocoder():
    return SimpleNamespace(geocode=lambda query: SimpleNamespace(lat=41.7637, lon=-72.6734))


def test_hartford_permit_row_geocodes_address_only_feed(producers):
    permits, _, _ = producers
    row = {
        "OBJECTID": 99123,
        "RECORD_ID": "RES-ALT-26-000445",
        "PROPERTY_ADDRESS": "165 CAPITOL AVE",
        "DateIssued": "2026-08-24T00:00:00+00:00",
        "PermitType": "Building Alteration",
        "EstimatedCost": "125000",
        "Status": "Issued",
        "PARCEL_ID": "HFD-001",
    }
    with patch("src.spatial.geocoder.get_geocoder", return_value=_geocoder()):
        event = permits.parse_socrata_row(row, city_id="hartford")
    assert event is not None
    assert event.city_id == "hartford"
    assert event.job_id == "RES-ALT-26-000445"
    assert event.address_street == "165 CAPITOL AVE"
    assert event.latitude == pytest.approx(41.7637)
    assert event.longitude == pytest.approx(-72.6734)
    assert event.issuance_date == datetime.fromisoformat("2026-08-24T00:00:00+00:00")


def test_hartford_311_state_plane_geometry_geocodes_match_address(producers):
    _, complaints, _ = producers
    row = {
        "OBJECTID": 882211,
        "SR_Number": "SRM-2026-11066",
        "SR_Type": "Pothole",
        "USER_Opened_Date": "2026-08-24",
        "Status": "Open",
        "Match_addr": "450 MAIN ST, HARTFORD, CT",
        "latitude": 837000,
        "longitude": 1020000,
    }
    with patch("src.spatial.geocoder.get_geocoder", return_value=_geocoder()):
        event = complaints.parse_socrata_row(row, city_id="hartford")
    assert event is not None
    assert event.incident_id == "SRM-2026-11066"
    assert event.complaint_type == "Pothole"
    assert event.latitude == pytest.approx(41.7637)
    assert event.longitude == pytest.approx(-72.6734)


def test_hartford_sla_row_geocodes_address_only_feed(producers):
    """A live liquor permit row (2026-09-30). The feed registered with
    ``license_number``/``business_name`` spellings the state table does not
    have, so every row was dropped for a missing licence id."""
    _, _, sla = producers
    row = {
        "credentialid": "2534916",
        "name": "URBAN LODGE BREWING - PRATT ST LLC",
        "type": "BUSINESS",
        "businessname": "URBAN LODGE BREWING - PRATT ST LLC",
        "dba": "URBAN LODGE BREWING",
        "fullcredentialcode": "LIR.0021240",
        "credentialtype": "LIR",
        "credentialnumber": "21240",
        "credential": "RESTAURANT LIQUOR",
        "status": "ACTIVE",
        "statusreason": "CURRENT",
        "active": "1",
        "issuedate": "2023-09-28T00:00:00.000",
        "effectivedate": "2026-09-28T00:00:00.000",
        "expirationdate": "2027-09-27T00:00:00.000",
        "address": "88 PRATT ST",
        "city": "HARTFORD",
        "state": "CT",
        "zip": "061031621",
        "recordrefreshedon": "2026-09-25T00:00:00.000",
    }
    with patch("src.spatial.geocoder.get_geocoder", return_value=_geocoder()):
        event = sla.parse_socrata_row(row, city_id="hartford")
    assert event is not None
    assert event.license_id == "2534916"
    assert event.license_type == "RESTAURANT LIQUOR"
    assert event.premises_name == "URBAN LODGE BREWING - PRATT ST LLC"
    assert event.dba == "URBAN LODGE BREWING"
    assert event.address == "88 PRATT ST"
    assert str(event.effective_date).startswith("2026-09-28")
    assert event.latitude == pytest.approx(41.7637)
    assert event.longitude == pytest.approx(-72.6734)
