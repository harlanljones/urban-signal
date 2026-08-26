"""Contract tests for Boise's residential-only ArcGIS PERMITS feed.

Boise ships Idaho Transverse Mercator (EPSG:3694) state-plane geometry in the
`SHAPE__X`/`SHAPE__Y` columns. Those are NOT geographic degrees: the shared
producer's `abs(lat) > 90 / abs(lng) > 180` guard drops them and the ADR-0004
geocoder resolves the permit's street address. These tests run WITHOUT a spine
registration (no REGISTRY / ALIASES / __init__ entry) — the field map is patched
in directly, so the leaf is verifiable on its own.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.producers.field_maps_boise import FIELD_MAP as BOISE_PERMITS_FIELD_MAP
from src.spatial.cities.boise import (
    BOISE_DIVISION_BBOXES,
    BOISE_DIVISIONS,
    BOISE_METRO_BBOX,
    BOISE_SUBMARKETS,
    is_in_boise_metro,
)
from src.producers.field_maps import first_mapped
from src.spatial.city_registry import FeedType


# --- Geometry self-consistency (no spine registration required) --------------

def test_boise_geometry_is_self_consistent():
    assert is_in_boise_metro(43.6131, -116.2110)
    assert not is_in_boise_metro(40.7128, -74.0060)
    assert not is_in_boise_metro(None, None)
    for name, bbox in BOISE_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= BOISE_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= BOISE_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= BOISE_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= BOISE_METRO_BBOX["max_lng"], name
    claimed = [name for division in BOISE_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(BOISE_SUBMARKETS)
    assert {m.city_id for m in BOISE_SUBMARKETS.values()} == {"boise"}


# --- field_map round-trips through first_mapped -------------------------------

def test_boise_field_map_resolves_spellings():
    row = {
        "PERMITNUMBER": "BLD-2026-004512",
        "PERMITTYPE": "Residential",
        "ISSUEDATE": "2026-08-20T00:00:00.000Z",
        "ESTIMATEDCOST": "245000",
        "STATUS": "Issued",
        "SITE_ADDRESS": "1204 W Franklin St",
        "SHAPE__X": 563210.0,   # EPSG:3694 state-plane easting (NOT a degree)
        "SHAPE__Y": 1314520.0,  # EPSG:3694 state-plane northing (NOT a degree)
    }
    assert first_mapped(row, BOISE_PERMITS_FIELD_MAP, "job_id") == "BLD-2026-004512"
    assert first_mapped(row, BOISE_PERMITS_FIELD_MAP, "job_type") == "Residential"
    assert first_mapped(row, BOISE_PERMITS_FIELD_MAP, "cost") == "245000"
    assert first_mapped(row, BOISE_PERMITS_FIELD_MAP, "address_street") == "1204 W Franklin St"
    # The state-plane columns are exposed through the latitude/longitude slots...
    assert first_mapped(row, BOISE_PERMITS_FIELD_MAP, "latitude") == 1314520.0
    assert first_mapped(row, BOISE_PERMITS_FIELD_MAP, "longitude") == 563210.0


# --- Producer integration: state-plane coords are dropped, address geocoded ---

@pytest.fixture
def permits_producer():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        yield DOBPermitsProducer()


# Geocoder returns genuine Boise degrees, never the state-plane values.
_GEOCODED = SimpleNamespace(lat=43.6131, lon=-116.2110)


from contextlib import contextmanager


@contextmanager
def _patch_resolution():
    with (
        patch(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: BOISE_PERMITS_FIELD_MAP if (city == "boise" and feed == FeedType.PERMITS) else {},
        ),
        patch(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *a, **k: (_GEOCODED.lat, _GEOCODED.lon),
        ),
    ):
        yield


def test_boise_permit_drops_state_plane_and_geocodes_address(permits_producer):
    row = {
        "OBJECTID": 88123,
        "PERMITNUMBER": "BLD-2026-004512",
        "PERMITTYPE": "Residential",
        "ISSUEDATE": "2026-08-20T00:00:00.000Z",
        "ESTIMATEDCOST": "245000",
        "STATUS": "Issued",
        "SITE_ADDRESS": "1204 W Franklin St, Boise, ID",
        # State-plane geometry that must NOT be emitted as lat/lng.
        "SHAPE__X": 563210.0,
        "SHAPE__Y": 1314520.0,
    }
    with _patch_resolution():
        event = permits_producer.parse_socrata_row(row, city_id="boise")
    assert event is not None
    assert event.city_id == "boise"
    assert event.job_id == "BLD-2026-004512"
    assert event.address_street == "1204 W Franklin St, Boise, ID"
    # Coordinates are the geocoded address, NOT the state-plane northing/easting.
    assert event.latitude == pytest.approx(43.6131)
    assert event.longitude == pytest.approx(-116.2110)
    assert event.latitude != 1314520.0
    assert event.longitude != 563210.0
    assert event.issuance_date is not None


def test_boise_permit_without_address_is_dropped(permits_producer):
    row = {
        "OBJECTID": 88124,
        "PERMITNUMBER": "BLD-2026-004513",
        "PERMITTYPE": "Residential",
        "ISSUEDATE": "2026-08-20T00:00:00.000Z",
        "ESTIMATEDCOST": "120000",
        # No SITE_ADDRESS; state-plane geometry must be dropped and there is no
        # address to geocode, so the row has no coordinate and must be skipped.
        "SHAPE__X": 563210.0,
        "SHAPE__Y": 1314520.0,
    }
    with _patch_resolution():
        with patch(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *a, **k: None,
        ):
            event = permits_producer.parse_socrata_row(row, city_id="boise")
    assert event is None
