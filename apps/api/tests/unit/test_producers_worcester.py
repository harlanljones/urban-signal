"""Unit tests for the Worcester, MA leaf (US-419): spatial module + field maps
+ producer parse wiring (permits + SLA).

Worcester is a TWO-FEED PARTIAL metro on the city's ArcGIS Hub
(`services1.arcgis.com/j8dqo2DJE7mVUBU1`): Building Permits and Food
Establishment Licenses. Both are NON-SPATIAL address-only Tables (no native
lat/lng) with TEXT M/D/YYYY watermarks — every parse resolves coordinates
through the ADR-0004 geocode hook.

Tests pass WITHOUT a spine registration (no CityId.WORCESTER, no REGISTRY
assertions — "worcester" stays a plain string). Division/borough resolution
and geocode-hook CALL COUNTS are deliberately NOT asserted: both change when
the spine lands. The geocode hook is patched to a fixed downtown-Worcester
coordinate so no test touches the network.

Live fixtures captured byte-verbatim 2026-08-30 from
services1.arcgis.com/j8dqo2DJE7mVUBU1 — newest rows by TRUE calendar watermark
(parsed, not lexical text-sort): permits Permit_License_Issued_Date and SLA
Issued_Date both reach 8/21/2026.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.schemas.models import JobType
from src.spatial.cities.worcester import (
    FIELD_MAP,
    GEOCODE_CONTEXT,
    NEVER_CANDIDATE_COLUMNS,
    REGISTRATION,
    WORCESTER_CITY_ID,
    WORCESTER_DIVISION_BBOXES,
    WORCESTER_DIVISIONS,
    WORCESTER_FEED_SPECS,
    WORCESTER_METRO_BBOX,
    WORCESTER_PERMITS_ENDPOINT,
    WORCESTER_PERMITS_FIELD_MAP,
    WORCESTER_SLA_ENDPOINT,
    WORCESTER_SLA_FIELD_MAP,
    WORCESTER_SUBMARKETS,
    get_worcester_dataset,
    is_in_worcester_metro,
)
from src.spatial.city_registry import FeedType

# Downtown Worcester — the fixed geocode stub used so parse tests never touch
# the network. (Address-only feeds: geocode_row_if_declared is the coordinate
# source.)
_GEOCODED = (42.2626, -71.8023)


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _patch_geocode(monkeypatch):
    monkeypatch.setattr(
        "src.spatial.geocoder.geocode_row_if_declared",
        lambda city_id, feed_value, address, context=None: _GEOCODED,
    )


# Newest permit row by TRUE calendar watermark (8/21/2026), byte-verbatim.
_PERMIT_SOUTHBRIDGE = {
    "Record__": "B-26-3230",
    "Record_Type": "Building Permit",
    "Permit_For": "N/A",
    "Date_Submitted": "8/10/2026",
    "Record_Status": "Active",
    "Address": "142 SOUTHBRIDGE ST Worcester MA 01608",
    "MBL": "03-006-00013",
    "Occupancy_Type": "Commercial / Mixed Use",
    "Permit_License_Issued_Date": "8/21/2026",
    "Contractor_Name": "N/A",
    "ObjectId": 2,
}

# Co-newest permit row (8/21/2026).
_PERMIT_STAFFORD = {
    "Record__": "B-26-3362",
    "Record_Type": "Building Permit",
    "Permit_For": "N/A",
    "Date_Submitted": "8/18/2026",
    "Record_Status": "Active",
    "Address": "9 Stafford St Worcester MA 01603",
    "MBL": "08-029-00005",
    "Occupancy_Type": "Commercial / Mixed Use",
    "Permit_License_Issued_Date": "8/21/2026",
    "Contractor_Name": "N/A",
    "ObjectId": 6,
}

# Third co-newest permit row (8/21/2026), residential occupancy.
_PERMIT_BEACONSFIELD = {
    "Record__": "B-26-3284",
    "Record_Type": "Building Permit",
    "Permit_For": "N/A",
    "Date_Submitted": "8/13/2026",
    "Record_Status": "Active",
    "Address": "125 Beaconsfield Rd Worcester MA 01602",
    "MBL": "25-008-00007",
    "Occupancy_Type": "1 or 2 Family Dwelling",
    "Permit_License_Issued_Date": "8/21/2026",
    "Contractor_Name": "N/A",
    "ObjectId": 9,
}

# Newest SLA row by TRUE calendar watermark (8/21/2026), byte-verbatim.
_SLA_SOUTHBRIDGE = {
    "Record__": "FFEL-2410",
    "Record_Type": "Food Establishment License",
    "Issued_Date": "8/21/2026",
    "Expiration_Date": "12/31/2026",
    "Address": "24 SOUTHBRIDGE ST Worcester MA",
    "Type": "Food & Drink Est 1-100",
    "Total_of_Fees": 275,
    "ObjectId": 37,
}

# Co-newest SLA row (8/21/2026).
_SLA_CHANDLER = {
    "Record__": "FFEL-2387",
    "Record_Type": "Food Establishment License",
    "Issued_Date": "8/21/2026",
    "Expiration_Date": "12/31/2026",
    "Address": "372 CHANDLER ST Worcester MA",
    "Type": "Food & Drink Est 1-100",
    "Total_of_Fees": 275,
    "ObjectId": 41,
}

# Third SLA row (8/20/2026).
_SLA_QUINSIGAMOND = {
    "Record__": "FFEL-2403",
    "Record_Type": "Food Establishment License",
    "Issued_Date": "8/20/2026",
    "Expiration_Date": "12/31/2026",
    "Address": "75 QUINSIGAMOND AVE Worcester MA",
    "Type": "Food & Drink Est 1-100",
    "Total_of_Fees": 275,
    "ObjectId": 50,
}


class TestWorcesterSpatial:
    def test_metro_bbox_sanity(self):
        assert WORCESTER_METRO_BBOX["min_lat"] < WORCESTER_METRO_BBOX["max_lat"]
        assert WORCESTER_METRO_BBOX["min_lng"] < WORCESTER_METRO_BBOX["max_lng"]

    def test_is_in_worcester_metro_rejects_missing_coordinates(self):
        assert is_in_worcester_metro(None, None) is False

    def test_is_in_worcester_metro_rejects_other_cities(self):
        assert is_in_worcester_metro(42.2626, -71.8023) is True    # Downtown
        assert is_in_worcester_metro(42.3601, -71.0589) is False   # Boston
        assert is_in_worcester_metro(42.6526, -73.7562) is False   # Albany
        assert is_in_worcester_metro(40.7128, -74.0060) is False   # NYC

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in WORCESTER_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= WORCESTER_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= WORCESTER_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= WORCESTER_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= WORCESTER_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in WORCESTER_SUBMARKETS.items():
            bbox = WORCESTER_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in WORCESTER_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(WORCESTER_SUBMARKETS)

    def test_submarkets_carry_the_worcester_city_id(self):
        assert {m.city_id for m in WORCESTER_SUBMARKETS.values()} == {"worcester"}

    def test_divisions_carry_the_worcester_city_id(self):
        assert {d.city_id for d in WORCESTER_DIVISIONS.values()} == {"worcester"}

    def test_city_id_and_registration_shape(self):
        assert WORCESTER_CITY_ID == "worcester"
        assert REGISTRATION.metro_bbox is WORCESTER_METRO_BBOX
        assert REGISTRATION.submarkets is WORCESTER_SUBMARKETS
        assert len(REGISTRATION.divisions) == 6
        assert len(WORCESTER_SUBMARKETS) == 9

    def test_required_real_neighborhoods_present(self):
        assert set(WORCESTER_SUBMARKETS) == {
            "Downtown",
            "Canal District",
            "Shrewsbury Street",
            "Grafton Hill",
            "Main South",
            "Webster Square",
            "Quinsigamond Village",
            "Tatnuck",
            "Greendale",
        }


class TestWorcesterFeedSpecs:
    def test_registered_feed_set(self):
        assert set(WORCESTER_FEED_SPECS) == {"permits", "sla"}

    def test_permits_spec_shape(self):
        spec = WORCESTER_FEED_SPECS["permits"]
        assert spec["endpoint"] == WORCESTER_PERMITS_ENDPOINT
        assert "Building_Permits/FeatureServer/0" in spec["endpoint"]
        assert spec["platform"] == "arcgis"
        assert spec["watermark_col"] == "Permit_License_Issued_Date"
        assert spec["id_keys"] == ["Record__", "ObjectId"]
        assert spec["producer_key"] == "permits"
        assert spec["topic_key"] == "topic_permits"

    def test_sla_spec_shape(self):
        spec = WORCESTER_FEED_SPECS["sla"]
        assert spec["endpoint"] == WORCESTER_SLA_ENDPOINT
        assert "Food_Establishment_Licenses/FeatureServer/0" in spec["endpoint"]
        assert spec["platform"] == "arcgis"
        assert spec["watermark_col"] == "Issued_Date"
        assert spec["id_keys"] == ["Record__", "ObjectId"]
        assert spec["producer_key"] == "sla"
        assert spec["topic_key"] == "topic_sla"

    def test_permits_extra_pins_text_watermark_and_geocode(self):
        extra = WORCESTER_FEED_SPECS["permits"]["extra"]
        assert extra["watermark_type"] == "text"
        assert extra["watermark_format"] == "%m/%d/%Y"
        assert extra["needs_geocode"] is True
        assert extra["geocode_context"] == "Worcester, MA"
        assert extra["oid_field"] == "ObjectId"
        assert extra["max_record_count"] == 1000
        assert extra["order_by"] == "Permit_License_Issued_Date DESC"
        assert extra["non_spatial"] is True

    def test_sla_extra_pins_text_watermark_and_geocode(self):
        extra = WORCESTER_FEED_SPECS["sla"]["extra"]
        assert extra["watermark_type"] == "text"
        assert extra["watermark_format"] == "%m/%d/%Y"
        assert extra["needs_geocode"] is True
        assert extra["geocode_context"] == "Worcester, MA"
        assert extra["oid_field"] == "ObjectId"
        assert extra["max_record_count"] == 1000
        assert extra["order_by"] == "Issued_Date DESC"
        assert extra["non_spatial"] is True

    def test_get_worcester_dataset_resolves_permits(self, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        spec = get_worcester_dataset(FeedType.PERMITS)
        assert spec.endpoint == WORCESTER_PERMITS_ENDPOINT
        assert spec.platform == "arcgis"
        assert spec.watermark_col == "Permit_License_Issued_Date"
        assert spec.watermark_type == "text"
        assert spec.watermark_format == "%m/%d/%Y"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Worcester, MA"
        assert spec.field_map == WORCESTER_PERMITS_FIELD_MAP

    def test_get_worcester_dataset_resolves_sla(self, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        spec = get_worcester_dataset(FeedType.SLA)
        assert spec.endpoint == WORCESTER_SLA_ENDPOINT
        assert spec.platform == "arcgis"
        assert spec.watermark_col == "Issued_Date"
        assert spec.field_map == WORCESTER_SLA_FIELD_MAP

    def test_get_worcester_dataset_rejects_unregistered_feeds(self):
        class _Feed:
            value = "deeds"

        with pytest.raises(KeyError, match="worcester"):
            get_worcester_dataset(_Feed())


class TestWorcesterFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert WORCESTER_PERMITS_FIELD_MAP["job_id"] == ["Record__", "ObjectId"]
        assert WORCESTER_PERMITS_FIELD_MAP["issuance_date"] == ["Permit_License_Issued_Date"]
        assert WORCESTER_PERMITS_FIELD_MAP["filing_date"] == ["Date_Submitted"]
        assert WORCESTER_PERMITS_FIELD_MAP["job_type"] == ["Record_Type", "Permit_For"]
        assert WORCESTER_PERMITS_FIELD_MAP["status"] == ["Record_Status"]
        assert WORCESTER_PERMITS_FIELD_MAP["address_street"] == ["Address"]
        assert WORCESTER_PERMITS_FIELD_MAP["bbl"] == ["MBL"]

    def test_permits_has_no_coordinate_or_cost_candidates(self):
        assert "latitude" not in WORCESTER_PERMITS_FIELD_MAP
        assert "longitude" not in WORCESTER_PERMITS_FIELD_MAP
        assert "cost" not in WORCESTER_PERMITS_FIELD_MAP
        assert "occupancy" not in WORCESTER_PERMITS_FIELD_MAP

    def test_sla_map_reads_live_columns(self):
        assert WORCESTER_SLA_FIELD_MAP["license_id"] == ["Record__", "ObjectId"]
        assert WORCESTER_SLA_FIELD_MAP["license_type"] == ["Type"]
        assert WORCESTER_SLA_FIELD_MAP["effective_date"] == ["Issued_Date"]
        assert WORCESTER_SLA_FIELD_MAP["expiration_date"] == ["Expiration_Date"]
        assert WORCESTER_SLA_FIELD_MAP["address_street"] == ["Address"]

    def test_sla_has_no_business_name_columns(self):
        assert "dba" not in WORCESTER_SLA_FIELD_MAP
        assert "premises_name" not in WORCESTER_SLA_FIELD_MAP

    def test_never_candidate_columns_stay_out_of_both_maps(self):
        for field_map in (WORCESTER_PERMITS_FIELD_MAP, WORCESTER_SLA_FIELD_MAP):
            for values in field_map.values():
                for col in values:
                    assert col not in NEVER_CANDIDATE_COLUMNS

    def test_map_is_exported_and_two_feed(self):
        assert set(FIELD_MAP) == {"permits", "sla"}
        assert FIELD_MAP["permits"] is WORCESTER_PERMITS_FIELD_MAP
        assert FIELD_MAP["sla"] is WORCESTER_SLA_FIELD_MAP
        assert GEOCODE_CONTEXT == "Worcester, MA"

    def test_permits_first_mapped_reads_fixture(self):
        assert first_mapped(_PERMIT_SOUTHBRIDGE, WORCESTER_PERMITS_FIELD_MAP, "job_id") == "B-26-3230"
        assert (
            first_mapped(_PERMIT_SOUTHBRIDGE, WORCESTER_PERMITS_FIELD_MAP, "issuance_date")
            == "8/21/2026"
        )
        assert (
            first_mapped(_PERMIT_SOUTHBRIDGE, WORCESTER_PERMITS_FIELD_MAP, "bbl")
            == "03-006-00013"
        )

    def test_sla_first_mapped_reads_fixture(self):
        assert first_mapped(_SLA_SOUTHBRIDGE, WORCESTER_SLA_FIELD_MAP, "license_id") == "FFEL-2410"
        assert (
            first_mapped(_SLA_SOUTHBRIDGE, WORCESTER_SLA_FIELD_MAP, "license_type")
            == "Food & Drink Est 1-100"
        )
        assert (
            first_mapped(_SLA_SOUTHBRIDGE, WORCESTER_SLA_FIELD_MAP, "effective_date")
            == "8/21/2026"
        )


class TestWorcesterPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_newest_permit_parses_through_real_producer_path(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        _patch_geocode(monkeypatch)
        event = permits.parse_socrata_row(_PERMIT_SOUTHBRIDGE, city_id="worcester")
        assert event is not None
        assert event.city_id == "worcester"
        assert event.job_id == "B-26-3230"
        assert event.address_street == "142 SOUTHBRIDGE ST Worcester MA 01608"
        assert event.bbl == "03-006-00013"
        assert event.status == "Active"
        assert event.issuance_date is not None and event.issuance_date.year == 2026
        assert event.issuance_date.month == 8 and event.issuance_date.day == 21
        assert event.filing_date is not None and event.filing_date.day == 10

    def test_permit_resolves_coordinates_via_geocode(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        _patch_geocode(monkeypatch)
        event = permits.parse_socrata_row(_PERMIT_SOUTHBRIDGE, city_id="worcester")
        assert event is not None
        assert event.latitude == pytest.approx(42.2626)
        assert event.longitude == pytest.approx(-71.8023)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert is_in_worcester_metro(event.latitude, event.longitude)

    def test_permit_job_type_is_constant_building_permit_ot(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        _patch_geocode(monkeypatch)
        event = permits.parse_socrata_row(_PERMIT_SOUTHBRIDGE, city_id="worcester")
        assert event is not None
        # Record_Type is constant "Building Permit" -> no keyword match -> OT.
        assert event.job_type == JobType.OT

    def test_second_permit_fixture_parses(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        _patch_geocode(monkeypatch)
        event = permits.parse_socrata_row(_PERMIT_STAFFORD, city_id="worcester")
        assert event is not None
        assert event.job_id == "B-26-3362"
        assert event.bbl == "08-029-00005"
        assert event.filing_date is not None and event.filing_date.day == 18

    def test_permit_source_neighborhood_is_none(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        _patch_geocode(monkeypatch)
        event = permits.parse_socrata_row(_PERMIT_SOUTHBRIDGE, city_id="worcester")
        assert event is not None
        assert event.source_neighborhood is None


class TestWorcesterSlaParsing:
    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_newest_sla_parses_through_real_producer_path(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        _patch_geocode(monkeypatch)
        event = sla.parse_socrata_row(_SLA_SOUTHBRIDGE, city_id="worcester")
        assert event is not None
        assert event.city_id == "worcester"
        assert event.license_id == "FFEL-2410"
        assert event.license_type == "Food & Drink Est 1-100"
        assert event.address == "24 SOUTHBRIDGE ST Worcester MA"
        assert event.dba is None and event.premises_name is None
        assert event.license_status == "ACTIVE"

    def test_sla_dates_parse_from_text_m_d_yyyy(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        _patch_geocode(monkeypatch)
        event = sla.parse_socrata_row(_SLA_SOUTHBRIDGE, city_id="worcester")
        assert event is not None
        assert event.effective_date is not None
        assert event.effective_date.year == 2026 and event.effective_date.month == 8
        assert event.effective_date.day == 21
        assert event.expiration_date is not None
        assert event.expiration_date.month == 12 and event.expiration_date.day == 31

    def test_sla_resolves_coordinates_via_geocode(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        _patch_geocode(monkeypatch)
        event = sla.parse_socrata_row(_SLA_SOUTHBRIDGE, city_id="worcester")
        assert event is not None
        assert event.latitude == pytest.approx(42.2626)
        assert event.longitude == pytest.approx(-71.8023)
        assert event.h3_res7 is not None
        assert is_in_worcester_metro(event.latitude, event.longitude)

    def test_second_sla_fixture_parses(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        _patch_geocode(monkeypatch)
        event = sla.parse_socrata_row(_SLA_CHANDLER, city_id="worcester")
        assert event is not None
        assert event.license_id == "FFEL-2387"
        assert event.address == "372 CHANDLER ST Worcester MA"

    def test_sla_source_neighborhood_is_none(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        _patch_geocode(monkeypatch)
        event = sla.parse_socrata_row(_SLA_SOUTHBRIDGE, city_id="worcester")
        assert event is not None
        assert event.source_neighborhood is None
