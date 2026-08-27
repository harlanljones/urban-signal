# Wave 3 Phase-0 probe: Miami / Fort Lauderdale, FL

**Date of probe: 2026-08-27.** Every host, catalog, watermark, and row below was
probed live that day. Catalog `modified` / Hub item timestamps were never used
as evidence. "Live" means a newest-row read (watermark descending) returned
fresh data. Linear: US-199.

Success criterion (Wave 3, ADR 0004): a feed is registrable if it is *live*
and either natively geocoded **or** address-geocodable. Tier 1 = live + native
geocode; Tier 2 = live + address-only; Tier 3 = stale / no portal / wrong grain.

## Verdict

**Platform: ArcGIS Hub + ArcGIS Server.** Socrata is gone.
**Wave-3-ready: yes (partial, Austin/LA shape).** Register Miami-Dade
**permits (Tier 1)** and **SLA / local business tax (Tier 1 snapshot)**.
Do not register 311. Deeds are a parcel-snapshot last-sale table (Tier 2,
monthly lag + future-date poison) — optional, not required for a first
registration. Fort Lauderdale city GIS is a distinct live portal whose
permits/311/licenses layers are stale; Broward County GeoHub publishes a
live business-tax snapshot (Tier 1) and nothing else in the four families.

This reverses the 2026-08-23 Wave-2 reject (`opendata.miamidade.gov` Socrata
stale; permits catalog stamp 2022-06-01) and the 2026-08-24 rejection-recheck
`INACCESSIBLE` (domain absent from Socrata discovery). The county left
Socrata. The same hostname is now an ArcGIS Hub custom domain.

## Method

1. Resolve portal: Socrata discovery, CKAN `status_show`, ArcGIS Hub v3
   search + DCAT, `gisweb.miamidade.gov` REST 11.1, City of Miami Hub,
   Fort Lauderdale ArcGIS Server, Broward GeoHub. Host fingerprint first,
   then family search.
2. Hub collection search (`/api/search/v1/collections/dataset/items?q=…`)
   per family (building permit, 311, business tax, sales/deed).
3. Row-level verify every survivor: layer metadata, newest-row by watermark
   DESC (or `outStatistics` max when ORDER BY timed out), count, geocoding
   fields, 30-day / 7-day / YTD windows. Only newest-row reads count.

## Platform

| Surface | What it is | Probe result 2026-08-27 |
|---|---|---|
| `https://opendata.miamidade.gov/` | **Correct county portal.** ArcGIS Hub custom domain (HTML title "Open Data Hub Site"). Same catalog as `gis-mdc.opendata.arcgis.com`. | HTTP 200. Hub search API live. Dataset collection **584**. DCAT `/data.json` answers. `/api/catalog/v1` 404 (not Socrata). `/api/3/action/status_show` 404 (not CKAN). |
| `https://gis-mdc.opendata.arcgis.com/` | Canonical Hub hostname | Search + DCAT 200. Org `services.arcgis.com/8Pc9XBTAsYuxx9Ny`. |
| `api.us.socrata.com?domains=opendata.miamidade.gov` | Former Socrata membership | **404 `Domain not found`**. Confirms 2026-08-24 `INACCESSIBLE`. |
| `https://gisweb.miamidade.gov/ArcGIS/rest/services` | County ArcGIS Server 11.1 | Live. Folders include `311` (empty), `EnerGov` (zoning/land-records viewer, not permits), `LandInformation`. `MD_LandInformation`, `BusinessTracker`, `MD_ComparableSales` are the family-relevant services. |
| `https://datahub-miamigis.opendata.arcgis.com/` | **City of Miami** GIS Hub (distinct municipality, 83 datasets) | Live. Permits + frozen 311. No SLA/deeds. Org `services1.arcgis.com/CvuPhqcTQpZPT9qY`. |
| `https://gis.fortlauderdale.gov/` | **City of Fort Lauderdale** GIS (distinct live portal, no Hub) | HTML 200. REST at `/server/rest/services`: `BuildingPermits`, `BusinessLicense`, `ServiceRequest` FeatureServers. |
| `https://geohub-bcgis.opendata.arcgis.com/` | **Broward County GeoHub** (distinct) | Hub search 200, **123** datasets. No permits/311/deeds. Live local-business-tax snapshot. `www.broward.org/OpenData` 404; `opendata.broward.org` / `data.broward.org` DNS fail; `gis.broward.org` connection refused. |
| Miami-Dade Clerk Official Records API | Deeds/consideration | Auth-key gated (`authKey=`). Not an anonymous open feed. |
| `https://bbs.miamidade.gov/` | Property Appraiser bulk CSV | Paid ($50/file), weekly extracts. Not an open API. |

Client fit: existing `ArcGISClient`. No fifth client is required.

## Summary

Metro-level recommendation is **Miami-Dade county** as the `miami` registration
(city-proper is a subset). Fort Lauderdale / Broward are noted because they
are distinct live portals inside the same MSA.

| Family | Jurisdiction | Tier | Watermark (newest-row) | Geocode path | Register? |
|---|---|---|---|---|---|
| Permits | Miami-Dade (GIS) | **1** | `ISSUDATE` = **2026-08-20**; 4,177 since 2026-07-28; 208 since 2026-08-20; 262,348 rows | native point (`esriGeometryPoint`, outSR 4326) + `ADDRESS` | **yes — primary** |
| Permits | Miami-Dade (Hub table) | **2** | `PermitIssuedDate` = **2026-08-25**; 5,928 / 1,120 / 46,190 (30d / 7d / YTD); 139,586 rows | address-only `PropertyAddress` + `City` + `State` → geocode | backup if valuation required (`EstimatedValue` lives here, not on the GIS layer) |
| Permits | City of Miami | **1** | `IssuedDate` = **2026-08-25T20:16Z**; 2,631 / 458 / 21,086; 230,545 rows | native `Latitude`/`Longitude` + point | optional city-proper companion (has `TotalCost`) |
| Permits | Fort Lauderdale | **3** | `SUBMITDT` max **2026-03-16** (~5 months stale); `APPROVEDT` entirely null; `SYNCDATE` sentinel 2030-01-16 | native point + `FULLADDR` | **no** |
| 311 | Miami-Dade Hub | **3** | yearly tables **2013–2023 only**. 2023 table newest `ticket_created_date_time` = **2024-01-01**. No 2024/25/26 item | table has `latitude`/`longitude` (archive only) | **no** |
| 311 | City of Miami | **3** | `ticket_created_date_time` = **2024-08-10** (~2 years stale); 88,078 rows | native lat/lng + point | **no** |
| 311 | Fort Lauderdale | **3** | `REQUESTDATE` = **2022-02-05**; 2,267 rows | native point + `ADDRESS` | **no** |
| SLA | Miami-Dade LBT | **1** | snapshot. `BUSSDATE` can be future (max **2026-09-29**); 5,053 `NEWBUS='Yes'` in 2026 YTD through today; 193,868 rows | native `LAT`/`LON` + point | **yes — snapshot** (`ingestion_mode: snapshot`; filter `BUSSDATE <= today`) |
| SLA | Miami-Dade Certificate of Use | **1** | `USER_ISSUED_DATE` = **2026-08-21**; 184 / 17 / 1,703; 147,074 rows | native point + `USER_BUS_ADDRESS` | optional companion (occupancy/use, not a tax receipt) |
| SLA | Fort Lauderdale licenses | **3** | `ISSUEDATE` entirely null; `ESTABDATE` max **2020-07-06**; `last_edited_date` **2023-03-31** | native point + `SITEADDRESS` | **no** |
| SLA | Broward County tax | **1** | snapshot. `Business_Start_Date` max future **2026-09-07**; 484 since 2026-07-28; 35 since 2026-08-20; 111,263 rows | native point + `Business_Address_Line_1` | optional if the metro includes Broward |
| Deeds | Miami-Dade PaGISView | **2** | per-parcel last-sale snapshot. Newest *real* `DATEOFSALE_UTC` = **2026-08-03** (`PRICE_1` $419k / $1.326M); future poison 2026-09-16 @ $100; 27 sales in last 30d vs 16,442 YTD with `PRICE_1 > 1000`; 943,251 parcels | native point + `TRUE_SITE_ADDR` | optional snapshot (PG County / Columbus pattern). Cadence ~monthly. Exclude futures. Grantor/grantee live on `MD_ComparableSales/MapServer/5` (`GRANTOR_1`/`GRANTEE_1`/`DOS_1` text `YYYYMMDD`), not on PaGISView. |

## Per-family findings

### Permits — Tier 1 (Miami-Dade GIS) / Tier 2 (Hub table) / Tier 1 (City of Miami)

**Primary (register): county GIS points.**

`https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/1`
(`County Building Permits @ BuildingPermit`). `maxRecordCount` 1000.
Metadata on the county GIS self-service page says this layer is the last
three years (rolling), matching the 262k row count.

- Watermark `ISSUDATE` (date). Newest row **2026-08-20** (permit `2026066527`,
  process `C2026046413`, `14310 SW 68 ST`, type `BLDG`, status `A`).
- Native point geometry. No lat/lon attributes; `ADDRESS` is present.
- Windows: 4,177 since 2026-07-28; 208 since 2026-08-20.
- Schema (43 fields): `ID` (permit number), `PROCNUM`, `FOLIO`, `ADDRESS`,
  `TYPE`, `CAT1`–`CAT10`/`DESC1`–`DESC10`, `ISSUDATE`, `RESCOMM`, `PROPUSE`,
  `APPTYPE`, `MPRMTNUM`, `CONTRNUM`, `CONTRNAME`, `BPSTATUS`. **No estimated
  value / square footage on this layer.**
- Caveat: `LSTINSDT` / `RENDATE` / `BLDCMPDT` / `LSTAPPRDT` are **text**
  dates (`00000000` sentinels observed). Do not use them as watermarks.

**Richer address-only publish (Tier 2 backup):** Hub hosted table
`https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/miamidade_permit_data/FeatureServer/0`
("Building Permits Issued By Miami-Dade County - 2 Previous Years to Present").
Type **Table**, no geometry. Watermark `PermitIssuedDate` (**DateOnly**)
newest **2026-08-25** (permit `2026067249`, `18930 SW 357 LN`, `EstimatedValue`
492100). 139,586 rows; 5,928 / 1,120 / 46,190. Geocode via
`PropertyAddress` + `City` + `State` (`needs_geocode=True`,
`geocode_context="Miami-Dade County, FL"`). Prefer this only if valuation
is a hard requirement; otherwise the GIS layer is the spatial contract.

**City of Miami (optional companion):**
`https://services1.arcgis.com/CvuPhqcTQpZPT9qY/arcgis/rest/services/Building_Permits_Since_2014/FeatureServer/0`.
Watermark **`IssuedDate`** (not `BuildingFinalLastInspDate` — a naive first
date-field pick returns inspection edits). Newest issued **2026-08-25T20:16Z**,
native `Latitude`/`Longitude` + point, `TotalCost`, `PermitNumber`,
`DeliveryAddress`, `ScopeofWork`. City-proper only. Hub item `modified`
2025-04-22 was stale metadata; the rows are current.

**Fort Lauderdale (do not register):**
`https://gis.fortlauderdale.gov/server/rest/services/BuildingPermits/FeatureServer/0`.
204,760 point features. `APPROVEDT` is entirely null (`outStatistics` n=0).
Newest `SUBMITDT` **2026-03-16** (sample `BLD-RENEWAL-` / `MEC-RES-2511`).
`last_edited_date` is a bulk stamp **2026-03-17T06:35Z** on every row.
`SYNCDATE`/`LASTUPDATEDATE` max **2030-01-16** (sentinel). Frozen dump, not
a live issuance stream. Transactional permits sit in Accela LauderBuild
(`aca-prod.accela.com/FTL/`), which is a search UI, not a bulk FeatureServer.

### 311 — Tier 3 (no live feed)

Miami-Dade Hub publishes **year-sliced tables**
`data_311_2013` … `data_311_2023` only. Site-scoped search for 2024 / 2025 /
2026 returns zero 311 items. The 2023 table
(`…/data_311_2023/FeatureServer/0`, 343,851 rows, **no geometry** but
`latitude`/`longitude` doubles) newest `ticket_created_date_time` =
**2024-01-01T04:57Z** — it is a closed year archive, not a current feed.

`gisweb.miamidade.gov` folder `311` is empty. `giswspro.miamidade.gov`
`311/311CRM` MapServer is a **reference-layer** service (folio, garbage
routes, flood zones, commissioner districts) — zero ticket layers.

City of Miami
`City_of_Miami_311_Service_Requests_Since_2015/FeatureServer/0` is a
point feed (88,078 rows, native lat/lng) whose newest
`ticket_created_date_time` is **2024-08-10**. Frozen.

Fort Lauderdale `ServiceRequest/FeatureServer/0` newest `REQUESTDATE`
**2022-02-05** (2,267 rows). Dead.

No Open311 / anonymous bulk 311 API was found for the county Answer Center.

### SLA — Tier 1 snapshot (Miami-Dade LBT)

**Primary (register):**
`https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/Local_Business_Tax_Feature_Layer_View/FeatureServer/0`
(same layer as `gisweb.miamidade.gov/arcgis/rest/services/BusinessTracker/MapServer/0`).
193,868 point features, `maxRecordCount` 16000 on the Hub view.

- Native `LAT`/`LON` + point + `BUSADDR`.
- `BUSSDATE` is a **business start date**, not an issuance watermark, and
  sorts into the future (newest **2026-09-29**, `NEWBUS=Yes`, still
  `Paid In Full` / `Active`). Filter `BUSSDATE <= CURRENT_DATE` before
  taking a high watermark. 5,053 new businesses with start dates in
  2026-01-01 … 2026-08-27; only 10 in the last 30 days — this is a
  registry snapshot, not a daily issuance stream.
- Schema: `RECEIPTNO`, `ACCOUNTNO`, `ACCSTATUS`, `PAIDSTATUS`, `RCPTSTATUS`,
  `NEWBUS`, `OWNERNAME`, `BUSNAME`, `BUSADDR`, `CATGRYNAME`, `OCCDESC`,
  `FOLIO`, `YEAR`.
- Register like SF / LA SLA: `ingestion_mode: "snapshot"`,
  `id_keys=["ACCOUNTNO","RECEIPTNO"]`.

**Companion (optional):** Certificates of Use
`CertificateOfUse_New_gdb/FeatureServer/0`. Newest `USER_ISSUED_DATE`
**2026-08-21**, 147,074 points, 184 in 30 days. Occupancy/use authorization
with `USER_DBA` / `USER_BUSINSESS_USE` / `USER_BUS_ADDRESS`. Not a tax
receipt; useful if the metro wants a second SLA-shaped signal.

Certificate-of-occupancy *daily table*
(`certif_of_occupancy_daily_data`, newest `ISSUE_DATE` **2026-08-26**) is
address-only and the sample `FOLIO` field was type-corrupted (datetime in
a folio column). Do not use it as the SLA.

**Fort Lauderdale city licenses:** `BusinessLicense/FeatureServer/0` —
`ISSUEDATE` null on every row, `ESTABDATE` max 2020-07-06, last edited
2023-03-31. Dead.

**Broward County (optional, distinct portal):**
`https://services.arcgis.com/JMAJrTsHNLrSsWf5/arcgis/rest/services/TaxDatabase2021/FeatureServer/0`
("Local Business Tax Database"). 111,263 points. `Business_Start_Date` max
future **2026-09-07**; 484 since 2026-07-28; 35 since 2026-08-20; 5,272 YTD.
Same snapshot-SLA shape as Miami-Dade LBT. Register only if the `miami`
metro bbox includes Broward.

### Deeds — Tier 2 snapshot (optional)

No anonymous transaction stream. The Clerk Official Records API is
auth-gated; PA bulk CSVs are paid.

What exists is a **per-parcel last-sale snapshot**, PG County `qzrv-2tnv`
shape:

`https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/PaGISView_gdb/FeatureServer/0`

- 943,251 point parcels. `DATEOFSALE_UTC` (date) + `DOS_1` (text `YYYYMMDD`)
  + `PRICE_1`. Current owner in `TRUE_OWNER1` (not grantor/grantee of the
  sale). Native point + `TRUE_SITE_ADDR`.
- Naive `ORDER BY DATEOFSALE_UTC DESC` returns **2026-09-16** at `$100`
  (future/sentinel). Real max with `DATEOFSALE_UTC <= DATE '2026-08-27'`
  AND `PRICE_1 > 1000` is **2026-08-03** (folio `1678230150210`, $419,000;
  `17001 COLLINS AVE 1807`, $1,326,000).
- 16,442 sales YTD with `PRICE_1 > 1000`, but only **27** in the last 30
  days — the roll lags ~3 weeks. Treat as monthly cadence, not daily.
- Grantor/grantee/OR book-page live on
  `https://gisweb.miamidade.gov/arcgis/rest/services/MD_ComparableSales/MapServer/5`
  (`GRANTOR_1`, `GRANTEE_1`, `PRICE_1`, `DOS_1` text). `LAST_EDIT_DATE` is
  text; do not ORDER BY it. Same 943k parcel grain.

If registered: `ingestion_mode: "snapshot"`, exclude future `DATEOFSALE_UTC`,
prefer `DOS_1` as typed text watermark (`%Y%m%d`) with a `<= today` cap,
`expected_cadence_days=30`. Not required for a first Miami registration.

## Probe contracts (Tier 1/2 only)

### Miami-Dade permits (GIS) — Tier 1

| Field | Value |
|---|---|
| platform | `arcgis` |
| endpoint | `https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/1` |
| watermark_col | `ISSUDATE` |
| id_keys | `ID`, `PROCNUM` |
| oid_field | `OBJECTID` |
| max_record_count | 1000 |
| geocode | native point |
| field_map sketch | `job_id←ID/PROCNUM`, `issuance_date←ISSUDATE`, `permit_type←TYPE`, `incident_address←ADDRESS`, `bbl←FOLIO`, `status←BPSTATUS`, `borough←RESCOMM` |
| cadence | daily (208 issued 2026-08-20; newest 7 days behind probe day) |
| caveat | rolling ~3-year window; no valuation column |

### Miami-Dade local business tax — Tier 1 snapshot

| Field | Value |
|---|---|
| platform | `arcgis` |
| endpoint | `https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/Local_Business_Tax_Feature_Layer_View/FeatureServer/0` |
| watermark_col | `BUSSDATE` (start date; **filter `<= today`**) |
| id_keys | `ACCOUNTNO`, `RECEIPTNO` |
| extra | `ingestion_mode: snapshot` |
| geocode | native `LAT`/`LON` + point |
| field_map sketch | `license_id←ACCOUNTNO`, `dba←BUSNAME`, `license_type←CATGRYNAME/OCCDESC`, `incident_address←BUSADDR`, `latitude←LAT`, `longitude←LON`, `effective_date←BUSSDATE` |

### City of Miami permits — Tier 1 (optional)

| Field | Value |
|---|---|
| platform | `arcgis` |
| endpoint | `https://services1.arcgis.com/CvuPhqcTQpZPT9qY/arcgis/rest/services/Building_Permits_Since_2014/FeatureServer/0` |
| watermark_col | `IssuedDate` |
| id_keys | `PermitNumber`, `ProcessNumber` |
| geocode | native `Latitude`/`Longitude` |
| field_map sketch | `issuance_date←IssuedDate`, `incident_address←DeliveryAddress`, `valuation←TotalCost`, `permit_type←ScopeofWork/WorkItems` |
| caveat | City of Miami only, not county-wide |

### Miami-Dade last-sale snapshot — Tier 2 (optional)

| Field | Value |
|---|---|
| platform | `arcgis` |
| endpoint | `https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/PaGISView_gdb/FeatureServer/0` |
| watermark_col | `DATEOFSALE_UTC` or text `DOS_1` (`%Y%m%d`) |
| extra | `ingestion_mode: snapshot`; exclude `DATEOFSALE_UTC > today`; `expected_cadence_days: 30` |
| geocode | native point |
| caveat | last sale per parcel, not a deed stream; future dates; ~3-week lag; no grantor on this layer |

## What this is not

- A Socrata city. Wave-2's `opendata.miamidade.gov` reject was against a
  platform the county has left.
- A four-family metro. 311 is unpublished after 2023; FTL city feeds are
  stale; deeds are a snapshot with lag.
- A Fort Lauderdale registration on this evidence. The city portal is
  real and live as a GIS site; the four families on it are not.

Shared Wave-3 roadmap synthesis (`docs/expansion-roadmap-wave-3.md`) is
owned by US-195; this file is the per-city probe contract.
