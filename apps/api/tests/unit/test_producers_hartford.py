"""Contract tests for Hartford's ArcGIS 311/permits/deeds and CT SLA feeds."""

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

# The layer's own columns (2026-10-02).
HARTFORD_PERMITS_FIELD_MAP = {
    "job_id": ["RECORD_ID"],
    "issuance_date": ["DateIssued"],
    "filing_date": ["DATE_OPENED"],
    "job_type": ["B1_APP_TYPE_ALIAS", "RECORD_TYPE_TYPE"],
    "cost": ["Total_Construction_Cost"],
    "status": ["RECORD_STATUS"],
    "address_street": ["PROPERTY_ADDRESS", "Location"],
    "zipcode": ["PROPERTY_ZIP"],
    "bbl": ["PARCEL_ID"],
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

# The CAMA table's owner, mailing (City, State, Zip10) and grantor columns are
# never mapped or requested.
HARTFORD_DEEDS_FIELD_MAP = {
    "doc_id": ["LegalRef", "ParcelNumber"],
    "recorded_date": ["LastSaleDate"],
    "document_amount": ["LastSalePrice"],
    "bbl": ["ParcelNumber"],
    "doc_type": ["LastSalecode"],
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
    # Fee records and amendments are not permits of their own.
    assert permits.where == "RECORD_TYPE_TYPE NOT IN ('Miscellaneous Fees', 'Amendment')"
    # The assignee and the free-text description stay on the server.
    assert not {"ASSIGNED_TO", "DESCRIPTION"} & set(permits.select.split(","))

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



def test_hartford_deeds_read_each_accounts_last_sale_at_its_parcel():
    """The city's CAMA table holds each account's last sale, live through
    2026-09-22, and no geometry; its ParcelNumber is the parcel layer's
    PARCELNUMBER (200 of 200 matched). CT OPM's statewide sales set ends
    2025-09-30 and the city's own sales table stopped at 2026-01-09."""
    from src.config import settings

    spec = get_dataset(CityId.HARTFORD, FeedType.DEEDS)
    assert spec.endpoint == settings.arcgis_hartford_deeds_url
    assert spec.endpoint.endswith("/HartfordOpenDataTables/FeatureServer/6")
    assert spec.platform == "arcgis"
    assert spec.ingestion_mode == "snapshot"
    assert spec.watermark_col == "LastSaleDate"
    assert spec.where == (
        "LastSaleDate >= CURRENT_DATE - INTERVAL '90' DAY AND LastSaleDate <= CURRENT_TIMESTAMP"
    )
    assert spec.order_by == "LastSaleDate DESC, OBJECTID DESC"
    assert spec.id_keys == ["ParcelNumber", "LastSaleDate", "LegalRef"]
    assert spec.composite_id is True
    assert spec.select == "OBJECTID,ParcelNumber,LastSaleDate,LastSalePrice,LastSalecode,LegalRef"
    # 353 sales in the window on 2026-09-30: one page, under the default cap.
    assert spec.batch_limit is None
    assert spec.needs_geocode is False
    assert spec.parcel_join == {
        "parcel_layer": settings.arcgis_hartford_parcel_layer_url,
        "join_key": "PARCELNUMBER",
        "geometry_source": "centroid",
        "row_key": "ParcelNumber",
    }
    assert spec.field_map == HARTFORD_DEEDS_FIELD_MAP


def test_hartford_joined_sale_parses_with_its_sale_code():
    with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
        from src.producers.deeds_acris_producer import DeedsACRISProducer

        deeds = DeedsACRISProducer()
    row = {
        "OBJECTID": 90003,
        "ParcelNumber": "900000001",
        "LastSaleDate": "2026-09-22T00:00:00+00:00",
        "LastSalePrice": 310000.0,
        "LastSalecode": "Valid Sale",
        "LegalRef": "99999 0001",
        # The parcel join's centroid.
        "latitude": 41.7637,
        "longitude": -72.6851,
    }

    event = deeds.parse_socrata_row(row, city_id="hartford")

    assert event is not None
    assert (event.doc_id, event.bbl, event.doc_type) == ("99999 0001", "900000001", "VALID SALE")
    assert event.document_amount == 310000.0
    assert event.recorded_date.date().isoformat() == "2026-09-22"
    assert is_in_hartford_metro(event.latitude, event.longitude)


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
        "DATE_OPENED": "2026-08-03T00:00:00+00:00",
        "B1_APP_TYPE_ALIAS": "Commercial Alteration Permit",
        "RECORD_TYPE_TYPE": "Commercial",
        "Total_Construction_Cost": 125000,
        "RECORD_STATUS": "Issued",
        "PROPERTY_ZIP": "06106",
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
    assert event.filing_date == datetime.fromisoformat("2026-08-03T00:00:00+00:00")
    assert event.estimated_cost == 125000.0
    assert event.status == "Issued"
    assert event.zipcode == "06106"
    assert event.job_type == "A2"


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
