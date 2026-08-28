"""Unit tests for the Las Cruces, NM leaf (US-240): spatial module + field
maps + producer parse wiring.

Las Cruces is a TWO-FEED PARTIAL metro: BuildingPermits (ArcGIS Server
MapServer/1 at ``maps.las-cruces.org``, Tier 1, ~82k rows, native WKID 4326
point geometry, ``Issued_Date`` watermark) and Business_Registrations
(MapServer/2, Tier 2, ~26k rows, native WKID 4326 point geometry,
``LastUpdateDate`` watermark). CertificateOFoccupancy (MapServer/3) is
available but not registered. 311 (Tyler Portico) and deeds (county parcel
data) stay Tier 3.

Tests pass WITHOUT a spine registration (no CityId.LAS_CRUCES, no REGISTRY
assertions — ``city_id="las_cruces"`` strings only). Spine-stable per the
wave-5 leaf contract: no division/borough-resolution assertions and no
geocode-hook call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28: BuildingPermits from MapServer/1
(``orderByFields=Issued_Date DESC, outSR=4326``; newest watermark
``1787292000000`` = 2026-08-20T06:00:00+00:00); Business_Registrations from
MapServer/2 (``orderByFields=LastUpdateDate DESC``; newest watermark same
date). Fixtures are RAW ArcGIS features (attributes + geometry); tests run
the real ``ArcGISClient._flatten_feature`` lift before parsing.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_las_cruces import (
    BUSREG_FIELD_MAP,
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.las_cruces import (
    LAS_CRUCES_CITY_ID,
    LAS_CRUCES_DIVISION_BBOXES,
    LAS_CRUCES_DIVISIONS,
    LAS_CRUCES_FEED_SPECS,
    LAS_CRUCES_GEOCODE_CONTEXT,
    LAS_CRUCES_METRO_BBOX,
    LAS_CRUCES_SUBMARKETS,
    REGISTRATION,
    get_las_cruces_dataset,
    is_in_greater_las_cruces_metro,
    is_in_las_cruces_metro,
)


def _flatten(feature: dict, date_fields: set | None = None) -> dict:
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, date_fields or set())


# ---------------------------------------------------------------------------
# BuildingPermits fixtures (MapServer/1, newest Issued_Date 2026-08-20)
# ---------------------------------------------------------------------------

_PERMIT_FEATURE_1 = {
    "attributes": {
        "Permit_Type": "FIRE SPRINKLER",
        "Permit_Number": "26CB3003527",
        "Permit_Location": "2360 E LOHMAN AVE",
        "Project": "COMMERCIAL",
        "Project_Valuation": 0,
        "Contractor_Business_Name": "A-1 NATIONAL FIRE CO LLC",
        "Contractor_Name": "BRYAN L BUNDRANT",
        "IssueMonthNo": 8,
        "Issued_Month": "AUG",
        "Issue_Year": 2026,
        "Issued_Date": 1787292000000,
        "Owner_Name": "MEXSAN LLC WAL-MART PROPERTY TAX DEPT",
        "Proposed_Use": "",
        "PropUseGrp": "",
        "RecTypeGrp": "OTHER",
        "recTypeOrd": 4,
        "Total_SQFT": 0,
        "PSFEE": 0,
        "PAFEE": 0,
        "UTFEE": 0,
        "CDFEE": 130,
        "TotalFeeInvoiced": 130,
        "X": -106.7486828,
        "Y": 32.31190886,
        "Zoning": "C-3",
        "OBJECTID": 81063,
    },
    "geometry": {"x": -106.74868279999998, "y": 32.311908860000074},
}

_PERMIT_FEATURE_2 = {
    "attributes": {
        "Permit_Type": "ELECTRICAL",
        "Permit_Number": "26OC6504612",
        "Permit_Location": "221 N MAIN ST",
        "Project": "COMMERCIAL",
        "Project_Valuation": 0,
        "Contractor_Business_Name": "RAD ELECTRIC INC",
        "Contractor_Name": "DUSTIN J RICO",
        "IssueMonthNo": 8,
        "Issued_Month": "AUG",
        "Issue_Year": 2026,
        "Issued_Date": 1787292000000,
        "Owner_Name": "BLEIWEISS GAIL ANNETTE TRUSTEE",
        "Proposed_Use": "",
        "PropUseGrp": "",
        "RecTypeGrp": "OTHER",
        "recTypeOrd": 4,
        "Total_SQFT": 0,
        "PSFEE": 0,
        "PAFEE": 0,
        "UTFEE": 0,
        "CDFEE": 130,
        "TotalFeeInvoiced": 130,
        "X": -106.77908581,
        "Y": 32.31094426,
        "Zoning": "DDC-MS",
        "OBJECTID": 82138,
    },
    "geometry": {"x": -106.77908580999997, "y": 32.31094426000004},
}

_PERMIT_FEATURE_3 = {
    "attributes": {
        "Permit_Type": "NA",
        "Permit_Number": "26SO10604641",
        "Permit_Location": "1442 CABIN CREEK AVE",
        "Project": "SOLAR PHOTO VOLTAIC SYSTEM",
        "Project_Valuation": 15404,
        "Contractor_Business_Name": "AC SOLAR & ELECTRIC LLC",
        "Contractor_Name": "ALEXANDER RIVERA CARDONE",
        "IssueMonthNo": 8,
        "Issued_Month": "AUG",
        "Issue_Year": 2026,
        "Issued_Date": 1787292000000,
        "Owner_Name": "Glenn Lively",
        "Proposed_Use": "",
        "PropUseGrp": "",
        "RecTypeGrp": "PV SYSTEM",
        "recTypeOrd": 3,
        "Total_SQFT": 0,
        "PSFEE": 0,
        "PAFEE": 0,
        "UTFEE": 0,
        "CDFEE": 305,
        "TotalFeeInvoiced": 305,
        "X": -106.76552711,
        "Y": 32.37486495,
        "Zoning": "R-1A",
        "OBJECTID": 82167,
    },
    "geometry": {"x": -106.76552710999994, "y": 32.374864950000074},
}

_PERMIT_DATE_ISO = "2026-08-21T06:00:00+00:00"
_PERMIT_FIXTURES = (_PERMIT_FEATURE_1, _PERMIT_FEATURE_2, _PERMIT_FEATURE_3)

# ---------------------------------------------------------------------------
# Business_Registrations fixtures (MapServer/2, newest LastUpdateDate)
# ---------------------------------------------------------------------------

_BUSREG_FEATURE_1 = {
    "attributes": {
        "PARENT_RECORD_ID_": "11757-25",
        "CannabisFlag": "",
        "OBJECTID": 994,
        "RECNO": "11757-25-REN-001",
        "BDGSQFT": 2500,
        "BRTotSqft": 2500,
        "BusCat": "COMMERCIAL BUSINESS",
        "BUSINESS_NAME": None,
        "BusTaxType": "LLC",
        "BusType": "RENTAL",
        "ContactName": "JEFF ANDERSON",
        "CRS": "03-271062-003",
        "DBA": "SUNNY ACRES RV PARK, LLC",
        "EmpVal": 8,
        "HOSQFT": None,
        "IssueMonth": 8,
        "IssueYear": 2026,
        "LastUpdateDate": 1787292000000,
        "LicExist": None,
        "MailAddress": "595 N VALLEY DR BOX 73LAS CRUCES, NM 88005",
        "MOBILESQFT": None,
        "NAICS": None,
        "Phone": "575-524-1716",
        "RecAddress": "595 N VALLEY DR, #73, LAS CRUCES, NM ",
        "Recipient": None,
        "RECNAME": "Sunny Acres RV Park, LLC",
        "RECORD_STATUS": "RENEWAL",
        "RECORD_TYPE": "Business Registration License Renewal",
        "RECORD_TYPE_SUBTYPE": "BUSINESS REGISTRATION",
        "RECORD_TYPE_TYPE": "Business",
        "RECORD_TYPESystem": "Business Registration License Renewal",
        "RESSQFT": None,
        "rptGrpBusCat": "ON-SITE BUSINESS",
        "SQBUSTYPE": "BUS SITE",
        "STATUS": "Renewed",
        "STATUSSystem": "Renewed",
        "TEMPLATE_ID": "REC26/00000/008EB",
        "TOTAL_INVOICED": 45,
        "TOTAL_PAID": 45,
        "TotalSQFT": None,
        "TotBldgFoot": None,
        "TRADE_NAME": None,
        "X": -106.79796866,
        "Y": 32.31089128,
        "PROJSQFT": None,
        "MonthCount": 205,
        "YearCount": 2787,
        "Email": "jandaendeavors@reagan.com",
    },
    "geometry": {"x": -106.79800000041723, "y": 32.31089999899268},
}

_BUSREG_FEATURE_2 = {
    "attributes": {
        "PARENT_RECORD_ID_": "24826-25",
        "CannabisFlag": "",
        "OBJECTID": 11367,
        "RECNO": "24826-25-REN-001",
        "BDGSQFT": 4000,
        "BRTotSqft": 4000,
        "BusCat": "COMMERCIAL BUSINESS",
        "BUSINESS_NAME": None,
        "BusTaxType": "LLC",
        "BusType": "RETAIL",
        "ContactName": "LAURA MENDOZA",
        "CRS": "03-583411-000",
        "DBA": "DULCERIA LA MEXICANA",
        "EmpVal": 2,
        "HOSQFT": None,
        "IssueMonth": 8,
        "IssueYear": 2026,
        "LastUpdateDate": 1787292000000,
        "LicExist": None,
        "MailAddress": "3524 ALAMEDA AVEEL PASO, TX 79905",
        "MOBILESQFT": None,
        "NAICS": None,
        "Phone": "915-329-8002",
        "RecAddress": "2217 MISSOURI AVE, LAS CRUCES, NM ",
        "Recipient": None,
        "RECNAME": "DULCERIA LA MEXICANA",
        "RECORD_STATUS": "RENEWAL",
        "RECORD_TYPE": "Business Registration License Renewal",
        "RECORD_TYPE_SUBTYPE": "BUSINESS REGISTRATION",
        "RECORD_TYPE_TYPE": "Business",
        "RECORD_TYPESystem": "Business Registration License Renewal",
        "RESSQFT": None,
        "rptGrpBusCat": "ON-SITE BUSINESS",
        "SQBUSTYPE": "BUS SITE",
        "STATUS": "Renewed",
        "STATUSSystem": "Renewed",
        "TEMPLATE_ID": "REC26/00000/008DZ",
        "TOTAL_INVOICED": 90,
        "TOTAL_PAID": 90,
        "TotalSQFT": None,
        "TotBldgFoot": None,
        "TRADE_NAME": None,
        "X": -106.74696149,
        "Y": 32.29812291,
        "PROJSQFT": None,
        "MonthCount": 205,
        "YearCount": 2787,
        "Email": "lauramendoza329@yahoo.com",
    },
    "geometry": {"x": -106.7470000013709, "y": 32.298099998384714},
}

_BUSREG_FEATURE_3 = {
    "attributes": {
        "PARENT_RECORD_ID_": "26008-25",
        "CannabisFlag": "",
        "OBJECTID": 12538,
        "RECNO": "26008-25-REN-001",
        "BDGSQFT": 17000,
        "BRTotSqft": 17000,
        "BusCat": "COMMERCIAL BUSINESS",
        "BUSINESS_NAME": None,
        "BusTaxType": "LLC",
        "BusType": "LODGING",
        "ContactName": "ANDI ADRIANO",
        "CRS": "03-625750-008",
        "DBA": "RIO GRANDE HOSPITALITY LLC",
        "EmpVal": 20,
        "HOSQFT": None,
        "IssueMonth": 8,
        "IssueYear": 2026,
        "LastUpdateDate": 1787292000000,
        "LicExist": None,
        "MailAddress": "2120 SUMMIT CT.LAS CRUCES, NM 88011",
        "MOBILESQFT": None,
        "NAICS": None,
        "Phone": "575-800-4840",
        "RecAddress": "2120 SUMMIT CT, LAS CRUCES, NM 88011",
        "Recipient": None,
        "RECNAME": "Motel 6 Las Cruces",
        "RECORD_STATUS": "RENEWAL",
        "RECORD_TYPE": "Business Registration License Renewal",
        "RECORD_TYPE_SUBTYPE": "BUSINESS REGISTRATION",
        "RECORD_TYPE_TYPE": "Business",
        "RECORD_TYPESystem": "Business Registration License Renewal",
        "RESSQFT": None,
        "rptGrpBusCat": "ON-SITE BUSINESS",
        "SQBUSTYPE": "BUS SITE",
        "STATUS": "Renewed",
        "STATUSSystem": "Renewed",
        "TEMPLATE_ID": "REC26/00000/008DI",
        "TOTAL_INVOICED": 35,
        "TOTAL_PAID": 35,
        "TotalSQFT": None,
        "TotBldgFoot": None,
        "TRADE_NAME": None,
        "X": -106.76334667,
        "Y": 32.342305,
        "PROJSQFT": None,
        "MonthCount": 205,
        "YearCount": 2787,
        "Email": "s63733bo@6franchise.com",
    },
    "geometry": {"x": -106.76330000162125, "y": 32.34230000153184},
}

_BUSREG_DATE_ISO = "2026-08-21T06:00:00+00:00"
_BUSREG_FIXTURES = (_BUSREG_FEATURE_1, _BUSREG_FEATURE_2, _BUSREG_FEATURE_3)


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


_PREMISES = (
    "name",
    "borough",
    "lat",
    "lng",
    "zoom",
    "pitch",
    "base_lims",
    "capex",
    "permit_vel",
    "shift_ratio",
    "sla",
    "description",
    "city_id",
)


# ---------------------------------------------------------------------------
# Tests: spatial invariants
# ---------------------------------------------------------------------------


class TestLasCrucesSpatial:
    def test_city_id_constant_is_the_leaf_string(self):
        assert LAS_CRUCES_CITY_ID == "las_cruces"

    def test_metro_bbox_sanity(self):
        assert LAS_CRUCES_METRO_BBOX["min_lat"] < LAS_CRUCES_METRO_BBOX["max_lat"]
        assert LAS_CRUCES_METRO_BBOX["min_lng"] < LAS_CRUCES_METRO_BBOX["max_lng"]

    def test_is_in_las_cruces_metro_rejects_missing_coordinates(self):
        assert is_in_las_cruces_metro(None, None) is False
        assert is_in_las_cruces_metro(32.3120, None) is False
        assert is_in_las_cruces_metro(None, -106.7780) is False

    def test_is_in_las_cruces_metro_rejects_other_cities(self):
        assert is_in_las_cruces_metro(32.3158, -106.7555) is True  # LC proper
        assert is_in_las_cruces_metro(35.0844, -106.6505) is False  # ABQ
        assert is_in_las_cruces_metro(31.7619, -106.4850) is False  # El Paso
        assert is_in_las_cruces_metro(34.0007, -106.8988) is False  # Socorro

    def test_known_anchors_are_contained(self):
        assert is_in_las_cruces_metro(32.3120, -106.7780)  # Downtown Plaza
        assert is_in_las_cruces_metro(32.2775, -106.8000)  # Mesilla
        assert is_in_las_cruces_metro(32.2820, -106.7450)  # NMSU

    def test_live_permit_fixture_coordinates_are_contained(self):
        for feature in _PERMIT_FIXTURES:
            assert is_in_las_cruces_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_live_busreg_fixture_coordinates_are_contained(self):
        for feature in _BUSREG_FIXTURES:
            assert is_in_las_cruces_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in LAS_CRUCES_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= LAS_CRUCES_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= LAS_CRUCES_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= LAS_CRUCES_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= LAS_CRUCES_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in LAS_CRUCES_SUBMARKETS.items():
            bbox = LAS_CRUCES_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in LAS_CRUCES_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(LAS_CRUCES_SUBMARKETS)

    def test_submarkets_carry_the_las_cruces_city_id(self):
        assert {m.city_id for m in LAS_CRUCES_SUBMARKETS.values()} == {"las_cruces"}

    def test_city_id_and_registration_shape(self):
        assert LAS_CRUCES_CITY_ID == "las_cruces"
        assert REGISTRATION.metro_bbox is LAS_CRUCES_METRO_BBOX
        assert REGISTRATION.submarkets is LAS_CRUCES_SUBMARKETS
        assert REGISTRATION.division_bboxes is LAS_CRUCES_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_las_cruces_metro
        assert len(REGISTRATION.divisions) == 6
        assert len(LAS_CRUCES_SUBMARKETS) == 9

    def test_required_real_neighborhoods_present(self):
        assert set(LAS_CRUCES_SUBMARKETS) == {
            "Downtown Las Cruces",
            "Las Cruces Plaza",
            "Mesilla Historic District",
            "NMSU Corridor",
            "East Mesa Growth",
            "Sonoma Ranch",
            "Telshor/Medical District",
            "Las Colinas",
            "West Mesa",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_las_cruces_metro is is_in_las_cruces_metro

    def test_submarket_meta_fields_all_present(self):
        for name, meta in LAS_CRUCES_SUBMARKETS.items():
            for field in _PREMISES:
                value = getattr(meta, field)
                assert value is not None, f"{name}.{field}"

    def test_downtown_anchor(self):
        assert is_in_las_cruces_metro(32.3120, -106.7780)
        assert is_in_las_cruces_metro(32.3119, -106.7791)  # Main St
        assert is_in_las_cruces_metro(32.3050, -106.8500)  # West Mesa

    def test_divisions_have_correct_submarket_counts(self):
        assert len(LAS_CRUCES_DIVISIONS["DOWNTOWN_CORE"].submarkets) == 2
        assert len(LAS_CRUCES_DIVISIONS["MESILLA_VALLEY"].submarkets) == 1
        assert len(LAS_CRUCES_DIVISIONS["EAST_MESA"].submarkets) == 2
        assert len(LAS_CRUCES_DIVISIONS["SONOMA_RANCH"].submarkets) == 1
        assert len(LAS_CRUCES_DIVISIONS["NORTHERN_LC"].submarkets) == 2
        assert len(LAS_CRUCES_DIVISIONS["WEST_MESA"].submarkets) == 1


# ---------------------------------------------------------------------------
# Tests: field maps
# ---------------------------------------------------------------------------


class TestLasCrucesFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["Permit_Number", "OBJECTID"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["Issued_Date"]
        assert PERMITS_FIELD_MAP["job_type"] == ["Permit_Type"]
        assert PERMITS_FIELD_MAP["cost"] == ["Project_Valuation"]
        assert PERMITS_FIELD_MAP["address_street"] == ["Permit_Location"]

    def test_busreg_map_reads_live_columns(self):
        assert BUSREG_FIELD_MAP["license_id"] == ["RECNO", "OBJECTID"]
        assert BUSREG_FIELD_MAP["dba"] == ["DBA", "RECNAME"]
        assert BUSREG_FIELD_MAP["premises_name"] == ["RECNAME", "DBA"]
        assert BUSREG_FIELD_MAP["license_type"] == ["BusCat", "BusType"]
        assert BUSREG_FIELD_MAP["status"] == ["STATUS"]
        assert BUSREG_FIELD_MAP["effective_date"] == ["LastUpdateDate"]
        assert BUSREG_FIELD_MAP["address_street"] == ["RecAddress"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP, "sla": BUSREG_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Las Cruces, NM"
        assert LAS_CRUCES_GEOCODE_CONTEXT == "Las Cruces, NM"

    def test_native_coordinates_not_in_field_map(self):
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP
        assert "latitude" not in BUSREG_FIELD_MAP
        assert "longitude" not in BUSREG_FIELD_MAP

    def test_no_borough_or_neighborhood_candidates(self):
        assert "borough" not in PERMITS_FIELD_MAP
        assert "neighborhood" not in PERMITS_FIELD_MAP
        assert "borough" not in BUSREG_FIELD_MAP
        assert "neighborhood" not in BUSREG_FIELD_MAP

    def test_pii_columns_never_become_candidates(self):
        for field_map in (PERMITS_FIELD_MAP, BUSREG_FIELD_MAP):
            mapped = {c for values in field_map.values() for c in values}
            assert mapped
            for values in field_map.values():
                for col in values:
                    assert col not in DROPPED_PII_COLUMNS

    def test_permit_fixture_first_mapped_field_access(self):
        attrs = _PERMIT_FEATURE_1["attributes"]
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "job_id") == "26CB3003527"
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "cost") is None  # 0 is falsy
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "address_street") == "2360 E LOHMAN AVE"

    def test_solar_fixture_cost_is_nonzero(self):
        attrs = _PERMIT_FEATURE_3["attributes"]
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "cost") == 15404

    def test_busreg_fixture_first_mapped_field_access(self):
        attrs = _BUSREG_FEATURE_1["attributes"]
        assert first_mapped(attrs, BUSREG_FIELD_MAP, "license_id") == "11757-25-REN-001"
        assert first_mapped(attrs, BUSREG_FIELD_MAP, "dba") == "SUNNY ACRES RV PARK, LLC"
        assert first_mapped(attrs, BUSREG_FIELD_MAP, "status") == "Renewed"

    def test_x_y_attributes_are_wgs84_decimals(self):
        attrs = _PERMIT_FEATURE_1["attributes"]
        assert -107 < attrs["X"] < -106  # WGS84 lng for LC
        assert 32 < attrs["Y"] < 33  # WGS84 lat for LC
        geo = _PERMIT_FEATURE_1["geometry"]
        assert abs(attrs["X"] - geo["x"]) < 0.001  # same CRS
        assert abs(attrs["Y"] - geo["y"]) < 0.001


# ---------------------------------------------------------------------------
# Tests: permit producer parsing
# ---------------------------------------------------------------------------


class TestLasCrucesPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_PERMIT_FEATURE_1, {"Issued_Date"})
        assert record["latitude"] == pytest.approx(32.311908860000074)
        assert record["longitude"] == pytest.approx(-106.74868279999998)

    def test_flatten_iso_normalizes_the_watermark(self):
        record = _flatten(_PERMIT_FEATURE_2, {"Issued_Date"})
        assert record["Issued_Date"] == _PERMIT_DATE_ISO

    def test_sprinkler_fixture_parses_through_the_producer(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_PERMIT_FEATURE_1, {"Issued_Date"})
        event = permits.parse_socrata_row(record, city_id="las_cruces")
        assert event is not None
        assert event.city_id == "las_cruces"
        assert event.job_id == "26CB3003527"
        assert event.job_type == JobType.OT  # FIRE SPRINKLER → OT
        assert event.address_street == "2360 E LOHMAN AVE"
        assert event.latitude == pytest.approx(32.311908860000074)
        assert event.longitude == pytest.approx(-106.74868279999998)
        assert event.issuance_date is not None

    def test_electrical_fixture_parses_h3_and_sits_in_metro(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_PERMIT_FEATURE_2, {"Issued_Date"})
        event = permits.parse_socrata_row(record, city_id="las_cruces")
        assert event is not None
        assert event.job_id == "26OC6504612"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_las_cruces_metro(event.latitude, event.longitude)

    def test_solar_fixture_valuation_and_containment(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_PERMIT_FEATURE_3, {"Issued_Date"})
        event = permits.parse_socrata_row(record, city_id="las_cruces")
        assert event is not None
        assert event.job_id == "26SO10604641"
        assert event.estimated_cost == pytest.approx(15404.0)
        assert event.address_street == "1442 CABIN CREEK AVE"
        assert is_in_las_cruces_metro(event.latitude, event.longitude)

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_PERMIT_FEATURE_1, {"Issued_Date"})
        record.pop("Permit_Number")
        event = permits.parse_socrata_row(record, city_id="las_cruces")
        assert event is not None
        assert event.job_id == "81063"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_PERMIT_FEATURE_1, {"Issued_Date"})
        record.pop("Permit_Number")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="las_cruces") is None


# ---------------------------------------------------------------------------
# Tests: SLA producer parsing
# ---------------------------------------------------------------------------


class TestLasCrucesSLAParsing:
    @pytest.fixture
    def sla_producer(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_flatten_lifts_busreg_geometry(self):
        record = _flatten(_BUSREG_FEATURE_1, {"LastUpdateDate"})
        assert "latitude" in record
        assert "longitude" in record
        assert record["LastUpdateDate"] == _BUSREG_DATE_ISO

    def test_rv_park_fixture_parses_through_sla_producer(self, sla_producer, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten(_BUSREG_FEATURE_1, {"LastUpdateDate"})
        event = sla_producer.parse_socrata_row(record, city_id="las_cruces")
        assert event is not None
        assert event.city_id == "las_cruces"
        assert event.license_id == "11757-25-REN-001"
        assert event.dba == "SUNNY ACRES RV PARK, LLC"
        assert event.premises_name == "Sunny Acres RV Park, LLC"
        assert event.license_type == "COMMERCIAL BUSINESS"
        assert event.license_status == "Renewed"
        assert event.address == "595 N VALLEY DR, #73, LAS CRUCES, NM "
        assert event.effective_date is not None

    def test_dulceria_fixture_parses_and_lands_in_metro(self, sla_producer, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten(_BUSREG_FEATURE_2, {"LastUpdateDate"})
        event = sla_producer.parse_socrata_row(record, city_id="las_cruces")
        assert event is not None
        assert event.license_id == "24826-25-REN-001"
        assert event.dba == "DULCERIA LA MEXICANA"
        assert is_in_las_cruces_metro(event.latitude, event.longitude)

    def test_motel_fixture_parses_with_h3_and_metro(self, sla_producer, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten(_BUSREG_FEATURE_3, {"LastUpdateDate"})
        event = sla_producer.parse_socrata_row(record, city_id="las_cruces")
        assert event is not None
        assert event.license_id == "26008-25-REN-001"
        assert event.dba == "RIO GRANDE HOSPITALITY LLC"
        assert event.premises_name == "Motel 6 Las Cruces"
        assert event.h3_res9 is not None
        assert is_in_las_cruces_metro(event.latitude, event.longitude)

    def test_license_id_falls_back_to_objectid(self, sla_producer, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten(_BUSREG_FEATURE_1, {"LastUpdateDate"})
        record.pop("RECNO")
        event = sla_producer.parse_socrata_row(record, city_id="las_cruces")
        assert event is not None
        assert event.license_id == "994"

    def test_feed_specs_contain_both_feeds(self):
        assert "permits" in LAS_CRUCES_FEED_SPECS
        assert "sla" in LAS_CRUCES_FEED_SPECS
        assert len(LAS_CRUCES_FEED_SPECS) == 2

    def test_get_dataset_returns_spec_for_valid_feed(self):
        from src.spatial.city_registry import FeedType

        ds = get_las_cruces_dataset(FeedType.PERMITS)
        assert ds is not None
        assert ds.endpoint == LAS_CRUCES_FEED_SPECS["permits"]["endpoint"]
        assert ds.platform == "arcgis"
        assert ds.watermark_col == "Issued_Date"

    def test_get_dataset_raises_for_absent_feed(self):
        from src.spatial.city_registry import FeedType

        with pytest.raises(KeyError) as exc:
            get_las_cruces_dataset(FeedType.COMPLAINTS_311)
        assert "las_cruces" in str(exc.value)
        assert "permits" in str(exc.value)