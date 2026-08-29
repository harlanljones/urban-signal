# Stream log — us-357-grand-rapids — 2026-08-29

## Claim

- **Stream id:** `us-357-grand-rapids`
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/grand_rapids.py`, `apps/api/tests/unit/test_producers_grand_rapids.py`, `docs/research/probe-grand_rapids.md` (only if research updates are needed)
- **Spine files I expect to need:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`, `apps/api/src/spatial/cities/__init__.py`, `apps/api/src/spatial/geo_utils.py`, `apps/api/src/spatial/submarkets.py`, `apps/api/src/producers/scheduler.py`, `apps/api/src/producers/dob_permits_producer.py`, `apps/api/src/producers/complaints_311_producer.py`, `apps/api/src/producers/sla_licenses_producer.py`, `apps/api/src/producers/deeds_acris_producer.py`

## Intent

Onboard Grand Rapids as a complete, map-visible metro registration using the shared Midwest Accela implementation where applicable, while preserving the verified absence of unsupported feeds and satisfying registry, snapshot, manifest, generated-dashboard, and interlock invariants.

## Decisions

- 2026-08-29 — Use the existing shared Accela work; do not duplicate a client or invent Hub feeds for the four families absent from the verified catalog. No shared Accela client is present on this base branch, and the live probe classifies Accela as UI-only.
- 2026-08-29 — Register geometry only, with an empty dataset map, so the metro is map-visible and unsupported feeds fail through the readable `get_dataset()` path.

## Current step

Spine hold is active: city enum/aliases/registry, package exports, dashboard metadata, and generated static copy are wired; interlock passes.

## Next step

Run focused city checks and diff review, then commit, push, and open the draft PR.
