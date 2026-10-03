"""Unit tests for the Eugene, OR leaf (US-225): spatial module + field
maps + producer parse wiring.

Eugene is a ONE-FEED PARTIAL metro on the City of Eugene ArcGIS Server at
``services3.arcgis.com/F7NiRLGNbA2hh7gE``: SLA
(Food_Service_Establishments_Updated_VIEW_CBE, 752 rows, snapshot). Its
COMPLAINTS_311 (2020_2021CampingWorkOrders, newest 2021-03-12) and DEEDS
(CityLandDeeds, the City's own land deeds) feeds were retired on 2026-10-03.
Permits are NOT registered: the city's ebuild permit system is an
Accela-style web portal with no bulk API, and Lane County records are
web-portal-only.

Tests pass WITHOUT a spine registration (no CityId.EUGENE, no REGISTRY
assertions — "eugene" stays a plain string). Spine-stable per the leaf
contract: no division/borough-resolution assertions and no geocode-hook
call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from Food_Service's
FeatureServer/0 by ObjectId. Fixtures are RAW ArcGIS features (attributes +
geometry); the tests run the real ``ArcGISClient._flatten_feature`` lift —
geometry to latitude/longitude — before parsing, exactly as the live
producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.spatial.cities.eugene import (
    FIELD_MAP,
    GEOCODE_CONTEXT,
    SLA_FIELD_MAP,
)
from src.spatial.cities.eugene import (
    EUGENE_CITY_ID,
    EUGENE_DIVISION_BBOXES,
    EUGENE_DIVISIONS,
    EUGENE_FEED_SPECS,
    EUGENE_FOOD_SERVICE_SLA_ENDPOINT,
    EUGENE_GEOCODE_CONTEXT,
    EUGENE_METRO_BBOX,
    EUGENE_SUBMARKETS,
    REGISTRATION,
    get_eugene_dataset,
    is_in_eugene_metro,
    is_in_greater_eugene_metro,
)


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _flatten(feature, date_fields):
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, date_fields)


# =========================================================================
# SLA — Food_Service_Establishments_Updated_VIEW_CBE (FeatureServer/0)
# Snapshot (no date column); first rows by ObjectId, outSR=4326.
# Store SR 102100 (Web Mercator); geometry lifts to WGS84 via outSR=4326.
# =========================================================================
_SLA_FEATURE_1 = {
    "attributes": {
        "UID": 433,
        "MatchAddr": "27359 CLEAR LAKE RD, Eugene, 97402",
        "DisplayX": -123.26453,
        "DisplayY": 44.11366988,
        "Name": "Mi Casita Mexican Cuisine",
        "Licensee": "Magaly Duarte Servin",
        "Active": "Y",
        "ObjectId": 1,
        "GlobalID": "9797d1b5-93fe-4de3-8aa5-037d39dfee68",
    },
    "geometry": {"x": -123.26453, "y": 44.11366988},
}

_SLA_FEATURE_2 = {
    "attributes": {
        "UID": 1,
        "MatchAddr": "1810 WILLAMETTE ST, Eugene, 97401",
        "DisplayX": -123.093057,
        "DisplayY": 44.0398293,
        "Name": "1960 Cocina",
        "Licensee": "Elizabeth Peredia-Leanos",
        "Active": "Y",
        "ObjectId": 2,
        "GlobalID": "492ab2d2-e60d-4308-a3a5-87cd04fe8628",
    },
    "geometry": {"x": -123.093057, "y": 44.039829299999994},
}

_SLA_FEATURE_3 = {
    "attributes": {
        "UID": 109,
        "MatchAddr": "1996 ECHO HOLLOW RD, Eugene, 97402",
        "DisplayX": -123.1683751,
        "DisplayY": 44.08423722,
        "Name": "Carl's Jr # 8239",
        "Licensee": "JCK Restaurants, Inc",
        "Active": "Y",
        "ObjectId": 3,
        "GlobalID": "fa13e725-b355-45b8-b3ad-7f3f32256c2f",
    },
    "geometry": {"x": -123.1683751, "y": 44.08423722},
}


class TestEugeneSpatial:
    def test_city_id_constant_is_the_leaf_string(self):
        assert EUGENE_CITY_ID == "eugene"

    def test_metro_bbox_sanity(self):
        assert EUGENE_METRO_BBOX["min_lat"] < EUGENE_METRO_BBOX["max_lat"]
        assert EUGENE_METRO_BBOX["min_lng"] < EUGENE_METRO_BBOX["max_lng"]

    def test_is_in_eugene_metro_rejects_missing_coordinates(self):
        assert is_in_eugene_metro(None, None) is False
        assert is_in_eugene_metro(44.0521, None) is False
        assert is_in_eugene_metro(None, -123.0920) is False

    def test_is_in_eugene_metro_rejects_other_cities(self):
        assert is_in_eugene_metro(45.5152, -122.6784) is False   # Portland
        assert is_in_eugene_metro(44.0575, -121.3150) is False   # Bend
        assert is_in_eugene_metro(44.0510, -123.0920 * -1) is False

    def test_downtown_anchors_are_contained(self):
        assert is_in_eugene_metro(44.0510, -123.0920)  # Downtown
        assert is_in_eugene_metro(44.0600, -123.0980)  # Whiteaker
        assert is_in_eugene_metro(44.0320, -123.0980)  # Friendly
        assert is_in_eugene_metro(44.0100, -123.0900)  # South Eugene
        assert is_in_eugene_metro(44.0700, -123.0520)  # Cal Young
        assert is_in_eugene_metro(44.1100, -123.0900)  # Santa Clara

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_SLA_FEATURE_1, _SLA_FEATURE_2, _SLA_FEATURE_3):
            geom = feature["geometry"]
            assert is_in_eugene_metro(geom["y"], geom["x"])

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in EUGENE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= EUGENE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= EUGENE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= EUGENE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= EUGENE_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in EUGENE_SUBMARKETS.items():
            bbox = EUGENE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in EUGENE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(EUGENE_SUBMARKETS)

    def test_submarkets_carry_the_eugene_city_id(self):
        assert {m.city_id for m in EUGENE_SUBMARKETS.values()} == {"eugene"}

    def test_registration_shape(self):
        assert REGISTRATION.metro_bbox is EUGENE_METRO_BBOX
        assert REGISTRATION.submarkets is EUGENE_SUBMARKETS
        assert REGISTRATION.division_bboxes is EUGENE_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_eugene_metro
        assert len(REGISTRATION.divisions) == 8
        assert len(EUGENE_SUBMARKETS) == 15

    def test_required_real_neighborhoods_present(self):
        assert {"Downtown", "Whiteaker", "Friendly", "South Eugene",
                "Cal Young", "Santa Clara", "Bethel", "Churchill",
                "Jefferson Westside", "Amazon"} <= set(EUGENE_SUBMARKETS)

    def test_greater_metro_alias(self):
        assert is_in_greater_eugene_metro is is_in_eugene_metro


class TestEugeneFieldMaps:
    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["UID", "GlobalID"]
        assert SLA_FIELD_MAP["dba"] == ["Name"]
        assert SLA_FIELD_MAP["premises_name"] == ["Name"]
        assert SLA_FIELD_MAP["address_street"] == ["MatchAddr"]
        assert SLA_FIELD_MAP["status"] == ["Active"]

    def test_field_map_module_shape(self):
        assert set(FIELD_MAP) == {"sla"}
        for feed in ("sla",):
            assert isinstance(FIELD_MAP[feed], dict)
            for canonical, candidates in FIELD_MAP[feed].items():
                assert isinstance(canonical, str)
                assert isinstance(candidates, list)

    def test_geocode_context(self):
        assert GEOCODE_CONTEXT == "Eugene, OR"
        assert EUGENE_GEOCODE_CONTEXT == "Eugene, OR"

    def test_no_coordinate_candidates_geometry_lift_is_sole_source(self):
        """The SLA feed relies on the outSR=4326 geometry lift. No
        latitude/longitude attribute candidates are declared — the Web
        Mercator attributes stay server-side."""
        assert "latitude" not in SLA_FIELD_MAP
        assert "longitude" not in SLA_FIELD_MAP

    def test_sla_first_mapped_resolves_live_rows(self):
        for feature in (_SLA_FEATURE_1, _SLA_FEATURE_2, _SLA_FEATURE_3):
            attrs = feature["attributes"]
            assert first_mapped(attrs, SLA_FIELD_MAP, "license_id") is not None
            assert first_mapped(attrs, SLA_FIELD_MAP, "dba") is not None
            assert first_mapped(attrs, SLA_FIELD_MAP, "address_street") is not None


class TestEugeneSLAParsing:
    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_SLA_FEATURE_1, set())
        assert record["latitude"] == pytest.approx(44.11366988)
        assert record["longitude"] == pytest.approx(-123.26453)

    def test_newest_fixture_parses_through_producer(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(
            _flatten(_SLA_FEATURE_1, set()),
            city_id="eugene",
        )
        assert event is not None
        assert event.city_id == "eugene"
        assert event.license_id == "433"
        assert event.dba == "Mi Casita Mexican Cuisine"
        assert event.premises_name == "Mi Casita Mexican Cuisine"
        assert event.address == "27359 CLEAR LAKE RD, Eugene, 97402"
        assert event.latitude == pytest.approx(44.11366988)
        assert event.longitude == pytest.approx(-123.26453)

    def test_second_fixture_h3_and_containment(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(
            _flatten(_SLA_FEATURE_2, set()),
            city_id="eugene",
        )
        assert event is not None
        assert event.license_id == "1"
        assert event.dba == "1960 Cocina"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert is_in_eugene_metro(event.latitude, event.longitude)

    def test_third_fixture_downtown_containment(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(
            _flatten(_SLA_FEATURE_3, set()),
            city_id="eugene",
        )
        assert event is not None
        assert event.dba == "Carl's Jr # 8239"
        assert event.address == "1996 ECHO HOLLOW RD, Eugene, 97402"
        assert is_in_eugene_metro(event.latitude, event.longitude)

    def test_license_id_falls_back_to_globalid(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten(_SLA_FEATURE_1, set())
        record.pop("UID")
        event = sla.parse_socrata_row(record, city_id="eugene")
        assert event is not None
        assert event.license_id == "9797d1b5-93fe-4de3-8aa5-037d39dfee68"

    def test_row_without_any_id_is_dropped(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten(_SLA_FEATURE_1, set())
        record.pop("UID")
        record.pop("GlobalID")
        assert sla.parse_socrata_row(record, city_id="eugene") is None


class TestEugeneFeedSpec:
    def test_sla_spec_matches_live_layer(self):
        spec = get_eugene_dataset("sla")
        assert spec.platform == "arcgis"
        assert spec.endpoint == EUGENE_FOOD_SERVICE_SLA_ENDPOINT
        assert spec.watermark_col == ""
        assert spec.id_keys == ["UID", "ObjectId", "GlobalID"]
        assert spec.oid_field == "ObjectId"
        assert spec.max_record_count == 2000
        assert spec.ingestion_mode == "snapshot"
        assert spec.needs_geocode is False
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.topic == "raw.municipal.sla"
        assert spec.alarm_exempt is True

    def test_registered_feed_set(self):
        assert set(EUGENE_FEED_SPECS) == {"sla"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_eugene_dataset("permits")
        assert "eugene" in str(exc.value)
        assert "sla" in str(exc.value)

    def test_retired_feeds_are_gone(self):
        """The camping work orders stopped in 2021 and CityLandDeeds holds the
        City's own land deeds, not sales: both were retired on 2026-10-03."""
        for feed in ("311", "deeds"):
            with pytest.raises(KeyError):
                get_eugene_dataset(feed)

    def test_endpoints_all_on_services3_arcgis(self):
        assert "services3.arcgis.com" in EUGENE_FOOD_SERVICE_SLA_ENDPOINT
        assert "FeatureServer/0" in EUGENE_FOOD_SERVICE_SLA_ENDPOINT
