# Wave 3 Phase-0 probe — Atlanta, GA

**Date of survey: 2026-08-27.** Every host, TLS handshake, catalog hit, watermark,
and row below was probed live this day. Linear US-198. Prior context:
`opendata.atlantaga.gov` failed TLS in the 2026-08 Hub sweep
(`wave-2-city-candidates.md`); the 2026-08-24 platform pass
(`nine-unidentified-metros-platform.md`) called the city skip-grade on a frozen
2019–24 permit CSV. This re-probe retries TLS, resolves the working platform,
and row-reads all four families (permits / 311 / SLA / deeds). Catalog
`modified` is not evidence — only newest-row-by-watermark counts.

Success criterion (Wave 3 / ADR 0004): live **and** (native geocode **or**
address-geocodable). Live means a current-window row, not a portal that exists.

## Verdict

**Register none. Wave-3-ready: no.** All four families are **Tier 3**. No
registration contract.

| Family | Tier | Live? | Watermark (newest row) | Geocode path | Why not Wave 3 |
|---|---|---|---|---|---|
| Permits | **3** | no | `OrigOpened` **2026-01-29** on unofficial `Building_Permit_latest`; Hub CSV `DATE OPENED` **2024-04-26** | native points on the stale AGOL extract; lat/lng on the CSV archive | Extract froze ~7 months ago; Accela ACA is HTML-only (Charlotte precedent) |
| 311 | **3** | no public feed | — | — | ATL311 is Dynamics 365 self-service; no Open311 / FeatureServer / Socrata table |
| SLA | **3** | no citywide live feed | citywide GBL `USER_Business_License_Issued_Da` **2022-06-01**; AMS-district clip `license_issued` **2026-07-30** (508 rows, 0 in Aug) | point / address mixed; clip is not citywide | Stale citywide snapshot + geographically clipped Main Street extract |
| Deeds | **3** | no | Fulton `Tyler_YearlySales` last published year **2022**; city tax parcels have no sale date | polygon parcels, no transaction stream | Yearly archive / snapshot parcels, not live conveyances |

## TLS — `opendata.atlantaga.gov` (retry)

**Still dead.** The 2026-08 failure was not a transient blip.

| Check | Result (2026-08-27) |
|---|---|
| DNS A | `52.247.175.244` → `gcws-prod-bn1-003.usgovvirginia.cloudapp.usgovcloudapi.net` (Azure Government) |
| Cert subject | `CN=*.azurewebsites.us` (Microsoft TLS G2 RSA CA OCSP 02) |
| SAN | `*.azurewebsites.us` and usgovvirginia Azure Web App names **only** — hostname `opendata.atlantaga.gov` is absent |
| `notBefore` / `notAfter` | 2026-08-27 15:41:59 GMT → 2027-02-23 15:41:59 GMT (cert rotated **today**, still wrong name) |
| Strict HTTPS | `curl: (60) SSL: no alternative certificate subject name matches target hostname` |
| HTTPS with `-k` | **HTTP 404** body `Microsoft Azure Web App - Error 404` |
| Plain HTTP | **HTTP 404**, same Azure 404 page |

The custom domain still points at an empty Azure Government web app. Do not
treat a future TLS fix as a data portal until the 404 also goes away.

## Platform

Atlanta city is **not** on Socrata or CKAN. Working surfaces:

| Host | What it is | Catalog size / version |
|---|---|---|
| `dpcd-coaplangis.opendata.arcgis.com` | **ArcGIS Hub** — "City of Atlanta – Open Data Hub", owner org `5RxyIIJ9boPdptdo` (`COA_DCP_GIS`) | DCAT **57** datasets |
| `https://gis.atlantaga.gov/dpcd/rest/services` | **ArcGIS Server 11.3** backing the Hub (Experience Builder title: Department of City Planning GIS) | folders: AdministrativeArea, DocumentArchive, LandUsePlanning, OPALMapServices, ReferenceData, Tolemi, Utilities |
| `aca-prod.accela.com/ATLANTA_GA` | Accela Citizen Access HTML portal ("Atlanta Online Portal") | live UI, **no public bulk REST** |
| `www.atl311.com` | Microsoft Dynamics 365 Customer Self-Service (Power Apps / Dataverse) | live UI, **no Open311** |
| `sharefulton.fultoncountyga.gov` / `data.fultoncountyga.gov` | Fulton County **Socrata** (not the city) | 1,984 / 195 catalog hits; KPI + aggregate + workflow tables |
| `gismaps.fultoncountyga.gov/arcgispub2` | Fulton County ArcGIS Server | parcels + yearly sales through **2022** |

Hub DCAT search (`/api/search/v1/collections/dataset/items`) for the four
families: **permit → 1 hit** (`All Building Permits 2019-2024`); **311 / license /
deed / sale / service request → 0**. The Hub is planning/GIS (parcels, zoning,
NPUs, parks, MARTA), not a live permit/311/license/deed catalog.

Guessed Hub hosts (`atlanta.opendata.arcgis.com`, `atlantaga.opendata.arcgis.com`,
`coa.opendata.arcgis.com`, `cityofatlanta.opendata.arcgis.com`,
`open-atlanta.opendata.arcgis.com`, `coaplangis.opendata.arcgis.com`) return
empty/401 catalogs. `data.atlantaga.gov` DNS-fails. City domain
`api.us.socrata.com/api/catalog/v1?domains=atlantaga.gov` is 404.
`gis.atlantaga.gov/api/3/action/package_list` is 404 (not CKAN).

Tyler-hosted `egimpgis.tylertech.com/.../Atlanta/City_of_Atlanta/MapServer` is
reference GIS (limits, addresses, parcels, streets) — no permit/311/license/deed
layers.

DeKalb GIS (`gis.dekalbcountyga.gov`, Atlanta's second county) presents an
**expired** cert (`notAfter` 2025-09-02) and **HTTP 502** even with `-k`. Not a
working deeds fallback.

## Permits — Tier 3

Transactional permits live in **Accela**. The public bulk surfaces are extracts,
not the system of record.

### Accela Citizen Access (live UI, not a feed)

`https://aca-prod.accela.com/ATLANTA_GA/` returns 200, title "Atlanta Online
Portal", Building module search. Same class as Charlotte: paginated HTML, no
anonymous FeatureServer / Socrata / CKAN table. **Do not register. Do not
scrape.**

`AccelaMap/MapServer` on `gis.atlantaga.gov/dpcd` is **404**.

### Hub official extract — frozen CSV (confirms 2026-08-24)

Item `655f985f43cc40b4bf2ab7bc73d2169b`, type CSV, owner `gpickren2`, Hub title
**All Building Permits 2019-2024**. 38,107 rows.

- Watermark `DATE OPENED` (text `M/D/YYYY`) — newest **2024-04-26**
  (`BB-202403714`, 2650 Proctor Dr NW). Prior survey's 2024-04-25 was the same
  archive; one-day difference is parse/sort, not a refresh.
- `RECORD STATUS DATE` carries a **2042-03-22** sentinel — do not watermark on it.
- Native `latitude`/`longitude` on 38,107 / 38,107 rows; address on 38,099.
- Year counts: 2019–2023 full-ish; 2024 = 1,952; **2025–2026 = 0**.
- Useful only as a historical backfill corpus if a live feed ever appears.

Lexicographic max on `DATE OPENED` is `9/9/2023` and is **wrong** — always parse.

### Unofficial AGOL "latest" extract — froze 2026-01-29

`Building_Permit_latest` FeatureServer
(`https://services5.arcgis.com/5RxyIIJ9boPdptdo/arcgis/rest/services/Building_Permit_latest/FeatureServer`,
item `d3513091fa7744138c17c670fd2ee8c6`, owner `gpickren2`, snippet *"Test
Official building permit data…"*, AGOL `modified` **2026-01-29T09:00:32Z** —
here metadata and rows agree).

| Layer | Rows | Geometry | Newest `OrigOpened` | Newest `StatusDate` |
|---|---|---|---|---|
| 0 `Building_Permit_latest_points` | 36,115 | point (Web Mercator) | **2026-01-29** | 2026-01-29 03:33 UTC |
| 1 `Building_Permit_latest_objects` | 3,500 | none (ungeocoded table) | 2026-01-28 | 2026-01-28 15:31 UTC |

- 1,028 rows opened in 2026-01; **0 in the last 30 days**; 10,363 in 2025; 8,604 in 2024.
- Native point geometry; `Address` nonempty on 36,115 / 36,115; `DisplayX`/`DisplayY`; `PARCEL`; `JOB_VALUE`; `TypeCombo`/`statusP`; `ACA_Link` back to Accela.
- Newest row: `BB-202600801`, 797 Vedado NE, Multi Family Miscellaneous, status "ACA Pending" / "Under Review (not issued)".
- Sibling `Building_Permit_Tracker` layer 2 (`BuildingPermits_ResComm_AllStatuses_AGOL`) is older: max `OrigOpened` **2024-11-18**. AMS-district clips stop in **2022-07**.

If this layer started moving again (newest `OrigOpened` within ~30 days of a
re-probe) it would be **Tier 1** (live + native points) — **thaw-watch only**,
not a registration. Today it is a seven-month-stale extract sitting outside the
official Hub catalog.

OpenDataService1 on the official GIS server has zoning / footprints /
moratoriums / special-use cases — **no building-permit table**.

## 311 — Tier 3

No published dataset on the Hub, DCP org (`orgid:5RxyIIJ9boPdptdo` 311 search =
0 Feature Services), Fulton Socrata, or city GIS.

ATL311 is a **Dynamics 365 Customer Self-Service** portal at `https://www.atl311.com/`
(cookies `Dynamics365PortalAnalytics`, `x-ms-portal-app`, Power Apps CSP).
`/open311/v2/services.json` **302**s to `/en-US/open311/v2/services.json` (portal
HTML, not GeoReport). Azure APIM `apim-d365atl311-prod.azure-api.net/open311/v2/services.json`
is 404. `311.atlantaga.gov` / `atl311.atlantaga.gov` DNS-fail. SeeClickFix has a
civic `seeclickfix.com/atlanta` page; Open311 `jurisdiction_id=atlanta` is 404.

Not confirmed absent from every upstream system — confirmed **absent as a public
bulk feed** on every portal this probe can see. Residents file through ATL311;
there is no row-level open table to watermark.

## SLA (business licenses) — Tier 3

No license dataset on the official Hub. Several AGOL extracts in the DCP org,
all unofficial (`gpickren2`):

| Layer | Rows | Watermark newest | Geography | Notes |
|---|---|---|---|---|
| `GBL_WFL1` "LicensedBusinesses" | 26,643 | `USER_Business_License_Issued_Da` **2022-06-01**; year max **2023** | citywide points | Stale occupational-tax dump; expiration max 2022-12-31 |
| `BusinessLicenses_2024_Revenue` | 19,297 | `BUSINESS_LICENSE_YEAR` = **2024**; `DATE_OF_OPENING_IN_ATLANTA` sentinel **2089-01-01** | citywide points + `latitude`/`longitude` | Annual snapshot, not a stream |
| `Business_Licenses_2026` layer 50 `Revenue2026BusinessLicenses_AMS` | **508** | `license_issued` **2026-07-30**; 14 since 2026-07-01; **0 in August** | Atlanta Main Street districts only | Address-geocodable (`street_address_1`); lat/lng often null. Too small and too clipped to be a city SLA feed |

`OccupTaxWaiver` is a zoning-eligibility polygon (68 rows), not licenses.
Granicus STR MapServer on DCP GIS is tax-parcel polygons with `LASTUPDATE`
**2021-05-18**, not a live STR register. `Short_Term_Rental_Permits` exists as an
AGOL item but is another district/analysis layer, not a Hub feed.

Fulton Socrata "license" hits are weapons-license KPIs and clinical credentialing
measures — not occupational tax.

## Deeds — Tier 3

City tax parcels (`gis.atlantaga.gov/dpcd/.../TaxParcel/MapServer/0` and Hub
"Tax Parcels 2025") carry owner / assessed value / `LASTUPDATE` — **no
`SALE_DATE` / price / deed book**. Snapshot cadastre, not conveyances.

Fulton GIS `Tax/Tyler_YearlySales` publishes **2018–2022** only (2022 layer:
12,875 polygons, `ParID` + `TaxYear` + `Price`). No 2023–2026 layers.
`Tyler_TaxParcels` and `Tax_ParcelCurrentDigest` have owner/address/assessed
value, **no sale fields**.

Fulton Socrata `7dey-txkb` "Tax Deed Activity" is **live** (`created_date` max
**2026-08-11**, 28,518 rows) but it is an internal **deeds-processing workflow**
(assignee, task queue, `workflow_type_name=Deeds Processing P1`) — not
grantor/grantee/price/parcel sales. `tg8q-cswr` "Monthly Building Permit Counts"
is Census SOCDS **county aggregates** (Autauga County, AL in row 1), not Atlanta
permits.

Recorded instruments sit with the Clerk / GSCCCA (not a free bulk REST). Sheriff
tax-sale PDFs are foreclosure lists, not the deeds family.

Under ADR 0007 a *live* Fulton sales layer would be a **separate county**
registration, not an Atlanta division. Nothing live exists to register.

## Registration contract

**None.** No Tier 1/2 feed. Do not add `atlanta` to `CityId` / `REGISTRY` on this
evidence.

Thaw-watch (not a contract): `Building_Permit_latest` FeatureServer layer 0,
watermark `OrigOpened`, native points. Re-probe row-level before any future wave;
require newest row ≤30 days old **and** a decision that an unofficial DCP-org
extract is an acceptable system of record versus Accela.

## Method (this probe)

1. TLS + DNS + HTTP on `opendata.atlantaga.gov` (strict and `-k`) and a hostname
   mesh (Hub guesses, `gis`/`agis.atlantaga.gov`, Accela, ATL311, Fulton, DeKalb).
2. Platform detection: Socrata discovery API, CKAN `package_list`, Hub DCAT +
   collection search, ArcGIS Server `?f=json` recursion, AGOL
   `sharing/rest/search` scoped to org `5RxyIIJ9boPdptdo`.
3. Every survivor: layer metadata, `returnCountOnly`, `outStatistics` max on
   date fields, `orderByFields=<watermark> DESC` newest row, geocoding columns,
   30-day / YTD counts. CSV archive parsed with real `strptime` (not
   lexicographic max).
4. Accela / ATL311 classified as portals by HTTP fingerprint, not scraped.

## Sources

- `https://opendata.atlantaga.gov/` — TLS mismatch + Azure 404 (2026-08-27)
- `https://dpcd-coaplangis.opendata.arcgis.com/api/feed/dcat-us/1.1.json` — 57 datasets
- `https://gis.atlantaga.gov/dpcd/rest/services?f=json` — ArcGIS Server 11.3
- `https://services5.arcgis.com/5RxyIIJ9boPdptdo/arcgis/rest/services/Building_Permit_latest/FeatureServer/0`
- `https://www.arcgis.com/sharing/rest/content/items/655f985f43cc40b4bf2ab7bc73d2169b/data`
- `https://aca-prod.accela.com/ATLANTA_GA/`
- `https://www.atl311.com/`
- `https://gismaps.fultoncountyga.gov/arcgispub2/rest/services/Tax/Tyler_YearlySales/MapServer`
- `https://sharefulton.fultoncountyga.gov/resource/7dey-txkb.json`
- Prior: `docs/research/nine-unidentified-metros-platform.md`, `docs/research/wave-2-city-candidates.md`
