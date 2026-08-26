# Stream log — city-hartford — 2026-08-26

## Claim

- **Stream id:** `city-hartford`
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/hartford.py`, `apps/api/tests/unit/test_producers_hartford.py`
- **Spine files I expect to need:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`, `apps/api/src/spatial/cities/__init__.py`, `apps/api/src/producers/dob_permits_producer.py`, `apps/api/src/producers/complaints_311_producer.py`, `apps/api/src/producers/sla_licenses_producer.py`, `apps/api/src/serving/dashboard.py`, `apps/dashboard/public/index.html`, `apps/api/tests/unit/test_interlock_gate.py`

## Intent

Register Hartford's verified PERMITS, 311, and CT eLicensing SLA feeds with complete spatial hierarchy, address-only/geocoder caveats, field maps, tests, generated artifacts, and dashboard wiring. Keep the stale deeds table unregistered.

## Decisions

- 2026-08-26 — Claimed Linear US-152 after verifying it was open, unassigned, and had no blocking relations.
- 2026-08-26 — Use the researched ArcGIS proxy layers for permits and 311, plus the live statewide `data.ct.gov` eLicensing Socrata feed filtered to Hartford; do not register the seven-month-lag deeds table.

## Current step

Hartford registration implemented and verified under the shared registry interlock.

## Next step

Recompute the Linear frontier; no ready-for-agent issues are currently available.

## Verification

- `apps/api/.venv/bin/pytest -q tests/unit/test_producers_hartford.py` — 5 passed.
- `apps/api/.venv/bin/pytest -q -m interlock` — 22 passed.
- Full unit suite's only failure was the unrelated live `kc_311` acceptance probe, blocked by sandbox DNS.
