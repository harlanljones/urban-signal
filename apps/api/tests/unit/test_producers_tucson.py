"""Unit tests for the Tucson, AZ leaf (US-328): spatial module + SLA field
map + parse chains through the real SLA producer path.

Tucson is a ONE-FEED PARTIAL metro: BUSLIC business licenses
(``PublicMaps/OpenData_EconomicDevelopment/MapServer/3``, Tier 2, ~93k
rows, native point geometry + FULLADDRESS). PERMITS is a 2022 row-freeze
archive and 311/DEEDS are absent — never registered. Tests pass WITHOUT a
spine registration (no CityId.TUCSON; ``city_id="tucson"`` strings only).

Wave-5 contract: these tests do NOT assert division/borough resolution
results or geocode-hook call counts (both change when the spine lands) —
they pin parse fields, source passthrough, H3 from fixture coordinates,
bbox containment, and field-map mappings.

Live fixtures captured 2026-08-28 byte-verbatim from
gis.tucsonaz.gov MapServer/3 (re-probe of docs/research/probe-tucson.md,
which was stamped 2026-08-27): row count 93,483; ``DT_START`` is the only
date column (epoch-ms → ISO via ArcGISClient); newest rows are
FUTURE-dated applications (2026-09-12 / 2026-09-03 — sentinels; OBJECTID
16 additionally has null geometry); newest non-future start 2026-05-29.
The host rejects ISO date literals in ``where`` (ANSI ``date '...'`` only
— the DC/Milwaukee/Charlotte family); ``DT_START <= CURRENT_TIMESTAMP``
works and is the sentinel guard.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.producers.acquisition import build_where, is_future_watermark
from src.producers.field_maps import first_mapped
from src.producers.field_maps_tucson import (
    DROPPED_NONADDRESS_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    SLA_FIELD_MAP,
)
from src.producers.sla_licenses_producer import _parse_datetime
from src.producers.watermarks import watermark_exclude_clause
from src.spatial.cities.tucson import (
    REGISTRATION,
    TUCSON_CITY_ID,
    TUCSON_DIVISIONS,
    TUCSON_DIVISION_BBOXES,
    TUCSON_FEED_SPECS,
    TUCSON_GEOCODE_CONTEXT,
    TUCSON_METRO_BBOX,
    TUCSON_SLA_ALARM_EXEMPT_REASON,
    TUCSON_SLA_ENDPOINT,
    TUCSON_SLA_WHERE,
    TUCSON_SUBMARKETS,
    get_tucson_dataset,
    is_in_greater_tucson_metro,
    is_in_tucson_metro,
)
from src.spatial.city_registry import FeedType
from src.spatial.h3_indexer import H3SpatialIndexer
from src.spatial.submarkets import SubmarketMeta

# ---------------------------------------------------------------------------
# Live fixtures (byte-verbatim attributes from the 2026-08-28 re-probe).
# DT_START epoch-ms ints are as served; latitude/longitude are what
# ArcGISClient._flatten_feature lifts from the outSR=4326 point geometry.
# CHAR-padded source columns (ACC_NUM / LIC_STATUS / STREETDIR / ZIP_CODE)
# are preserved verbatim — see field_maps_tucson docstring.
# ---------------------------------------------------------------------------

# Newest row on the layer — FUTURE-dated DT_START sentinel (2026-09-12),
# and geometry is null (ArcGISClient lifts no latitude/longitude).
SENTINEL_RAW_FEATURE = {
    "attributes": {
        "ACC_NAME": "NICHOLS BARBARA JANE",
        "ACC_NUM": "T3092163            ",
        "CITY": "PIMA COUNTY",
        "DT_START": 1789171200000,
        "FULLADDRESS": "5010 W SWEETWATER DR",
        "GlobalID": "{5409DBC8-D056-4231-889D-76787A993C82}",
        "HOME_OCCUPATION": "T",
        "LIC_STATUS": "Active              ",
        "LIC_TYPE": "BUS",
        "NAIC_CODE": "458210",
        "NAIC_DESC": "",
        "OBJECTID": 16,
        "OWN_TYPE": "Individual",
        "STATE": "AZ",
        "STREETDIR": "W         ",
        "STREETNAM": "SWEETWATER",
        "STREETNUM": "5010           ",
        "STREETSUF": "DR",
        "ZIP_CODE": "85745     ",
    },
    "geometry": None,
}

# Newest non-future row (DT_START 2026-05-29) — Broadway corridor.
TRADER_JOES_RAW_FEATURE = {
    "attributes": {
        "ACC_NAME": "TRADER JOES #288",
        "ACC_NUM": "T3091773",
        "CITY": "TUCSON",
        "DT_START": 1780012800000,
        "FULLADDRESS": "2150 E BROADWAY BL",
        "GlobalID": "{228CC67C-2A3B-4BB7-8DC9-FE16BDF2B11B}",
        "HOME_OCCUPATION": "F",
        "LIC_STATUS": "Application",
        "LIC_TYPE": "BUS",
        "NAIC_CODE": "445298",
        "NAIC_DESC": "",
        "OBJECTID": 6,
        "OWN_TYPE": "Corporation",
        "STATE": "AZ",
        "STREETDIR": "E",
        "STREETNAM": "BROADWAY",
        "STREETNUM": "2150",
        "STREETSUF": "BL",
        "ZIP_CODE": "85719",
    },
    "geometry": {"x": -110.93989797596089, "y": 32.221281920528575},
}

# Second-newest non-future row (DT_START 2026-05-20) — S 6th Ave.
REVIVE_RAW_FEATURE = {
    "attributes": {
        "ACC_NAME": "REVIVE HAIR LOUNGE LLC",
        "ACC_NUM": "T3092127",
        "DT_START": 1779235200000,
        "FULLADDRESS": "747 S 6TH AV STE 101",
        "GlobalID": "{4E64C5A8-E8D9-4F4F-8795-75388DEBF3DB}",
        "HOME_OCCUPATION": "F",
        "LIC_STATUS": "Application",
        "LIC_TYPE": "BUS",
        "NAIC_CODE": "812112",
        "NAIC_DESC": "Beauty Salons",
        "OBJECTID": 7,
        "OWN_TYPE": "LLC",
        "STATE": "AZ",
        "STREETDIR": "S",
        "STREETNAM": "6TH",
        "STREETNUM": "747",
        "STREETSUF": "AV",
        "ZIP_CODE": "85701",
        "CITY": "TUCSON",
    },
    "geometry": {"x": -110.96824347090345, "y": 32.21226392285235},
}

# Padded-columns row (DT_START 2026-05-12) — 34 W Columbia St.
SWEET_TOOTH_RAW_FEATURE = {
    "attributes": {
        "ACC_NAME": "SWEET TOOTH",
        "ACC_NUM": "T3092422            ",
        "CITY": "TUCSON",
        "DT_START": 1778544000000,
        "FULLADDRESS": "34 W COLUMBIA ST UNIT 2",
        "GlobalID": "{D0D528A2-7D5B-459D-9398-80B84871E7F9}",
        "HOME_OCCUPATION": "F",
        "LIC_STATUS": "Application         ",
        "LIC_TYPE": "BUS",
        "NAIC_CODE": "722330",
        "NAIC_DESC": "Mobile Food Services",
        "OBJECTID": 9,
        "OWN_TYPE": "LLC",
        "STATE": "AZ",
        "STREETDIR": "W         ",
        "STREETNAM": "COLUMBIA",
        "STREETNUM": "34             ",
        "STREETSUF": "ST",
        "ZIP_CODE": "85714     ",
    },
    "geometry": {"x": -110.96942247341907, "y": 32.173446928872636},
}


def _flatten(feature: dict) -> dict:
    """Flatten a raw ArcGIS feature exactly as the client does at fetch."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, {"DT_START"})


TRADER_JOES_ROW = _flatten(TRADER_JOES_RAW_FEATURE)
REVIVE_ROW = _flatten(REVIVE_RAW_FEATURE)
SWEET_TOOTH_ROW = _flatten(SWEET_TOOTH_RAW_FEATURE)
SENTINEL_ROW = _flatten(SENTINEL_RAW_FEATURE)

LIVE_FIXTURE_COORDS = (
    (TRADER_JOES_ROW["latitude"], TRADER_JOES_ROW["longitude"]),
    (REVIVE_ROW["latitude"], REVIVE_ROW["longitude"]),
    (SWEET_TOOTH_ROW["latitude"], SWEET_TOOTH_ROW["longitude"]),
)

# Downtown Tucson WGS84 (geocoder stub for null-geometry rows).
_GEOCODED = (32.2226, -110.9723)

_SUBMARKET_FIELDS = (
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
# Spatial invariants (no registry needed)
# ---------------------------------------------------------------------------


class TestTucsonSpatial:
    def test_city_id_constant_is_the_leaf_string(self):
        assert TUCSON_CITY_ID == "tucson"

    def test_metro_contains_known_places(self):
        assert is_in_tucson_metro(32.2226, -110.9723) is True  # Downtown
        assert is_in_tucson_metro(32.2312, -110.9480) is True  # U of A
        assert is_in_tucson_metro(32.3280, -110.9380) is True  # Foothills
        assert is_in_tucson_metro(32.3907, -110.9757) is True  # Oro Valley
        assert is_in_tucson_metro(32.1959, -110.9680) is True  # South Tucson

    def test_metro_rejects_null_and_foreign(self):
        assert is_in_tucson_metro(None, None) is False
        assert is_in_tucson_metro(33.4484, -112.0740) is False  # Phoenix
        assert is_in_tucson_metro(31.3325, -110.9660) is False  # Nogales
        assert is_in_tucson_metro(35.1983, -106.5256) is False  # Albuquerque

    def test_live_fixture_coords_sit_inside_the_metro_bbox(self):
        for lat, lng in LIVE_FIXTURE_COORDS:
            assert is_in_tucson_metro(lat, lng), (lat, lng)

    def test_live_fixture_coords_land_in_their_divisions(self):
        # TJ (Broadway) -> MIDTOWN, REVIVE (S 6th Ave) -> DOWNTOWN_CORE.
        # The SWEET TOOTH row (34 W Columbia St) sits in the South-Tucson
        # area — south of every hand-authored division bbox (South Tucson
        # is an independent city, not a leaf division) but inside the
        # metro bbox; it must land in ZERO divisions.
        expected_hits = {
            "TRADER_JOES": ["MIDTOWN"],
            "REVIVE": ["DOWNTOWN_CORE"],
            "SWEET_TOOTH": [],
        }
        for (label, (lat, lng)) in zip(
            ("TRADER_JOES", "REVIVE", "SWEET_TOOTH"), LIVE_FIXTURE_COORDS
        ):
            hits = [
                name
                for name, bbox in TUCSON_DIVISION_BBOXES.items()
                if bbox["min_lat"] <= lat <= bbox["max_lat"]
                and bbox["min_lng"] <= lng <= bbox["max_lng"]
            ]
            assert hits == expected_hits[label], (label, lat, lng, hits)

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in TUCSON_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= TUCSON_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= TUCSON_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= TUCSON_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= TUCSON_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in TUCSON_SUBMARKETS.items():
            bbox = TUCSON_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in TUCSON_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(TUCSON_SUBMARKETS)

    def test_submarket_count_in_leaf_band(self):
        assert 6 <= len(TUCSON_SUBMARKETS) <= 10

    def test_required_real_neighborhoods_present(self):
        for name in (
            "Downtown Tucson",
            "Armory Park",
            "Barrio Viejo",
            "Fourth Avenue",
            "University of Arizona",
            "Midtown",
            "Catalina Foothills edge",
            "Oro Valley edge",
        ):
            assert name in TUCSON_SUBMARKETS, name

    def test_submarkets_carry_tucson_city_id_and_all_meta_fields(self):
        assert {m.city_id for m in TUCSON_SUBMARKETS.values()} == {"tucson"}
        for name, meta in TUCSON_SUBMARKETS.items():
            assert isinstance(meta, SubmarketMeta), name
            for field in _SUBMARKET_FIELDS:
                value = getattr(meta, field)
                assert value is not None, f"{name}.{field}"
                if field == "description":
                    assert len(value) > 20, name

    def test_division_centers_sit_inside_their_bbox(self):
        assert 4 <= len(TUCSON_DIVISION_BBOXES) <= 8
        assert set(TUCSON_DIVISION_BBOXES) == set(TUCSON_DIVISIONS)
        for name, meta in TUCSON_DIVISIONS.items():
            assert meta.city_id == "tucson"
            bbox = TUCSON_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_spatial_registration_references_module_constants(self):
        assert REGISTRATION.metro_bbox is TUCSON_METRO_BBOX
        assert REGISTRATION.submarkets is TUCSON_SUBMARKETS
        assert REGISTRATION.divisions is TUCSON_DIVISIONS
        assert REGISTRATION.contains is is_in_tucson_metro


# ---------------------------------------------------------------------------
# Feed spec (leaf-local get_dataset mirror)
# ---------------------------------------------------------------------------


class TestFeedRegistration:
    def test_exactly_one_feed_type_is_registered(self):
        assert set(TUCSON_FEED_SPECS) == {"sla"}

    def test_sla_spec_matches_live_layer(self):
        spec = get_tucson_dataset(FeedType.SLA)
        assert spec.platform == "arcgis"
        assert spec.endpoint == TUCSON_SLA_ENDPOINT
        assert spec.watermark_col == "DT_START"
        assert spec.id_keys == ["ACC_NUM", "LIC_TYPE", "OBJECTID"]
        assert spec.producer_key == "sla"
        assert spec.ingestion_mode == "snapshot"
        assert spec.where == TUCSON_SLA_WHERE == "DT_START <= CURRENT_TIMESTAMP"
        assert spec.order_by == "DT_START DESC"
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.needs_geocode is True
        assert spec.geocode_context == TUCSON_GEOCODE_CONTEXT == "Tucson, AZ"
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.topic  # settings.topic_sla resolves

    def test_sla_spec_encodes_slow_cadence_and_alarm_exempt(self):
        spec = get_tucson_dataset(FeedType.SLA)
        assert spec.expected_cadence_days == 30
        assert spec.alarm_exempt is True
        assert spec.alarm_exempt_reason == TUCSON_SLA_ALARM_EXEMPT_REASON
        assert "future-dated" in spec.alarm_exempt_reason
        assert "2 per 60d" in spec.alarm_exempt_reason

    def test_sla_spec_leaves_watermark_exclude_empty(self):
        # Sentinels are a ROLLING set of future-dated applications — no
        # static literal list can pin them, and this host is ANSI-date
        # (the bare-literal NOT IN form watermark_exclude_clause emits
        # 400s live). The where guard is the sentinel mechanism.
        spec = get_tucson_dataset(FeedType.SLA)
        assert spec.watermark_exclude == []
        assert watermark_exclude_clause("DT_START", spec.watermark_exclude) is None

    @pytest.mark.parametrize(
        "absent_feed", [FeedType.PERMITS, FeedType.COMPLAINTS_311, FeedType.DEEDS]
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'tucson'.*available"):
            get_tucson_dataset(absent_feed)


# ---------------------------------------------------------------------------
# Sentinel guard (US-111 future-watermark discipline)
# ---------------------------------------------------------------------------


class TestSentinelGuard:
    def test_live_sentinel_row_is_future_dated_after_flatten(self):
        assert SENTINEL_ROW["DT_START"] == "2026-09-12T00:00:00+00:00"
        parsed = _parse_datetime(SENTINEL_ROW["DT_START"])
        assert parsed is not None
        assert is_future_watermark(parsed, datetime.now(timezone.utc)) is True

    def test_newest_non_future_fixture_is_not_future_dated(self):
        assert TRADER_JOES_ROW["DT_START"] == "2026-05-29T00:00:00+00:00"
        parsed = _parse_datetime(TRADER_JOES_ROW["DT_START"])
        assert parsed is not None
        assert is_future_watermark(parsed, datetime.now(timezone.utc)) is False

    def test_where_guard_composes_with_the_us111_convention(self):
        spec = get_tucson_dataset(FeedType.SLA)
        where = build_where(
            base_where=spec.where,
            watermark_col=spec.watermark_col,
            high_watermark="2026-05-29T00:00:00+00:00",
            endpoint=spec.endpoint,
            incremental=True,
            snapshot=False,
        )
        assert where is not None
        assert f"({TUCSON_SLA_WHERE})" in where
        assert "DT_START >" in where


# ---------------------------------------------------------------------------
# Field map mechanics
# ---------------------------------------------------------------------------


class TestTucsonFieldMaps:
    def test_sla_map_reads_live_columns(self):
        row = TRADER_JOES_ROW
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "T3091773"
        assert first_mapped(row, SLA_FIELD_MAP, "dba") == "TRADER JOES #288"
        assert first_mapped(row, SLA_FIELD_MAP, "premises_name") == "TRADER JOES #288"
        assert first_mapped(row, SLA_FIELD_MAP, "license_type") == "BUS"
        assert first_mapped(row, SLA_FIELD_MAP, "status") == "Application"
        assert first_mapped(row, SLA_FIELD_MAP, "effective_date") == (
            "2026-05-29T00:00:00+00:00"
        )
        assert first_mapped(row, SLA_FIELD_MAP, "address_street") == "2150 E BROADWAY BL"
        assert first_mapped(row, SLA_FIELD_MAP, "zipcode") == "85719"

    def test_sla_license_type_falls_back_to_naics_desc(self):
        row = {"LIC_TYPE": "", "NAIC_DESC": "Beauty Salons"}
        assert first_mapped(row, SLA_FIELD_MAP, "license_type") == "Beauty Salons"

    def test_sla_address_is_fulladdress_not_a_parts_join(self):
        # first_mapped returns one value; the padded STREETNUM part alone
        # ("5010           ") is not geocodeable — FULLADDRESS is the
        # only sane address candidate on this layer.
        assert first_mapped(SENTINEL_ROW, SLA_FIELD_MAP, "address_street") == (
            "5010 W SWEETWATER DR"
        )

    def test_sla_map_declares_no_native_coordinates(self):
        # Store SR is WKID 2868 (Arizona East feet); coordinates come ONLY
        # from the outSR=4326 geometry lift, never from attribute columns.
        mapped = {c for cols in SLA_FIELD_MAP.values() for c in cols}
        assert "latitude" not in mapped
        assert "longitude" not in mapped
        assert "Shape" not in mapped
        assert not (set(mapped) & set(DROPPED_NONADDRESS_COLUMNS))

    def test_map_is_the_exported_field_map(self):
        assert FIELD_MAP["sla"] is SLA_FIELD_MAP
        assert set(FIELD_MAP) == {"sla"}

    def test_geocode_context_is_tucson_az(self):
        assert GEOCODE_CONTEXT == "Tucson, AZ"
        assert TUCSON_GEOCODE_CONTEXT == "Tucson, AZ"


# ---------------------------------------------------------------------------
# ArcGISClient flatten contract (real client code, no network)
# ---------------------------------------------------------------------------


class TestArcgisFlatten:
    def test_geometry_lifts_to_wgs84_lat_lng_keys(self):
        assert TRADER_JOES_ROW["latitude"] == pytest.approx(32.221281920528575)
        assert TRADER_JOES_ROW["longitude"] == pytest.approx(-110.93989797596089)

    def test_null_geometry_row_lifts_no_coordinates(self):
        assert "latitude" not in SENTINEL_ROW
        assert "longitude" not in SENTINEL_ROW

    def test_epoch_ms_dates_flatten_to_iso(self):
        assert REVIVE_ROW["DT_START"] == "2026-05-20T00:00:00+00:00"
        assert SWEET_TOOTH_ROW["DT_START"] == "2026-05-12T00:00:00+00:00"

    def test_source_char_padding_is_preserved_verbatim(self):
        assert SENTINEL_ROW["ACC_NUM"] == "T3092163            "
        assert SWEET_TOOTH_ROW["ACC_NUM"] == "T3092422            "
        assert SWEET_TOOTH_ROW["LIC_STATUS"] == "Application         "
        assert SWEET_TOOTH_ROW["ZIP_CODE"] == "85714     "


# ---------------------------------------------------------------------------
# Producer path with the Tucson field map injected (no spine registration)
# ---------------------------------------------------------------------------


@pytest.fixture
def sla():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        return SLALicensesProducer()


def _patch_resolve(monkeypatch, geocode_point=None):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: SLA_FIELD_MAP,
    )
    if geocode_point is not None:
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: geocode_point,
        )
    else:
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )


class TestTucsonSlaParsing:
    def test_trader_joes_row_parses_all_fields(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(TRADER_JOES_ROW, city_id="tucson")
        assert event is not None
        assert event.city_id == "tucson"
        assert event.license_id == "T3091773"
        assert event.dba == "TRADER JOES #288"
        assert event.premises_name == "TRADER JOES #288"
        assert event.license_type == "BUS"
        assert event.license_status == "Application"
        assert event.address == "2150 E BROADWAY BL"
        assert event.effective_date is not None
        assert event.effective_date.year == 2026
        assert event.effective_date.month == 5
        assert event.effective_date.day == 29

    def test_geometry_row_carries_wgs84_coords_h3_and_metro_containment(
        self, sla, monkeypatch
    ):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(TRADER_JOES_ROW, city_id="tucson")
        assert event is not None
        assert event.latitude == pytest.approx(32.221281920528575)
        assert event.longitude == pytest.approx(-110.93989797596089)
        expected = H3SpatialIndexer.get_multi_res_hierarchy(event.latitude, event.longitude)
        assert event.h3_res7 == expected["h3_res7"]
        assert event.h3_res8 == expected["h3_res8"]
        assert event.h3_res9 == expected["h3_res9"]
        assert is_in_tucson_metro(event.latitude, event.longitude) is True

    def test_second_fixture_parses_with_native_geometry(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(REVIVE_ROW, city_id="tucson")
        assert event is not None
        assert event.license_id == "T3092127"
        assert event.license_type == "BUS"
        assert event.address == "747 S 6TH AV STE 101"
        assert event.latitude == pytest.approx(32.21226392285235)
        assert event.longitude == pytest.approx(-110.96824347090345)
        assert event.h3_res7 is not None
        assert is_in_tucson_metro(event.latitude, event.longitude) is True

    def test_padded_row_license_id_is_stripped_status_keeps_source_form(
        self, sla, monkeypatch
    ):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(SWEET_TOOTH_ROW, city_id="tucson")
        assert event is not None
        assert event.license_id == "T3092422"
        assert event.license_status.startswith("Application")
        assert event.license_type == "BUS"
        assert event.latitude == pytest.approx(32.173446928872636)
        assert is_in_tucson_metro(event.latitude, event.longitude) is True

    def test_null_geometry_row_falls_to_geocoder_stub(self, sla, monkeypatch):
        # Sentinel row has no lifted coordinates; with the ADR-0004
        # declaration the parser resolves FULLADDRESS via the declared
        # geocoder. Result-level assertions only — no hook-call counts.
        _patch_resolve(monkeypatch, geocode_point=_GEOCODED)
        event = sla.parse_socrata_row(SENTINEL_ROW, city_id="tucson")
        assert event is not None
        assert event.license_id == "T3092163"
        assert event.dba == "NICHOLS BARBARA JANE"
        assert event.license_status.startswith("Active")
        assert event.effective_date is not None
        assert event.effective_date.year == 2026 and event.effective_date.month == 9
        assert event.latitude == pytest.approx(_GEOCODED[0])
        assert event.longitude == pytest.approx(_GEOCODED[1])
        assert event.h3_res7 is not None
        assert is_in_tucson_metro(event.latitude, event.longitude) is True

    def test_null_geometry_row_with_geocode_failure_keeps_null_coords(
        self, sla, monkeypatch
    ):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(SENTINEL_ROW, city_id="tucson")
        assert event is not None
        assert event.license_id == "T3092163"
        assert event.latitude is None and event.longitude is None
        assert event.h3_res7 is None and event.h3_res8 is None and event.h3_res9 is None

    def test_city_id_string_is_accepted_verbatim_without_enum(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(
            {**TRADER_JOES_ROW, "ACC_NUM": "T3099999"}, city_id="tucson"
        )
        assert event is not None
        assert event.city_id == "tucson"
        assert event.license_id == "T3099999"

    def test_row_without_any_id_is_dropped(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        row = {k: v for k, v in TRADER_JOES_ROW.items() if k != "ACC_NUM"}
        assert sla.parse_socrata_row(row, city_id="tucson") is None
