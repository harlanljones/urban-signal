# Stream log — city-gainesville — 2026-08-28

## Claim

- Stream id: `city-gainesville`
- Leaf files I will create/edit:
  - `apps/api/src/spatial/cities/gainesville.py` (NEW)
  - `apps/api/src/producers/field_maps_gainesville.py` (NEW)
  - `apps/api/tests/unit/test_producers_gainesville.py` (NEW)
- Spine files I expect to need (per docs/agents/spine-manifest.txt):
  - `apps/api/src/spatial/city_registry.py` (CityId.GAINESVILLE + ALIASES + REGISTRY entry)
  - `apps/api/src/config.py` (add `socrata_gainesville_permits_endpoint`)
  - `apps/api/src/spatial/cities/__init__.py` (export Gainesville constants)
  - `apps/api/src/serving/dashboard.py` (METRO_META + byte-sync)

## Intent

Register Gainesville, FL as a new Urban Signal metro (`CityId.gainesville`) with verified public feed coverage (PERMITS via Socrata `p798-x3nx`), full spatial leaf (metro bbox, divisions, submarkets), aliases, dashboard `METRO_META` and static sync, and product facts. Fit is High; aliases include `gainesville`, `gainesville_fl`, `gainesville fl`. Prefer verified public permits (found) over SNAP fallback.

## Decisions

- 2026-08-28 — Verified City of Gainesville Socrata portal `data.cityofgainesville.org` carries a live, geocoded Building Permits dataset `p798-x3nx` with `location_1` point, `latitude`/`longitude`, `issue` date, and `permit` id.
- 2026-08-28 — 311 dataset exists (`78uv-94ar`) but reflects a migration note and appears stale post-2021; not registering 311 in this ticket. PERMITS only.
- 2026-08-28 — CityId is free (`gainesville`); proceed with that id. Aliases: `gainesville`, `gainesville_fl`, `gainesville fl`.
- 2026-08-28 — Field map: `job_id` ← `permit`, `issuance_date` ← `issue`, `address_street` ← `address`, `latitude`/`longitude` ← direct or `location_1.{latitude,longitude}`; `status` if present.

## Current step

Additive rebase onto origin/main is complete. PR #31 should update in place on `cursor/gainesville-metro-9b36`. Tests green (unit + interlock). Stop — do not start Columbus/Melbourne/Ocala.

## Next step

Human merge of #31. No further city onboarding from this stream.

