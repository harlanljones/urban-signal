"""Unit tests for the Santa Fe, NM leaf (US-241): spatial module + field
maps + producer parse wiring.

Santa Fe is a ONE-FEED PARTIAL metro: CRM_Report_A_Problem_New_Public
(FeatureServer/0 at ``services7.arcgis.com/p0Gk2nDbPs7KEqSZ``, Tier 1,
daily, native WGS84 point geometry). PERMITS, SLA, and DEEDS stay Tier 3 —
only ``311`` is registered.

Tests pass WITHOUT a spine registration (no CityId.SANTA_FE, no REGISTRY
assertions — "santa_fe" stays a plain string). Spine-stable per the
leaf contract: no division/borough-resolution assertions and no
geocode-hook call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from FeatureServer/0 (newest rows
via ``orderByFields=CreationDate DESC`` at ``outSR=4326``; newest watermark
``1787949766476`` = 2026-08-28T20:42:46.476000+00:00). Fixtures are RAW
ArcGIS features (attributes + geometry); the tests run the real
``ArcGISClient._flatten_feature`` lift — geometry to latitude/longitude,
epoch-ms to ISO — before parsing, exactly as the live producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.complaints_311_producer import (
    Complaints311Producer,
)
from src.producers.field_maps import first_mapped
from src.producers.field_maps_santa_fe import (
    COMPLAINTS_311_FIELD_MAP,
    FIELD_MAP,
    GEOCODE_CONTEXT,
)
from src.spatial.cities.santa_fe import (
    REGISTRATION,
    SANTA_FE_311_ENDPOINT,
    SANTA_FE_CITY_ID,
    SANTA_FE_DIVISION_BBOXES,
    SANTA_FE_DIVISIONS,
    SANTA_FE_FEED_SPECS,
    SANTA_FE_GEOCODE_CONTEXT,
    SANTA_FE_METRO_BBOX,
    SANTA_FE_SUBMARKETS,
    get_santa_fe_dataset,
    is_in_greater_santa_fe_metro,
    is_in_santa_fe_metro,
)


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _flatten(feature):
    """Run the real ArcGIS flatten lift over a raw captured feature.

    ``date_fields`` is what the client discovers from the live layer's
    metadata: CreationDate is esriFieldTypeDate.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, {"CreationDate"})


# Newest rows on the 2026-08-28 probe (orderByFields=CreationDate DESC,
# outSR=4326). Byte-verbatim: problemtype coded values, status string domain,
# CreationDate epoch ms, native WGS84 point geometry.
_FEATURE_ENRAMPMENTS = {
    "attributes": {
        "objectid": 3160,
        "globalid": "ba1ba97e-329a-402a-87fe-920aff129d53",
        "problemtype": "encampments",
        "problem2": None,
        "status": "Submitted",
        "resolved_on": None,
        "CreationDate": 1787949766476,
        "field_notes": None,
    },
    "geometry": {
        "x": -105.992067688,
        "y": 35.642782711,
    },
}

_FEATURE_ROADS = {
    "attributes": {
        "objectid": 3159,
        "globalid": "5e7ace02-f14b-4b26-83e8-c1a52f577de4",
        "problemtype": "roads",
        "problem2": "signals",
        "status": "Submitted",
        "resolved_on": None,
        "CreationDate": 1787944479869,
        "field_notes": None,
    },
    "geometry": {
        "x": -105.9704024,
        "y": 35.652168609,
    },
}

_FEATURE_GRAFFITI = {
    "attributes": {
        "objectid": 3158,
        "globalid": "529112e4-713c-4734-805b-539d44a9990a",
        "problemtype": "roads",
        "problem2": "traffic_engineer_study",
        "status": "Submitted",
        "resolved_on": None,
        "CreationDate": 1787943649478,
        "field_notes": None,
    },
    "geometry": {
        "x": -105.942257948,
        "y": 35.722559465,
    },
}

_CREATIONDATE_ISO = "2026-08-28T20:42:46.476000+00:00"


class TestSantaFeSpatial:
    def test_metro_bbox_sanity(self):
        assert SANTA_FE_METRO_BBOX["min_lat"] < SANTA_FE_METRO_BBOX["max_lat"]
        assert SANTA_FE_METRO_BBOX["min_lng"] < SANTA_FE_METRO_BBOX["max_lng"]

    def test_is_in_santa_fe_metro_rejects_missing_coordinates(self):
        assert is_in_santa_fe_metro(None, None) is False
        assert is_in_santa_fe_metro(35.6869, None) is False
        assert is_in_santa_fe_metro(None, -105.9372) is False

    def test_is_in_santa_fe_metro_rejects_other_cities(self):
        assert is_in_santa_fe_metro(35.2271, -80.8431) is False   # Charlotte
        assert is_in_santa_fe_metro(35.0844, -106.6504) is False  # Albuquerque
        assert is_in_santa_fe_metro(35.6880, -105.80) is False    # Las Vegas, NM (east, outside)

    def test_downtown_anchors_are_contained(self):
        assert is_in_santa_fe_metro(35.6869, -105.9372)  # Plaza
        assert is_in_santa_fe_metro(35.6770, -105.9500)  # Railyard
        assert is_in_santa_fe_metro(35.6850, -105.9250)  # Eastside

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_FEATURE_ENRAMPMENTS, _FEATURE_ROADS, _FEATURE_GRAFFITI):
            assert is_in_santa_fe_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in SANTA_FE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= SANTA_FE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= SANTA_FE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= SANTA_FE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= SANTA_FE_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in SANTA_FE_SUBMARKETS.items():
            bbox = SANTA_FE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in SANTA_FE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(SANTA_FE_SUBMARKETS)

    def test_submarkets_carry_the_santa_fe_city_id(self):
        assert {m.city_id for m in SANTA_FE_SUBMARKETS.values()} == {"santa_fe"}

    def test_city_id_and_registration_shape(self):
        assert SANTA_FE_CITY_ID == "santa_fe"
        assert REGISTRATION.metro_bbox is SANTA_FE_METRO_BBOX
        assert REGISTRATION.submarkets is SANTA_FE_SUBMARKETS
        assert REGISTRATION.division_bboxes is SANTA_FE_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_santa_fe_metro
        assert len(REGISTRATION.divisions) == 6
        assert len(SANTA_FE_SUBMARKETS) == 10

    def test_required_real_neighborhoods_present(self):
        assert set(SANTA_FE_SUBMARKETS) == {
            "Downtown Plaza",
            "Baca Street",
            "South Capitol",
            "Siler Road",
            "Railyard",
            "Eastside",
            "Casa Solana",
            "Cerro Gordo",
            "Agua Fria",
            "Southside",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_santa_fe_metro is is_in_santa_fe_metro


class TestSantaFeFieldMaps:
    def test_311_map_reads_live_columns(self):
        assert COMPLAINTS_311_FIELD_MAP["incident_id"] == ["globalid", "objectid"]
        assert COMPLAINTS_311_FIELD_MAP["complaint_type"] == ["problemtype"]
        assert COMPLAINTS_311_FIELD_MAP["created_date"] == ["CreationDate"]
        assert COMPLAINTS_311_FIELD_MAP["status"] == ["status"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"311": COMPLAINTS_311_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Santa Fe, NM"
        assert SANTA_FE_GEOCODE_CONTEXT == "Santa Fe, NM"

    def test_no_geometry_attributes_in_map(self):
        """Coordinates come only from the outSR=4326 geometry lift, not
        attribute columns. No latitude/longitude candidates are declared."""
        assert "latitude" not in COMPLAINTS_311_FIELD_MAP
        assert "longitude" not in COMPLAINTS_311_FIELD_MAP

    def test_no_borough_candidate_so_source_neighborhood_passes_none(self):
        """No neighborhood/district column exists on the layer (Omaha
        discipline): no borough candidate is declared, so
        source_neighborhood passes through as None on parsed events."""
        assert "borough" not in COMPLAINTS_311_FIELD_MAP
        assert "neighborhood" not in COMPLAINTS_311_FIELD_MAP

    def test_no_zipcode_address_or_bbl_candidates(self):
        assert "zipcode" not in COMPLAINTS_311_FIELD_MAP
        assert "incident_address" not in COMPLAINTS_311_FIELD_MAP
        assert "bbl" not in COMPLAINTS_311_FIELD_MAP

    def test_first_mapped_reads_globalid(self):
        attrs = _FEATURE_ENRAMPMENTS["attributes"]
        assert first_mapped(attrs, COMPLAINTS_311_FIELD_MAP, "incident_id") == "ba1ba97e-329a-402a-87fe-920aff129d53"

    def test_first_mapped_globalid_falls_back_to_objectid(self):
        attrs = dict(_FEATURE_ENRAMPMENTS["attributes"])
        attrs.pop("globalid")
        assert first_mapped(attrs, COMPLAINTS_311_FIELD_MAP, "incident_id") == 3160


class TestSantaFe311Parsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            return Complaints311Producer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_FEATURE_ENRAMPMENTS)
        assert record["latitude"] == pytest.approx(35.642782711)
        assert record["longitude"] == pytest.approx(-105.992067688)

    def test_flatten_iso_normalizes_creationdate(self):
        record = _flatten(_FEATURE_ROADS)
        assert record["CreationDate"] == "2026-08-28T19:14:39.869000+00:00"

    def test_encampment_fixture_parses_through_producer(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints.parse_socrata_row(_flatten(_FEATURE_ENRAMPMENTS), city_id="santa_fe")
        assert event is not None
        assert event.city_id == "santa_fe"
        assert event.incident_id == "ba1ba97e-329a-402a-87fe-920aff129d53"
        assert event.complaint_type == "encampments"
        assert event.status == "Submitted"
        assert event.latitude == pytest.approx(35.642782711)
        assert event.longitude == pytest.approx(-105.992067688)
        assert event.created_date is not None
        assert event.closed_date is None
        assert event.source_neighborhood is None
        assert event.zipcode == ""
        assert event.incident_address is None

    def test_roads_fixture_parses_with_complaint_type(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints.parse_socrata_row(_flatten(_FEATURE_ROADS), city_id="santa_fe")
        assert event is not None
        assert event.complaint_type == "roads"
        assert event.status == "Submitted"
        assert event.latitude == pytest.approx(35.652168609)
        assert event.longitude == pytest.approx(-105.9704024)

    def test_graffiti_fixture_indexes_h3(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints.parse_socrata_row(_flatten(_FEATURE_GRAFFITI), city_id="santa_fe")
        assert event is not None
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_santa_fe_metro(event.latitude, event.longitude)

    def test_all_three_fixtures_share_watermark_date(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        events = [
            complaints.parse_socrata_row(_flatten(f), city_id="santa_fe")
            for f in (_FEATURE_ENRAMPMENTS, _FEATURE_ROADS, _FEATURE_GRAFFITI)
        ]
        assert all(e is not None for e in events)
        assert {e.created_date.isoformat() for e in events} == {
            "2026-08-28T20:42:46.476000+00:00",
            "2026-08-28T19:14:39.869000+00:00",
            "2026-08-28T19:00:49.478000+00:00",
        }
        assert len({e.h3_res9 for e in events}) == 3

    def test_incident_id_falls_back_to_objectid(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_FEATURE_ENRAMPMENTS)
        record.pop("globalid")
        event = complaints.parse_socrata_row(record, city_id="santa_fe")
        assert event is not None
        assert event.incident_id == "3160"

    def test_row_without_any_id_is_dropped(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_FEATURE_ENRAMPMENTS)
        record.pop("globalid")
        record.pop("objectid")
        assert complaints.parse_socrata_row(record, city_id="santa_fe") is None

    def test_geometry_less_row_is_dropped(self, complaints, monkeypatch):
        """No address column exists on the feed, so a row without geometry
        cannot be geocoded (needs_geocode=False) and drops."""
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_FEATURE_ENRAMPMENTS)
        record.pop("latitude")
        record.pop("longitude")
        assert complaints.parse_socrata_row(record, city_id="santa_fe") is None

    def test_complaint_type_classifies_through_shift_dynamics(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints.parse_socrata_row(_flatten(_FEATURE_ENRAMPMENTS), city_id="santa_fe")
        assert event is not None
        assert event.category is not None


class TestSantaFeFeedSpec:
    def test_311_spec_matches_live_layer(self):
        spec = get_santa_fe_dataset("311")
        assert spec.platform == "arcgis"
        assert spec.endpoint == SANTA_FE_311_ENDPOINT
        assert spec.watermark_col == "CreationDate"
        assert spec.id_keys == ["globalid"]
        assert spec.oid_field == "objectid"
        assert spec.max_record_count == 1000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "CreationDate DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.geocode_context == "Santa Fe, NM"
        assert spec.field_map == COMPLAINTS_311_FIELD_MAP
        assert spec.topic == "raw.municipal.311"

    def test_registered_feed_set_is_311_only(self):
        assert set(SANTA_FE_FEED_SPECS) == {"311"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_santa_fe_dataset("permits")
        assert "santa_fe" in str(exc.value)
        assert "311" in str(exc.value)

    def test_endpoint_is_the_probed_featureserver(self):
        assert "services7.arcgis.com/p0Gk2nDbPs7KEqSZ" in SANTA_FE_311_ENDPOINT
        assert "CRM_Report_A_Problem_New_Public/FeatureServer/0" in SANTA_FE_311_ENDPOINT