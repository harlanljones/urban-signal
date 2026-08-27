# Wave-3 probe — St. Louis, MO (City of St. Louis)

**Date of survey: 2026-08-27.** Every host, dataset, watermark, and row below was
probed live this day. "Newest row" means a row actually read back ordered by its
watermark descending — not a catalog `modified` timestamp. Hub/DCAT `modified`
and file `Last-Modified` were treated as unreliable unless the row watermark
agreed.

Linear: **US-200**. Prior 2026-08-25 survey (`south-heartland-city-candidates.md`)
reported an empty JS-rendered Hub at `stlouis-moa-gis.opendata.arcgis.com` and
rejected the metro. That host is a **private ArcGIS org** (Hub search API returns
401). The real portal is the City of St. Louis ColdFusion catalog.

## Platform

**Custom.** Not Socrata, not CKAN, not ArcGIS Hub-as-catalog.

| Surface | Host | Role |
|---|---|---|
| Open-data catalog (DCAT) | `https://www.stlouis-mo.gov/data.json` (72 datasets; `Last-Modified` 2026-08-27 19:15 UTC) | HTML catalog at `/data/datasets/`; CommonSpot/ColdFusion |
| Generated CSV/JSON exports | `https://www.stlouis-mo.gov/customcf/endpoints/…` | Row-level 30-day building-permit and occupancy dumps |
| Static dumps | `https://www.stlouis-mo.gov/data/upload/data-files/` and `https://static.stlouis-mo.gov/open-data/` | CSB 311 yearly CSVs (zip), excise CSVs, parcel-sales Access MDB |
| ArcGIS REST | `https://maps8.stlouis-mo.gov/arcgis/rest/services` | SLDC permits/licenses (year-sliced / stale), assessor parcel points |
| Permit JSON APIs | `https://www.stlcitypermits.com/API/…` | Live **trades** (electrical/plumbing/demolition), not building permits |
| Open311 | `https://www.stlouis-mo.gov/powernap/stlouis/api.cfm` | GeoReport v2; **API key required** (400 without key) |

Socrata discovery for `data.stlouis-mo.gov` did not resolve a catalog. The 2026-08
Hub hostname `stlouis-moa-gis.opendata.arcgis.com` is the wrong door (401 private
org), which is why the prior sweep found nothing.

Existing clients cover the registrable feeds: **CSVClient** (CSB zip / CF CSV /
excise CSV) and **ArcGISClient** (parcel points, frozen permit year-slices). No
fifth platform client is required. CSVClient will need a zip-member (D3 year file
inside `csb.zip`) for 311; the CF permit export is already a stable CSV URL.

The independent **City of St. Louis** is the target. St. Louis County is a
separate jurisdiction and was not used to fill city gaps.

## Summary

| Family | Tier | Watermark | Newest row | Geocode path | Register? |
|---|---|---|---|---|---|
| **311** | **1** | `DATETIMEINIT` | **2026-08-27 05:54:02** | native `SRX`/`SRY` Web Mercator EPSG:3857 (82,582 / 82,617 = 99.96%) + `PROBADDRESS` | **yes** |
| **PERMITS** | **2** | `ISSUEDATE` | **2026-08-07** | address-only `ADDRESS` (140 / 140) → ADR 0004 geocoder | **yes**, with cadence caveat |
| **SLA** | **2** (narrow liquor) | snapshot (`DATE_EXPIRATION` is not an issue watermark) | file packed **2026-08-27 09:07 UTC** | address `LOCATION` (1,793 / 1,800 ACTIVE) → geocoder | **yes**, Baltimore-style liquor-only |
| **DEEDS** | **3** | `SaleDate` | **2026-02-11** | parcel id → `PARCEL_PTS` point / `SITEADDR` | **no** — 6-month row lag |

**Wave-3-ready: yes**, as a **partial** metro (`st_louis`), same shape as
Austin/LA/San Diego: register 311 + building permits (+ optional liquor SLA).
Do not wait for deeds.

## Per-family findings

### 311 — Tier 1 (register)

Citizens' Service Bureau (CSB). Catalog claimed weekly; the dump is **same-day**.

- **Endpoint:** `https://www.stlouis-mo.gov/data/upload/data-files/csb.zip`
  (`Last-Modified` 2026-08-27 11:04 UTC, 127 MB). Zip of yearly CSVs; current
  member `2026.csv` packed 2026-08-27 06:04, 82,617 rows.
- **Watermark:** `DATETIMEINIT`. Newest row **2026-08-27 05:54:02.043**,
  `REQUESTID=2121679`, `PROBADDRESS=1100 OHIO ST`, status `WEB`.
- **Volume:** ~9–12k requests/month in 2026; 6 rows already on the survey
  morning; 471 on 2026-08-26.
- **Geocoding:** `SRX`/`SRY` are **WGS 84 Web Mercator (EPSG:3857)**, matching
  the dataset page (not the older stlcsb State-Plane assumption). Sample
  `(-10043376.82, 4667655.54)` → `(-90.2212, 38.6219)` at 1100 Ohio St.
  35 rows lack XY (0.04%). `PROBADDRESS` is present on 82,514 rows as a
  geocoder fallback.
- **Open311** at `/powernap/stlouis/api.cfm` is live-documented but returns
  `400 API Key is required` anonymously. Do not register it; the zip is the
  public feed.
- **Quirks:** D3 year-file rollover (`2008.csv`…`2026.csv` inside one zip).
  Catalog `modified=2024-04-04` is stale metadata. `STATUS` mix includes
  `CLOSED` / `CANCEL` / `NEW` / `WEB`.

### PERMITS — Tier 2 (register, cadence caveat)

True **building** permits exist and are current enough to register under the
Wave-3 loosened criterion (live + address-geocodable), but they fail a 7-day
staleness gate as published.

- **Live row-level source:** ColdFusion 30-day export
  `https://www.stlouis-mo.gov/customcf/endpoints/building-permits/building-permits-30-days-export.cfm?permitType=all&dataType=csv`
  (JSON twin with `dataType=json`). Filename on 2026-08-27:
  `Building-Permits-2026-07-28-2026-08-27-all.json`. **140 rows**, all with
  `ADDRESS`. Columns: `ADDRESS`, `PROJECTTYPE`, `STRUCTURETYPE`,
  `APPLICATIONDATE`, `ISSUEDATE`, `DAYSTOISSUE`, `ESTPROJECTCOST`,
  `APPLICATIONDESCRIPTION`. No X/Y.
- **Watermark:** `ISSUEDATE` as `August, 07 2026 00:00:00` text. Newest
  **2026-08-07**; oldest in the file 2026-07-28. Dashboard chrome says the
  window ends today (Aug 27) and claims 140 issued / $13.0 M — the row
  watermark stops 20 days earlier. **`expected_cadence_days=21`** (or hold
  until a ≤7-day re-probe). Year dashboard aggregate: **2,962 issued in 2026**
  / $504 M; the year export is **totals only**, not rows.
- **Geocoding:** address-only → `needs_geocode=True` (ADR 0004). 0/140 blank
  `ADDRESS`.
- **Do not register these ArcGIS layers as the live feed:**
  - `SLDC/Building_Permits/FeatureServer/1` — 9,142 pts, native WGS84 via
    `outSR=4326`, but newest `IssueDate` **2025-03-05** (frozen snapshot;
    `AgeInDays=1` is snapshot-relative).
  - `SLDC/Building_Permits_2025/MapServer/8` — 7,992 pts, typed `IssueDate`,
    newest **2025-12-31**. D3 year-slice with **no 2026 successor** on maps8.
- **Trades (not the PERMITS family):** `stlcitypermits.com` JSON APIs are
  anonymously live — electrical newest `ApprovalDate` **2026-08-26**, plumbing
  **2026-08-27**, demolition application **2026-08-27** with State-Plane
  `ProjectX`/`ProjectY`. `GetBuildingPermits` 404s; `GetAllPermits` timed out
  (60 s, 0 bytes). Do not substitute trades for building permits (Dallas ROW
  lesson). Occupancy 30-day export is also address-only, newest `ISSUEDATE`
  **2026-08-07**, 50 rows — occupancy certificates, not building permits.

### SLA — Tier 2 narrow liquor (register optional)

General business licenses are **not** a live incremental feed.

- `SLDC/Business_License_2024/FeatureServer/0` — 13,283 pts, `Tax_Year=2024`,
  `Date_Business_Started` sentinels (year 4220 / 5202).
- `SLDC/Business_Licenses_as_of_October_2025/FeatureServer/0` — 6,239 pts,
  geocoded snapshot titled "as of October 2025". Not a 2026 stream.
- `LICENSE_COLLECTOR` folder on maps8 returns 499 Token Required.

**Liquor (Excise Commissioner)** is a daily CSV snapshot, Baltimore/Montgomery
precedent:

- `https://www.stlouis-mo.gov/data/upload/data-files/excise-data/excise-permits-licenses.csv`
  (`Last-Modified` 2026-08-27 09:07 UTC). 2,576 rows; **1,800 ACTIVE**
  (776 `RENEWAL`); 1,793 ACTIVE have `LOCATION`.
- No issue-date column. `DATE_EXPIRATION` carries sentinels (1969-12-31,
  3027-07-02). Filter `STATUS_CODE='ACTIVE'` and expiration year 2024–2032
  (1,705 rows). Snapshot ingest (`ingestion_mode='snapshot'`), id `CASE_NUMBER`
  or `ID`, geocode `LOCATION` via ADR 0004.
- Companion `excise-establishments.csv` is a location list without dates.

### DEEDS — Tier 3 (do not register)

Assessor parcel-sales exist but the **transaction watermark is six months
behind**. Daily zip refresh is a catalog trap.

- `https://www.stlouis-mo.gov/data/upload/data-files/prclsale.zip`
  (`Last-Modified` 2026-08-27 12:30 UTC) → `prclsale.mdb` packed 2026-08-26
  22:21. Table `PrclSale`: **192,504** rows. `SaleDate` max **2026-02-11**
  (468 rows in 2026, almost all January; 1 in February). `SaleType=10`
  (open-market valid) has **one** 2026 row. No address; keys `AsrParcelId` /
  `CityBlock`+`Parcel`. `SalePrice` is integer 10,000× dollars
  (`4850000000` ↔ `$485,000.00`).
- `ASSESSOR/PARCEL_PTS/MapServer/0` — 134,335 points, native `outSR=4326`,
  `SITEADDR` + `HANDLE` + `ResSaleDate`/`ResSalePrice`. Newest `ResSaleDate`
  **2026-01-08** (1 row in 2026). Parcel snapshot of last residential sale,
  not a deed stream.
- Recorder of Deeds is Fidlar (`mostlouiscity.fidlar.com`) — search UI, not
  an open feed. Tax-sale polygons (`SLDC/Tax_Sales`) are sheriff auctions,
  not market deeds (`Sales_Date` 2026-06-09).

Join path for a future deeds wave: `PrclSale.AsrParcelId` → `PARCEL_PTS`
point / `SITEADDR`. Not Wave-3.

## Registration contract (Tier 1 / 2)

Exact spec a `city-st-louis` stream would implement. Re-probe ≤72 h before
build (Wave-3 §5.3). Partial city: no DEEDS.

| City (`job_suffix`) | Feeds → datasets (watermark) | Platform | field_map budget | Known quirks that tests must pin |
|---|---|---|---|---|
| **St. Louis** `stl` | 311 `csb.zip` member `{year}.csv` (`DATETIMEINIT`) · PERMITS CF 30-day CSV (`ISSUEDATE`) · SLA excise-permits-licenses.csv (snapshot, `DATE_EXPIRATION` filtered) | csv ×3 | ~12 | 311: EPSG:3857 `SRX`/`SRY` must be projected before H3 (do not ingest as degrees — Boston-SLA lesson); D3 zip year-member rollover. Permits: 30-day rolling window, `ISSUEDATE` is `"Month, DD YYYY HH:MM:SS"` text, 20-day publish lag as of 2026-08-27, no native coords (`needs_geocode=True`). SLA: liquor-only; `STATUS_CODE='ACTIVE'`; drop expiration sentinels yr 1969/3027; no issue date — snapshot diff on `CASE_NUMBER`. |

### DatasetSpec payloads (leaf-local dicts)

```python
STL_311_SPEC = {
    "endpoint": "settings.csv_st_louis_311_endpoint",  # csb.zip
    "platform": "csv",
    "watermark_col": "datetimeinit",
    "id_keys": ["requestid"],
    "topic": "settings.topic_311",
    "interval_seconds": 1800.0,
    "producer_key": "311",
    "extra": {
        "expected_cadence_days": 1,
        "endpoint_by_year": {"2026": "2026.csv", "2027": "2027.csv"},
        "zip_member": True,
        "src_crs": "EPSG:3857",
        "scope": "City of St. Louis CSB service requests (yearly CSV inside csb.zip)",
    },
}

STL_PERMITS_SPEC = {
    "endpoint": "settings.csv_st_louis_permits_endpoint",
    # https://www.stlouis-mo.gov/customcf/endpoints/building-permits/building-permits-30-days-export.cfm?permitType=all&dataType=csv
    "platform": "csv",
    "watermark_col": "issuedate",
    "id_keys": ["address", "issuedate", "applicationdescription"],  # no permit number in the 30-day export
    "topic": "settings.topic_permits",
    "interval_seconds": 1800.0,
    "producer_key": "permits",
    "extra": {
        "expected_cadence_days": 21,
        "rolling_window_days": 30,
        "needs_geocode": True,
        "watermark_format": "%B, %d %Y %H:%M:%S",
        "scope": "City of St. Louis building permits, 30-day rolling CF export (address-only)",
    },
}

STL_SLA_SPEC = {
    "endpoint": "settings.csv_st_louis_sla_endpoint",
    # https://www.stlouis-mo.gov/data/upload/data-files/excise-data/excise-permits-licenses.csv
    "platform": "csv",
    "watermark_col": "date_expiration",
    "id_keys": ["case_number", "id"],
    "topic": "settings.topic_sla",
    "interval_seconds": 1800.0,
    "producer_key": "sla",
    "extra": {
        "expected_cadence_days": 1,
        "ingestion_mode": "snapshot",
        "needs_geocode": True,
        "where": "status_code = 'ACTIVE'",
        "scope": "City of St. Louis excise (liquor) licenses — snapshot, not general business licenses",
    },
}
```

Permit 30-day export has **no permit number**. Composite id is a registration
risk (address+date collisions). Prefer holding permits until a numbered source
appears (2026 ArcGIS year-slice, or a working `stlcitypermits` building
collection) **or** accept composite keys with a documented collision test.
311 does not have this problem (`REQUESTID`).

## Negative / rejected paths

| Path | Result |
|---|---|
| `stlouis-moa-gis.opendata.arcgis.com` Hub search | 401 private org — prior "empty Hub" was this |
| Socrata `data.stlouis-mo.gov` | no discovery mesh membership |
| Open311 without key | 400 |
| `LICENSE_COLLECTOR`, `VSI`, `DEVNET`, `WEB` folders | 499 Token Required |
| `GetBuildingPermits` | 404 |
| `GetAllPermits` | timeout, 0 bytes in 60 s |
| County `data.stlouiscountymissouri.gov` | not used (wrong jurisdiction; prior DNS miss) |

## Method

Hostname + DCAT (`data.json`) + maps8 folder enumeration + row-level
FeatureServer/MapServer `query` (`orderByFields` + `outSR=4326`) + HEAD/download
of catalog distributions + Access parse of `prclsale.mdb` (`PrclSale.SaleDate`)
+ CSV parse of `csb.zip/2026.csv` and excise licenses. Hub `modified` and zip
`Last-Modified` were recorded but never treated as watermarks.

(End of file)
