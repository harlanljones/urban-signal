"""Unit tests for the St. Louis leaf (US-200): spatial module + field maps +
EPSG:3857 311 coordinates + CSV specs.

These tests run with NO spine registration (no CityId.ST_LOUIS, no ALIASES
entry, no DatasetSpec in REGISTRY). They exercise the leaf directly.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_st_louis import FIELD_MAP, GEOCODE_CONTEXT
from src.spatial.cities.st_louis import (
    STL_311_ENDPOINT,
    STL_311_SPEC,
    STL_PERMITS_ENDPOINT,
    STL_PERMITS_SPEC,
    STL_SLA_ENDPOINT,
    STL_SLA_SPEC,
    ST_LOUIS_311_FIELD_MAP,
    ST_LOUIS_ALIASES,
    ST_LOUIS_CITY_ID,
    ST_LOUIS_DIVISION_BBOXES,
    ST_LOUIS_DIVISIONS,
    ST_LOUIS_FEED_SPECS,
    ST_LOUIS_GEOCODE_CONTEXT,
    ST_LOUIS_JOB_SUFFIX,
    ST_LOUIS_METRO_BBOX,
    ST_LOUIS_PERMITS_FIELD_MAP,
    ST_LOUIS_SLA_FIELD_MAP,
    ST_LOUIS_SUBMARKETS,
    attach_wgs84_from_srxy,
    get_st_louis_dataset,
    is_active_excise_license,
    is_excise_expiration_sentinel,
    is_in_st_louis_metro,
    is_wgs84_degrees,
    mercator_xy_to_wgs84,
    permit_composite_id,
)
from src.spatial.city_registry import FeedType
from src.spatial.geocoder import _STATE_RE, normalize_address


# Live-probe fixtures captured 2026-08-27 from stlouis-mo.gov CSB / CF / excise.
# 1100 Ohio St: SRX/SRY are EPSG:3857, not degrees.
_311_FIXTURE = {
    "requestid": "2121679",
    "datetimeinit": "2026-08-27 05:54:02.043",
    "probaddress": "1100 OHIO ST",
    "status": "WEB",
    "problemcode": "Street Repair",
    "srx": "-10043376.82",
    "sry": "4667655.54",
}

_PERMITS_FIXTURE = {
    "address": "2200 GRAVOIS AVE",
    "projecttype": "Commercial",
    "structuretype": "Alteration",
    "applicationdate": "July, 28 2026 00:00:00",
    "issuedate": "August, 07 2026 00:00:00",
    "daystoissue": "10",
    "estprojectcost": "125000",
    "applicationdescription": "Interior renovation of existing storefront",
}

_SLA_FIXTURE = {
    "case_number": "EXC-2026-4412",
    "id": "18801",
    "status_code": "ACTIVE",
    "date_expiration": "2027-06-30",
    "location": "1600 S 7TH ST",
    "dba": "SOULARD SOCIAL",
}

# Probe sample: (-10043376.82, 4667655.54) → (-90.2212, 38.6219) at 1100 Ohio St.
_OHIO_ST_WGS84 = (38.6219, -90.2212)
_GRAVOIS_GEOCODE = (38.5920, -90.2260)
_SOULARD_GEOCODE = (38.6045, -90.2085)


# ---------------------------------------------------------------------------
# Spatial invariants (no registry needed)
# ---------------------------------------------------------------------------

class TestStLouisSpatial:
    def test_city_id_and_aliases(self):
        assert ST_LOUIS_CITY_ID == "st_louis"
        assert "stl" in ST_LOUIS_ALIASES
        assert ST_LOUIS_JOB_SUFFIX == "stl"

    def test_metro_contains_center(self):
        assert is_in_st_louis_metro(38.6270, -90.1994) is True
        assert is_in_st_louis_metro(38.6447, -90.2614) is True  # CWE
        assert is_in_st_louis_metro(38.6045, -90.2085) is True  # Soulard

    def test_metro_rejects_null_county_and_illinois(self):
        assert is_in_st_louis_metro(None, None) is False
        assert is_in_st_louis_metro(38.643, -90.338) is False  # Clayton (County)
        assert is_in_st_louis_metro(38.625, -90.151) is False  # East St. Louis, IL
        assert is_in_st_louis_metro(38.627, -90.407) is False  # Kirkwood (County)

    def test_live_311_sample_sits_inside_the_metro_bbox(self):
        lat, lng = mercator_xy_to_wgs84(_311_FIXTURE["srx"], _311_FIXTURE["sry"])
        assert is_in_st_louis_metro(lat, lng)

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in ST_LOUIS_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= ST_LOUIS_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= ST_LOUIS_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= ST_LOUIS_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= ST_LOUIS_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in ST_LOUIS_SUBMARKETS.items():
            bbox = ST_LOUIS_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in ST_LOUIS_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(ST_LOUIS_SUBMARKETS)

    def test_submarkets_carry_st_louis_city_id(self):
        assert {m.city_id for m in ST_LOUIS_SUBMARKETS.values()} == {"st_louis"}

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in ST_LOUIS_DIVISIONS.items():
            bbox = ST_LOUIS_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name


# ---------------------------------------------------------------------------
# EPSG:3857 — raw SRX/SRY must not be ingested as WGS84 degrees
# ---------------------------------------------------------------------------

class TestMercatorSrxSry:
    def test_raw_srx_sry_are_not_wgs84_degrees(self):
        x, y = float(_311_FIXTURE["srx"]), float(_311_FIXTURE["sry"])
        assert abs(x) > 180
        assert abs(y) > 90
        assert is_wgs84_degrees(y, x) is False
        # Mapping SRY→lat / SRX→lng would be the Boston-SLA failure mode.
        assert is_wgs84_degrees(_311_FIXTURE["sry"], _311_FIXTURE["srx"]) is False

    def test_helper_converts_ohio_st_sample_to_wgs84(self):
        lat, lng = mercator_xy_to_wgs84(_311_FIXTURE["srx"], _311_FIXTURE["sry"])
        assert lat == pytest.approx(_OHIO_ST_WGS84[0], abs=1e-4)
        assert lng == pytest.approx(_OHIO_ST_WGS84[1], abs=1e-4)
        assert is_wgs84_degrees(lat, lng) is True
        assert is_in_st_louis_metro(lat, lng)

    def test_field_map_does_not_put_srx_sry_in_lat_lng_slots(self):
        assert "latitude" not in ST_LOUIS_311_FIELD_MAP
        assert "longitude" not in ST_LOUIS_311_FIELD_MAP
        for slot in ("latitude", "longitude"):
            candidates = [c.lower() for c in ST_LOUIS_311_FIELD_MAP.get(slot, [])]
            assert "srx" not in candidates
            assert "sry" not in candidates

    def test_first_mapped_latitude_is_none_on_raw_csb_row(self):
        assert first_mapped(_311_FIXTURE, ST_LOUIS_311_FIELD_MAP, "latitude") is None
        assert first_mapped(_311_FIXTURE, ST_LOUIS_311_FIELD_MAP, "longitude") is None

    def test_attach_helper_writes_wgs84_without_mutating_raw_xy(self):
        attached = attach_wgs84_from_srxy(_311_FIXTURE)
        assert attached["srx"] == _311_FIXTURE["srx"]
        assert is_wgs84_degrees(attached["latitude"], attached["longitude"])
        assert attached["latitude"] == pytest.approx(_OHIO_ST_WGS84[0], abs=1e-4)


# ---------------------------------------------------------------------------
# Field maps
# ---------------------------------------------------------------------------

class TestStLouisFieldMaps:
    def test_311_map_reads_normalized_csb_columns(self):
        row = _311_FIXTURE
        assert first_mapped(row, ST_LOUIS_311_FIELD_MAP, "incident_id") == "2121679"
        assert first_mapped(row, ST_LOUIS_311_FIELD_MAP, "created_date") == (
            "2026-08-27 05:54:02.043"
        )
        assert first_mapped(row, ST_LOUIS_311_FIELD_MAP, "incident_address") == "1100 OHIO ST"
        assert first_mapped(row, ST_LOUIS_311_FIELD_MAP, "status") == "WEB"

    def test_permits_map_reads_normalized_cf_columns(self):
        row = _PERMITS_FIXTURE
        assert first_mapped(row, ST_LOUIS_PERMITS_FIELD_MAP, "job_id") == "2200 GRAVOIS AVE"
        assert first_mapped(row, ST_LOUIS_PERMITS_FIELD_MAP, "issuance_date") == (
            "August, 07 2026 00:00:00"
        )
        assert first_mapped(row, ST_LOUIS_PERMITS_FIELD_MAP, "address_street") == (
            "2200 GRAVOIS AVE"
        )
        assert first_mapped(row, ST_LOUIS_PERMITS_FIELD_MAP, "cost") == "125000"

    def test_permits_have_no_coordinate_candidates(self):
        assert "latitude" not in ST_LOUIS_PERMITS_FIELD_MAP
        assert "longitude" not in ST_LOUIS_PERMITS_FIELD_MAP

    def test_sla_map_reads_normalized_excise_columns(self):
        row = _SLA_FIXTURE
        assert first_mapped(row, ST_LOUIS_SLA_FIELD_MAP, "license_id") == "EXC-2026-4412"
        assert first_mapped(row, ST_LOUIS_SLA_FIELD_MAP, "expiration_date") == "2027-06-30"
        assert first_mapped(row, ST_LOUIS_SLA_FIELD_MAP, "address_street") == "1600 S 7TH ST"
        assert first_mapped(row, ST_LOUIS_SLA_FIELD_MAP, "status") == "ACTIVE"

    def test_sla_has_no_coordinate_candidates(self):
        assert "latitude" not in ST_LOUIS_SLA_FIELD_MAP
        assert "longitude" not in ST_LOUIS_SLA_FIELD_MAP

    def test_map_is_the_exported_field_map(self):
        assert FIELD_MAP["311"] is ST_LOUIS_311_FIELD_MAP
        assert FIELD_MAP["permits"] is ST_LOUIS_PERMITS_FIELD_MAP
        assert FIELD_MAP["sla"] is ST_LOUIS_SLA_FIELD_MAP

    def test_geocode_context_is_st_louis_mo(self):
        assert GEOCODE_CONTEXT == ST_LOUIS_GEOCODE_CONTEXT == "St. Louis, MO"


# ---------------------------------------------------------------------------
# Feed specs (leaf-local; no CityId.ST_LOUIS)
# ---------------------------------------------------------------------------

class TestFeedRegistration:
    def test_partial_city_registers_three_feeds(self):
        assert set(ST_LOUIS_FEED_SPECS) == {"311", "permits", "sla"}

    def test_specs_are_city_hosted_transactional_sources(self):
        """Keep the registration on the probed St. Louis publishing surface."""
        for spec in ST_LOUIS_FEED_SPECS.values():
            assert spec["platform"] == "csv"
            assert "stlouis-mo.gov" in spec["endpoint"]
            assert "socrata" not in spec["endpoint"].lower()
            assert "arcgis" not in spec["endpoint"].lower()

    def test_producer_keys_match_feed_names(self):
        for feed_name, spec in ST_LOUIS_FEED_SPECS.items():
            assert spec["producer_key"] == feed_name

    def test_311_spec_is_zip_year_member_mercator(self):
        extra = STL_311_SPEC["extra"]
        assert STL_311_SPEC["platform"] == "csv"
        assert STL_311_SPEC["watermark_col"] == "datetimeinit"
        assert STL_311_SPEC["id_keys"] == ["requestid"]
        assert STL_311_SPEC["endpoint"] == STL_311_ENDPOINT
        assert extra["zip_member"] is True
        assert extra["src_crs"] == "EPSG:3857"
        assert extra["endpoint_by_year"] == {"2026": "2026.csv", "2027": "2027.csv"}
        assert extra["expected_cadence_days"] == 1

    def test_permits_spec_is_rolling_address_only(self):
        extra = STL_PERMITS_SPEC["extra"]
        assert STL_PERMITS_SPEC["platform"] == "csv"
        assert STL_PERMITS_SPEC["watermark_col"] == "issuedate"
        assert STL_PERMITS_SPEC["endpoint"] == STL_PERMITS_ENDPOINT
        assert extra["needs_geocode"] is True
        assert extra["expected_cadence_days"] == 21
        assert extra["rolling_window_days"] == 30
        assert extra["watermark_format"] == "%B, %d %Y %H:%M:%S"

    def test_sla_spec_is_liquor_snapshot(self):
        extra = STL_SLA_SPEC["extra"]
        assert STL_SLA_SPEC["platform"] == "csv"
        assert STL_SLA_SPEC["watermark_col"] == "date_expiration"
        assert STL_SLA_SPEC["endpoint"] == STL_SLA_ENDPOINT
        assert extra["ingestion_mode"] == "snapshot"
        assert extra["needs_geocode"] is True
        assert extra["where"] == "status_code = 'ACTIVE'"
        assert extra["expected_cadence_days"] == 1

    def test_get_dataset_builds_typed_specs_without_cityid(self):
        complaints = get_st_louis_dataset(FeedType.COMPLAINTS_311)
        assert complaints.platform == "csv"
        assert complaints.watermark_col == "datetimeinit"
        assert complaints.endpoint_by_year["2026"] == "2026.csv"
        assert complaints.field_map == ST_LOUIS_311_FIELD_MAP

        permits = get_st_louis_dataset(FeedType.PERMITS)
        assert permits.needs_geocode is True
        assert permits.rolling_window_days == 30
        assert permits.expected_cadence_days == 21
        assert permits.watermark_format == "%B, %d %Y %H:%M:%S"

        sla = get_st_louis_dataset(FeedType.SLA)
        assert sla.ingestion_mode == "snapshot"
        assert sla.needs_geocode is True
        assert sla.where == "status_code = 'ACTIVE'"

    @pytest.mark.parametrize("absent_feed", [FeedType.DEEDS, FeedType.STR, FeedType.CRIME])
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'st_louis'.*available"):
            get_st_louis_dataset(absent_feed)

    def test_permit_issuedate_format_parses_probe_text(self):
        fmt = STL_PERMITS_SPEC["extra"]["watermark_format"]
        parsed = datetime.strptime(_PERMITS_FIXTURE["issuedate"], fmt)
        assert parsed.year == 2026
        assert parsed.month == 8
        assert parsed.day == 7

    def test_permit_composite_id_separates_same_address_rows(self):
        other = {**_PERMITS_FIXTURE, "applicationdescription": "Roof replacement"}
        assert permit_composite_id(_PERMITS_FIXTURE) != permit_composite_id(other)
        assert _PERMITS_FIXTURE["address"] == other["address"]


# ---------------------------------------------------------------------------
# SLA snapshot filters (Baltimore liquor-only precedent)
# ---------------------------------------------------------------------------

class TestExciseSnapshotFilters:
    def test_active_row_is_kept(self):
        assert is_active_excise_license(_SLA_FIXTURE) is True

    def test_renewal_status_is_dropped(self):
        row = {**_SLA_FIXTURE, "status_code": "RENEWAL"}
        assert is_active_excise_license(row) is False

    def test_expiration_sentinels_1969_and_3027_are_dropped(self):
        assert is_excise_expiration_sentinel("1969-12-31") is True
        assert is_excise_expiration_sentinel("3027-07-02") is True
        assert is_excise_expiration_sentinel("2027-06-30") is False
        assert is_active_excise_license({**_SLA_FIXTURE, "date_expiration": "1969-12-31"}) is False
        assert is_active_excise_license({**_SLA_FIXTURE, "date_expiration": "3027-07-02"}) is False


# ---------------------------------------------------------------------------
# Geocoding caveats (ADR 0004) — registry-free
# ---------------------------------------------------------------------------

class TestGeocodingCaveats:
    def test_permit_address_has_no_state_token_so_context_appends(self):
        assert _STATE_RE.search("2200 GRAVOIS AVE".upper()) is None
        assert _STATE_RE.search("2200 GRAVOIS AVE, ST. LOUIS, MO".upper()) is not None

    def test_excise_location_has_no_state_token(self):
        assert _STATE_RE.search("1600 S 7TH ST".upper()) is None

    def test_unit_designator_normalization_preserves_context(self):
        norm = normalize_address("1600 S 7TH ST UNIT 2, ST. LOUIS, MO")
        assert "UNIT" not in norm
        assert "2" not in norm
        assert "ST. LOUIS" in norm or "ST LOUIS" in norm
        assert "MO" in norm


# ---------------------------------------------------------------------------
# Producer path with the St. Louis field map injected (no spine registration)
# ---------------------------------------------------------------------------

@pytest.fixture
def complaints():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        from src.producers.complaints_311_producer import Complaints311Producer

        return Complaints311Producer()


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


def _patch_resolve_and_geocode(monkeypatch, feed_key, geocode_side_effect):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )
    captured = []

    def fake_geocode(city_id, feed_value, address, context=None):
        captured.append((city_id, feed_value, address, context))
        return geocode_side_effect

    monkeypatch.setattr(
        "src.spatial.geocoder.geocode_row_if_declared",
        fake_geocode,
    )
    return captured


class TestStLouis311Parsing:
    def test_transformed_row_parses_without_treating_srxy_as_degrees(
        self, complaints, monkeypatch
    ):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: FIELD_MAP["311"],
        )
        event = complaints.parse_socrata_row(
            attach_wgs84_from_srxy(_311_FIXTURE), city_id="st_louis"
        )
        assert event is not None
        assert event.incident_id == "2121679"
        assert event.latitude == pytest.approx(_OHIO_ST_WGS84[0], abs=1e-4)
        assert event.longitude == pytest.approx(_OHIO_ST_WGS84[1], abs=1e-4)
        assert event.h3_res7 is not None
        # Raw mercator values must not leak onto the event.
        assert abs(event.latitude) <= 90
        assert abs(event.longitude) <= 180

    def test_raw_srxy_are_dropped_not_emitted_as_degrees(self, complaints, monkeypatch):
        # A mistaken latitude→sry map would feed meters into the parser.
        # The >90/>180 guard nulls those, then the spine EPSG:3857 path
        # recovers WGS84 from srx/sry — never emit mercator as degrees.
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: {
                **FIELD_MAP["311"],
                "latitude": ["sry"],
                "longitude": ["srx"],
            },
        )
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        event = complaints.parse_socrata_row(_311_FIXTURE, city_id="st_louis")
        assert event is not None
        assert event.latitude == pytest.approx(_OHIO_ST_WGS84[0], abs=1e-4)
        assert event.longitude == pytest.approx(_OHIO_ST_WGS84[1], abs=1e-4)
        assert abs(event.latitude) <= 90
        assert abs(event.longitude) <= 180


class TestStLouisPermitParsing:
    def test_address_only_permit_uses_declared_geocoder(self, permits, monkeypatch):
        captured = _patch_resolve_and_geocode(monkeypatch, "permits", _GRAVOIS_GEOCODE)
        event = permits.parse_socrata_row(_PERMITS_FIXTURE, city_id="st_louis")
        assert event is not None
        assert event.job_id == "2200 GRAVOIS AVE"
        assert event.latitude == pytest.approx(_GRAVOIS_GEOCODE[0])
        assert event.longitude == pytest.approx(_GRAVOIS_GEOCODE[1])
        assert captured == [
            ("st_louis", "permits", "2200 GRAVOIS AVE", None)
        ]

    def test_permit_row_without_address_is_dropped(self, permits, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: FIELD_MAP["permits"],
        )
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        row = {**_PERMITS_FIXTURE, "address": ""}
        assert permits.parse_socrata_row(row, city_id="st_louis") is None


class TestStLouisSlaParsing:
    def test_address_only_excise_row_uses_declared_geocoder(self, sla, monkeypatch):
        captured = _patch_resolve_and_geocode(monkeypatch, "sla", _SOULARD_GEOCODE)
        event = sla.parse_socrata_row(_SLA_FIXTURE, city_id="st_louis")
        assert event is not None
        assert event.license_id == "EXC-2026-4412"
        assert event.latitude == pytest.approx(_SOULARD_GEOCODE[0])
        assert event.longitude == pytest.approx(_SOULARD_GEOCODE[1])
        assert captured == [
            ("st_louis", "sla", "1600 S 7TH ST", None)
        ]
