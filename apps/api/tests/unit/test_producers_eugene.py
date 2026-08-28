"""Unit tests for the Eugene, OR leaf (US-225): spatial module + field
maps + producer parse wiring.

Eugene is a THREE-FEED PARTIAL metro on the City of Eugene ArcGIS Server at
``services3.arcgis.com/F7NiRLGNbA2hh7gE``: COMPLAINTS_311
(2020_2021CampingWorkOrders, 10k rows), SLA
(Food_Service_Establishments_Updated_VIEW_CBE, 752 rows, snapshot), and
DEEDS (CityLandDeeds, 2.9k rows). Permits are NOT registered: the city's
ebuild permit system is an Accela-style web portal with no bulk API, and
Lane County records are web-portal-only.

Tests pass WITHOUT a spine registration (no CityId.EUGENE, no REGISTRY
assertions — "eugene" stays a plain string). Spine-stable per the leaf
contract: no division/borough-resolution assertions and no geocode-hook
call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from each FeatureServer/0
(CampingWorkOrders via ``orderByFields=CreatedOn DESC``, CityLandDeeds via
``orderByFields=DATE_ DESC``, Food_Service by ObjectId). Fixtures are RAW
ArcGIS features (attributes + geometry); the tests run the real
``ArcGISClient._flatten_feature`` lift — geometry to latitude/longitude,
epoch-ms to ISO — before parsing, exactly as the live producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_eugene import (
    COMPLAINTS_311_FIELD_MAP,
    DEEDS_FIELD_MAP,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    SLA_FIELD_MAP,
)
from src.spatial.cities.eugene import (
    EUGENE_CAMPING_311_ENDPOINT,
    EUGENE_CITY_ID,
    EUGENE_CITYLAND_DEEDS_ENDPOINT,
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
# COMPLAINTS_311 — 2020_2021CampingWorkOrders (FeatureServer/0)
# Newest 3 rows by CreatedOn DESC, outSR=4326.
# Watermark: CreatedOn = 1615507200000 = 2021-03-12T00:00:00+00:00
# =========================================================================
_311_FEATURE_1 = {
    "attributes": {
        "FID": 1,
        "CreatedOn": 1615507200000,
        "Title": "Vehicle Stored on Street",
        "WorkDescri": "<p>Vehicle Make: Other Vehicle Model: Old RV Vehicle Color: White Vehicle License: HC55664 Vehicle State: OR Reported Violations: Vehicle Stored on Street: Request generated from web via IP Address: 207.173.17.214.</p>\n",
        "ServiceCod": "PDD10",
        "StatusText": "Assigned",
        "DateTime": 1615507200000,
        "GlobalID": "dd660009-1101-4ca5-b6fb-418a1b701a59",
    },
    "geometry": {"x": -123.07430953726018, "y": 44.10267726454463},
}

_311_FEATURE_2 = {
    "attributes": {
        "FID": 3284,
        "CreatedOn": 1615507200000,
        "Title": "Park Found Camp",
        "WorkDescri": "Blue tent",
        "ServiceCod": "PFI10",
        "StatusText": "Edited",
        "DateTime": 1615507200000,
        "GlobalID": "5c50b204-96d0-4ff7-8e39-65cea22c9163",
    },
    "geometry": {"x": -123.0852410475859, "y": 44.058248796378564},
}

_311_FEATURE_3 = {
    "attributes": {
        "FID": 3299,
        "CreatedOn": 1615507200000,
        "Title": "Inspection Required",
        "WorkDescri": "<p>Vehicle Make: Other Vehicle Model: Vehicle Color: White Vehicle License: H975827 Vehicle State: OR Reported Violations: Vehicle Stored on Street: Request generated from web via IP Address: 174.253.192.237.</p>\n",
        "ServiceCod": "PDD10",
        "StatusText": "Edited",
        "DateTime": 1615507200000,
        "GlobalID": "b4970a73-ca3e-426f-812d-cb9a6a03a950",
    },
    "geometry": {"x": -123.15683851322103, "y": 44.07394839918304},
}

_CREATED_ON_ISO = "2021-03-12T00:00:00+00:00"

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

# =========================================================================
# DEEDS — CityLandDeeds (FeatureServer/0)
# Newest 3 rows by DATE_ DESC, outSR=4326.
# Watermark: DATE_ = 1767571200000 = 2026-01-04T00:00:00+00:00
# =========================================================================
_DEED_FEATURE_1 = {
    "attributes": {
        "CITYDEED": "P02961",
        "GIS_ID": 25663,
        "ACQDIS": "A",
        "WIDTH": None,
        "MISC": None,
        "DATE_": 1767571200000,
        "PROP": None,
        "OBJECTID_1": 2871,
        "Shape__Area": 228589.87377929688,
        "Shape__Length": 1903.3581270658974,
    },
    "geometry": {
        "rings": [
            [
                [-123.150041213012, 43.9956994141967],
                [-123.149395995612, 43.9956760791285],
                [-123.14884557886, 43.9954834070963],
                [-123.148484717436, 43.9952415796396],
                [-123.148378425599, 43.9951703409076],
                [-123.148351238329, 43.9940545554873],
                [-123.148488978745, 43.9940633497198],
                [-123.1500036803, 43.9941600667564],
                [-123.150041213012, 43.9956994141967],
            ]
        ]
    },
}

_DEED_FEATURE_2 = {
    "attributes": {
        "CITYDEED": "P02961",
        "GIS_ID": 25664,
        "ACQDIS": "A",
        "WIDTH": None,
        "MISC": None,
        "DATE_": 1767571200000,
        "PROP": None,
        "OBJECTID_1": 2872,
        "Shape__Area": 306169.4885253906,
        "Shape__Length": 2382.0750495865445,
    },
    "geometry": {
        "rings": [
            [
                [-123.150041213012, 43.9956994141967],
                [-123.1500036803, 43.9941600667564],
                [-123.150670243746, 43.9942026155116],
                [-123.152934102781, 43.9943471096271],
                [-123.152934424573, 43.9945768786517],
                [-123.152916538341, 43.9945980781872],
                [-123.152405201698, 43.9952041757801],
                [-123.151878863205, 43.9955000758791],
                [-123.150833045088, 43.995370910233],
                [-123.150041213012, 43.9956994141967],
            ]
        ]
    },
}

_DEED_FEATURE_3 = {
    "attributes": {
        "CITYDEED": "P02961",
        "GIS_ID": 25665,
        "ACQDIS": "A",
        "WIDTH": None,
        "MISC": None,
        "DATE_": 1767571200000,
        "PROP": None,
        "OBJECTID_1": 2873,
        "Shape__Area": 214396.79272460938,
        "Shape__Length": 1907.0325062007037,
    },
    "geometry": {
        "rings": [
            [
                [-123.146349631331, 43.9939267216838],
                [-123.148351238329, 43.9940545554873],
                [-123.148378425599, 43.9951703409076],
                [-123.148038166929, 43.9949806319779],
                [-123.147416046884, 43.9951531938391],
                [-123.146863149302, 43.9951975918028],
                [-123.146590886658, 43.9951241379691],
                [-123.146374944272, 43.9949670753889],
                [-123.146349631331, 43.9939267216838],
            ]
        ]
    },
}

_DATE_ISO = "2026-01-05T00:00:00+00:00"


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
        for feature in (
            _311_FEATURE_1, _311_FEATURE_2, _311_FEATURE_3,
            _SLA_FEATURE_1, _SLA_FEATURE_2, _SLA_FEATURE_3,
            _DEED_FEATURE_1, _DEED_FEATURE_2, _DEED_FEATURE_3,
        ):
            geom = feature["geometry"]
            if "rings" in geom:
                ys = [pt[1] for part in geom["rings"] for pt in part]
                xs = [pt[0] for part in geom["rings"] for pt in part]
                assert is_in_eugene_metro(
                    sum(ys) / len(ys), sum(xs) / len(xs)
                )
            else:
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
    def test_311_map_reads_live_columns(self):
        assert COMPLAINTS_311_FIELD_MAP["incident_id"] == ["FID", "GlobalID"]
        assert COMPLAINTS_311_FIELD_MAP["complaint_type"] == ["Title"]
        assert COMPLAINTS_311_FIELD_MAP["created_date"] == ["CreatedOn"]
        assert COMPLAINTS_311_FIELD_MAP["status"] == ["StatusText"]

    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["UID", "GlobalID"]
        assert SLA_FIELD_MAP["dba"] == ["Name"]
        assert SLA_FIELD_MAP["premises_name"] == ["Name"]
        assert SLA_FIELD_MAP["address_street"] == ["MatchAddr"]
        assert SLA_FIELD_MAP["status"] == ["Active"]

    def test_deeds_map_reads_live_columns(self):
        assert DEEDS_FIELD_MAP["doc_id"] == ["CITYDEED", "OBJECTID_1"]
        assert DEEDS_FIELD_MAP["recorded_date"] == ["DATE_"]
        assert DEEDS_FIELD_MAP["doc_type"] == ["ACQDIS"]

    def test_field_map_module_shape(self):
        assert set(FIELD_MAP) == {"311", "sla", "deeds"}
        for feed in ("311", "sla", "deeds"):
            assert isinstance(FIELD_MAP[feed], dict)
            for canonical, candidates in FIELD_MAP[feed].items():
                assert isinstance(canonical, str)
                assert isinstance(candidates, list)

    def test_geocode_context(self):
        assert GEOCODE_CONTEXT == "Eugene, OR"
        assert EUGENE_GEOCODE_CONTEXT == "Eugene, OR"

    def test_no_coordinate_candidates_geometry_lift_is_sole_source(self):
        """All three feeds rely on the outSR=4326 geometry lift. No
        latitude/longitude attribute candidates are declared — the State
        Plane / Web Mercator attributes stay server-side."""
        for fm in (COMPLAINTS_311_FIELD_MAP, SLA_FIELD_MAP, DEEDS_FIELD_MAP):
            assert "latitude" not in fm
            assert "longitude" not in fm

    def test_311_first_mapped_resolves_live_rows(self):
        for feature in (_311_FEATURE_1, _311_FEATURE_2, _311_FEATURE_3):
            attrs = feature["attributes"]
            assert first_mapped(attrs, COMPLAINTS_311_FIELD_MAP, "incident_id") is not None
            assert first_mapped(attrs, COMPLAINTS_311_FIELD_MAP, "complaint_type") is not None
            assert first_mapped(attrs, COMPLAINTS_311_FIELD_MAP, "created_date") is not None
            assert first_mapped(attrs, COMPLAINTS_311_FIELD_MAP, "status") is not None

    def test_sla_first_mapped_resolves_live_rows(self):
        for feature in (_SLA_FEATURE_1, _SLA_FEATURE_2, _SLA_FEATURE_3):
            attrs = feature["attributes"]
            assert first_mapped(attrs, SLA_FIELD_MAP, "license_id") is not None
            assert first_mapped(attrs, SLA_FIELD_MAP, "dba") is not None
            assert first_mapped(attrs, SLA_FIELD_MAP, "address_street") is not None

    def test_deeds_first_mapped_resolves_live_rows(self):
        for feature in (_DEED_FEATURE_1, _DEED_FEATURE_2, _DEED_FEATURE_3):
            attrs = feature["attributes"]
            assert first_mapped(attrs, DEEDS_FIELD_MAP, "doc_id") is not None
            assert first_mapped(attrs, DEEDS_FIELD_MAP, "recorded_date") is not None


class TestEugene311Parsing:
    @pytest.fixture
    def complaints_311(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_311_FEATURE_1, {"CreatedOn", "DateTime"})
        assert record["latitude"] == pytest.approx(44.10267726454463)
        assert record["longitude"] == pytest.approx(-123.07430953726018)

    def test_flatten_iso_normalizes_report_date(self):
        record = _flatten(_311_FEATURE_1, {"CreatedOn", "DateTime"})
        assert record["CreatedOn"] == _CREATED_ON_ISO
        assert record["DateTime"] == _CREATED_ON_ISO
        assert record["ServiceCod"] == "PDD10"

    def test_newest_fixture_parses_through_producer(self, complaints_311, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints_311.parse_socrata_row(
            _flatten(_311_FEATURE_1, {"CreatedOn", "DateTime"}),
            city_id="eugene",
        )
        assert event is not None
        assert event.city_id == "eugene"
        assert event.incident_id == "1"
        assert event.complaint_type == "Vehicle Stored on Street"
        assert event.latitude == pytest.approx(44.10267726454463)
        assert event.longitude == pytest.approx(-123.07430953726018)

    def test_third_fixture_h3_and_containment(self, complaints_311, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints_311.parse_socrata_row(
            _flatten(_311_FEATURE_3, {"CreatedOn", "DateTime"}),
            city_id="eugene",
        )
        assert event is not None
        assert event.incident_id == "3299"
        assert event.complaint_type == "Inspection Required"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert is_in_eugene_metro(event.latitude, event.longitude)

    def test_incident_id_falls_back_to_globalid(self, complaints_311, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_311_FEATURE_2, {"CreatedOn", "DateTime"})
        record.pop("FID")
        event = complaints_311.parse_socrata_row(record, city_id="eugene")
        assert event is not None
        assert event.incident_id == "5c50b204-96d0-4ff7-8e39-65cea22c9163"

    def test_row_without_any_id_is_dropped(self, complaints_311, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_311_FEATURE_1, {"CreatedOn", "DateTime"})
        record.pop("FID")
        record.pop("GlobalID")
        assert complaints_311.parse_socrata_row(record, city_id="eugene") is None


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


class TestEugeneDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_flatten_lifts_polygon_centroid_to_degrees(self):
        record = _flatten(_DEED_FEATURE_1, {"DATE_"})
        assert record["latitude"] == pytest.approx(43.994910, rel=1e-5)
        assert record["longitude"] == pytest.approx(-123.149160, rel=1e-5)

    def test_flatten_iso_normalizes_record_date(self):
        record = _flatten(_DEED_FEATURE_1, {"DATE_"})
        assert record["DATE_"] == _DATE_ISO
        assert record["ACQDIS"] == "A"

    def test_newest_fixture_parses_through_producer(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(
            _flatten(_DEED_FEATURE_1, {"DATE_"}),
            city_id="eugene",
        )
        assert event is not None
        assert event.city_id == "eugene"
        assert event.doc_id == "P02961"
        assert event.doc_type == "A"
        assert event.recorded_date.date().isoformat() == "2026-01-05"
        assert event.latitude == pytest.approx(43.994910, rel=1e-5)
        assert event.longitude == pytest.approx(-123.149160, rel=1e-5)

    def test_second_fixture_h3_and_containment(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(
            _flatten(_DEED_FEATURE_2, {"DATE_"}),
            city_id="eugene",
        )
        assert event is not None
        assert event.doc_id == "P02961"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert is_in_eugene_metro(event.latitude, event.longitude)

    def test_third_fixture_containment(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(
            _flatten(_DEED_FEATURE_3, {"DATE_"}),
            city_id="eugene",
        )
        assert event is not None
        assert event.doc_id == "P02961"
        assert is_in_eugene_metro(event.latitude, event.longitude)


class TestEugeneFeedSpec:
    def test_311_spec_matches_live_layer(self):
        spec = get_eugene_dataset("311")
        assert spec.platform == "arcgis"
        assert spec.endpoint == EUGENE_CAMPING_311_ENDPOINT
        assert spec.watermark_col == "CreatedOn"
        assert spec.id_keys == ["FID", "GlobalID"]
        assert spec.oid_field == "FID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "CreatedOn DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.field_map is COMPLAINTS_311_FIELD_MAP
        assert spec.topic == "raw.municipal.311"

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
        assert spec.field_map is SLA_FIELD_MAP
        assert spec.topic == "raw.municipal.sla"
        assert spec.alarm_exempt is True

    def test_deeds_spec_matches_live_layer(self):
        spec = get_eugene_dataset("deeds")
        assert spec.platform == "arcgis"
        assert spec.endpoint == EUGENE_CITYLAND_DEEDS_ENDPOINT
        assert spec.watermark_col == "DATE_"
        assert spec.id_keys == ["CITYDEED", "OBJECTID_1"]
        assert spec.oid_field == "OBJECTID_1"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 3
        assert spec.order_by == "DATE_ DESC"
        assert spec.interval_seconds == 600.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.field_map is DEEDS_FIELD_MAP
        assert spec.topic == "raw.municipal.deeds"

    def test_registered_feed_set(self):
        assert set(EUGENE_FEED_SPECS) == {"311", "sla", "deeds"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_eugene_dataset("permits")
        assert "eugene" in str(exc.value)
        assert "311" in str(exc.value)
        assert "deeds" in str(exc.value)

    def test_endpoints_all_on_services3_arcgis(self):
        for ep in (EUGENE_CAMPING_311_ENDPOINT, EUGENE_FOOD_SERVICE_SLA_ENDPOINT,
                   EUGENE_CITYLAND_DEEDS_ENDPOINT):
            assert "services3.arcgis.com" in ep
            assert "FeatureServer/0" in ep