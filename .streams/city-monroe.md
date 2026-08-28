# Stream log — city-monroe — 2026-08-28

## Claim

- **Stream id:** city-monroe
- **Leaf files I will create/edit:**
  - apps/api/src/spatial/cities/monroe.py
  - apps/api/tests/unit/test_producers_monroe.py
- **Spine files I expect to need:**
  - apps/api/src/spatial/city_registry.py
  - apps/api/src/spatial/cities/__init__.py
  - apps/api/src/serving/dashboard.py
  - apps/dashboard/public/index.html (byte-synced from get_dashboard_html)
  - apps/product/public/facts.json (exported)
  - apps/product/public/cities/monroe.json (exported)

## Intent

Onboard Monroe, LA as a new Urban Signal metro per US-277. Leaf: add spatial geometry and containment-tested submarkets/divisions for Monroe. Spine: register CityId.monroe with SLA (LA slice) only (no verifiable public permits endpoint found); wire METRO_META and ensure snapshot/grid export and dashboard static copy are in sync. Keep edits additive and isolated from other cities.

## Decisions

- 2026-08-28 — Ouachita Parish uses iWorq Citizen Portal for permits; no public ArcGIS/Socrata open-data permits feed found. Register SNAP SLA (LA) only; do not register permits until a verifiable endpoint exists.

## Current step

Implementing leaf module `apps/api/src/spatial/cities/monroe.py` and unit tests for spatial containment.

## Next step

Export in `cities/__init__.py`, then hold the spine: add CityId.monroe + REGISTRY + ALIASES, add METRO_META entry, run facts/dashboard export, and run `pytest -m interlock`.

