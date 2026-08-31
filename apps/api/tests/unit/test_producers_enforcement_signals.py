"""Unit tests for the US-209 Boston signal-supplement producers (violations + inspections).

Fixtures mirror live rows probed 2026-08-28 from data.boston.gov CKAN.
"""

from unittest.mock import patch

from src.producers.enforcement_signals_producer import (
    InspectionsProducer,
    ViolationsProducer,
    _parse_location_tuple,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType, get_dataset

VIOLATION_ROW = {
    "case_no": "V91983",
    "ap_case_defn_key": "1013",
    "status_dttm": "2026-08-24T14:30:00+00:00",
    "status": "Closed",
    "code": "121.2",
    "value": "N/A",
    "description": "Unsafe and Dangerous",
    "violation_stno": "12",
    "violation_street": "MAIN ST",
    "violation_city": "BOSTON",
    "violation_state": "MA",
    "violation_zip": "02129",
    "ward": "1",
    "latitude": "42.3750",
    "longitude": "-71.0625",
}

INSPECTION_ROW = {
    "businessname": "1000 Degrees Pizza",
    "dbaname": None,
    "legalowner": "KHOSLA VIPAN",
    "licenseno": "313440",
    "issdttm": "2017-08-14 12:49:37+00",
    "expdttm": None,
    "licstatus": "Active",
    "licensecat": "Food Establishment",
    "result": "Pass",
    "violation": None,
    "viol_level": "NON-CRITICAL",
    "violdesc": "Cold holding",
    "viol_status": "Open",
    "status_date": "2026-08-01 10:00:00+00",
    "address": "12 MAIN ST",
    "city": "BOSTON",
    "state": "MA",
    "zip": "02129",
    "property_id": "P-123",
    "location": "(42.35925954972639, -71.05890048027378)",
}


def test_boston_registers_violations_and_inspections():
    reg = REGISTRY[CityId.BOSTON]
    assert FeedType.VIOLATIONS in reg.datasets
    assert FeedType.INSPECTIONS in reg.datasets
    v_spec = get_dataset(CityId.BOSTON, FeedType.VIOLATIONS)
    i_spec = get_dataset(CityId.BOSTON, FeedType.INSPECTIONS)
    assert v_spec.platform == "ckan"
    assert v_spec.watermark_col == "status_dttm"
    assert i_spec.platform == "ckan"
    assert i_spec.watermark_col == "status_date"


def test_violations_producer_parses_row():
    with patch.object(ViolationsProducer, "__init__", lambda self, bootstrap_servers=None: None):
        prod = ViolationsProducer()
        prod.spatial_indexer = __import__("src.spatial.h3_indexer", fromlist=["H3SpatialIndexer"]).H3SpatialIndexer()
        event = prod.parse_row(VIOLATION_ROW)
        assert event is not None
        assert event.violation_id == "V91983"
        assert event.code == "121.2"
        assert event.status == "Closed"
        assert event.latitude == 42.3750
        assert event.longitude == -71.0625
        assert event.status_date is not None
        assert event.h3_res9 is not None


def test_violations_producer_drops_missing_coords():
    with patch.object(ViolationsProducer, "__init__", lambda self, bootstrap_servers=None: None):
        prod = ViolationsProducer()
        bad = dict(VIOLATION_ROW)
        bad.pop("latitude")
        bad.pop("longitude")
        assert prod.parse_row(bad) is None


def test_inspections_producer_parses_location_tuple():
    with patch.object(InspectionsProducer, "__init__", lambda self, bootstrap_servers=None: None):
        prod = InspectionsProducer()
        prod.spatial_indexer = __import__("src.spatial.h3_indexer", fromlist=["H3SpatialIndexer"]).H3SpatialIndexer()
        event = prod.parse_row(INSPECTION_ROW)
        assert event is not None
        assert event.inspection_id == "313440"
        assert event.business_name == "1000 Degrees Pizza"
        assert event.result == "Pass"
        assert event.latitude == 42.35925954972639
        assert event.longitude == -71.05890048027378
        assert event.h3_res9 is not None


def test_location_tuple_parser():
    assert _parse_location_tuple("(42.359, -71.058)") == (42.359, -71.058)
    assert _parse_location_tuple("(0.0, 0.0)") is None
    assert _parse_location_tuple("not a tuple") is None
    assert _parse_location_tuple(None) is None


# ---------------------------------------------------------------------------
# NYC DOHMH Restaurant Inspections (US-208) — Socrata, native lat/lng
# ---------------------------------------------------------------------------

NYC_INSPECTION_ROW = {
    "camis": "50051779",
    "dba": "1000 Degrees Pizza",
    "boro": "MANHATTAN",
    "building": "123",
    "street": "BROADWAY",
    "zipcode": "10007",
    "cuisine_description": "Pizza",
    "inspection_date": "2026-08-27T00:00:00.000",
    "action": "Violations were cited in the following area(s).",
    "violation_code": "04L",
    "violation_description": "Food not protected during storage, preparation, display, transportation and service",
    "critical_flag": "CRITICAL",
    "score": "13",
    "grade": "A",
    "grade_date": "2026-08-27T00:00:00.000",
    "record_date": "2026-08-28T00:00:00.000",
    "inspection_type": "Cycle Inspection / Initial Inspection",
    "latitude": "40.7128",
    "longitude": "-74.0060",
    "location": {"type": "Point", "coordinates": [-74.0060, 40.7128]},
}


def test_nyc_inspection_parses_native_latlng():
    with patch.object(InspectionsProducer, "__init__", lambda self, bootstrap_servers=None: None):
        prod = InspectionsProducer()
        prod.spatial_indexer = __import__("src.spatial.h3_indexer", fromlist=["H3SpatialIndexer"]).H3SpatialIndexer()
        event = prod.parse_row(NYC_INSPECTION_ROW, city_id="nyc")
        assert event is not None
        assert event.inspection_id == "50051779"
        assert event.business_name == "1000 Degrees Pizza"
        assert event.borough == "MANHATTAN"
        assert event.address == "123 BROADWAY"
        assert event.zipcode == "10007"
        assert event.latitude == 40.7128
        assert event.longitude == -74.0060
        assert event.issued_date is not None
        assert event.h3_res9 is not None


def test_nyc_inspection_drops_zero_coords():
    with patch.object(InspectionsProducer, "__init__", lambda self, bootstrap_servers=None: None):
        prod = InspectionsProducer()
        bad = dict(NYC_INSPECTION_ROW)
        bad["latitude"] = "0"
        bad["longitude"] = "0"
        assert prod.parse_row(bad, city_id="nyc") is None


# ---------------------------------------------------------------------------
# Austin Code Complaint Cases (US-210) — Socrata, native lat/lng
# ---------------------------------------------------------------------------

AUSTIN_VIOLATION_ROW = {
    "case_id": "2025-005905 CC",
    "priority": "High",
    "status": "Open",
    "address": "2400 DORMARION LN",
    "house_number": "2400",
    "street_name": "DORMARION LN",
    "city": "AUSTIN",
    "state": "TX",
    "zip_code": "78745",
    "opened_date": "2026-08-15T00:00:00.000",
    "closed_date": None,
    "department": "Code",
    "case_type": "Zoning",
    "description": "Unpermitted construction",
    "latitude": "30.2100",
    "longitude": "-97.7700",
    "location": {"type": "Point", "coordinates": [-97.7700, 30.2100]},
}


def test_austin_violation_parses_native_latlng():
    with patch.object(ViolationsProducer, "__init__", lambda self, bootstrap_servers=None: None):
        prod = ViolationsProducer()
        prod.spatial_indexer = __import__("src.spatial.h3_indexer", fromlist=["H3SpatialIndexer"]).H3SpatialIndexer()
        event = prod.parse_row(AUSTIN_VIOLATION_ROW, city_id="austin")
        assert event is not None
        assert event.violation_id == "2025-005905 CC"
        assert event.code == "Zoning"
        assert event.status == "Open"
        assert event.description == "Unpermitted construction"
        assert event.latitude == 30.2100
        assert event.longitude == -97.7700
        assert event.status_date is not None
        assert event.h3_res9 is not None


def test_austin_violation_drops_missing_coords():
    with patch.object(ViolationsProducer, "__init__", lambda self, bootstrap_servers=None: None):
        prod = ViolationsProducer()
        bad = dict(AUSTIN_VIOLATION_ROW)
        bad.pop("latitude")
        bad.pop("longitude")
        assert prod.parse_row(bad, city_id="austin") is None


# ---------------------------------------------------------------------------
# Maricopa County Sales Affidavits (US-392) — pipe-delimited CSV, DEEDS
# ---------------------------------------------------------------------------

def test_phoenix_registers_deeds_csv():
    from src.spatial.city_registry import REGISTRY, CityId, FeedType, get_dataset

    reg = REGISTRY[CityId.PHOENIX]
    assert FeedType.DEEDS in reg.datasets
    spec = get_dataset(CityId.PHOENIX, FeedType.DEEDS)
    assert spec.platform == "csv"
    assert spec.delimiter == "|"
    assert spec.zip_member == "Sales_Affidavits.txt"
    assert spec.ingestion_mode == "snapshot"
    assert spec.watermark_col == ""
    assert spec.id_keys == ["PARCELNUMBER", "DEEDNUMBER"]


def test_maricopa_field_map_targets():
    from src.producers.field_maps_maricopa_deeds import MARICOPA_DEEDS_FIELD_MAP

    assert MARICOPA_DEEDS_FIELD_MAP["doc_id"] == ["DEEDNUMBER", "PARCELNUMBER"]
    assert MARICOPA_DEEDS_FIELD_MAP["document_amount"] == ["SALEPRICE"]
    assert MARICOPA_DEEDS_FIELD_MAP["recorded_date"] == ["DEEDDATE_MMDDYYYY"]
    assert MARICOPA_DEEDS_FIELD_MAP["address_street"] == ["SITUSADDRESS"]
