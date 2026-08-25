# Northeast / Pacific NW city candidates — Jersey City, Newark, Hartford, Spokane, Reno

**Date of survey: 2026-08-25.** Every host, dataset, watermark, and row below was probed live that
day with `curl -sm`; "live" means a newest-row read (watermark column descending) returned fresh
data. Metadata `modified` timestamps were never used as evidence — this matters here because one
metro (Hartford) carries a prior "effectively dead" verdict from the 2026-08 non-Socrata sweep that
row-level probing **overturns**.

## Method

For each metro: discover the correct portal host (Socrata catalog-v1 domain check, `*.opendata.arcgis.com`
DCAT feeds, `arcgis.com/sharing/rest/search` item/org search, targeted web search); enumerate the
catalog for the four feed families; row-level verify every survivor — newest row by watermark
descending, column list, geometry type, and a recent-30-day count where the watermark supports it.
County portals were treated as in-scope hosts (Montgomery MD / Alameda CA precedents).

## Summary

| Metro | Correct host(s) | Platform | Register | Not register |
|---|---|---|---|---|
| Hartford, CT | `data.hartford.gov` (services proxied via `utility.arcgis.com/usrsvcs/...`) | ArcGIS Hub + FeatureServer tables | **311**, **permits** (building/planning/PW) | deeds/sales (7-mo recorder lag), food licenses (no watermark) |
| Spokane, WA | `gismo.spokanecounty.org` + county GIS Data Catalog hub (`GISspokane`) | ArcGIS MapServer/FeatureServer | **sales/deeds** (county) | permits (Accela SPA + static Excel), 311 (Salesforce-locked), licenses |
| Reno, NV | `explore-washoe.opendata.arcgis.com` + `gisweb.washoecounty.gov` (+ `citymaps.reno.gov`, `data-cityofreno.opendata.arcgis.com`) | ArcGIS Hub + Server | **sales/deeds** (Washoe parcels) | permits, 311 (RenoDirect), business licenses |
| Jersey City, NJ | `data.jerseycitynj.gov` | **Huwise/Opendatasoft — unsupported platform** | **none** | all four (families absent from catalog anyway) |
| Newark, NJ | `data.ci.newark.nj.us` | CKAN (bot-walled, 503 to all machine clients) | **none** | all four (unprobeable; last visible updates 2020) |

## Per-metro findings

### Hartford, CT — register 311 + permits (overturns the earlier "dead" verdict)

Portal: `data.hartford.gov` (ArcGIS Hub, 128 datasets). All feed datasets are layers of two hosted
services reached through `utility.arcgis.com/usrsvcs/<uuid>/rest/services/...` proxies: a shared
`HartfordOpenDataTables` FeatureServer and `Service_Requests_2015_to_Current` FeatureServer.
The prior survey (`docs/research/non-socrata-platforms.md`) called Hartford "effectively dead" off an
item-modified timestamp of 2024-09; the row-level probe below shows every family dataset is current
to 2026-08-24. Treat the old verdict as superseded.

- **311 — live.** `Service_Requests_2015_to_Current/FeatureServer/9` ("Service Request Current
  Year"; layers 0–11 slice 2015→current). Watermark `USER_Opened_Date` (string `YYYY-MM-DD`);
  newest **2026-08-24** (`SRM-2026-11066`); **993 rows in 30 days**. Point geometry with full
  ArcGIS-geocoder attribute block (`Match_addr`, `Addr_type=StreetAddress`, score), but `X`/`Y`
  are **CT state-plane feet** (~1,020,000 / ~837,000), not lat/lng → geocoded but state-plane.
  Yearly layer rollover caveat, same shape as DC/Nashville.
- **Permits — live (three tables).** `HartfordOpenDataTables/FeatureServer/0` = Building Permits
  20200101-to-current: watermark `DateIssued` (date); newest **2026-08-24**; **329 issued in 30
  days**; Accela-style schema (`RECORD_ID` `RES-ALT-26-000445`, status, cost,
  `PROPERTY_ADDRESS`, `PARCEL_ID`). `/3` Planning Permits and `/4` Public Works Permits both
  newest-opened 2026-08-24. All three are **non-spatial Tables, address-only**
  (`Location` string, no lat/lng).
- **Deeds/sales — stale, do not register.** Real Estate Sales table (`.../FeatureServer/5`),
  watermark `SaleDate`: newest **2026-01-09**, 33 sales in 2026 total, **0 since Apr 1**,
  600 in the trailing year — a ~7-month town-clerk publishing lag. Rich schema (`SalePrice`,
  `LegalReference` book/page, `xrDeedID`, parcel ID) makes it good backfill/validation corpus only.
- **Licenses — snapshot only.** Food Establishments Licenses Current: 735 rows, **no per-row date
  column at all** (status/classification/seating only). No other license family found.

### Spokane, WA — register county sales/deeds only

City portal `data.spokanecity.org` serves an Incapsula JS challenge to curl on every path (API
included); `my.spokanecity.org/opendata/` is HTML pages only and points to the **county** GIS Data
Catalog for public data. The real host is Spokane County: org `GISspokane` on arcgis.com (197 items),
Hub site subdomain `gisdatacatalog`, services at `gismo.spokanecounty.org/arcgis/rest/services`.
City permits run on Accela Citizen Access (`aca.spokanepermits.org`, no REST); city 311 runs on
Salesforce (`myspokane311.my.site.com`) and a 2018 city RFP states the data is vendor-housed with no
public APIs.

- **Sales/deeds — live (county).** `OpenData/Property/MapServer` layer 20 "2026" (yearly layers
  2015–2026 plus an all-years "Sales" layer 4). Watermark `document_date` (date): newest
  **2026-08-21**; **683 rows since 2026-07-26**. Polygon geometry; fields `Parcel` (APN),
  `gross_sale_price`, `prop_use_code`. Geocoded polygons, not just addresses.
- **Permits — no feed.** County publishes `BuildingAndPlanningPermits` as a **static Microsoft
  Excel item** (no service); `SmartGov` folder exposes only parcels; `BPPublic` folder is reference
  map layers (zoning/contours). City side is Accela ACA SPA.
- **311 — no feed.** Salesforce-locked per RFP #4504-18; nothing in the 197-item county catalog
  matches citizen service requests.
- **Licenses — no feed.** Nothing in the county catalog or city site.

### Reno, NV — register Washoe County sales/deeds only

City of Reno: Hub `data-cityofreno.opendata.arcgis.com` (105 datasets, all boundaries/zoning/GIS
context), ArcGIS Server `citymaps.reno.gov/server/rest/services` (folders incl. `Accela`,
`Business`, `RenoDirect`). The Accela MapServers are **reference layers** (zoning, wards, fee
areas), not permit records; `Business` and `RenoDirect` folders are empty; the Hosted folder is
affordable-housing/parks views. The only permit artifact anywhere is
`EAE_Permits_Layer_View/FeatureServer` (services5.arcgis.com, owner `fausettj_cityofreno`):
watermark `Opened`, newest **2022-01-18** — stale, and a street-boring subset besides. REJECT.

- **Sales/deeds — live (Washoe County).** `gisweb.washoecounty.gov/.../OpenData/WashoeDataShare/
  MapServer/0` (the free "Washoe Open Data" share behind `explore-washoe.opendata.arcgis.com`;
  DCAT has 68 datasets, none titled sale/deed — the sales fields hide inside Parcels). 193,939
  parcel rows county-wide (Reno + Sparks + unincorporated). Watermark `SALEDATE`
  (**string MM/DD/YYYY** — sort it as text carefully or parse); verified 2026 monthly counts:
  Jan 181 / May 341 / Jun 265 / Jul 175 / Aug **207** so far — current through Aug 2026. Polygon
  geometry; `SALEPRICE`, `BOOK`/`PAGE`, owner names, assessment values present. Sample newest-by-
  string-sort row is a 12/31 artifact; use parsed dates or month-LIKE counts for freshness.
- **Permits — no feed.** See EAE above; main Accela permits unpublished.
- **311 — no feed.** `RenoDirect` (= Reno's 311) service folder empty; nothing on Hub or AGOL org
  scan (375 items across `cityofreno` owners, all context GIS).
- **Licenses — no feed.** `Business` folder empty; no license dataset in Hub DCAT or org items.

### Jersey City, NJ — register none (unsupported platform; families absent)

Portal: `data.jerseycitynj.gov` is **Huwise** (Opendatasoft rebrand — `odsui` assets, Explore API)
— **not** Socrata despite the expectation carried into this task; Socrata catalog-v1 returns
"Domain not found", and the DCAT endpoint 404s. The Explore v2.1 API works
(`total_count: 1535` datasets) but ODS/Huwise is outside the supported platform set
(ArcGIS/CKAN/Socrata/CSV-last-resort; ODS CSV exports exist per-dataset but there is no client).

- **All four families — effectively absent regardless of platform.** Scanning all 1,535
  `dataset_id`s: permits hits are parking-permit docs and permit-*requirement* documents; the six
  "311" hits are zoning-case titles that happen to contain street number 311; zero hits for
  license / sale / deed patterns. Closest construction-adjacent set, `building-inspections`,
  returns **0 records** via the legacy records API. The portal is document/agenda-heavy
  (board applications, certified-artist reviews), not transactional feeds.

### Newark, NJ — register none

Portal: `data.ci.newark.nj.us` is a **CKAN** deployment (Galician-localized UI, `api/3` endpoints)
but returns **503 with a JS anti-bot challenge on every path** — `package_list`, `package_search`,
`data.json` — to curl, with browser UA/Accept headers and cookies alike. Machine access is
effectively dead. Last publicly indexed state (via web-search snapshots of the site): flagship
dataset "Newark 4311" updated **July 2020**, i.e., already years stale before it became
unreachable. No Newark-specific datasets surfaced on Socrata (`data.nj.gov` q=newark: 0 results)
or in an official-looking ArcGIS presence (NewGIN statewide hub is parcels/context only). Verdict:
not viable now; re-check only if the portal comes back up.

## Recommendation

**Register Hartford first** — it is the sleeper of this wave: three live permit families (329
building permits in the last 30 days, planning + PW also current to 2026-08-24) plus a live 993/30d
311 feed, all through ordinary ArcGIS REST that the existing `ArcGISClient` can page. Costs to
accept: every feed is address-only/state-plane (PROVISIONAL-grade geocoding under our rubric), the
311 service slices by calendar year (current-layer pointer needed at rollover), and the services sit
behind `utility.arcgis.com/usrsvcs` proxy URLs whose stability should be watched. Its deeds table is
a 7-month-lag backfill corpus, not a signal.

**Register the two county sales feeds opportunistically:** Spokane County's Property Sales layers
(683 sales in 30 days, polygon-geocoded, price + use code) and Washoe's parcel share for Reno metro
(current through Aug 2026, polygon + price, but an awkward MM/DD/YYYY string watermark). Both are
deeds-family registrations in metros that otherwise have nothing, matching the Las Vegas
sales/deeds precedent; neither metro has any other live family.

Skip Jersey City (Huwise/Opendatasoft is unsupported, and the catalog holds no feed families even
before the platform problem) and Newark (bot-walled CKAN with 2020-era content). If a fifth
registration ever matters, revisit Newark after confirming its portal responds to machines again;
nothing else here warrants a re-probe inside 12 months except Hartford's deeds lag, which could
shrink if the town clerk catches up.

Every claim above is row-verified or explicitly marked otherwise (Jersey City's building-inspections
zero-record check is the shallowest probe; Newark is verdict-by-inaccessibility plus third-party
snapshots). License/deed "no feed" verdicts are confirmed within the city/county portals probed, not
provably absent from state systems.
