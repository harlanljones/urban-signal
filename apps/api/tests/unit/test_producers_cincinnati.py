"""Contract tests for the Cincinnati registration and three Socrata feeds."""

import pytest

from src.spatial.cities.cincinnati import (
    CINCINNATI_DIVISION_BBOXES,
    CINCINNATI_DIVISIONS,
    CINCINNATI_METRO_BBOX,
    CINCINNATI_SUBMARKETS,
    is_in_cincinnati_metro,
)
from src.spatial.city_registry import CityId, FeedType


def test_cincinnati_geometry_is_self_consistent():
    assert is_in_cincinnati_metro(39.1031, -84.5120)
    assert not is_in_cincinnati_metro(41.8781, -87.6298)
    assert not is_in_cincinnati_metro(None, None)
    for name, bbox in CINCINNATI_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= CINCINNATI_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= CINCINNATI_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= CINCINNATI_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= CINCINNATI_METRO_BBOX["max_lng"], name
    claimed = [name for division in CINCINNATI_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(CINCINNATI_SUBMARKETS)
    assert {meta.city_id for meta in CINCINNATI_SUBMARKETS.values()} == {"cincinnati"}


def test_cincinnati_registers_three_verified_feeds_and_no_sales_feed():
    from src.spatial.city_registry import REGISTRY, normalize_city

    city = CityId.CINCINNATI
    assert normalize_city("cinci") is city
    assert REGISTRY[city].job_suffix == "cinci"
    assert set(REGISTRY[city].datasets) == {
        FeedType.PERMITS,
        FeedType.COMPLAINTS_311,
        FeedType.SLA,
    }
    assert REGISTRY[city].datasets[FeedType.PERMITS].watermark_col == "issued"
    assert REGISTRY[city].datasets[FeedType.COMPLAINTS_311].watermark_col == "created_on"
    assert REGISTRY[city].datasets[FeedType.SLA].watermark_col == "entered"
    with pytest.raises(KeyError, match="no.*feed"):
        from src.spatial.city_registry import get_dataset

        get_dataset(city, FeedType.DEEDS)


@pytest.mark.parametrize(
    ("feed", "endpoint", "watermark"),
    [
        (FeedType.PERMITS, "uhjb-xac9", "issued"),
        (FeedType.COMPLAINTS_311, "gcej-gmiw", "created_on"),
        (FeedType.SLA, "ehdi-ajku", "entered"),
    ],
)
def test_cincinnati_specs_pin_researched_socrata_sources(feed, endpoint, watermark):
    from src.spatial.city_registry import REGISTRY

    spec = REGISTRY[CityId.CINCINNATI].datasets[feed]
    assert endpoint in spec.endpoint
    assert spec.watermark_col == watermark
