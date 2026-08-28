"""Unit tests for the Spartanburg leaf (US-301 rebuild): spatial module + field
maps + PERMITS / SLA parse wiring.

Spartanburg County, SC publishes both feeds from ONE shared on-prem ArcGIS
FeatureServer layer — ``EnerGov/EnerGov_Spatial_Collections/FeatureServer/5``
("History Points") on ``maps.spartanburgcounty.org`` (site root
``/server/rest/services``). They are separated solely by a load-bearing
``where`` module filter: ``ModuleName='PermitManagement'`` (PERMITS) and
``ModuleName IN ('BusinessLicenseEntity','BusinessLicenseManagement')`` (SLA).
COMPLAINTS_311 (CodeManagement = code enforcement) and DEEDS (ROD portal only)
are NOT registered.

Both feeds are native POINT layers (outSR=4326 on query), so the client lifts
geometry to ``latitude``/``longitude`` and ``needs_geocode`` stays False. There
are NO address columns (every row has ``SpatialType='Address'``, a server-side
geocode flag, plus a ``SpatialID`` GUID). The watermark is ``ApplicationDate``
(esriFieldTypeDate — epoch-ms on the wire, ISO after ArcGISClient flatten).

Tests pass WITHOUT a spine registration (no CityId.SPARTANBURG): the producers
resolve city_id="spartanburg" as a plain string, the leaf-local field maps are
pinned via resolve_field_map patches, and geocoding is mocked at
src.spatial.geocoder.geocode_row_if_declared (Virginia Beach / Lynchburg
pattern).

Live fixtures captured from the 2026-08-28 live re-probe (byte-verbatim
attribute values). ArcGIS epoch-ms dates are shown flattened to the ISO strings
the client produces; the wire value is noted per fixture. The ``longitude`` /
``latitude`` keys are the client's geometry lift (``longitude``=x,
``latitude``=y).

Stability contract: these tests assert PARSE fields, source-neighborhood
passthrough (none for this feed), H3-from-fixture-coordinates, bbox
containment, and field-map mappings — deliberately NOT division/borough
resolution results and NOT geocode-hook call counts, both of which shift when
the spine lands.
"""

import h3
from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_spartanburg import (
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
    SPARTANBURG_FIELD_MAP,
)
from src.producers.watermarks import newest_typed_watermark, typed_watermark_entry
from src.spatial.cities.spartanburg import (
    REGISTRATION,
    SPARTANBURG_CENTER,
    SPARTANBURG_CITY_ID,
    SPARTANBURG_DIVISION_BBOXES,
    SPARTANBURG_DIVISIONS,
    SPARTANBURG_FEATURESERVER_URL,
    SPARTANBURG_FEED_SPECS,
    SPARTANBURG_GEOCODE_CONTEXT,
    SPARTANBURG_METRO_BBOX,
    SPARTANBURG_PERMITS_ENDPOINT,
    SPARTANBURG_SLA_ENDPOINT,
    SPARTANBURG_SUBMARKETS,
    get_spartanburg_dataset,
    is_in_spartanburg_metro,
)
from src.spatial.city_registry import FeedType


# ---------------------------------------------------------------------------
# Live fixtures (2026-08-28 live re-probe, maps.spartanburgcounty.org /5).
# ---------------------------------------------------------------------------

# Newest PermitManagement row by ApplicationDate DESC (wire epoch 1787933333000
# flattens to the fixture ISO). Native point. Newest same-day 2026-08-28T16:08:53Z.
PERMITS_ROW_NEWEST = {
    "OBJECTID": 441509,
    "ModuleName": "PermitManagement",
    "CaseID": "bb9dfe9d-9730-4fc1-9627-79c5738afaf5",
    "CaseNumber": "BRMECHANIC-0826-4236",
    "CaseType": "Mechanical (Residential)",
    "WorkClass": "HVAC Changeout",
    "ApplicationDate": "2026-08-28T16:08:53+00:00",
    "ProjectID": " ",
    "ProjectName": "",
    "GISHistoryQueueID": "5b1e5942-7f08-43fc-8446-b876d5b401d3",
    "SpatialType": "Address",
    "SpatialID": "93193aa1-d8d5-4a97-8c1c-44680b4819a0",
    "longitude": -82.19186976577463,
    "latitude": 35.19298449304841,
}

# Demolition (Residential) / Residential Demolition (wire epoch 1787921922000).
# Classifies to JobType.DM.
PERMITS_ROW_DEMOLITION = {
    "OBJECTID": 441482,
    "ModuleName": "PermitManagement",
    "CaseID": "16954def-6034-4541-ab65-6e924d521f95",
    "CaseNumber": "BRDEMOLISH-0826-0698",
    "CaseType": "Demolition (Residential)",
    "WorkClass": "Residential Demolition",
    "ApplicationDate": "2026-08-28T12:58:42+00:00",
    "ProjectID": " ",
    "ProjectName": "",
    "GISHistoryQueueID": "affb093f-a2c8-429c-ba02-a58430c25b1c",
    "SpatialType": "Address",
    "SpatialID": "14d44340-fb2c-49cd-80f2-83dff2fa3bf4",
    "longitude": -82.12658363651074,
    "latitude": 34.78404387059208,
}

# Building (Residential) / Alteration, Remodel, Repair (wire epoch 1787917929000).
# Classifies to JobType.A2.
PERMITS_ROW_ALTERATION = {
    "OBJECTID": 441472,
    "ModuleName": "PermitManagement",
    "CaseID": "c8d21955-7399-4f7c-b124-35c1f99af609",
    "CaseNumber": "BLDRESDNTL-0826-22014",
    "CaseType": "Building (Residential)",
    "WorkClass": "Alteration, Remodel, Repair",
    "ApplicationDate": "2026-08-28T11:52:09+00:00",
    "ProjectID": " ",
    "ProjectName": "",
    "GISHistoryQueueID": "eb5b2c49-7b57-4f3c-bcaf-4487108ae44f",
    "SpatialType": "Address",
    "SpatialID": "d1902159-d5fb-47ad-b4c3-494082482de8",
    "longitude": -82.20823694002038,
    "latitude": 34.95898230137291,
}

# Newest SLA row (BusinessLicenseManagement) by ApplicationDate DESC (wire epoch
# 1783511700000 flattens to the fixture ISO). Trickle — 2026-07-08T11:55:00Z.
SLAROW_ZPANNUFOOD = {
    "OBJECTID": 417364,
    "ModuleName": "BusinessLicenseManagement",
    "CaseID": "ddefad55-467f-4f93-9f55-cd1b3e109874",
    "CaseNumber": "ZPANNUFOOD-000521-2026",
    "CaseType": "Mobile Food Service Vendor Annual Zoning Permit",
    "WorkClass": "Mobile Food Service Vendor Annual Zoning Permit ",
    "ApplicationDate": "2026-07-08T11:55:00+00:00",
    "ProjectID": " ",
    "ProjectName": "",
    "GISHistoryQueueID": "1f9e3ec0-d645-460a-8776-0d6cdd214924",
    "SpatialType": "Address",
    "SpatialID": "21416265-6f80-479c-bbbc-d79f2e7d24ea",
    "longitude": -82.16361301048246,
    "latitude": 34.91440800906092,
}

# BusinessLicenseEntity row whose CaseNumber is the business NAME, byte-verbatim
# HTML-escaped (wire epoch 1783468800000 -> 2026-07-08T00:00:00Z). The producer
# does NOT HTML-unescape, so license_id/dba carry `&amp;` verbatim.
SLAROW_BRAT_CURRY = {
    "OBJECTID": 416954,
    "ModuleName": "BusinessLicenseEntity",
    "CaseID": "0957a079-fad2-49b1-bd06-09e60320a735",
    "CaseNumber": "Brat &amp; Curry Co",
    "CaseType": "Limited Liability Company",
    "WorkClass": "",
    "ApplicationDate": "2026-07-08T00:00:00+00:00",
    "ProjectID": " ",
    "ProjectName": "",
    "GISHistoryQueueID": "395c03bd-d134-41b7-b31e-2ca15c37a532",
    "SpatialType": "Address",
    "SpatialID": "ebd9ed0b-5a25-435a-8a34-78872ddb35e8",
    "longitude": -82.16361301048246,
    "latitude": 34.91440800906092,
}

# Mocked ADR-0004 geocodes (native point rows never reach the geocoder, but the
# SLA null-coord tolerance test exercises it). Address-plausible, inside metro:
PERMITS_GEOCODE_DUMMY = (34.9500, -81.9300)
SLA_GEOCODE_DUMMY = (34.9500, -81.9300)


def _h3_res7(lat: float, lng: float) -> str:
    return h3.cell_to_parent(h3.latlng_to_cell(lat, lng, 9), 7)


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


@pytest.fixture
def permits():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        return DOBPermitsProducer()


@pytest.fixture
def sla():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        return SLALicensesProducer()


class TestSpartanburgSpatial:
    def test_city_id_constant(self):
        assert SPARTANBURG_CITY_ID == "spartanburg"

    def test_metro_contains_registration_center(self):
        assert is_in_spartanburg_metro(
            SPARTANBURG_CENTER["lat"], SPARTANBURG_CENTER["lng"]
        ) is True

    def test_metro_contains_known_landmarks(self):
        assert is_in_spartanburg_metro(34.9497, -81.9320) is True  # Downtown
        assert is_in_spartanburg_metro(34.9091, -82.2270) is True  # Greer
        assert is_in_spartanburg_metro(34.7390, -82.0320) is True  # Woodruff
        assert is_in_spartanburg_metro(35.1280, -82.0300) is True  # Landrum
        assert is_in_spartanburg_metro(34.8716, -81.9658) is True  # Roebuck

    def test_metro_rejects_null_and_neighbors(self):
        assert is_in_spartanburg_metro(None, None) is False
        assert is_in_spartanburg_metro(34.60, -82.30) is False  # Greenville Co
        assert is_in_spartanburg_metro(35.30, -82.10) is False  # NC (Polk/Laurens)
        assert is_in_spartanburg_metro(34.40, -81.70) is False  # Union Co SC
        assert is_in_spartanburg_metro(35.00, -81.50) is False  # Union/Cherokee edge
        assert is_in_spartanburg_metro(34.90, -82.40) is False  # Greenville Co
        assert is_in_spartanburg_metro(35.05, -82.30) is False  # Tryon west (NC)

    def test_metro_bbox_grounded_in_county_extent(self):
        """Live County_Line FeatureServer/0 extent, EPSG:3361 -> 4326 (2026-08-28):
        lng -82.2316..-81.7104, lat 34.5771..35.2001. The metro box must cover it
        with margin (the max_lng fix -81.71 -> -81.69 keeps the east edge in)."""
        assert SPARTANBURG_METRO_BBOX["min_lat"] <= 34.5771
        assert SPARTANBURG_METRO_BBOX["max_lat"] >= 35.2001
        assert SPARTANBURG_METRO_BBOX["min_lng"] <= -82.2316
        assert SPARTANBURG_METRO_BBOX["max_lng"] >= -81.7104

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in SPARTANBURG_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= SPARTANBURG_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= SPARTANBURG_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= SPARTANBURG_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= SPARTANBURG_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in SPARTANBURG_SUBMARKETS.items():
            bbox = SPARTANBURG_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in SPARTANBURG_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(SPARTANBURG_SUBMARKETS)

    def test_submarkets_carry_spartanburg_city_id(self):
        assert {m.city_id for m in SPARTANBURG_SUBMARKETS.values()} == {"spartanburg"}

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in SPARTANBURG_DIVISIONS.items():
            bbox = SPARTANBURG_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_division_count(self):
        assert len(SPARTANBURG_DIVISIONS) == 6
        for div in SPARTANBURG_DIVISIONS.values():
            assert div.city_id == "spartanburg"

    def test_submarket_count(self):
        assert len(SPARTANBURG_SUBMARKETS) == 10

    def test_registration_bundles_leaf_constants(self):
        assert REGISTRATION.metro_bbox is SPARTANBURG_METRO_BBOX
        assert REGISTRATION.submarkets is SPARTANBURG_SUBMARKETS
        assert REGISTRATION.contains is is_in_spartanburg_metro


class TestFeedRegistration:
    def test_exactly_two_feed_types_are_registered(self):
        assert set(SPARTANBURG_FEED_SPECS) == {"permits", "sla"}

    def test_both_feeds_share_the_one_featureserver_layer(self):
        base = (
            "https://maps.spartanburgcounty.org/server/rest/services/"
            "EnerGov/EnerGov_Spatial_Collections/FeatureServer/5"
        )
        assert SPARTANBURG_FEATURESERVER_URL == base
        assert SPARTANBURG_PERMITS_ENDPOINT == base
        assert SPARTANBURG_SLA_ENDPOINT == base

    def test_permits_spec_matches_probe_contract(self):
        spec = get_spartanburg_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == SPARTANBURG_PERMITS_ENDPOINT
        assert spec.watermark_col == "ApplicationDate"
        # True date column — client flattens to ISO; no ADR-0005 declaration.
        assert spec.watermark_type is None
        assert spec.watermark_format is None
        assert spec.id_keys == ["CaseNumber", "OBJECTID"]
        assert spec.producer_key == "permits"
        assert spec.needs_geocode is False
        assert spec.where == "ModuleName='PermitManagement'"
        assert spec.order_by == "OBJECTID"
        assert spec.oid_field == "OBJECTID"
        assert spec.expected_cadence_days == 1
        assert spec.field_map is PERMITS_FIELD_MAP

    def test_sla_spec_declares_trickle_cadence_and_module_filter(self):
        spec = get_spartanburg_dataset(FeedType.SLA)
        assert spec.platform == "arcgis"
        assert spec.endpoint == SPARTANBURG_SLA_ENDPOINT
        assert spec.watermark_col == "ApplicationDate"
        assert spec.watermark_type is None
        assert spec.id_keys == ["CaseNumber", "CaseID", "OBJECTID"]
        assert spec.producer_key == "sla"
        assert spec.needs_geocode is False
        assert spec.where == (
            "ModuleName IN ('BusinessLicenseEntity','BusinessLicenseManagement')"
        )
        assert spec.order_by == "OBJECTID"
        assert spec.expected_cadence_days == 30
        assert spec.field_map is SLA_FIELD_MAP

    @pytest.mark.parametrize(
        "absent_feed",
        [FeedType.COMPLAINTS_311, FeedType.DEEDS, FeedType.CRIME, FeedType.STR],
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'spartanburg'.*available"):
            get_spartanburg_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert FIELD_MAP["permits"] is PERMITS_FIELD_MAP
        assert FIELD_MAP["sla"] is SLA_FIELD_MAP
        assert SPARTANBURG_FIELD_MAP is FIELD_MAP
        assert GEOCODE_CONTEXT == SPARTANBURG_GEOCODE_CONTEXT == "Spartanburg, SC"
        assert "311" not in FIELD_MAP

    def test_featureserver_host_is_ansi_date_literal(self):
        """The host must be added to ANSI_DATE_LITERAL_HOSTS in the spine (the
        leaf does NOT edit watermarks.py). Pin the host string so the spine hold
        registers the URL verbatim."""
        assert "maps.spartanburgcounty.org" in SPARTANBURG_FEATURESERVER_URL


class TestSpartanburgFieldMaps:
    def test_permits_map_reads_live_columns(self):
        row = PERMITS_ROW_NEWEST
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "BRMECHANIC-0826-4236"
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_type") == "HVAC Changeout"
        assert (
            first_mapped(row, PERMITS_FIELD_MAP, "issuance_date")
            == "2026-08-28T16:08:53+00:00"
        )

    def test_permits_map_has_no_address_or_coordinate_candidates(self):
        """The layer carries NO address columns (SpatialType='Address' is a
        server-side geocode flag) and coordinates come from the native point, so
        the map declares neither address nor coordinate candidates."""
        assert "address_street" not in PERMITS_FIELD_MAP
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP
        assert "filing_date" not in PERMITS_FIELD_MAP
        assert "bbl" not in PERMITS_FIELD_MAP
        assert "cost" not in PERMITS_FIELD_MAP

    def test_sla_map_reads_live_columns(self):
        row = SLAROW_ZPANNUFOOD
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "ZPANNUFOOD-000521-2026"
        assert (
            first_mapped(row, SLA_FIELD_MAP, "license_type")
            == "Mobile Food Service Vendor Annual Zoning Permit"
        )
        assert (
            first_mapped(row, SLA_FIELD_MAP, "effective_date")
            == "2026-07-08T11:55:00+00:00"
        )

    def test_sla_html_escaped_business_name_preserved(self):
        """BusinessLicenseEntity rows carry the business NAME as CaseNumber,
        byte-verbatim HTML-escaped. first_mapped must return it untouched (the
        producer does not HTML-unescape)."""
        row = SLAROW_BRAT_CURRY
        assert row["CaseNumber"] == "Brat &amp; Curry Co"
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "Brat &amp; Curry Co"
        assert first_mapped(row, SLA_FIELD_MAP, "dba") == "Brat &amp; Curry Co"
        assert first_mapped(row, SLA_FIELD_MAP, "premises_name") == "Brat &amp; Curry Co"

    def test_sla_map_falls_back_to_case_guid(self):
        row = {**SLAROW_BRAT_CURRY, "CaseNumber": ""}
        # Empty CaseNumber falls through to the CaseID GUID.
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "0957a079-fad2-49b1-bd06-09e60320a735"

    def test_sla_map_has_no_address_or_coordinate_candidates(self):
        assert "address_street" not in SLA_FIELD_MAP
        assert "latitude" not in SLA_FIELD_MAP
        assert "longitude" not in SLA_FIELD_MAP


class TestWatermarkTyping:
    def test_permits_applicationdate_iso_parses(self):
        entry = typed_watermark_entry("2026-08-28T16:08:53+00:00")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 28)

    def test_sla_applicationdate_iso_parses(self):
        entry = typed_watermark_entry("2026-07-08T11:55:00+00:00")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 7, 8)

    def test_newest_across_both_feeds_is_permits(self):
        newest = newest_typed_watermark(
            [
                "2026-08-28T16:08:53+00:00",  # permits ApplicationDate
                "2026-07-08T11:55:00+00:00",  # SLA ApplicationDate
            ]
        )
        assert newest is not None
        assert newest[0].startswith("2026-08-28")

    def test_empty_watermark_values_are_dropped(self):
        assert typed_watermark_entry("") is None
        assert typed_watermark_entry(None) is None


class TestSpartanburgPermitParsing:
    def test_native_point_permit_parses_with_original_coordinates(
        self, permits, monkeypatch
    ):
        """Spartanburg permits are native POINT (not address-only): the client
        lifts geometry to latitude/longitude, so the parsed event carries the
        fixture coordinates and derives its H3 cells from them — no geocode call."""
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_DUMMY,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_NEWEST, city_id="spartanburg")
        assert event is not None
        assert event.city_id == "spartanburg"
        assert event.job_id == "BRMECHANIC-0826-4236"
        assert event.latitude == pytest.approx(35.19298449304841)
        assert event.longitude == pytest.approx(-82.19186976577463)
        assert event.h3_res7 == _h3_res7(35.19298449304841, -82.19186976577463)
        assert is_in_spartanburg_metro(event.latitude, event.longitude)

    def test_geocode_sits_inside_metro(self):
        assert is_in_spartanburg_metro(35.19298449304841, -82.19186976577463)
        assert is_in_spartanburg_metro(34.78404387059208, -82.12658363651074)
        assert is_in_spartanburg_metro(34.95898230137291, -82.20823694002038)

    def test_applicationdate_parses_to_issuance_date(self, permits, monkeypatch):
        """ApplicationDate is a true date-typed column — the client flattens it
        to ISO and the producer's date chain parses it into issuance_date."""
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_DUMMY,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_NEWEST, city_id="spartanburg")
        assert event is not None
        assert str(event.issuance_date).startswith("2026-08-28")

    def test_demolition_classifies_as_dm(self, permits, monkeypatch):
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_DUMMY,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_DEMOLITION, city_id="spartanburg")
        assert event is not None
        assert event.job_id == "BRDEMOLISH-0826-0698"
        assert event.job_type == JobType.DM

    def test_alteration_classifies_as_a2(self, permits, monkeypatch):
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_DUMMY,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_ALTERATION, city_id="spartanburg")
        assert event is not None
        assert event.job_id == "BLDRESDNTL-0826-22014"
        assert event.job_type == JobType.A2

    def test_native_point_permit_has_no_address(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_DUMMY,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_NEWEST, city_id="spartanburg")
        assert event is not None
        assert event.address_street is None


class TestSpartanburgSlaParsing:
    def test_native_point_license_parses_with_original_coordinates(
        self, sla, monkeypatch
    ):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: SLA_GEOCODE_DUMMY,
        )
        event = sla.parse_socrata_row(SLAROW_ZPANNUFOOD, city_id="spartanburg")
        assert event is not None
        assert event.city_id == "spartanburg"
        assert event.license_id == "ZPANNUFOOD-000521-2026"
        assert event.license_type == "Mobile Food Service Vendor Annual Zoning Permit"
        assert event.latitude == pytest.approx(34.91440800906092)
        assert event.longitude == pytest.approx(-82.16361301048246)
        assert event.h3_res7 == _h3_res7(34.91440800906092, -82.16361301048246)
        assert event.h3_res9 is not None
        assert is_in_spartanburg_metro(event.latitude, event.longitude)

    def test_html_escaped_business_name_survives_verbatim(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: SLA_GEOCODE_DUMMY,
        )
        event = sla.parse_socrata_row(SLAROW_BRAT_CURRY, city_id="spartanburg")
        assert event is not None
        assert event.license_id == "Brat &amp; Curry Co"
        assert event.dba == "Brat &amp; Curry Co"
        assert event.license_type == "Limited Liability Company"

    def test_applicationdate_parses_to_effective_date(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: SLA_GEOCODE_DUMMY,
        )
        event = sla.parse_socrata_row(SLAROW_ZPANNUFOOD, city_id="spartanburg")
        assert event is not None
        assert str(event.effective_date).startswith("2026-07-08")

    def test_address_is_none_for_native_point(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: SLA_GEOCODE_DUMMY,
        )
        event = sla.parse_socrata_row(SLAROW_ZPANNUFOOD, city_id="spartanburg")
        assert event is not None
        assert event.address is None

    def test_coordinate_less_row_keeps_null_coord_event(self, sla, monkeypatch):
        """SLA producer tolerance: a row whose client did NOT lift geometry
        (no latitude/longitude) still emits as a null-lat/lng/null-H3 event (DC
        precedent) rather than being dropped. The geocoder is mocked to return
        None so the address-less row stays non-spatial."""
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        row = {
            k: v
            for k, v in SLAROW_ZPANNUFOOD.items()
            if k not in ("latitude", "longitude")
        }
        event = sla.parse_socrata_row(row, city_id="spartanburg")
        assert event is not None
        assert event.latitude is None and event.longitude is None
        assert event.h3_res7 is None and event.h3_res9 is None
