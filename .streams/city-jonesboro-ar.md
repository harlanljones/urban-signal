# Stream log — city-jonesboro-ar — 2026-08-28

## Claim

- **Stream id:** city-jonesboro-ar
- **Leaf files I will create/edit:**
  - apps/api/src/spatial/cities/jonesboro.py
  - apps/api/tests/unit/test_producers_jonesboro.py
- **Spine files I expect to need:**
  - apps/api/src/spatial/city_registry.py
  - apps/api/src/spatial/cities/__init__.py
  - apps/api/src/serving/dashboard.py
  - docs/agents/spine-manifest.txt (read-only guard)

## Intent

Onboard Jonesboro, AR as a new Urban Signal metro (South Central). Deliver a
leaf-first spatial definition (metro bbox, divisions, submarkets) with
containment tests, then register `CityId.jonesboro` in the spine with SNAP SLA
(`snap_sla_spec("AR")`) pending a verifiable municipal permits endpoint. Wire
`METRO_META` and byte-sync the dashboard. Regenerate site facts so product
artifacts remain in lockstep with the registry. Keep edits additive and isolated
per parallel-streams guidance (US-283).

## Decisions

- 2026-08-28 — No verifiable public Jonesboro permits API identified quickly;
  register SNAP-only (AR slice) and defer permits to a follow-up once proven.

## Current step

Leaf geometry and containment tests added; proceeding to hold the spine to
register the city, wire `METRO_META`, and export product facts + dashboard.

## Next step

Run the interlock gate (`pytest -m interlock` from `apps/api`) and remediate
any failures. Then open the PR linked to Linear US-283.

