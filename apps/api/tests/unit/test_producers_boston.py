"""Contract tests for Boston's CKAN feeds and rollover geometry."""

from datetime import date

from src.spatial.cities.boston import (
    BOSTON_DIVISION_BBOXES,
    BOSTON_DIVISIONS,
    BOSTON_METRO_BBOX,
    BOSTON_SUBMARKETS,
    is_in_boston_metro,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType, resolve_endpoint


def test_boston_geometry_is_self_consistent():
    assert is_in_boston_metro(42.355, -71.055)
    assert not is_in_boston_metro(40.7128, -74.0060)
    assert not is_in_boston_metro(None, None)
    for name, bbox in BOSTON_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= BOSTON_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= BOSTON_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= BOSTON_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= BOSTON_METRO_BBOX["max_lng"], name
    claimed = [name for division in BOSTON_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(BOSTON_SUBMARKETS)
    assert {meta.city_id for meta in BOSTON_SUBMARKETS.values()} == {"boston"}


def test_boston_registers_ckan_feeds_and_no_sales_feed():
    city = CityId.BOSTON
    assert REGISTRY[city].job_suffix == "boston"
    assert set(REGISTRY[city].datasets) == {
        FeedType.PERMITS,
        FeedType.COMPLAINTS_311,
        FeedType.SLA,
    }
    assert REGISTRY[city].datasets[FeedType.PERMITS].platform == "ckan"
    # Licensing Board (04dc653b) fails G5 by construction: gpsx/gpsy are
    sla = REGISTRY[city].datasets[FeedType.SLA]
    assert sla.platform == "ckan"
    assert sla.watermark_col == "expires"
    assert sla.id_keys == ["license_num", "_id"]
    assert sla.extra["state_plane_crs"] == "EPSG:2249"
    assert sla.extra["state_plane_units"] == "US survey feet"
    assert FeedType.DEEDS not in REGISTRY[city].datasets


def test_boston_resources_and_field_maps_are_pinned():
    permits = REGISTRY[CityId.BOSTON].datasets[FeedType.PERMITS]
    assert permits.endpoint == "ckan://data.boston.gov/6ddcd912-32a0-43df-9908-63574f8c7e77"
    assert permits.watermark_col == "issued_date"
    assert permits.extra["field_map"]["job_id"] == ["permitnumber"]

    current_311 = REGISTRY[CityId.BOSTON].datasets[FeedType.COMPLAINTS_311]
    assert current_311.extra["endpoint_by_year"]["2026"].endswith("1a0b420d-99f1-4887-9851-990b2a5a6e17")
    assert resolve_endpoint(current_311, date(2026, 8, 23)).endswith("1a0b420d-99f1-4887-9851-990b2a5a6e17")
    assert current_311.watermark_col == "open_dt"


def test_boston_311_rollover_dry_run_uses_latest_past_resource():
    current_311 = REGISTRY[CityId.BOSTON].datasets[FeedType.COMPLAINTS_311]
    assert resolve_endpoint(current_311, date(2025, 12, 31)).endswith(
        "9d7c2214-4709-478a-a2e8-fb2020a5bb94"
    )
    assert resolve_endpoint(current_311, date(2027, 1, 2)).endswith(
        "1a0b420d-99f1-4887-9851-990b2a5a6e17"
    )
