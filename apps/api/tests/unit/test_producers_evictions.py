"""Unit tests for the NYC executed-evictions registration (US-93).

Fixtures mirror live rows probed 2026-08-24 from `6z8x-wfk4`.
"""

from unittest.mock import patch

import pytest

from src.producers.evictions_producer import EvictionsProducer
from src.spatial.city_registry import (
    REGISTRY,
    CityId,
    FeedType,
    get_dataset,
    get_job_name,
)

EVICTION_ROW = {
    "court_index_number": "302444/23B",
    "docket_number": "211444",
    "eviction_address": "951 EAST 104TH ST",
    "eviction_apt_num": "1",
    "executed_date": "2026-08-20T00:00:00.000",
    "residential_commercial_ind": "Residential",
    "borough": "BROOKLYN",
    "eviction_zip": "11236",
    "ejectment": "Not an Ejectment",
    "eviction_possession": "Possession",
    "latitude": "40.646197",
    "longitude": "-73.894456",
    "community_board": "18",
    "council_district": "46",
    "census_tract": "986",
    "bin": "3230517",
    "bbl": "3082120026",
    "nta": "Canarsie",
}


@pytest.fixture
def producer():
    with patch("src.producers.evictions_producer.BaseKafkaProducer"):
        return EvictionsProducer()


def test_eviction_row_parses(producer):
    event = producer.parse_socrata_row(EVICTION_ROW, city_id="nyc")
    assert event is not None
    assert event.city_id == "nyc"
    assert event.eviction_id == "302444/23B"
    assert event.address == "951 EAST 104TH ST #1"
    assert event.borough is not None
    assert event.zipcode == "11236"
    assert event.residential_commercial == "Residential"
    assert event.executed_date is not None
    assert event.latitude == pytest.approx(40.646197)
    assert event.longitude == pytest.approx(-73.894456)
    assert event.h3_res9
    bbox = REGISTRY[CityId.NYC].metro_bbox
    assert bbox["min_lat"] <= event.latitude <= bbox["max_lat"]
    assert bbox["min_lng"] <= event.longitude <= bbox["max_lng"]


def test_eviction_without_coordinates_is_dropped(producer):
    row = {k: v for k, v in EVICTION_ROW.items() if k not in ("latitude", "longitude")}
    assert producer.parse_socrata_row(row, city_id="nyc") is None


def test_eviction_registration_is_nyc_only():
    assert FeedType.EVICTIONS in REGISTRY[CityId.NYC].datasets
    assert get_job_name(FeedType.EVICTIONS, CityId.NYC) == "evictions"
    spec = get_dataset(CityId.NYC, FeedType.EVICTIONS)
    assert spec.endpoint.endswith("6z8x-wfk4.json")
    assert spec.watermark_col == "executed_date"
    assert spec.topic == "raw.municipal.evictions"
    # No other city registers evictions (single-metro asymmetry rule).
    for cid, reg in REGISTRY.items():
        if cid is not CityId.NYC:
            assert FeedType.EVICTIONS not in reg.datasets, cid