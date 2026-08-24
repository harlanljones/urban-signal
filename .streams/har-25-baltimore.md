# Stream log — har-25-baltimore — 2026-08-23

## Claim

- **Stream id:** `har-25-baltimore`
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/baltimore.py`, `apps/api/tests/unit/test_producers_baltimore.py`, Baltimore-specific fixtures under `apps/api/tests/fixtures/`, Baltimore research/docs files, and Baltimore-specific README/dashboard copy where disjoint.
- **Spine files I expect to need:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`, `apps/api/src/spatial/cities/__init__.py`, `apps/api/src/producers/scheduler.py`, `apps/api/src/producers/dob_permits_producer.py`, `apps/api/src/producers/complaints_311_producer.py`, `apps/api/src/producers/sla_licenses_producer.py`, `apps/api/src/producers/deeds_acris_producer.py`, plus the excluded static dashboard `apps/product/public/index.html`.

## Intent

Complete Baltimore registration for the three verified ArcGIS feeds (permits, year-sliced 311, and notifications-grade licenses), including rollover-safe 311 discovery, geographic config, fixtures/tests, registry and dashboard wiring, and supporting README/research documentation.

## Decisions

- 2026-08-23 — Existing worktree contains unrelated edits; preserve them and keep Baltimore changes additive.
- 2026-08-23 — Graph project is indexed and has no parse gaps; `apps/product/public/index.html` is excluded by design and will be read directly.
- 2026-08-23 — `.streams/city-baltimore.md` identifies an earlier owner and complete implementation; no source edits made in this stream.
- 2026-08-23 — Direct dashboard inspection confirms Baltimore selector, comparison option, and `BALTIMORE_CORE` camera in the excluded static copy.
- 2026-08-23 — `compileall` and `git diff --check` pass. Focused tests and `pytest -m interlock` are blocked during collection because the environment has no `pydantic`.

## Current step

Verification of the existing Baltimore implementation is complete; source ownership remains with the earlier stream.

## Next step

Report verification evidence and the Linear credential/dependency blockers without touching the earlier stream’s files.
