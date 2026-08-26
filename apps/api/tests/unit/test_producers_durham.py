"""Contract tests for Durham's PERMITS + DEEDS ArcGIS feeds (US-154).

Durham ships two live ArcGIS layers on ``webgis2.durhamnc.gov``:

* PERMITS — ``Inspections/MapServer/12`` "All Building Permits", an
  ``esriGeometryPoint`` layer whose geometry the ArcGISClient lifts to
  ``latitude``/``longitude``.
* DEEDS — ``Property/MapServer/4`` "Parcels", an ``esriGeometryPolygon`` layer
  whose centroid the ArcGISClient lifts to ``latitude``/``longitude``. The
  assessor parcel table has no grantor/grantee split.

These tests run WITHOUT a spine registration (no REGISTRY / ALIASES /
``__init__`` entry) — the field map is patched in directly, so the leaf is
verifiable on its own. Coordinates are supplied inline to simulate the
ArcGISClient geometry lift; the field map deliberately does NOT bind
latitude/longitude.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps_durham import FIELD_MAP as DURHAM_FIELD_MAP
from src.producers.field_maps import first_mapped
from src.spatial.cities.durham import (
    DURHAM_DEEDS_SPEC,
    DURHAM_DIVISION_BBOXES,
    DURHAM_DIVISIONS,
    DURHAM_METRO_BBOX,
    DURHAM_PERMITS_SPEC,
    DURHAM_SUBMARKETS,
    is_in_durham_metro,
)
from src.spatial.city_registry import FeedType


# --- Geometry self-consistency (no spine registration required) --------------

def test_durham_geometry_is_self_consistent():
    assert is_in_durham_metro(35.9940, -78.8986)   # downtown
    assert is_in_durham_metro(35.9970, -78.9390)   # Duke West Campus
    assert is_in_durham_metro(35.9050, -78.9050)   # Southpoint
    assert not is_in_durham_metro(40.7128, -74.0060)  # NYC
    assert not is_in_durham_metro(35.7796, -78.6382)  # Raleigh
    assert not is_in_durham_metro(None, None)
    for name, bbox in DURHAM_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= DURHAM_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= DURHAM_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= DURHAM_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= DURHAM_METRO_BBOX["max_lng"], name
    claimed = [name for division in DURHAM_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(DURHAM_SUBMARKETS)
    assert {m.city_id for m in DURHAM_SUBMARKETS.values()} == {"durham"}


def test_every_submarket_sits_inside_its_own_division():
    for name, meta in DURHAM_SUBMARKETS.items():
        bbox = DURHAM_DIVISION_BBOXES[meta.borough]
        assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
        assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name


# --- Spec payloads embed the per-city field map -----------------------------

def test_permits_spec_embeds_field_map():
    assert DURHAM_PERMITS_SPEC["platform"] == "arcgis"
    assert DURHAM_PERMITS_SPEC["watermark_col"] == "ISSUE_DATE"
    assert DURHAM_PERMITS_SPEC["extra"]["field_map"] is DURHAM_FIELD_MAP["permits"]
    assert DURHAM_PERMITS_SPEC["extra"]["oid_field"] == "OBJECTID"


def test_deeds_spec_embeds_field_map():
    assert DURHAM_DEEDS_SPEC["platform"] == "arcgis"
    assert DURHAM_DEEDS_SPEC["watermark_col"] == "DEED_DATE"
    assert DURHAM_DEEDS_SPEC["extra"]["field_map"] is DURHAM_FIELD_MAP["deeds"]
    assert DURHAM_DEEDS_SPEC["extra"]["oid_field"] == "OBJECTID_1"


# --- field_map round-trips through first_mapped -----------------------------

def test_permits_field_map_resolves_spellings():
    row = {
        "PermitNum": "BLD-2026-009876",
        "ISSUE_DATE": "2026-08-20T00:00:00.000Z",
        "BLD_Cost": "245000",
        "BLDB_ACTIVITY": "New",
        "PmtStatus": "Issued",
        "PROJECT_NAME": "West Village Mixed Use",
        "PIN": "0930509034",
        "OBJECTID": 88123,
        "latitude": 35.9940,
        "longitude": -78.8986,
    }
    assert first_mapped(row, DURHAM_FIELD_MAP["permits"], "job_id") == "BLD-2026-009876"
    assert first_mapped(row, DURHAM_FIELD_MAP["permits"], "cost") == "245000"
    assert first_mapped(row, DURHAM_FIELD_MAP["permits"], "job_type") == "New"
    assert first_mapped(row, DURHAM_FIELD_MAP["permits"], "issuance_date") == "2026-08-20T00:00:00.000Z"
    assert first_mapped(row, DURHAM_FIELD_MAP["permits"], "status") == "Issued"


def test_deeds_field_map_resolves_spellings():
    row = {
        "REID": "2026-0001234",
        "DEED_DATE": "2026-07-15T00:00:00.000Z",
        "PKG_SALE_PRICE": "450000",
        "LAND_CLASS": "Residential",
        "NEIGHBORHOOD": "Trinity Park",
        "PROPERTY_OWNER": "DEMO HOLDINGS LLC",
        "PIN": "0930509034",
        "OBJECTID_1": 55123,
        "latitude": 35.9990,
        "longitude": -78.9180,
    }
    assert first_mapped(row, DURHAM_FIELD_MAP["deeds"], "doc_id") == "2026-0001234"
    assert first_mapped(row, DURHAM_FIELD_MAP["deeds"], "recorded_date") == "2026-07-15T00:00:00.000Z"
    assert first_mapped(row, DURHAM_FIELD_MAP["deeds"], "document_amount") == "450000"
    assert first_mapped(row, DURHAM_FIELD_MAP["deeds"], "borough") == "Trinity Park"
    assert first_mapped(row, DURHAM_FIELD_MAP["deeds"], "party1_grantor") == "DEMO HOLDINGS LLC"


# --- Producer integration: permits -----------------------------------------

@pytest.fixture
def permits_producer():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        yield DOBPermitsProducer()


@pytest.fixture
def deeds_producer():
    with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
        from src.producers.deeds_acris_producer import DeedsACRISProducer

        yield DeedsACRISProducer()


def _patch_field_map():
    return patch(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: (
            DURHAM_FIELD_MAP["permits"]
            if (city == "durham" and feed == FeedType.PERMITS)
            else DURHAM_FIELD_MAP["deeds"]
            if (city == "durham" and feed == FeedType.DEEDS)
            else {}
        ),
    )


def test_durham_permit_parses_with_field_map(permits_producer):
    row = {
        "OBJECTID": 88123,
        "PermitNum": "BLD-2026-009876",
        "ISSUE_DATE": "2026-08-20T00:00:00.000Z",
        "BLD_Cost": "245000",
        "BLDB_ACTIVITY": "New",
        "PmtStatus": "Issued",
        "PROJECT_NAME": "West Village Mixed Use",
        "PIN": "0930509034",
        # Simulated ArcGIS Point geometry lift.
        "latitude": 35.9940,
        "longitude": -78.8986,
    }
    with _patch_field_map():
        event = permits_producer.parse_socrata_row(row, city_id="durham")
    assert event is not None
    assert event.city_id == "durham"
    assert event.job_id == "BLD-2026-009876"
    assert event.estimated_cost == 245000.0
    assert event.latitude == pytest.approx(35.9940)
    assert event.longitude == pytest.approx(-78.8986)
    assert str(event.issuance_date).startswith("2026-08-20")
    assert event.status == "Issued"


def test_durham_permit_without_coordinates_is_dropped(permits_producer):
    row = {
        "OBJECTID": 88124,
        "PermitNum": "BLD-2026-009877",
        "ISSUE_DATE": "2026-08-20T00:00:00.000Z",
        "BLD_Cost": "120000",
        "BLDB_ACTIVITY": "Alterations",
        # No latitude/longitude and no address -> no coordinate -> dropped.
    }
    with _patch_field_map():
        event = permits_producer.parse_socrata_row(row, city_id="durham")
    assert event is None


# --- Producer integration: deeds -------------------------------------------

def test_durham_deed_parses_with_field_map(deeds_producer):
    row = {
        "OBJECTID_1": 55123,
        "REID": "2026-0001234",
        "DEED_DATE": "2026-07-15T00:00:00.000Z",
        "PKG_SALE_PRICE": "450000",
        "LAND_CLASS": "Residential",
        "NEIGHBORHOOD": "Trinity Park",
        "PROPERTY_OWNER": "DEMO HOLDINGS LLC",
        "PIN": "0930509034",
        # Simulated ArcGIS Polygon centroid lift.
        "latitude": 35.9990,
        "longitude": -78.9180,
    }
    with _patch_field_map():
        event = deeds_producer.parse_socrata_row(row, city_id="durham")
    assert event is not None
    assert event.city_id == "durham"
    assert event.doc_id == "2026-0001234"
    assert event.document_amount == 450000.0
    assert str(event.recorded_date).startswith("2026-07-15")
    assert event.latitude == pytest.approx(35.9990)
    assert event.longitude == pytest.approx(-78.9180)


def test_durham_deed_without_coordinates_is_dropped(deeds_producer):
    row = {
        "OBJECTID_1": 55124,
        "REID": "2026-0001235",
        "DEED_DATE": "2026-07-15T00:00:00.000Z",
        "PKG_SALE_PRICE": "300000",
        # No latitude/longitude on the wire and no centroid lift -> null coords.
        # DeedEvent tolerates null coords (Cook County / Norfolk precedent), so
        # this still parses; assert it does NOT raise and coords are None.
    }
    with _patch_field_map():
        event = deeds_producer.parse_socrata_row(row, city_id="durham")
    assert event is not None
    assert event.latitude is None
    assert event.longitude is None
