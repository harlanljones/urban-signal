# Stream log — us-356-madison — 2026-08-29

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** us-356-madison
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/madison.py`, Madison-specific tests under `apps/api/tests/`
- **Spine files I expect to need:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`, `apps/api/src/spatial/cities/__init__.py`, `apps/api/src/spatial/geo_utils.py`, `apps/api/src/spatial/submarkets.py`, `apps/api/src/producers/scheduler.py`, `apps/api/src/producers/dob_permits_producer.py`, `apps/api/src/producers/complaints_311_producer.py`, `apps/api/src/producers/sla_licenses_producer.py`, `apps/api/src/producers/deeds_acris_producer.py`

## Intent

Register Madison, add the reusable Accela integration needed by Midwest cities,
and wire map metadata, published res-5 coverage, snapshot export, and generated
dashboard output while preserving interlock invariants.

## Decisions

<Appended as made. Findings go here the moment they are learned (F5) —
not at the end.>

- 2026-08-29 — Issue triage confirms Madison’s ArcGIS Hub has no usable transactional feeds; Accela is the intended source.

## Current step

Leaf geometry, field map, and shared Accela client are implemented; the
interlock hold is active for registry, config, producer, and dashboard wiring.

## Next step

Regenerate the static dashboard, add contract tests, run interlock and focused
producer checks, then commit and push the requested branch.
