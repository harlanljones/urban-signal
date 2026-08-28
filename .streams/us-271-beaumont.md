# Stream log — city-beaumont — 2026-08-28

## Claim

- **Stream id:** city-beaumont
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/beaumont.py`
  - `apps/api/tests/unit/test_producers_beaumont.py`
- **Spine files I expect to need:**
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/serving/dashboard.py` (METRO_META)
  - `apps/dashboard/public/index.html` (byte-sync via `python scripts/export_dashboard.py`)

## Intent

Onboard Beaumont, TX as a new Urban Signal metro. Implement the leaf geometry and submarkets first, then register `CityId.beaumont` in the spine with aliases, dashboard METRO_META, and byte-synced dashboard static copy. Register only feeds that exist and are verifiable; use `snap_sla_spec("TX")` if no public permits feed is available.

## Decisions

- 2026-08-28 — Initial claim created. Will verify public feeds (permits, county GIS) and proceed leaf-first.
- 2026-08-28 — Feed verification:
  - Beaumont ArcGIS services discovered:
    - Cityworks Planning & Community Development MapServer: `https://gis.beaumonttexas.gov/arcgis/rest/services/Cityworks/PlanningAndComDev/MapServer?f=pjson` (no permits layer; addresses/zoning/streets only).
    - CityWorks PLL service: `https://gis.beaumonttexas.gov/arcgis/rest/services/CityWorks_PLL/FeatureServer?f=pjson` (addresses, boundaries; no explicit permits layer exposed).
    - Demo open cases: `https://gis.beaumonttexas.gov/arcgis/rest/services/CWDemoPM_OpenCases/MapServer/1?f=pjson` (parcel-join polygons, no issuance/created date column — unsuitable as an incremental permits feed).
  - Texas Open Data (data.texas.gov): no city-specific Beaumont building-permits dataset located (collateral finds include Collin CAD permits and statewide tax permits; neither are Beaumont permits).
  - 311 is SeeClickFix-based; no public Open311 or ArcGIS 311 layer found.
  - Conclusion: no verifiable public building-permits feed at this time; register SNAP SLA (TX slice) only per US-364 precedent.

## Current step

Spine wired: `REGISTRY` + `ALIASES` + `METRO_META` updated and dashboard byte-synced.

## Next step

Run `pytest -m interlock` from `apps/api` (local deps permitting) and open PR with verification notes. Monitor CI interlock suite for containment and dashboard wiring.
