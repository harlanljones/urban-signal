# South Central Phase-0 probe — Brownsville, TX (RGV / Cameron County)

**Date of probe: 2026-08-30 (UTC).** AGOL org sweep (`COBGISManager`,
`CAMERONCOUNTY_GIS3`), City of Brownsville ArcGIS Server
(`cobgis.brownsvilletx.gov`), Cameron County GIS Experience
(`experience.arcgis.com/…/9153381449d7407ab67e4d0d7285dd3b`), Cameron CAD
(`gissvr.cameroncad.org`), Socrata/CKAN discovery, and row-level reads on
every public permit/311/SLA/deeds-adjacent layer.

Linear: **US-269**. Ticket hint: `data.brownsvilletx.gov` / CamerGIS —
county GIS + city permits (Cameron County GIS), pop ~420K (Cameron County),
Fit Medium. Both prior sweeps (South-Central 2026-08-25 and Southwest &
Mountain West 2026-08-30) graded the whole **Rio Grande Valley —
Brownsville / McAllen / Cameron / Hidalgo — Tier 3 DEFER** (permits behind
Tyler/EnerGov + internal city systems, deeds as CAD annual rolls, no public
bulk stream). This probe **re-opens Brownsville at the datastore layer** and
confirms the DEFER stands: **no live family feed survives.**

**Verdict: NO REGISTER (all four families Tier 3).** There is **no civic
Socrata or CKAN domain** (both city and county `data.*.gov` hosts are
DNS-dead; `api.us.socrata.com` → Domain not found), the **Cameron /
Brownsville ArcGIS Hub is private (401)** with a non-resolvable DCAT feed,
the city's AGOL org (`COBGISManager`, 603 items /
`services2.arcgis.com/6oaLMZEZlktbQpyi`) is **GIS reference + Survey123
intake infrastructure**, and the one true permit stream — Accela — is
exposed only as a **frozen dated snapshot**: `Accela_Permits_Report_03312026`
(4,753 rows, native coords, watermark `Permit_Issue_Date` max
**2026-03-31**, **152 days stale**, 0 rows in last 30/60/90 days). The
local ArcGIS Server Accela map services are **broken (sync 500)**. County
permitting is a **Survey123 intake form** ("Do I Need a Permit"), not an
issuance stream; county 311 has **no layer** (`q=311` → 0 items); deeds are
**Cameron CAD parcel polygons** (187,816 rows, no transaction/sales
fields); municipal SLA is a **2015 snapshot** + state TABC geocode. Only the
state super-feeds (TX TDLR/TREC/TABC) offer county-filterable SLA support —
a companion, not a municipal leaf.

---

## Method, and its limits

1. **Host resolution / dispatch:** `data.brownsvilletx.gov`,
   `data.brownsville-tx.gov`, `data.cameroncountytx.gov`,
   `data.cameroncounty-tx.gov` → **all DNS-unresolvable (000)**. There is
   no municipal Socrata or CKAN data domain for city or county. Socrata
   discovery `api.us.socrata.com/api/catalog/v1?domains=cameroncountytx.gov,brownsvilletx.gov`
   and `domains=brownsville.gov` → **Domain not found**. Cayman/Cameron
   Hub DCAT `api/feed/dcat-us/1.1.json` for `co-cameron` / `cameroncountytx`
   → **404 Domain record not found**.
2. **Hub:** `brownsville.opendata.arcgis.com`, `cameroncountytx.opendata.arcgis.com`,
   `co-cameron.opendata.arcgis.com` all HTTP 200 at root but the v3 catalog
   `api/search/v1/collections/dataset/items` → **401 private org id not
   accessible** and DCAT → 404. No enumerable dataset catalog.
3. **AGOL org sweep:** `q=owner:COBGISManager` (City of Brownsville, 603
   items) and `q=owner:CAMERONCOUNTY_GIS3` (Cameron County, 207 items),
   plus per-family keyword filters (permit/accela/311/service request/
   building/code/complaint/deed/valuat/license/inspection/request). Every
   family-adjacent survivor was then row-verified.
4. **City ArcGIS Server:** `cobgis.brownsvilletx.gov/arcgis/rest/services`
   → folders `Accela, Annexations, FEMA, Hosted, Utilities`. Probe of the
   `Accela/Accela_Map_Service_V1`, `Accela/Accela_Map_Service_Test1`, and
   root `Accela_Map_Service` → **esriCarto GraphicFeatureServer 500 sync
   error** (not a bulk-query surface). `Hosted` → parcels/address/ACS/parks
   snapshots only.
5. **Row-level verification** on every family-adjacent survivor: `count` +
   watermark (`orderByFields=… DESC`) + coordinate/candidate presence for
   `Accela_Permits_Report_03312026`, `Residential_Permits`, and Cameron CAD
   `parcels`.
6. **Cameron County GIS Experience** `9153381449d7407ab67e4d0d7285dd3b` is
   an Experience Builder SPA (no service URLs in the initial HTML); the
   county's public GIS content is the `CAMERONCOUNTY_GIS3` AGOL org, which
   is reference/boundary layers only.

Limits: `brownsville`/`cameroncountytx` Hub catalogs are **private (401)**
so the Hub's dataset inventory cannot be enumerated — the AGOL public search
+ ArcGIS Server service-directory walk is the authoritative standing-in.
Accela is the live permitting system but is **interactive Account
Administration (ACA) only**; the bulk surface is the dated *Report* snapshot
the city itself publishes, which is what was row-verified. The Cameron
County GIS Experience's webmap contents could not be enumerated from its
SPA shell; the county org service directory was used instead.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `services2.arcgis.com/6oaLMZEZlktbQpyi/.../Accela_Permits_Report_03312026/FeatureServer/0` (Accela). Live system = Accela ACA (`cobgis.brownsvilletx.gov`, but its MapServices are **sync 500**; ACA portal is interactive-only) | `Permit_Issue_Date` max = **2026-03-31** (epoch ms 1774933200000); min = 2023-07-03 (1688360400000); 4,753 rows | **native** `X_COORD`/`Y_COORD` — 4,753 / 4,753 present (100%); fields `Permit__No`, `Address`, `Work_Description`, `Permit_Category`, `Permit_Type`, `Rec_Open_Date`, `Permit_Issue_Date` | 30/60/90d **0** (capped 2026-03-31 → 2026-08-30 = **152 days stale**); 2026 YTD flow stops at Mar 31 | **3** |
| **311** | No civic service-request layer. Only Survey123 *intake* (`Requests_submit`, `MosquitoReports`, `Illegal Dumping Reports`, `Parks and Grounds Request` — all form/feature-services, no SR watermark). `ServiceNow Interface Map` (mod 2026-07-29) is **reference layers only** (parcels/streets/parks/bus stops), no SR feed | n/a | n/a | n/a | **3** |
| **SLA** | No municipal license issuance feed. `Business Licenses Inspections 2015` (webmap) = **stale 2015**; `TABC_Geocoded` = state data. `q=license` City → 3 items, all 2015/state; County → **0** | n/a | n/a | n/a | **3** — use TX state super-feeds (TDLR `7358-krk7`, TREC `s7ft-44qi`, TABC `7hf9-qc9f`) filterable to **Cameron 48061** as SLA companion only |
| **DEEDS** | Cameron CAD `gissvr.cameroncad.org/arcgiswa/rest/services/Features/parcels/FeatureServer/0` (187,816 rows) + `PARCELS_2024` (county) + `CCAD_Parcels_*` snapshots | `last_edite`/`created_da` are **parcel maintenance dates, not sale dates**; no `IndexType='D'`-style transaction layer | parcel polygons (native geometry) | n/a — annual/static parcel rolls, not transactional recorded-sales | **3** |

**Keep or reject: REJECT for municipal leaf — all four families Tier 3.**

---

## Portal inventory

| Surface | What it is | Feed? |
|---|---|---|
| `data.brownsvilletx.gov` / `data.cameroncountytx.gov` (+ `-tx` variants) | Hypothesized civic data domains | **DNS-unresolvable (000)** — no Socrata/CKAN domain |
| `api.us.socrata.com/api/catalog/v1?domains=cameroncountytx.gov,brownsvilletx.gov` / `brownsville.gov` | Socrata discovery | **Domain not found** — not Socrata |
| `brownsville.opendata.arcgis.com` / `cameroncountytx.opendata.arcgis.com` / `co-cameron.opendata.arcgis.com` | ArcGIS Hub (city + county) | Root 200 but v3 catalog **401 private**, DCAT **404** — no enumerable catalog |
| `services2.arcgis.com/6oaLMZEZlktbQpyi/arcgis/rest/services` | City of Brownsville AGOL org (`COBGISManager`, 603 items) | GIS reference + Survey123 intake; one dated permit report + a 2016 geo-log, both Tier 3 |
| `services5.arcgis.com/p65BQlkv8na0Y5l9/arcgis/rest/services` | Cameron County AGOL org (`CAMERONCOUNTY_GIS3`, 207 items) | Reference/boundary layers (parcels, roads, drainage, JP/constables, schools) — no permits/311/license/sales stream |
| `cobgis.brownsvilletx.gov/arcgis/rest/services` | City of Brownsville ArcGIS Server | **Hosted parcels/address/ACS/parks snapshots**; `Accela` MapServices are **sync 500** (non-queryable); no permit issuance bulk surface |
| `Accela_Permits_Report_03312026` (FeatureServer 0) | City's own Accela permit report extract | **Dated snapshot** — 4,753 rows, native coords, watermark 2026-03-31, 152d stale. Used by "Accela Permits Map" webmap + "Development Activity Report" dashboard |
| `Residential_Permits` (FeatureServer 0) | "New Residential Permits w/ time enabled" | **2016 geo-log** — `CreatedDat` max 2016-05-31, 2,451 rows, ~10y stale, wrong grain |
| `experience.arcgis.com/experience/9153381449d7407ab67e4d0d7285dd3b` | Cameron County GIS Experience | SPA shell — no service URLs surfaced; county content is the `CAMERONCOUNTY_GIS3` org |
| `gissvr.cameroncad.org/arcgiswa/rest/services/Features/parcels/FeatureServer/0` | Cameron County Appraisal District parcels | **187,816 parcel polygons**, fields only `OBJECTID/GEO_ID/PROP_ID` + maint dates — no sale/transfer fields |
| `www.brownsvilletx.gov` | City site | 200; only `bonfirehub` procurement link surfaced — no data portal |
| `www.cameroncountytx.gov/cameron-county-gis/` | County GIS page | 200; links to the Experience + staff request form + PDF maps — no bulk feed |

---

## Per-family findings

### Permits — Tier 3

The City of Brownsville permitting system is **Accela**. The only public
bulk surface the city publishes is a **dated ad-hoc report snapshot**:

- **`Accela_Permits_Report_03312026`** (`services2.arcgis.com/6oaLMZEZlktbQpyi/.../Accela_Permits_Report_03312026/FeatureServer/0`, serviceDesc `AccelaAdhocreport`), 4,753 rows. Fields: `Permit_Type, Permit__No, Address, Work_Description, X_COORD, Y_COORD, Rec_Open_Date, Permit_Issue_Date, Permit_Category`. Every row carries native `X_COORD`/`Y_COORD` (4,753/4,753 = **100% native geocode**). Watermark `Permit_Issue_Date` (ms epoch) max **1774933200000 = 2026-03-31**, min **1688360400000 = 2023-07-03** (a ~2.7-year window). Item created `1775163111000` (~2026-01-01), modified `1777608698000` (~2026-05-01) — i.e. the report is **frozen; its data does not advance** (newest row is still Mar 31 while the item was last touched May). Newest `Rec_Open_Date` (2026-06-01-ish) trails the issue date, consistent with a frozen extract. Newest examples read live:
  `2025-03604` 7234 OLD HIGHWAY 77 (Commercial New Construction), `2026-00339` 6672 PADRE ISLAND HWY (Commercial Alteration), `2026-00682` 2050 JOHNSON ST (Residential Duplex) — all *issue* 2026-03-31 (the snapshot's ceiling). This same layer backs the public "Accela Permits Map" webmap and the "Development Activity Report" dashboard. **0 rows in the last 30/60/90 days** (max date is Mar 31). → **Tier 3** (152-day stale frozen snapshot, not a regenerating live layer; cf. Laredo's *actively-maintained monthly* CKAN that was accepted as marginal Tier 2 despite 58-day lag).
- **`Residential_Permits`** ("New Residential Permits w/ time enabled", `services2.arcgis.com/6oaLMZEZlktbQpyi/.../Residential_Permits/FeatureServer/0`), 2,451 rows, `CreatedDat` max **1464652800000 = 2016-05-31** (~10 years stale). Fields `PermitNumb/FullAddres/Descriptio/PermitType/PrintedDat/CreatedDat/Match_addr` — a geocoded resident-permit log, wrong grain and long dead. → **Tier 3**.
- **Living Accela services are broken**: `cobgis.brownsvilletx.gov/arcgis/rest/services/Accela/Accela_Map_Service_V1`, `Accela_Map_Service_Test1`, and root `Accela_Map_Service` all return `{"error":{"code":500,"message":"Layer(s) or table(s) are not configured for Sync…"}}`. The `Accela/ADDRESS_CreateLocator`/`Address_Points_CreateLocator_Test1` are locators, not permit data. The ACA citizen portal (`cobgis`-adjacent) is interactive, matching the McAllen/Tyler/EnerGov internal-systems DEFER — no public bulk API.
- **County side**: Cameron County's permitting surface is an **intake/jurisdiction UI**, not issuance data: `Do I Need a Permit` webmap, `DO I NEED A PERMIT_form` (`survey123_cc719dfef0c34cc4892afa1a680d7039_form/FeatureServer`), a `PERMIT SURVEY` dashboard, and a `LOCATE PERMIT JURISDICTION` Hub page. No permit-issuance FeatureServer exists in the `CAMERONCOUNTY_GIS3` org (`q=permit` → boundaries + form only). Unincorporated permitting runs through the Cameron County DOT / Accela portal (interactive), matching the prior sweep.

### 311 — Tier 3 (none)

- **City**: no civic service-request layer. `q=311` → 1 item (`Buffer of 15-Scorpion Circulator`, unrelated). The 311-like surfaces are **Survey123 intake forms**: `Requests_submit` (mod 2025-07-24), `MosquitoObservations` / `MosquitoReports` (mosquito complaint survey), `Illegal Dumping Reports`, `Parks and Grounds Request` (+ `_results`/`_fieldworker` variants). These are per-request intake feature-services without a unified SR watermark/taxonomy. The `ServiceNow Interface Map` (webmap, **mod 1785428550000 = 2026-07-29**, the freshest item in the org) is a reference base map — parcels (`CCAD Parcels Feed`), streets, parks, bus stops, resacas, city buildings, address points — **it contains no service-request layer**.
- **County**: `q=311` → **0 items**; `q=service request` → 5 hits, all boundary/reference layers; `q=complaint` → 0. No county 311 feed.

### SLA / business licenses — Tier 3 (none municipal)

- City: `q=license` → 3 items, all either **stale** (`Business Licenses Inspections 2015` webmap/app, 2015 snapshot) or **state** (`TABC_Geocoded` FeatureServer — TABC state data, already available via the state super-feed). No municipal license-issuance stream.
- County: `q=license` → **0 items**.
- State companion (verified in prior RGV probe): **TDLR** `7358-krk7` (`business_county`), **TREC** `s7ft-44qi` (`county`), **TABC** `7hf9-qc9f` — all Socrata, `SocrataClient`-owned, filterable to **Cameron 48061**. Companion only, not a municipal leaf.

### Deeds / sales — Tier 3 (none transactional)

- Cameron County Appraisal District `gissvr.cameroncad.org/arcgiswa/rest/services/Features/parcels/FeatureServer/0` — **187,816 parcel polygons**, fields only `OBJECTID_1/OBJECTID/GEO_ID/PROP_ID/created_us/created_da/last_edite/last_edi_1` (parcel-maintenance timestamps, not sale/transfer dates). No recorded-sales/`IndexType='D'` layer. Annual/static.
- The city AGOL org carries **dated parcel snapshots** (`CCAD_Parcels_09082025`, `CameronCAD_Parcels_05312026_View`, `Cameron_County_Parcels`, `Cameron_CAD_Parcels_Jan_2025_View`) — all parcel polygons, not transactions. County `PARCELS_2024` (county org) is the same grain. Matches the Cameron/Hidalgo CAD-roll **Tier 3 DEFER** stance in both prior sweeps, and the McAllen reject.

---

## Hosts probed and rejected

| Host | Result |
|---|---|
| `data.brownsvilletx.gov` / `data.brownsville-tx.gov` | **DNS-unresolvable (000)** — no data domain |
| `data.cameroncountytx.gov` / `data.cameroncounty-tx.gov` | **DNS-unresolvable (000)** — no data domain |
| `api.us.socrata.com/api/catalog/v1?domains=cameroncountytx.gov,brownsvilletx.gov` / `brownsville.gov` | **Domain not found** — not Socrata |
| `brownsville.opendata.arcgis.com` | Root 200; v3 catalog **401 private**, DCAT 404 |
| `cameroncountytx.opendata.arcgis.com` / `co-cameron.opendata.arcgis.com` | Root 200; v3 catalog **401 private**, DCAT **404 Domain record not found** |
| `services2.arcgis.com/6oaLMZEZlktbQpyi/.../Accela_Permits_Report_03312026/FeatureServer/0` | **4,753 rows, native coords, watermark 2026-03-31, 152d stale** — dated frozen snapshot (Tier 3) |
| `services2.arcgis.com/6oaLMZEZlktbQpyi/.../Residential_Permits/FeatureServer/0` | **2,451 rows, CreatedDat 2016-05-31** — geo-log, ~10y stale (Tier 3) |
| `cobgis.brownsvilletx.gov/arcgis/rest/services/Accela/...` | Accela MapService V1 / Test1 / root → **sync 500** (non-queryable) |
| `cobgis.brownsvilletx.gov/arcgis/rest/services/Hosted` | Parcels/address/ACS/parks snapshots — reference, not family streams |
| `gissvr.cameroncad.org/arcgiswa/rest/services/Features/parcels/FeatureServer/0` | **187,816 parcel polygons**, no sale/transfer fields — annual/static |
| `services5.arcgis.com/p65BQlkv8na0Y5l9/...` (Cameron County org) | Reference/boundary layers only; no permits/311/license/sales stream |
| `experience.arcgis.com/experience/9153381449d7407ab67e4d0d7285dd3b` | Cameron County GIS Experience — SPA shell, no service URLs |
| `www.brownsvilletx.gov` | 200; no data portal (bonfirehub procurement only) |
| `www.cameroncountytx.gov/cameron-county-gis/` | 200; links to Experience + PDF maps + staff form |

---

## Recommendation

**REJECT Brownsville, TX (`brownsville`, Cameron County 48061) for municipal
leaf registration — Tier 3 across all four families.** No public bulk REST
endpoint satisfies ADR 0004's row-level watermark + geocode requirements.
There is no city/county Socrata or CKAN domain, both ArGIS Hubs are private
with no DCAT catalog, the two AGOL orgs are GIS reference + Survey123 intake
infrastructure, the one true permit stream (Accela) is published only as a
**frozen dated snapshot** (newest **2026-03-31**, 152 days stale, 0 rows in
last 30/60/90d), the local ArcGIS Server Accela services are **broken
(sync 500)**, county permitting is a **Survey123 intake form**, civic 311 has
**no layer in either org**, deeds are **Cameron CAD parcel polygons** with no
transaction fields, and municipal SLA is a **2015 snapshot** plus state
TABC geocodes.

The higher-leverage move — matching the RGV/Cameron **Tier 3 DEFER**, the
McAllen reject, and the Corpus Christi municipal-Tier-3 stance — is to treat
the metro as a **state-feed-only county** via the existing `SocrataClient`
on `data.texas.gov` (`7358-krk7` TDLR, `s7ft-44qi` TREC, `7hf9-qc9f` TABC)
filtered to **Cameron 48061**, with no new city leaf. Re-probe trigger: the
Accela ACA portal exposing a live bulk/data-extract endpoint, a public Hub
dataset catalog (401 → 200) with permit/311 layers, the city AGOL org
republishing the Accela permit report as a **regenerating** (undated)
service, or a current-year permit/311 service-request layer with a live
watermark.

No leaf files created (Tier 3 only): no `spatial/cities/brownsville.py`, no
`field_maps_brownsville.py`, no `test_producers_brownsville.py`. No spine
edits, no git commit, no Linear state change. Stamp: 2026-08-30.
