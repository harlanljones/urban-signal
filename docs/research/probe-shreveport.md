# Wave 3 Phase-0 probe — Shreveport, LA (US-267)

**Date of probe: 2026-08-30 (live).** AGOL org enumeration for both City
and Parish, Hub/Opendata host fingerprinting, app-graph traversal into the
operational 311 portal, and row-level metadata reads on every public
survivor.

Linear: **US-267**. Ticket hint: "Parish/city permits — Caddo GIS",
pop ~385K, Fit Medium. That hint is the *only* thing pointing at a
transactional feed; **it does not survive live verification.**

**Verdict: NO REGISTER (all four families Tier 3).** City of Shreveport
publishes **no anonymous transaction feed** in any family. Its AGOL org is
a pure reference body (1107 items: zoning, parcels, buildings, boundaries,
flood, parks, liquor points). Caddo Parish's GIS surface
(`caddopw.maps.arcgis.com`, org `ekpaOXhC7fFWoTJ9`) is reference-only
(districts, posted bridges, compactor sites, road events, precincts). The
"Port City 311" app is **QScend**, login-gated with no public export. The
Caddo Parish Assessor parcels are a **paid DataScout SaaS** (transaction
histories paywalled; no open bulk/API/watermark). `gis.shreveportla.gov`,
`gis.caddo.org`, `gis.caddo.gov`, `maps.caddo.org` all **DNS fail**.

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | No permit layer. City org case-indexes only: `MPC_CASE_INDEX` (layer 2), `ZBA_CASE_INDEX` (layer 4), `PZC_CASE_INDEX` (layer 1) — case number/case type/no DATE, PZC has `USER_Year` (year-only) | n/a (no date columns) | n/a | unverifiable | **3** |
| **311** | Port City 311 = QScend `shreveportla.qscend.com/311/request/add` (login-gated; `account/signin`+`signup` on page; no public bulk list/API; `/311/feed/notices` is notices only) | n/a | n/a | n/a | **3** |
| **SLA** | `Liquor Stores` / `LiquorStores_Oct4_2022` Feature Service (static Oct-2022 point snapshot); ABO Liquor-Beer License page informational | n/a (frozen 2022 roll) | points | no window | **3** |
| **DEEDS** | Caddo Parish Assessor → DataScout `actdatascout.com/RealProperty/Louisiana/Caddo` (free search per-parcel GUI; Pro $35/mo unlocks transaction histories + mapping; **no open bulk/API/watermark**) | n/a | n/a | paywalled | **3** |

---

## Platform

Resolved: **ArcGIS Online (2 reference-only orgs) + a login-gated SaaS 311
portal + a paid SaaS property-search vendor.** Not Socrata, not CKAN, not a
self-hosted ArcGIS Server.

| Surface probed | Result |
|---|---|
| `caddo.opendata.arcgis.com`, `shreveportla.opendata.arcgis.com` | Legacy Opendata-shell HTML; `api/search`, `api/v1/search`, `api/feed/search` → 404; no Hub catalog served. The real catalogs are the AGOL orgs below. |
| City AGOL org `services3.arcgis.com/cEsSI6IR59h5UGE4` (`cosgisadmin` / `gerald.sneary@shreveportla.gov` / `Bamesh.Roy@shreveportla.gov`) | **1107 items** — reference (zoning/UDC, SUBDIVISIONS, BUILDINGS, parcels, city limits, flood, council districts, parks, SHELTER_HOUSING, Traffic_Signals, Liquor Stores, Water Pressure Zones, LoRaWAN). No permit/311/transaction layer. |
| Caddo Public Works org `services1.arcgis.com/ekpaOXhC7fFWoTJ9` / `caddopw.maps.arcgis.com` (`swalker@caddo.org`) | **16 public items** — Districts, Posted Bridges, Compactor_Sites, Road Event, Caddo_Precincts, Voting. Reference only. |
| `gis.shreveportla.gov`, `gis.caddo.org`, `gis.caddo.gov`, `maps.caddo.org` | All **DNS fail** (moved to AGOL; no self-hosted Server). |
| `data.shreveportla.gov`, `opendata.louisiana.gov`, `data.louisiana.gov`, `shreveport.socrata.com` | All `000` / no Socrata host. |

## Row-level verification

- **MPC_CASE_INDEX** (FeatureServer layer 2): fields `OBJECTID, Loc_name,
  CASE_NUMBER, CASE_TYPE, PREV_CASE_NUMBER*, GLOBALID, Shape__Area/Length`.
  **No DATE field, no address, no permit value.** maxRecordCount 1000 →
  reference index, Tier 3.
- **ZBA_CASE_INDEX** (layer 4): `FID, CASE_NUMBE, CASE_TYPE, PREV_CASE_*,
  GLOBALID, Shape`. **No DATE field.** Tier 3.
- **PZC_CASE_INDEX** (layer 1): `OBJECTID, Loc_name, USER_Case_Number,
  USER_Address, USER_Year, USER_Board, Prev_Case_Number`. `USER_Year` is a
  **year integer**, not a timestamp — no month/day, no watermark, no value.
  Tier 3.
- **BUILDINGS, INSPECTOR_ZONES, PLANNING_DISTRICTS_MasterPlan,
  Future_Land_Use, Subdivisions, DDA_Boundary, Zoning** — reference layers.
- **Liquor Stores** (`LiquorStores_Oct4_2022`) — static point snapshot,
  title names the 2022-10-04 build date; no date column → stale list, Tier 3.
- **DataScout** `actdatascout.com/RealProperty/Louisiana/Caddo` — free public
  search is per-parcel card lookup (owner/values/book-page); the JSON/history
  feed and mapping are **Pro subscription only** ($35/mo + $10 map). No
  anonymous REST/watermark. Tier 3.
- Third-party "Caddo" parcel/sales AGOL services (Virginia Tech
  `_virginiatech` uploads, `Michaeljuser58` "Caddo Parcel Data 2023",
  `BriceDarbyCEC` "South Caddo Parcels", `klandreneau@latterblum.com` brokerage
  sales comps) — **not the municipality**, no sale-date/price watermark,
  stale/one-off. Not registrable.

## Method, and its limits

1. Host/DNS fingerprint of the hinted `gis.*` hosts, Parish site
   (`www.caddo.gov` = WordPress informational), and assessor/clerk hosts.
2. AGOL org enumeration for the City (100-item read + full-title org query,
   1107 total) and Caddo Public Works (16 items), plus targeted keyword
   searches for permit / 311 / inspection / sale / deed / license.
3. Row-level metadata reads on the case-index, liquor, and parcel survivors.
4. QScend app surface: `shreveportla.qscend.com/311/request/add` and sister
   URLs (`/311`, `/311/requests`, `/api/requests`, `/api/v1/requests`).
5. DataScout pricing/feature read (`caddoassessor.org`).

Limits: QScend may expose an internal/authenticated list endpoint not
reachable anonymously; a permit feed behind the city's builder portal or an
unpublished ArcGIS Server cannot be fully ruled out. But no candidate was
found on any public surface, and every operational system identified (QScend
311, DataScout assessor, AGOL case-index) is reference UI or paywalled.

## Decision

**Do not register Shreveport.** All four families Tier 3: no permit
transaction layer (case-indexes carry no dates), Port City 311 is a
login-gated QScend portal with no watermarked export, liquor licenses are a
frozen 2022 reference snapshot, and Caddo parcels are a paid DataScout SaaS
(transaction histories paywalled). Re-probe triggers: the city publishing
permit records or a 311 export to AGOL/Hub, or the Parish assessor/Clerk of
Court landing an anonymous bulk parcel/Sales stream. Stamp: 2026-08-30.
