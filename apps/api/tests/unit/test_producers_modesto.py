"""Unit tests for the Modesto, CA leaf (US-231): spatial module + field
maps + producer parse wiring.

Modesto is a ONE-FEED PARTIAL metro: Business Licenses
(``ExternalServices/Map_Layer_Service_External/FeatureServer/7`` on the
city ArcGIS Enterprise 12.1 server ``gis.modestogov.com/hosting``,
verified live 2026-08-28, 4,574 rows, 214/4574 null geometry ≈ 4.7%).
311 (GoModesto on the PublicStuff vendor platform, no anonymous API),
permits (TrakIT folder is 403; only aggregate showcase layers exist), and
deeds (Stanislaus recorder is an interactive search portal; the county
parcel mirror is a cadastre without sale/deed fields) stay Tier 3 — only
``sla`` is registered.

Tests pass WITHOUT a spine registration (no CityId.MODESTO, no REGISTRY
assertions — "modesto" stays a plain string). Spine-stable per the
west-region leaf contract: no division/borough-resolution assertions and
no geocode-hook call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from FeatureServer/7 (newest
window via ``orderByFields=OBJECTID`` at ``outSR=4326``; the layer has NO
esriFieldTypeDate column, so OBJECTID ordering is the only stable sort).
Fixtures are RAW ArcGIS features (attributes + geometry); the tests run
the real ``ArcGISClient._flatten_feature`` lift — geometry to
latitude/longitude, date_fields empty for this layer — before parsing,
exactly as the live producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_modesto import (
    DROPPED_NONADDRESS_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    SLA_FIELD_MAP,
)
from src.spatial.cities.modesto import (
    MODESTO_CITY_ID,
    MODESTO_DIVISION_BBOXES,
    MODESTO_DIVISIONS,
    MODESTO_FEED_SPECS,
    MODESTO_GEOCODE_CONTEXT,
    MODESTO_METRO_BBOX,
    MODESTO_SLA_ENDPOINT,
    MODESTO_SUBMARKETS,
    REGISTRATION,
    get_modesto_dataset,
    is_in_greater_modesto_metro,
    is_in_modesto_metro,
)


def _patch_resolve(monkeypatch):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed],
    )


def _flatten(feature):
    """Run the real ArcGIS flatten lift over a raw captured feature.

    ``date_fields`` is what the client discovers from the live layer's
    metadata: the Business Licenses layer carries NO esriFieldTypeDate
    column, so the set is empty and nothing is epoch-normalized.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, set())


# Byte-verbatim rows from the 2026-08-28 live pull (orderByFields=OBJECTID,
# outSR=4326). Zero-padded ACCOUNTNUM strings, split address parts, no date
# fields, native WGS84 geometry lifted client-side.
_FEATURE_2 = {
    "attributes": {
        "OBJECTID": 2,
        "ACCOUNTNUM": "0000563",
        "BUSNAME": "NORTHERN STEEL INC",
        "LOCSTNUM": "1636",
        "LOCSTADDR1": "CULPEPPER AVE",
        "LOCSUITE": "",
        "LOCCITY": "MODESTO",
        "LOCST": "CA",
        "LOCZIP1": "95351",
        "LOCZIP2": "1139",
        "LOCPHNUM": "(209) 527-7934",
        "GlobalID": "{D59C9A96-956E-4560-8F87-F9E399EEDA87}"
    },
    "geometry": {
        "x": -121.02748649999812,
        "y": 37.6594380000033
    }
}

_FEATURE_3 = {
    "attributes": {
        "OBJECTID": 3,
        "ACCOUNTNUM": "0000612",
        "BUSNAME": "HUCKLEBERRY'S",
        "LOCSTNUM": "2213",
        "LOCSTADDR1": "YOSEMITE BLVD",
        "LOCSUITE": "",
        "LOCCITY": "MODESTO",
        "LOCST": "CA",
        "LOCZIP1": "95354",
        "LOCZIP2": "3003",
        "LOCPHNUM": "(209) 527-0872",
        "GlobalID": "{B3AEF6DF-A1CF-416C-8613-99EA77783721}"
    },
    "geometry": {
        "x": -120.95620200034008,
        "y": 37.63833299965516
    }
}

_FEATURE_4 = {
    "attributes": {
        "OBJECTID": 4,
        "ACCOUNTNUM": "0000646",
        "BUSNAME": "BELL & GAINES INC",
        "LOCSTNUM": "1117",
        "LOCSTADDR1": "7TH ST",
        "LOCSUITE": "",
        "LOCCITY": "MODESTO",
        "LOCST": "CA",
        "LOCZIP1": "95354",
        "LOCZIP2": "2208",
        "LOCPHNUM": "(209) 521-9400",
        "GlobalID": "{6468E629-1BA8-4FF1-8FC7-5EF5EA0C1687}"
    },
    "geometry": {
        "x": -121.00504949969475,
        "y": 37.63972799965493
    }
}


class TestModestoSpatial:
    def test_metro_bbox_sanity(self):
        assert MODESTO_METRO_BBOX["min_lat"] < MODESTO_METRO_BBOX["max_lat"]
        assert MODESTO_METRO_BBOX["min_lng"] < MODESTO_METRO_BBOX["max_lng"]

    def test_is_in_modesto_metro_rejects_missing_coordinates(self):
        assert is_in_modesto_metro(None, None) is False
        assert is_in_modesto_metro(37.6391, None) is False
        assert is_in_modesto_metro(None, -120.9969) is False

    def test_is_in_modesto_metro_rejects_other_cities(self):
        assert is_in_modesto_metro(37.9577, -121.2908) is False   # Stockton
        assert is_in_modesto_metro(38.5816, -121.4944) is False   # Sacramento
        assert is_in_modesto_metro(36.7378, -119.7871) is False   # Fresno
        assert is_in_modesto_metro(37.4947, -120.8466) is False   # Turlock
        assert is_in_modesto_metro(37.5947, -120.9566) is False   # Ceres (south, outside)
        assert is_in_modesto_metro(37.7058, -121.0795) is False   # Salida (northwest, outside)

    def test_downtown_anchors_are_contained(self):
        assert is_in_modesto_metro(37.6397, -120.9927)  # Gallo Center for the Arts
        assert is_in_modesto_metro(37.6452, -120.9944)  # McHenry Mansion
        assert is_in_modesto_metro(37.6495, -120.9777)  # Modesto Junior College east campus
        assert is_in_modesto_metro(37.6640, -120.9760)  # Village One
        assert is_in_modesto_metro(37.6785, -120.9954)  # Vintage Faire Mall

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_FEATURE_2, _FEATURE_3, _FEATURE_4):
            assert is_in_modesto_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in MODESTO_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= MODESTO_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= MODESTO_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= MODESTO_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= MODESTO_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in MODESTO_SUBMARKETS.items():
            bbox = MODESTO_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in MODESTO_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(MODESTO_SUBMARKETS)

    def test_submarkets_carry_the_modesto_city_id(self):
        assert {m.city_id for m in MODESTO_SUBMARKETS.values()} == {"modesto"}

    def test_city_id_and_registration_shape(self):
        assert MODESTO_CITY_ID == "modesto"
        assert REGISTRATION.metro_bbox is MODESTO_METRO_BBOX
        assert REGISTRATION.submarkets is MODESTO_SUBMARKETS
        assert REGISTRATION.division_bboxes is MODESTO_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_modesto_metro
        assert len(REGISTRATION.divisions) == 8
        assert len(MODESTO_SUBMARKETS) == 13

    def test_required_real_neighborhoods_present(self):
        assert set(MODESTO_SUBMARKETS) == {
            "Downtown Modesto",
            "Virginia Corridor South",
            "Graceada Park Historic District",
            "Modesto Junior College East",
            "College & El Vista",
            "La Loma",
            "Village One",
            "Sherwood Forest & Sylvan",
            "Kiernan Business Corridor",
            "Pelandale Corridor",
            "Airport Neighborhood",
            "West Modesto & Beard Industrial Edge",
            "Rosemount & Scenic",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_modesto_metro is is_in_modesto_metro


class TestModestoFieldMaps:
    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["ACCOUNTNUM"]
        assert SLA_FIELD_MAP["dba"] == ["BUSNAME"]
        assert SLA_FIELD_MAP["premises_name"] == ["BUSNAME"]
        assert SLA_FIELD_MAP["address_street"] == ["LOCSTADDR1"]
        assert SLA_FIELD_MAP["zipcode"] == ["LOCZIP1"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"sla": SLA_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Modesto, CA"
        assert MODESTO_GEOCODE_CONTEXT == "Modesto, CA"

    def test_state_plane_store_sr_is_never_a_coordinate_candidate(self):
        """The layer's store SR is WKID 102643 (NAD83 California Zone 3
        state plane ftUS) but the attributes carry no X/Y pair at all, so
        coordinates come only from the outSR=4326 geometry lift (Tucson
        precedent) — and no state_plane_* spec keys are declared."""
        assert "latitude" not in SLA_FIELD_MAP
        assert "longitude" not in SLA_FIELD_MAP
        for key in ("state_plane_crs", "state_plane_units",
                    "state_plane_x_col", "state_plane_y_col"):
            assert key not in MODESTO_FEED_SPECS["sla"]["extra"]

    def test_no_license_type_candidate_so_the_parser_default_is_pinned(self):
        """The live layer has NO license-class/status/NAICS column, so
        license_type is deliberately NOT a map candidate: every Modesto
        event carries the shared parser's legacy default
        ("On-Premises Liquor") — the registration caveat the spine hold
        must carry. See TestModestoSLAParsing."""
        assert "license_type" not in SLA_FIELD_MAP
        assert "status" not in SLA_FIELD_MAP
        assert "effective_date" not in SLA_FIELD_MAP

    def test_no_borough_candidate_so_source_neighborhood_passes_none(self):
        """No neighborhood/district column exists on the layer (Omaha
        discipline): no borough candidate is declared, so
        source_neighborhood passes through as None on parsed events."""
        assert "borough" not in SLA_FIELD_MAP
        assert "neighborhood" not in SLA_FIELD_MAP

    def test_no_latitude_longitude_or_date_columns_exist_live(self):
        """Byte-verbatim field list: the live layer carries exactly twelve
        columns, none of them a date, a coordinate pair, or a license
        class — the snapshot + parser-default contract is the source's
        shape, not a mapping choice."""
        live_columns = set(_FEATURE_2["attributes"])
        assert live_columns == {
            "OBJECTID", "ACCOUNTNUM", "BUSNAME", "LOCSTNUM", "LOCSTADDR1",
            "LOCSUITE", "LOCCITY", "LOCST", "LOCZIP1", "LOCZIP2",
            "LOCPHNUM", "GlobalID",
        }

    def test_phone_and_address_parts_never_become_candidates(self):
        mapped = {c for values in SLA_FIELD_MAP.values() for c in values}
        assert mapped
        for col in DROPPED_NONADDRESS_COLUMNS:
            assert col not in mapped
        # The phone block and the un-joinable address parts are exactly
        # what is dropped.
        assert {"LOCPHNUM", "LOCSTNUM", "LOCSUITE"} <= set(DROPPED_NONADDRESS_COLUMNS)

    def test_accountnum_is_a_zero_padded_string(self):
        assert first_mapped(_FEATURE_2["attributes"], SLA_FIELD_MAP, "license_id") == "0000563"
        assert isinstance(
            first_mapped(_FEATURE_4["attributes"], SLA_FIELD_MAP, "license_id"), str
        )


class TestModestoSLAParsing:
    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_FEATURE_2)
        assert record["latitude"] == pytest.approx(37.6594380000033)
        assert record["longitude"] == pytest.approx(-121.02748649999812)
        # Attributes ride along untouched — no date normalization exists
        # on this layer.
        assert record["ACCOUNTNUM"] == "0000563"

    def test_steel_fixture_parses_through_the_producer(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        event = sla.parse_socrata_row(_flatten(_FEATURE_2), city_id="modesto")
        assert event is not None
        assert event.city_id == "modesto"
        assert event.license_id == "0000563"
        assert event.dba == "NORTHERN STEEL INC"
        assert event.premises_name == "NORTHERN STEEL INC"
        assert event.address == "CULPEPPER AVE"
        assert event.latitude == pytest.approx(37.6594380000033)
        assert event.longitude == pytest.approx(-121.02748649999812)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3

    def test_huckleberrys_fixture_indexes_h3_and_sits_in_metro(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        event = sla.parse_socrata_row(_flatten(_FEATURE_3), city_id="modesto")
        assert event is not None
        assert event.license_id == "0000612"
        assert is_in_modesto_metro(event.latitude, event.longitude)

    def test_bell_gaines_fixture_address_and_containment(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        event = sla.parse_socrata_row(_flatten(_FEATURE_4), city_id="modesto")
        assert event is not None
        assert event.license_id == "0000646"
        assert event.address == "7TH ST"
        assert is_in_modesto_metro(event.latitude, event.longitude)

    def test_all_three_fixtures_parse_with_distinct_res9_cells(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        events = [
            sla.parse_socrata_row(_flatten(f), city_id="modesto")
            for f in (_FEATURE_2, _FEATURE_3, _FEATURE_4)
        ]
        assert all(e is not None for e in events)
        assert len({e.h3_res9 for e in events}) == 3

    def test_license_type_lands_on_the_parser_default(self, sla, monkeypatch):
        """The layer has no license-class column, so the shared parser's
        legacy default labels every Modesto event. Pinned honestly at the
        leaf (Greenville OT precedent): the spine hold must carry this
        caveat before any license-type-facing surface consumes the feed."""
        _patch_resolve(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        event = sla.parse_socrata_row(_flatten(_FEATURE_2), city_id="modesto")
        assert event is not None
        assert event.license_type == "On-Premises Liquor"

    def test_status_defaults_active_and_dates_stay_null(self, sla, monkeypatch):
        """No status/date columns exist: license_status rides the parser's
        ACTIVE default and both lifecycle dates stay null — the snapshot
        id-dedup diff is the open/close signal (KC SLA precedent)."""
        _patch_resolve(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        event = sla.parse_socrata_row(_flatten(_FEATURE_3), city_id="modesto")
        assert event is not None
        assert event.license_status == "ACTIVE"
        assert event.effective_date is None
        assert event.expiration_date is None

    def test_row_without_an_id_is_dropped(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        record = _flatten(_FEATURE_2)
        record.pop("ACCOUNTNUM")
        assert sla.parse_socrata_row(record, city_id="modesto") is None

    def test_null_geometry_row_emits_a_null_coord_event(self, sla, monkeypatch):
        """214/4574 live rows carry no geometry. needs_geocode stays False
        (the mapped address is a street string without a house number,
        which fails the ADR-0004 confidence gate — MC311 precedent), so
        the row keeps emitting a null-coordinate event (DC non-spatial
        precedent). Call-args/counts are spine-volatile and not
        asserted — only the event outcome."""
        _patch_resolve(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        record = _flatten(_FEATURE_2)
        record.pop("latitude")
        record.pop("longitude")
        event = sla.parse_socrata_row(record, city_id="modesto")
        assert event is not None
        assert event.city_id == "modesto"
        assert event.license_id == "0000563"
        assert event.latitude is None
        assert event.longitude is None
        assert event.h3_res7 is None

    def test_state_plane_feet_never_emit_as_degrees(self, sla, monkeypatch):
        """The store SR is state-plane feet (WKID 102643). If projected
        feet ever leaked into latitude/longitude (a bad future map edit),
        the SLA event model's ±90/±180 bounds reject the row and the
        producer drops it — fake degrees can never reach the wire."""
        _patch_resolve(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        record = _flatten(_FEATURE_2)
        record["latitude"] = 3096551.0     # state-plane feet magnitude
        record["longitude"] = -7195703.0
        assert sla.parse_socrata_row(record, city_id="modesto") is None


class TestModestoFeedSpec:
    def test_sla_spec_matches_live_layer(self):
        spec = get_modesto_dataset("sla")
        assert spec.platform == "arcgis"
        assert spec.endpoint == MODESTO_SLA_ENDPOINT
        assert spec.watermark_col == ""
        assert spec.id_keys == ["ACCOUNTNUM", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 90
        assert spec.interval_seconds == 1800.0
        assert spec.ingestion_mode == "snapshot"
        assert spec.needs_geocode is False
        assert spec.alarm_exempt is True
        assert spec.alarm_exempt_reason is not None
        assert "no date fields" in spec.alarm_exempt_reason
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.topic == "raw.municipal.sla"

    def test_registered_feed_set_is_sla_only(self):
        assert set(MODESTO_FEED_SPECS) == {"sla"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_modesto_dataset("permits")
        assert "modesto" in str(exc.value)
        assert "sla" in str(exc.value)

    def test_endpoint_is_the_probed_featureserver(self):
        assert "gis.modestogov.com" in MODESTO_SLA_ENDPOINT
        assert (
            "ExternalServices/Map_Layer_Service_External/FeatureServer/7"
            in MODESTO_SLA_ENDPOINT
        )
