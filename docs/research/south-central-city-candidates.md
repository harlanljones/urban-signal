# South-Central Metro Research — El Paso, Tulsa, Plano, Shreveport, Wichita (+ OKC re-probe)

**Date of survey: 2026-08-25.** Every host, dataset, watermark, and row below was
probed live that day with row-level verification (newest-row reads by watermark
descending). Metadata `modified`/`created` timestamps were treated as unreliable
and never used as evidence, except where explicitly noted as an upload event.
"Live feed" means a freshest-row read confirmed current data.

## Method

For each metro: discover the portal (Socrata catalog membership via
`api.us.socrata.com/api/catalog/v1`, ArcGIS item search via
`arcgis.com/sharing/rest/search`, direct hostname probes); detect platform;
enumerate service directories (`…/rest/services?f=json`) for the four feed
families (PERMITS, 311, SLA business licenses, DEEDS/sales); then row-level
verify every survivor — layer index, watermark column, freshest-row date,
geometry type / spatial reference, geocoding fields, total rows, and a recent-
30-day count where the watermark supports it. Only freshest-row reads counted
as evidence.

Two survey-wide gotchas worth recording:

- **ArcGIS layers can start at any index.** Querying `/FeatureServer/0/query`
  on a service whose real layer id is non-zero returns HTTP 200 with
  `{"error":{"code":400,"message":"Invalid URL"}}`. This single quirk produced
  both the original OKC "unreachable endpoint" finding and would have hidden
  two more feeds this pass (see Tulsa County and Plano entries).
- **Socrata membership ≠ city portal.** Plano's datasets live under
  `dashboard.plano.gov`, not `data.plano.gov`; the plain hostnames DNS-fail.

## Summary

| Metro | Correct host(s) | Platform | Register | Not register |
|---|---|---|---|---|
| El Paso, TX | `gis.elpasotexas.gov` (+ hosted org `hyTVSIhR7dHyDsJF`) | ArcGIS Server | **311** | permits (frozen 2022 corpus), licenses, deeds |
| Tulsa, OK | `maps.cityoftulsa.org/hosting` + `services2.arcgis.com/XkZ90iCdbTJ9oNXl` | ArcGIS Server + AGOL org | **311** (rolling-window caveat) | permits (county snapshot, ~11-mo lag), licenses, deeds |
| Plano, TX | `dashboard.plano.gov` + hosted org `1DyhsVa6rviDKn5t` | Socrata + AGOL | **none** | all four at row level (aggregates only) |
| Shreveport, LA | `services3.arcgis.com/cEsSI6IR59h5UGE4` | ArcGIS Online org | **none** | all four (dated manual snapshots) |
| Wichita, KS | `gismaps.wichita.gov/ageweb` (+ Sedgwick Co. `McLat6HlPl45bNBv`) | ArcGIS Server | **permits** | 311, licenses, deeds |
| Oklahoma City, OK (re-probe) | `data.okc.gov` (Incapsula-bot-shielded) | custom portal | **none** — prior PROVISIONAL retracted | permits (the "Building Permit" item was never OKC's), 311, licenses, deeds |

## Per-metro findings

### El Paso, TX — register 311

Portal: city ArcGIS Server at `gis.elpasotexas.gov` (root + folders incl.
`accela`, `ParcelArchive`, `EconomicDev`, `CitySourced`); hosted AGOL org
`services1.arcgis.com/hyTVSIhR7dHyDsJF` (owner `VelozRX@elpasotexas.gov_CoEPGIS`,
224 feature-service items). The guessed Hub hosts
(`cityofelpaso-opendata.opendata.arcgis.com` et al.) return DCAT catalogs with
0 datasets — SPA shells, not portals. No Socrata domain.

- **311 — live.** `Requests` FeatureServer,
  `https://gis.elpasotexas.gov/accela/rest/services/311/Requests/FeatureServer/0`.
  Watermark `created_at` (esriFieldTypeDate); newest row **2026-08-25 04:59 UTC**
  (day of probe); 4,915 rows in 30 days; 66,384 total. Fields: `id` (azureID),
  `internal_system` ("Accela"), `request_category`, `request_type`, `status`,
  `address` (full single-line), `description`, `source`, `request_id`,
  `district`. Geometry: `esriGeometryPoint` in TX state-plane feet
  (wkid 102739 / latest 2277); no native lat/lng columns — coordinates are the
  projected points plus an address string. Note this directory is invisible in
  the server's own folder listing (only folders `311`, `Cityworks`, `Utilities`
  show, and the listing omits the `311` service itself) — probe the URL directly.
- **Permits — no live feed.** The AGOL "Permit" Map Service item 404s at its
  published URL. The Accela-backed `NewResidential` FeatureServer
  (`services1.arcgis.com/hyTVSIhR7dHyDsJF/.../NewResidential/FeatureServer/0`,
  5,886 rows, `B1_ALT_ID` Accela IDs like `TPRN22-00050`, point geometry) is a
  frozen housing-dashboard corpus: max `Issued_Dat` **2022-01-31**, max
  `B1_FILE_DD` 2019-09-26, 0 rows issued in the last 30 days. Useful only as
  backfill/validation data.
- **Licenses — no feed.** Nothing license-like in root, `accela`, or
  `EconomicDev` directories (TIRZ/tax-abatement layers are boundary/admin).
- **Deeds — no feed.** `Deeds/FeatureServer` (layer "Parcels", polygon) carries
  assessment values (`X021_ASSES`/`X022_APPRA` etc.), owner and situs fields,
  but no sale price/date columns. `EPParcels` likewise has no sale fields.
  `ParcelArchive` holds yearly parcel MapServers (2021/2022/archive), i.e.
  snapshots, not transactions. El Paso County deed records are not exposed.

### Tulsa, OK — register 311 (with window caveat)

Portal: city ArcGIS Server `maps.cityoftulsa.org/hosting/rest/services`
(folders: OpenData, CustomerCare, Planning, Engineering, …) + hosted AGOL org
`services2.arcgis.com/XkZ90iCdbTJ9oNXl` (owner `CityofTulsaGIS`, 76 public
feature services). Confirmed off Socrata: zero catalog hits and no Socrata
domain. The old sweep's "left Socrata" note holds — they are an ArcGIS shop.

- **311 — live.** `VerintCasesPublic` FeatureServer,
  `https://maps.cityoftulsa.org/hosting/rest/services/CustomerCare/VerintCasesPublic/FeatureServer/0`.
  Watermark `case_opened` (Date); newest case **2026-08-25 22:34 UTC** (day of
  probe, minutes before read). Case types look exactly like citizen requests
  ("Improper Storage", "Traffic Signal Malfunction", "Abandoned Vehicles GID").
  Geometry: `esriGeometryPoint` in OK-North state plane (wkid 2911). **Caveat:**
  the public view holds only **418 rows total** — a rolling recent-window view,
  not an archive (a `case_opened > now-30d` filter matches all 418). Expect
  ~400+ rows/month volume and no history beyond the window. Fields include
  `case_id`, `case_subject/reason/type/status/priority`, `case_opened/closed`,
  but no explicit address column — rely on the point geometry.
- **Permits — no city feed; county assessor snapshot only.** The
  `tca_cperkins` "Building Permit" item resolves to
  `https://services3.arcgis.com/JfsWgLAOPxX7NGuG/ArcGIS/rest/services/Building_Permit/FeatureServer`
  — **Tulsa County Assessor**, not OKC (see re-probe section below). Its single
  layer is **index 195** (querying `/0` yields the misleading "Invalid URL"
  error). Row-verified: 6,154 county-wide permit points joined to CAMA parcels;
  fields `ParcelNo`, `AccountNo`, `PermitType`, `PermitNo`, `Status`,
  `PermitReason`, `PermitUse`, `Source`; `PermitDate` is a **string**
  (`'YYYY-MM-DD HH:MM:SS'` padded) but sorts correctly; newest **2025-09-18**
  (~11 months stale at probe; item was uploaded ~2026-07-29, so annual-snapshot
  cadence); geometry point in OK-North state plane (wkid 102724/2267) on parcel
  centroids — address-less. Backfill/validation corpus only. The city's own org
  publishes `DevPlans_OpenData`, zoning, neighborhoods — no building-permit
  feed surfaced in 76 items or the hosting-server folders.
- **Licenses / deeds — no feed.** Nothing license- or sale-like in either the
  hosted org or the hosting server's public folders.

### Plano, TX — register none

Portal: **Socrata at `dashboard.plano.gov`** (30 datasets; `data.plano.gov`
DNS-fails — the old sweep missed the real hostname). Hosted AGOL org
`services2.arcgis.com/1DyhsVa6rviDKn5t` (184 services) carries their planning
dashboard layers.

- **311 — aggregates only.** `FIXIT_Plugin_Data` (`kce6-krz4`) is monthly
  counts (`date_month_year`, `requested`, `completed`; 52 rows; newest month
  2025-09) — not row-level service requests. REJECT for our purposes.
- **Permits — summarized dashboards only.** No permit dataset exists in the
  Socrata catalog (30 datasets reviewed by name). On AGOL,
  `Commercial_Building_Permits_0126_WFL1` contains a single layer at **index 7**
  ("Permits_Summarized") — neighborhood polygons with integer count columns
  (`NEW_CONSTR`, `FULL_DEMOL`, `Grand_Tota` …), not permit rows;
  `res_bldg_permits_2022_01` and `2010_Building_Permits_*` are dated snapshots.
  No row-level feed.
- **Licenses / deeds — no feed.** Catalog has none; `Present_Home_Sales_WFL1`
  is MLS-sale *polygons* (aggregated areas), not transaction rows; Collin and
  Denton counties hold the deed records.

### Shreveport, LA — register none

Portal: ArcGIS Online org `services3.arcgis.com/cEsSI6IR59h5UGE4` (owners
`*@shreveportla.gov`; ~600 services, dominated by one-off distance buffers per
address). Ex-Socrata `data.shreveportla.gov` DNS-dead, confirming the move.
The org's pattern is **manual dated snapshots** (layer names embed publish
dates: `MPC_Zoning06022026_view`, `STR_Licenses_03272026`,
`PZC_Case_Index04222026`), which caps freshness regardless of individual
watermarks.

- **Permits — no live feed.** `Development_2019`–`Development_2024` are annual
  MPC-case point layers (geocoded: `Loc_name` locator output; WGS84). Probed
  `Development_2024`: 117 rows; newest `USER_Case_Number` `24-26-P` ("Temporary
  Certificate of Occupancy", APPROVED) — hearing-board cases (variances, code
  amendments, TCOs), not building-permit issuance, and **no 2025/2026 layer
  existed at probe time**, so even this proxy is >19 months stale.
  `CASE`/`Cases_View` MPC layers: 7 rows, hearings frozen 2024-07-17.
- **311 — no feed.** `Resolved_Tickets`/`TicketsJan2025` are agent-level
  aggregate tables (`Agent_Name`, `Tickets_Resolved`), not request rows; no
  citizen-request layer anywhere in the org.
- **Licenses — snapshots only.** `STR_Licenses_03272026` (point; fields
  `License__`, `Address`, `Status`, `Link`) and static liquor-store lists
  (Dec 2024). Dated republishes without per-row watermarks. REJECT.
- **Deeds — no feed.** `City_of_Shreveport_Property_Merged` carries owner,
  tax, improvement/land values and an `ADJUDICATE` flag — an assessment roll,
  not transactions. Caddo Parish holds the actual deed records.

### Wichita, KS — register permits

Portal: city ArcGIS Server `gismaps.wichita.gov/ageweb/rest/services` (plus
`/ageweb3` for utilities) and hosted org `services5.arcgis.com/lOHEurd1BgncOSk1`.
The `OpenData` folder holds only Census/Crime/Fire/TrafficAccidents — but the
building department's data hides in `MISC`. No Socrata domain.

- **Permits — live.** `MABCD Permits SDE`,
  `https://gismaps.wichita.gov/ageweb/rest/services/MISC/MABCD/FeatureServer/1`
  (**layer index 1** — `/0` is Code Enforcement Violations). 271,991 rows.
  Watermark `ApplicationDate`; newest **2026-08-25** (day of probe);
  **3,298 applications in the last 30 days**. Schema is unusually rich:
  `PermitNumber` (e.g. `RFS2026-11032`), `ApplicationDate`, `LastModifiedDate`,
  `DeclaredValuation`, fee columns (`Paid_Amt`…`Refunded_Amt`),
  `OccupancyType`, `PermitStatus`, `WorkType` ("ROOFING" …), `PermitDesc`,
  `InwardAddress`/`City`/`State`/`PostalCode`, `ParcelID`, `SubdivNM`,
  census geocode fields (tract/block-group/block), opportunity-zone and urban-
  renewal flags. Geometry: `esriGeometryPoint`, KS state plane (wkid 3420).
  Caveat: `Jurisdiction` came back null on sampled fresh rows while
  `City='WICHITA'` — filter on `City`, and expect a metro-wide mix until
  jurisdiction semantics are confirmed during registration.
- **311 — no feed.** Nothing request-like in `OpenData`, `MISC`, or the hosted
  org (citations/parking/facilities only).
- **Licenses — no feed.**
- **Deeds — no usable feed.** Sedgwick County's `Sedgwick_County_Land_Records`
  FeatureServer (org `McLat6HlPl45bNBv`; layers Subdivisions/Lots/**Parcels**
  at ids 1/3/4) exposes `RDParDocID` (Register-of-Deeds document IDs) and an
  often-null `EditDT`, but **no sale price or sale date columns** — document
  references without transactions. County tax/zoning views round out
  assessment data only.

### Oklahoma City, OK — re-probe: prior PROVISIONAL retracted, register none

The earlier finding ("Building Permit FeatureServer exists but is unreachable")
was a **misattribution**. The item found via browser search — owner
`tca_cperkins`, service org `JfsWgLAOPxX7NGuG` — belongs to the **Tulsa County
Assessor**: the org directory lists `Building_Permit`, `Historical_Parcels`,
`Records`, `TCA_SectionStreet_SHP`; the item description reads "current
building permits in **Tulsa County**"; extent is Tulsa County. The HTTP 400
"Invalid URL" that looked like auth-gating was simply **layer index 0 against a
service whose only layer is index 195** — verified by querying
`…/Building_Permit/FeatureServer/195/query` successfully (details in the Tulsa
section above).

OKC's actual publishing surfaces, re-probed the same day:

- `data.okc.gov` — custom portal behind **Incapsula bot-shield**: every path
  (`/portal/page/start/`, `/portal/api/datasets`, `/api/catalog`) returns the
  challenge iframe to curl, with and without browser UA strings. Not scrapeable
  CLI-side; would need a real browser session or an allowlisted integration.
- `oklahomacity-ok.opendata.arcgis.com` — Hub shell, DCAT feed = 0 datasets.
- `AGOL_Content_OKC` org — parks/GIS-ops utility services
  (`utility.arcgis.com/usrsvcs/...`, token-gated) plus one public hosted org
  (`services5.arcgis.com/2mOVdIcRtNH2JsSF`, ~250 services): parks, surveys,
  marathons, `Infrastructure_Projects_OD`, `Event_Reports` — **no permit, 311,
  license, or deed feeds**. AGOL-wide searches for OKC-owned permit/311 feature
  services returned nothing relevant.

**Verdict: REJECT for CLI-side ingestion.** If OKC matters later, the path is
browser-assisted discovery of `data.okc.gov` dataset pages (their downloads may
still be plain CSVs behind the shield) rather than any REST surface.

## Recommendation

Two metros graduate to the candidate list:

1. **Wichita, KS — register PERMITS.** The strongest find of the wave: 272k-row
   MABCD permit layer, freshest application same-day as probe, ~3,300/month,
   with valuation, fees, work type, parcel ID, and census geocoding built in.
   Point geometry in KS state plane. Verify the `Jurisdiction` null pattern at
   registration time and filter on `City`.
2. **El Paso, TX — register 311.** Live Accela-backed feed, same-day freshness,
   ~4,900 requests/month (10× Louisville-class volume), clean category/type/
   status fields and full addresses; geocoded points arrive in TX state-plane
   feet rather than lat/lng. Single-feed registration cost comparable to
   Indianapolis/Houston precedent.
3. **Tulsa, OK — register 311 conditionally.** Freshest feed of the entire wave
   (minutes old at read) and unmistakably 311, but the public Verint view is a
   rolling ~418-row window: acceptable for change-signal detection, useless for
   backfill. Register only if producers accept the no-history constraint and
   monitor whether the city later publishes a full archive.

Skip-grade for live feeds: **Plano** (Socrata portal is real but holds only
monthly aggregates and summarized dashboards), **Shreveport** (an ArcGIS org of
manually republished dated snapshots — even its best proxy layer predates 2025),
and **OKC** (portal bot-shielded; its "provisional permit lead" is formally
retracted as a Tulsa County Assessor misattribution whose "Invalid URL" was a
layer-index artifact — query `/195`). Tulsa County's permit snapshot (fresh to
2025-09) and El Paso's frozen NewResidential corpus are backfill/validation
assets, not live signals.

Every claim above is row-verified or explicitly marked unverified; shallow
probes are labeled as such (Shreveport's ~600-layer org was sampled by
candidate name, not exhaustively enumerated; OKC's Incapsula wall blocks
exhaustive confirmation inside the portal itself).
