"""Unit tests for the Medford, OR leaf (US-238): spatial module + field
maps + producer parse wiring.

Medford is a THREE-FEED PARTIAL metro on the city's ArcGIS Server 12.1
(``maps.medfordmaps.org``), fed by the TRAKiT Community Development database:

* **PERMITS** — ``TRAKiTExport/TRAKiTPermits_service/FeatureServer/1``
  (~59k rows, daily). Native point geometry (store SR WKID 2270 OR State
  Plane North feet; outSR=4326 lift); ``ISSUED`` watermark.
* **SLA** — ``MLI2/MLI_TRAKiT_Service/FeatureServer/14`` License2_Main
  (~29.6k rows, 6,594 ACTIVE). A Table — no geometry, geocode supplement
  on ``SITE_ADDR`` (ADR 0004); ``ISSUED`` watermark.
* **COMPLAINTS_311** — ``MLI2/MLI_TRAKiT_Service/FeatureServer/12``
  Case_Main code-enforcement cases (~83.7k rows). A Table — no geometry,
  geocode supplement on ``SITE_ADDR``; ``STARTED`` watermark.

Tests pass WITHOUT a spine registration (no CityId.MEDFORD, no REGISTRY
assertions — "medford" stays a plain string). Spine-stable per the
wave-leaf contract: no division/borough-resolution assertions and no
geocode-hook call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from the three layers (newest
rows via ``orderByFields=<watermark> DESC`` at ``outSR=4326`` for permits;
newest license ISSUED = 2026-08-28, newest case STARTED = 2026-08-28).
Fixtures are RAW ArcGIS features (attributes + geometry); the tests run the
real ``ArcGISClient._flatten_feature`` lift — geometry to latitude/longitude,
epoch-ms to ISO — before parsing, exactly as the live producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps_medford import (
    CASE_FIELD_MAP,
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.medford import (
    MEDFORD_CASES_ENDPOINT,
    MEDFORD_CITY_ID,
    MEDFORD_DIVISION_BBOXES,
    MEDFORD_DIVISIONS,
    MEDFORD_FEED_SPECS,
    MEDFORD_GEOCODE_CONTEXT,
    MEDFORD_METRO_BBOX,
    MEDFORD_PERMITS_ENDPOINT,
    MEDFORD_SLA_ENDPOINT,
    MEDFORD_SUBMARKETS,
    REGISTRATION,
    get_medford_dataset,
    is_in_greater_medford_metro,
    is_in_medford_metro,
)
from src.spatial.city_registry import FeedType

# Date fields per layer as discovered from live metadata (the client
# fetches these from each layer's /FeatureServer/<id>?f=json response).
_PERMIT_DATE_FIELDS = {"APPLIED", "APPROVED", "ISSUED", "FINALED", "EXPIRED", "OTHER_DATE1"}
_LICENSE_DATE_FIELDS = {
    "APPLIED",
    "EXPIRED",
    "ISSUED",
    "LIAB_EXP",
    "LIAB_ISS",
    "ST_LIC_EXP",
    "ST_LIC_ISS",
    "W_COMP_EXP",
    "W_COMP_ISS",
    "INVOICE_DATE",
}
_CASE_DATE_FIELDS = {"STARTED", "CLOSED", "LASTACTION", "FOLLOWUP", "OTHER_DATE1"}


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _flatten(feature, date_fields):
    """Run the real ArcGIS flatten lift over a raw captured feature."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, date_fields)


# ---------------------------------------------------------------------------
# Live fixtures (byte-verbatim, captured 2026-08-28).
# ---------------------------------------------------------------------------

# Newest permit by ISSUED DESC (outSR=4326) — BELE26-02927, electrical panel
# replacement on N Keene Way Dr (North Medford division).
_FEATURE_PERMIT = {
    "attributes": {
        "OBJECTID": 600843133,
        "Taxlots_MAPLOT": "371W17BB8100",
        "Taxlots_ACCOUNT": "10565645",
        "Taxlots_SITEADD": "2865 N KEENE WAY DR",
        "PERMIT_NO": "BELE26-02927",
        "PermitType": "ELECTRICAL",
        "PermitSubType": "RESIDENTIAL",
        "Taxlots_FEEOWNER": "PRICE F K/NELSON E DAVIDSON",
        "OWNER_NAME": "PRICE F K/NELSON E DAVIDSON",
        "APPLICANT_NAME": "CARLSON CORP / ACCURATE PLUMBING & ELEC",
        "CONTRACTOR_NAME": "CARLSON CORP / ACCURATE PLUMBING & ELEC",
        "STATUS": "ISSUED",
        "PREFIX": "BELE",
        "YRMO": 26,
        "APPLIED": 1787702400000,
        "APPLIED_BY": "KJR",
        "APPROVED": 1787702400000,
        "APPROVED_BY": "KJR",
        "ISSUED": 1787788800000,
        "ISSUED_BY": "KJR",
        "FINALED": None,
        "FINALED_BY": None,
        "EXPIRED": 1803340800000,
        "EXPIRED_BY": "KJR",
        "VALID_FOR": None,
        "PARENT_PROJECT_NO": None,
        "PARENT_PERMIT_NO": None,
        "SITE_LOT_NO": "20",
        "SITE_BLOCK": None,
        "SITE_TRACT": None,
        "SITE_SUBDIVISION": "Sandra J. Subdivision, Blk 1",
        "SITE_DESCRIPTION": "RESIDENCE",
        "TAX_RATE_AREA": None,
        "SCHOOL": None,
        "CENSUS": None,
        "FWDODGE": None,
        "SITE_APN": "371W17BB8100",
        "SITE_ADDR": "2865 N KEENE WAY DR",
        "SITE_NUMBER": "2865",
        "SITE_STREETID": None,
        "SITE_STREETNAME": "N KEENE WAY DR",
        "SITE_UNIT_NO": None,
        "SITE_CITY": "MEDFORD",
        "SITE_STATE": "OR",
        "SITE_ZIP": "97504",
        "SITE_ST_NO": None,
        "LOCATION_DESC": None,
        "DESCRIPTION": "REPLACE 200A PANEL",
        "NOTES": None,
        "LOT_SF": 0,
        "BLDG_SF": 0,
        "BLDG2_SF": 0,
        "GAR_SF": 0,
        "GAR2_SF2": 0,
        "PORCH_SF": 0,
        "PORCH2_SF": 0,
        "HEIGHT": 0,
        "NO_STORIES": 0,
        "NO_UNITS": None,
        "NO_BLDGS": 0,
        "JOBVALUE": 1900,
        "FEES_CHARGED": 151.54,
        "FEE_ADJUSTMENTS": None,
        "FEES_PAID": 151.54,
        "BALANCE_DUE": 0.0,
        "OTHER_DATE1": None,
        "OTHER_BY1": None,
        "SITE_ALTERNATE_ID": "ADD-033550",
        "SITE_GEOTYPE": "ADDRESS",
        "TSstatus": None,
    },
    "geometry": {"x": -122.85266606122694, "y": 42.35830498058966},
}

# Newest license by ISSUED DESC — BL24-00951, HOME BASED professional
# services on Brookdale Ave. Table (no geometry).
_FEATURE_LICENSE = {
    "attributes": {
        "BALANCE_DUE": 0,
        "CHECKBOX1": None,
        "CHECKBOX2": None,
        "CHECKBOX3": None,
        "CHECKBOX4": None,
        "CHECKBOX5": None,
        "CHECKBOX6": None,
        "CHECKBOX7": None,
        "CHECKBOX8": None,
        "COMPANY": "PROFESSIONAL SERVICES, LLC",
        "COMPANY_PRINT_AS": "PROFESSIONAL SERVICES, LLC",
        "DEFAULT_INSPECTOR": None,
        "DEPOSITTYPE": None,
        "EMAIL": "dodieklong@gmail.com",
        "EMERGENCY": "5419418153",
        "APPLIED": 1733097600000,
        "APPLIED_BY": "SLC",
        "EXPIRED": 1819756800000,
        "EXPIRED_BY": "SLC",
        "FAX": None,
        "FEES_CHARGED": 160,
        "FEES_PAID": 160,
        "HISTORICAL_APN": None,
        "ISSUED": 1787875200000,
        "ISSUED_BY": "SLC",
        "LIAB_CARRIER": None,
        "LIAB_EXP": None,
        "LIAB_ISS": None,
        "LIAB_NO": None,
        "LICENSE_NO": "BL24-00951",
        "LICENSE_SUBTYPE": "HOME BASED",
        "LICENSE_TYPE": "HOME BASED",
        "LOC_RECORDID": "CONV:1902281111290511455",
        "LOCKID": None,
        "MAIL_ADDRESS1": "1093 BROOKDALE AVE",
        "MAIL_ADDRESS2": None,
        "MAIL_CITY": "MEDFORD",
        "MAIL_STATE": "OR",
        "MAIL_ZIP": "97501",
        "MAINTEXTFIELD1": None,
        "MAINTEXTFIELD2": None,
        "MAINTEXTFIELD3": None,
        "MAINTEXTFIELD4": None,
        "MAINTEXTFIELD5": None,
        "MAINTEXTFIELD6": None,
        "MAINTEXTFIELD7": None,
        "MAINTEXTFIELD8": None,
        "NOTES": None,
        "OWNER_NAME": "LONG, DODIE",
        "PARENT_RECORDID": None,
        "PHONE": "9282317386",
        "PREFIX": "BL",
        "RECORDID": "SLC:2412020301412100",
        "REFERENCE_NO": None,
        "SEQ_NO": 951,
        "SIC_2": None,
        "SIC_3": None,
        "SITE_ALTERNATE_ID": "ADD-073947",
        "SITE_APN": "371W21BC2500",
        "SITE_BLOCK": None,
        "SITE_CITY": "MEDFORD",
        "SITE_DESCRIPTION": "Building",
        "SITE_GEOTYPE": "ADDRESS",
        "SITE_LOT_NO": None,
        "SITE_NUMBER": "1093",
        "SITE_STATE": "OR",
        "SITE_STREETID": None,
        "SITE_STREETNAME": "BROOKDALE AVE",
        "SITE_SUBDIVISION": None,
        "SITE_TRACT": None,
        "SITE_UNIT_NO": None,
        "SITE_ZIP": "97504",
        "ST_LIC_EXP": None,
        "ST_LIC_ISS": None,
        "STATUS": "ACTIVE",
        "STATUS_BY": "SLC",
        "TAG": None,
        "TEXTFIELD1": None,
        "TEXTFIELD2": None,
        "TEXTFIELD3": None,
        "TEXTFIELD4": None,
        "TEXTFIELD5": None,
        "TEXTFIELD6": None,
        "TEXTFIELD7": None,
        "TEXTFIELD8": None,
        "W_COMP_EXP": None,
        "W_COMP_ISS": None,
        "W_COMP_NO": None,
        "WRKR_COMP": None,
        "YRMO": 24,
        "SITE_ADDR": "1093 BROOKDALE AVE",
        "OWNERSHIP_TYPE": None,
        "RESALE_ID": None,
        "SIC_1": None,
        "INVOICE_DATE": None,
        "PHONE_EXT": None,
        "TSstatus": None,
        "ActivityTypeID": 3,
        "TAX_ID": None,
        "Unique_Key": None,
        "RowNum": 27689,
    }
}

# Newest case by STARTED DESC — CE26-02274, right-of-way obstruction on
# Viewpoint Dr. Table (no geometry). LASTACTION is future-dated
# (1788307200000 = 2026-09-02) — never the watermark.
_FEATURE_CASE = {
    "attributes": {
        "PREFIX": "CE",
        "YRMO": 26,
        "SEQ_NO": 2274,
        "CASE_NO": "CE26-02274",
        "CASE_NAME": None,
        "STARTED": 1787875200000,
        "STARTED_BY": "DMA",
        "CLOSED": None,
        "CLOSED_BY": None,
        "LASTACTION": 1788307200000,
        "LASTACTION_BY": "DMA",
        "FOLLOWUP": 1788307200000,
        "FOLLOWUP_BY": "DMA",
        "RECEIVED_BY": None,
        "HOW_RECEIVED": None,
        "CaseType": "OBSTRUCTION IN RIGHT OF WAY",
        "CaseSubType": "LANDSCAPE SUPPLIES",
        "CASE_LOCATION": None,
        "SITE_APN": "371W16BA8904",
        "SITE_STREETID": None,
        "SITE_NUMBER": "3366",
        "SITE_STREETNAME": "VIEWPOINT DR",
        "SITE_UNIT_NO": None,
        "SITE_CITY": "MEDFORD",
        "SITE_STATE": "OR",
        "SITE_ZIP": "97504",
        "SITE_LOT_NO": "20",
        "SITE_BLOCK": None,
        "SITE_TRACT": None,
        "SITE_SUBDIVISION": "Hidden Hills Subdivision Ph 2",
        "SITE_DESCRIPTION": "RESIDENCE",
        "SITE_ADDR": "3366 VIEWPOINT DR",
        "CODE_SECTION": None,
        "DESCRIPTION": None,
        "ASSIGNED_TO": "Vivian Lopez",
        "REFERRED_TO": "Email",
        "STATUS": "ACTIVE",
        "FEES_CHARGED": 0,
        "FEES_PAID": 0,
        "BALANCE_DUE": 0,
        "PARENT_PROJECT_NO": None,
        "OTHER_DATE1": None,
        "OTHER_BY1": None,
        "OWNER_NAME": "ELEGANT CUSTOM HOMES LLC",
        "RESIDENT_NAME": None,
        "COMPLAINANT_NAME": None,
        "RECORDID": "DMA:2608281217591299",
        "LOCKID": None,
        "LOC_RECORDID": "GTUR:2412030600131178732",
        "DEPOSITTYPE": None,
        "HISTORICAL_APN": None,
        "PARENT_PERMIT_NO": None,
        "PARENT_BUS_LIC_NO": None,
        "REFERENCE_NO": None,
        "SITE_ALTERNATE_ID": "ADD-153754",
        "SITE_GEOTYPE": "ADDRESS",
        "Parent_Generic1_ActivityNo": None,
        "Parent_Generic2_ActivityNo": None,
        "Parent_Generic3_ActivityNo": None,
        "Parent_Generic4_ActivityNo": None,
        "Parent_Generic5_ActivityNo": None,
        "TSstatus": None,
        "ActivityTypeID": 4,
        "Unique_Key": None,
        "RowNum": 83677,
    }
}

_PERMIT_ISSUED_ISO = "2026-08-27T00:00:00+00:00"
_LICENSE_ISSUED_ISO = "2026-08-28T00:00:00+00:00"
_CASE_STARTED_ISO = "2026-08-28T00:00:00+00:00"


class TestMedfordSpatial:
    def test_metro_bbox_sanity(self):
        assert MEDFORD_METRO_BBOX["min_lat"] < MEDFORD_METRO_BBOX["max_lat"]
        assert MEDFORD_METRO_BBOX["min_lng"] < MEDFORD_METRO_BBOX["max_lng"]

    def test_is_in_medford_metro_rejects_missing_coordinates(self):
        assert is_in_medford_metro(None, None) is False
        assert is_in_medford_metro(42.3266, None) is False
        assert is_in_medford_metro(None, -122.8756) is False

    def test_is_in_medford_metro_rejects_other_cities(self):
        assert is_in_medford_metro(45.5152, -122.6784) is False  # Portland
        assert is_in_medford_metro(42.1946, -122.7095) is False  # Ashland (south, outside)
        assert is_in_medford_metro(42.4367, -122.8563) is False  # White City (north, outside)
        assert is_in_medford_metro(43.3266, -122.8756) is False  # Oregon north of metro

    def test_downtown_anchors_are_contained(self):
        assert is_in_medford_metro(42.3266, -122.8756)  # Main St downtown core
        assert is_in_medford_metro(42.3418, -122.8786)  # Medford Center midtown
        assert is_in_medford_metro(42.3759, -122.9162)  # Central Point

    def test_live_fixture_coordinates_are_contained(self):
        assert is_in_medford_metro(
            _FEATURE_PERMIT["geometry"]["y"], _FEATURE_PERMIT["geometry"]["x"]
        )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in MEDFORD_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= MEDFORD_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= MEDFORD_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= MEDFORD_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= MEDFORD_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in MEDFORD_SUBMARKETS.items():
            bbox = MEDFORD_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in MEDFORD_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(MEDFORD_SUBMARKETS)

    def test_submarkets_carry_the_medford_city_id(self):
        assert {m.city_id for m in MEDFORD_SUBMARKETS.values()} == {"medford"}

    def test_city_id_and_registration_shape(self):
        assert MEDFORD_CITY_ID == "medford"
        assert REGISTRATION.metro_bbox is MEDFORD_METRO_BBOX
        assert REGISTRATION.submarkets is MEDFORD_SUBMARKETS
        assert REGISTRATION.division_bboxes is MEDFORD_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_medford_metro
        assert len(REGISTRATION.divisions) == 8
        assert len(MEDFORD_SUBMARKETS) == 11

    def test_required_real_neighborhoods_present(self):
        assert set(MEDFORD_SUBMARKETS) == {
            "Downtown",
            "Medford Center",
            "East Medford",
            "McAndrews Corridor",
            "South Medford",
            "Stewart Meadows",
            "North Medford",
            "Airport Edge",
            "Riverside",
            "Central Point",
            "Jacksonville",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_medford_metro is is_in_medford_metro


class TestMedfordFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["PERMIT_NO", "OBJECTID"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["ISSUED"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["APPLIED"]
        assert PERMITS_FIELD_MAP["status"] == ["STATUS"]
        assert PERMITS_FIELD_MAP["job_type"] == ["PermitType"]
        assert PERMITS_FIELD_MAP["cost"] == ["JOBVALUE"]
        assert PERMITS_FIELD_MAP["address_street"] == ["SITE_ADDR"]
        assert PERMITS_FIELD_MAP["zipcode"] == ["SITE_ZIP"]
        assert PERMITS_FIELD_MAP["bbl"] == ["SITE_APN"]
        assert PERMITS_FIELD_MAP["borough"] == ["SITE_CITY"]

    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["LICENSE_NO"]
        assert SLA_FIELD_MAP["dba"] == ["COMPANY"]
        assert SLA_FIELD_MAP["premises_name"] == ["COMPANY"]
        assert SLA_FIELD_MAP["license_type"] == ["LICENSE_TYPE"]
        assert SLA_FIELD_MAP["status"] == ["STATUS"]
        assert SLA_FIELD_MAP["effective_date"] == ["ISSUED"]
        assert SLA_FIELD_MAP["expiration_date"] == ["EXPIRED"]
        assert SLA_FIELD_MAP["address_street"] == ["SITE_ADDR"]
        assert SLA_FIELD_MAP["zipcode"] == ["SITE_ZIP"]
        assert SLA_FIELD_MAP["borough"] == ["SITE_CITY"]
        assert SLA_FIELD_MAP["bbl"] == ["SITE_APN"]

    def test_case_map_reads_live_columns(self):
        assert CASE_FIELD_MAP["incident_id"] == ["CASE_NO"]
        assert CASE_FIELD_MAP["complaint_type"] == ["CaseType"]
        assert CASE_FIELD_MAP["status"] == ["STATUS"]
        assert CASE_FIELD_MAP["created_date"] == ["STARTED"]
        assert CASE_FIELD_MAP["closed_date"] == ["CLOSED"]
        assert CASE_FIELD_MAP["incident_address"] == ["SITE_ADDR"]
        assert CASE_FIELD_MAP["zipcode"] == ["SITE_ZIP"]
        assert CASE_FIELD_MAP["borough"] == ["SITE_CITY"]
        assert CASE_FIELD_MAP["bbl"] == ["SITE_APN"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {
            "permits": PERMITS_FIELD_MAP,
            "sla": SLA_FIELD_MAP,
            "311": CASE_FIELD_MAP,
        }
        assert GEOCODE_CONTEXT == "Medford, OR"
        assert MEDFORD_GEOCODE_CONTEXT == "Medford, OR"

    def test_tables_declare_no_coordinate_candidates(self):
        """SLA and 311 feeds are Tables (no geometry); coordinates come only
        from the ADR-0004 geocode supplement, so no latitude/longitude map
        candidates may exist on those maps."""
        for feed_map in (SLA_FIELD_MAP, CASE_FIELD_MAP):
            assert "latitude" not in feed_map
            assert "longitude" not in feed_map

    def test_permits_layer_has_native_geometry_so_no_coord_candidates(self):
        """The permit layer is a point FeatureServer; coordinates come from
        the outSR=4326 geometry lift (store SR is OR State Plane North
        feet, WKID 2270), never from attribute columns."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP

    def test_lastaction_is_never_a_candidate(self):
        """LASTACTION carries future-dated sentinels (2026-09-02 on the
        probe fixture) — it must never become a created_date candidate."""
        assert "LASTACTION" not in [
            c for values in CASE_FIELD_MAP.values() for c in values
        ]

    def test_pii_columns_never_become_candidates(self):
        mapped = {
            c for values in FIELD_MAP.values() for column_list in values.values() for c in column_list
        }
        assert mapped
        for values in FIELD_MAP.values():
            for column_list in values.values():
                for col in column_list:
                    assert col not in DROPPED_PII_COLUMNS
        # The owner/complainant/mailing/contact blocks are exactly what is dropped.
        assert {"OWNER_NAME", "COMPLAINANT_NAME", "EMAIL", "PHONE", "FAX",
                "MAIL_ADDRESS1", "RESIDENT_NAME"} <= set(DROPPED_PII_COLUMNS)


class TestMedfordPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_FEATURE_PERMIT, _PERMIT_DATE_FIELDS)
        assert record["latitude"] == pytest.approx(42.35830498058966)
        assert record["longitude"] == pytest.approx(-122.85266606122694)

    def test_flatten_iso_normalizes_the_watermark_only(self):
        record = _flatten(_FEATURE_PERMIT, _PERMIT_DATE_FIELDS)
        assert record["ISSUED"] == _PERMIT_ISSUED_ISO
        assert record["APPLIED"] == "2026-08-26T00:00:00+00:00"
        assert record["EXPIRED"] == "2027-02-23T00:00:00+00:00"
        assert record["FINALED"] is None

    def test_fixture_parses_through_the_producer(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            _flatten(_FEATURE_PERMIT, _PERMIT_DATE_FIELDS), city_id="medford"
        )
        assert event is not None
        assert event.city_id == "medford"
        assert event.job_id == "BELE26-02927"
        assert event.status == "ISSUED"
        assert event.job_type == JobType.A2  # ELECTRICAL contains "ELECTRIC"
        assert event.estimated_cost == pytest.approx(1900.0)
        assert event.address_street == "2865 N KEENE WAY DR"
        assert event.zipcode == "97504"
        assert event.bbl == "371W17BB8100"
        assert event.borough == "MEDFORD"
        assert event.source_neighborhood == "MEDFORD"
        assert event.latitude == pytest.approx(42.35830498058966)
        assert event.longitude == pytest.approx(-122.85266606122694)
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat() == _PERMIT_ISSUED_ISO
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert is_in_medford_metro(event.latitude, event.longitude)

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_PERMIT, _PERMIT_DATE_FIELDS)
        record.pop("PERMIT_NO")
        event = permits.parse_socrata_row(record, city_id="medford")
        assert event is not None
        assert event.job_id == "600843133"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_PERMIT, _PERMIT_DATE_FIELDS)
        record.pop("PERMIT_NO")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="medford") is None


class TestMedfordSlaParsing:
    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_flatten_keeps_no_geometry_for_table_row(self):
        record = _flatten(_FEATURE_LICENSE, _LICENSE_DATE_FIELDS)
        assert "latitude" not in record
        assert "longitude" not in record
        assert record["ISSUED"] == _LICENSE_ISSUED_ISO
        assert record["EXPIRED"] == "2027-09-01T00:00:00+00:00"

    def test_fixture_parses_through_the_producer_with_geocode(
        self, sla, monkeypatch
    ):
        """Table rows carry no geometry; the ADR-0004 geocode supplement on
        SITE_ADDR resolves coordinates. Call-args/counts are spine-volatile
        and not asserted — only the event outcome."""
        _patch_resolve(monkeypatch, "sla")
        record = _flatten(_FEATURE_LICENSE, _LICENSE_DATE_FIELDS)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (42.3282, -122.8563),
        )
        event = sla.parse_socrata_row(record, city_id="medford")
        assert event is not None
        assert event.city_id == "medford"
        assert event.license_id == "BL24-00951"
        assert event.dba == "PROFESSIONAL SERVICES, LLC"
        assert event.premises_name == "PROFESSIONAL SERVICES, LLC"
        assert event.license_type == "HOME BASED"
        assert event.license_status == "ACTIVE"
        assert event.latitude == pytest.approx(42.3282)
        assert event.longitude == pytest.approx(-122.8563)
        assert event.effective_date is not None
        assert event.effective_date.isoformat() == _LICENSE_ISSUED_ISO
        assert event.expiration_date is not None
        assert event.expiration_date.isoformat() == "2027-09-01T00:00:00+00:00"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None

    def test_license_id_required(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten(_FEATURE_LICENSE, _LICENSE_DATE_FIELDS)
        record.pop("LICENSE_NO")
        assert sla.parse_socrata_row(record, city_id="medford") is None

    def test_coordinate_less_row_without_geocode_stays_null_coords(
        self, sla, monkeypatch
    ):
        """If the geocode supplement fails, the license row is retained with
        null coordinates (DC precedent) — never dropped."""
        _patch_resolve(monkeypatch, "sla")
        record = _flatten(_FEATURE_LICENSE, _LICENSE_DATE_FIELDS)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        event = sla.parse_socrata_row(record, city_id="medford")
        assert event is not None
        assert event.license_id == "BL24-00951"
        assert event.latitude is None
        assert event.longitude is None
        assert event.h3_res7 is None


class TestMedfordCaseParsing:
    @pytest.fixture
    def cases(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_flatten_keeps_no_geometry_for_table_row(self):
        record = _flatten(_FEATURE_CASE, _CASE_DATE_FIELDS)
        assert "latitude" not in record
        assert "longitude" not in record
        assert record["STARTED"] == _CASE_STARTED_ISO
        assert record["CLOSED"] is None
        # Future-dated sentinel: LASTACTION is 2026-09-02 on the probe fixture.
        assert record["LASTACTION"] == "2026-09-02T00:00:00+00:00"

    def test_fixture_parses_through_the_producer_with_geocode(
        self, cases, monkeypatch
    ):
        """Table rows carry no geometry; the ADR-0004 geocode supplement on
        SITE_ADDR resolves coordinates. Call-args/counts are spine-volatile
        and not asserted — only the event outcome."""
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_FEATURE_CASE, _CASE_DATE_FIELDS)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (42.3322, -122.8631),
        )
        event = cases.parse_socrata_row(record, city_id="medford")
        assert event is not None
        assert event.city_id == "medford"
        assert event.incident_id == "CE26-02274"
        assert event.complaint_type == "OBSTRUCTION IN RIGHT OF WAY"
        assert event.incident_address == "3366 VIEWPOINT DR"
        assert event.zipcode == "97504"
        assert event.borough == "MEDFORD"
        assert event.source_neighborhood == "MEDFORD"
        assert event.status == "ACTIVE"
        assert event.latitude == pytest.approx(42.3322)
        assert event.longitude == pytest.approx(-122.8631)
        assert event.created_date is not None
        assert event.created_date.isoformat() == _CASE_STARTED_ISO
        assert event.closed_date is None
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None

    def test_incident_id_required(self, cases, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_FEATURE_CASE, _CASE_DATE_FIELDS)
        record.pop("CASE_NO")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (42.3322, -122.8631),
        )
        assert cases.parse_socrata_row(record, city_id="medford") is None

    def test_coordinate_less_row_dropped_when_geocode_fails(self, cases, monkeypatch):
        """Unlike SLA, the 311 producer drops rows that fail the geocode
        supplement (no null-coordinate 311 events)."""
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_FEATURE_CASE, _CASE_DATE_FIELDS)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert cases.parse_socrata_row(record, city_id="medford") is None


class TestMedfordFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_medford_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == MEDFORD_PERMITS_ENDPOINT
        assert spec.watermark_col == "ISSUED"
        assert spec.id_keys == ["PERMIT_NO"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "ISSUED DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"

    def test_sla_spec_matches_live_layer(self):
        spec = get_medford_dataset(FeedType.SLA)
        assert spec.platform == "arcgis"
        assert spec.endpoint == MEDFORD_SLA_ENDPOINT
        assert spec.watermark_col == "ISSUED"
        assert spec.id_keys == ["LICENSE_NO", "RECORDID"]
        assert spec.oid_field == "RowNum"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "ISSUED DESC"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Medford, OR"
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.topic == "raw.municipal.sla"

    def test_cases_spec_matches_live_layer(self):
        spec = get_medford_dataset(FeedType.COMPLAINTS_311)
        assert spec.platform == "arcgis"
        assert spec.endpoint == MEDFORD_CASES_ENDPOINT
        assert spec.watermark_col == "STARTED"
        assert spec.id_keys == ["CASE_NO", "RECORDID"]
        assert spec.oid_field == "RECORDID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "STARTED DESC"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Medford, OR"
        assert spec.field_map == CASE_FIELD_MAP
        assert spec.topic == "raw.municipal.311"

    def test_registered_feed_set_is_three_feeds(self):
        assert set(MEDFORD_FEED_SPECS) == {"permits", "sla", "311"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_medford_dataset("deeds")
        assert "medford" in str(exc.value)
        assert "permits" in str(exc.value)

    def test_endpoint_is_the_probed_server(self):
        assert "maps.medfordmaps.org" in MEDFORD_PERMITS_ENDPOINT
        assert "maps.medfordmaps.org" in MEDFORD_SLA_ENDPOINT
        assert "maps.medfordmaps.org" in MEDFORD_CASES_ENDPOINT
        assert "TRAKiTPermits_service/FeatureServer/1" in MEDFORD_PERMITS_ENDPOINT
        assert "MLI_TRAKiT_Service/FeatureServer/14" in MEDFORD_SLA_ENDPOINT
        assert "MLI_TRAKiT_Service/FeatureServer/12" in MEDFORD_CASES_ENDPOINT
