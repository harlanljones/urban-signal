# Wave 3 Phase-0 probe — Albuquerque, NM

**Date of probe: 2026-08-27.** Every host, dataset, watermark, and row below
was read live that day. "Live" means a newest-row read (watermark column
descending / max parsed date) confirmed fresh data; catalog `modified`, HTTP
`Last-Modified`, and ArcGIS `last_edited_date` were never treated as
issuance evidence.

Linear: **US-205** (parent US-192). Stream: `.streams/probe-albuquerque.md`.

This re-probe supersedes the 2026-08-25 Hub-only pass in
`west-midwest-city-candidates.md`, which correctly found `abqopen.opendata.arcgis.com`
private and empty MapServer catalogs, then concluded "no Socrata, no CKAN."
The ticket hint was CKAN. There is **no municipal CKAN**. The missed surface
is the city's Apache file dump at `data.cabq.gov` plus the AGIS REST host
`coageo.cabq.gov`.

## Headline

**Platform resolved: custom CSV dumps + ArcGIS Server. Not CKAN.**

Albuquerque is **Wave-3-ready as a partial metro** (building permits only),
same shape as Boise / Austin / LA. Existing `CSVClient` covers the live
permits file; ADR 0004 covers address geocoding. No fifth platform client.

| Surface | What it is | Verdict |
|---|---|---|
| `data.cabq.gov/api/3/action/*` | Candidate CKAN | **404.** Apache directory listing, not CKAN. |
| `opendata.cabq.gov/api/3/action/status_show` | Candidate CKAN | **404** (nginx). |
| `www.cabq.gov/abq-data` | Plone human catalog | Links at `data.cabq.gov` file dirs + GIS REST. |
| `www.civicdata.com` package_search `albuquerque`/`cabq` | Accela CivicData CKAN | **0 packages.** |
| `data.cabq.gov/business/buildingpermits/BuildingPermitsCABQ-en-us.csv` | Daily UTF-8 CSV dump | **Live.** Newest non-future `IssueDate` **2026-08-26**. |
| `coageo.cabq.gov/.../agis/City_Building_Permits/FeatureServer/0` | AGIS point layer (KIVA/POSSE) | **Frozen.** Max `DateIssued` **2025-01-16**. Do not register. |
| `coageo.cabq.gov/.../CRM_Service_Requests_MIL1` | 311 CRM MapServer | Metadata public; FeatureServer **token required**; MapServer queries **timeout**. |
| `data.cabq.gov/business/busregistration/BusinessRegistrationCABQ-en-us.csv` | UTF-16 TSV dump | **Frozen extract.** Max `MOSTRECENTISSUEDATE` **2025-01-24**; `FILEEXPORTDATE` **2025-08-30**. |
| Bernalillo Clerk RPA / Assessor parcels / `Commercial_Sales` | Deeds | Index UI, ownership snapshot, or **token required**. No transaction stream. |

## Method

1. Fingerprint CKAN (`status_show` / `package_search`) on `data.cabq.gov`,
   `opendata.cabq.gov`, `www.cabq.gov`, CivicData, inventory.data.gov, and
   NM statewide hosts. Socrata discovery `domains=data.cabq.gov` → domain
   not found.
2. Walk `coageo.cabq.gov/cabqgeo/rest/services` folders (`agis`,
   `Call_Center`, `public`, `DMD`, `EHD`, `Hosted`) and
   `assessormap.bernco.gov/server/rest/services`.
3. For every survivor: layer metadata, `outStatistics` max on the date
   field and/or `orderByFields=<watermark> DESC` with `outSR=4326`, plus
   windowed counts. CSV dumps: HTTP `Last-Modified` recorded as a label;
   freshness is the max parsed row date.
4. County side: Bernalillo Clerk Records Public Access (index only),
   Assessor public parcels (no sale date/price), `Commercial_Sales` folder
   (token).

Limits: CRM 311 queries hang even for `returnExtentOnly` / `resultRecordCount=1`.
SeeClickFix `place_url=albuquerque` answered once (newest issue **2026-08-27**)
then Cloudflare-403'd; it is not a municipal bulk feed and is not a
registration candidate (same stance as the Phoenix / Providence probes).

## Summary table

| Family | Tier | Watermark (newest row) | Geocode path | Register? |
|---|---|---|---|---|
| Permits | **2** — live CSV, address-only | `IssueDate` **2026-08-26** (`YYYYMMDD`; 4 future `20261224` sentinels) | SiteNumber+Street+Type+Directional+Zip → ADR 0004 | **yes** |
| 311 | **3** — CRM not queryable; graffiti archive 2020 | n/a (usable) | n/a | **no** |
| SLA | **3** — frozen registration dump | `MOSTRECENTISSUEDATE` **2025-01-24** | address present, but feed is not live | **no** |
| Deeds | **3** — no transaction stream | n/a | n/a | **no** |

**Wave-3-ready: yes, partial (PERMITS only).**

---

## Permits — Tier 2 (register)

Transactional permits now live in **ABQ-PLAN** (replaced POSSE). There is no
public Accela/ABQ-PLAN bulk API. The city still publishes a daily CSV dump
that **is** catching 2026 issuances (`BPR-2026-*`, `BPC-2026-*`, `SOL-2026-*`).

### Register this: daily CSV dump

- **URL:** `https://data.cabq.gov/business/buildingpermits/BuildingPermitsCABQ-en-us.csv`
- **Catalog:** https://www.cabq.gov/abq-data → Building Permits
- **Platform:** `csv` (`CSVClient`). UTF-8, comma-separated. HTTP
  `Last-Modified` **2026-08-27 14:40 GMT**; `Content-Length` 19,838,277.
  File rewrite is not evidence; the row watermark is.
- **Rows:** 62,066. `IssueDate` present on 58,522; empty on 3,544.
  Address parts present on 61,904.
- **Schema:** `ApplicationPermitNumber`, `SiteNumber`, `SiteStreet`,
  `SiteStreetType`, `SiteStreetDirectional`, `SiteZip`, `PlanCheckValuation`,
  `TypeofWork`, `Lot`, `Block`, `Subdivision`, `Description`,
  `TotalSquareFeet`, `OwnerName`, `ContractorName`, `NumberOfUnits`,
  `IssueDate`, `Status`.
- **Watermark:** `IssueDate` text `YYYYMMDD` (ADR 0005:
  `watermark_type="text"`, `watermark_format="%Y%m%d"`). Newest
  **non-future** value **20260826**. Eight newest past rows that day include
  `BPR-2026-00781` (1017 22ND ST NW, Issued, valuation 10000),
  `BPC-2026-00621`, `SOL-2026-00294`. **254** rows with `IssueDate >= 20260728`;
  **43** with `IssueDate >= 20260821`; **221** in calendar August 2026;
  **2,098** in 2026 excluding four future sentinels.
- **Sentinels:** four rows share `IssueDate=20261224` (all `BPR-2025-0176*`
  at 1601 ARROYO VISTA). Exclude `20261224` (and empty) from the high
  watermark. Do not take `max(IssueDate)` raw.
- **Geocoding:** no coordinate columns. Compose
  `{SiteNumber} {SiteStreet} {SiteStreetType} {SiteStreetDirectional}, Albuquerque, NM {SiteZip}`
  and set `needs_geocode=True`, `geocode_context="Albuquerque, NM"`.
- **Status mix:** Complete 33,010 / Expired 25,525 / Issued 2,727 / other
  small. Filter to Issued+Complete (or drop Expired) at registration; do
  not ingest the expired majority as current activity.
- **id_keys:** `["ApplicationPermitNumber"]`.
- **Cadence:** daily dump. `expected_cadence_days: 1`.
- **Client fit:** existing `CSVClient` + `dob_permits_producer`. Headers
  normalize to lowercase (`issuedate`). No new client.

### Do not register: AGIS City_Building_Permits

- **URL:** `https://coageo.cabq.gov/cabqgeo/rest/services/agis/City_Building_Permits/FeatureServer/0`
- Point geometry, WKID **2903** (NAD83 NM Central ft); `supportsDatumTransformation`
  true so `outSR=4326` works. Sample WGS84 (−106.596, 35.185) is inside
  Albuquerque. Addresses `CalculatedAddress` / `FreeFormAddress`.
- **45,382** rows. Max `DateIssued` **2025-01-16**; max `DateEntered`
  **2025-01-09**; **0** rows with `DateIssued` in 2026. `last_edited_date`
  max **2026-07-17** is an ETL stamp on frozen POSSE rows (`DataSource`
  KIVA/POSSE only — no ABQ-PLAN). Hub `modified` / edit dates would have
  lied; the issuance watermark is the evidence.

### Rejected permit-adjacent

| Surface | Why not |
|---|---|
| `agis/POSSE_Casetracking/FeatureServer/0` | Planning cases (site plans, rezones), not building permits. Max `EnteredDate` **2024-12-12**. |
| ABQ-PLAN citizen portal | Search UI. No bulk API. |
| CivicData Accela CKAN | Zero Albuquerque packages. |

### Registration sketch

- `config.py`: `csv_albuquerque_permits_endpoint` =
  `https://data.cabq.gov/business/buildingpermits/BuildingPermitsCABQ-en-us.csv`
- `city_registry.py` `ALBUQUERQUE.datasets[FeedType.PERMITS]`:
  `platform="csv"`, `watermark_col="IssueDate"`,
  `watermark_type="text"`, `watermark_format="%Y%m%d"`,
  `watermark_exclude=["20261224"]`,
  `id_keys=["ApplicationPermitNumber"]`,
  `extra={"needs_geocode": True, "geocode_context": "Albuquerque, NM",
  "expected_cadence_days": 1,
  "field_map": {"permit_id": ["ApplicationPermitNumber"],
  "issuance_date": ["IssueDate"], "job_type": ["TypeofWork"],
  "valuation": ["PlanCheckValuation"], "units": ["NumberOfUnits"],
  "incident_address": ["SiteNumber","SiteStreet","SiteStreetType","SiteStreetDirectional"],
  "zipcode": ["SiteZip"]}}`.
- Filter `Status IN ('Issued','Complete')` in `where` / client predicate.
- Partial city: `get_dataset()` raises for 311 / SLA / DEEDS.

---

## 311 — Tier 3

No registerable municipal 311 bulk feed.

### CRM Service Requests (not usable)

- **MapServer:** `https://coageo.cabq.gov/cabqgeo/rest/services/CRM_Service_Requests_MIL1/MapServer/0`
  ("Service Requests"). Point geom, Web Mercator. Fields include `CRM_ID`,
  `CREATEDTIME`, `UPDATEDTIME`, `CLOSEDTIME`, `QUICK_CODE`, `ADDRESS`,
  `LATITUDE`, `LONGITUDE` (strings), `ZIP_CODE`, `COUNCIL_DISTRICT`.
  `supportsAdvancedQueries` / `Supports OrderBy` advertised. Citizen-311
  categories (pothole, graffiti, abandoned vehicle, SeeClickFix-*) are in
  the renderer.
- **FeatureServer** at the same service name: **HTTP 499 Token Required**.
- Anonymous MapServer queries (`returnCountOnly`, `returnExtentOnly`,
  `orderByFields=CREATEDTIME DESC`, `resultRecordCount=1`) **timed out or
  400**. Metadata HTML is public; the table is not a working anonymous
  bulk API. Not registerable.

### Graffiti subset (dead)

- `Call_Center/SWD_Graffiti_Cases/MapServer/0` — 25,612 rows, native
  lat/lng + point. Newest `CREATEDTIME` **2020-01-24**. Archive.

### Call_Center MapServer

Reference layers (streets, parks, trash routes) for the 311 app, not
service-request records.

### SeeClickFix (not a candidate)

Place `seeclickfix.com/albuquerque` exists. One anonymous
`/api/v2/issues?place_url=albuquerque` read at 12:38 PT returned issue
`22627890` (Pothole, `created_at` **2026-08-27T14:49:47-04:00**, native
lat/lng 35.180 / −106.570). Later calls **Cloudflare 403**. Third-party
intake, not the city's CRM extract; would need a new client. Do not
register.

---

## SLA — Tier 3

City ordinance moved from Business Registration to **Business License**
(ABQ-PLAN) in 2025. The open-data dump is the old registration extract.

- **URL:** `https://data.cabq.gov/business/busregistration/BusinessRegistrationCABQ-en-us.csv`
- UTF-16 LE tab-separated (not the UTF-8 CSV `CSVClient` currently
  assumes). HTTP `Last-Modified` **2026-08-26 18:38 GMT** is a republish
  of frozen rows.
- **109,614** rows. Columns: `REGISTRATIONNUM`, `TYPE`, `STATUS`,
  `LEGALNAME`, `DOINGBUSINESSAS`, `BUSINESSLOCATION`, street parts,
  `ORIGNALISSUEDATE` (sic), `MOSTRECENTISSUEDATE`, `EXPIRATIONDATE`,
  `NAICSCODE`, `FILEEXPORTDATE`.
- **Watermark:** max `MOSTRECENTISSUEDATE` **01/24/2025**. **0** rows with
  a 2026 recent-issue date; 1,042 in 2025. Max `FILEEXPORTDATE`
  **2025-08-30 03:48**. 31,358 `MOSTRECENTISSUEDATE=01/01/1900` sentinels;
  `ORIGNALISSUEDATE` max `20460101` and `EXPIRATIONDATE` max `30240629`
  are also garbage.
- Address-geocodable **if it were live**. It is not. Status mix
  Closed/Active/Expired on a stopped registration system.

No GIS business-license FeatureServer on `coageo` `agis`. ABQ-PLAN license
search is UI-only.

---

## Deeds — Tier 3

No anonymous recorded-deed / sales transaction stream.

| Surface | Finding |
|---|---|
| Bernalillo Clerk RPA (`berncoclerk.gov` Records Public Access) | Grantor/grantee index. No bulk API; images in-office only. |
| `assessormap.bernco.gov/.../GIS/Assessor_Parcels_Public/MapServer/0` | Ownership snapshot: `UPC`, `OWNER`, `SITUSADD`, `DOCNUM`, `TAXYR`, values. **No sale date, no sale price.** City copy on AGIS is "twice a year (Spring and Fall)". |
| `Commercial_Sales` folder | **Token required.** |
| `Enterprise_Assessment_And_Tax/Public_Access_Parcel_Data_EAT` | Parcel layer 0 only. Same snapshot family. |

---

## CKAN fingerprint (negative, complete)

| URL | Result |
|---|---|
| `https://data.cabq.gov/api/3/action/status_show` | 404 HTML |
| `https://data.cabq.gov/api/3/action/package_search?q=permit` | 404 HTML |
| `https://opendata.cabq.gov/api/3/action/status_show` | 404 nginx |
| `https://www.cabq.gov/api/3/action/status_show` | 404 `{"error_type":"NotFound"}` |
| `https://www.cabq.gov/abq-data/api/3/action/package_search` | 404 |
| `https://www.civicdata.com/api/3/action/package_search?q=albuquerque` | 200, **count=0** |
| `https://inventory.data.gov/api/3/action/status_show` | 200 (federal inventory; not CABQ) |
| NM statewide `data.nm.gov` / `catalog.data.nm.gov` | DNS fail |

**CKAN base URL: none.** File host `https://data.cabq.gov/`. GIS host
`https://coageo.cabq.gov/cabqgeo/rest/services`. Human catalog
`https://www.cabq.gov/abq-data`.

Socrata: `api.us.socrata.com/api/catalog/v1?domains=data.cabq.gov` →
`Domain not found`. `q=albuquerque` hits SAMHSA metro reports, not CABQ.

---

## Recommendation

Register Albuquerque as a **partial** Wave-3 city on the permits CSV only.
Do not wire the stale AGIS permits layer, the frozen business-registration
TSV, or the token/timeout CRM 311 service. Re-probe 311 if AGIS ever
publishes an anonymous FeatureServer of `CRM_Service_Requests`, and SLA
if ABQ-PLAN licenses land on `data.cabq.gov` as UTF-8 CSV.
