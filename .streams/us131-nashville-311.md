# Stream log — us131-nashville-311 — 2026-08-25

## Claim

- **Issue:** US-131 — Register Nashville 311 feed (hubNashville ArcGIS)
- **Parallel leaf stream.** Additive-only; I own the Nashville 311 registration and did not touch other cities' blocks. The orchestrator holds the interlock; I did **not** run `pytest -m interlock` or the full suite.
- **Files changed (working tree, uncommitted):**
  - `apps/api/src/config.py`
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/tests/unit/test_producers_nashville.py`
  - `README.md` (Nashville 311 coverage cell)
  - `.streams/us131-nashville-311.md` (this log)

## Live probe (verified, not trusted)

Probed on 2026-08-25 with curl against `services2.arcgis.com/HdTo6HJqh92wn4D8`.

- **Layer metadata** (`.../hubNashville_311_Service_Requests_Current_Year_view/FeatureServer/0?f=json`): name `hubNashville 311 Service Requests Current Year`; `objectIdField: OBJECTID`; `maxRecordCount: 2000`; `geometryType: esriGeometryPoint`, `spatialReference.wkid: 4326` (native WGS84, no transform needed — `outSR=4326` returns the stored coordinates verbatim).
- **Date fields are `esriFieldTypeDate`** (epoch-ms): `Date_Time_Opened`, `Date_Time_Closed` — the Producer's `ArcGISClient` converts them to ISO 8601 UTC.
- **Schema confirmed:** `Request__` (String, id), `GlobalID` (GUID), `OBJECTID` (OID), `Latitude`/`Longitude` (Double), `Status`, `Request_Type`/`Subrequest_Type` (String), `Address`/`City`/`ZIP` (String), `Council_District` (Double). Matches the sweep doc §8.
- **Geocode gap:** `where=1=1` → **185,902** rows; `where=Latitude IS NOT NULL` → **132,905** rows. So 52,997 (28.5%) carry a NULL latitude → 71.5% native geocoded. The `where: Latitude IS NOT NULL` filter makes the stream 100% geocoded (matches the ticket and the Baltimore 311 precedent of registering a published ~25% gap).
- **Freshness:** newest `Date_Time_Opened` in a `orderByFields=Date_Time_Opened DESC` query = `1787639972000` ms = **2026-08-25T06:39:32Z** (today). lastEditDate/current-year view confirmed live today. The re-adjudication called for by the old HJ-119 comment is positive: the Current_Year view carries 2026 rows.
- **Sample row (live, geocoded):** `Request__=2270024`, `GlobalID=f6832cb7-…`, `OBJECTID=186947`, `Latitude=36.0546092`, `Longitude=-86.65544`, `Date_Time_Opened=…972000` (−86.65544/36.0546092 = the geometry x/y, so Point = the native WGS84 coordinate), `Status=Closed`, `Request_Type=Public Safety`, `Subrequest_Type=Control Number Request for Towing`, `Address=1421 Rural Hill Rd, Antioch, TN 37013, USA`, `City=ANTIOCH`, `ZIP=37013`, `Council_District=28`.

## Decisions

- **`watermark_col="Date_Time_Opened"`**, `id_keys=["Request__","GlobalID","OBJECTID"]`, `platform="arcgis"`, `producer_key="311"`, `interval_seconds=180.0`, `topic=settings.topic_311`.
- **`extra={"oid_field":"OBJECTID","max_record_count":2000,"where":"Latitude IS NOT NULL","field_map":{...}}`**. The scheduler reads `extra["where"]` as `base_where` and ANDs it with the incremental watermark clause, so the 28.5% NULL-lat rows are never fetched (mirrors Baltimore 311's published-gap handling).
- **`field_map` keys are the 311 producer's canonical keys:** `incident_id`→`Request__`; `latitude`→`Latitude`; `longitude`→`Longitude`; `created_date`→`Date_Time_Opened`; `closed_date`→`Date_Time_Closed`; `status`→`Status`; `complaint_type`→`Request_Type`+`Subrequest_Type`; `incident_address`→`Address`; `borough`→`Council_District`; `zipcode`→`ZIP`. Capital columns (`Latitude`/`Longitude`) ride the field map, not a generic fallback chain.
- **No `complaints_311_producer.py` change.** ArcGIS is already wired (`self.arcgis` + `"arcgis"` in `_client_for`), the client flattens features + lifts point geometry, and the field-map keys are generic. The `where` clause is applied by the scheduler, not the producer's manual `run_stream`.
- **No config for a `endpoint_by_year`/`rollover`.** The Current_Year view is a single live endpoint carrying 2026 rows; unlike Baltimore's year-slice it needs no rollover map.
- **No dashboard / snapshot wiring.** Nashville is already on the map (selector option + CITY_CONFIGS + static copy — wired for its existing permits/SLA feeds). Adding a feed to an already-listed city does not change the dashboard. `TestDashboardWiring` iterates over *cities* in `REGISTRY`, not per-feed — passes unchanged.

## Verification run

From `apps/api` (`.venv`), focused tests only (not interlock / not full suite — orchestrator runs those at close-out):

- `test_producers_nashville.py` → **passed**.
- 311-producer + registry/config/field-map regression: `test_producers_baltimore.py`, `test_producers_la.py`, `test_producers_sf.py`, `test_field_maps.py`, `test_config.py`, `test_feedtype_taxonomy.py`, `test_registry_cadence.py`.
- `ruff check` on touched Python files → **zero net-new violations**.

## Discrepancy / open question

- None blocking; the live probe matched the sweep doc §8 exactly (geometry type + wkid, 185,902 total / 132,905 geocoded = 28.5% published gap, epoch-ms watermark, `Request__`/`GlobalID`/`OBJECTID` id fields, newest `Date_Time_Opened` today).
- Note: `Council_District` is typed `esriFieldTypeDouble` in the live metadata (a numeric district id), not a string — field mapping uses it as-is for `borough`.
- The `Date_Time_Opened`/`Date_Time_Closed` epoch-ms values are converted client-side to ISO by `ArcGISClient`; the producer's `_parse_datetime` absorbs the `+00:00` suffix. Watermark comparison in the scheduler follows the same arcgis-ISO mechanism Baltimore 311 already uses.
