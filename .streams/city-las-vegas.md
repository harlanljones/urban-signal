# Stream log — city-las-vegas — 2026-08-26

Phase-2 registration stream for Linear US-145: register Las Vegas, NV
(Clark County) for PERMITS + sales/deeds, geocoder-ready per ADR-0004.

## Claim

- **Stream id:** `city-las-vegas`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/las_vegas.py` (NEW — bbox, submarkets, divisions, FeedType specs for PERMITS + DEEDS)
  - `apps/api/src/producers/field_maps_las_vegas.py` (NEW — exports `FIELD_MAP`, imported by `las_vegas.py`)
  - `apps/api/tests/unit/test_producers_las_vegas.py` (NEW — fixtures + assertions; passes WITHOUT spine)
- **Spine files I expect to need (do NOT edit here — reported as deltas):**
  - `apps/api/src/spatial/city_registry.py` (CityId.LAS_VEGAS + REGISTRY entry + ALIASES + imports from `las_vegas.py`)
  - `apps/api/src/spatial/cities/__init__.py` (import line)
  - `apps/api/src/producers/field_maps.py` — NOT edited (per HARD RULE); map rides on `las_vegas.py` specs instead
  - `apps/api/src/serving/dashboard.py` METRO_META + `apps/dashboard/public/index.html` sync (city registration rule)
  - `apps/api/src/config.py` — optional endpoint settings if the orchestrator hoists the URL constants

## Intent

Register Las Vegas / Clark County as a TWO-FEED partial city: PERMITS and
DEEDS are official ArcGIS tables without native geometry, so both are
geocoder-ready under ADR-0004 (`needs_geocode: True`). The leaf is fully
self-contained and testable without any spine edit, following the Austin
two-feed pattern.

## Decisions

- 2026-08-26 — Scope is **Clark County** (countywide), consistent with the
  Reno/Washoe and Austin/Travis pattern: the county feeds cover the metro and
  the registration is named "Las Vegas".
- 2026-08-26 — Stream claimed; registration completed in the orchestrator hold and tracked in Linear US-145.
- 2026-08-26 — **Live audit confirmed official ArcGIS tables.** Permits: `https://services1.arcgis.com/F1v0ufATbBQScMtY/ArcGIS/rest/services/OpenData_Building_Permits_/FeatureServer/0`, `Building_Permits_MV`, address-only, 437,123 rows in the ticket audit, `ISSDTTM` newest 2026-08-14. Deeds: `https://services1.arcgis.com/F1v0ufATbBQScMtY/ArcGIS/rest/services/parcels/FeatureServer/0`, address-only, 302,153 rows in the ticket audit, `SALEDATE` newest 2026-08-01.
- 2026-08-26 — **Field maps use live ArcGIS names.** Permits map `APNO`, `APTYPE`, `WORKTYPE`, `APL_ADDRESS`, `BLDGAPPLSTATUS`, `ISSDTTM`, `DECLVLTN`, `PRCLID`, and `ZIP`; deeds map `PARCEL`, `DOCNO`, `SALEPRICE`, `SALETYPE`, `DOCDATE`, `SALEDATE`, `ADDRESS1`, and `ZIP`. Both specs declare ADR-0004 geocoding with `geocode_context="Las Vegas, NV"`.

## Validation

- Registry, config, spatial exports, dashboard `METRO_META`, snapshot wiring, and static copy are complete.
- Las Vegas focused tests: 26 passed.
- Shared ArcGIS/deeds regression tests passed.
- `pytest -m interlock`: 22 passed.
- `SITE_FACTS_OK (48 metros)`, `SITE_BUILD_OK (58 routes)`, `FACTS_FRESH`, and `SITE_CONTENT_OK` are green.
- Linear US-145 is resolved.
