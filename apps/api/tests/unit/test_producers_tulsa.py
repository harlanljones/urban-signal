"""Contract tests for Tulsa's rolling-window 311 ArcGIS feed."""

from unittest.mock import patch

import pytest

from src.spatial.cities.tulsa import (
    TULSA_DIVISION_BBOXES,
    TULSA_DIVISIONS,
    TULSA_METRO_BBOX,
    TULSA_SUBMARKETS,
    is_in_tulsa_metro,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType, get_dataset, normalize_city

TULSA_FIELD_MAP = {
    "incident_id": ["case_id", "OBJECTID"],
    "created_date": ["case_opened"],
    "closed_date": ["case_closed"],
    "status": ["case_status"],
    "complaint_type": ["case_type", "case_reason", "case_subject"],
    "incident_address": ["case_external_ref"],
}


def test_tulsa_geometry_is_self_consistent():
    assert is_in_tulsa_metro(36.1540, -95.9928)
    assert is_in_tulsa_metro(36.2293, -95.9679)
    assert not is_in_tulsa_metro(40.7128, -74.0060)
    assert not is_in_tulsa_metro(None, None)
    for name, bbox in TULSA_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= TULSA_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= TULSA_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= TULSA_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= TULSA_METRO_BBOX["max_lng"], name
    claimed = [name for division in TULSA_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(TULSA_SUBMARKETS)
    assert {meta.city_id for meta in TULSA_SUBMARKETS.values()} == {"tulsa"}


def test_tulsa_registers_rolling_311_and_crime():
    city = CityId.TULSA
    assert normalize_city("tulsa ok") is city
    assert normalize_city("tulsa county") is city
    assert set(REGISTRY[city].datasets) == {
        FeedType.COMPLAINTS_311,
        FeedType.CRIME,
        FeedType.SLA,
    }
    complaints = get_dataset(city, FeedType.COMPLAINTS_311)
    assert complaints.platform == "arcgis"
    assert complaints.watermark_col == "case_opened"
    assert complaints.id_keys == ["case_id", "OBJECTID"]
    assert complaints.rolling_window_days == 30
    assert complaints.retention_days == 30
    assert complaints.field_map == TULSA_FIELD_MAP
    for feed in (FeedType.PERMITS, FeedType.DEEDS):
        with pytest.raises(KeyError, match="no.*feed"):
            get_dataset(city, feed)


@pytest.fixture
def producer():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        from src.producers.complaints_311_producer import Complaints311Producer

        yield Complaints311Producer()


def test_tulsa_live_shaped_row_parses(producer):
    row = {
        "OBJECTID": 1002981,
        "case_id": "101000312317",
        "case_reason": "Solid Waste Services",
        "case_type": "Dead Animal Pickup",
        "case_status": "open",
        "case_opened": "2026-08-26T18:35:15+00:00",
        "case_closed": None,
        "case_external_ref": "",
        "latitude": 36.229289656449289,
        "longitude": -95.967880807413138,
    }
    event = producer.parse_socrata_row(row, city_id="tulsa")
    assert event is not None
    assert event.city_id == "tulsa"
    assert event.incident_id == "101000312317"
    assert event.complaint_type == "Dead Animal Pickup"
    assert event.status == "open"
    assert event.latitude == pytest.approx(36.229289656449289)
    assert event.longitude == pytest.approx(-95.967880807413138)
