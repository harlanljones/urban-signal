# Stream log — city-durham — 2026-08-26

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** city-durham
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/durham.py` (NEW — bbox, divisions, submarkets, PERMITS + DEEDS spec payloads)
  - `apps/api/src/producers/field_maps_durham.py` (NEW — per-city `FIELD_MAP`)
  - `apps/api/tests/unit/test_producers_durham.py` (NEW — geometry + parser contract tests)
- **Spine files I expect to need (phase 3, NOT touched in phase 2):**
  - `apps/api/src/spatial/city_registry.py` (CityId.DURHAM, REGISTRY entry, ALIASES)
  - `apps/api/src/spatial/cities/__init__.py` (import durham symbols)
  - `apps/api/src/producers/field_maps.py` (NO edit — per-city module used instead; documented)
  - `apps/api/src/config.py` (NO edit — `arcgis_durham_permits_url` / `arcgis_durham_deeds_url` already present)
  - dashboard METRO_META + `apps/dashboard/public/index.html` sync

## Intent

Register Durham, NC as a two-feed city (PERMITS + DEEDS) carried by the
existing ArcGIS-backed shared producers via registry + field_map, exactly like
the Boise/San Jose leaf precedent. Both Durham layers are live ArcGIS services
on `webgis2.durhamnc.gov`. No new producer archetype is required.

## Decisions

- 2026-08-26 — VERIFIED live schemas via ArcGIS REST (`?f=pjson`):
  - PERMITS = `Inspections/MapServer/12` "All Building Permits", geometryType
    `esriGeometryPoint` → native lat/lng lifted by ArcGISClient (no field_map
    latitude/longitude binding needed). Key fields: `PermitNum`, `ISSUE_DATE`
    (esriFieldTypeDate, also the layer's timeInfo startTimeField), `BLD_Cost`,
    `BLDB_ACTIVITY`/`PROJECT_TYPE`/`TYPE`, `PmtStatus`, `OBJECTID`.
  - DEEDS = `Property/MapServer/4` "Parcels", geometryType `esriGeometryPolygon`
    → centroid lat/lng lifted by ArcGISClient. Key fields: `REID`, `PIN`,
    `PARCEL_PK`, `DEED_DATE`, `PKG_SALE_PRICE`/`LAND_SALE_PRICE`, `NEIGHBORHOOD`,
    `PROPERTY_OWNER`, `OBJECTID_1` (the OID). No grantor/grantee split exists on
    the assessor parcel table — `party1_grantor` maps to `PROPERTY_OWNER` as a
    best-effort owner; `party2_grantee` left unmapped (producer tolerates None).
- 2026-08-26 — PERMITS + DEEDS only. Durham has no open 311/SLA-quality feed at
  the same tier; register the two that exist (partial-city, LA/Austin style) and
  let `get_dataset` raise a readable error for the rest.
- 2026-08-26 — `oid_field` = `OBJECTID` for permits, `OBJECTID_1` for deeds
  (the parcel layer's true OID is `OBJECTID_1`; bare `OBJECTID` is an Integer).
- 2026-08-26 — Field map mirrors Boise's per-city module pattern
  (`FIELD_MAP` exported, consumed by the registry `extra["field_map"]`); shared
  `field_maps.py` is intentionally NOT edited.

## Current step

Phase 3 build complete: registry, producer, dashboard, generated facts, and
static product wiring are verified. Linear US-154 is completed.

## Next step

Complete.
