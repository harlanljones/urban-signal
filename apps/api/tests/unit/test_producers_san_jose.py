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
    def test_permits_map_spells_job_id_and_coords(self):
        row = {
            "PERMIT_NUMBER": "BP-2026-01234",
            "Y_COORD": "37.337",
            "X_COORD": "-121.886",
            "ADDRESS": "120 N MARKET ST",
        }
        assert first_mapped(row, SAN_JOSE_PERMITS_FIELD_MAP, "job_id") == "BP-2026-01234"
        assert first_mapped(row, SAN_JOSE_PERMITS_FIELD_MAP, "latitude") == "37.337"
        assert first_mapped(row, SAN_JOSE_PERMITS_FIELD_MAP, "longitude") == "-121.886"
        assert first_mapped(row, SAN_JOSE_PERMITS_FIELD_MAP, "address_street") == "120 N MARKET ST"

    def test_311_map_reads_request_id_not_service_request_id(self):
        row = {
            "SR_REQUEST_ID": "SJ-311-2026-55",
            "REQUEST_TYPE": "Graffiti",
            "Y_COORD": "37.33",
            "X_COORD": "-121.88",
            "ADDRESS": "1 W SAN CARLOS ST",
        }
        assert first_mapped(row, SAN_JOSE_311_FIELD_MAP, "incident_id") == "SJ-311-2026-55"
        assert first_mapped(row, SAN_JOSE_311_FIELD_MAP, "complaint_type") == "Graffiti"
        assert first_mapped(row, SAN_JOSE_311_FIELD_MAP, "incident_address") == "1 W SAN CARLOS ST"

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
            "SR_REQUEST_ID": "SJ-311-2026-55",
            "REQUEST_TYPE": "Graffiti",
            "STATUS": "OPEN",
            "CREATE_DATE": "2026-08-21T22:39:12.000",
            "ADDRESS": "1 W SAN CARLOS ST, SAN JOSE, CA",
            "Y_COORD": "37.3300",
            "X_COORD": "-121.8800",
        }
        event = complaints.parse_socrata_row(row, city_id="san_jose")
        assert event is not None
        assert event.incident_id == "SJ-311-2026-55"
        assert event.latitude == pytest.approx(37.33)
        assert event.longitude == pytest.approx(-121.88)
        assert event.h3_res7 is not None
        # Native coordinates were usable — the geocoder must NOT have been called.
        assert captured == []

    def test_address_only_row_geocodes_at_parse(self, complaints, monkeypatch):
        captured = _patch_resolve_and_geocode(monkeypatch, (37.3350, -121.8900))
        row = {
            "SR_REQUEST_ID": "SJ-311-2026-56",
            "REQUEST_TYPE": "Pothole",
            "STATUS": "OPEN",
            "CREATE_DATE": "2026-08-21T10:00:00.000",
            "ADDRESS": "200 E SANTA CLARA ST, SAN JOSE, CA",
            # no Y_COORD / X_COORD => address-only row
        }
        event = complaints.parse_socrata_row(row, city_id="san_jose")
        assert event is not None
        assert event.latitude == pytest.approx(37.3350)
        assert event.longitude == pytest.approx(-121.8900)
        assert event.h3_res7 is not None
        assert captured == [
            ("san_jose", "311", "200 E SANTA CLARA ST, SAN JOSE, CA", None)
        ]

    def test_out_of_range_projected_coords_geocode_instead(self, complaints, monkeypatch):
        captured = _patch_resolve_and_geocode(monkeypatch, (37.3410, -121.9010))
        # SanGIS sometimes emits state-plane feet in Y_COORD/X_COORD on legacy
        # rows; abs(lat)>90 / abs(lng)>180 must reject them as non-geographic.
        row = {
            "SR_REQUEST_ID": "SJ-311-2026-57",
            "REQUEST_TYPE": "Street Light Out",
            "STATUS": "OPEN",
            "CREATE_DATE": "2026-08-20T10:00:00.000",
            "ADDRESS": "50 N ALMADEN BLVD, SAN JOSE, CA",
            "Y_COORD": "4100000",
            "X_COORD": "1900000",
        }
        event = complaints.parse_socrata_row(row, city_id="san_jose")
        assert event is not None
        assert event.latitude == pytest.approx(37.3410)
        assert event.longitude == pytest.approx(-121.9010)
        assert event.h3_res7 is not None
        assert captured == [
            ("san_jose", "311", "50 N ALMADEN BLVD, SAN JOSE, CA", None)
        ]

    def test_geocode_failure_drops_the_row(self, complaints, monkeypatch):
        captured = _patch_resolve_and_geocode(monkeypatch, None)
        row = {
            "SR_REQUEST_ID": "SJ-311-2026-58",
            "REQUEST_TYPE": "Noise",
            "STATUS": "OPEN",
            "CREATE_DATE": "2026-08-20T10:00:00.000",
            "ADDRESS": "UNKNOWN AND VOID, SAN JOSE, CA",
        }
        assert complaints.parse_socrata_row(row, city_id="san_jose") is None
        assert captured  # geocoder was consulted at least once
