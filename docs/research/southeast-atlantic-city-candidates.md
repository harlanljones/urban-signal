# Southeast Atlantic city candidates — Raleigh, Durham, Charleston, Birmingham, Virginia Beach

**Date of survey: 2026-08-25.** Every host, dataset, watermark reading, and row below was
probed live this day. Prior context: Charlotte NC is registered; Raleigh appeared in the
Socrata sweep only as "left Socrata" and was never row-probed until now. "Live feed"
means a newest-row read (watermark descending) confirmed fresh data; portal
`modified` metadata was treated as unreliable and never used as evidence.

## Method

For each metro: find the correct portal host; detect platform (ArcGIS Hub /
ArcGIS Server / CKAN / Socrata / none-found). Socrata membership was checked two ways
(`api.us.socrata.com/api/catalog/v1?domains=<DOMAIN>` and direct host probes) — **none of
the five metros is on Socrata**, including Virginia Beach: `data.vbgov.com` does not
resolve at all (DNS failure on http and https). Discovery then used ArcGIS item search
(`arcgis.com/sharing/rest/search`) plus org-level service enumeration
(`<host>/arcgis/rest/services?f=json`) and CKAN `package_search`. Every surviving layer
was verified row-level — newest row by watermark descending, geometry type, geocoding
fields, and a recent-window row count. Only newest-row reads count as evidence.

## Summary

| Metro | Correct host(s) | Platform | Register | Not register |
|---|---|---|---|---|
| Raleigh, NC | `data.raleighnc.gov` (Hub of `ral.maps.arcgis.com`) + `services.arcgis.com/v400IkDOw1ad7Yad` | ArcGIS Hub + FeatureServer | **permits, 311** | licenses, deeds (city); deeds available at county level |
| Durham, NC | `webgis2.durhamnc.gov/server` + `live-durhamnc.opendata.arcgis.com` (org `Open.Data_DurhamNC`) | ArcGIS Server + Hub | **permits, deeds** | 311, licenses |
| Charleston, SC | city `services2.arcgis.com/tQaXW7Zb1Vphzvgd`; county `services.arcgis.com/jR9eNCjAkxwH2nLe` | ArcGIS FeatureServer (hosted, city IT + county GIS) | **permits**; 311 provisional | licenses (archive), deeds |
| Birmingham, AL | `data.birminghamal.gov` | CKAN 2.9.11 (static files) | **none** | all four (stale archives) |
| Virginia Beach, VA | `services2.arcgis.com/CyVvlIiUfRBmMQuu` (org `VBCGIS_OrgAcct1`); `data.vbgov.com` DNS-dead | ArcGIS FeatureServer | **permits (state-plane), sales/deeds (address-only)** — both provisional-grade | 311 (not found), licenses (no watermark) |

## Per-metro findings

### Raleigh, NC — register permits + 311

Portal: `data.raleighnc.gov` is now an **ArcGIS Hub site** (confirmed — the Socrata
sweep's "left Socrata" note resolves to this), backed by org services at
`https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services` (1,312 services,
many internal). All feeds are hosted FeatureServers.

- **Permits — live.** `Building_Permits/FeatureServer/0`, 183,729 rows, point geometry
  (Web Mercator). Watermark `issueddate` (esriFieldTypeDate); newest **2026-08-22
  16:04 UTC**; 405 issued in the last 30 days. Native `latitude_perm`/`longitude_perm`
  doubles + full address fields + parcel `pin`; `permitclassmapped`, `estprojectcost`,
  `statuscurrent` ("Issued"), contractor fields. Related views: "Building Permits Issued
  Past 180 Days", "Building Permits Past 31 Days".
- **311 — live.** `Ask_Raleigh_Requests/FeatureServer/0` (layer "Service Request"),
  14,649 rows, point geometry (WGS84). Watermark `APPLIED_DATE`; newest **2026-08-25
  06:00 UTC** (survey day); 1,552 rows in 30 days. `ADDRESS`/`ZIP_CODE` present;
  `CATEGORY`/`SERVICE`/`STATUS` typed. **Caveat:** 14.6k total rows against 1.5k/month
  volume implies a rolling window (~9 months), not a full archive.
- **Licenses — not found.** Org catalog has only marginal items (Nightlife Permitted
  Businesses, Streeteries, Outdoor Seating Temporary License Applications) — no general
  business-license register.
- **Deeds — no city feed**, but the county option is strong: Wake County
  `Parcels` MapServer (`https://maps.wake.gov/arcgis/rest/services/Property/Parcels/MapServer/0`,
  437,837 parcels) carries `SALE_DATE` (newest **2026-08-19**), `TOTSALPRICE`
  (newest row $1.25M), `DEED_BOOK`/`DEED_PAGE`; 784 sales >$0 in 30 days. Polygon
  geometry. Under ADR 0007 this would be a **separate Wake County registration**, not a
  Raleigh division.

### Durham, NC — register permits + deeds

Portal: ArcGIS Server 11.x at `https://webgis2.durhamnc.gov/server/rest/services`
(folders incl. `PublicServices`, `CityworksServices`), Hub mirror
`live-durhamnc.opendata.arcgis.com`, AGOL org `Open.Data_DurhamNC`.

- **Permits — live.** `PublicServices/Inspections/MapServer/12` "All Building Permits",
  point geometry. Watermark `ISSUE_DATE`; newest **2026-08-21**. Rich attributes:
  `BLD_Cost` (newest row $28.7M, 225-unit MF), `DWELLING_UNITS`, `SQFT_FLOOR`,
  `BLD_Type`, `PmtStatus`, `PIN15`. Companion layers: Active Building/Plumbing/
  Mechanical/Electrical Permits, Demolition Permits (9–13), Driveway Permits.
- **Deeds — live.** `PublicServices/Property/MapServer/4` "Parcels" (polygon),
  80 fields. Watermarks `PKG_SALE_DATE` / `DEED_DATE`; newest sale **2026-08-10**
  ($1,025,000, `DEED_BOOK` 010603/00481); 69,379 rows carry a sale date; 244 sales >$0
  since Jul 1. Address fields (`PHYADDR_*`, `LOCATION_ADDR`). **Integration caveat:**
  `orderByFields=DEED_DATE|PKG_SALE_DATE DESC` returns HTTP 400 on this server —
  producers must page by `OBJECTID DESC` with a date `where` filter instead.
- **311 — not found.** `CityworksServices/OneCall` contains solid-waste layers only;
  no citizen-request table in any public folder or AGOL hit. Not confirmed absent
  outside these surfaces.
- **Licenses — not found.**

### Charleston, SC — register permits (city); 311 provisional

Portal: no city open-data website found (`opendata.charleston-sc.gov`,
`data.charleston.gov`, all `*.charlestoncounty.org` candidates DNS-fail). Both
jurisdictions publish through hosted ArcGIS orgs instead:
city IT owner `python_chs` → `https://services2.arcgis.com/tQaXW7Zb1Vphzvgd/...`
(484 services); county GIS owner `mradams_chascogis` →
`https://services.arcgis.com/jR9eNCjAkxwH2nLe/...` (490 services).

- **Permits — live (subset scope).** City `New_Construction_Permits/FeatureServer/0`,
  14,788 rows, point geometry. Watermark `ISSUE_DATE`; newest **2026-08-07 11:48 UTC**
  (~2.5-week cadence at survey); 18 issued in the last 18 days. `VALUATION`,
  `MAIN_PARCEL_NUMBER`, `PARCELADDR_LINE1/2`, `PERMIT_TYPE` ("Building Multi-Family",
  "Single Family/Duplex Dwelling"). **Caveat:** new-construction permits only — the
  full-permit register is not published to this org. County `Building_Permits_2025`
  (layer 47, 1,781 geocoded points, newest `USER_Date` **2025-12-31**) is a frozen
  annual archive of unincorporated-area permits — backfill corpus only.
- **311 — provisional.** The canonical `CHS_Public_311_Feature_Service` is a dead demo
  (4 rows total, newest 2016-11-23). Live citizen requests arrive as **monthly rotated
  "Sheet" layers**: `Citizen_Services_July_Requests_2026` (1,635 rows, newest
  Create_Date **2026-07-29**; native `Latitude`/`Longitude`; `Request_Type`,
  `Completed_Closed`). Monthly cadence means up to ~4 weeks of staleness and requires
  layer-name rotation tracking (Louisville-style), hence provisional rather than
  register.
- **Licenses — reject.** County `Business_Licenses_2024` (layer 46) is a static geocoded
  CSV with 4 fields and no dates.
- **Deeds — not found.** County org publishes project-scoped parcel layers only; no
  sales/price/deed layer surfaced.

### Birmingham, AL — register none

Portal: `data.birminghamal.gov` (**CKAN 2.9.11**, official city portal). No datastore
API usage — every candidate dataset is a static XLSX/CSV file download:

- **Permits — stale.** "Building Permits and Valuations" = yearly files 2015–2017 only
  (last resource modified 2017-06-09); "Demolition Permits" last modified 2017-06-05.
- **311 — stale.** "311 Cases - Yearly": newest file `2019cases.csv` published
  2021-07-29; row check confirms 18,761 cases all dated 2019.
- **Licenses — stale.** "Business Recruitment" (new-business-licenses) XLSX from
  2017-06-05.
- **Deeds — no feed.** Only budget/financial reports and a property-for-sale notice.
- ArcGIS cross-check: `arcgis.com/sharing/rest/search?q=birmingham alabama building permit`
  returns 0 relevant items. Verdict: the portal is effectively abandoned for our feed
  families (nothing newer than 2021). **REJECT.**

### Virginia Beach, VA — register nothing outright; two provisional feeds

Portal: **not Socrata.** `data.vbgov.com` does not resolve (the survey hypothesis that
VB lives there is wrong — likely a retired hostname). The working surface is the AGOL
org `VBCGIS_OrgAcct1` (260 public items) served from
`https://services2.arcgis.com/CyVvlIiUfRBmMQuu/arcgis/rest/services` (367 services).

- **Permits — live, state-plane (provisional).** `Building_Permits/FeatureServer/0`,
  202,601 rows, point geometry **EPSG:2284 (NAD83 Virginia South, ftUS)**. Watermark
  `Building_Permits_IssueDate` (string `YYYY-MM-DD`); newest **2026-07-31**; 475 issued
  since 07-26. Address + `GPIN` on every row. Fresher companion:
  `Building_Permits_Applications_view` (newest application **2026-08-21**, same schema,
  non-spatial view). Issue-date lag vs application-date suggests weekly batch refresh.
  State-plane geometry + string dates ⇒ provisional grade, needs geocoding/reprojection.
- **Sales/deeds — live, address-only (provisional).** `Property_Sales_/FeatureServer/0`
  (non-spatial table, 290 rows since 07-26, 151 with `Sale_Price` > 0). Watermark
  `Sales_Date`; newest **2026-08-10**. `Sale_Price`, `Document_Number`, `Deed_Book`,
  `Deed_Page`, `GPIN`, `Street_Address` — a genuine deed-transfer feed; join to parcels
  via GPIN for geometry.
- **Licenses — no watermark, skip.** `Business_Licenses_view` (452k rows) has no
  per-row date column usable as a watermark (`Begin_Date` strings are license-period
  starts, inconsistently populated); inserts are only detectable by `OBJECTID`.
- **311 — not found.** No citizen-service-request service among the 367 org services or
  260 public items (closest: FOIA Requests and Police Calls for Service — neither is
  311).

## Recommendation

Three metros graduate with real signal, one stays out, one splits into two partial wins:

1. **Raleigh, NC — register permits + 311.** Two fresh, geocoded FeatureServers
   (permits newest 2026-08-22 with native lat/lng; Ask Raleigh 311 newest survey-day).
   Same dual-feed shape as San Antonio/San Jose. Watch the 311 rolling window when
   backfilling. Optionally follow with a **separate Wake County registration** (deeds
   via `maps.wake.gov` parcels, newest sale 2026-08-19) under ADR 0007 precedent.
2. **Durham, NC — register permits + deeds.** Permits are the strongest single permit
   feed in this wave (newest 2026-08-21, cost/dwelling-unit attributes). Deeds come
   free off the parcel table (sale price + deed book/page). Producer must avoid
   `orderByFields` on the date columns (HTTP 400) — page by OBJECTID with date filters.
3. **Charleston, SC — register city permits; take 311 only as a provisional monthly
   rotation.** New-construction-only permit scope is narrower than other cities but
   valuation+parcel+address make it a real development signal. The 311 family requires
   month-layer rotation plumbing; defer unless rotation support lands first.
4. **Virginia Beach, VA — park both feeds as provisional.** Sales/deeds is genuinely
   live (newest 2026-08-10) but address-only; permits are voluminous but state-plane
   with string dates and a visible refresh lag. Both need ADR-0004 geocoding /
   reprojection before registration. Licenses lack any watermark; 311 absent. Note
   `data.vbgov.com` is dead — do not re-test it.
5. **Birmingham, AL — skip.** CKAN portal frozen (nothing newer than 2019 data /
   2021 upload); no ArcGIS alternative. Revisit only if the city revives the portal.

Every claim above is row-verified or explicitly marked unverified/provisional. License/
deed "not found" verdicts are confirmed within the discovered city/county portals and
org catalogs, not provably absent from every upstream system.
