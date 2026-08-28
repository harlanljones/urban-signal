# Stream log — west-bozeman — 2026-08-28

## Claim

- **Stream id:** `west-bozeman`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/bozeman.py`
  - `apps/api/src/producers/field_maps_bozeman.py`
  - `apps/api/tests/unit/test_producers_bozeman.py`
- **Spine files I expect to need:** NONE

## Intent

Onboard Bozeman, MT as a new metro area with two verified ArcGIS feeds:
(1) Building Permits via BP_Comm_Dev_Report_Data view (hosted AGOL FeatureServer,
24,338 rows, PERMIT_ISSUE_DATE watermark, native point geometry), and (2) BPD
Calls for Service (crime with coordinates per ADR-0004, 5,202 rows, 30-day rolling
window, DATE watermark). Business licenses, 311, and Gallatin County recorded
deeds are Tier 3. SNAP SLA "MT" state-slice fallback is available as a companion
SLA. No spine edits required.

## Decisions

- <2026-08-28T~14:00> — Phase A PROBE: live-verified two official feeds.

  PERMITS — BP_Comm_Dev_Report_Data view (id 787b6105d73a4f0ab4d5ec46ed9c2c17):
  - Endpoint: https://services3.arcgis.com/f4hk1qcfxRJ0L2BU/arcgis/rest/services/BP_Comm_Dev_Report_Data_view/FeatureServer/0
  - Platform: arcgis (hosted AGOL FeatureServer, public)
  - Row count: 24,338
  - Watermark: PERMIT_ISSUE_DATE (esriFieldTypeDate, epoch-ms). Newest: 1787814000000 = 2026-08-27T07:00 UTC
  - Geometry: Native point. outSR=4326 returns WGS84 ({x: -111.0397, y: 45.6796}).
  - Mixed-CRS trap: LATITUDE/LONGITUDE attribute columns are Montana State Plane (NAD83 26912) feet, NOT degrees (e.g. 5058449.43 / 496910.47). These are NOT mapped.
  - Columns: PERMIT_NUMBER, PERMIT_ISSUE_DATE, PERMIT_TYPE, PERMIT_STATUS, VALUATION, APPLICATION_NUMBER, APPLICATION_DATE, APPLICATION_TYPE, APPLICATION_STATUS, APPLICATION_DESC, APPLICATION_SQUARE_FOOTAGE, APPLICATION_YEAR, PLAN_REVIEWED_BY, TENANT_NAME, LOCATION, WORK_CATEGORY_DESC, New_Dwelling_Units, LATITUDE(SP), LONGITUDE(SP), etc.
  - No PII (no owner/contractor columns — this is a public view). needs_geocode=True on LOCATION address.
  - Where-clause on PERMIT_ISSUE_DATE works with ANSI DATE literal.

  PERMITS companion — Internal/Building_Permits/MapServer (id 5e6b6280945e4d94a8ebe13665f40dee):
  - 3 layers: Plan Review (536), Active and Open (985), Certificate of Occupancy (349)
  - Rolling "Past Six Months" window. Not used as primary — BP_Comm_Dev_Report_Data is cleaner.
  - Has PII (contractor/owner columns) — must be dropped if used.

  CRIME (BPD CFS) — BPD_CFS_Public_30_Days (id 959cc6139d7b4342adc3cca17dc26bd2):
  - Endpoint: https://gisweb.bozeman.net/hosted/rest/services/BPD_CFS_Public_30_Days/FeatureServer/0
  - Platform: arcgis (hosted FeatureServer, public)
  - Row count: 5,202
  - Watermark: DATE (esriFieldTypeDate). Newest: 1787814000000 = 2026-08-27T07:00 UTC
  - Geometry: Native point WGS84 ({x: -111.058, y: 45.682}). ADR-0004: crime with coordinates OK.
  - Columns: INCIDENT_NUMBER, ALL_CALL_TYPES, PRIMARY_CODE, PRIMARY_DESCRIPTION, DATE, TIME, RESULT, CASE_NUMBER
  - 30-day rolling window (title "30 Days").

  Tier 3 / NOT REGISTERED:
  - Business licenses (SLA): No license registry found. Rec_Marijuana_Map is a zoning polygon, not a registry.
  - 311/Service Requests: Help Center Call Data is aggregated counts; Potholes is stale (2019); Cityworks requires token.
  - Gallatin County deeds: gallatin.mt.us unreachable; Parcels is CAMA, not recorded deeds.
  - SNAP SLA "MT" state-slice is available as a national fallback (not part of this leaf).

- <2026-08-28T~14:30> — Writing leaf files. 2 verified feeds: PERMITS + CRIME.
  Permits is the primary. Crime is secondary (calls-for-service, coordinates present).

- <2026-08-28T~15:00> — Leaf build complete. 7 divisions anchored on the city's
  official TIF/URD districts (Downtown, Midtown, North Park, Story Mill,
  South Bozeman Tech) + Valley West + Bridger/College (MSU). 10 submarkets.
  Tests pass; ruff clean; interlock stays 24/24.

## Current step

Phase B — LEAF BUILD complete: bozeman.py, field_maps_bozeman.py,
test_producers_bozeman.py written and verified.

## Next step

None — stream complete. Leave REJECT/REGISTER recommendation for orchestrator.

## Outcome

**2 verified feeds, REGISTER (partial):**
1. **PERMITS** — `BP_Comm_Dev_Report_Data_view/FeatureServer/0` (ArcGIS hosted AGOL). 24,338 rows. Watermark PERMIT_ISSUE_DATE newest `2026-08-27T07:00:00+00:00`. Native WGS84 point geometry via outSR=4326. Mixed-CRS trap pinned: LATITUDE/LONGITUDE attrs are MT State Plane feet, unmapped. needs_geocode=True (LOCATION).
2. **CRIME (BPD CFS)** — `BPD_CFS_Public_30_Days/FeatureServer/0` (ArcGIS hosted). 5,202 rows. Watermark DATE newest `2026-08-27T07:00:00+00:00`. Native WGS84 point geometry. ADR-0004 satisfied. 30-day rolling window.

NOT registered (Tier 3, evidence): SLA (no business license registry), 311 (no bulk feed), Gallatin County deeds (recorder not bulk-accessible).

Tests: `pytest tests/unit/test_producers_bozeman.py` → 41 passed. `pytest -k bozeman` → passed (leaf-naming pin is spine-owned, 110 leaves vs 97 pinned — concurrent waves). `pytest -m interlock` → 24 passed (unchanged). `ruff check` on all three files → clean.

## Spine delta

When the spine hold opens (CityId.BOZEMAN + registry + config), add:
- **CityId.BOZEMAN = "bozeman"** to `CityId` enum in `apps/api/src/spatial/city_registry.py`.
- **Aliases**: `"bozeman"`, `"bozeman_mt"`, `"bozeman-mt"`, `"bozeman mt"` → CityId.BOZEMAN.
- **Registry entry** (CityId.BOZEMAN): name "Bozeman, MT", state "MT", center {"lat": 45.6770, "lng": -111.0429}, metro_bbox/division_bboxes/submarkets/divisions imported from `src.spatial.cities.bozeman` (BOZEMAN_METRO_BBOX, BOZEMAN_DIVISION_BBOXES, BOZEMAN_SUBMARKETS, BOZEMAN_DIVISIONS). job_suffix "bozeman".
- **Datasets**: FeedType.PERMITS spec from `BOZEMAN_FEED_SPECS["permits"]` (endpoint BOZEMAN_PERMITS_ENDPOINT, platform arcgis, watermark_col PERMIT_ISSUE_DATE, id_keys [PERMIT_NUMBER, APPLICATION_NUMBER, OBJECTID], topic topic_permits, interval 300.0, producer_key permits, needs_geocode True, geocode_context "Bozeman, MT", oid_field OBJECTID, max_record_count 1000, order_by "PERMIT_ISSUE_DATE DESC", expected_cadence_days 1). FeedType.CRIME spec from `BOZEMAN_FEED_SPECS["crime"]` (endpoint BOZEMAN_CFS_ENDPOINT, watermark_col DATE, id_keys [INCIDENT_NUMBER, CASE_NUMBER, OBJECTID], topic topic_crime, interval 300.0, producer_key crime, needs_geocode False, oid_field OBJECTID, max_record_count 20000, order_by "DATE DESC", expected_cadence_days 1).
- **Config (apps/api/src/config.py)**: no new settings strictly needed (leaf endpoints are inline constants, matching greenville/tucson style); if preferred, add `bozeman_permits_url` / `bozeman_cfs_url` settings and point the specs at them.
- **Recommendation**: REGISTER as a 2-feed partial metro (permits + crime). Do NOT register SLA/311/deeds. Consider adding the SNAP SLA `snap_sla_spec("MT")` companion if a food-retail SLA slice is wanted. Linear comment recommended with this summary + live-probe evidence.