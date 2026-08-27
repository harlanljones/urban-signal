# Wave 3 Phase-0 probe — City of Fort Lauderdale, FL

**Date of probe: 2026-08-27.** Every host, dataset, watermark, and row below
was read live that day. Catalog `modified` / Hub `item.modified` is recorded
only as a label; **freshness evidence is always newest-row-by-watermark**.

Linear: **US-199** (Miami / Fort Lauderdale split). Stream:
`.streams/probe-fort-lauderdale.md`. City GIS only — does not replace the
Miami-Dade or Broward county probes.

Success criterion (Wave 3 / ADR 0004): live **and** (native geometry **or**
address-geocodable). Tiers: **1** live + native geocode; **2** live +
address-only; **3** stale / absent / wrong family.

## Headline

**Platform resolved: ArcGIS Server + Enterprise portal + a thin ArcGIS Hub
catalog.** No Socrata, no CKAN. The gallery at `gis.fortlauderdale.gov` is
not basemap-only — it fronts two REST catalogs with real FeatureServers —
but **three of the four feed families are frozen extracts**, and the one
live sales signal is a **Broward Property Appraiser parcel snapshot** hosted
on city GIS, covering 19 municipalities.

**Fort Lauderdale is not a viable Wave-3 leaf.** Register Broward County
(or nothing) rather than a city-only FTL metro. The existing `ArcGISClient`
would cover every GIS endpoint below; no fifth platform client is required
for the city feeds. Nothing currently satisfies the Wave 3 loosened bar for
a city registration.

## Platform

| Host | What it is | Probe |
|---|---|---|
| `gis.fortlauderdale.gov` | City GIS gallery (JSAPI 3.15; title "City of Fort Lauderdale GIS") | HTML 200. Apps gallery, not a tabular catalog. Config points at `fortlauderdale.maps.arcgis.com`. |
| `gis.fortlauderdale.gov/server/rest/services` | **ArcGIS Server 10.9.1** (the live FeatureServer catalog) | `BuildingPermits`, `BusinessLicense`, `ServiceRequest`, `TaxParcel` (+ ~70 reference layers). |
| `gis.fortlauderdale.gov/arcgis/rest/services` | **ArcGIS Server 10.6.1** (app MapServers) | Folders `BuildingPermitTracker`, `CodeCaseTracker`, `NeighborRequest`, `Accela`, `Qalert`, `FranchisePermit`. Accela folder = Charlotte-style **reference/area layers only**, no permit records. |
| `gis.fortlauderdale.gov/portal` | ArcGIS Enterprise portal ("Fort Lauderdale GIS Portal") | `/sharing/rest/search` resolves the same 10.9.1 FeatureServers. |
| `fortlauderdale.opendata.arcgis.com` (= `fortlauderdale.hub.arcgis.com`) | ArcGIS Hub, **80** dataset items, org `82LxCEC4N4AxRpwc` | `q=permit` hits Building Permits (same frozen FeatureServer). `q=311` = **0**. Business licenses are on Server, not in the Hub keyword hit. |
| `services2.arcgis.com/82LxCEC4N4AxRpwc` | AGO-hosted layers for the Hub org | 27 services: fire zones, wifi, stormwater parcel *views*, Survey123. No transactional permits/311/SLA/deeds. |
| `data.fortlauderdale.gov` / `opendata.fortlauderdale.gov` | — | NXDOMAIN. |
| Placeholder Hub hosts (`opendata-fortlauderdale`, `gis-fortlauderdale`, `cityoffortlauderdale`, `ftlgis`.opendata.arcgis.com) | empty / 401 | Not the catalog. |
| `aca-prod.accela.com/FTL/` | Accela Citizen Access | Search UI 200. No public bulk API. Same Charlotte lesson. |
| `seeclickfix.com/fort-lauderdale` | SeeClickFix public place | Live, thin, not the city GIS extract. See §311. |

`www.fortlauderdale.gov` returned Akamai 403 from this probe environment;
city-website pages were not used as evidence.

## Summary

| Family | Dataset | Newest watermark | Geocode | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `BuildingPermits/FeatureServer/0` | `SUBMITDT` = **2026-03-16**; last GISCLOUD edit **2026-03-17** | native point, NAD83 FL East ft (WKID **102658** / **2236**); `FULLADDR` | **0** submitted ≥ 2026-04-01 (cliff after 2,299 in March) | **3** — frozen |
| **311** (city GIS) | `ServiceRequest/FeatureServer/0` | `REQUESTDATE` = **2022-02-05** | native point, Web Mercator 3857; `ADDRESS` | **0** since 2022-02; layer is Jan 5–Feb 5 2022 only (2,267 rows) | **3** — frozen |
| **311** (SeeClickFix, not GIS) | `seeclickfix.com/api/v2/issues?place_url=fort-lauderdale` | `created_at` = **2026-08-27** | native `lat`/`lng` on 1,299 / 1,299 | **105** created ≥ 2026-07-28 | **not a city feed** — thin public place, new client |
| **SLA** | `BusinessLicense/FeatureServer/0` | `ESTABDATE` = **2020-07-06**; `last_edited_date` = **2023-03-31** | native point, Web Mercator 3857; `SITEADDRESS` | `ISSUEDATE` **0 / 21,849** non-null; newest `EXPIREDATE` **2021-09-30** | **3** — frozen 2019–20 BTR dump |
| **DEEDS** | `TaxParcel/FeatureServer/0` last-5 sales | `SALEDATE1` = **2026-08-14**; layer edit **2026-08-19** | native polygon (2236) **and** `LATITUDE`/`LONGITUDE` WGS84 | **459** countywide / **217** `PARCELCITY='FORT LAUDERDALE'` in 30d | **3 as FTL leaf** — live, but Broward PA snapshot, 19 cities, mutating last-5 not a transaction log |

**Wave-3-ready as a city leaf: no.** The only currently-publishing tabular
signal on city GIS is last-sale-on-parcel, and that layer is a Broward-wide
assessor extract. Do not register FTL to fill the Miami/Fort Lauderdale
slot; let the Broward county probe own sales if it finds a cleaner stream.

## Method

1. Fingerprint `gis.fortlauderdale.gov` HTML → `scripts/config0.js` /
   `gisApps.js` (AGO gallery groups; no FeatureServer URLs in markup).
2. Common REST paths: `/arcgis/rest/services` (10.6.1) and
   `/server/rest/services` (10.9.1) both 200. Hub DCAT-style
   `/api/search/v1/collections/dataset/items` on
   `fortlauderdale.opendata.arcgis.com` (80 items). Portal
   `/sharing/rest/search`. AGO org hosted services list.
3. Family keyword searches (permit, 311, license, deed/sale, qalert,
   business, service request) against Hub + portal + REST folder names.
4. For every survivor: layer metadata (fields, geometry, WKID),
   `returnCountOnly`, sample row, `orderByFields=<watermark> DESC`.
   Window counts used Esri `DATE '…'` literals (epoch-ms `where` 400 on
   these services). Sentinel dates (`SYNCDATE` / some `LASTUPDATEDATE` =
   2030-01-16) excluded from watermarks.
5. Side checks: Accela ACA `/FTL/`, SeeClickFix place JSON + v2 issues API,
   QAlert folder (sanitation polygons only).

---

## Permits — Tier 3 (frozen Accela extract)

- **URL:** `https://gis.fortlauderdale.gov/server/rest/services/BuildingPermits/FeatureServer/0`
  (Hub item "Building Permits"; identical 204,760-row copy on
  `…/arcgis/rest/services/BuildingPermitTracker/BuildingPermitTracker/MapServer/0`).
- **Rows:** 204,760. Point geometry, WKID 102658 / latest 2236 (NAD83 State
  Plane Florida East, US survey feet). `FULLADDR` present on the newest
  page. Native geocode — **if it were live this would be Tier 1**, not
  address-only.
- **Watermark:** `SUBMITDT` (Date Submitted). Newest **2026-03-16**
  (`PERMITID` `BLD-RENEWAL-` / `PLB-GEN-2603` / `MEC-GEN-2603`, status
  Plan Set Submitted). Oldest sampled `SUBMITDT` **2021-03-18**.
  `APPROVEDT` is **null on every row** (0 results `IS NOT NULL`).
  `LASTUPDATEDATE` cannot be used: newest values include **2030-01-16**
  and **2028-05-30** sentinels; after dropping ≥2027 the remainder still
  cliffs in March 2026.
  `last_edited_date` is a **bulk GISCLOUD stamp 2026-03-17 06:35:11 UTC
  on the newest page** — republish, not a row event.
  `SYNCDATE` is uniformly 2030-01-16.
- **Cadence (monthly `SUBMITDT`):**

  | Month | Count |
  |---|---|
  | 2025-10 | 4,047 |
  | 2025-11 | 3,461 |
  | 2025-12 | 3,596 |
  | 2026-01 | 4,001 |
  | 2026-02 | 4,219 |
  | 2026-03 | 2,299 (through the 16th) |
  | 2026-04 … 2026-08 | **0** |

  Hard freeze, not lag. Pipeline last ran ~2026-03-17.
- **Status mix (whole layer):** Complete 97,346 / Issued 25,483 / Void
  16,400 / Open 10,721 / Awaiting Client Reply 11,072 / Plan Set
  Submitted 9,280 / In Process 9,148 / … 59 `PERMITTYPE` values
  (General, Revision, WalkThru, Electrical, Plumbing, Residential, …).
  This *was* a full Accela building-permit universe, not a single-family
  slice.
- **Do not register.** Accela Citizen Access (`aca-prod.accela.com/FTL/`)
  is the transactional system of record and has no bulk REST. Franchise /
  ROW permits (`FranchisePermit/MapServer`, polyline, `last_edited_date`
  **2026-08-26**) are live but **utility franchise**, not building
  permits — out of the four-family contract.

## 311 — Tier 3 (GIS frozen; SeeClickFix is not a substitute)

### City GIS `ServiceRequest` — frozen 2022 window

- **URL:** `https://gis.fortlauderdale.gov/server/rest/services/ServiceRequest/FeatureServer/0`
  (same 2,267 rows on
  `…/arcgis/rest/services/NeighborRequest/Requests/MapServer/0`).
- **Not in Hub** (`q=311` matched 0). Portal keyword `ServiceRequest`
  also 0 — the layer is on the REST root but unpublished as a Hub dataset.
- **Watermark:** `REQUESTDATE`. Newest **2022-02-05 17:49 UTC** (Open
  "Sanitation Missed By Contractor"). Oldest **2022-01-05**. Monthly
  counts: 2022-01 = 1,920; 2022-02 = 347; every later month **0**.
- **Geocoding:** native point, WKID 3857; `ADDRESS` + `CITY`. Types on
  the newest page are sanitation / yard waste / noise — citizen 311, not
  police CFS. Volume (~70 rows/day in that 2022 window) looks like a
  real QAlert extract that **stopped publishing**.
- **QAlert folder** on 10.6.1 is reference only (`Trash_Information`,
  `Parcels`, crew polygons). Hub `QAlert Sanitation Schedule` is pickup
  *areas*, not requests.

### SeeClickFix place — live but thin, not GIS

`GET https://seeclickfix.com/api/v2/issues?place_url=fort-lauderdale`
returns **1,299** issues, newest `created_at` **2026-08-27 00:16 ET**
("Sea Turtle Lighting", native lat/lng 26.177, −80.097), **105** created
in the 30 days to 2026-08-27, geometry on 1,299 / 1,299. Oldest row in
the place dump is 2009. ~3.5 public issues/day is an order of magnitude
below the 2022 QAlert extract and below a city-scale 311. This is a
public SeeClickFix place, not the municipal system of record, and it
would need a new client. **Do not register as FTL 311.**

## SLA — Tier 3 (2019–20 business-tax dump)

- **URL:** `https://gis.fortlauderdale.gov/server/rest/services/BusinessLicense/FeatureServer/0`
  (portal search `license` hits this FeatureServer; Hub `q=business`
  does **not** — keyword miss).
- **Rows:** 21,849, all `BUSINESSCITY=Fort Lauderdale`. Point geometry,
  WKID 3857. `SITEADDRESS` present. Native geocode, frozen.
- **Watermark:** `ISSUEDATE` is **null on 21,849 / 21,849**. Newest
  `ESTABDATE` **2020-07-06**. Newest `EXPIREDATE` **2021-09-30** (Florida
  BTR cycle). Newest `last_edited_date` **2023-03-31** (republish of old
  rows — `ESTABDATE` still 2019–20). Year counts on `ESTABDATE`: 2019 =
  19,920; 2020 = 1,920; 2021+ = 0.
- **Do not register.** No live business-tax / occupational-license feed
  on city GIS or Hub.

## Deeds / sales — not an FTL leaf (live Broward PA snapshot)

- **URL:** `https://gis.fortlauderdale.gov/server/rest/services/TaxParcel/FeatureServer/0`
  (Hub "Tax Parcel"; point twin `TaxParcelPoint`, 195,107 rows each).
- **What it is:** current-ownership tax parcels joined to CAMA, with
  **last five sales** as attributes (`SALEDATE1`…`5`, `DEEDTYPE1`,
  `ACTAMOUNT1`, `STAMPAMNT1`, book/page). Snippet names BCPA (Broward
  County Property Appraiser). This is **not** a recorded-documents
  stream: when a parcel sells again, `SALEDATE1` mutates and the prior
  sale shifts to `SALEDATE2`. Backfill parity on a watermark of
  `SALEDATE1` is unverifiable.
- **Coverage is not Fort Lauderdale.** `PARCELCITY` on 195,107 rows:

  | City | Parcels |
  |---|---|
  | FORT LAUDERDALE | 86,674 |
  | POMPANO BEACH | 24,781 |
  | OAKLAND PARK | 19,583 |
  | LAUDERDALE LAKES | 12,795 |
  | LAUDERHILL | 9,022 |
  | + 14 others (Tamarac, Wilton Manors, Unincorporated, …) | remainder |

- **Watermark:** `SALEDATE1` newest **2026-08-14** (WD / DRR). Layer
  `last_edited_date` **2026-08-19**. Monthly `SALEDATE1` in 2026 stays
  non-zero through August (1,030–1,507/month Jan–Jul; 224 through Aug 14).
  30-day window `DATE '2026-07-28'` … `'2026-08-27'`: **459** all cities,
  **217** Fort Lauderdale, **108** FTL `DEEDTYPE1='WD' AND ACTAMOUNT1>1000`.
- **Geocoding:** polygon WKID 2236 **and** populated `LATITUDE`/`LONGITUDE`
  WGS84 (86,674 / 86,674 FTL rows). Sample FTL WD 2026-08-12:
  `1741 NE 4 AVE #F5`, $525,000, 26.15013, −80.14154. Native — ADR 0004
  not required.
- **Why Tier 3 as an FTL leaf:** the feed is live and geocoded, but (1)
  it is a county assessor extract the city happens to host, (2) a city
  registration would either leak Pompano/Tamarac/… or require a
  `PARCELCITY` filter that still is not a deed log, (3) last-5 mutation
  breaks the deeds watermark contract. **Broward-county-only** is the
  right home if the county probe finds this (or a better recorder feed).
  Do not stretch this into a Fort Lauderdale DEEDS registration.

Code-case tracker (`CodeCaseTracker/CodeCase/MapServer/0`, 66,436 rows,
newest `INITDATE` **2019-10-03**, zero rows 2020+) is a frozen code-
enforcement archive, not 311 and not deeds.

---

## Verdict vs Broward-county-only

| Question | Answer |
|---|---|
| REST / Hub base | **Yes.** Primary: `https://gis.fortlauderdale.gov/server/rest/services`. Secondary MapServers: `https://gis.fortlauderdale.gov/arcgis/rest/services`. Hub: `https://fortlauderdale.opendata.arcgis.com` (80 items, same Building Permits + Tax Parcel). Portal: `https://gis.fortlauderdale.gov/portal`. |
| Permits | Tier **3** — native points, frozen 2026-03-16 |
| 311 | Tier **3** on GIS (frozen 2022-02-05). SeeClickFix live but thin / unofficial |
| SLA | Tier **3** — native points, frozen 2020/2021 BTR |
| Deeds | Live last-sale on parcels, **Broward-shaped**, not an FTL leaf |
| Register FTL as a Wave-3 city? | **No.** Broward-county-only (or Miami-Dade + Broward counties, no FTL city row). |

Re-probe permits if `SUBMITDT` starts moving again — the schema is already
Tier-1-shaped (point + address + Accela IDs). Until the March 2026 cliff
clears, it is a stale extract, not a feed.
