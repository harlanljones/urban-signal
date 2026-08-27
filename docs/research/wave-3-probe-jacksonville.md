# Wave 3 Phase-0 probe — Jacksonville, FL

**Date of survey: 2026-08-27.** Every host, DNS answer, catalog hit, watermark,
and row below was probed live this day. Linear US-203. Prior context:
`opendata.coj.net` DNS-failed in the 2026-08 Hub sweep
(`wave-2-city-candidates.md`); the 2026-08-24 platform pass
(`nine-unidentified-metros-platform.md`) called the city skip-grade and treated
the open-data hostname as retired. This re-probe retries DNS, hunts a successor
portal, and row-reads all four families (permits / 311 / SLA / deeds). Catalog
`modified` is not evidence — only newest-row-by-watermark counts.

Success criterion (Wave 3 / ADR 0004): live **and** (native geocode **or**
address-geocodable). Live means a current-window row, not a portal that exists.

## Verdict

**Register none. Wave-3-ready: no.** All four families are **Tier 3**. No
registration contract. `opendata.coj.net` is still DNS-dead; there is no
successor open-data catalog. Working surfaces are an ArcGIS Server (GIS
reference layers), an AGOL org of operational maps, a WAF-gated permitting
SPA, a Salesforce 311 portal, and monthly Property Appraiser file dumps.

| Family | Tier | Live? | Watermark (newest row) | Geocode path | Why not Wave 3 |
|---|---|---|---|---|---|
| Permits | **3** | no public bulk feed | — | — | JAXEPICS is an MSAL Angular SPA; `jaxepicsapi.coj.net` is Akamai-403 without a token. Power BI dashboards are aggregates. |
| 311 | **3** | no public feed | — | — | MyJax is Oracle/Salesforce RightNow (`myjax.custhelp.com`). Transparency dashboards are Power BI, not row exports. Hosted graffiti/litter/nuisance layers 404 anonymously. |
| SLA | **3** | no | `Business_Data_WFL1` is a 2020 JSO snapshot (59,765 rows, **no date column**) | native `LATITUDE`/`LONGITUDE` on the stale snapshot | Local Business Tax Receipts live on `county-taxes.net/fl-duval/btexpress` (search/pay UI only). |
| Deeds | **3** | monthly extract, not live REST | PA sales file newest sale **2026-07-22** (file as-of 2026-08-10, HTTP `Last-Modified` 2026-08-12); GIS last-sale **2026-08-10** | site address on rec04; parcels REST has native `LAT`/`LONG` 407,986 / 407,986 | Last-sale parcel snapshot is the wrong signal (Seattle deeds ADR). The transaction file is a 1 GB monthly fixed-width dump with ~5-week lag and **no observed sale-price field**. |

## DNS — `opendata.coj.net` (retry)

**Still dead.** The 2026-08 failure was not a transient blip.

| Host | DNS 2026-08-27 |
|---|---|
| `opendata.coj.net` | **UNRESOLVED** (no A / AAAA / CNAME) |
| `www.opendata.coj.net`, `open-data.coj.net` | UNRESOLVED |
| `data.coj.net` | UNRESOLVED |
| `opendata.jacksonville.gov`, `data.jacksonville.gov` | UNRESOLVED |
| `data.duvalcounty.gov`, `opendata.duvalcounty.gov` | UNRESOLVED |
| `pa.coj.net`, `myjax.coj.net`, `311.coj.net`, `www.jax311.com` | UNRESOLVED |
| `gis.coj.net` | UNRESOLVED |
| `reports.coj.net` | UNRESOLVED (linked from JAXEPICS JS) |

Socrata discovery (`api.us.socrata.com/api/catalog/v1?domains=`) for
`coj.net`, `jacksonville.gov`, `data.coj.net`, `opendata.coj.net`,
`data.jacksonville.gov`, `jaxpublic.com` → **Domain not found**. CKAN
`/api/3/action/package_search` on the same guessed hosts → NXDOMAIN or
city-website 404/302 HTML. No Socrata, no CKAN.

## Platform

Jacksonville (consolidated city-county with Duval) does **not** run an
open-data catalog. Working surfaces:

| Host | What it is | Probe |
|---|---|---|
| `https://maps.coj.net/coj/rest/services` | **ArcGIS Server 11.1** (JaxGIS) | 36 folders; live `CityBiz/Parcels` MapServer. HTTP 301 → HTTPS. |
| `https://maps1.coj.net/ags115/rest/services` | ArcGIS Server **11.5** (sibling) | Same folder names (`CRM`, `DuvalProperty`, `CityBiz`, `SolidWaste`) but **empty** except `ParkingMeters` + `SepticTanks`. |
| AGOL org `NXfNVaFp7QMxnE3j` (`jaxgis.maps.arcgis.com`) | City GIS org | **88** Feature Services — parks, evacuation, solid-waste hauler polygons, a 2020 business snapshot. **0** hits for permit / 311 / license / deed. |
| `jaxgis.opendata.arcgis.com` / `coj.opendata.arcgis.com` (and `.hub.arcgis.com` twins) | Unfinished Hub shells | Site title "ArcGIS Hub Home" / "Create your own initiative…". Dataset collection `numberMatched` 83 / 73 is the **org's operational layers**, not a public catalog. `/data.json` and DCAT **404**. `api/v3/datasets` unscoped total ~21 M (global Hub, ignore). |
| `jaxready-jaxgis.hub.arcgis.com` | EOC Hub | **1** dataset (`Tropical_Weather_Hosted`). |
| `jaxepics.coj.net` | JAXEPICS permitting SPA | Angular + Calcite; MSAL (`login.microsoftonline.com`). API host `jaxepicsapi.coj.net` → Akamai **403 Access Denied** with and without `Origin: https://jaxepics.coj.net`. |
| `myjax.custhelp.com` | MyJax 311 | Oracle Service Cloud / RightNow. Submit/track UI only. |
| `www.jacksonville.gov/departments/property-appraiser/data-offerings` | Duval PA file dumps | Monthly zip: tax roll, GIS shapefile, **sales fixed-width text**. Newest sales zip as-of **2026-08-10**. |
| `or.duvalclerk.com` / `acclaim.duvalclerk.com` | Clerk official records | Interactive search; bulk/automated harvest prohibited (AOSC). |
| `stateofjax.org` | mySidewalk census dashboard | Not municipal event feeds. |
| `gisportal.coj.net` | ArcGIS Enterprise portal | `portals/self` answers; Hosted FeatureServers listed on AGOL **404** anonymously (token). Portal search "Citizen Requests" is the **Enterprise default template group**, not a 311 layer. |

**Do not confuse** AGOL org `p6AtkBQ0z2Evsivu` / owners `gisadmin_coj`,
`hherrmann_coj` — that is **Jacksonville, NC** (`jacksonvillenc.gov` /
Onslow County), not Florida.

Guessed Hub hosts (`jacksonville.opendata.arcgis.com`, `duval.opendata.arcgis.com`,
`jax.opendata.arcgis.com`, `cityofjacksonville.opendata.arcgis.com`,
`jacksonvillefl.opendata.arcgis.com`, and 10 more) return Hub **401**
(site does not exist). `jaxgis.coj.net` TCP-times out. `maps.jaxgis.com`
has a hostname/cert mismatch.

The existing `ArcGISClient` and `CSVClient` would cover every surface that
*does* answer; no fifth client is implied. Nothing in the four families is
registrable.

## Method

DNS sweep of catalog-shaped hostnames. Socrata discovery + CKAN
`package_search` negatives. ArcGIS.com item search, then org-scoped
`orgid:NXfNVaFp7QMxnE3j type:"Feature Service"` (88 services, paginated).
REST directory walk of `maps.coj.net/coj` (every folder) and
`maps1.coj.net/ags115`. Hub collection listing on `jaxgis` / `coj`
opendata + hub hosts. Row-level `returnCountOnly`, `outStatistics`, and
`orderByFields=<watermark> DESC` on every survivor. JAXEPICS `main-*.js`
chunk grep for API hosts, then unauthenticated GETs. PA sales zip:
inflate + record-type inventory + `MM/DD/YYYY` max on rec03.

## Permits — Tier 3

Transactional permits live in **JAXEPICS** (Jacksonville Enterprise
Permitting, Inspections and Compliance System), launched 2024–25 and still
absorbing civil/plat review as of 2026-02-26 (`jaxdailyrecord.com`). Online
submission is required (`jaxepics.coj.net`). Guest search exists in the SPA;
there is **no public bulk REST**.

| Surface | Result |
|---|---|
| `GET https://jaxepics.coj.net/api`, `/swagger`, `/openapi.json`, `/odata` | SPA HTML (client-side routes) or IIS 404 |
| `jaxepicsapi.coj.net` (from bundled JS; also `jaxcivilplan.coj.net`) | Akamai **403 Access Denied** on `/`, `/api`, `/swagger/v1/swagger.json`, `/api/Documentations/DownloadFile/42` |
| AGOL org search `permit` / `JAXEPICS` | **0** Feature Services |
| `maps.coj.net` folder walk | No permit / inspection / building-permit MapServer. `CapitalProjects` MapServer has **0 layers**. |
| Mayor's Permitting / Permitting Maps dashboards | Power BI aggregates sourced from JAXEPICS — not row-level |
| Third-party PermitStack | Claims an ArcGIS Hub source that **does not exist**; out of scope |

Org Feature Service `Requests_submit`
(`…/Requests_submit_5b0c4c181fcf4f60bb9ce96881318007/FeatureServer/0`,
layer "Requests") looks like a Survey123 parks/work-order form
(`reqcategory`, `pocemail`, `created_date`). Anonymous `query` returns
**"This operation is not supported"** — not a public 311/permits table.

Charlotte / Atlanta precedent: Accela/custom permitting HTML without a bulk
API is **genuine absence**, not a search miss.

## 311 — Tier 3

MyJax is the city's 311. Public surfaces:

- Submit/track: `https://myjax.custhelp.com/` (Oracle Service Cloud).
- Aggregates: `jacksonville.gov/mayor/transparency-dashboards/…/myjax-dashboard`
  (Power BI; "address labeled 00" = missing address). No CSV / FeatureServer /
  Open311 / Socrata table.
- AGOL search `MyJax` in org `NXfNVaFp7QMxnE3j`: **0**.
- `HydrantsInspections/JEA_Service_Requests_Background` on `maps.coj.net`:
  **0 layers** (basemap stub). JEA web maps in the org are **utility** work
  orders, not citizen 311.
- Hosted code-enforcement-ish layers (`Graffiti_Cluster`, `Litter_*`,
  `Nuisance_Yard`, …) advertised at
  `gisportal.coj.net/server/rest/services/Hosted/<name>/FeatureServer` →
  **HTTP 404** without a portal token.

A public-records export of MyJax is possible under Ch. 119 but is not a
feed.

## SLA — Tier 3

Local Business Tax Receipts (occupational licenses pre-2007) are issued by
the Duval County Tax Collector (`taxcollector.jacksonville.gov/taxes/local-business-tax`).
The system of record is `https://county-taxes.net/fl-duval/btexpress`
(find/pay UI). No bulk dataset, GIS layer, or CKAN/Socrata table.

Closest AGOL hit: `Business_Data_WFL1`
(`https://services1.arcgis.com/NXfNVaFp7QMxnE3j/arcgis/rest/services/Business_Data_WFL1/FeatureServer/0`),
layer name **`BusinessData_2020_JSO`**, 59,765 points, SIC/NAICS + native
`LATITUDE`/`LONGITUDE` + `PRIMARY_ADDRESS`. **Zero date fields.** This is
the 2020 static JSO snapshot already rejected in the 2026-08-24 pass. Do
not register.

## Deeds — Tier 3

Two related surfaces; neither is a Wave-3 feed.

### A. `CityBiz/Parcels` MapServer — last-sale snapshot (reject)

- **URL:** `https://maps.coj.net/coj/rest/services/CityBiz/Parcels/MapServer/0`
- **Platform:** ArcGIS Server 11.1, polygon, `maxRecordCount=2000`.
- **Rows:** **407,986**. Native `LAT`/`LONG` (and `X_WGS`/`Y_WGS`) on
  **407,986 / 407,986**. Site address `LONGNAME` / `STREET_NO`+`ST_NAME`.
- **Watermark:** split ints `SALESLYY` / `SALESLMM` / `SALESLDD`.
  `outStatistics` max `SALESLYY` = **2026**. Newest ordered row:
  **2026-08-10** (`SALESLYY=2026, SALESLMM=8, SALESLDD=10`), e.g. RE
  `162145 9825` / `1095 TOLKIEN LN`.
- **Windows:** 2026 YTD last-sale **21,954**; 2026-07 **1,685**; 2026-08
  **21**. August is thin because the layer tracks the PA extract as-of
  2026-08-10, not a live recorder stream.
- **Missing:** no `SALEPRICE` / deed book / instrument number. Assessed
  values (`CAMA_VAL`, `TOT_LND_VA`, `TOT_BLD_VA`) are not transaction
  amounts.

This is a **one-row-per-parcel last-sale overlay**. `docs/research/seattle-deeds-replacement.md`
rejects exactly this shape ("no new row per sale; watermark would not move
with sales"). Las Vegas deeds were registered only because that parcel
table carried `SALEPRICE` / `SALETYPE` / `DOCNO` as a sales extract, not
because last-sale dates existed. **Do not register.**

Downtown-only AGOL clips (`Parcels_Downtown`,
`parcels_downtown_20260421`) are geographic subsets of the same snapshot.

### B. Duval PA monthly sales file — transaction extract, too laggy / incomplete

- **Page:** `https://www.jacksonville.gov/departments/property-appraiser/data-offerings`
- **File probed:** `DCPAO-REAL-ESTATE-SALES-FIXED-FORMAT-TEXT-FILE-08-10-2026.zip`
  (94 MB zip / **1,019,440,222** byte text;
  `Last-Modified: Wed, 12 Aug 2026 13:43:52 GMT`).
- **Layout:** NAL-style record types, CRLF, Latin-1.

| Rec | Count | Role | Width |
|---|---|---|---|
| `00001` | 643,694 | owner / mailing | 311 |
| `00002` | 2,136,273 | legal description | 67 |
| `00003` | **3,479,623** | sale history (grantor, OR book/page, sale date, record date, qual code) | 156 |
| `00004` | 682,377 | **site address** | 175 |

- **Watermark (rec03 `MM/DD/YYYY` tokens):** min 2000-01-01, max
  **2026-07-22**. Sample newest:
  `000030071250808R … 14IQCLB07/21/2026 … 07/22/2026 … 100`.
- **2026-07 rec03 lines containing a July-2026 date: 217** (June 5,896 /
  May 7,884). July is a partial, low-volume cutoff — not a live month.
- **Sale price:** not present on rec03 in the bytes observed. Qual code
  `100` and book/page are. `document_amount` would be null/0.
- **Geocode path:** rec04 site address (e.g. `N US 301 HWY`, Jacksonville
  32234) → ADR 0004, **or** join rec03 RE to `CityBiz/Parcels` `RE` for
  native lat/long. Address-geocodable in principle.
- **Cadence:** monthly. Newest sale **2026-07-22** on a 2026-08-27 probe
  is ~36 days lag. Milwaukee's 2-month-lag permits were already "marginal";
  Cincinnati deeds is a **daily** county CSV. This is not that.

Companion monthly GIS zips (`GIS-Aug-2026.zip`) are parcel shapefiles, not
a deed stream. Florida DOR SDF is a three-times-a-year roll submission —
worse cadence. Clerk Acclaim is search-only.

A later wave *could* build a Cincinnati-style `CSVClient` parser for the
fixed-width dump **if** (1) sale price is confirmed in the layout PDF or
an SDF join, and (2) monthly lag is accepted as `expected_cadence_days: 45`.
That is not Wave-3 "easiest verified win" work.

## What changed vs 2026-08-24

The earlier pass was right that `opendata.coj.net` is retired and that
JAXEPICS / MyJax / PA downloads are not REST feeds. This pass **did**
find the real GIS platform (`maps.coj.net` ArcGIS Server 11.1 + org
`NXfNVaFp7QMxnE3j`) and row-read it. None of the four families graduate.
Treat Hub hostname guesses as exhausted; the successor to the dead portal
is **GIS + file dumps**, not a catalog.

## Wave-3-ready?

**No.** Do not add `jacksonville` / `jax` / `duval` to `CityId` /
`REGISTRY` from this probe. Partial-metro registration needs at least one
Tier 1/2 family; Jacksonville has zero.
