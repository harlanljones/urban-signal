"""Contract tests for Baton Rouge's three verified Socrata feeds."""

import pytest

from src.spatial.cities.baton_rouge import (
    BATON_ROUGE_DIVISION_BBOXES,
    BATON_ROUGE_DIVISIONS,
    BATON_ROUGE_METRO_BBOX,
    BATON_ROUGE_SUBMARKETS,
    is_in_baton_rouge_metro,
)
from src.spatial.city_registry import CityId, FeedType


def test_baton_rouge_geometry_is_self_consistent():
    assert is_in_baton_rouge_metro(30.4505, -91.1870)
    assert not is_in_baton_rouge_metro(29.9511, -90.0715)
    assert not is_in_baton_rouge_metro(None, None)
    for name, bbox in BATON_ROUGE_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= BATON_ROUGE_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= BATON_ROUGE_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= BATON_ROUGE_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= BATON_ROUGE_METRO_BBOX["max_lng"], name
    claimed = [name for division in BATON_ROUGE_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(BATON_ROUGE_SUBMARKETS)
    assert {meta.city_id for meta in BATON_ROUGE_SUBMARKETS.values()} == {"baton_rouge"}


def test_baton_rouge_registers_three_feeds_and_excludes_sales():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.BATON_ROUGE
    assert normalize_city("brla") is city
    assert REGISTRY[city].job_suffix == "brla"
    assert set(REGISTRY[city].datasets) == {
        FeedType.PERMITS,
        FeedType.COMPLAINTS_311,
        FeedType.SLA,
    }
    assert REGISTRY[city].datasets[FeedType.PERMITS].watermark_col == "issueddate"
    assert REGISTRY[city].datasets[FeedType.COMPLAINTS_311].watermark_col == "createdate"
    license_spec = REGISTRY[city].datasets[FeedType.SLA]
    assert license_spec.watermark_col == ""
    assert license_spec.extra["ingestion_mode"] == "snapshot"
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.DEEDS)


@pytest.mark.parametrize(
    ("feed", "endpoint"),
    [
        (FeedType.PERMITS, "7fq7-8j7r"),
        (FeedType.COMPLAINTS_311, "7ixm-mnvx"),
        (FeedType.SLA, "xw6s-bcqm"),
    ],
)
def test_baton_rouge_specs_pin_researched_sources(feed, endpoint):
    from src.spatial.city_registry import REGISTRY

    assert endpoint in REGISTRY[CityId.BATON_ROUGE].datasets[feed].endpoint
