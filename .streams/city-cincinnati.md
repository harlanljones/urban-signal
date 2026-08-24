# Stream log — city-cincinnati — 2026-08-24

## Claim

- **Stream id:** city-cincinnati
- **Leaf files I will create/edit:** `src/spatial/cities/cincinnati.py`, `tests/unit/test_producers_cincinnati.py`
- **Spine files I expect to need:** `src/config.py`, `src/spatial/city_registry.py`, `src/spatial/cities/__init__.py`, `src/serving/dashboard.py`, `apps/dashboard/public/index.html`, `README.md`

## Intent

Register Cincinnati's three verified Socrata feeds (permits, 311, licenses), preserve the no-sales and address-geocoded permit caveats, and wire the city through the selector, dashboard map, static edge copy, README, and tests with the interlock gate green.

## Decisions

- 2026-08-24 — Use `cinci` as the job suffix and register only permits, 311, and SLA; no sales dataset was found.
- 2026-08-24 — Use one Cincinnati Core division with a city-wide bbox because the verified contract supplies no authoritative submarket/division roster.

## Current step

Leaf city geometry and producer fixtures are being authored before the serial spine hold.

## Next step

Apply config, registry, package export, dashboard, static-copy, and README wiring; run `pytest -m interlock` immediately.
