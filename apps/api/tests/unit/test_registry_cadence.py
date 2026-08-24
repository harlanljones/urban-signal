"""G11 registry invariant: every registered feed declares its cadence.

The staleness probe alarms at 2 x expected_cadence_days; a feed without the
declaration silently falls back to the legacy global window. This test keeps
that path empty so no future registration can page forever (or never page)
because its publishing rhythm was never declared.
"""

from src.spatial.city_registry import REGISTRY


def test_every_registered_feed_declares_expected_cadence():
    bad = []
    for city, registration in REGISTRY.items():
        for feed, spec in registration.datasets.items():
            days = (spec.extra or {}).get("expected_cadence_days")
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
        spec.extra["expected_cadence_days"]
        for registration in REGISTRY.values()
        for spec in registration.datasets.values()
        if "expected_cadence_days" in spec.extra
    }
    assert 7 in values
