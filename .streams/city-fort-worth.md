# Stream log — city-fort-worth — 2026-08-26

## Claim

- **Stream id:** `city-fort-worth`
- **Leaf files created:**
  - `apps/api/src/spatial/cities/fort_worth.py` (geography + PERMITS spec data)
  - `apps/api/src/producers/field_maps_fort_worth.py` (exports `FIELD_MAP`)
  - `apps/api/tests/unit/test_producers_fort_worth.py` (geometry + producer contract)
- **Spine files edited (interlock phase):**
  - `apps/api/src/spatial/city_registry.py` (CityId.FORT_WORTH, ALIASES, REGISTRY entry, import)
  - `apps/api/src/spatial/cities/__init__.py` (import + __all__)
  - `apps/api/src/config.py` (`arcgis_fort_worth_permits_url` setting)
  - `apps/api/src/serving/dashboard.py` + `apps/dashboard/public/index.html` (METRO_META)

## Intent

Register Fort Worth, TX (Tarrant County) as a **PERMITS-only** city sourced from
the City of Fort Worth "CFW Development Permits Points" ArcGIS FeatureServer
(`https://mapit.fortworthtexas.gov/ags/rest/services/CIVIC/Permits/FeatureServer/0`,
759,008 WGS84 point records, refreshed hourly). Mirrors the Boise thin-ArcGIS
pattern: geometry resolves directly from `SHAPE__Y`/`SHAPE__X` (WGS84), with
ADR-0004 address geocoding retained as a fallback for geometry-less rows. No
311/SLA/DEEDS feeds are registered. Must pass the interlock gate and appear on
the map (METRO_META + byte-synced `index.html`) per the city-registration rule.

## Decisions

- 2026-08-26 — Platform = `arcgis` (CFW Permits FeatureServer, layer 0). Geometry
  arrives in WGS84 via `outSR=4326`; `needs_geocode: True` kept only as fallback.
- 2026-08-26 — Scope = `PERMITS` only (building/mechanical/plumbing/grading). No
  new `FeedType`; reuse `FeedType.PERMITS` with a new `CityId.FORT_WORTH`.
- 2026-08-26 — Watermark = `File_Date`, `order_by='File_Date DESC'`,
  `max_record_count=1000` (matches service MaxRecordCount). Id keys
  `Unique_ID`/`Permit_No`/`OBJECTID`.
- 2026-08-26 — Single division `FORT_WORTH_CORE`; six hand-authored submarkets
  with synthetic signal metrics (same pattern as Boise).

## Current step

Leaf + spine complete. `pytest -m interlock` => 20 passed, 2 failed.
The 2 failures are PRE-EXISTING and unrelated to this hold:
`boston/crime` (ckan:// scheme assertion) and `austin/crime` (literal
`https://data.austintexas.gov/...` URL not a settings field) — both are
registry values not touched here. `fort_worth` is NOT in the failure list.
`tests/unit/test_producers_fort_worth.py` => 4 passed.
`TestDashboardWiring` + `TestSnapshotWiring` => 5 passed (city-registration
rule satisfied: METRO_META + byte-synced `index.html` + snapshot wiring).
`scripts/export_site_facts.py` regenerated `apps/product/public/facts.json`
and `apps/product/public/cities/fort_worth.json` (50 metros).

## Next step

Pre-existing `boston/crime` + `austin/crime` reds are out of scope for this
hold; recommend a separate ticket to point those endpoints at settings fields.
Commit leaf + spine together when the interlock gate is otherwise green for
this city. (dist copies of the product site rebuild via `bun run build` in
`apps/product`.)
