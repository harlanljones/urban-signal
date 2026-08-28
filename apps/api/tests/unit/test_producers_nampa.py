"""Unit tests for the Nampa, ID leaf (US-243): spatial module + field
maps + producer parse wiring.

Nampa is a ONE-FEED PARTIAL metro: ROW_Road_Closure road-closure permits
(ArcGIS FeatureServer/3 on the city's utility ArcGIS server, polyline
geometry, CreationDate watermark, ~76 rows). Building permits are Tyler
EnerGov SaaS (no REST API); 311/SLA/deeds are absent — only ``permits``
is registered (road closure permits through the DOBPermitsProducer
field-map path).

Tests pass WITHOUT a spine registration (no CityId.NAMPA, no REGISTRY
assertions — "nampa" stays a plain string). Spine-stable per the
wave-5 leaf contract: no division/borough-resolution assertions and no
geocode-hook call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from FeatureServer/3 (newest
rows via ``orderByFields=CreationDate DESC`` at ``outSR=4326``; newest
watermark ``1787857841000`` = 2026-08-27T19:10:41+00:00). Fixtures are
RAW ArcGIS features (attributes + polyline geometry); the tests run the
real ``ArcGISClient._flatten_feature`` lift — polyline paths reduced to a
representative (mean) latitude/longitude, epoch-ms to ISO — before parsing,
exactly as the live producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps_nampa import (
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.nampa import (
    NAMPA_CITY_ID,
    NAMPA_DIVISION_BBOXES,
    NAMPA_DIVISIONS,
    NAMPA_FEED_SPECS,
    NAMPA_GEOCODE_CONTEXT,
    NAMPA_METRO_BBOX,
    NAMPA_STREET_CUT_ENDPOINT,
    NAMPA_SUBMARKETS,
    REGISTRATION,
    get_nampa_dataset,
    is_in_greater_nampa_metro,
    is_in_nampa_metro,
)
from src.spatial.city_registry import FeedType


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _flatten(feature):
    """Run the real ArcGIS flatten lift over a raw captured feature.

    ``date_fields`` is what the client discovers from the live layer's
    metadata: CreationDate, starttime, endtime, and EditDate are
    esriFieldTypeDate columns; everything else is a string.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        feature, {"CreationDate", "starttime", "endtime", "EditDate"}
    )


# Newest rows on the 2026-08-28 probe (orderByFields=CreationDate DESC,
# outSR=4326). Byte-verbatim: polyline paths in WGS84, identifier permit
# IDs, Status/type_/subtype_ columns, CreationDate epoch-ms.
_FEATURE_41695 = {
    "attributes": {
        "OBJECTID": 41695,
        "street": "2nd St S",
        "type_": "Road Closure",
        "subtype_": "Capital Project",
        "description": "Sewer Line Installation",
        "direction": "Both Directions",
        "impact": "Hard Closure",
        "starttime": 1788786001000,
        "endtime": 1791464399000,
        "textstart": "9/7/26",
        "textend": "10/7/26",
        "textdescr": "Road Closure",
        "altroute": "22nd Ave S/Powerline/Amity/Southside/2nd St S",
        "access_": "Local Access",
        "activeincid": "Yes",
        "Status": "Active",
        "identifier": "ROW-08302-2026",
        "reference": "Nampa City",
        "pocname": "Cheney, Travis",
        "pocemail": "PM@mountainwestex.com",
        "pocphone": "(208) 506-2134",
        "permitcontractor": "Mountain West Excavation",
        "url": None,
        "Comments": None,
        "GlobalID": "{1399AFF1-67D9-4AE5-A5F8-622D78D905D1}",
        "CreationDate": 1787857841000,
        "Creator": "gisservicepublishing",
        "EditDate": 1787857841000,
        "Editor": "gisservicepublishing",
        "Shape__Length": 2625.741895468002
    },
    "geometry": {
        "paths": [
            [
                [-116.54438483934425, 43.56686264600045],
                [-116.54198212886406, 43.565276441624185],
                [-116.53832467064267, 43.565121688202574],
                [-116.53741698043896, 43.56485086741352],
                [-116.53597535391538, 43.56382560902354],
            ]
        ]
    }
}

_FEATURE_41295 = {
    "attributes": {
        "OBJECTID": 41295,
        "street": "Flamingo Ave",
        "type_": "Road Closure",
        "subtype_": "Development",
        "description": "Approach for Ederra Subdivision",
        "direction": "Both Directions",
        "impact": "Hard Closure",
        "starttime": 1787576401000,
        "endtime": 1791637199000,
        "textstart": "8/24/26",
        "textend": "10/9/26",
        "textdescr": None,
        "altroute": "Midway/Orchard/Middleton",
        "access_": "No Access",
        "activeincid": "Yes",
        "Status": "Active",
        "identifier": "ROW-08220-2026",
        "reference": "Nampa City",
        "pocname": "Baldwin, Samantha",
        "pocemail": "sami@nampapaving.com",
        "pocphone": "(208) 919-1461",
        "permitcontractor": "Nampa Paving & Asphalt",
        "url": None,
        "Comments": None,
        "GlobalID": "{5EBD8049-99A2-42F4-AC4A-2AC5ECD93084}",
        "CreationDate": 1786036207000,
        "Creator": "gisservicepublishing",
        "EditDate": 1786036207000,
        "Editor": "gisservicepublishing",
        "Shape__Length": 1285.750261802077
    },
    "geometry": {
        "paths": [
            [
                [-116.62603384531117, 43.59766143248051],
                [-116.62118037063411, 43.597661432903315],
            ]
        ]
    }
}

_FEATURE_41294 = {
    "attributes": {
        "OBJECTID": 41294,
        "street": "14th Ave S",
        "type_": "Road Closure",
        "subtype_": "Capital Project",
        "description": "Water Line Replacement",
        "direction": "Both Directions",
        "impact": "Hard Closure",
        "starttime": 1786971601000,
        "endtime": 1788353999000,
        "textstart": "8/17/26",
        "textend": "9/1/26",
        "textdescr": None,
        "altroute": "13 Ave S/1st St S",
        "access_": "No Access",
        "activeincid": "Yes",
        "Status": "Active",
        "identifier": "ROW-08242-2026",
        "reference": "Nampa City",
        "pocname": "Mortensen, Gabe",
        "pocemail": "gabe@l2excavation.com",
        "pocphone": "(303) 895-5997",
        "permitcontractor": "L2 Excavation",
        "url": None,
        "Comments": None,
        "GlobalID": "{E076581A-5FFD-45A3-B6D3-79F5612A99A1}",
        "CreationDate": 1786024073000,
        "Creator": "gisservicepublishing",
        "EditDate": 1786024073000,
        "Editor": "gisservicepublishing",
        "Shape__Length": 262.81109304641984
    },
    "geometry": {
        "paths": [
            [
                [-116.55682977816191, 43.57806231688423],
                [-116.55749292579276, 43.577526207090344],
            ]
        ]
    }
}

_NEWEST_ISO = "2026-08-27T19:10:41+00:00"


class TestNampaSpatial:
    def test_metro_bbox_sanity(self):
        assert NAMPA_METRO_BBOX["min_lat"] < NAMPA_METRO_BBOX["max_lat"]
        assert NAMPA_METRO_BBOX["min_lng"] < NAMPA_METRO_BBOX["max_lng"]

    def test_is_in_nampa_metro_rejects_missing_coordinates(self):
        assert is_in_nampa_metro(None, None) is False
        assert is_in_nampa_metro(43.58, None) is False
        assert is_in_nampa_metro(None, -116.564) is False

    def test_is_in_nampa_metro_rejects_other_cities(self):
        assert is_in_nampa_metro(43.615, -116.201) is False   # Boise
        assert is_in_nampa_metro(43.6626, -116.6857) is False  # Caldwell
        assert is_in_nampa_metro(43.6691, -117.03) is False    # Ontario, OR
        assert is_in_nampa_metro(33.7490, -84.3880) is False   # Atlanta

    def test_downtown_anchors_are_contained(self):
        assert is_in_nampa_metro(43.580, -116.564)  # Downtown Nampa Civic Center
        assert is_in_nampa_metro(43.585, -116.560)  # Nampa Public Library
        assert is_in_nampa_metro(43.562, -116.564)  # CWI Nampa Campus

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_FEATURE_41695, _FEATURE_41295, _FEATURE_41294):
            lng, lat = _coords_for(feature)
            assert is_in_nampa_metro(lat, lng)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in NAMPA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= NAMPA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= NAMPA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= NAMPA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= NAMPA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in NAMPA_SUBMARKETS.items():
            bbox = NAMPA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in NAMPA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(NAMPA_SUBMARKETS)

    def test_submarkets_carry_the_nampa_city_id(self):
        assert {m.city_id for m in NAMPA_SUBMARKETS.values()} == {"nampa"}

    def test_city_id_and_registration_shape(self):
        assert NAMPA_CITY_ID == "nampa"
        assert REGISTRATION.metro_bbox is NAMPA_METRO_BBOX
        assert REGISTRATION.submarkets is NAMPA_SUBMARKETS
        assert REGISTRATION.division_bboxes is NAMPA_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_nampa_metro
        assert len(REGISTRATION.divisions) == 6
        assert len(NAMPA_SUBMARKETS) == 8

    def test_required_real_neighborhoods_present(self):
        assert set(NAMPA_SUBMARKETS) == {
            "Downtown Nampa",
            "Old Nampa",
            "College of Western Idaho",
            "West Nampa",
            "Middleton Road Edge",
            "South Nampa",
            "North Nampa",
            "East Nampa",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_nampa_metro is is_in_nampa_metro


def _coords_for(feature):
    """The exact mean-of-path-points reduction ArcGISClient applies."""
    paths = feature["geometry"]["paths"]
    points = [pt for path in paths for pt in path]
    lng = sum(p[0] for p in points) / len(points)
    lat = sum(p[1] for p in points) / len(points)
    return lng, lat


class TestNampaFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["identifier", "OBJECTID"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["CreationDate"]
        assert PERMITS_FIELD_MAP["status"] == ["Status"]
        assert PERMITS_FIELD_MAP["job_type"] == ["type_", "subtype_"]
        assert PERMITS_FIELD_MAP["address_street"] == ["street"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Nampa, ID"
        assert NAMPA_GEOCODE_CONTEXT == "Nampa, ID"

    def test_state_plane_coordinates_are_never_candidates(self):
        """No latitude/longitude candidates are declared — coordinates come
        only from the outSR=4326 geometry lift. The native CRS is Idaho
        State Plane West (wkid 102670/2243, feet)."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP

    def test_no_borough_zipcode_or_bbl_candidates(self):
        """No neighborhood/district, site-zip, or parcel/APN column exists
        on the layer (Omaha discipline) — all stay undeclared."""
        assert "borough" not in PERMITS_FIELD_MAP
        assert "neighborhood" not in PERMITS_FIELD_MAP
        assert "zipcode" not in PERMITS_FIELD_MAP
        assert "bbl" not in PERMITS_FIELD_MAP

    def test_pii_columns_never_become_candidates(self):
        mapped = {c for values in PERMITS_FIELD_MAP.values() for c in values}
        assert mapped
        for values in PERMITS_FIELD_MAP.values():
            for col in values:
                assert col not in DROPPED_PII_COLUMNS
        assert {"pocname", "pocemail", "pocphone", "permitcontractor"} <= set(DROPPED_PII_COLUMNS)


class TestNampaPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_polyline_geometry_to_degrees(self):
        record = _flatten(_FEATURE_41695)
        lng, lat = _coords_for(_FEATURE_41695)
        assert record["latitude"] == pytest.approx(lat)
        assert record["longitude"] == pytest.approx(lng)

    def test_flatten_iso_normalizes_the_watermark_only(self):
        record = _flatten(_FEATURE_41695)
        assert record["CreationDate"] == _NEWEST_ISO
        # starttime/endtime are esri dates too and ISO-normalize.
        assert record["starttime"] is not None

    def test_sewer_line_fixture_parses_through_the_producer(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_41695), city_id="nampa")
        assert event is not None
        assert event.city_id == "nampa"
        assert event.job_id == "ROW-08302-2026"
        assert event.status == "Active"
        lng, lat = _coords_for(_FEATURE_41695)
        assert event.latitude == pytest.approx(lat)
        assert event.longitude == pytest.approx(lng)
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat() == _NEWEST_ISO
        assert event.address_street == "2nd St S"
        assert event.zipcode == ""
        assert event.bbl is None

    def test_flamingo_fixture_indexes_h3_and_sits_in_metro(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_41295), city_id="nampa")
        assert event is not None
        assert event.job_id == "ROW-08220-2026"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_nampa_metro(event.latitude, event.longitude)

    def test_water_line_fixture_containment(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_41294), city_id="nampa")
        assert event is not None
        assert event.job_id == "ROW-08242-2026"
        assert is_in_nampa_metro(event.latitude, event.longitude)

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_41695)
        record.pop("identifier")
        event = permits.parse_socrata_row(record, city_id="nampa")
        assert event is not None
        assert event.job_id == "41695"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_41695)
        record.pop("identifier")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="nampa") is None

    def test_road_closure_type_codes_stay_unclassified_at_the_leaf(self, permits, monkeypatch):
        """type_ is 'Road Closure' — not among the producer's recognized
        codes, so it lands on OT honestly."""
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_41695), city_id="nampa")
        assert event is not None
        assert event.job_type == JobType.OT

    def test_all_three_fixtures_share_distinct_job_ids(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        events = [
            permits.parse_socrata_row(_flatten(f), city_id="nampa")
            for f in (_FEATURE_41695, _FEATURE_41295, _FEATURE_41294)
        ]
        assert all(e is not None for e in events)
        assert {e.job_id for e in events} == {
            "ROW-08302-2026", "ROW-08220-2026", "ROW-08242-2026"
        }
        assert len({e.h3_res9 for e in events}) == 3


class TestNampaFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_nampa_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == NAMPA_STREET_CUT_ENDPOINT
        assert spec.watermark_col == "CreationDate"
        assert spec.id_keys == ["identifier", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 7
        assert spec.order_by == "CreationDate DESC"
        assert spec.interval_seconds == 600.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"

    def test_registered_feed_set_is_permits_only(self):
        assert set(NAMPA_FEED_SPECS) == {"permits"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_nampa_dataset("sla")
        assert "nampa" in str(exc.value)
        assert "permits" in str(exc.value)

    def test_endpoint_is_the_probed_feature_server(self):
        assert "utility.arcgis.com" in NAMPA_STREET_CUT_ENDPOINT
        assert (
            "PublicRoadClosures/FeatureServer/3"
            in NAMPA_STREET_CUT_ENDPOINT
        )