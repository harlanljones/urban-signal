"""Leaf tests for Boston's Licensing Board SLA feed (US-137).

Boston's Licensing Board source (CKAN 04dc653b-...) carries gpsx/gpsy in
Massachusetts State Plane meters (EPSG:26986) and no WGS84 columns. This feed
is registered as an address-only SLA feed (ADR 0004): gpsx/gpsy are never mapped
to latitude/longitude, and the business address string is geocoded at parse
time. These tests pass WITHOUT the spine registration (no REGISTRY SLA entry),
proving the field map and the ADR-0004 geocode path before the orchestrator
applies the interlock.

Column spellings are PROPOSED (pinned below) pending a live CKAN probe.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.producers.field_maps_boston_licensing import FIELD_MAP
from src.spatial.cities.boston import (
    BOSTON_DIVISION_BBOXES,
    BOSTON_DIVISIONS,
    BOSTON_LICENSING_BOARD_FEED,
    BOSTON_METRO_BBOX,
    BOSTON_SUBMARKETS,
    is_in_boston_metro,
)

BOSTON_LICENSING_FIELD_MAP = {
    "license_id": ["license_id", "licenseno", "license_number"],
    "license_type": ["licensetype", "license_type", "licensecategory"],
    "effective_date": ["licensetype_effective_date", "license_effective_date", "effectivedate"],
    "expiration_date": [
        "licensetype_expiration_date",
        "license_expiration_date",
        "expirationdate",
    ],
    "address_street": ["business_address", "location_address", "address"],
    "dba": ["dba", "doing_business_as", "business_name"],
    "premises_name": ["business_name", "premises_name", "entity_name"],
    "status": ["license_status", "status", "licensestatus"],
    "borough": ["ward", "neighborhood"],
}

# A representative Licensing Board row. gpsx/gpsy are MA State Plane METERS
# (Boston ~ easting 780000, northing 2950000) — clearly not WGS84 degrees.
BOSTON_LICENSING_ROW = {
    "license_id": "LIC-2026-0048217",
    "licensetype": "Common Victualler",
    "licensetype_effective_date": "2026-03-01",
    "licensetype_expiration_date": "2027-02-28",
    "business_name": "Harlan Square Diner LLC",
    "dba": "HARLAN SQUARE DINER",
    "business_address": "123 MAIN ST, BOSTON, MA 02118",
    "ward": "9",
    "license_status": "Active",
    # State Plane meters — must NOT surface as WGS84 degrees.
    "gpsx": 780421.36,
    "gpsy": 2950117.88,
}


def test_boston_geometry_is_self_consistent():
    assert is_in_boston_metro(42.355, -71.055)
    assert not is_in_boston_metro(40.7128, -74.0060)
    assert not is_in_boston_metro(None, None)
    for name, bbox in BOSTON_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= BOSTON_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= BOSTON_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= BOSTON_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= BOSTON_METRO_BBOX["max_lng"], name
    claimed = [n for d in BOSTON_DIVISIONS.values() for n in d.submarkets]
    assert sorted(claimed) == sorted(BOSTON_SUBMARKETS)
    assert {m.city_id for m in BOSTON_SUBMARKETS.values()} == {"boston"}


def test_feed_spec_is_address_only_ckan_resource():
    spec = BOSTON_LICENSING_BOARD_FEED
    assert spec["platform"] == "ckan"
    assert spec["feed_type"] == "sla"
    assert spec["dataset_id"] == "04dc653b-1789-4374-9669-b07df7233344"
    assert spec["needs_geocode"] is True
    # State Plane columns must NOT be wired to WGS84 latitude/longitude.
    assert "gpsx" not in FIELD_MAP.get("longitude", [])
    assert "gpsy" not in FIELD_MAP.get("latitude", [])
    assert "latitude" not in FIELD_MAP
    assert "longitude" not in FIELD_MAP


def test_field_map_matches_pinned_proposal():
    assert FIELD_MAP == BOSTON_LICENSING_FIELD_MAP
    # The address column the producer geocodes must be mapped.
    assert "business_address" in FIELD_MAP["address_street"]


@pytest.fixture
def sla_producer():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        return SLALicensesProducer()


def _geocode_row_if_declared(city_id, feed_value, address, context=None):
    """Stand-in for the ADR 0004 geocoder: returns a deterministic WGS84 point
    for the Boston licensing address, proving the address-only path resolves
    real coordinates without touching the State Plane gpsx/gpsy columns."""
    if city_id == "boston" and feed_value == "sla" and address:
        return (42.3368, -71.0721)
    return None


def test_licensing_row_geocodes_address_only_via_adr0004(sla_producer):
    with (
        patch(
            "src.producers.field_maps.resolve_field_map",
            lambda city_value, feed: FIELD_MAP if (city_value == "boston" and feed.value == "sla") else {},
        ),
        patch(
            "src.spatial.geocoder.geocode_row_if_declared",
            _geocode_row_if_declared,
        ),
    ):
        event = sla_producer.parse_socrata_row(BOSTON_LICENSING_ROW, city_id="boston")

    assert event is not None
    assert event.city_id == "boston"
    assert event.license_id == "LIC-2026-0048217"
    assert event.license_type == "Common Victualler"
    assert event.dba == "HARLAN SQUARE DINER"
    assert event.premises_name == "Harlan Square Diner LLC"
    assert event.address == "123 MAIN ST, BOSTON, MA 02118"
    assert event.license_status == "Active"
    # Coordinates came from the geocoder, NOT the State Plane gpsx/gpsy.
    assert event.latitude == pytest.approx(42.3368)
    assert event.longitude == pytest.approx(-71.0721)
    assert event.latitude != pytest.approx(780421.36)
    assert event.longitude != pytest.approx(2950117.88)
    assert event.h3_res7 is not None


def test_state_plane_columns_are_never_used_as_wgs84(sla_producer):
    """Guard: even if a row somehow also carried `latitude`/`longitude` shaped
    like the State Plane values, the field map must not route gpsx/gpsy into
    WGS84 — the producer falls through to geocoding instead."""
    with (
        patch(
            "src.producers.field_maps.resolve_field_map",
            lambda city_value, feed: FIELD_MAP if (city_value == "boston" and feed.value == "sla") else {},
        ),
        patch(
            "src.spatial.geocoder.geocode_row_if_declared",
            _geocode_row_if_declared,
        ),
    ):
        event = sla_producer.parse_socrata_row(BOSTON_LICENSING_ROW, city_id="boston")
    assert event is not None
    # Explicitly assert the event never inherits the meter-scale numbers.
    assert not (750000 < (event.latitude or 0) < 850000)
    assert not (2900000 < (event.longitude or 0) < 3000000)
