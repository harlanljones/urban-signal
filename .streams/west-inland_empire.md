# Stream log — west-inland_empire — 2026-08-28

## Claim

- **Stream id:** west-inland_empire (US-222)
- **Leaf files I will create/edit:**
  - apps/api/src/spatial/cities/inland_empire.py
  - apps/api/src/producers/field_maps_inland_empire.py
  - apps/api/tests/unit/test_producers_inland_empire.py
- **Spine files I expect to need:** NONE

## Intent

Verify 1-4 live official open-data feeds for an Inland Empire jurisdiction
(Riverside CA / Riverside County / San Bernardino County candidates on ArcGIS
Hub), then build the leaf trio (city spec, field maps, producer tests) for the
verified anchor. Single-jurisdiction anchor; no spine edits, no commits.

## Decisions

- 2026-08-28 — Hub front-doors: rivco.opendata.arcgis.com search API → 401
  "private org id not accessible"; riversideca.opendata.arcgis.com → same 401;
  sbcounty.opendata.arcgis.com Hub API IS public (org aA3snZwJfFkVyDuP) but its
  catalog has NO building permits / 311 / business license — only Fire
  burn-permit views, static assessor/TRA/parcel layers.
- 2026-08-28 — County of Riverside real door = AGOL org pWmBUdSlVpXStHU6
  ("Riverside County Mapping Portal", countyofriverside.maps.arcgis.com) +
  on-prem ArcGIS Server gis1.countyofriverside.us (OpenData folder =
  static boundaries only). Item "Permits" (cd4aa86406fd49508f45f3714c14196c)
  resolves to gis.countyofriverside.us/arcgis_mapping/rest/services/OpenData/
  General/MapServer/280 = layer **PLUS_ACTIVITIES**: 2,142,939 rows, Accela
  planning+permit cases, APPLIED_DATE watermark, state-plane polygon geometry
  (wkid 102646 — outSR=4326 returns WGS84 rings → client centroid lift).
  LIVE: newest real row OAPT2603552 "NEW SINGLE-FAMILY DWELLING" APPLIED
  1787019074000 = 2026-08-16. TRAP: a CASE_MODULE='PLAN' row carries
  APPLIED_DATE 1798587280000 = 2026-12-26 (future-dated scheduled case) —
  watermark sentinels must be handled/documented.
- 2026-08-28 — RivCo hosted FeatureServers (services1.arcgis.com/
  pWmBUdSlVpXStHU6): **Septic_Permits/FeatureServer/0** — 17,263 rows, points
  w/ LATITUDE/LONGITUDE attrs + geometry (4269→4326 outSR), newest
  SUBMITTED_DATE 1787616000000 = 2026-08-23; **Rivco_Well_Permits/
  FeatureServer/2** (layer id 2, not 0) — 32,218 rows, newest Submitted_Date
  1787184000000 = 2026-08-19. Both env-health permits (same PERMITS family
  slot as PLUS_ACTIVITIES — only one can register).
- 2026-08-28 — City of Riverside AGOL org Fu2oOWg1Aw7azh41: no permits/311/
  business-license feeds (only form surveys, planning views, homeless
  point-in-time maps). **View_CrimesRPD/FeatureServer/4** "Crime (Last Year to
  Date)": 77,234 rows, Web Mercator point geometry (3857), BLOCK_ADDRESS +
  NIBRS fields, newest offendate 1787882766890 = 2026-08-27 (live daily).
  ADR-0004 satisfied (coordinates + block address).
- 2026-08-28 — ANCHOR DECISION: **Riverside County** (strongest verified
  feeds; San Bernardino County has none; City of Riverside only crime).
  Registration follows the miami_dade county exception; docstring must say
  so. Inland Empire spans two counties — San Bernardino documented as absent.

- 2026-08-28 — FEED SET LOCKED (Phase A done):
  1. PERMITS = Riverside County PLUS_ACTIVITIES
     gis.countyofriverside.us/arcgis_mapping/rest/services/OpenData/General/
     MapServer/280, `where=CASE_MODULE = 'PERMIT'` (1,487,546 of 2,142,939
     rows; excludes PLAN-module future-date sentinels), watermark APPLIED_DATE
     newest 1787019074000 = 2026-08-18T02:11:14+00:00 (~10-day publication
     lag; since-8/10 count 852, since-8/1 1,489), maxRecordCount 2000, state-
     plane polygon source (wkid 102646) reprojected server-side via
     outSR=4326 → WGS84 rings → client centroid. TLS valid.
  2. CRIME = City of Riverside View_CrimesRPD/FeatureServer/4 (77,234 rows),
     watermark offendate newest 1787882766890 = 2026-08-28T02:06:06.890000+
     00:00 (live today), WGS84 point geometry out of outSR=4326 + BLOCK_
     ADDRESS (ADR-0004 satisfied), COMMUNITY → borough candidate, maxRecord-
     Count 2000. City-of-Riverside scope inside county-anchored metro —
     documented in docstring.
  Considered NOT registered: Septic_Permits (17,263 rows, watermark
  1787616000000 = 2026-08-25) and Rivco_Well_Permits/2 (32,218 rows,
  1787184000000 = 2026-08-20) — PERMITS-family slot conflict; SB County Hub —
  no transactional feeds; 311/SLA/deeds — none found in either county or the
  city org.
  SPINE DELTA (discovered): gis.countyofriverside.us REJECTS ISO-string date
  comparisons (400 error, verified live) and only accepts ANSI
  `date 'YYYY-MM-DD'` literals — the host must join ANSI_DATE_LITERAL_HOSTS
  in src/producers/watermarks.py during the spine hold. Also
  test_city_leaf_naming.py pins leaf-module count (97 → 98 when
  inland_empire.py lands) and requires INLAND_EMPIRE_* constant names.

## Current step

DONE — leaf trio complete, all gates green, Outcome + Spine delta recorded.

## Next step

Spine hold: register CityId.INLAND_EMPIRE per the Spine delta below (leaf
work complete; no further leaf action).

## Outcome

**Feeds verified (2 registered — NOT a REJECT):**

1. **PERMITS** — Riverside County Accela `PLUS_ACTIVITIES`
   (`https://gis.countyofriverside.us/arcgis_mapping/rest/services/OpenData/General/MapServer/280`,
   platform arcgis, layer id 280 of the OpenData/General MapServer — the
   county's on-prem ArcGIS Server 10.61; the rivco.opendata.arcgis.com Hub
   front-door is a private org, search API 401).
   - Row count: 2,142,939 total; **1,487,546** under the registered filter
     `where=CASE_MODULE = 'PERMIT'` (building/online-permit applications;
     excludes PLAN-module planning cases and their future-date sentinels).
   - Watermark: `APPLIED_DATE`, newest verbatim **1787019074000** =
     2026-08-18T02:11:14+00:00 (batch publication with ~10-day lag; since
     2026-08-10: 852 rows, since 2026-08-01: 1,489 → expected_cadence_days=14).
   - Geometry: parcel polygons, native CA State Plane Zone VI US-ft
     (wkid 102646) → queried with `outSR=4326` (WGS84 rings), client ring-
     centroid lift. No address/valuation/zip columns → cost 0.0, no geocode,
     geometry-less rows drop. maxRecordCount 2000; OID `OBJECTID`. TLS valid.
   - Future-date trap documented: unfiltered layer max APPLIED_DATE
     1798587280000 = 2026-12-29 (PLAN module) — excluded by the module
     filter + US-111 future-watermark guard.
2. **CRIME** — City of Riverside PD `View_CrimesRPD/FeatureServer/4`
   (`https://services.arcgis.com/Fu2oOWg1Aw7azh41/arcgis/rest/services/View_CrimesRPD/FeatureServer/4`,
   "Crime (Last Year to Date)", org Fu2oOWg1Aw7azh41).
   - Row count: **77,234**; live to probe day.
   - Watermark: `offendate`, newest verbatim **1787882766890** =
     2026-08-28T02:06:06.890000+00:00.
   - Geometry: native WGS84 point geometry (outSR=4326) + `BLOCK_ADDRESS`
     → ADR 0004 satisfied; no geocode declared. NIBRS fields; `COMMUNITY`
     = city community-planning-area (borough candidate). maxRecordCount
     2000; OID camelCase `ObjectID`. Rolling last-year-to-date window.

**Probed and REJECTED (evidence):** sbcounty.opendata.arcgis.com Hub (public,
org aA3snZwJfFkVyDuP) — only Fire burn-permit views + static
assessor/TRA/parcel layers, no transactional feeds; City of Riverside org —
no permits/311/SLA/deeds; RivCo `Septic_Permits` (17,263 rows, watermark
2026-08-25) and `Rivco_Well_Permits/2` (32,218 rows, 2026-08-20) — PERMITS
slot conflict; `AllPermits_2015_2019` stale; county `10_Min_Crime`/
`15_Min_Crime` untouched since 2021; Treasurer tax-sale inventories (episodic
auction lists, not deeds); `AssessorTables` empty shell (zero layers/tables);
`data.fontanaca.gov` Hub — zero datasets. 311/SLA/deeds: none found anywhere
probed. PARTIAL registration: PERMITS + CRIME.

**Tests:** test_producers_inland_empire.py **47 passed**; `-k inland_empire`
**49 passed** (incl. naming-gate parametrized case for inland_empire);
`-m interlock` **24 passed** (gate held); ruff clean on all three files.

**Files:** apps/api/src/spatial/cities/inland_empire.py (7 divisions, 14
submarkets, FEED_SPECS, REGISTRATION), apps/api/src/producers/
field_maps_inland_empire.py (PERMITS_FIELD_MAP, CRIME_FIELD_MAP, FIELD_MAP),
apps/api/tests/unit/test_producers_inland_empire.py (3 byte-verbatim
live fixtures per feed through ArcGISClient._flatten_feature + real producer
pipeline). No spine edits, no commits.

## Spine delta

Exact edits the spine hold must make to register `CityId.INLAND_EMPIRE`:

1. **`src/spatial/city_registry.py`**:
   - `CityId.INLAND_EMPIRE = "inland_empire"` member.
   - `_HANDWRITTEN_ALIASES`: `"inland_empire"`, `"inland-empire"`,
     `"inland empire"`, `"rivco"`, `"riverside_county"`, `"riverside county"`.
     Do NOT claim plain `"riverside"` (City of Riverside is a sibling) or
     `"san_bernardino"` (absent feeds — documented, not registered).
   - REGISTRY entry importing from `src.spatial.cities.inland_empire`:
     `INLAND_EMPIRE_METRO_BBOX` (min_lat 33.40, max_lat 34.03, min_lng
     -117.67, max_lng -116.05), `INLAND_EMPIRE_DIVISION_BBOXES` (7),
     `INLAND_EMPIRE_SUBMARKETS` (14), `INLAND_EMPIRE_DIVISIONS` (7),
     name "Inland Empire (Riverside County anchor)", state "CA",
     center {"lat": 33.9803, "lng": -117.3769}, job_suffix "inland_empire".
   - `datasets` from `INLAND_EMPIRE_FEED_SPECS` via the leaf's
     `get_inland_empire_dataset` shape — PERMITS: endpoint
     `INLAND_EMPIRE_PERMITS_ENDPOINT` (config setting suggestion:
     `arcgis_rivco_permits_url`), platform arcgis, watermark_col
     APPLIED_DATE, id_keys ["CASE_ID","OBJECTID"], producer_key "permits",
     where "CASE_MODULE = 'PERMIT'", oid_field "OBJECTID",
     max_record_count 2000, expected_cadence_days 14, interval 300.0,
     field_map PERMITS_FIELD_MAP. CRIME: endpoint
     `INLAND_EMPIRE_CRIME_ENDPOINT` (config: `arcgis_riverside_crime_url`),
     watermark_col offendate, id_keys ["offenseid","ObjectID"],
     producer_key "crime", oid_field "ObjectID", max_record_count 2000,
     expected_cadence_days 7, interval 300.0, field_map CRIME_FIELD_MAP.
   - Import `FIELD_MAP as INLAND_EMPIRE_FIELD_MAP` from
     `src.producers.field_maps_inland_empire` alongside the other per-city
     imports (resolve_field_map needs no further wiring — it reads the spec).
2. **`src/config.py`**: add `arcgis_rivco_permits_url` and
   `arcgis_riverside_crime_url` settings (greenville precedent) or accept the
   leaf-literal endpoints.
3. **`src/producers/watermarks.py`** — REQUIRED: append
   `"gis.countyofriverside.us"` to `ANSI_DATE_LITERAL_HOSTS` (verified live
   2026-08-28: ISO-string watermark comparison returns ArcGIS 400 "Unable to
   complete operation"; ANSI `date 'YYYY-MM-DD'` works — count query
   returned 1,489). Without this the scheduler's incremental poll 400s.
   Mirror the same host in any test pinning that tuple.
4. **`tests/unit/test_city_leaf_naming.py`**: bump pinned leaf-module count
   **97 → 98** (currently red on trunk-after-leaf: `inland_empire.py` adds a
   98th module; the parametrized canonical-constants case for
   `inland_empire` already passes).
5. **City-registration rule** (AGENTS.md): after the spine hold, wire the
   dashboard METRO_META chip + `?city=inland_empire` deep link, snapshot
   export coverage, and res-5 grid-tile manifest entry, and byte-sync
   `apps/dashboard/public/index.html` — a registration is not done until the
   city shows on the map (enforced by TestDashboardWiring/TestSnapshotWiring).
6. **Recommended Linear comment for US-222**: verified + built (not a REJECT)
   — Riverside County anchor (miami_dade county exception; San Bernardino
   documented feedless), 2-feed partial: PERMITS 1,487,546 rows / APPLIED_DATE
   watermark 2026-08-18T02:11:14Z / state-plane polygons via outSR=4326 /
   ANSI-date-only host, CRIME 77,234 rows / offendate 2026-08-28T02:06:06Z /
   WGS84 points per ADR-0004. Leaf trio landed spine-stable (47 tests,
   interlock 24 passed). Spine hold needs the 6 items above.
