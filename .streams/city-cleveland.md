# Stream log — city-cleveland — 2026-08-26

## Claim

- **Stream id:** `city-cleveland`
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/cleveland.py`, `apps/api/tests/unit/test_producers_cleveland.py`
- **Spine files I expect to need:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`, `apps/api/src/spatial/cities/__init__.py`, `apps/api/src/producers/dob_permits_producer.py`, `apps/api/src/producers/complaints_311_producer.py`, `apps/api/src/producers/deeds_acris_producer.py`, `apps/api/src/serving/dashboard.py`, `apps/dashboard/public/index.html`, `apps/api/tests/unit/test_interlock_gate.py`

## Intent

Register Cleveland's verified PERMITS, 311, and DEEDS ArcGIS feeds with complete spatial hierarchy, field maps, tests, snapshot coverage, and dashboard wiring.

## Decisions

- 2026-08-26 — Claimed Linear US-153 after verifying it was open, unassigned, and had no blocking relations.
- 2026-08-26 — Use the researched live feeds: `Building_Permits/FeatureServer/0`, `Data_311/FeatureServer/0`, and `Parcel_Analytics_(PUBLIC_DRAFT_)/FeatureServer/0`; preserve the documented permit-sync lag.

## Current step

Cleveland leaf, registry, producer, dashboard, generated-artifact, and interlock wiring are implemented and verified.

## Next step

Review and merge the implementation; US-153 remains open and assigned to the implementing agent.
