"""Contract tests for Augusta, GA registration (US-287)."""

from src.spatial.cities.augusta import (
    AUGUSTA_DIVISION_BBOXES,
    AUGUSTA_DIVISIONS,
    AUGUSTA_METRO_BBOX,
    AUGUSTA_SUBMARKETS,
    is_in_augusta_metro,
)
from src.spatial.city_registry import CityId, FeedType


def test_augusta_geometry_is_self_consistent():
    assert is_in_augusta_metro(33.476, -82.010)
    assert not is_in_augusta_metro(34.0522, -118.2437)  # Los Angeles, outside GA bbox
    assert not is_in_augusta_metro(None, None)
    for name, bbox in AUGUSTA_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= AUGUSTA_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= AUGUSTA_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= AUGUSTA_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= AUGUSTA_METRO_BBOX["max_lng"], name
    claimed = [name for division in AUGUSTA_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(AUGUSTA_SUBMARKETS)
    assert {meta.city_id for meta in AUGUSTA_SUBMARKETS.values()} == {"augusta"}


def test_augusta_registry_carries_permits_and_sla_specs():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.AUGUSTA
    assert normalize_city("augusta") is city
    assert normalize_city("augusta_ga") is city
    assert set(REGISTRY[city].datasets) == {FeedType.PERMITS, FeedType.SLA}

    permits = REGISTRY[city].datasets[FeedType.PERMITS]
    assert permits.platform == "arcgis"
    assert permits.producer_key == "permits"
    assert permits.needs_geocode is True
    assert permits.oid_field == "OBJECTID"
    assert "PERMITNUMBER" in permits.id_keys

    # Unregistered feeds raise readable errors
    for feed in (FeedType.COMPLAINTS_311, FeedType.DEEDS):
        try:
            get_dataset(city, feed)
            assert False, "get_dataset should raise for unregistered feeds"
        except KeyError as e:
            msg = str(e)
            assert "augusta" in msg and feed.value in msg

