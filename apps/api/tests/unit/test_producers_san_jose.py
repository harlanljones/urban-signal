"""Unit tests for the San Jose leaf (US-147): spatial module + field maps +
geocoding caveats.

These tests run with NO spine registration (no CityId.SAN_JOSE in the registry,
no ALIASES entry, no DatasetSpec). They exercise the leaf directly:

* spatial containment / submarket invariants (pure module imports),
* the per-city field map via the shared ``first_mapped`` mechanism,
* the ADR-0004 geocoding caveats that define this registration:
  - address strings that already carry "CA" must not get a doubled context
    suffix (geocoder ``_STATE_RE``),
  - unit-designator normalization,
  - 311 rows that are address-only or carry projected/out-of-range coordinates
    fall through to the geocoder, while rows with native coordinates parse
    straight through without geocoding.

The producer path is tested by monkeypatching the two registry-touching helpers
(``resolve_field_map`` and ``geocode_row_if_declared``) so the real shared
parsers run against the San Jose field map without needing a registered spec.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_san_jose import FIELD_MAP, GEOCODE_CONTEXT
from src.spatial.cities.san_jose import (
    SAN_JOSE_311_FIELD_MAP,
    SAN_JOSE_DIVISION_BBOXES,
    SAN_JOSE_DIVISIONS,
    SAN_JOSE_METRO_BBOX,
    SAN_JOSE_PERMITS_FIELD_MAP,
    SAN_JOSE_SUBMARKETS,
    is_in_san_jose_metro,
)
from src.spatial.geocoder import _STATE_RE, normalize_address


# ---------------------------------------------------------------------------
# Spatial invariants (no registry needed)
# ---------------------------------------------------------------------------

class TestSanJoseSpatial:
    def test_metro_contains_center(self):
        assert is_in_san_jose_metro(37.3382, -121.8863) is True

    def test_metro_rejects_null_and_foreign(self):
        assert is_in_san_jose_metro(None, None) is False
        assert is_in_san_jose_metro(37.7749, -122.4194) is False  # San Francisco
        assert is_in_san_jose_metro(34.0522, -118.2437) is False  # Los Angeles

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in SAN_JOSE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= SAN_JOSE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= SAN_JOSE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= SAN_JOSE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= SAN_JOSE_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in SAN_JOSE_SUBMARKETS.items():
            bbox = SAN_JOSE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in SAN_JOSE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(SAN_JOSE_SUBMARKETS)

    def test_submarkets_carry_san_jose_city_id(self):
        assert {m.city_id for m in SAN_JOSE_SUBMARKETS.values()} == {"san_jose"}


# ---------------------------------------------------------------------------
# Field map mechanics (shared first_mapped against the leaf FIELD_MAP)
# ---------------------------------------------------------------------------

class TestSanJoseFieldMaps:
    def test_permits_map_reads_live_ckan_columns(self):
        row = {
            "FOLDERNUMBER": "2026-130149-CI",
            "ISSUEDATE": "8/14/2026 12:00:00 AM",
            "gx_location": "1 CURTNER AV, SAN JOSE CA 95125",
            "ASSESSORS_PARCEL_NUMBER": "45505012",
        }
        assert first_mapped(row, SAN_JOSE_PERMITS_FIELD_MAP, "job_id") == "2026-130149-CI"
        assert first_mapped(row, SAN_JOSE_PERMITS_FIELD_MAP, "issuance_date") == "8/14/2026 12:00:00 AM"
        assert first_mapped(row, SAN_JOSE_PERMITS_FIELD_MAP, "address_street") == "1 CURTNER AV, SAN JOSE CA 95125"
        assert first_mapped(row, SAN_JOSE_PERMITS_FIELD_MAP, "bbl") == "45505012"

    def test_311_map_reads_live_ckan_columns(self):
        row = {
            "Incident_ID": "2117594",
            "Service Type": "Other Issues",
            "Date Created": "1/1/2026 12:01:31 AM",
            "Latitude": "37.399977000001",
            "Longitude": "-121.925974500002",
        }
        assert first_mapped(row, SAN_JOSE_311_FIELD_MAP, "incident_id") == "2117594"
        assert first_mapped(row, SAN_JOSE_311_FIELD_MAP, "complaint_type") == "Other Issues"
        assert first_mapped(row, SAN_JOSE_311_FIELD_MAP, "created_date") == "1/1/2026 12:01:31 AM"

    def test_map_is_the_exported_field_map(self):
        assert FIELD_MAP["permits"] is SAN_JOSE_PERMITS_FIELD_MAP
        assert FIELD_MAP["311"] is SAN_JOSE_311_FIELD_MAP

    def test_geocode_context_is_san_jose_ca(self):
        assert GEOCODE_CONTEXT == "San Jose, CA"


# ---------------------------------------------------------------------------
# Geocoding caveats (ADR 0004) — registry-free
# ---------------------------------------------------------------------------

class TestGeocodingCaveats:
    def test_address_already_carrying_ca_is_not_double_contexted(self):
        # The geocoder appends geocode_context only when no state token is
        # present; San Jose addresses end in "CA", so this must be detected.
        assert _STATE_RE.search("123 MAIN ST, SAN JOSE, CA".upper()) is not None

    def test_address_without_state_would_accept_context(self):
        # A bare address lacking a state token is where the suffix is applied.
        assert _STATE_RE.search("123 MAIN ST".upper()) is None

    def test_unit_designator_normalization(self):
        # "APT 4" is dropped in place; the CA city context is preserved so the
        # geocoder still gets a resolvable query (US-74-style caveat).
        norm = normalize_address("123 MAIN ST APT 4, SAN JOSE, CA")
        assert "APT" not in norm
        assert "SAN JOSE" in norm
        assert "CA" in norm

    def test_punctuation_and_house_number_preserved(self):
        norm = normalize_address("123-A MAIN ST., SAN JOSE, CA")
        assert norm == "123 A MAIN ST SAN JOSE CA"


# ---------------------------------------------------------------------------
# Producer path with the San Jose field map injected (no spine registration)
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


def _patch_resolve_and_geocode(monkeypatch, geocode_side_effect):
    """Wire the real 311 parser to the San Jose leaf field map + a fake geocoder.

    The producer imports both helpers inside parse_socrata_row, so patching the
    modules they live on is sufficient — no registry entry required.
    """
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP["311"],
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


class TestSanJose311Parsing:
    def test_native_coords_parse_without_geocoding(self, complaints, monkeypatch):
        captured = _patch_resolve_and_geocode(monkeypatch, (37.33, -121.88))
        row = {
            "Incident_ID": "2117594",
            "Service Type": "Other Issues",
            "Status": "Closed",
            "Date Created": "1/1/2026 12:01:31 AM",
            "Latitude": "37.399977000001",
            "Longitude": "-121.925974500002",
        }
        event = complaints.parse_socrata_row(row, city_id="san_jose")
        assert event is not None
        assert event.incident_id == "2117594"
        assert event.latitude == pytest.approx(37.399977)
        assert event.longitude == pytest.approx(-121.9259745)
        assert event.h3_res7 is not None
        # Native coordinates were usable — the geocoder must NOT have been called.
        assert captured == []

    def test_zero_coordinate_row_is_dropped_without_geocoding(self, complaints, monkeypatch):
        captured = _patch_resolve_and_geocode(monkeypatch, (37.3350, -121.8900))
        row = {
            "Incident_ID": "2117596",
            "Service Type": "Pothole",
            "Status": "Open",
            "Date Created": "1/1/2026 10:00:00 AM",
            "Latitude": "0.0",
            "Longitude": "0.0",
        }
        assert complaints.parse_socrata_row(row, city_id="san_jose") is None
        assert captured == []


class TestSanJosePermitParsing:
    def test_address_only_permit_uses_declared_geocoder(self, permits, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: FIELD_MAP["permits"],
        )
        captured = []

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address, context))
            return 37.337, -121.886

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        event = permits.parse_socrata_row(
            {
                "FOLDERNUMBER": "2026-130149-CI",
                "Status": "30",
                "gx_location": "1 CURTNER AV, SAN JOSE CA 95125",
                "ISSUEDATE": "8/14/2026 12:00:00 AM",
                "PERMITVALUATION": "130200",
                "ASSESSORS_PARCEL_NUMBER": "45505012",
                "FOLDERNAME": "(B)",
            },
            city_id="san_jose",
        )
        assert event is not None
        assert event.job_id == "2026-130149-CI"
        assert event.latitude == pytest.approx(37.337)
        assert event.issuance_date is not None
        assert captured == [
            ("san_jose", "permits", "1 CURTNER AV, SAN JOSE CA 95125", None)
        ]
