# Stream log — city-asheville — 2026-08-28

## Claim

- **Stream id:** `city-asheville`
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/asheville.py`, `apps/api/tests/unit/test_producers_asheville.py`
- **Spine files I expect to need:** `apps/api/src/spatial/city_registry.py`, `apps/api/src/spatial/cities/__init__.py`, `apps/api/src/serving/dashboard.py`, `apps/dashboard/public/index.html` (via `scripts/export_dashboard.py`)

## Intent

Register Asheville, NC as a new Urban Signal metro (`CityId.asheville`) with verified leaf geometry (metro bbox, divisions, submarkets) and containment tests. Prefer a verifiable public municipal feed; absent that, wire SLA via `snap_sla_spec("NC")`. Complete the spine (CityId + ALIASES + REGISTRY + cities/__init__.py + METRO_META + static index.html sync) so Asheville appears on the map per the city-registration rule, and export product facts.

## Decisions

- 2026-08-28 — ArcGIS Hub `data-avl.opendata.arcgis.com` does not expose a clearly verifiable permits/311 FeatureServer suitable for registration in this pass. Proceed with SLA SNAP (NC slice) only; prefer municipal endpoints when proven.

## Current step

Leaf complete (geometry + tests). Beginning spine wiring and dashboard sync.

## Next step

1) Add `CityId.ASHEVILLE`, ALIASES, and REGISTRY entry with `snap_sla_spec("NC")`; 2) import Asheville in `cities/__init__.py`; 3) add METRO_META entry and export `apps/dashboard/public/index.html`; 4) export product site facts.

