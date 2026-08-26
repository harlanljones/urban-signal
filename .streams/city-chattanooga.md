# Stream log — city-chattanooga — 2026-08-26

## Claim

- **Stream id:** `city-chattanooga`
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/chattanooga.py`, `apps/api/tests/unit/test_producers_chattanooga.py`
- **Spine files I expect to need:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`, `apps/api/src/spatial/cities/__init__.py`, `apps/api/src/producers/dob_permits_producer.py`, `apps/api/src/producers/deeds_acris_producer.py`, `apps/dashboard/src/index.ts`, `apps/dashboard/public/index.html`, `apps/api/src/export/snapshot_builder.py`

## Intent

Register Chattanooga's live PERMITS CSV and DEEDS parcel feeds with complete spatial hierarchy, field maps, tests, snapshot coverage, and dashboard wiring so the city is visible end to end.

## Decisions

- 2026-08-26 — Claimed Linear US-155 after verifying it was open, unassigned, and had no blocking relations.
- 2026-08-26 — Added Chattanooga geometry, PERMITS CSV + DEEDS ArcGIS specs, field maps, and a CSV fallback test; registered dashboard/static/facts coverage.

## Current step

Focused city, interlock, scheduler, snapshot, and product-facts checks are green; the broader unit run is environment-limited by live Socrata DNS and unrelated long-running tests.

## Next step

Review and merge the implementation; US-155 remains open and assigned to the implementing agent.
