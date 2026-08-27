"""US-70: frozen-clock New Year rollover drill for year-sliced feeds (roadmap §8.2)."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.producers.rollover import (
    RolloverDrillError,
    YearSliceFeed,
    drill_rollover,
    iter_year_sliced_feeds,
)
from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, DatasetSpec, FeedType

REGISTERED_YEAR_SLICED_JOBS = {"permits_dc", "311_dc", "311_boston", "311_baltimore"}


# ---------------------------------------------------------------------------
# Drill: every year-sliced feed must map the target year (green) or fail loudly
# ---------------------------------------------------------------------------

def _mapped_year_of(every_feed: list[YearSliceFeed]) -> int:
    """The most recent year that every registered year-sliced feed maps."""
    common = None
    for entry in every_feed:
        years = set((entry.spec.endpoint_by_year or {}).keys())
        common = years if common is None else (common & years)
    assert common, "registry has no year shared by every year-sliced feed"
    return max(int(y) for y in common)


def test_drill_green_when_all_feeds_map_target_year():
    feeds = iter_year_sliced_feeds()
    year = _mapped_year_of(feeds)
    checks = drill_rollover(date(year, 6, 1))
    assert len(checks) == len(feeds)
    assert {check.job for check in checks} >= REGISTERED_YEAR_SLICED_JOBS
    assert all(check.year == year for check in checks)
    # Each resolved endpoint matches the mapping the scheduler would use.
    for check in checks:
        entry = next(f for f in feeds if f.feed.value == check.feed and f.city_id.value == check.city_id)
        assert check.endpoint == entry.spec.endpoint_by_year[str(year)]


def test_drill_green_for_synthetic_mapped_year():
    spec = DatasetSpec(
        endpoint="https://fake.example/base",
        endpoint_by_year={"2026": "u/2026", "2027": "u/2027"},
    )
    feed = YearSliceFeed(CityId.BOSTON, FeedType.COMPLAINTS_311, spec)
    checks = drill_rollover(date(2027, 1, 2), feeds=[feed])
    assert len(checks) == 1
    assert checks[0].job == "311_boston"
    assert checks[0].year == 2027
    assert checks[0].endpoint == "u/2027"


def test_drill_fails_loudly_for_unmapped_year():
    spec = DatasetSpec(
        endpoint="https://fake.example/base",
        endpoint_by_year={"2026": "u/2026"},
    )
    feed = YearSliceFeed(CityId.WASHINGTON_DC, FeedType.PERMITS, spec)
    with pytest.raises(RolloverDrillError, match="2027"):
        drill_rollover(date(2027, 1, 2), feeds=[feed])


def test_drill_raises_with_registerable_details_on_live_registry():
    """As of 2026 no feed maps 2027 yet — the drill must fail loudly and
    name the offenders (the R3 failure mode, not a silent fallback pass)."""
    with pytest.raises(RolloverDrillError, match="2027") as excinfo:
        drill_rollover(date(2027, 1, 2))
    message = str(excinfo.value)
    assert "permits_dc" in message or "311_dc" in message


# ---------------------------------------------------------------------------
# Scheduler: frozen-clock rollover detection, baseline reset, metric event
# ---------------------------------------------------------------------------

@pytest.fixture
def scheduler():
    sched = MunicipalIngestionScheduler(dlq_producer=MagicMock(), rate_limit_delay_seconds=0.0)
    for p in sched.producers.values():
        p.producer = MagicMock()
        for client_name in ("socrata", "arcgis", "carto", "ckan"):
            client = getattr(p, client_name, None)
            if client is not None:
                client.paginate = MagicMock(return_value=iter([]))
    return sched


def test_rollover_check_is_noop_for_plain_feeds(scheduler):
    assert scheduler._rollover_check("permits") is False  # NYC permits: no year slice


def test_rollover_switches_layer_resets_baseline_emits_event(scheduler):
    meta = scheduler.job_metadata["311_dc"]
    meta["endpoint_by_year"]["2027"] = "https://fake.example/FeatureServer/99"
    met = scheduler.metrics["311_dc"]
    met.high_watermark = "2026-12-31T00:00:00"
    scheduler._today_provider = lambda: date(2027, 1, 2)

    assert scheduler._rollover_check("311_dc") is True
    assert meta["endpoint"] == "https://fake.example/FeatureServer/99"
    assert met.high_watermark is None
    assert met.rollovers == 1
    assert met.last_rollover == "2027-01-02"

    # While the same layer is current, no re-rollover.
    assert scheduler._rollover_check("311_dc") is False
    assert met.rollovers == 1


def test_poll_job_applies_rollover_before_watermark_filter(scheduler):
    meta = scheduler.job_metadata["311_dc"]
    meta["endpoint_by_year"]["2027"] = "https://fake.example/FeatureServer/99"
    met = scheduler.metrics["311_dc"]
    met.high_watermark = "2026-12-31T00:00:00"
    scheduler._today_provider = lambda: date(2027, 1, 2)
    producer = scheduler.producers[meta["producer_key"]]
    producer.arcgis.paginate = MagicMock(return_value=iter([]))

    result = scheduler.poll_job("311_dc", limit=10)

    assert result["status"] == "SUCCESS"
    assert meta["endpoint"] == "https://fake.example/FeatureServer/99"
    assert met.high_watermark is None
    assert met.rollovers == 1
    _, kwargs = producer.arcgis.paginate.call_args
    assert kwargs["endpoint_url"] == "https://fake.example/FeatureServer/99"
    assert not kwargs.get("where_clause")  # baseline reset -> no watermark filter


def test_same_year_poll_keeps_watermark_baseline(scheduler):
    """Frozen clock within the mapped year: no rollover, the watermark clause
    still guards the incremental fetch."""
    meta = scheduler.job_metadata["311_dc"]
    met = scheduler.metrics["311_dc"]
    met.high_watermark = "2026-12-31T00:00:00"
    scheduler._today_provider = lambda: date(2026, 6, 1)
    producer = scheduler.producers[meta["producer_key"]]
    producer.arcgis.paginate = MagicMock(return_value=iter([]))

    scheduler.poll_job("311_dc", limit=10)

    assert met.rollovers == 0
    assert met.high_watermark == "2026-12-31T00:00:00"
    _, kwargs = producer.arcgis.paginate.call_args
    assert kwargs["endpoint_url"] == meta["endpoint_by_year"]["2026"]
    assert meta["watermark_col"] in (kwargs.get("where_clause") or "")