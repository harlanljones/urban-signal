# Resolving the platform for nine unidentified metros

**Date of survey: 2026-08-24.** Every host, dataset, watermark, and row below was
probed live that day. The nine metros were flagged in the 2026-08-24 wave survey
because their candidate hosts failed discovery; **nothing in the Wave-2 plan
should be read as evidence about them** — this closes the gap. "Live feed" means
a newest-row read (watermark column descending) confirmed fresh data; Hub/CKAN
`modified` metadata was treated as unreliable and never used as evidence.

## Method

For each metro: find the correct portal host; detect platform (ArcGIS Hub /
CKAN / Socrata / custom); search the catalog for the four feed families
(building permits, 311, business licenses, property sales/deeds); row-level
verify every survivor — newest row by watermark descending, column list,
geocoding fields, and a recent-30-day row count. Only newest-row reads count as
evidence. See the per-metro entries for exact endpoints.

**Correction to the survey:** three of the nine "failed" hosts were the right
site probed with the wrong API. `data.houstontx.gov`, `phoenixopendata.com`, and
`data.sanantonio.gov` are **CKAN** portals and 404 on the ArcGIS Hub DCAT probe
that the wave survey used; `data.milwaukee.gov` answered a transient 404 and is
also CKAN/OpenGov. Houston additionally runs a live ArcGIS Hub under
`houston-mycity.opendata.arcgis.com` (the wave survey's `cohgis-mycity` is a
stale alias that still returns an empty catalog).

## Summary

| Metro | Correct host(s) | Platform | Register | Not register |
|---|---|---|---|---|
| Houston, TX | `data.houstontx.gov` + `houston-mycity.opendata.arcgis.com` | CKAN + ArcGIS Hub | **311** | permits, licenses, deeds |
| Phoenix, AZ | `phoenixopendata.com` | CKAN | **none** | all four |
| San Antonio, TX | `data.sanantonio.gov` + `opendata-cosagis.opendata.arcgis.com` | CKAN + ArcGIS Hub | **permits, 311** | licenses, deeds |
| San Jose, CA | `data.sanjoseca.gov` | CKAN | **permits, 311** | licenses, deeds |
| Atlanta, GA | `dpcd-coaplangis.opendata.arcgis.com` | ArcGIS Hub (GIS only) | **none** (frozen 2019–24 permit archive only) | 311 (unverified), licenses, deeds |
| Indianapolis, IN | `data.indy.gov` / `gis.indy.gov` | ArcGIS Hub + Server | **311** | permits, licenses, deeds |
| Jacksonville, FL | — (none found) | none-found | **none** | all four |
| Milwaukee, WI | `data.milwaukee.gov` | CKAN (OpenGov) | **liquor licenses** (+ permits w/ 2-mo-lag caveat) | 311, deeds (yearly archive) |
| Las Vegas, NV | `opendataportal-lasvegas.opendata.arcgis.com` | ArcGIS Hub | **permits, sales/deeds**; 311 (partial-view caveat) | business licenses (no watermark) |

## Per-metro findings

### Houston, TX — register 311 only

Portal: `data.houstontx.gov` (CKAN, 99 packages), `houston-mycity.opendata.arcgis.com`
(ArcGIS Hub, 160 entries), `geohub.houstontx.gov` (Public Works hub).

- **311 — live.** `HOUSTON311_RECENT_SR_SNOW` FeatureServer,
  `https://mycity2.houstontx.gov/gisweb01/rest/services/311/HOUSTON311_RECENT_SR_SNOW/FeatureServer/0`.
  Watermark `CREATED_ON` (date); newest 2026-08-24 10:17; native `LATITUDE`/`LONGITUDE`
  doubles + point geometry; 16,478 rows in 30 days. **Caveat:** a rolling
  window back to 2021-07, not a full archive.
- **Permits — no feed.** Only stale/bounded sets (SCPS street-cut permits newest
  2020-12-09 on a `geogimstest` server; a 2020–2023 sidewalk-permit archive;
  annual aggregate XLS). Houston's transactional permits are not on any portal.
- **Licenses / deeds — no feed.** Registry is stale XLS; "Sales Parcel" layer is
  boundary-only (no price/date/transaction attributes).

### Phoenix, AZ — register none

Portal: `phoenixopendata.com` (CKAN, 158 packages); `egishub-phoenix.hub.arcgis.com`
(Hub, 6,847 items but 0 dataset-typed entries for these families — apps/pages only).

- **Permits — no feed.** Only a SOCDS/Census annual aggregate ending 2021.
- **311 — no feed.** The closest hit is `calls-for-service`, which is **police
  911 dispatch** (440k rows, live), not citizen 311.
- **Licenses / deeds — no feed.**

### San Antonio, TX — register permits + 311

Portal: `data.sanantonio.gov` (CKAN), `opendata-cosagis.opendata.arcgis.com` (Hub).

- **Permits — live.** CKAN `building-permits` datastore
  (`resource_id=c21106f9-3ef5-4f3a-8604-f992b4db7512`, CSV `permits_issued.csv`,
  137,425 rows). Watermark `DATE ISSUED` (also `DATE SUBMITTED`); newest
  2026-08-21 (309 issued that day); `X_COORD`/`Y_COORD` = lon/lat on 91.9% of
  rows + address fields; 6,670 rows issued in 30 days (5,313 submitted).
  **Caveat:** coordinates are text lon/lat with ~8% blank; the layer is
  geometry-less.
- **311 — live.** `311_All_Service_Calls` FeatureServer
  (`https://services.arcgis.com/g1fRTDLeMgspWrYp/arcgis/rest/services/311_All_Service_Calls/FeatureServer/0`).
  Watermark `OpenedDateTime`; newest 2026-08-21; point geometry (WGS84 sample
  -98.55/29.48) + state-plane `XCOORD`/`YCOORD`; 39,622 rows in 30 days.
- **Licenses / deeds — no feed.** Only economic aggregates; plat maps.

### San Jose, CA — register permits + 311

Portal: `data.sanjoseca.gov` (CKAN, 181 datasets).

- **Permits — live.** `last-30-days-building-permits` CSV
  (`.../download/buildingpermits30.csv`, 2,323 rows). Watermark `ISSUEDATE`;
  newest 2026-08-22; 2,240 rows in the rolling 30-day window. **Coordinates:
  address-only** (`gx_location` string); `ASSESSORS_PARCEL_NUMBER` (APN) present.
- **311 — live.** `311-service-request-data` CSV (223,944 rows). Watermark
  `Date Created`; newest 2026-08-23 20:29; native `Latitude`/`Longitude`
  (~49% of rows are 0,0); 29,072 rows in 30 days.
- **Licenses / deeds — no feed.** Deeds live at Santa Clara County, not the city.

### Atlanta, GA — register none

Portal: `opendata.atlantaga.gov` is **dead** (TLS fails; tolerant probe returns
"Microsoft Azure Web App - Error 404"). Working host: `dpcd-coaplangis.opendata.arcgis.com`
(Hub, 57 datasets — planning/GIS only).

- **Permits — no live feed.** Only "All Building Permits 2019-2024"
  (item `655f985f43cc40b4bf2ab7bc73d2169b`, 38,107 rows): watermark `DATE OPENED`,
  **newest 2024-04-25** — a frozen historical archive with native lat/lng, useful
  only as a backfill corpus.
- **311 — not found, not confirmed absent** (no published dataset surfaced; cannot
  rule out a non-portal source).
- **Licenses / deeds — no feed** (annual parcel snapshot only).

### Indianapolis, IN — register 311 only

Portal: `data.indy.gov` (ArcGIS Hub; ArcGIS Server 11.3 under `gis.indy.gov/server`).

- **311 — live.** `OpenData/ODP_RIMACServiceRequests` FeatureServer
  (`https://gis.indy.gov/server/rest/services/OpenData/ODP_RIMACServiceRequests/FeatureServer/0`),
  718,401 rows. Watermark `REQUESTEDDATETIME`; newest 2026-08-23 03:36; point
  geometry + native `LAT`/`LONG_` columns; 12,695 rows in 30 days.
- **Permits — no feed (confirmed absent).** City permits sit in Accela Citizen
  Access (`aca-prod.accela.com/INDY`) — no public bulk API.
- **Licenses — no feed.** INBiz SOS bulk data is paid ($9,500).
- **Deeds — no feed.** Only a nightly parcel snapshot with owner/assessed values,
  no sale transactions.

### Jacksonville, FL — register none

Portal: **not found.** `opendata.coj.net` and `data.coj.net` DNS-fail; 26 candidate
`*.opendata.arcgis.com` subdomains all returned empty DCAT catalogs; no Socrata or
CKAN host.

- **Permits — no feed.** JAXEPICS (`jaxepics.coj.net`) is an Angular SPA with no
  public REST; Power BI dashboards are not machine-readable.
- **311 — no feed.** MyJax 311 runs on Salesforce/custhelp; no published dataset.
- **Licenses — no feed.** Only a 2020 static JSO snapshot.
- **Deeds — no API feed.** The Property Appraiser publishes monthly certified
  sales/tax-roll **file downloads** only; no REST. Treat `opendata.coj.net` as
  retired.

### Milwaukee, WI — register liquor licenses (+ permits with a 2-month-lag caveat)

Portal: `data.milwaukee.gov` (CKAN/OpenGov, 196 packages — the survey's "404" was
transient); ArcGIS Server at `milwaukeemaps.milwaukee.gov`.

- **Permits — live but laggy.** `buildingpermits` CSV (16,685 rows, 2013→2026).
  Watermark `Date Issued`; **newest 2026-06-15** despite a 2026-08-24 file
  refresh — monthly cadence with ~2 months lag; address-only; 0 rows in the last
  30 days. Marginal for a live signal.
- **311 — no feed.** Only EMS dispatch and a static 2016–17 comparison.
- **Licenses — live (liquor only).** `liquorlicenses` CSV (nightly) + spatial twin
  `milwaukeemaps.milwaukee.gov/arcgis/rest/services/regulation/license/MapServer/0`
  (verified point geometry). Expiry-based watermark (`EXP_DATE`/`EXPIRATION_DATE`);
  1,273 currently valid.
- **Deeds — yearly archive.** 2025 sales file published 2026-04-17, newest sale
  2025-09-09 — not a live feed.

### Las Vegas, NV — register permits + sales/deeds; 311 with a caveat

Portal: `opendataportal-lasvegas.opendata.arcgis.com` (ArcGIS Hub, 56 datasets;
the old `opendata.lasvegasnevada.gov` is gone). All services on
`services1.arcgis.com/F1v0ufATbBQScMtY/...`.

- **Permits — live.** `OpenData_Building_Permits_` FeatureServer, 437,123 rows.
  Watermark `ISSDTTM`; newest 2026-08-14; 2,104 rows in 30 days. **Address-only**
  (non-spatial Table; `PRCLID` present).
- **311 — live but partial.** `City_of_Las_Vegas_Service_Requests_Open_Data`,
  55,000 rows (oldest 2008). Watermark `ADDDTTM`; newest 2026-08-14; only 85 rows
  in 30 days — a curated subset, completeness unverified. `LAT_1`/`LONG_1` are
  null on every row.
- **Business licenses — no watermark.** 212,204 rows, no per-row date column;
  register only if a metadata-based refresh is acceptable.
- **Sales/deeds — live.** `parcels` FeatureServer (302,153 rows). Watermark
  `SALEDATE` (int `YYYYMMDD`); newest 2026-08-01; `SALEPRICE`/`SALETYPE`/
  `DOCDATE`/`DOCNO` present; 166 rows in 30 days; address-only in this view.

## Recommendation

Three metros graduate to the candidate list with real signal: **San Antonio**
(permits + 311), **San Jose** (permits + 311), and **Las Vegas** (permits +
sales/deeds). **Houston** (311) and **Indianapolis** (311) are single-feed
candidates at Austin-like partial-registration cost. **Milwaukee** (liquor
licenses) and **Phoenix / Atlanta / Jacksonville** are skip-grade for live feeds;
Atlanta's frozen 2019–24 permit file and Milwaukee's yearly sales file are
backfill/validation corpus, not live feeds.

Every claim above is row-verified or explicitly marked unverified; no unprobed
conclusions are drawn. License/deed "no feed" verdicts are confirmed within the
city's own portals, not provably absent from county/state systems.