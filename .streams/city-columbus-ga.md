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
- 2026-08-28 — Additive rebase onto origin/main. First onto ACS tip `26237f0` (stripped leftover `<<<<<<< HEAD` markers main carried). Then again onto `361d265` after PR #31 merged Gainesville — kept Gainesville from main, re-applied Columbus GA only. Ocala already on main is preserved. Did not start Melbourne/Ocala follow-on work.

## Current step

Additive rebase of #32 onto origin/main (`361d265`, includes Gainesville). Shared files took incoming main, then Columbus GA-only lines. Leaf-count pin 94 → 95. Conflict-free against main.

## Next step

Stop after #32 is conflict-free against main and pushed. Do not start Melbourne/Ocala. Merge stays human.

