"""Unit tests for the Honolulu leaf (US-193): spatial module + field maps +
geocoding caveats.

These tests run with NO spine registration (no CityId.HONOLULU in the registry,
no ALIASES entry, no DatasetSpec). They exercise the leaf directly:

* spatial containment / submarket invariants (pure module imports),
* the per-city field map via the shared ``first_mapped`` mechanism,
* the ADR-0004 geocoding caveats that define this registration:
  - 311 `street` values carry no state token, so geocode_context
    "Honolulu, HI" must be appendable (`_STATE_RE` misses them),
  - concatenating the feed's full-word `state` ("Hawaii") would also miss
    `_STATE_RE` and double-append the context suffix,
  - unit-designator normalization preserves the HI city context.

The producer path is tested by monkeypatching the two registry-touching helpers
(``resolve_field_map`` and ``geocode_row_if_declared``) so the real shared
parsers run against the Honolulu field map without needing a registered spec.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_honolulu import FIELD_MAP, GEOCODE_CONTEXT
from src.spatial.cities.honolulu import (
    HONOLULU_311_FIELD_MAP,
    HONOLULU_DIVISION_BBOXES,
    HONOLULU_DIVISIONS,
    HONOLULU_METRO_BBOX,
    HONOLULU_PERMITS_FIELD_MAP,
    HONOLULU_SUBMARKETS,
    is_in_honolulu_metro,
)
from src.spatial.geocoder import _STATE_RE, normalize_address


# Live-probe fixtures captured 2026-08-27 from data.honolulu.gov.
_311_FIXTURE = {
    "id": "R2026-23200",
    "date_created": "August 26, 2026 at 11:52 PM",
    "request_type": "Restriping",
    "street": "1160 Kuala St",
    "city": "Pearl City",
    "state": "Hawaii",
    "zip_code": "96782",
    "status": "Received",
    "description": "3 of the 4 crosswalks at the intersection of Kuala Street "
    "and the driveways to Walmart are so faded.",
}

_PERMITS_FIXTURE = {
    "buildingpermitno": "924426",
    "issuedate": "2025-07-01T00:00:00.000",
    "createddate": "2025-06-02T10:00:00.000",
    "joblocation": "91-1001 KEAUNUI DR UNIT 154 Ewa Beach 96706",
    "address": "91-1001 KEAUNUI DR Ewa Beach 96706",
    "statusdescription": "Inspection(s) in Progress",
    "externalfilenum": "A2025-06-0027",
    "objectid": "139291880",
    "estimatedvalueofwork": "6000",
    "proposeduse": "SFD",
    "tmk": "91149022",
    "numunitsadd": "0",
    "occupancygroupassessed": "01 - Single Family",
    "commercialresidential": "Residential",
}


# ---------------------------------------------------------------------------
# Spatial invariants (no registry needed)
# ---------------------------------------------------------------------------

class TestHonoluluSpatial:
    def test_metro_contains_center(self):
        assert is_in_honolulu_metro(21.3069, -157.8583) is True  # Downtown
        assert is_in_honolulu_metro(21.2766, -157.8278) is True  # Waikiki
        assert is_in_honolulu_metro(21.5906, -158.1036) is True  # Haleiwa

    def test_metro_rejects_null_and_foreign(self):
        assert is_in_honolulu_metro(None, None) is False
        assert is_in_honolulu_metro(21.309, -157.858) is True
        assert is_in_honolulu_metro(37.7749, -122.4194) is False  # San Francisco
        assert is_in_honolulu_metro(19.707, -155.082) is False  # Hilo (Big Island)

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in HONOLULU_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= HONOLULU_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= HONOLULU_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= HONOLULU_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= HONOLULU_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in HONOLULU_SUBMARKETS.items():
            bbox = HONOLULU_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in HONOLULU_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(HONOLULU_SUBMARKETS)

    def test_submarkets_carry_honolulu_city_id(self):
        assert {m.city_id for m in HONOLULU_SUBMARKETS.values()} == {"honolulu"}

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in HONOLULU_DIVISIONS.items():
            bbox = HONOLULU_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name


# ---------------------------------------------------------------------------
# Field map mechanics (shared first_mapped against the leaf FIELD_MAP)
# ---------------------------------------------------------------------------

class TestHonoluluFieldMaps:
    def test_permits_map_reads_live_socrata_columns(self):
        row = _PERMITS_FIXTURE
        assert first_mapped(row, HONOLULU_PERMITS_FIELD_MAP, "job_id") == "924426"
        assert first_mapped(row, HONOLULU_PERMITS_FIELD_MAP, "issuance_date") == "2025-07-01T00:00:00.000"
        assert first_mapped(row, HONOLULU_PERMITS_FIELD_MAP, "address_street") == (
            "91-1001 KEAUNUI DR UNIT 154 Ewa Beach 96706"
        )
        assert first_mapped(row, HONOLULU_PERMITS_FIELD_MAP, "bbl") == "91149022"
        assert first_mapped(row, HONOLULU_PERMITS_FIELD_MAP, "cost") == "6000"

    def test_permits_job_id_falls_back_when_buildingpermitno_is_null(self):
        row = {"buildingpermitno": None, "externalfilenum": "A2025-06-0877", "objectid": "139859174"}
        assert first_mapped(row, HONOLULU_PERMITS_FIELD_MAP, "job_id") == "A2025-06-0877"

    def test_311_map_reads_live_socrata_columns(self):
        row = _311_FIXTURE
        assert first_mapped(row, HONOLULU_311_FIELD_MAP, "incident_id") == "R2026-23200"
        assert first_mapped(row, HONOLULU_311_FIELD_MAP, "complaint_type") == "Restriping"
        assert first_mapped(row, HONOLULU_311_FIELD_MAP, "created_date") == "August 26, 2026 at 11:52 PM"
        assert first_mapped(row, HONOLULU_311_FIELD_MAP, "incident_address") == "1160 Kuala St"
        assert first_mapped(row, HONOLULU_311_FIELD_MAP, "zipcode") == "96782"

    def test_311_map_does_not_pass_city_or_state_as_address(self):
        # Concatenating city+state would feed "Hawaii" to the geocoder, which
        # `_STATE_RE` does not treat as a state token — the context suffix
        # would then double-append. Street-only is the contract.
        assert HONOLULU_311_FIELD_MAP["incident_address"] == ["street"]
        assert first_mapped(_311_FIXTURE, HONOLULU_311_FIELD_MAP, "incident_address") == "1160 Kuala St"

    def test_map_is_the_exported_field_map(self):
        assert FIELD_MAP["permits"] is HONOLULU_PERMITS_FIELD_MAP
        assert FIELD_MAP["311"] is HONOLULU_311_FIELD_MAP

    def test_geocode_context_is_honolulu_hi(self):
        assert GEOCODE_CONTEXT == "Honolulu, HI"

    def test_311_has_no_coordinate_candidates(self):
        assert "latitude" not in HONOLULU_311_FIELD_MAP
        assert "longitude" not in HONOLULU_311_FIELD_MAP

    def test_permits_has_no_coordinate_candidates(self):
        assert "latitude" not in HONOLULU_PERMITS_FIELD_MAP
        assert "longitude" not in HONOLULU_PERMITS_FIELD_MAP


# ---------------------------------------------------------------------------
# Geocoding caveats (ADR 0004) — registry-free
# ---------------------------------------------------------------------------

class TestGeocodingCaveats:
    def test_street_only_has_no_state_token_so_context_appends(self):
        # 311 `street` is "1160 Kuala St" — no HI abbreviation, so the
        # geocoder will append geocode_context ("Honolulu, HI").
        assert _STATE_RE.search("1160 KUALA ST".upper()) is None

    def test_full_word_hawaii_is_not_a_state_token(self):
        # The feed's `state` column is "Hawaii", not "HI". Treating the
        # concatenated "1160 Kuala St, Pearl City, Hawaii" as already-stated
        # would skip the suffix and then (because Hawaii ≠ HI) still miss.
        assert _STATE_RE.search("1160 KUALA ST, PEARL CITY, HAWAII".upper()) is None
        assert _STATE_RE.search("1160 KUALA ST, HONOLULU, HI".upper()) is not None

    def test_permit_joblocation_has_no_hi_abbreviation(self):
        loc = "91-1001 KEAUNUI DR UNIT 154 Ewa Beach 96706"
        assert _STATE_RE.search(loc.upper()) is None

    def test_unit_designator_normalization_preserves_context(self):
        norm = normalize_address("91-1001 KEAUNUI DR UNIT 154, EWA BEACH, HI")
        assert "UNIT" not in norm
        assert "154" not in norm
        assert "EWA BEACH" in norm
        assert "HI" in norm

    def test_punctuation_and_house_number_preserved(self):
        norm = normalize_address("1160 Kuala St., Pearl City")
        assert norm == "1160 KUALA ST PEARL CITY"


# ---------------------------------------------------------------------------
# Producer path with the Honolulu field map injected (no spine registration)
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


def _patch_resolve_and_geocode(monkeypatch, feed_key, geocode_side_effect):
    """Wire a shared parser to the Honolulu leaf field map + a fake geocoder."""
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


class TestHonolulu311Parsing:
    def test_address_only_311_uses_declared_geocoder(self, complaints, monkeypatch):
        captured = _patch_resolve_and_geocode(monkeypatch, "311", (21.3972, -157.9731))
        event = complaints.parse_socrata_row(_311_FIXTURE, city_id="honolulu")
        assert event is not None
        assert event.incident_id == "R2026-23200"
        assert event.latitude == pytest.approx(21.3972)
        assert event.longitude == pytest.approx(-157.9731)
        assert event.h3_res7 is not None
        assert captured == [
            ("honolulu", "311", "1160 Kuala St", None)
        ]

    def test_311_row_without_street_is_dropped(self, complaints, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: FIELD_MAP["311"],
        )
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        row = {**_311_FIXTURE, "street": ""}
        assert complaints.parse_socrata_row(row, city_id="honolulu") is None


class TestHonoluluPermitParsing:
    def test_address_only_permit_uses_declared_geocoder(self, permits, monkeypatch):
        captured = _patch_resolve_and_geocode(monkeypatch, "permits", (21.3169, -158.0122))
        event = permits.parse_socrata_row(_PERMITS_FIXTURE, city_id="honolulu")
        assert event is not None
        assert event.job_id == "924426"
        assert event.latitude == pytest.approx(21.3169)
        assert event.issuance_date is not None
        assert captured == [
            (
                "honolulu",
                "permits",
                "91-1001 KEAUNUI DR UNIT 154 Ewa Beach 96706",
                None,
            )
        ]
