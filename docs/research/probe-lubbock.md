# Wave 3 Phase-0 probe — Lubbock, TX (US-268)

**Probe stamp: 2026-08-30.** Every host, dataset, watermark, and row below was
read live that day. Hub `item.modified` / Insights `rowsUpdatedAt` / ArcGIS
`created_date` are labels only; freshness evidence is newest-row-by-watermark
with row-level verification.

Linear: **US-268**. Ticket hint: *County GIS + city permits, pop ~360K
(Lubbock County), Fit Medium.* Region: South Central / South Plains. City of
Lubbock (Lubbock County seat, FIPS 48303). The prior Southwest & Mountain West
sweep marked Lubbock **Tier 3 DEFER** (municipal Tier 3 — Texas state
super-feed cluster). This probe **re-verifies live** at Socrata, Hub DCAT,
ArcGIS Server (`pubgis.ci.lubbock.tx.us`), hosted AGOL org (orgid
`eYXun6c1pgy8Qpta`), ArcGIS Search API, Tyler EnerGov SelfService, Permitium,
GovQA 311, and LCAD/County parcel surfaces.

Success criterion (ADR 0004): a feed is registrable if it is *live* and either
natively geocoded **or** address-geocodable. Tier 1 = live + native geocode;
Tier 2 = live + address-only (ADR-0004 geocoder); Tier 3 = stale / absent /
vendor-locked without bulk API / wrong grain.

## Verdict

**REJECT — Tier 3 across all four families. No registrable municipal bulk feed
for the four target families (permits, 311, SLA, deeds).**

The City of Lubbock runs its development-permitting on **Tyler EnerGov
Citizen Self Service** (`egovaccess.ci.lubbock.tx.us/EnerGov_Prod/SelfService/`)
— a JavaScript SPA with **no anonymous bulk REST** (every `/selfservice/api/*`
route returns `The resource cannot be found.`; the live API base is a
`webApiBaseUrl=/user/token` bearer-auth flow). The public ArcGIS footprint
(`pubgis.ci.lubbock.tx.us` + hosted AGOL org `eYXun6c1pgy8Qpta` = 164 Feature
Services) is **infrastructure / basemap / parcel only** — zero permit, 311,
license, or deed transaction layers. The only live point layer, Police
`Crime_Map`, is **stale** (newest `REPORTDATE` 2024-09-24, ~23 months before
probe). Parcels (LCAD `DashboardParcelData/2`) are an appraisal **tax roll**
(assessed value + owner), **not** deeds/sales. Code Cases / Building Safety
"Performance Metrics" are ArcGIS **Insights** workbooks gated behind
`insightsservices2.arcgis.com/.../WorkspaceServer` and a Dashboard item whose
`data` references only the city website — no public row source.

This matches the tier-3 Texas cluster pattern already adopted for Corpus
Christi / Bryan / Killeen / RGV in the Southwest & Mountain West sweep.

**No family passes Tier 1/2. Leaf build NOT authorized; spine hold must not
proceed.** State companion remains viable: TX TREC `s7ft-44qi`, TDLR
`7358-krk7`, TABC `7hf9-qc9f` — all Socrata on `data.texas.gov`, HTTP 200,
filterable to Lubbock County 48303 with zero new client machinery
(`SocrataClient` + county FIPS crosswalk). Recommend state super-feed for SLA
only if Lubbock advances via derived-state registration (no municipal leaf).

## Method

1. **Socrata discovery:** `api.us.socrata.com/api/catalog/v1?domains=` for
   `data.lubbocktx.gov`, `lubbocktx.gov`, `data.lubbocktx.us`,
   `opendata.lubbocktx.gov`, `data.lubbock.com`, `mylubbock.us` (all
   2026-08-30, `-m 20` + `Accept: application/json`). **All return Domain not
   found.** No Socrata portal.
2. **Hub discovery:** `https://lubbock.opendata.arcgis.com/api/search/v1/...`
   → HTTP 401 `private org id`; variant `data-lubbockcma.opendata.arcgis.com`
   → 401. No public Hub.
3. **ArcGIS Server enumeration:** `gis.lubbocktx.gov`, `gis.co.lubbock.tx.us`,
   `maps.lubbocktx.gov`, `services.lubbocktx.gov`, `gis.lubbock.tx.us` →
   DNS-resolve but **HTTPS ETIMEDOUT** (HTTP 000, 30 s). The live city server
   is **`pubgis.ci.lubbock.tx.us/server/rest/services`** (ArcGIS Server 10.91):
   20+ folders enumerated (`Basemaps`, `EnerGov`, `ESRI`, `Imagery`,
   `Internal`, `ITFacilitiesWebMap`, `LakeAlanHenry`, `Layers`, `Locators`,
   `OpenData`, `Planning`, `Police`, `PubViewer`, `Stormwater`, `SWBill`,
   `test`, `Testing`, `Utilities`, `WaterTap`, `Zoning`).
4. **AGOL org sweep:** ArcGIS Search API `orgid:eYXun6c1pgy8Qpta AND
   type:"Feature Service"` (paginated `num=100`) = **164 Feature Services**;
   full title scan for `permit|building|licen|case|311|develop|construc|
   ensoft|energov|violation|code` → **0** transaction layers (closest hits:
   `March2026_Geocoded_Codes`, `Resident Permit Only Parking Zone`). Owners
   `GISDS_CityofLubbock` (232), `THudson_CityofLubbock` (70),
   `CFields_CityofLubbock` (12), `LECDGIS` (14, Lubbock ECD), `LCTechLogin`
   (39, County) and `LubbockCo`-family also swept.
5. **Permits — EnerGov + Permitium:** City Permitting pages
   (`/923/Permits`, `/896/PermittingInspections`, `/903/Commercial-Permitting`,
   `/904/Residential-Permitting`) all link to
   `https://egovaccess.ci.lubbock.tx.us/EnerGov_Prod/SelfService/#/home`
   (Tyler EnerGov). SelfService is a JS Angular SPA (`data-ng-app="app.main"`,
   `webApiBaseUrl`), `/selfservice/api/*` → 404. Permitium
   `lubbocktx.permitium.com/rod` is the city's **vital-records / order-tracker**
   portal (links to DSHS vital statistics) — application/status UI, no bulk
   REST. No bulk permit FeatureServer found anywhere.
6. **311 — GovQA:** `/194/Submit-a-Report-Request` + `/607/MyLBK-App` →
   `https://lubbocktx.govqa.us/WEBAPP/.../SupportHome.aspx` (GovQA service
   request web form) — no bulk API, no incident FeatureServer. Code Cases
   Insights (`675d4ea...`, `e3a809a...`) source a gated
   `insightsservices2.arcgis.com/eYXun6c1pgy8Qpta/.../4aa8d521/WorkspaceServer`
   and `Layers/Council_Districts` basemap only — not raw case records.
7. **Deeds / sales — LCAD + OpenData Deeds:** `Layers/DashboardParcelData`
   FeatureServer L2 `Parcels` = LCAD tax roll (fields `PIN, APN, LCADID,
   OWNER_NAME, LANDVALUE, IMPVALUE, TOTALVALUE, EXEMPTIONS` — **no sale price,
   sale date, grantor/grantee, document ref**). `OpenData/City_Base_Data` L4-8
   "Property Acquisition / Alley Dedication / Property Divestiture / Park
   Dedication / Street Dedication **Deeds**" are City right-of-way & park
   **dedication polygons** (ROW/utility), not ownership deeds or sales.

## Platform

| Surface | What it is | Probe result 2026-08-30 (UTC) |
|---|---|---|
| `api.us.socrata.com/api/catalog/v1?domains=data.lubbocktx.gov` (etc) | Socrata membership probe (hint) | HTTP 404 `Domain not found` for all 6 domain variants |
| `https://lubbock.opendata.arcgis.com/api/search/v1/...` | ArcGIS Hub (hint) | HTTP 401 `private org id` — not public |
| `https://data-lubbockcma.opendata.arcgis.com/api/search/v1/...` | Hub variant | HTTP 401 private |
| `gis.lubbocktx.gov` / `gis.co.lubbock.tx.us` (etc, `arcgis/rest/services`) | City/County ArcGIS Server (hint hosts) | DNS-resolve; **ETIMEDOUT HTTP 000** (5 hosts) |
| `https://pubgis.ci.lubbock.tx.us/server/rest/services?f=json` | **City ArcGIS Server (live)** | HTTP 200, 20+ folders, 30+ root services, 10.91 |
| `https://services2.arcgis.com/eYXun6c1pgy8Qpta/arcgis/rest/services?f=json` | City hosted AGOL org | HTTP 200 ~160 hosted services |
| `orgid:eYXun6c1pgy8Qpta AND type:"Feature Service"` | AGOL org sweep | **164 Feature Services; 0 permit/311/license/deed transaction layers** |
| `https://egovaccess.ci.lubbock.tx.us/EnerGov_Prod/SelfService/` | **Permits portal — Tyler EnerGov SelfService** | HTTP 200 Angular SPA; `/selfservice/api/*` → 404; `webApiBaseUrl=/user/token` bearer |
| `https://lubbocktx.permitium.com/rod` | Permitium (`/923/Permits` link) | **Vital-records / order-tracker** portal (DSHS links) — app UI, no bulk REST |
| `https://lubbocktx.govqa.us/WEBAPP/.../SupportHome.aspx` | **311 — GovQA** | Service-request web form; no bulk API, no incident FeatureServer |
| `https://pubgis.ci.lubbock.tx.us/server/rest/services/Police/Crime_Map/FeatureServer/0` | Crime incidents (only live point layer) | 53,355 pts; `REPORTDATE` non-null 53,355 but **max 2024-09-24**; `OFFENDATE`/`LASTUPDATE` 0 non-null; SR 2276 |
| `https://pubgis.ci.lubbock.tx.us/server/rest/services/Layers/DashboardParcelData/FeatureServer/2` | LCAD Parcels | **Tax roll** — `LANDVALUE/IMPVALUE/TOTALVALUE/OWNER_NAME`; no sale price/date |
| `https://pubgis.ci.lubbock.tx.us/server/rest/services/OpenData/City_Base_Data/FeatureServer/4-8` | City "Deeds" layers | ROW/park **dedication polygons**, not ownership deeds/sales |
| `https://data.texas.gov/api/views/s7ft-44qi.json` (etc) | State super-feeds | HTTP 200 TREC / TDLR / TABC — county-filterable to Lubbock 48303 |

## Summary

| Family | Tier | Watermark (newest-row) | Geocode path | Register? |
|---|---|---|---|---|
| **PERMITS** | **3** | N/A — vendor-locked. Tyler **EnerGov SelfService** Angular SPA (`egovaccess.ci.lubbock.tx.us/EnerGov_Prod/SelfService/`), `/selfservice/api/*` → 404 (bearer `/user/token`). No bulk FeatureServer; EnerGov MapServer layers (`EnerGov/Egov_Ext`, `EgovExt`, `Egov_Ext_01`) are basemap/parcel/inspection-area **reference** only. Permitium `/rod` = vital records, not building permits. | EnerGov would expose situs **address** but no bulk rows/geometry to map | **no** — vendor-locked no-bulk-REST (ADR 0002 rejects a bearer-token scraper) |
| **311 / code cases** | **3** | N/A — GovQA web form (`lubbocktx.govqa.us/WEBAPP/.../SupportHome.aspx`); Code Cases are ArcGIS **Insights** workbooks gated behind `insightsservices2.arcgis.com/.../WorkspaceServer` + `Layers/Council_Districts` basemap; `March2026_Geocoded_Codes/July2026_Geocoded` is a **geocoder output** (Match_addr/etc), not case records. | no public incident FeatureServer to harvest coordinates | **no** |
| **SLA / business licenses** | **3** | none municipal — no license/business FeatureServer in org or pubgis. City licensing runs behind EnerGov. | — | **no** — use TX state super-feeds (Lubbock 48303) as SLA companion |
| **Deeds / sales** | **3** | none municipal — LCAD Parcels is a tax/assessment roll (`TOTALVALUE`, no sale); OpenData "Deeds" = ROW/park dedication polygons. | tax-roll polygons, not address-geocodable deed transactions | **no** — annual CAD roll, not transactional deeds |
| (bonus) **Crime** | **3** | `Police/Crime_Map` 53,355 pts, `REPORTDATE` max **2024-09-24** (~23 mo stale); `OFFENDATE`/`LASTUPDATE` 0 non-null; native SR 2276 | native point but stale | **no** — stale |

## Per-family findings

### Permits — Tier 3 (Tyler EnerGov vendor-locked)

- Portal: `https://egovaccess.ci.lubbock.tx.us/EnerGov_Prod/SelfService/#/home`
  (Tyler EnerGov Citizen Self Service, `data-ng-app="app.main"` Angular SPA).
  City permitting pages `/923/Permits`, `/896/PermittingInspections` link there.
- API: the self-service is bearer-auth JS (`globalsService.webApiBaseUrl =
  "<...>/user/token"`) — **no anonymous records/search REST**. Probed
  `/selfservice/api/`, `/getrecords`, `/records`, `/getrecord`, `/counts` →
  all `The resource cannot be found.` (404).
- ArcGIS EnerGov MapServers (`EnerGov/Egov_Ext`, `EgovExt`, `Egov_Ext_01`,
  `Egov_Ext_Test_*`, `Egov_Ext_AddrPrem*`) are **reference** — `Parcels`,
  `Addresses`, `Street Centerlines`, `Struct/Plumb/Elect Insp Areas`,
  `Design Review Districts`. **No BuildingPermits / CertificateOfOccupancy /
  permit-transaction layer.**
- Permitium `lubbocktx.permitium.com/rod` = vital-records **order tracker**
  (links `dshs.texas.gov/vs/reqproc`, `mailto:vitalstatistics@mylubbock.us`) —
  application/status UI, no bulk permit export. The `/923/Permits` page links
  to it for birth/death records, not building permits.
- AGOL org 164-Feature-Service scan → **0** permit layers.
- **Verdict:** POR is a credentialed Tyler EnerGov portal (JS SPA + bearer
  token) with no bulk watermark column and no `ORDER BY DESC LIMIT 3`
  facility. ADR 0002 platform-gating (new client = author scraper +
  bearer-token rotation) priced as a new platform → rejected. no change since
  prior sweep's Tier 3.

### 311 / Code Cases — Tier 3 (GovQA form + Insights gate)

- 311: `/194/Submit-a-Report-Request` and `/607/MyLBK-App` →
  `https://lubbocktx.govqa.us/WEBAPP/_rs/.../SupportHome.aspx` (GovQA service
  request web form). No API, no incident FeatureServer.
- Code Cases ("City of Lubbock Code Cases", "Monthly Code Cases") are ArcGIS
  **Insights** items (`e3a809a...` workbook, `dc380c9...` page, `675d4ea...`
  page). Their `data` JSON references only
  `insightsservices2.arcgis.com/eYXun6c1pgy8Qpta/.../4aa8d521/WorkspaceServer`
  (Insights **auth-gated workspace**, not a public FeatureServer) and the
  `Layers/Council_Districts/MapServer/0` basemap. `March2026_Geocoded_Codes/
  (L0 July2026_Geocoded)` is a **geocoder output table** (fields `Match_addr`,
  `Addr_type`, `PlaceName`, `Phone`, `URL`) — not raw case rows.
- Building Safety / Code Enforcement "Performance Metrics" are ArcGIS
  **Dashboard** items; the Building Safety item's `data` references only
  `https://ci.lubbock.tx.us/...` (website) — no underlying dataset.
- **Verdict:** no bulk incident watermark source; Insights/govQA gate it.

### SLA / business licenses — Tier 3 (none municipal)

- No license/business-registration FeatureServer in the 164-service org, none
  on pubgis, none under Lubbock ECD (`LECDGIS`) or county owners. Municipal
  business licensing runs behind the same EnerGov credential wall.
- State companion (verified live): `data.texas.gov/api/views/s7ft-44qi`
  (TREC), `7358-krk7` (TDLR), `7hf9-qc9f` (TABC) — HTTP 200, county-filterable
  to Lubbock 48303 via `SocrataClient` + FIPS crosswalk (0 new client).

### Deeds / sales — Tier 3 (tax roll + dedication polygons)

- `Layers/DashboardParcelData/FeatureServer/2` `Parcels`: fields `PIN, APN,
  LCADID, SUBDIVISION, LEGAL_DESCRIPTION, OWNER_NAME, OWNER_ADDRESS,
  LANDVALUE, IMPVALUE, TOTALVALUE, EXEMPTIONS, SQUARE_FOOT, STATUS` (+
  `created_user/date`, `last_edited_*`) — **assessment roll, no sale**. SR 2276.
- `OpenData/City_Base_Data` L4-8 (and mirrored `BasemapData`) "Property
  Acquisition Deeds", "Alley Dedication Deeds", "Property Divestiture Deeds",
  "Park Dedication Deeds", "Street Dedication Deeds", L9-15 "Easements",
  "Railroad Deeds", "State ROW Deeds" — all **City right-of-way / park /
  utility dedication polygons**, not ownership deeds or sales transactions.
- LCAD portal `lubbockcad.org` / `www.lubbockcad.org` HTTP 200 (appraisal
  search HTML, no bulk sales feed). County GIS hosts
  (`gis.co.lubbock.tx.us`, `gisservices.halff.com` Lubbock/Lubbock_Co) →
  contours/stormwater/FEMA — no parcels sales layer.

## Hosts probed and rejected

| Host | Result |
|---|---|
| `api.us.socrata.com/api/catalog/v1?domains=data.lubbocktx.gov` (and 5 variants incl `mylubbock.us`) | **Domain not found (404)** — no Socrata |
| `https://lubbock.opendata.arcgis.com/api/search/v1/...` + `data-lubbockcma` | **HTTP 401 private org** — no public Hub |
| `gis.lubbocktx.gov` / `maps.lubbocktx.gov` / `services.lubbocktx.gov` / `gis.co.lubbock.tx.us` / `gis.lubbock.tx.us` | DNS-resolve; **ETIMEDOUT HTTP 000** (30 s) — no browseable server |
| `https://pubgis.ci.lubbock.tx.us/server/rest/services` | Live (10.91) — infra/basemap/parcel only |
| `https://services2.arcgis.com/eYXun6c1pgy8Qpta/arcgis/rest/services` | Live hosted org; 164 Feature Services, **0 transaction layers** |
| `https://egovaccess.ci.lubbock.tx.us/EnerGov_Prod/SelfService/` | Toby EnerGov Angular SPA, bearer auth, `/selfservice/api/*` → 404 |
| `https://lubbocktx.permitium.com/rod` | vital-records / order tracker — not building permits |
| `https://lubbocktx.govqa.us/WEBAPP/.../SupportHome.aspx` | GovQA 311 web form — no bulk API |
| `https://insightsservices2.arcgis.com/eYXun6c1pgy8Qpta/.../WorkspaceServer` | Auth-gated Insights workspace — not public |
| `https://pubgis.ci.lubbock.tx.us/server/rest/services/Police/Crime_Map/FeatureServer/0` | Live but **stale** — max `REPORTDATE` 2024-09-24 |
| `https://pubgis.ci.lubbock.tx.us/server/rest/services/Layers/DashboardParcelData/FeatureServer/2` | LCAD tax roll — no sale price/date |
| `gisservices.halff.com/ags/rest/services` (Lubbock, Lubbock_Co) | contours / stormwater / FEMA only |
| `https://data.texas.gov/api/views/s7ft-44qi.json` (etc) | **Live state super-feed** (TREC/TDLR/TABC) — SLA companion for 48303 |

## Recommendation

**REJECT Lubbock, TX (`lubbock`, Lubbock County 48303) for municipal leaf
registration — Tier 3 across all families.** No municipal bulk REST endpoint
satisfies ADR 0004's row-level watermark + geocode requirements: Socrata is
Domain-not-found, Hub is private (401), City/County ArcGIS Server hint hosts
ETIMEDOUT, the live city server + hosted AGOL org (164 Feature Services)
carry only infrastructure/basemap/parcel data, permits are a **credentialed
Tyler EnerGov SelfService** JS SPA (/selfservice/api → 404), 311 is a
**GovQA web form** (with only Insights-gated Code Cases dashboards), Parcels
are an **LCAD tax roll**, and the sole live point layer (`Police/Crime_Map`)
is **stale** (2024-09-24). The higher-leverage move is to treat Lubbock as a
**state-feed-only** county via existing `SocrataClient` on `data.texas.gov`
(`s7ft-44qi`, `7358-krk7`, `7hf9-qc9f` filtered to 48303) — the same pattern
already adopted for the tier-3 Texas cluster.

**Do not create leaf files** (`cities/lubbock.py`, `field_maps_lubbock.py`,
`test_producers_lubbock.py`) — no tier justifies leaf build. **Do not take
spine hold** — no `CityId.lubbock` / `ALIASES` / `REGISTRY` entry, no
`METRO_META` dashboard chip, no snapshot/export wiring, no product facts.
The interlock gate (`pytest -m interlock`) is not implicated. Re-probe
trigger: a future public `.../FeatureServer`/`.../datastore_search` permit or
311 layer with `ORDER BY <watermark> DESC LIMIT 3` freshest-row <60d and
`esriGeometryPoint` (WGS84 4326) or address-geocodable column — or a Socrata
`4x4` view on `data.lubbocktx.gov` / `data.ci.lubbock.tx.us` — would be
necessary but is not observed 2026-08-30.

*Evidence recorded 2026-08-30 UTC with row-level verification or explicit
"N/A — no bulk endpoint" where the surface itself gates enumeration. Shallow
seal: City AGOL org fully enumerated (164 Feature Services, paginated);
EnerGov SelfService API routes probed; all pubgis folders enumerated; county
hint hosts probed for DNS + TCP; state super-feeds name-checked live.*
