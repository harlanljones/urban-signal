# Stream log — us140-houston — 2026-08-25

## Claim

- **Issue:** US-140 — Register Houston, TX — 311 only (partial). Feed: Houston 311 `HOUSTON311_RECENT_SR_SNOW` FeatureServer.
- **Parallel leaf stream. Additive-only; I own the Houston registration and did not touch any other city's registry/dashboard block. I never hand-edited the generated static copy** — `apps/dashboard/public/index.html` was regenerated via the repo's mechanism (`python scripts/export_dashboard.py`, which calls `get_dashboard_html()`).
- **Files changed (working tree, uncommitted):**
  - `apps/api/src/spatial/cities/houston.py` (new geometry module)
  - `apps/api/src/spatial/cities/__init__.py` (import + `__all__` export of `HOUSTON_*`)
  - `apps/api/src/spatial/city_registry.py` (`CityId.HOUSTON`, aliases, `CityRegistration`, import)
  - `apps/api/src/config.py` (`arcgis_houston_311_url`)
  - `apps/api/src/serving/dashboard.py` (selector option, `CITY_CONFIGS`, `CITY_COORDINATES`)
  - `apps/api/tests/unit/test_interlock_gate.py` (`CITY_EXPORT_NAMES` entry, required by the gate)
  - `apps/api/tests/unit/test_producers_houston.py` (new)
  - `README.md` (coverage row + registered-metros count)
  - `apps/dashboard/public/index.html` (REGENERATED static copy — not hand-edited)
  - `.streams/us140-houston.md` (this log)

## Live probe (verified, not trusted)

Probed on 2026-08-26 with curl (uses `https`, `f=json`, `outSR=4326` where noted).

- **Layer metadata** (`.../HOUSTON311_RECENT_SR_SNOW/FeatureServer/0?f=json`): `type: Feature Layer`, `objectIdField: OBJECTID`, `geometryType: esriGeometryPoint`, `maxRecordCount: 2000`.
- **Fields:** `OBJECTID` (OID), `UID` (int), `CASE_NUMBER` (String), `CASE_TYPE` (String), `DEPARTMENT`, `DIVISION`, `STATE_CODE`, `STATUS`, `CREATED_ON` (`esriFieldTypeDate`), `RESOLVE_BY` (Date), `SLA`, `CLOSED_ON` (Date), `ADDRESS`, `STREET`, `CITY`, `STATE`, `ZIP`, `COUNTY`, `LATITUDE`/`LONGITUDE` (`esriFieldTypeDouble`), `TAXID`, `COUNCIL_DISTRICT`, `SUPERNEIGHBORHOOD`, `MANAGEMENT_DISTRICT`, `ETJ`, `SWM_QUADRANT`, `GARBAGE_DAY`, `RECYCLING_*`, `HEAVY_TRASH_*`, `NOTES`.
- **Geometry is native point + native `LATITUDE`/`LONGITUDE` doubles** and agrees with the `outSR=4326` geometry x/y (e.g. row `2600277265`: attributes `LATITUDE=29.60919`/`LONGITUDE=-95.25369`, geometry `x=-95.2536899…`/`y=29.60919000…`).
- **Watermark `CREATED_ON` is epoch-ms**: `1787584644000` = **2026-08-24T15:17:24Z** (newest). Probed 2026-08-26 → ~1.6 d freshness, matches the ticket's "newest 2026-08-24". `CLOSED_ON`/`RESOLVE_BY` are also `esriFieldTypeDate` (epoch-ms).
- **Ordering:** `orderByFields=CREATED_ON DESC` returns the newest rows; the ArcGIS pages on `resultOffset`/`resultRecordCount` with `exceededTransferLimit`.
- **No `SR_NUMBER` field.** The ticket's suggested `SR_NUMBER` id key does **not** exist; the feed's case identifier is `CASE_NUMBER` (String) + `OBJECTID` (OID). id_keys = `["CASE_NUMBER", "OBJECTID"]`.
- **Volume / geocode gap:** `where=1=1` → `count=47100`; `where=LATITUDE IS NOT NULL` → `count=47091` (99.98% geocoded; 9 null). `where=CREATED_ON>=DATE'2026-07-25'` → `count=15435` (~30 d window, consistent with the ticket's 16,478/30 d estimate). No `where` filter needed.

## Decisions

- **`watermark_col="CREATED_ON"`**, `id_keys=["CASE_NUMBER","OBJECTID"]`, `platform="arcgis"`, `producer_key="311"`, `interval_seconds=180.0`, `topic=settings.topic_311`.
- **`extra={"expected_cadence_days":7,"oid_field":"OBJECTID","max_record_count":2000,"field_map":{…}}`** (mirror of the Charlotte 311 spec, the closest single-division ArcGIS-native-coords analog). No `where` filter (0.02% geocode gap); no `endpoint_by_year` (single rolling view, not year-sliced like DC/Minneapolis/Baltimore).
- **`field_map` uses the 311 producer's canonical keys** (uppercase columns the fallback chains can't reach): `incident_id`→`CASE_NUMBER`; `latitude`→`LATITUDE`; `longitude`→`LONGITUDE`; `complaint_type`→`CASE_TYPE`; `created_date`→`CREATED_ON`; `closed_date`→`CLOSED_ON`; `status`→`STATUS`; `incident_address`→`ADDRESS`,`STREET`; `zipcode`→`ZIP`; `borough`→`SUPERNEIGHBORHOOD`,`COUNCIL_DISTRICT`. (The geometry lift to lowercase `latitude`/`longitude` also fires, but the native doubles are authoritative.)
- **No `complaints_311_producer.py` / `field_maps.py` change** — ArcGIS is already wired, and the field-map is purely additive data.
- **Geometry metrics** (real coords): `HOUSTON_METRO_BBOX` = lat 29.20–30.30, lng −95.90 – −94.80 (Houston–Harris County metro); `HOUSTON_DIVISION_BBOXES["HOUSTON_CORE"]` = lat 29.58–30.02, lng −95.65 – −95.10 (city proper), nested inside the metro bbox. Six submarkets inside the core: Downtown, Midtown, Montrose, The Heights, Museum District, Galleria/Uptown.
- **Dashboard + snapshot wiring.** This is a NEW city, so the dashboard three-layer rule applies: selector option + `CITY_CONFIGS` + `CITY_COORDINATES` in `apps/api/src/serving/dashboard.py`, and the synced `apps/dashboard/public/index.html`. `SUPPORTED_CITIES` in `snapshot_builder.py` is derived from `CityId`, so adding `CityId.HOUSTON` covers the KV snapshot export automatically (the Indianapolis/Wichita concurrent agents did the same). The interlock gate's `CITY_EXPORT_NAMES` needed a `CityId.HOUSTON` entry.

## Verification run

From `apps/api` (`.venv`):

- **`pytest -m interlock` → 21 passed, 888 deselected.** Covers closure / completeness (endpoints, job-name uniqueness, arcgis `oid_field`, readable errors) / containment / package-export identity / dashboard wiring (selector + `CITY_CONFIGS` + static-copy freshness, with `"houston"` present) / snapshot wiring for Houston.
- **`test_producers_houston.py` → 4 passed** (geometry self-consistency, arcgis-311-only registration, live-row parse via `Complaints311Producer`, missing-case-id → None).

## Discrepancy / open question

- **Concurrent-stream clobber (resolved).** This stream ran against `apps/api/src/serving/dashboard.py` and `apps/api/src/spatial/city_registry.py` while sibling agents registered Indianapolis and Wichita in the same files, so the working tree changed under me. Twice a sibling edit reverted my block: (1) the Houston `<option>` in the dashboard selector was dropped, and (2) `CityId.HOUSTON` was removed from the enum. Both were re-applied by re-reading the current file and re-editing; the final state is verified intact (grep). If a later sibling run re-clobbers, re-verify `grep -n 'HOUSTON = "houston"'`, `grep -n 'value="houston"'`, and re-run `pytest -m interlock`.
- The static-copy diff contains both my Houston additions and the siblings' Indianapolis/Wichita additions — all generated from source by `export_dashboard.py`, none hand-edited.
- The ticket's suggested id key `SR_NUMBER` does not exist on this layer; implementation uses the real `CASE_NUMBER` (confirmed against metadata + live rows). Watermark geometry/schema otherwise matched the ticket (native doubles, point geometry, `CREATED_ON` epoch-ms, freshness 2026-08-24).
