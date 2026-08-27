# Wave 3 Phase-0 probe — Salt Lake City, UT

**Date of probe: 2026-08-27.** Every host, dataset, watermark, and row below
was read live that day. "Live" means a newest-row read (watermark column
descending) confirmed fresh data; Hub/CKAN `modified` metadata and catalog
timestamps were not treated as evidence.

Linear: **US-202** (parent US-192). Stream: `.streams/probe-salt-lake-city.md`.

This re-probe supersedes the 2026-08-25 Hub-only pass in
`west-midwest-city-candidates.md`, which correctly found no transactional
feeds on `slcgov.opendata.arcgis.com` but did not enumerate the city's own
ArcGIS Server, the decommissioned state Socrata catalog, or Accela CivicData.

## Headline

**Platform resolved: ArcGIS Server + ArcGIS Hub.** No Tier-1 or Tier-2 feed.
Salt Lake City is **not Wave-3-ready**.

The 2026-08-25 survey's "GIS/catalog only" verdict on the Hub still holds for
transactional data. The deeper pass found the missing surfaces and then
killed them at row level:

| Surface | What it is | Verdict |
|---|---|---|
| `opendata.utah.gov` | State Socrata catalog (historical SLC permits `3eji-gn2j`, SLCMobile 311 `yga5-qpeq`) | **Decommissioned.** SODA returns `This domain has been decommissioned.` Homepage 400. Central discovery: `Domain not found`. `utah.gov` still links here. |
| `data.slc.gov` | WordPress landing page | Catalog of *links*, not an API. Points at the dead Socrata microsite + GIS Hub. |
| `civicdata.com` / `slc_permits_licenses` | Accela CKAN (building permits, planning, business licenses) | **End-of-life.** Resource IDs 404; HTML still says last updated **2014-11-19**. |
| `slcgov.opendata.arcgis.com` | ArcGIS Hub (~100 datasets) | Planning overlays, parking-permit *areas*, Survey123. No transactional permits/311/SLA/deeds. |
| `maps.slc.gov/server/rest/services` | City ArcGIS Server 11.5 | **The real GIS host.** Accela active-permit layers + Cartegraph requests exist and answer anonymously, but both watermarks are stale. CRS is NAD83 Utah Central State Plane feet (WKID **102743** / EPSG:**3566**). |
| `opendata.gis.utah.gov` | UGRC / SGID Hub | Statewide GIS. Liquor-*store* points (not licensees). Salt Lake LIR parcels (snapshot, no sale fields). |
| Accela Citizen Access | `aca-prod.accela.com/SLCREF` | Search UI for building permits through 1980. No public bulk API. |
| Salt Lake County Recorder | `apps.saltlakecounty.gov/data-services/` | Paywalled ($5/24h token or data packages). Not an anonymous feed. |

Existing `ArcGISClient` would cover every GIS endpoint below; no fifth platform
client is required. Nothing currently satisfies the Wave 3 loosened bar
(live + native geocode **or** address-geocodable).

## Method

1. Fingerprint candidate hosts (Socrata discovery, Hub DCAT, CKAN
   `package_search`/`datastore_search`, ArcGIS Server `/rest/services`,
   homepage HTML).
2. Search Hub catalogs (`slcgov.opendata.arcgis.com`, `opendata.gis.utah.gov`)
   for the four families; enumerate `maps.slc.gov` folders including Accela,
   Cartegraph, MySLC, businessLicensing, Hosted, Public_Maps, transportation.
3. For every survivor: layer metadata (fields, geometry, spatial reference),
   `returnCountOnly`, sample row, newest-row `orderByFields=<watermark> DESC`.
   Windowed `count` with date `where` clauses on this server returned 400 or
   timed out; year-prefix `LIKE` and newest-row reads are the evidence.
4. County/state sides: UGRC LIR, DABS liquor stores, Recorder Data Services,
   SeeClickFix place `salt-lake-city`.

Limits: `maps.slc.gov` was intermittently overloaded during the probe
(Web Adaptor 500 / "Could not access any server machines" / 20s query
timeouts). Newest-row reads that succeeded before the brownout are the
source of truth; failed window counts are noted, not invented.

## Summary table

| Family | Tier | Watermark (newest row) | Geocode path | Register? |
|---|---|---|---|---|
| Permits | **3** — stale active-only snapshot | `OpenedDate` **2025-04-03**; `PermitIssuance` **2025-02-21** | Point geom EPSG:3566 **or** `FULL_` address → ADR 0004 | **no** |
| 311 | **3** — paused ETL (closest miss) | Cartegraph `EntryDate` **2026-06-20**; `created_date` **2026-06-21** | Point geom EPSG:3566 **or** street/locator address → ADR 0004 | **no** |
| SLA | **3** — no live registry | CivicData licenses last row-publish 2014; DABS stores are outlets not licensees | n/a | **no** |
| Deeds | **3** — no transaction stream | LIR `CURRENT_ASOF` **2026-03-26** (parcel snapshot, no sale fields); Recorder paywalled | n/a | **no** |

**Wave-3-ready: no.**

If Cartegraph `EntryDate` starts moving again, that one layer would become
Tier 1 (native point after a State-Plane→WGS84 transform) or Tier 2 (address
geocode, no new client). Re-probe before treating it as a swap candidate.

---

## Permits — Tier 3

Transactional building permits live in Accela (`aca-prod.accela.com/SLCREF`,
also branded SLCPermits.com). That is a citizen search portal, not a bulk
API. Historical scans older than 2007 sit on `webdme.slcgov.com/BldgPermitHistory/`
(HTML). Neither is registerable.

### Candidate: Accela Active Building Permits (row-probed)

- **Endpoint:** `https://maps.slc.gov/server/rest/services/Accela/Accela_Permits_v2/MapServer/1`
- **Name:** Active Building Permits. Companion layers on the same service:
  L0 Active Engineering Permits (197 rows), L2 Active Transportation Permits
  (1,902), L3 Active Planning Petitions (79).
- **Count:** 4,243 (anonymous `where=1=1`).
- **Schema (building):** `PermitNumber`, `PermitType`, `RecordType`,
  `OpenedDate` (date), `AppliedDate`, `PermitIssuance`, `CertificateIssuance`,
  `ApplicationStatus`, `TypeOfWork`, `JobValue`, `TotalSqFt`,
  `NumberOfResidentialUnits`, `FULL_` (site address), `ParcelNumber`,
  `WorkDescription`, `Department`. Accela-shaped (`BLD2022-02051` sample).
- **Watermark:** newest `OpenedDate` = **2025-04-03**; newest `AppliedDate` =
  **2025-04-03**; newest `PermitIssuance` = **2025-02-21**; newest
  `CertificateIssuance` = **2025-04-03**. Engineering L0 newest
  `permitOpenDate` = **2025-11-05**. Transportation L2 newest
  `freshFromSQL_IssuedDate` (planning join) / engineering issued **2025-11-05**.
- **Year-prefix check:** `PermitNumber LIKE 'BLD2023%'` → **985**.
  `BLD2026%` crashed the Web Adaptor; combined with the April 2025 watermark
  this is an **active-window snapshot that has not ingested 2026 issuances**.
- **Geometry:** point, WKID 102743 / latestWkid **3566** (NAD83 Utah Central
  ft). Sample `x,y` ≈ 1.50e6, 7.46e6 — not degrees. SLC GIS documents this
  CRS on `maps.slc.gov/mws/data.htm`.
- **Address:** `FULL_` / house+street parts present → ADR 0004 would work
  *if the feed were live*.
- **Why Tier 3:** "Active" means currently-open records, not a full issued
  stream (closed/finaled permits drop out). Even as a snapshot it is **16
  months stale** on `OpenedDate` and **18 months** on `PermitIssuance` as of
  2026-08-27. Not live.

### Rejected permit-adjacent layers

| Layer | Why not |
|---|---|
| Hub `Permits_GeoPlanner_Datasets` (`…/FeatureServer/0–3`) | Census-block polygons with `Permit_Count` only. No permit id, no date. |
| CivicData `f09a1cf4-…` building / `9ce972c2-…` planning | Datastore 404; package metadata last updated 2014-11-19. |
| Socrata `3eji-gn2j` | Domain decommissioned. |
| `Public_Maps/EngROWPermits` | ROW/utility occupancy (small cell, fiber), not building permits. Queries timed out after the brownout; not pursued as a substitute family. |
| `transportation/accela_Transportation` L0 `currentPermits` | Street-closure / barricade permits. Same Accela source, same likely staleness; count query timed out 20s. |
| `Hosted/SewerPermits` | Utility, not building. |
| Parking Permit Areas (Hub) | Residential parking *zones*, not construction permits. |

**Geocode path if it ever goes live:** native State-Plane point (needs
transform, Boise/Minneapolis precedent) **or** `FULL_` → `needs_geocode=True`
(ADR 0004). Client: existing `ArcGISClient`.

---

## 311 — Tier 3 (closest miss)

City 311 is branded **mySLC** (app + `slc.gov/myslc`). There is no public
Open311 org feed for the city. SeeClickFix place `salt-lake-city` (id 22838)
is live as of 2026-08-27 but the page-1 organizations are **Utah DOT**
roadway tickets (pothole, striping, signals) — 18/20 sampled — not municipal
citizen 311. Do not register.

### Candidate: Cartegraph Requests (row-probed)

- **Endpoint:** `https://maps.slc.gov/server/rest/services/Cartegraph/Request/FeatureServer/0`
  (MapServer twin exists). Capabilities include Query (anonymous read
  succeeded).
- **Count:** 56,444.
- **Schema:** `RequestID`, `Issue` (e.g. "Sidewalk"), `Status`, `Department`
  (e.g. Engineering), `Description`, `EntryDate`, `CloseDate`, `DueDate`,
  `created_date`, `last_edited_date`, `Street`, `AddressNumber`,
  `LocatorStreet`, `LocatorAddressNumber`, `ZipCode`. This is a public-works
  request stream, i.e. the 311 family.
- **Watermark:** newest `EntryDate` = **2026-06-20T23:03:01Z**; newest
  `created_date` = **2026-06-21T05:03:02Z**; newest `last_edited_date` =
  **2026-06-21T05:58:48Z**. `CloseDate` has future values through
  2026-12-22 (scheduled/planned close — do not use as the watermark).
- **Geometry:** point, same WKID 102743 / EPSG 3566. Sample `x,y` ≈ 1.53e6,
  7.45e6.
- **Address:** street + locator fields present.
- **Why Tier 3:** last new row and last edit both stop on **2026-06-21**
  (~67 days before this probe). That is a **frozen ETL**, not a known monthly
  cadence (a lagging-but-live feed would still show July/August rows).
  Windowed `count` with `DATE`/`timestamp` where-clauses returned 400
  ("Query with count request failed") — newest-row is the evidence.

If this layer resumes, it is the swap candidate: existing `ArcGISClient`,
watermark `EntryDate` (or `created_date`), geocode via State-Plane transform
(Tier 1) or ADR 0004 on locator/street (Tier 2). Re-probe ≤72 h before any
registration.

### Other 311-shaped layers — reject

| Layer | Evidence |
|---|---|
| `D6_Constituent_Requests` / Hosted `D6_Constituent_Request` | 90 rows, **native WGS84** `Spatial_X`/`Spatial_Y`. Newest `Entry_Date` **2025-09-10**. Council district 6 only. PII (name, phone, email) on the public layer. |
| Hub `Cit_Req` | "citizen requests received by Bill Brown"; item modified epoch 1478546914000 ≈ 2016-11. ROW complaints, not citywide 311. |
| Hub `ConstituentRequest` | Item modified ≈ 2016-03; polylines. |
| Socrata `yga5-qpeq` SLCMobile | Domain decommissioned. |
| Hosted `MySLC_Homeless_Camp_Reports_2025_YTD_*` | Narrow topic, not general 311. |
| Hosted SLCMobile shopping-cart *prediction* layers | Dated 2022-03-18 in the service name. |

---

## SLA — Tier 3

No live occupational, business-tax, or liquor-license registry.

| Candidate | Evidence |
|---|---|
| CivicData `slc_business_licenses` (`60eadddc-…`) | Last updated **2014-11-19**. Datastore 404. |
| `businessLicensing/businessLicenseAreas4` | Polygon **areas**, not licensees. |
| UGRC `UtahLiquorStores` (`…/UtahLiquorStores/FeatureServer/0`) | **111** DABS state liquor *store* points (`STORENUMBER`, `TYPE=Liquor Store`, native `LAT`/`LONG`). Outlet inventory for planning, not a licensee/SLA stream. Newest-row not meaningful (snapshot of stores). |
| DABS "Licensee List" (`abs.utah.gov/licenses-permits/license-information/`) | Marketing page + online licensing portal. No CSV/JSON bulk URL. Static PDFs (e.g. beer distributors) are not an SLA feed. |
| Hub `license` search | One unrelated Survey123 test item. |

---

## Deeds — Tier 3

No anonymous recorded-document or market-sales API.

| Candidate | Evidence |
|---|---|
| UGRC `Parcels_SaltLake_LIR` (`…/Parcels_SaltLake_LIR/FeatureServer/0`) | 394,610 parcel polygons. Fields: `PARCEL_ID`, `TOTAL_MKT_VALUE`, `BUILT_YR`, `CURRENT_ASOF`, address. **No sale date, price, grantor/grantee, or deed type.** Newest `CURRENT_ASOF` **2026-03-26** (monthly assessor snapshot, not transactions). |
| Basic `Parcels_SaltLake` | Boundary + `OWN_TYPE` only; HB113 stripped sale attributes by design. |
| Salt Lake County Recorder Data Services | Subscription. $5/24-hour token or prepaid packages. Explicitly not a public bulk API. |
| Assessor 2025 CAMA | **For purchase** (`saltlakecounty.gov/assessor/parcel-data/`). |
| `data.slco.org` | DNS does not resolve (same as 2026-08-25). |
| Hub `sales` / `deed` queries | No property-transfer hits (false friends: sales-tax zones, ADA "sales" forms). |

---

## Platform fingerprint (hosts probed)

| Host | HTTP | Platform |
|---|---|---|
| `opendata.utah.gov` | 400 HTML "Domain Decommissioned"; SODA 404 | Dead Socrata |
| `api.us.socrata.com/api/catalog/v1?domains=opendata.utah.gov` | 404 `Domain not found` | — |
| `data.utah.gov` | 200 → `utah.gov/government/data.html` | HTML links, still points at dead Socrata |
| `data.slc.gov` | 200 | WordPress catalog |
| `data.slco.org` | DNS fail | — |
| `slcgov.opendata.arcgis.com` | 200 Hub DCAT | ArcGIS Hub |
| `opendata.gis.utah.gov` | 200 Hub | UGRC SGID |
| `maps.slc.gov/server/rest/services` | 200, v11.5, 40 folders | ArcGIS Server |
| `slcgov.maps.arcgis.com/sharing/rest/services` | 200, 0 services | Empty AGOL org |
| `civicdata.com/api/3/action/package_show?id=slc_permits_licenses` | 403 | CKAN ghost |
| `gis.utah.gov` | 200 | UGRC docs (not a row API) |
| `aca-prod.accela.com/SLCREF` | 200 | Accela ACA UI |
| `seeclickfix.com/api/v2/places?address=Salt Lake City UT` | 200, place 22838 | SeeClickFix (UDOT, not city) |

Correction vs 2026-08-25: `maps.slc.gov` **does** expose Accela and
Cartegraph feature layers. They are real, queryable, and currently **stale**.
The Hub-only "none found" reading was a search miss on the Server directory,
not a missing platform.

---

## Probe contract (if a later re-probe flips a tier)

Use these IDs; do not trust Hub `modified`.

| Family | Endpoint | Watermark | Geometry / geocode | Live bar |
|---|---|---|---|---|
| Permits | `Accela/Accela_Permits_v2/MapServer/1` | `OpenedDate` or `PermitIssuance` DESC; also `PermitNumber LIKE 'BLD2026%'` | EPSG:3566 point or `FULL_` | Newest issuance ≤ ~60 d **and** not active-only if a full issued archive appears |
| 311 | `Cartegraph/Request/FeatureServer/0` | `EntryDate` DESC (ignore future `CloseDate`) | EPSG:3566 point or locator/street | Newest `EntryDate` ≤ ~60 d (currently frozen 2026-06-21) |
| SLA | none | — | — | Need a licensee table, not store points or license *areas* |
| Deeds | none public | — | — | Recorder remains paywalled; LIR is not a deed feed |

Fixture row (permits, captured 2026-08-27): `PermitNumber=BLD2022-02051`,
`OpenedDate=2022-03-14`, `FULL_=5270 W JOHN CANNON Dr`,
`ApplicationStatus=Inspections`, `JobValue=663474`.

---

## Recommendation

**Do not register Salt Lake City in Wave 3.** All four families are Tier 3.
Platform work is done: ArcGIS Server is the host; Socrata is gone; CivicData
is a 2014 fossil. Watch `Cartegraph/Request` — it is the only layer that was
alive in calendar 2026 and would graduate without a new client if the ETL
resumes. Building permits remain trapped in Accela ACA until the city
publishes a current issued-permit FeatureServer (not an "Active" view).
Deeds stay behind the county recorder paywall.
