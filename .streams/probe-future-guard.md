# Stream log — probe-future-guard — 2026-08-24

## Claim

- **Stream id:** `probe-future-guard`
- **Leaf files I will create/edit:** `scripts/feed_staleness_probe.py`, `apps/api/tests/unit/test_feed_staleness_probe.py`
- **Spine files I expect to need:** NONE

## Intent

The staleness probe treats FUTURE-dated watermarks as freshness evidence, so
dead feeds with e.g. license-expiration dates in the watermark column look
fresh (observed: nyc/sla 2029-09-01, detroit/deeds 2925-12-24). Done looks
like: `newest_watermark` ignores parsed values strictly greater than `now`
(keyword param, default `datetime.now(UTC)`), probe_feed passes its `now`
through, docstring documents the all-future → None → conservative-stale
consequence, and unit tests cover future-row filtering and the all-future case.

## Decisions

- 2026-08-24 — Guard lives only in the probe script; `parse_watermark` in
  apps/api/src/producers/watermarks.py stays untouched (shared with ingestion).
- 2026-08-24 — Filter is strictly-greater-than `now` (`value <= now` kept), so
  a watermark exactly at `now` still counts as fresh.
- 2026-08-24 — Future-row test fixture uses rows 2026-08-21 + 2027-05-01
  instead of the brief's literal 2026-08-01: with now=2026-08-23 a kept row of
  2026-08-01 is itself 22 days old, so "not stale" would be unreachable no
  matter the source_updated_at; 2026-08-21 keeps the not-stale assertion
  meaningful while still asserting the exact filtered watermark.

## Outcome

DONE — all three verification gates pass:

- `.venv/bin/ruff check scripts/feed_staleness_probe.py apps/api/tests/unit/test_feed_staleness_probe.py`
  → `All checks passed!`
- `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/unit/test_feed_staleness_probe.py`
  → `......... [100%]` — 9 passed (6 pre-existing + 3 new)
- `PYTHONPATH=apps/api .venv/bin/python -m pytest -q -m interlock apps/api`
  → `.................... [100%]` — 20 passed (warnings pre-existing, unrelated)

Changes left uncommitted in the working tree per stream rules.

## Current step

Complete. No work in flight.

## Next step

None for this stream. Orchestrator may close out; dispatch-log update is
orchestrator-owned.
