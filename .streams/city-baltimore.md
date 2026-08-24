# Stream log — city-baltimore — 2026-08-24

## Claim

- **Stream id:** city-baltimore
- **Leaf files already present in the shared worktree:** `src/spatial/cities/baltimore.py`, `tests/unit/test_producers_baltimore.py`
- **Spine files already wired in the shared worktree:** `src/config.py`, `src/spatial/city_registry.py`, `src/spatial/cities/__init__.py`, `src/serving/dashboard.py`, `apps/edge/public/index.html`, `README.md`

## Intent

Verify the existing Baltimore ArcGIS registration, preserve the current-year 311 rollover and notifications-grade liquor scope, and avoid duplicating or overwriting the other agent's implementation.

## Decisions

- 2026-08-24 — Existing Baltimore work is treated as owned by the other agent; this stream performs read-only verification only.

## Current step

Read-only verification complete against the shared implementation: Baltimore, export, and interlock tests passed; site content and diff checks passed.

## Next step

Report verification status; leave Linear ownership and source changes to the existing agent.
