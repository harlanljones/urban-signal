"""Unit tests for the Santa Rosa, CA leaf (US-247): spatial module + field
maps + crime producer parse wiring.

Santa Rosa is a ONE-FEED PARTIAL metro: Sonoma County Sheriff's Office
Incident Data (Socrata ``3rsj-iche``, Tier 1, daily, native Socrata point
geometry). Permits, 311, SLA, and deeds all stay Tier 3.

Tests pass WITHOUT a spine registration (no CityId.SANTA_ROSA, no REGISTRY
assertions — "santa_rosa" stays a plain string). Spine-stable per the
leaf contract: no division/borough-resolution assertions and no geocode-hook
call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from
data.sonomacounty.ca.gov/resource/3rsj-iche.json ($where=city='SANTA ROSA',
$order=date_time DESC) — newest 3 rows by watermark.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_santa_rosa import (
    CRIME_FIELD_MAP,
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
)
from src.spatial.cities.santa_rosa import (
    REGISTRATION,
    SANTA_ROSA_CITY_ID,
    SANTA_ROSA_CRIME_ENDPOINT,
    SANTA_ROSA_DIVISION_BBOXES,
    SANTA_ROSA_DIVISIONS,
    SANTA_ROSA_FEED_SPECS,
    SANTA_ROSA_GEOCODE_CONTEXT,
    SANTA_ROSA_METRO_BBOX,
    SANTA_ROSA_SUBMARKETS,
    get_santa_rosa_dataset,
    is_in_greater_santa_rosa_metro,
    is_in_santa_rosa_metro,
)
from src.spatial.city_registry import FeedType

# Newest 3 rows on the live probe 2026-08-28 (city=SANTA ROSA,
# order=date_time DESC). Native Socrata point container (latitude/longitude
# dict keys). Captured byte-verbatim: note the location dict uses
# {latitude, longitude, human_address} format (not GeoJSON).
_CRIME_FIXTURE_TODD = {
    "id": "LW_DWInformRMS_89028FD7-FFB3-CC5B-96C8-08DF04BCF75F",
    "agency_code": "SCSD",
    "agency": "Sonoma County Sheriff's Office",
    "incident_number": "SD260827018",
    "date_time": "2026-08-27T12:10:51.000",
    "incident_type": "All Other - Criminal",
    "location_type": "COMMERCIAL / OFFICE BUILDING",
    "city": "SANTA ROSA",
    "intersection": "E Todd Rd / Santa Rosa Ave / Todd Rd",
    "location": {
        "latitude": "38.387072",
        "longitude": "-122.713579",
        "human_address": "{\"address\": \"\", \"city\": \"\", \"state\": \"\", \"zip\": \"\"}"
    },
    "upload": "2026-08-28T00:00:00.000",
}

_CRIME_FIXTURE_CARRIAGE = {
    "id": "LW_DWInformRMS_5A4E0F76-88FA-C5FD-CC54-08DF04B96D83",
    "agency_code": "SCSD",
    "agency": "Sonoma County Sheriff's Office",
    "incident_number": "SD260827003",
    "date_time": "2026-08-27T05:26:33.000",
    "incident_type": "Burglary",
    "location_type": "RESIDENTIAL FACILITY",
    "city": "SANTA ROSA",
    "intersection": "Carriage Ln / Limelight Pl",
    "location": {
        "latitude": "38.515107",
        "longitude": "-122.759691",
        "human_address": "{\"address\": \"\", \"city\": \"\", \"state\": \"\", \"zip\": \"\"}"
    },
    "upload": "2026-08-28T00:00:00.000",
}

_CRIME_FIXTURE_DUTTON = {
    "id": "LW_DWInformRMS_276330A6-08F9-C970-DCF1-08DF045E6816",
    "agency_code": "SCSD",
    "agency": "Sonoma County Sheriff's Office",
    "incident_number": "SD260827001",
    "date_time": "2026-08-27T00:33:00.000",
    "incident_type": "Drug Offense",
    "location_type": "HIGHWAY / ROAD / ALLEY / STREET",
    "city": "SANTA ROSA",
    "intersection": "Dutton Meadow / Hearn Ave",
    "location": {
        "latitude": "38.414227",
        "longitude": "-122.729289",
        "human_address": "{\"address\": \"\", \"city\": \"\", \"state\": \"\", \"zip\": \"\"}"
    },
    "upload": "2026-08-28T00:00:00.000",
}

_WATERMARK_ISO = "2026-08-27T12:10:51+00:00"


class TestSantaRosaSpatial:
    def test_metro_bbox_sanity(self):
        assert SANTA_ROSA_METRO_BBOX["min_lat"] < SANTA_ROSA_METRO_BBOX["max_lat"]
        assert SANTA_ROSA_METRO_BBOX["min_lng"] < SANTA_ROSA_METRO_BBOX["max_lng"]

    def test_is_in_santa_rosa_metro_rejects_missing_coordinates(self):
        assert is_in_santa_rosa_metro(None, None) is False
        assert is_in_santa_rosa_metro(38.4405, None) is False
        assert is_in_santa_rosa_metro(None, -122.7144) is False

    def test_is_in_santa_rosa_metro_rejects_other_cities(self):
        assert is_in_santa_rosa_metro(40.7128, -74.0060) is False   # NYC
        assert is_in_santa_rosa_metro(37.7749, -122.4194) is False   # SF
        assert is_in_santa_rosa_metro(37.8715, -122.2730) is False   # Berkeley
        assert is_in_santa_rosa_metro(38.5766, -121.4934) is False   # Sacramento

    def test_downtown_anchors_are_contained(self):
        assert is_in_santa_rosa_metro(38.4405, -122.7144)  # Old Courthouse Square
        assert is_in_santa_rosa_metro(38.4380, -122.7220)  # Railroad Square
        assert is_in_santa_rosa_metro(38.4310, -122.7360)  # Roseland

    def test_live_fixture_coordinates_are_contained(self):
        for fixture in (_CRIME_FIXTURE_TODD, _CRIME_FIXTURE_CARRIAGE, _CRIME_FIXTURE_DUTTON):
            loc = fixture["location"]
            assert is_in_santa_rosa_metro(
                float(loc["latitude"]), float(loc["longitude"])
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in SANTA_ROSA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= SANTA_ROSA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= SANTA_ROSA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= SANTA_ROSA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= SANTA_ROSA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in SANTA_ROSA_SUBMARKETS.items():
            bbox = SANTA_ROSA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in SANTA_ROSA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(SANTA_ROSA_SUBMARKETS)

    def test_submarkets_carry_the_santa_rosa_city_id(self):
        assert {m.city_id for m in SANTA_ROSA_SUBMARKETS.values()} == {"santa_rosa"}

    def test_city_id_and_registration_shape(self):
        assert SANTA_ROSA_CITY_ID == "santa_rosa"
        assert REGISTRATION.metro_bbox is SANTA_ROSA_METRO_BBOX
        assert REGISTRATION.submarkets is SANTA_ROSA_SUBMARKETS
        assert REGISTRATION.division_bboxes is SANTA_ROSA_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_santa_rosa_metro
        assert len(REGISTRATION.divisions) == 6
        assert len(SANTA_ROSA_SUBMARKETS) == 12

    def test_required_real_neighborhoods_present(self):
        assert set(SANTA_ROSA_SUBMARKETS) == {
            "Downtown",
            "Railroad Square",
            "West End",
            "Northwest Santa Rosa",
            "Larkfield-Wikiup",
            "North Santa Rosa",
            "Roseland",
            "Southwest Santa Rosa",
            "Bennett Valley",
            "Southeast Santa Rosa",
            "Rincon Valley",
            "Fountaingrove",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_santa_rosa_metro is is_in_santa_rosa_metro


class TestSantaRosaFieldMaps:
    def test_crime_map_reads_live_columns(self):
        assert CRIME_FIELD_MAP["incident_id"] == ["id", "incident_number"]
        assert CRIME_FIELD_MAP["offense_type"] == ["incident_type"]
        assert CRIME_FIELD_MAP["occurred_date"] == ["date_time"]
        assert CRIME_FIELD_MAP["reported_date"] == ["upload"]
        assert CRIME_FIELD_MAP["borough"] == ["city"]
        assert CRIME_FIELD_MAP["address"] == ["intersection", "location_address"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"crime": CRIME_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Santa Rosa, CA"
        assert SANTA_ROSA_GEOCODE_CONTEXT == "Santa Rosa, CA"

    def test_latitude_longitude_are_never_mapped(self):
        """Coordinates come from the Socrata location point container
        (latitude/longitude dict keys), never from field-mapped columns."""
        assert "latitude" not in CRIME_FIELD_MAP
        assert "longitude" not in CRIME_FIELD_MAP
        attrs = _CRIME_FIXTURE_TODD
        assert first_mapped(attrs, CRIME_FIELD_MAP, "latitude") is None
        assert first_mapped(attrs, CRIME_FIELD_MAP, "longitude") is None

    def test_agency_columns_never_become_candidates(self):
        mapped = {c for values in CRIME_FIELD_MAP.values() for c in values}
        assert mapped
        for col in DROPPED_PII_COLUMNS:
            assert col not in mapped

    def test_no_zipcode_or_bbl_candidates(self):
        """No zipcode or bbl column exists on the layer."""
        assert "zipcode" not in CRIME_FIELD_MAP
        assert "bbl" not in CRIME_FIELD_MAP

    def test_no_borough_candidate_so_source_neighborhood_passes_none(self):
        """No neighborhood/district/borough column on the Sheriff layer
        (Omaha discipline): the city field maps to borough, but division
        resolution comes from coordinates at ingest."""
        assert "neighborhood" not in CRIME_FIELD_MAP


class TestSantaRosaCrimeParsing:
    @pytest.fixture
    def crime(self):
        with patch("src.producers.crime_incidents_producer.BaseKafkaProducer"):
            from src.producers.crime_incidents_producer import CrimeIncidentsProducer
            return CrimeIncidentsProducer()

    def test_todd_fixture_parses_through_the_producer(self, crime, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: CRIME_FIELD_MAP,
        )
        event = crime.parse_socrata_row(_CRIME_FIXTURE_TODD, city_id="santa_rosa")
        assert event is not None
        assert event.city_id == "santa_rosa"
        assert event.incident_id == "LW_DWInformRMS_89028FD7-FFB3-CC5B-96C8-08DF04BCF75F"
        assert event.offense_type == "All Other - Criminal"
        assert event.offense_class == "PART2"
        assert event.address == "E Todd Rd / Santa Rosa Ave / Todd Rd"
        assert event.latitude == pytest.approx(38.387072)
        assert event.longitude == pytest.approx(-122.713579)
        assert event.occurred_date is not None
        assert event.occurred_date.isoformat() == "2026-08-27T12:10:51"
        assert event.reported_date is not None
        assert event.reported_date.isoformat() == "2026-08-28T00:00:00"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None

    def test_carriage_fixture_burglary_classifies_as_part1(self, crime, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: CRIME_FIELD_MAP,
        )
        event = crime.parse_socrata_row(_CRIME_FIXTURE_CARRIAGE, city_id="santa_rosa")
        assert event is not None
        assert event.offense_type == "Burglary"
        assert event.offense_class == "PART1"
        assert event.latitude == pytest.approx(38.515107)
        assert event.longitude == pytest.approx(-122.759691)
        assert is_in_santa_rosa_metro(event.latitude, event.longitude)

    def test_dutton_fixture_parses_and_metro_containment(self, crime, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: CRIME_FIELD_MAP,
        )
        event = crime.parse_socrata_row(_CRIME_FIXTURE_DUTTON, city_id="santa_rosa")
        assert event is not None
        assert event.incident_id == "LW_DWInformRMS_276330A6-08F9-C970-DCF1-08DF045E6816"
        assert event.offense_type == "Drug Offense"
        assert event.offense_class == "PART2"
        assert event.h3_res7 is not None
        assert is_in_santa_rosa_metro(event.latitude, event.longitude)

    def test_all_three_fixtures_share_the_upload_watermark(self, crime, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: CRIME_FIELD_MAP,
        )
        events = [
            crime.parse_socrata_row(f, city_id="santa_rosa")
            for f in (_CRIME_FIXTURE_TODD, _CRIME_FIXTURE_CARRIAGE, _CRIME_FIXTURE_DUTTON)
        ]
        assert all(e is not None for e in events)
        assert {e.reported_date.isoformat() for e in events} == {"2026-08-28T00:00:00"}
        assert len({e.h3_res9 for e in events}) == 3

    def test_incident_id_falls_back_to_incident_number(self, crime, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: CRIME_FIELD_MAP,
        )
        record = dict(_CRIME_FIXTURE_TODD)
        record.pop("id")
        event = crime.parse_socrata_row(record, city_id="santa_rosa")
        assert event is not None
        assert event.incident_id == "SD260827018"

    def test_row_without_any_id_is_dropped(self, crime, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: CRIME_FIELD_MAP,
        )
        record = dict(_CRIME_FIXTURE_TODD)
        record.pop("id")
        record.pop("incident_number")
        assert crime.parse_socrata_row(record, city_id="santa_rosa") is None

    def test_geometry_less_row_resolves_through_the_geocode_fallback(
        self, crime, monkeypatch
    ):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: CRIME_FIELD_MAP,
        )
        record = dict(_CRIME_FIXTURE_TODD)
        record.pop("location")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (38.4405, -122.7144),
        )
        event = crime.parse_socrata_row(record, city_id="santa_rosa")
        assert event is not None
        assert event.city_id == "santa_rosa"
        assert event.incident_id == "LW_DWInformRMS_89028FD7-FFB3-CC5B-96C8-08DF04BCF75F"
        assert event.latitude == pytest.approx(38.4405)
        assert event.longitude == pytest.approx(-122.7144)

    def test_geometry_less_row_dropped_when_geocode_fails(self, crime, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: CRIME_FIELD_MAP,
        )
        record = dict(_CRIME_FIXTURE_CARRIAGE)
        record.pop("location")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert crime.parse_socrata_row(record, city_id="santa_rosa") is None

    def test_borough_passes_through_as_city_name(self, crime, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: CRIME_FIELD_MAP,
        )
        event = crime.parse_socrata_row(_CRIME_FIXTURE_DUTTON, city_id="santa_rosa")
        assert event is not None
        assert event.source_neighborhood == "SANTA ROSA"

    def test_offense_classification_distinguishes_part1(self, crime, monkeypatch):
        for incident_type in ("Burglary", "Theft", "Robbery", "Assault", "Arson"):
            record = dict(_CRIME_FIXTURE_TODD)
            record["incident_type"] = incident_type
            monkeypatch.setattr(
                "src.producers.field_maps.resolve_field_map",
                lambda city, feed: CRIME_FIELD_MAP,
            )
            event = crime.parse_socrata_row(record, city_id="santa_rosa")
            assert event is not None
            assert event.offense_class == "PART1"


class TestSantaRosaFeedSpec:
    def test_crime_spec_matches_live_layer(self):
        spec = get_santa_rosa_dataset(FeedType.CRIME)
        assert spec.platform == "socrata"
        assert spec.endpoint == SANTA_ROSA_CRIME_ENDPOINT
        assert spec.watermark_col == "date_time"
        assert spec.id_keys == ["id", "incident_number"]
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "date_time DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.field_map == CRIME_FIELD_MAP
        assert spec.topic == "raw.municipal.crime"

    def test_registered_feed_set_is_crime_only(self):
        assert set(SANTA_ROSA_FEED_SPECS) == {"crime"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_santa_rosa_dataset("permits")
        assert "santa_rosa" in str(exc.value)
        assert "crime" in str(exc.value)

    def test_endpoint_is_the_probed_socrata_dataset(self):
        assert "data.sonomacounty.ca.gov" in SANTA_ROSA_CRIME_ENDPOINT
        assert "3rsj-iche" in SANTA_ROSA_CRIME_ENDPOINT