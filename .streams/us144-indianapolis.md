# Stream log — us144-indianapolis — 2026-08-25

## Claim

- **Issue:** US-144 — Register Indianapolis, IN — 311 only (partial) `ODP_RIMACServiceRequests`
- **Parallel leaf stream.** Additive-only; I own the Indianapolis registration only and did not touch another city's registry/dashboard block. The orchestrator holds dispatch; I ran the interlock gate for this city as instructed.
- **Files changed (working tree, uncommitted):**
  - `apps/api/src/spatial/cities/indianapolis.py` (new)
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py`
  - `apps/dashboard/public/index.html` (regenerated via `scripts/export_dashboard.py`)
  - `README.md` (Indianapolis row + metro count 27 → 28)
  - `apps/api/tests/unit/test_producers_indianapolis.py` (new)
  - `.streams/us144-indianapolis.md` (this log)

## Live probe (verified, not trusted)

Probed 2026-08-25 with curl against `gis.indy.gov/server/rest/services/OpenData/ODP_RIMACServiceRequests/FeatureServer/0`.

- **Layer metadata** (`?f=json`): name `ODP_RIMACServiceRequests`; `type: Feature Layer`; `geometryType: esriGeometryPoint`; `objectIdField: OBJECTID`; `maxRecordCount: 2000`; `currentVersion: 11.3`.
- **Count:** `where=1=1` → **718,616** rows (ticket said 718,401 — live feed, still growing, not a discrepancy).
- **Schema confirmed:** `SERVICEREQUESTID` (String), `EXTERNALSERVICEREQUEST` (String/null), `SERVICENAME`, `ACTIVITY`, `SERVICEDEPARTMENT` (String), `ADDRESS` (String), `TOWNSHIP` (String/null), `ZIPCODE` (Integer), `COUNCILDISTRICT` (Integer/null), `REQUESTEDDATETIME` (esriFieldTypeDate), `UPDATEDDATETIME` (esriFieldTypeDate), `CLOSEDDATETIME` (esriFieldTypeDate), `STATUS` (String), `ORIGIN` (String), `LAT`/`LONG_` (esriFieldTypeDouble), `OBJECTID` (OID).
- **Watermark is epoch-ms:** `REQUESTEDDATETIME` is `esriFieldTypeDate` → ArcGISClient converts to ISO 8601 UTC.
- **Freshness:** newest `REQUESTEDDATETIME` via `orderByFields=REQUESTEDDATETIME DESC` = `1787543627000` ms = **2026-08-24T03:53:47Z** (matches the ticket's "newest 2026-08-24").
- **Geometry + native coords:** Point geometry x/y matches `LAT`/`LONG_` verbatim on the sample rows; both served with `outSR=4326` (native WGS84).
- **id fields:** no `REQUESTID` column exists on the feed — the ticket's `REQUESTID`/`OBJECTID` example is a stub. Effective id chain is `SERVICEREQUESTID` + `OBJECTID` (confirmed from probe).
- **Sample row (live, OBJECTID 842538):** `SERVICEREQUESTID=26-00124733`, `SERVICENAME=Streets and Alley Repair`, `ACTIVITY=Depression`, `ADDRESS=1496 W EPLER AVE, INDIANAPOLIS, 46217`, `ZIPCODE=46217`, `STATUS=open`, `LAT=39.68581414`, `LONG_=-86.18702727` (= geometry x/y).

## Decisions

- **`watermark_col="REQUESTEDDATETIME"`**, `id_keys=["SERVICEREQUESTID","OBJECTID"]`, `platform="arcgis"`, `producer_key="311"`, `interval_seconds=180.0`, `topic=settings.topic_311`.
- **`extra={"expected_cadence_days":7,"oid_field":"OBJECTID","max_record_count":2000,"field_map":{...}}`**. Native `LAT`/`LONG_` are uppercase and ride the field map, not a generic fallback; the ArcGISClient geometry lift lands on lowercase `latitude`/`longitude` via `setdefault`, but the field map wins for the coordinates.
- **`field_map` keys are the 311 producer's canonical keys:** `incident_id`→`SERVICEREQUESTID`+`EXTERNALSERVICEREQUEST`; `created_date`→`REQUESTEDDATETIME`; `closed_date`→`CLOSEDDATETIME`; `status`→`STATUS`; `complaint_type`→`ACTIVITY`+`SERVICENAME`; `incident_address`→`ADDRESS`; `borough`→`COUNCILDISTRICT`; `zipcode`→`ZIPCODE`; `latitude`→`LAT`; `longitude`→`LONG_`.
- **No `where` clause / geocode-gap filter.** Every probed row carries native `LAT`/`LONG_` (and point geometry), so no published null-coordinate gap needs the Nash/Virginia `IS NOT NULL` guard; rows are always point-geocoded.
- **No `complaints_311_producer.py` change.** ArcGIS is already wired (`self.arcgis` + `"arcgis"` in `_client_for`); field-map keys are generic.
- **311-only registration.** PERMITS (Accela ACA no-bulk), SLA (INBiz SOS paid), DEEDS (nightly parcel snapshot no sales) all stay unregistered; `get_dataset` raises readable errors for them.

## Dashboard wiring (city registration rule)

Added to the map in the same spine hold as the REGISTRY entry: selector `<option value="indianapolis">`, `CITY_CONFIGS.indianapolis` (center/zoom/divisions/presets), and `CITY_COORDINATES.indianapolis`. Regenerated the synced worker static copy via the repo mechanism so `TestDashboardWiring` passes:

    python scripts/export_dashboard.py

`TEST_WORKER_STATIC` now carries `"indianapolis"`. `TestSnapshotWiring`/SUPPORTED_CITIES derives from `CityId` automatically, so `indianapolis` is exported without a snapshot_builder edit.

## Verification run

From `apps/api` (`.venv`), as instructed:

- `pytest -m interlock` → **passed** (all 7 invariant classes, incl. `TestContainment`, `TestDashboardWiring`, `TestPackageExportsMatchRegistry`, `TestSnapshotWiring`).
- `pytest tests/unit/test_producers_indianapolis.py` → **passed**.
- `ruff check` on touched Python files → **zero net-new violations**.

## Discrepancy / open question

- **id_keys diverges from the ticket's example.** The ticket suggested `["REQUESTID","OBJECTID"]` "if present"; the probe found **no `REQUESTID` column** — the real business key is `SERVICEREQUESTID` (the RIMAC request number, e.g. `26-00124733`), with `EXTERNALSERVICEREQUEST` available as a secondary foreign id. Registered as `["SERVICEREQUESTID","OBJECTID"]`. Not blocking — confirmed from the live schema.
- **Row count 718,616 vs ticket 718,401** — live feed, still growing; not a discrepancy.
