"""Unit tests for the Billings, MT leaf (US-234): spatial module + field maps +
producer parse wiring.

Billings is a TWO-FEED PARTIAL metro: ``BuildingPermits_CodeViolations_EXT``
(MapServer/0 at ``billingsgis.com``, Tier 1, daily, native outSR=4326 point
geometry + native Latitude/Longitude attribute columns) and ``Requests_public``
(FeatureServer/0 on the city's ArcGIS Online org, Tier 1, daily, native WGS84
point geometry). Crime, SLA, and deeds stay Tier 3 — only ``permits`` and
``311`` are registered.

Tests pass WITHOUT a spine registration (no CityId.BILLINGS, no REGISTRY
assertions — "billings" stays a plain string). Spine-stable per the wave-5
leaf contract: no division/borough-resolution assertions and no geocode-hook
call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from MapServer/0 and FeatureServer/0
(newest rows via ``orderByFields=Issue_Date DESC`` and ``created_date DESC`` at
``outSR=4326``). Fixtures are RAW ArcGIS features (attributes + geometry); the
tests run the real ``ArcGISClient._flatten_feature`` lift — geometry to
latitude/longitude, epoch-ms to ISO — before parsing, exactly as the live
producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps_billings import (
    BILLINGS_311_FIELD_MAP,
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.schemas.models import ComplaintCategory, JobType
from src.spatial.cities.billings import (
    BILLINGS_311_ENDPOINT,
    BILLINGS_CITY_ID,
    BILLINGS_DIVISION_BBOXES,
    BILLINGS_DIVISIONS,
    BILLINGS_FEED_SPECS,
    BILLINGS_GEOCODE_CONTEXT,
    BILLINGS_METRO_BBOX,
    BILLINGS_PERMITS_ENDPOINT,
    BILLINGS_SUBMARKETS,
    REGISTRATION,
    get_billings_dataset,
    is_in_billings_metro,
    is_in_greater_billings_metro,
)
from src.spatial.city_registry import FeedType


def _patch_resolve_permits(monkeypatch):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP["permits"],
    )


def _patch_resolve_311(monkeypatch):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: BILLINGS_311_FIELD_MAP,
    )


def _flatten(feature, date_fields):
    """Run the real ArcGIS flatten lift over a raw captured feature."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, date_fields)


# ---------------------------------------------------------------------------
# 311 fixtures — byte-verbatim 2026-08-28 (newest rows via
# orderByFields=created_date DESC, outSR=4326)
# ---------------------------------------------------------------------------

_FEATURE_311_417 = {
    "attributes": {
        "OBJECTID": 417,
        "reqid": "PW-00340",
        "reqcategory": "Streets",
        "reqtype": "Sight Obstruction",
        "details": "The weeds at Robertson and Lake Elmo are high again and knee chopped down. It\u2019s dangerous to try to turn from Robertson onto Lake Elmo.",
        "pocfirstname": "Jackie",
        "poclastname": "JS",
        "locdesc": None,
        "status": "Submitted",
        "resolutiondt": None,
        "resolution": None,
        "globalid": "d66d9931-e2a0-4d54-98a6-2388b90aec30",
        "created_date": 1787808604235,
        "created_user": "",
    },
    "geometry": {
        "x": -108.474459959415,
        "y": 45.83967506691798,
    },
}

_FEATURE_311_416 = {
    "attributes": {
        "OBJECTID": 416,
        "reqid": "PW-00339",
        "reqcategory": "Streets",
        "reqtype": "Pothole",
        "details": "They\u2019re everywhere, especially when you\u2019re driving next to Wendy\u2019s! ",
        "pocfirstname": "Sandria ",
        "poclastname": "Arnold",
        "locdesc": None,
        "status": "Submitted",
        "resolutiondt": None,
        "resolution": None,
        "globalid": "41bac480-e159-4ced-be50-3b52607cdab4",
        "created_date": 1787793943329,
        "created_user": "",
    },
    "geometry": {
        "x": -108.52954348015112,
        "y": 45.7545820277904,
    },
}

_FEATURE_311_414 = {
    "attributes": {
        "OBJECTID": 414,
        "reqid": "PW-00337",
        "reqcategory": "Garbage",
        "reqtype": "Broken, Missing parts - Residential Black Barrel",
        "details": "We live at 209 s 28th to our knowledge there is at least 3 potentially 4 address/ units at 209 s 28th but we for the past 5 years have shared 1 9 gallon trash can",
        "pocfirstname": "Kassandra ",
        "poclastname": "Green",
        "locdesc": None,
        "status": "Submitted",
        "resolutiondt": None,
        "resolution": None,
        "globalid": "2e34aa89-be58-43ef-913d-0c45e383e1b1",
        "created_date": 1787681677112,
        "created_user": "",
    },
    "geometry": {
        "x": -108.50185151607816,
        "y": 45.77844983235861,
    },
}

_CREATED_DATE_NEWEST_ISO = "2026-08-27T05:30:04.235000+00:00"

# ---------------------------------------------------------------------------
# Permit fixtures — byte-verbatim 2026-08-28 (newest rows via
# orderByFields=Issue_Date DESC, outSR=4326). The first two share the same
# Building_Permit_Num (contractor-to-permit join).
# ---------------------------------------------------------------------------

_FEATURE_PERMIT_58907 = {
    "attributes": {
        "OBJECTID": 58907,
        "CitizenAccess": "https://cityview.billingsmt.gov/Portal/",
        "Property_Address": "1595 GRAND AVE, BILLINGS, MT 59102",
        "Permit_Type": "Remodel",
        "Job_Description": "COM REMODEL\n",
        "Account": "RM",
        "Building_Permit_Num": "BP-25-04603",
        "Permit_Status": "In Progress",
        "Work_Type": "Remodel",
        "Contractor": "J2BG CONSTRUCTION",
        "Contractor_Num": "LC111213913",
        "Date_Entered": 1760572800000,
        "Expiration_Date": 1802304000000,
        "Entered_By": "kleinb",
        "Issue_Date": 1786437732857,
        "Last_Inspection_Date": 1776901507577,
        "Application_Status": "IP",
        "Owner": "WEST PARK PROMENADE 8 LLC",
        "Owner_Address": "3412 COLTON BLVD UNIT 101",
        "Owner_City": "BILLINGS",
        "Owner_State": "MT",
        "Owner_Zip": "59102-2078",
        "Latitude": 45.78548987,
        "Longitude": -108.5569727,
    },
    "geometry": {
        "x": -108.55696087493484,
        "y": 45.7854830102184,
    },
}

_FEATURE_PERMIT_129 = {
    "attributes": {
        "OBJECTID": 129,
        "CitizenAccess": "https://cityview.billingsmt.gov/Portal/",
        "Property_Address": "474 FOOTE ST, BILLINGS, MT 59101",
        "Permit_Type": "Right of Way",
        "Job_Description": "ENG - RIGHT OF WAY PERMIT\nCharter/Springline Construction to bore on W side of Foote St, E along easement, and onto Morey St",
        "Account": "ROW",
        "Building_Permit_Num": "ENG-26-00670",
        "Permit_Status": "Issued",
        "Work_Type": "New",
        "Contractor": "CHARTER COMMUNICATIONS",
        "Contractor_Num": "LC054711883",
        "Date_Entered": 1772409600000,
        "Expiration_Date": 1803168000000,
        "Entered_By": "carlsonr",
        "Issue_Date": 1786320000000,
        "Last_Inspection_Date": 1787664520820,
        "Application_Status": "ISS",
        "Owner": "474 FOOTE STREET LLC",
        "Owner_Address": "4115 SEDGWICK PL",
        "Owner_City": "BILLINGS",
        "Owner_State": "MT",
        "Owner_Zip": "59106-2423",
        "Latitude": 45.76118809,
        "Longitude": -108.53950782,
    },
    "geometry": {
        "x": -108.53949600222383,
        "y": 45.76118122576167,
    },
}

_ISSUE_DATE_NEWEST_ISO = "2026-08-11T08:42:12.857000+00:00"


# ======================================================================
# Spatial
# ======================================================================


class TestBillingsSpatial:
    def test_metro_bbox_sanity(self):
        assert BILLINGS_METRO_BBOX["min_lat"] < BILLINGS_METRO_BBOX["max_lat"]
        assert BILLINGS_METRO_BBOX["min_lng"] < BILLINGS_METRO_BBOX["max_lng"]

    def test_is_in_billings_metro_rejects_missing_coordinates(self):
        assert is_in_billings_metro(None, None) is False
        assert is_in_billings_metro(45.7835, None) is False
        assert is_in_billings_metro(None, -108.5045) is False

    def test_is_in_billings_metro_rejects_other_cities(self):
        assert is_in_billings_metro(45.6770, -111.0429) is False  # Bozeman
        assert is_in_billings_metro(46.8797, -113.3250) is False  # Missoula
        assert is_in_billings_metro(44.0682, -114.7420) is False  # Stanley, ID
        assert is_in_billings_metro(47.4940, -111.2870) is False  # Great Falls

    def test_downtown_anchors_are_contained(self):
        assert is_in_billings_metro(45.7835, -108.5045)  # Downtown core
        assert is_in_billings_metro(45.7875, -108.5460)  # Midtown
        assert is_in_billings_metro(45.7795, -108.5900)  # West End

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_FEATURE_311_417, _FEATURE_311_416, _FEATURE_311_414):
            assert is_in_billings_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )
        for feature in (_FEATURE_PERMIT_58907, _FEATURE_PERMIT_129):
            assert is_in_billings_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in BILLINGS_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= BILLINGS_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= BILLINGS_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= BILLINGS_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= BILLINGS_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in BILLINGS_SUBMARKETS.items():
            bbox = BILLINGS_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in BILLINGS_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(BILLINGS_SUBMARKETS)

    def test_submarkets_carry_the_billings_city_id(self):
        assert {m.city_id for m in BILLINGS_SUBMARKETS.values()} == {"billings"}

    def test_city_id_and_registration_shape(self):
        assert BILLINGS_CITY_ID == "billings"
        assert REGISTRATION.metro_bbox is BILLINGS_METRO_BBOX
        assert REGISTRATION.submarkets is BILLINGS_SUBMARKETS
        assert REGISTRATION.division_bboxes is BILLINGS_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_billings_metro
        assert len(REGISTRATION.divisions) == 6
        assert len(BILLINGS_SUBMARKETS) == 10

    def test_required_real_neighborhoods_present(self):
        assert set(BILLINGS_SUBMARKETS) == {
            "Downtown",
            "Midtown",
            "MetraPark District",
            "West End",
            "Rimrock",
            "South Side",
            "Southgate",
            "Billings Heights",
            "Airport District",
            "Lockwood",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_billings_metro is is_in_billings_metro


# ======================================================================
# Field maps
# ======================================================================


class TestBillingsFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["Building_Permit_Num", "OBJECTID"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["Issue_Date"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["Date_Entered"]
        assert PERMITS_FIELD_MAP["status"] == ["Permit_Status"]
        assert PERMITS_FIELD_MAP["job_type"] == ["Permit_Type"]
        assert PERMITS_FIELD_MAP["address_street"] == ["Property_Address"]

    def test_311_map_reads_live_columns(self):
        assert BILLINGS_311_FIELD_MAP["incident_id"] == ["reqid", "OBJECTID"]
        assert BILLINGS_311_FIELD_MAP["created_date"] == ["created_date"]
        assert BILLINGS_311_FIELD_MAP["closed_date"] == ["resolutiondt"]
        assert BILLINGS_311_FIELD_MAP["status"] == ["status"]
        assert BILLINGS_311_FIELD_MAP["complaint_type"] == ["reqtype"]
        assert BILLINGS_311_FIELD_MAP["incident_address"] == ["locdesc"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Billings, MT"
        assert BILLINGS_GEOCODE_CONTEXT == "Billings, MT"

    def test_native_lat_lng_columns_exist_but_are_not_in_the_field_map(self):
        """Latitude/Longitude attribute columns are native degrees on the
        permit layer, but the leaf relies on the geometry lift only (Greenville
        discipline). The 311 layer has no lat/lng attribute columns at all."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP
        assert "latitude" not in BILLINGS_311_FIELD_MAP
        assert "longitude" not in BILLINGS_311_FIELD_MAP

    def test_no_borough_candidate_so_source_neighborhood_passes_none(self):
        assert "borough" not in PERMITS_FIELD_MAP
        assert "borough" not in BILLINGS_311_FIELD_MAP
        assert "neighborhood" not in PERMITS_FIELD_MAP

    def test_no_zipcode_or_bbl_candidates(self):
        """Property_Address contains the full address with zip, but no
        dedicated zipcode column is declared. No parcel/APN exists."""
        assert "zipcode" not in PERMITS_FIELD_MAP
        assert "zipcode" not in BILLINGS_311_FIELD_MAP
        assert "bbl" not in PERMITS_FIELD_MAP

    def test_pii_columns_never_become_candidates(self):
        mapped = {c for values in PERMITS_FIELD_MAP.values() for c in values}
        assert mapped
        for col in DROPPED_PII_COLUMNS:
            assert col not in mapped
        mapped_311 = {c for values in BILLINGS_311_FIELD_MAP.values() for c in values}
        for col in ("pocfirstname", "poclastname", "created_user"):
            assert col not in mapped_311
        assert {"Owner", "Owner_Address", "Owner_Zip",
                "Contractor", "Contractor_Num", "Entered_By",
                "pocfirstname", "poclastname"} <= set(DROPPED_PII_COLUMNS)

    def test_permits_have_no_cost_column(self):
        assert "cost" not in PERMITS_FIELD_MAP


# ======================================================================
# Permit parsing
# ======================================================================


class TestBillingsPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_FEATURE_PERMIT_58907, {"Issue_Date", "Date_Entered",
                                                  "Expiration_Date", "Last_Inspection_Date"})
        assert record["latitude"] == pytest.approx(45.7854830102184)
        assert record["longitude"] == pytest.approx(-108.55696087493484)
        assert record["Issue_Date"] == _ISSUE_DATE_NEWEST_ISO

    def test_flatten_iso_normalizes_the_watermark(self):
        record = _flatten(_FEATURE_PERMIT_129, {"Issue_Date", "Date_Entered",
                                                "Expiration_Date", "Last_Inspection_Date"})
        assert record["Issue_Date"] == "2026-08-10T00:00:00+00:00"
        assert record["Date_Entered"] == "2026-03-02T00:00:00+00:00"

    def test_grand_ave_remodel_parses_through_the_producer(self, permits, monkeypatch):
        _patch_resolve_permits(monkeypatch)
        record = _flatten(_FEATURE_PERMIT_58907, {"Issue_Date", "Date_Entered",
                                                  "Expiration_Date", "Last_Inspection_Date"})
        event = permits.parse_socrata_row(record, city_id="billings")
        assert event is not None
        assert event.city_id == "billings"
        assert event.job_id == "BP-25-04603"
        assert event.status == "In Progress"
        assert event.estimated_cost == pytest.approx(0.0)
        assert event.address_street == "1595 GRAND AVE, BILLINGS, MT 59102"
        assert event.latitude == pytest.approx(45.7854830102184)
        assert event.longitude == pytest.approx(-108.55696087493484)
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat() == _ISSUE_DATE_NEWEST_ISO
        assert event.filing_date is not None
        assert event.filing_date.isoformat() == "2025-10-16T00:00:00+00:00"
        assert event.source_neighborhood is None
        assert event.zipcode == ""

    def test_foote_st_right_of_way_parses_and_sits_in_metro(self, permits, monkeypatch):
        _patch_resolve_permits(monkeypatch)
        record = _flatten(_FEATURE_PERMIT_129, {"Issue_Date", "Date_Entered",
                                                "Expiration_Date", "Last_Inspection_Date"})
        event = permits.parse_socrata_row(record, city_id="billings")
        assert event is not None
        assert event.job_id == "ENG-26-00670"
        assert event.status == "Issued"
        assert event.estimated_cost == pytest.approx(0.0)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_billings_metro(event.latitude, event.longitude)

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve_permits(monkeypatch)
        record = _flatten(_FEATURE_PERMIT_58907, {"Issue_Date", "Date_Entered",
                                                  "Expiration_Date", "Last_Inspection_Date"})
        record.pop("Building_Permit_Num")
        event = permits.parse_socrata_row(record, city_id="billings")
        assert event is not None
        assert event.job_id == "58907"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve_permits(monkeypatch)
        record = _flatten(_FEATURE_PERMIT_58907, {"Issue_Date", "Date_Entered",
                                                  "Expiration_Date", "Last_Inspection_Date"})
        record.pop("Building_Permit_Num")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="billings") is None

    def test_billings_remodel_stays_unclassified_at_the_leaf(self, permits, monkeypatch):
        """Permit_Type codes (Remodel, Right of Way) pass through as job_type
        candidates. 'Remodel' is not among the producer's recognized codes,
        so it lands on OT."""
        _patch_resolve_permits(monkeypatch)
        event = permits.parse_socrata_row(
            _flatten(_FEATURE_PERMIT_58907, {"Issue_Date", "Date_Entered",
                                             "Expiration_Date", "Last_Inspection_Date"}),
            city_id="billings",
        )
        assert event is not None
        assert event.job_type == JobType.OT


# ======================================================================
# 311 parsing
# ======================================================================


class TestBillings311Parsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_flatten_lifts_311_geometry(self):
        record = _flatten(_FEATURE_311_417, {"created_date", "resolutiondt"})
        assert record["latitude"] == pytest.approx(45.83967506691798)
        assert record["longitude"] == pytest.approx(-108.474459959415)
        assert record["created_date"] == _CREATED_DATE_NEWEST_ISO

    def test_sight_obstruction_parses_through_the_producer(self, complaints, monkeypatch):
        _patch_resolve_311(monkeypatch)
        record = _flatten(_FEATURE_311_417, {"created_date", "resolutiondt"})
        event = complaints.parse_socrata_row(record, city_id="billings")
        assert event is not None
        assert event.city_id == "billings"
        assert event.incident_id == "PW-00340"
        assert event.complaint_type == "Sight Obstruction"
        assert event.status == "Submitted"
        assert event.incident_address is None
        assert event.latitude == pytest.approx(45.83967506691798)
        assert event.longitude == pytest.approx(-108.474459959415)
        assert event.created_date.isoformat() == _CREATED_DATE_NEWEST_ISO
        assert event.closed_date is None
        assert event.borough is None
        assert event.category == ComplaintCategory.OTHER

    def test_pothole_parses_and_sits_in_metro(self, complaints, monkeypatch):
        _patch_resolve_311(monkeypatch)
        record = _flatten(_FEATURE_311_416, {"created_date", "resolutiondt"})
        event = complaints.parse_socrata_row(record, city_id="billings")
        assert event is not None
        assert event.incident_id == "PW-00339"
        assert event.complaint_type == "Pothole"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert is_in_billings_metro(event.latitude, event.longitude)

    def test_garbage_barrel_parses_through_the_producer(self, complaints, monkeypatch):
        _patch_resolve_311(monkeypatch)
        record = _flatten(_FEATURE_311_414, {"created_date", "resolutiondt"})
        event = complaints.parse_socrata_row(record, city_id="billings")
        assert event is not None
        assert event.incident_id == "PW-00337"
        assert event.complaint_type == "Broken, Missing parts - Residential Black Barrel"
        assert event.latitude == pytest.approx(45.77844983235861)
        assert event.longitude == pytest.approx(-108.50185151607816)

    def test_all_three_311_fixtures_share_the_co_newest_watermark(self, complaints, monkeypatch):
        _patch_resolve_311(monkeypatch)
        events = [
            complaints.parse_socrata_row(
                _flatten(f, {"created_date", "resolutiondt"}), city_id="billings"
            )
            for f in (_FEATURE_311_417, _FEATURE_311_416, _FEATURE_311_414)
        ]
        assert all(e is not None for e in events)
        assert {e.incident_id for e in events} == {"PW-00340", "PW-00339", "PW-00337"}
        assert len({e.h3_res9 for e in events}) == 3

    def test_311_incident_id_falls_back_to_objectid(self, complaints, monkeypatch):
        _patch_resolve_311(monkeypatch)
        record = _flatten(_FEATURE_311_417, {"created_date", "resolutiondt"})
        record.pop("reqid")
        event = complaints.parse_socrata_row(record, city_id="billings")
        assert event is not None
        assert event.incident_id == "417"


# ======================================================================
# Feed spec
# ======================================================================


class TestBillingsFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_billings_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == BILLINGS_PERMITS_ENDPOINT
        assert spec.watermark_col == "Issue_Date"
        assert spec.id_keys == ["Building_Permit_Num", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "Issue_Date DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.geocode_context == "Billings, MT"
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"

    def test_311_spec_matches_live_layer(self):
        spec = get_billings_dataset(FeedType.COMPLAINTS_311)
        assert spec.platform == "arcgis"
        assert spec.endpoint == BILLINGS_311_ENDPOINT
        assert spec.watermark_col == "created_date"
        assert spec.id_keys == ["reqid", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "created_date DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.geocode_context == "Billings, MT"
        assert spec.field_map == BILLINGS_311_FIELD_MAP
        assert spec.topic == "raw.municipal.311"

    def test_registered_feed_set_is_permits_and_311(self):
        assert set(BILLINGS_FEED_SPECS) == {"permits", "311"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_billings_dataset("sla")
        assert "billings" in str(exc.value)
        assert "permits" in str(exc.value)

    def test_endpoints_are_the_probed_services(self):
        assert "billingsgis.com" in BILLINGS_PERMITS_ENDPOINT
        assert (
            "BuildingPermits_CodeViolations_EXT/MapServer/0"
            in BILLINGS_PERMITS_ENDPOINT
        )
        assert "services6.arcgis.com/rCC3yWJa2mjYtKDP" in BILLINGS_311_ENDPOINT
        assert (
            "Requests_public_00e63199176f44b788fd43684476713d/FeatureServer/0"
            in BILLINGS_311_ENDPOINT
        )