"""Annual year-slice rollover drill (US-70; roadmap §8.2, risk R3).

DC permits/311, Boston 311, and Baltimore 311 publish one layer/resource per
calendar year via ``DatasetSpec.extra["endpoint_by_year"]``. If the mapping
for the new year is never appended, the scheduler silently keeps polling last
year's stale layer — the exact "Certain (if unmitigated)" failure risk R3.

This module is the frozen-clock drill: simulate the scheduler at a target
date (staging freezes the clock to Jan 2) and assert every year-sliced feed
resolves to a layer/resource for that year. ``resolve_endpoint`` deliberately
falls back to the newest past year when the current year is unmapped (graceful
when the ETL publishes the new layer late), so the drill must catch the
missing mapping itself — a feed without the target year raises
:class:`RolloverDrillError` loudly instead of silently passing.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from src.spatial.city_registry import (
    REGISTRY,
    CityId,
    DatasetSpec,
    FeedType,
    get_job_name,
    resolve_endpoint,
)


@dataclass(frozen=True)
class YearSliceFeed:
    """One registered feed that publishes a layer/resource per calendar year."""

    city_id: CityId
    feed: FeedType
    spec: DatasetSpec


def iter_year_sliced_feeds() -> list[YearSliceFeed]:
    """Every registered feed carrying an ``endpoint_by_year`` mapping."""
    return [
        YearSliceFeed(city_id, feed, spec)
        for city_id, reg in REGISTRY.items()
        for feed, spec in reg.datasets.items()
        if spec.extra.get("endpoint_by_year")
    ]


class RolloverDrillError(RuntimeError):
    """One or more year-sliced feeds lack a mapping for the drill's target year."""


@dataclass(frozen=True)
class RolloverCheck:
    """A year-sliced feed resolved to a layer for the drill's target year."""

    job: str
    city_id: str
    feed: str
    year: int
    endpoint: str


def drill_rollover(
    today: date,
    feeds: Iterable[YearSliceFeed] | None = None,
) -> list[RolloverCheck]:
    """Frozen-clock rollover drill for every year-sliced feed.

    Resolves each feed's endpoint the way the scheduler will at ``today`` and
    requires a mapping for ``today.year``. Returns the resolved checks; raises
    :class:`RolloverDrillError` naming every feed whose mapping lacks the
    target year — the drill must fail loudly before production silently
    re-polls last year's layer.
    """
    missing: list[tuple[CityId, FeedType, list[str]]] = []
    checks: list[RolloverCheck] = []
    for entry in feeds if feeds is not None else iter_year_sliced_feeds():
        by_year = entry.spec.extra.get("endpoint_by_year") or {}
        if str(today.year) not in by_year:
            missing.append((entry.city_id, entry.feed, sorted(by_year)))
            continue
        endpoint = resolve_endpoint(entry.spec, today=today)
        checks.append(
            RolloverCheck(
                job=get_job_name(entry.feed, entry.city_id),
                city_id=entry.city_id.value,
                feed=entry.feed.value,
                year=today.year,
                endpoint=endpoint,
            )
        )
    if missing:
        details = "; ".join(
            f"{get_job_name(feed, city)} ({city.value}/{feed.value}) maps "
            f"{mapped_years or 'no years'}"
            for city, feed, mapped_years in missing
        )
        raise RolloverDrillError(
            f"Year-slice rollover drill FAILED for {today.year}: {len(missing)} "
            f"feed(s) have no endpoint_by_year mapping for that year — append "
            f"the year's layer/resource before New Year (roadmap §8.2). "
            f"{details}"
        )
    return checks