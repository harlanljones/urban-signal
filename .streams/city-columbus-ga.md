# Stream log — city-columbus-ga — 2026-08-28

## Claim

- Stream id: city-columbus-ga (US-294)
- Leaf files I will create/edit:
  - apps/api/src/spatial/cities/columbus_ga.py
  - apps/api/tests/unit/test_spatial_columbus_ga.py
- Spine files I expect to need:
  - apps/api/src/spatial/city_registry.py
  - apps/api/src/spatial/cities/__init__.py
  - apps/api/src/config.py
  - apps/api/src/serving/dashboard.py
  - apps/dashboard/public/index.html (byte-synced via scripts/export_dashboard.py)

## Intent

Onboard Columbus, GA as a new Urban Signal metro (`CityId.columbus_ga`) with verified ArcGIS permits and SNAP SLA fallback. Register REGISTRY + ALIASES, wire METRO_META and snapshot/grid coverage, export product facts, and byte-sync the dashboard static copy — all per the city-registration rule.

## Decisions

- 2026-08-28 — Public permits feed verified at `ccggisprod.columbusga.org` MapServer layer 0 (“Residential”) with `Issued` date, `OBJECTID` OID, native point geometry (WKID 2240; client outSR=4326 path). Using layer 0 as primary; scheduler does not poll companion_endpoints today.
- 2026-08-28 — SLA via SNAP state slice for GA (`snap_sla_spec("GA")`).

## Current step

Create `columbus_ga.py` leaf with bbox, divisions, submarkets, REGISTRATION; then export in `cities/__init__.py`.

## Next step

Add CityId/ALIASES/REGISTRY entry + settings endpoint; wire dashboard METRO_META and regenerate static copy; export product facts; run `pytest -m interlock`.

