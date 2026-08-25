# Ohio Valley & Tennessee Valley metro research — Cleveland, Toledo, Dayton, Akron, Knoxville, Chattanooga

**Date of survey: 2026-08-25.** Every host, dataset, watermark, and row count below was
probed live this day. The six metros were left out of the Socrata sweep because none
of their candidate domains are Socrata members (verified against
`api.us.socrata.com/api/catalog/v1` for 19 candidate domains — zero hits). They run
ArcGIS Hub, ArcGIS Enterprise/ArcGIS Online orgs, and one Hub-hosted CSV pipeline.
"Live feed" means a newest-row read (watermark column descending) confirmed fresh
data; Hub `modified` metadata was never used as evidence. Only newest-row reads count.

## Method

For each metro: probe candidate portal hosts directly (`data.<city>.gov`,
`*.opendata.arcgis.com`, `<org>.maps.arcgis.com`, city GIS hostnames); detect platform
by content (Hub DCAT feed at `/api/feed/dcat-us/1.1.json`, ArcGIS REST services
directory, CKAN/Socrata API paths); search catalogs for the four feed families
(building permits, 311 service requests, business licenses, property sales/deeds);
row-level verify every survivor — geometry type, watermark column, freshest-row date,
total rows, recent-30-day count, and geocoding fields. ArcGIS queries used
`where=1=1&orderByFields=<WATERMARK>+DESC&resultRecordCount=1`; epoch-ms watermarks
converted with UTC datetime. Wildcard `*.opendata.arcgis.com` shells return HTTP 200
with an empty DCAT catalog — a 200 alone proves nothing.

## Summary

| Metro | Correct host(s) | Platform | Register | Not register |
|---|---|---|---|---|
| Cleveland, OH | `data.clevelandohio.gov` + `services3.arcgis.com/dty2kHktVXHrqO8i` | ArcGIS Hub + FeatureServer | **permits, 311, sales/deeds**; contractor licenses (provisional) | general business licenses |
| Chattanooga, TN | `data.chattanooga.gov` + `pwgis.chattanooga.gov` | ArcGIS Hub (CSV items) + FeatureServer | **permits (CSV)**, **sales/deeds (parcels FS)** | 311 (stale 2025-10-28), licenses |
| Dayton, OH | `maps.daytonohio.gov/gisservices` | ArcGIS Enterprise | **311** (rolling-90-day caveat) | permits, licenses, deeds |
| Toledo, OH | `data.toledo.gov` + `gis.toledo.oh.gov` | ArcGIS Hub + Server | 311 (provisional — state-plane coords) | permits, licenses, deeds |
| Akron, OH | — (AkronGIS AGOL org; Summit County fiscal office layers) | AGOL fragments | **none** (Summit sales = yearly snapshot) | all four live feeds |
| Knoxville, TN | `services1.arcgis.com/QWaOgwdmpqI9HUzf` (KnoxGIS org) | ArcGIS FeatureServer | **none** (permits frozen Feb 2026) | 311, licenses, deeds |

## Per-metro findings

### Cleveland, OH — register permits + 311 + sales/deeds

Portal: `data.clevelandohio.gov` ("City of Cleveland Open Data", ArcGIS Hub, 277
DCAT entries); all datasets hosted on org
`https://services3.arcgis.com/dty2kHktVXHrqO8i/arcgis/rest/services`.
Cuyahoga County also runs a healthy ArcGIS Enterprise at
`https://gis.cuyahogacounty.gov/server/rest/services` (CCFO parcel fabric, CCPC
planning) — its Taxparcels layer carries no sale fields, so it is redundant given
the city's own parcel-analytics feed.

- **Permits — live.** `Building_Permits/FeatureServer/0` ("Issued Building Permits"):
  199,359 point features. Watermark `ISSUE_DATE`; newest 2026-08-14; 1,115 rows in
  30 days but 0 in the trailing week — the issued-permit sync lags roughly 10 days
  (`FILE_DATE` caps at the same 2026-08-14). Fields include `PERMIT_TYPE`,
  `PERMIT_SUBTYPE`, `JOB_VALUE`, `TOTAL_FEES_PAID`, `PARCEL_NUMBER`, `WARD`,
  contractor name/license. Point geometry verified (WGS84 via `outSR=4326`,
  sample -81.58/41.45).
  Companion feeds on the same org: `Building_Permit_Application_Tasks`
  (215,172 rows; newest `FILE_DATE` 2026-08-24; 291 in 7 days — the freshest permit
  signal in the metro, includes full Accela task/status history JSON) and
  `Demolition_Permits` (11,004 rows; newest `ISSUED_DATE` 2026-08-12; only 4 in
  30 days — low volume but current).
- **311 — live.** `Data_311/FeatureServer/0`: 172,462 rows. Watermark
  `requested_datetime`; newest 2026-08-24 23:54 UTC; 9,592 rows in 30 days,
  1,817 in 7 days. Native `lat`/`long` doubles populated on the newest row
  (41.4504/-81.7843) plus point geometry, `service_name`, `agency_responsible`,
  address, `parcelpin`. A frozen historical twin covers 2017-06→2024-02.
- **Sales/deeds — live.** `Parcel_Analytics_(PUBLIC_DRAFT_)/FeatureServer/0`
  ("Property Insights"): 162,849 parcel polygons. Watermark `last_transfer_date`;
  newest 2026-08-21; 1,052 transfers in 30 days. `grantor`/`grantee`/
  `book_page` (deed book-page reference) populated (sample: DSV SPV3 LLC →
  3S FUND I LLC, "B 138 P 24"). Polygon geometry; owner/mailing/address columns.
- **Licenses — no general SLA feed.** `Active_Contractor_Registrations`
  (Accela contractor licenses): 3,159 rows; newest `B1_APPL_STATUS_DATE`
  2026-08-14 — live but **address-only** (no geometry) and scoped to contractors,
  not all businesses. Rental Registrations (landlord registry) exists as an
  adjacent housing-signal source.

### Chattanooga, TN — register permits (CSV) + sales/deeds

Portal: `data.chattanooga.gov` ("City of Chattanooga Hub", 103 DCAT entries);
CHATTGIS org `services2.arcgis.com/OIAIimblRxPs0xxc` (392 services) and city
ArcGIS Enterprise `https://pwgis.chattanooga.gov/arcgis/rest/services`.

- **Permits — live via CSV item.** "All Permits" Hub item
  (`9937e99e93de467eae5f592061c2672c`) downloads as a 76.8 MB CSV
  (`.../api/download/v1/items/<id>/csv?layers=0`): 215,369 rows, Accela-style
  schema (`permitnum`, `applieddate`, `issueddate`, `statusdate`, `permitclass`,
  `estprojectcostdec`, contractor block, `pin`). Max `issueddate` **2026-08-24**
  and max `applieddate` 2026-08-23 at probe time — refreshed daily; ~770–1,100
  permits/month across 2026. **Geocoded:** `latitude`/`longitude` +
  `location_wkt` (POINT) populated on data rows.
  **Trap:** the hosted FeatureServer twin `Permits_Permitted_to_Contractor`
  (same org, point geometry) is **frozen** — max `issueddate` 2024-07-01, max
  `applieddate` 2022-09-29, 5,544 rows. Consume the CSV item, never the FS.
  The Hub download API requires `?layers=0` and rejects the bare item id.
- **311 — stale.** "311 Service Requests" CSV item: 68,572 rows, created range
  2025-04-15 → **2025-10-28** — ten months dead at probe time. No live
  FeatureServer alternative surfaced in the org catalog.
- **Sales/deeds — live.** `pwgis.chattanooga.gov/arcgis/rest/services/Misc/Parcels/
  FeatureServer/0`: 85,772 parcel polygons with rolling transfer history —
  `SALE1DATE`…`SALE4DATE` + `SALE1CONSD` (consideration/price) + book/page/type.
  Newest `SALE1DATE` 2026-08-10, `SALE2DATE` 2026-08-07, `SALE3DATE`
  2026-08-03; `OWNERNAME1`/`ADDRESS` present. Note the sale-date literal is
  epoch-ms — plain date-string comparisons return query errors.
- **Licenses — no feed.** `Chattanooga_Business_Points` is an Infogroup-style
  business list (NAICS/SIC, no date columns); "Registered Suppliers" is a
  purchasing vendor app. Neither is a business-license registry.

### Dayton, OH — register 311 only (rolling window)

Portal: no open-data Hub found (`data.daytonohio.gov` DNS-dead; daytonohio AGOL
org is internal apps/maps). The working surface is the city ArcGIS Enterprise at
`https://maps.daytonohio.gov/gisservices/rest/services` (34 folders incl. Accela,
BuildingServices, OpenData, PublicWorks). Montgomery County OH publishes nothing
machine-readable: `data.mcohio.org`/`opendata.mcohio.org` DNS-dead,
`gis.mcohio.org` serves a bare IIS default page, no CKAN/Socrata/AGOL org found.

- **311 — live.** `PublicWorks/COD_ServiceRequests_Last90/MapServer/0`
  ("Hansen Service Requests - Last 90 Days"): 19,900 rows. Watermark `ADDDTTM`;
  newest **2026-08-25 17:45 UTC** (same-day). Point geometry; native
  `X_COORD`/`Y_COORD` are Ohio State Plane feet, but the service reprojections
  verified cleanly with `outSR=4326` (sample -84.1315/39.7609). `ADDRESS`,
  `PROBCODE`/`PROBDESC`, resolution timestamps present.
  **Caveat:** a rolling 90-day window — no archive (Houston-style partial view).
- **Permits — no feed.** The Accela folder exposes only `AccelaIncidents`
  MapServer whose layer returns empty results / no count (broken or empty
  publication); BuildingServices holds inspection *areas*, not permit records.
  Dayton's Accela Citizen Access has no public bulk API.
- **Deeds — blocked.** `PublicWorks/DaytonParcel/MapServer/0` carries joined
  county CAMA fields `GISADMIN.WEB_CAMA.SALE_DATE`/`SALE_PRICE` in its schema,
  but every query touching the dotted field names fails with HTTP 400 —
  not consumable as-is. Marked unverified/blocked rather than absent.
- **Licenses / other — no feed.** OpenData folder is police analytics
  (arrests/CFS/crimes) only.

### Toledo, OH — 311 provisional only

Portal: `data.toledo.gov` ("City of Toledo Data Hub", ArcGIS Hub, 47 datasets —
infrastructure layers: sewer/water/storm/trees/snow; no core families). City GIS
Enterprise at `https://gis.toledo.oh.gov/arcgis/rest/services`; AGOL org
`toledo.maps.arcgis.com`. Lucas County Auditor's Tyler-based server
(`lcaudgis.co.lucas.oh.us/gisaudserver`) exposes cadastre parcels **without**
sale fields in the public layers.

- **311 — live but weak geocoding.** `Public/CityWorks_ServiceRequest_2022/
  MapServer/0`: 42,881 rows. Watermark `INIT_DATE`; newest **2026-08-25 19:01 UTC**
  (same-day). 42,569 rows carry `X_COORD`/`Y_COORD` (Ohio State Plane ft) and a
  `LOCATION` address string; however the service-side geometry is unreliable —
  the newest row returned NaN coordinates under `outSR=4326`, and raw x/y are in
  an inconsistent projection. Treat as PROVISIONAL: usable via X/Y+address after
  client-side reprojecting/geocoding, not as a clean point feed.
- **Permits — no feed.** Only a Demolition web-app (AGOL instant app) and a
  static `Demolition_Map_MIL1` MapServer; no building-permit dataset on any host.
- **Sales/deeds — no feed.** Hub "For_Sale_Data" is city-owned land disposition
  inventory (no price/date transactions); county parcels lack public sale fields.
- **Licenses — no feed.**

### Akron, OH — register none

No unified portal: `data.akronohio.gov` DNS-dead; `summitcountyoh.opendata...`
and similar Hub shells are empty wildcard pages. AkronGIS AGOL org
(`akrongis.maps.arcgis.com`, id `8roChjXOF0iBhNoB`) holds ward/reference layers,
Cityworks grass-mowing SRs **without any date column** (7,102 rows), address-request
Survey123 forms, and one-off capital-program snapshots. The Summit County map
server `summitmaps.summitoh.net` is behind a login gate ("Application Blocked").

The one real find is the Summit County Fiscal Office AGOL content (owner
`dmullen_summit`): `Parcels_SCFO` — 260,934 parcel polygons with `SaleDate`
(integer **year**, max 2025) and `Sale_Price` — plus a "Real Estate Sales
Dashboard" Experience built on the same reappraisal layers.

- **Verdict: REJECT all four families as live feeds.** Summit's sales data is a
  yearly reappraisal snapshot, useful only as backfill/validation corpus. Akron's
  311 runs on Cityworks internally but is not published with watermarks.

### Knoxville, TN — register none (archives only)

Portal: no city open-data hub (`data.knoxvilletn.gov` DNS-dead; knoxvilletn.gov
site exposes no data links). The joint Knoxville-Knox County-KUB GIS AGOL org
("KnoxGIS", id `QWaOgwdmpqI9HUzf`) hosts the regional data; `www.kgis.org`
ArcGIS Server REST is locked behind credentials (401) except a public address
geocoder. City of Knoxville's own AGOL org contains zero family-relevant items.

- **Permits — stale archive.** `BuildingPermits_KNO/FeatureServer/0`:
  29,788 point features, rich schema (`PERMITVALUE`, `SQFEET`, `NUMBERUNITS`,
  `RESNONRES`, `ZONING`, `CLASSWORK`) — but watermark `DATEISSUED` caps at
  **2026-02-24** (six months frozen; 0 rows in 30d). `LDTM_Permits` sibling
  freezes at 2025-12-02. Backfill corpus only.
- **Development proxy — semi-live.** `DevelopmentProjects` ("Groundbreakers
  Data"): 545 point features; newest `ANNOUNCE_DATE` 2026-07-09; carries
  DEVELOPER, UNITS, COST, START_DATE. Updated on announcement cadence (~monthly),
  not a permit transaction stream. Optional weak proximity signal.
- **311 / licenses / deeds — no feed.** No 311 dataset anywhere in the KGIS org;
  business parks are static boundaries; parcels/deeds are not published through
  the accessible endpoints.

## Recommendation

Two metros graduate immediately: **Cleveland** (permits + 311 + sales/deeds —
the strongest four-family coverage found since San Antonio/Las Vegas; watch the
~10-day issued-permit sync lag and prefer `Building_Permit_Application_Tasks`
for freshness) and **Chattanooga** (daily-refreshed geocoded All Permits CSV +
live parcel-sale history on `pwgis Misc/Parcels`; wire the CSV item, avoid the
frozen FeatureServer twin, and expect the missing `?layers=0` trap on the Hub
download API). **Dayton** is a single-feed candidate (Hansen 311, same-day fresh,
outSR=4326 verified) at Louisville-like cost, gated on accepting a rolling
90-day-only window. **Toledo** stays provisional until its Cityworks SR feed is
reprojected reliably (NaN geometry on newest rows today). **Akron** and
**Knoxville** are skip-grade for live signals: Summit County's year-grain sales
file and Knoxville's frozen-through-Feb-2026 permit archive are backfill and
model-validation corpus; Knoxville's Groundbreakers announcements are an
optional low-cadence development proxy.

Every claim above is row-verified or explicitly marked unverified/provisional
(Dayton CAMA deed fields = blocked-by-API, untested values; Toledo SR geometry =
NaN observed on newest row). License/deed "no feed" verdicts are confirmed within
the cities' own portals and the probed county servers, not provably absent from
every state system.
