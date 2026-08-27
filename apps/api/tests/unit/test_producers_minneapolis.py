"""Unit tests for the Minneapolis registration (permits + year-sliced 311).

Fixtures mirror live rows probed 2026-08-24 from the ArcGIS layers, flattened
the way ArcGISClient flattens them (attributes + geometry-lifted lowercase
latitude/longitude + epoch-ms dates converted to ISO).
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.producers.complaints_311_producer import Complaints311Producer
from src.producers.dob_permits_producer import DOBPermitsProducer
from src.producers.sla_licenses_producer import SLALicensesProducer
from src.spatial.cities.minneapolis import (
    MINNEAPOLIS_DIVISION_BBOXES,
    MINNEAPOLIS_DIVISIONS,
    MINNEAPOLIS_METRO_BBOX,
    MINNEAPOLIS_SUBMARKETS,
    is_in_minneapolis_metro,
)
from src.spatial.city_registry import (
    REGISTRY,
    CityId,
    FeedType,
    get_dataset,
    get_job_name,
    resolve_endpoint,
)

# Live-probed 2026-08-24, flattened to what ArcGISClient emits.
PERMIT_ROW = {
    "permitNumber": "BLDG1197550",
    "permitType": "Res",
    "occupancyType": "MFD",
    "workType": "ComMin",
    "status": "Issued",
    "milestone": "Issued",
    "value": 1250000.0,
    "totalFees": 2850.0,
    "dwellingUnitsNew": 4,
    "dwellingUnitsEliminated": 2,
    "applicantName": "EXAMPLE CONTRACTING",
    "Neighborhoods_Desc": "Nicollet Island - East Bank",
    "Wards": "3",
    "issueDate": "2026-08-23T00:00:00+00:00",
    "completeDate": "2026-08-23T00:00:00+00:00",
    "latitude": 44.98583799507117,
    "longitude": -93.2574077499995,
}

THREE11_ROW = {
    "CASEID": 201000824527,
    "SUBJECTNAME": "Streets",
    "REASONNAME": "Street Maintenance",
    "TYPENAME": "Pothole",
    "TITLE": "Pothole",
    "OPENEDDATETIME": "2026-08-22T19:51:00+00:00",
    "CLOSEDDATETIME": "2026-08-24T06:00:00+00:00",
    "CASESTATUS": 0,
    "IsAccessibilityRelated": "No",
    "latitude": 44.95553322115808,
    "longitude": -93.28047149607914,
}


@pytest.fixture
def permits():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        return DOBPermitsProducer()


@pytest.fixture
def complaints():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        return Complaints311Producer()


def test_minneapolis_permit_parses(permits):
    event = permits.parse_socrata_row(PERMIT_ROW, city_id="minneapolis")
    assert event is not None
    assert event.city_id == "minneapolis"
    assert event.job_id == "BLDG1197550"
    assert event.estimated_cost == 1250000.0
    assert event.proposed_dwelling_units == 4
    assert event.existing_dwelling_units == 2
    assert event.status == "Issued"
    assert event.issuance_date is not None
    assert event.latitude == pytest.approx(44.98583799507117)
    assert event.h3_res9
    assert is_in_minneapolis_metro(event.latitude, event.longitude)


def test_minneapolis_311_parses(complaints):
    event = complaints.parse_socrata_row(THREE11_ROW, city_id="minneapolis")
    assert event is not None
    assert event.city_id == "minneapolis"
    assert event.incident_id == "201000824527"
    assert event.complaint_type == "Pothole"
    assert event.created_date is not None
    assert event.closed_date is not None
    assert event.latitude == pytest.approx(44.95553322115808)
    assert event.h3_res9
    assert is_in_minneapolis_metro(event.latitude, event.longitude)


def test_minneapolis_311_maps_type_from_typename_via_field_map(complaints):
    event = complaints.parse_socrata_row(THREE11_ROW, city_id="minneapolis")
    # TYPENAME/REASONNAME ride the declared field map (the shared chains know
    # none of the camelCase spellings).
    assert event.complaint_type == "Pothole"


def test_registration_is_partial_permits_311_and_sla():
    reg = REGISTRY[CityId.MINNEAPOLIS]
    assert set(reg.datasets) == {FeedType.PERMITS, FeedType.COMPLAINTS_311, FeedType.SLA}
    # Property sales stay deliberately unregistered (stale + county-coordinate X/Y).
    for absent in (FeedType.DEEDS,):
        with pytest.raises(KeyError):
            get_dataset(CityId.MINNEAPOLIS, absent)
    assert get_job_name(FeedType.PERMITS, CityId.MINNEAPOLIS) == "permits_minneapolis"
    assert get_job_name(FeedType.COMPLAINTS_311, CityId.MINNEAPOLIS) == "311_minneapolis"
    assert get_job_name(FeedType.SLA, CityId.MINNEAPOLIS) == "sla_minneapolis"


def test_311_is_year_sliced_and_resolves_current_year():
    spec = get_dataset(CityId.MINNEAPOLIS, FeedType.COMPLAINTS_311)
    by_year = spec.endpoint_by_year
    assert "2026" in by_year
    assert resolve_endpoint(spec, datetime(2026, 8, 24).date()).endswith("Public_311_2026/FeatureServer/0")
    assert resolve_endpoint(spec, datetime(2025, 6, 1).date()).endswith("Public_311_2025/FeatureServer/0")
    assert spec.oid_field == "OBJECTID"
    assert spec.max_record_count == 16000


def test_division_geometry_nests_and_resolves():
    from src.spatial.geo_utils import get_division_for_coordinate

    div = get_division_for_coordinate(44.9770, -93.2730, city_id="minneapolis")
    assert div == "CENTRAL"
    assert MINNEAPOLIS_SUBMARKETS and MINNEAPOLIS_DIVISIONS and MINNEAPOLIS_DIVISION_BBOXES
    assert MINNEAPOLIS_METRO_BBOX["min_lat"] < MINNEAPOLIS_METRO_BBOX["max_lat"]


# Live-probed 2026-08-25 via `query?f=json&where=1=1&outFields=*&outSR=4326`,
# then flattened the way ArcGISClient._flatten_feature delivers it: attributes
# dict with esriFieldTypeDate fields (issueDate/expirationDate/lastUpdateDate)
# re-encoded to ISO 8601, and point geometry (outSR=4326) lifted onto
# longitude/latitude because this layer spells its own coordinates `lat`/`long`.
SLA_ROW = {
    "apn": "1002824220002",
    "OBJECTID": 648,
    "licenseNumber": "LIC404929",
    "licenseType": "BLWine",
    "licenseStatus": "Approved",
    "liquorType": "On Sale",
    "issueDate": "2026-06-01T14:29:48+00:00",
    "expirationYear": 2027,
    "expirationDate": "2027-04-01T23:59:59+00:00",
    "licenseName": "Clancey's",
    "address": "3804 GRAND AVE S",
    "endorsements": " Wine, On Sale, Add Strong Beer; Wine, On Sale, No Entertainment",
    "ward": "8",
    "neighborhood": "King Field",
    "lat": 44.93383,
    "long": -93.28474,
    "xWebMercator": -10384409.4881,
    "yWebMercator": 5611110.8236,
    "lastUpdateDate": "2026-06-02T18:15:26+00:00",
    # geometry-lifted by the client (setdefault on a layer without those keys)
    "latitude": 44.9338328064466,
    "longitude": -93.2847375971601,
}


@pytest.fixture
def sla():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        return SLALicensesProducer()


class TestMinneapolisSLAParsing:
    """US-135: register the On/Off-Sale liquor ArcGIS layer (camelCase, native
    `lat`/`long` spelling). The registry field_map is the only thing mapping
    the Minneapolis spellings; no producer chain knows any of them, so these
    pins prove the declared map resolves every field."""

    def test_live_row_parses_via_the_registry_field_map(self, sla):
        event = sla.parse_socrata_row(dict(SLA_ROW), city_id="minneapolis")
        assert event is not None
        assert event.city_id == "minneapolis"
        assert event.license_id == "LIC404929"
        assert event.license_type == "BLWine"
        assert event.dba == "Clancey's"
        assert event.address == "3804 GRAND AVE S"
        assert event.effective_date is not None
        assert (event.effective_date.year, event.effective_date.month) == (2026, 6)
        assert event.expiration_date is not None
        assert (event.expiration_date.year, event.expiration_date.month) == (2027, 4)
        # ward is the first borough candidate in the declared field map
        assert event.source_neighborhood == "8"
        assert event.borough is not None

    def test_lat_long_spelling_resolves_through_first_mapped(self, sla):
        """The feed spells its coordinates `lat`/`long` (not latitude/longitude)
        but ArcGISClient also lifts the point geometry onto latitude/longitude.
        The field map pins `latitude:["lat"]` / `longitude:["long"]`, so the
        native attribute values win over the geometry lift."""
        event = sla.parse_socrata_row(dict(SLA_ROW), city_id="minneapolis")
        assert event.latitude == pytest.approx(44.93383)
        assert event.longitude == pytest.approx(-93.28474)
        assert event.h3_res9 is not None
        assert is_in_minneapolis_metro(event.latitude, event.longitude)

    def test_missing_license_number_returns_none(self, sla):
        row = dict(SLA_ROW)
        row.pop("licenseNumber")
        assert sla.parse_socrata_row(row, city_id="minneapolis") is None

    def test_off_sale_registered_as_companion_endpoint(self):
        spec = get_dataset(CityId.MINNEAPOLIS, FeedType.SLA)
        companion = spec.companion_endpoints["off_sale"]
        assert companion.endswith("/Off_Sale_Liquor/FeatureServer/0")
        assert spec.watermark_col == "issueDate"
        assert spec.id_keys == ["licenseNumber", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 16000