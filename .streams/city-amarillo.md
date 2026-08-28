# Stream log — city-amarillo — 2026-08-28

## Claim

- **Stream id:** city-amarillo
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/amarillo.py`
- **Spine files I expect to need:**
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/serving/dashboard.py` (METRO_META)
  - `apps/dashboard/public/index.html` (byte-sync via `scripts/export_dashboard.py`)

## Intent

Register Amarillo, TX as a new Urban Signal metro (`CityId.amarillo`) with verified public feed coverage, geometry (metro bbox, divisions, submarkets), alias wiring, dashboard METRO_META, and snapshot/export inclusion. The initial feed coverage will register SLA (SNAP Retailers, TX slice) pending a verifiable city permits dataset; do not fake endpoints.

## Decisions

- 2026-08-28 05:58 UTC — Verified City of Amarillo operates MGO Connect for permits; no open building-permits API found on `data.texas.gov` or the city's ArcGIS services. Public permits feed is not verifiable at this time.
- 2026-08-28 06:00 UTC — County-level open deeds/feed endpoints not found for Potter/Randall via public ArcGIS FeatureServers. Proceed with minimal viable registration using SNAP SLA (TX) only, per ADR 0007 multi-source precedent, and complete map wiring (METRO_META + snapshot/tile coverage).

## Current step

Create `amarillo.py` leaf with metro bbox, a minimal divisions catalog, and submarkets; wire `CityId.AMARILLO` into `city_registry.py` (REGISTRY + ALIASES with SLA SNAP TX) and update `cities/__init__.py`. Then update dashboard METRO_META and byte-sync the Worker static copy.

## Next step

Run `pytest -m interlock` from `apps/api` and adjust wiring as needed. If all green, push and open a PR documenting feed verification and current registration scope.

