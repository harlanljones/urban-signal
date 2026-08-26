# Stream log — city-raleigh — 2026-08-26

## Claim

- **Stream id:** `city-raleigh`
- **Leaf files:** `apps/api/src/spatial/cities/raleigh.py`, `apps/api/tests/unit/test_producers_raleigh.py`
- **Spine expected:** config.py, city_registry.py, cities/__init__.py, producers, dashboard, generated exports, interlock test

## Intent

Register Raleigh's verified PERMITS, 311, and Wake County DEEDS feeds with complete spatial wiring and tests.

## Decisions

- 2026-08-26 — Claimed Linear US-151 after verifying it was open, unassigned, and had no blocking relations.
- 2026-08-26 — Use live Raleigh ArcGIS permits/311 and Wake County parcel sales; no SLA feed. Official ArcGIS endpoints were verified before registration.

## Current step

Implementation complete; dashboard and product exports regenerated.

## Verification

- `tests/unit/test_producers_raleigh.py`: 5 passed
- `pytest -q -m interlock`: 22 passed
- `scripts/export_dashboard.py` and `scripts/export_site_facts.py`: completed; 35 metro artifacts emitted
- Broad `pytest -q` was stopped after stalling without a result in this environment.

## Next step

No remaining implementation step; resolve Linear US-151 after posting the durable resolution comment.
