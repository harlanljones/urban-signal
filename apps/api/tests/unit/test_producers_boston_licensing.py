"""Leaf tests for Boston's Licensing Board SLA feed (US-137).

Boston's Licensing Board source (CKAN 04dc653b-...) carries gpsx/gpsy in
Massachusetts State Plane US survey feet (EPSG:2249) and no WGS84 columns. Path A
transforms those coordinates to WGS84 in the SLA producer.

Column spellings are pinned below against the live CKAN schema.
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
    "license_id": ["license_num"],
    "license_type": ["license_type", "license_category"],
    "effective_date": ["issued"],
    "expiration_date": ["expires"],
    "address_street": ["address"],
    "dba": ["dba_name", "business_name"],
    "premises_name": ["business_name", "dba_name"],
    "status": ["status"],
    "borough": ["city"],
}

# A representative Licensing Board row. gpsx/gpsy are MA State Plane METERS
# (Boston ~ easting 780000, northing 2950000) — clearly not WGS84 degrees.
BOSTON_LICENSING_ROW = {
    "license_num": "LB-578141",
    "license_type": "CV7 Malt Wine Liq by Zip Restricted",
    "issued": None,
    "expires": "2025-12-31",
    "business_name": "Dominican Kitchen, Inc.",
    "dba_name": "La Parada Dominican Kitchen",
    "address": "3094-  Washington ST",
    "city": "Roxbury",
    "status": "Active",
# State Plane US survey feet — must be transformed to WGS84 degrees.
    "gpsx": 764720.2549378872,
    "gpsy": 2940110.4333568066,
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


def test_feed_spec_declares_state_plane_transform():
    spec = BOSTON_LICENSING_BOARD_FEED
    assert spec["platform"] == "ckan"
    assert spec["feed_type"] == "sla"
    assert spec["dataset_id"] == "04dc653b-1789-4374-9669-b07df7233344"
    assert spec["state_plane_crs"] == "EPSG:2249"
    assert spec["state_plane_units"] == "US survey feet"


def test_field_map_matches_pinned_proposal():
    assert FIELD_MAP == BOSTON_LICENSING_FIELD_MAP
    assert "address" in FIELD_MAP["address_street"]


@pytest.fixture
def sla_producer():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        return SLALicensesProducer()


def test_licensing_row_transforms_state_plane_coordinates(sla_producer):
    with patch(
        "src.producers.field_maps.resolve_field_map",
        lambda city_value, feed: FIELD_MAP if (city_value == "boston" and feed.value == "sla") else {},
    ):
        event = sla_producer.parse_socrata_row(BOSTON_LICENSING_ROW, city_id="boston")

    assert event is not None
    assert event.city_id == "boston"
    assert event.license_id == "LB-578141"
    assert event.license_type == "CV7 Malt Wine Liq by Zip Restricted"
    assert event.dba == "La Parada Dominican Kitchen"
    assert event.premises_name == "Dominican Kitchen, Inc."
    assert event.address == "3094-  Washington ST"
    assert event.license_status == "Active"
    assert event.latitude == pytest.approx(42.3151, abs=0.001)
    assert event.longitude == pytest.approx(-71.0986, abs=0.001)
    assert event.latitude != pytest.approx(2940110.4333568066)
    assert event.longitude != pytest.approx(764720.2549378872)
    assert event.h3_res7 is not None


def test_state_plane_columns_are_transformed_not_emitted_as_meters(sla_producer):
    with patch(
        "src.producers.field_maps.resolve_field_map",
        lambda city_value, feed: FIELD_MAP if (city_value == "boston" and feed.value == "sla") else {},
    ):
        event = sla_producer.parse_socrata_row(BOSTON_LICENSING_ROW, city_id="boston")
    assert event is not None
    # Explicitly assert the event never inherits the meter-scale numbers.
    assert not (750000 < (event.latitude or 0) < 850000)
    assert not (2900000 < (event.longitude or 0) < 3000000)
