"""G11 registry invariant: every registered feed declares its cadence.

The staleness probe alarms at 2 x expected_cadence_days; a feed without the
declaration silently falls back to the legacy global window. This test keeps
that path empty so no future registration can page forever (or never page)
because its publishing rhythm was never declared.
"""

from src.spatial.city_registry import REGISTRY, CityId, FeedType


def test_every_registered_feed_declares_expected_cadence():
    bad = []
    for city, registration in REGISTRY.items():
        for feed, spec in registration.datasets.items():
            days = spec.expected_cadence_days
            if not isinstance(days, int) or isinstance(days, bool) or days < 1:
                bad.append(f"{city.value}/{feed.value}: {days!r}")
    assert bad == []


def test_backfilled_feeds_keep_the_default_seven():
    """Wave-2 D8 backfill: existing feeds declare N=7 (alarm at 14d).

    Per-feed overrides (PG County ~monthly, KC weekly) arrive with their own
    registration tickets and will legitimately shrink this set's membership
    in favor of their declared value.
    """
    values = {
        spec.expected_cadence_days
        for registration in REGISTRY.values()
        for spec in registration.datasets.values()
        if spec.expected_cadence_days is not None
    }
    assert 7 in values


def test_connecticuts_yearly_sales_set_declares_a_yearly_cadence():
    """data.ct.gov's sales set (``5mzw-sjtu``) is published once a year: the
    2026-08-12 update added sales to 2025-09-30, so its newest sale runs 10 to
    23 months old, and a 30-day declaration paged every weekly run."""
    for city in (CityId.BRIDGEPORT, CityId.NEW_HAVEN):
        spec = REGISTRY[city].datasets[FeedType.DEEDS]
        assert spec.endpoint.endswith("5mzw-sjtu.json")
        assert spec.expected_cadence_days == 365
