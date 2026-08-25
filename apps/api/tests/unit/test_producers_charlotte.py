"""Contract tests for Charlotte, NC (ArcGIS 311 service requests)."""

from unittest.mock import patch

import pytest

from src.spatial.cities.charlotte import (
    CHARLOTTE_DIVISION_BBOXES,
    CHARLOTTE_DIVISIONS,
    CHARLOTTE_METRO_BBOX,
    CHARLOTTE_SUBMARKETS,
    is_in_charlotte_metro,
)
from src.spatial.city_registry import CityId, FeedType

# Recommended DatasetSpec.extra["field_map"] for US-88. Every entry spells an
# uppercase column the shared producer fallback chains cannot reach;
# latitude/longitude need no entry because ArcGISClient lifts point geometry
# onto those exact keys (outSR=4326) before parsing.
CHARLOTTE_FIELD_MAP = {
    "incident_id": ["REQUEST_NO"],
    "created_date": ["RECEIVED_DATE"],
    "complaint_type": ["REQUEST_TYPE"],
    "incident_address": ["FULL_ADDRESS"],
    "borough": ["COUNCIL_DISTRICT"],
}


def test_charlotte_geometry_is_self_consistent():
    assert is_in_charlotte_metro(35.2271, -80.8431)  # Uptown center
    assert is_in_charlotte_metro(35.16488019, -80.83107563)  # observed live-row
    assert is_in_charlotte_metro(35.10438352, -80.78525774)  # observed live-row
    assert not is_in_charlotte_metro(35.9940, -80.8490)  # Statesville, north of the county
    assert not is_in_charlotte_metro(None, None)
    for name, bbox in CHARLOTTE_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= CHARLOTTE_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= CHARLOTTE_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= CHARLOTTE_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= CHARLOTTE_METRO_BBOX["max_lng"], name
    claimed = [name for division in CHARLOTTE_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(CHARLOTTE_SUBMARKETS)
    assert {meta.city_id for meta in CHARLOTTE_SUBMARKETS.values()} == {"charlotte"}


def test_charlotte_registers_arcgis_311_only():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.CHARLOTTE
    assert normalize_city("charlotte") is city
    assert normalize_city("mecklenburg") is city
    assert REGISTRY[city].job_suffix == "clt"
    assert set(REGISTRY[city].datasets) == {FeedType.COMPLAINTS_311}

    s311 = REGISTRY[city].datasets[FeedType.COMPLAINTS_311]
    assert s311.platform == "arcgis"
    assert s311.watermark_col == "RECEIVED_DATE"
    assert s311.interval_seconds == 180.0
    assert s311.producer_key == "311"
    assert s311.extra["expected_cadence_days"] == 7
    assert s311.extra["oid_field"] == "OBJECTID"
    assert s311.extra["max_record_count"] == 7500
    assert s311.extra["field_map"] == CHARLOTTE_FIELD_MAP

    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.PERMITS)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.SLA)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.DEEDS)


CLT_311_ROW = {
    # Live newest-rows sample via REST on 2026-08-24, flattened exactly as
    # ArcGISClient._flatten_feature delivers it: attributes dict, point
    # geometry lifted to latitude/longitude, epoch-ms date fields re-encoded
    # to ISO 8601 UTC strings.
    "OBJECTID": 3380558,
    "REQUEST_NO": 11041585,
    "DEPARTMENT": "Solid Waste Services",
    "REQUEST_TYPE": "NON_RECYCLABLE ITEMS",
    "RECEIVED_DATE": "2026-08-24T02:08:29+00:00",
    "FULL_ADDRESS": "3030 FERNCLIFF RD, CHARLOTTE, NC  28211",
    "LATITUDE": 35.16488019,
    "LONGITUDE": -80.83107563,
    "COUNCIL_DISTRICT": "6",
    "latitude": 35.16488019,
    "longitude": -80.83107563,
}


class TestCharlotte311Parsing:
    """Parse pins against the shared Complaints311Producer (US-88)."""

    @pytest.fixture
    def producer(self):
        with (
            patch("src.producers.complaints_311_producer.BaseKafkaProducer"),
            patch(
                "src.producers.field_maps.resolve_field_map",
                return_value=CHARLOTTE_FIELD_MAP,
            ),
        ):
            from src.producers.complaints_311_producer import Complaints311Producer

            yield Complaints311Producer()

    def test_live_row_parses_uppercase_schema(self, producer):
        event = producer.parse_socrata_row(dict(CLT_311_ROW), city_id="charlotte")
        assert event is not None
        assert event.city_id == "charlotte"
        assert event.incident_id == "11041585"
        assert event.complaint_type == "NON_RECYCLABLE ITEMS"
        assert event.created_date is not None
        assert event.created_date.year == 2026
        assert event.latitude == pytest.approx(35.16488019)
        assert event.longitude == pytest.approx(-80.83107563)

    def test_missing_request_no_returns_none(self, producer):
        row = dict(CLT_311_ROW)
        row.pop("REQUEST_NO")
        assert producer.parse_socrata_row(row, city_id="charlotte") is None