"""Contract tests for Houston, TX (ArcGIS 311 service requests)."""

from unittest.mock import patch

import pytest

from src.spatial.cities.houston import (
    HOUSTON_DIVISION_BBOXES,
    HOUSTON_DIVISIONS,
    HOUSTON_METRO_BBOX,
    HOUSTON_SUBMARKETS,
    is_in_houston_metro,
)
from src.spatial.city_registry import CityId, FeedType

# US-140. Every entry spells an uppercase column the shared producer fallback
# chains cannot reach; latitude/longitude map to the feed's native doubles
# (point geometry is also lifted onto latitude/longitude by ArcGISClient, but
# the native columns are authoritative).
HOUSTON_FIELD_MAP = {
    "incident_id": ["CASE_NUMBER"],
    "latitude": ["LATITUDE"],
    "longitude": ["LONGITUDE"],
    "complaint_type": ["CASE_TYPE"],
    "created_date": ["CREATED_ON"],
    "closed_date": ["CLOSED_ON"],
    "status": ["STATUS"],
    "incident_address": ["ADDRESS", "STREET"],
    "zipcode": ["ZIP"],
    "borough": ["SUPERNEIGHBORHOOD", "COUNCIL_DISTRICT"],
}


def test_houston_geometry_is_self_consistent():
    assert is_in_houston_metro(29.7604, -95.3698)  # Downtown center
    assert is_in_houston_metro(29.60919, -95.25369)  # observed live-row
    assert not is_in_houston_metro(30.2672, -97.7431)  # Austin, outside the county
    assert not is_in_houston_metro(None, None)
    for name, bbox in HOUSTON_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= HOUSTON_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= HOUSTON_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= HOUSTON_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= HOUSTON_METRO_BBOX["max_lng"], name
    claimed = [name for division in HOUSTON_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(HOUSTON_SUBMARKETS)
    assert {meta.city_id for meta in HOUSTON_SUBMARKETS.values()} == {"houston"}


def test_houston_registers_arcgis_311_only():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.HOUSTON
    assert normalize_city("houston") is city
    assert normalize_city("houston_tx") is city
    assert normalize_city("htx") is city
    assert REGISTRY[city].job_suffix == "houston"
    assert set(REGISTRY[city].datasets) == {FeedType.COMPLAINTS_311}

    s311 = REGISTRY[city].datasets[FeedType.COMPLAINTS_311]
    assert s311.platform == "arcgis"
    assert s311.watermark_col == "CREATED_ON"
    assert s311.interval_seconds == 180.0
    assert s311.producer_key == "311"
    assert s311.extra["expected_cadence_days"] == 7
    assert s311.extra["oid_field"] == "OBJECTID"
    assert s311.extra["max_record_count"] == 2000
    assert s311.extra["field_map"] == HOUSTON_FIELD_MAP

    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.PERMITS)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.SLA)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.DEEDS)


HOUSTON_311_ROW = {
    # Live newest-row sample via REST on 2026-08-26, flattened exactly as
    # ArcGISClient._flatten_feature delivers it: attributes dict, point
    # geometry lifted to lowercase latitude/longitude, date fields converted
    # to ISO 8601 UTC strings.
    "OBJECTID": 41174,
    "CASE_NUMBER": "2600277265",
    "CASE_TYPE": "Water Service",
    "CREATED_ON": "2026-08-24T15:17:24+00:00",
    "CLOSED_ON": None,
    "STATUS": "New",
    "LATITUDE": 29.60919,
    "LONGITUDE": -95.25369,
    "ADDRESS": "10810 LINDEN GATE DR",
    "STREET": "LINDEN GATE",
    "ZIP": "77075",
    "SUPERNEIGHBORHOOD": "SOUTH BELT / ELLINGTON",
    "COUNCIL_DISTRICT": "I",
    "latitude": 29.609190000118634,
    "longitude": -95.25368999964554,
}


class TestHouston311Parsing:
    """Parse pins against the shared Complaints311Producer (US-140)."""

    @pytest.fixture
    def producer(self):
        with (
            patch("src.producers.complaints_311_producer.BaseKafkaProducer"),
            patch(
                "src.producers.field_maps.resolve_field_map",
                return_value=HOUSTON_FIELD_MAP,
            ),
        ):
            from src.producers.complaints_311_producer import Complaints311Producer

            yield Complaints311Producer()

    def test_live_row_parses_uppercase_schema(self, producer):
        event = producer.parse_socrata_row(dict(HOUSTON_311_ROW), city_id="houston")
        assert event is not None
        assert event.city_id == "houston"
        assert event.incident_id == "2600277265"
        assert event.complaint_type == "Water Service"
        assert event.status == "New"
        assert event.created_date is not None
        assert event.created_date.year == 2026
        assert event.zipcode == "77075"
        assert event.incident_address == "10810 LINDEN GATE DR"
        assert event.latitude == pytest.approx(29.60919)
        assert event.longitude == pytest.approx(-95.25369)
        assert event.borough == "HOUSTON_CORE"
        assert event.source_neighborhood == "SOUTH BELT / ELLINGTON"

    def test_missing_case_number_returns_none(self, producer):
        row = dict(HOUSTON_311_ROW)
        row.pop("CASE_NUMBER")
        assert producer.parse_socrata_row(row, city_id="houston") is None
