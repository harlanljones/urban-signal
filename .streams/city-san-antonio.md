# Stream log — city-san-antonio — 2026-08-26

## Claim

- **Stream id:** `city-san-antonio`
- **Leaf files:** `apps/api/src/spatial/cities/san_antonio.py`, `apps/api/tests/unit/test_producers_san_antonio.py`
- **Spine expected:** config.py, city_registry.py, cities/__init__.py, CKAN/ArcGIS producer seams, dashboard, generated exports, interlock test

## Intent

Register San Antonio's verified PERMITS and 311 feeds with mixed-coordinate handling, complete spatial wiring, and tests.

## Decisions

- 2026-08-26 — Claimed Linear US-141 after verifying it was open, unassigned, and had no blocking relations.
- 2026-08-26 — Use the live CKAN permits datastore and ArcGIS 311 layer; do not register dateless TABC licenses or unverified deeds.

## Current step

Implementation complete; dashboard and product exports regenerated.

## Verification

- `tests/unit/test_producers_san_antonio.py`: 5 passed
- `pytest -q -m interlock`: 22 passed
- San Antonio CKAN permit tests cover native text coordinates and projected-coordinate geocoder fallback.
- Broad `pytest -q` was stopped after stalling without a result in this environment.

## Next step

No remaining implementation step; resolve Linear US-141 after posting the durable resolution comment.
