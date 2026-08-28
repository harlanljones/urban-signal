# Stream log — city-cape-coral-fort-myers — 2026-08-28

## Claim

- **Stream id:** city-cape-coral-fort-myers
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/cape_coral.py`
  - `apps/api/src/producers/field_maps_cape_coral.py`
  - `apps/api/tests/unit/test_producers_cape_coral.py`
- **Spine files I expect to need:**
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py`
  - `apps/dashboard/public/index.html` (byte-sync via `scripts/export_dashboard.py`)

## Intent

Register Cape Coral–Fort Myers, FL as a new Urban Signal metro (`cape_coral`) with verified public permits feed from the City of Cape Coral ArcGIS MapServer (address-only; declare ADR-0004 geocoding) and SNAP SLA fallback for Florida. Deliver leaf geometry (metro bbox covering both Cape Coral and Fort Myers, divisions, submarkets) with containment tests. Wire the spine: add `CityId.cape_coral`, aliases (including Fort Myers variants), `_HANDWRITTEN_REGISTRY` with PERMITS + SNAP SLA, export from `cities/__init__.py`, add `METRO_META` and byte-sync the dashboard static copy, and regenerate product facts. Keep edits additive and isolated to avoid conflicts with concurrent spine work.

## Decisions

- 2026-08-28 — Verified public permits endpoint:
  `https://capeims.capecoral.gov/arcgis/rest/services/OpenData/OpenData/MapServer/1`
  (ArcGIS MapServer table “Building Permits” with columns: `Permit_Number`,
  `issuedate`, `permit_status`, `permitvalue`, address fields `Addr1`, `Street_Type`,
  `City`, `State`, `Zip`, and `lastchangedon`). Register as PERMITS with
  `needs_geocode=True` and `geocode_context="Cape Coral, FL"`.
- 2026-08-28 — SLA: Use `snap_sla_spec("FL")` as fallback per ticket.
- 2026-08-28 — CityId: `cape_coral`; include Fort Myers aliases
  (`fort_myers`, `fort myers`, `cape coral`, `cape coral fort myers`, etc.).

## Current step

Scaffolding leaf module (`cape_coral.py`), field map, and unit test for spatial containment.

## Next step

Update spine (`city_registry.py` CityId/aliases/registry/imports, `config.py` endpoint),
export from `cities/__init__.py`, add `METRO_META` + run `scripts/export_dashboard.py`,
then regenerate product facts and run `pytest -m interlock`.

