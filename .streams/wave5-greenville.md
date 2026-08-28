# wave5-greenville — US-340 Greenville, SC (leaf implementation)

**Status: IN PROGRESS** — 2026-08-28, LEAF-IMPLEMENTATION agent.

## Claim

- **Stream id:** wave5-greenville (US-340)
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/greenville.py` (new)
  - `apps/api/src/producers/field_maps_greenville.py` (new, if needed)
  - `apps/api/tests/unit/test_producers_greenville.py` (new)
  - `.streams/wave5-greenville.md` + one dispatch-log outcome row
- **Spine files I expect to need (NOT touched by this leaf):**
  `city_registry.py`, `config.py`, `serving/dashboard.py`, `cities/__init__.py`,
  existing tests, `apps/product/**`. No git commit.

## Intent

Register Greenville, SC as a ONE-FEED PARTIAL metro (PERMITS only, Tier 1 —
`citygis.greenvillesc.gov` ArcGIS Server 10.81 MapServer
`InfoHUB/BuildingPermits_PriorTwoYears/MapServer/0`, watermark `NewIssueDate`,
daily; 311/SLA/deeds Tier 3 unregistered per probe). Author the leaf module
mirroring `git show 2a70e39:apps/api/src/spatial/cities/henderson.py` with
6–8 submarkets, parse tests through the real `DOBPermitsProducer` path with
live-captured fixtures (`city_id="greenville"` strings, no CityId import),
and run all gates. Tests must NOT assert division/borough resolution or
geocode-hook call counts (spine-volatile); assert parse fields,
source-neighborhood passthrough, H3 from fixture coords, bbox containment,
field-map mappings instead.

## Evidence

- `docs/research/probe-greenville.md` (stamped 2026-08-28): PERMITS T1 daily,
  native outSR=4326 geometry (do NOT use State Plane `X_COORD`/`Y_COORD`
  attributes), `STREETADDRESS` fallback, id_keys `["PERMIT_NUM"]`,
  maxRecordCount 7000, rolling 2-year window, MapServer (not FeatureServer).
- Live re-probe: appended below as learned (F5).

## Decisions

- 2026-08-28 — Claimed per wave-5 leaf contract.

## Current step

Claim written; starting live re-probe of the permits layer.

## Next step

Capture ≥2 fixture rows byte-verbatim → author leaf module → field maps →
tests → gates.
