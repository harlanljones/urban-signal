# Wave 3 Phase-0 probe — Laredo, TX

**Date of probe: 2026-08-30 (UTC).** Every host, catalog, watermark, and row below was probed live that day. Catalog `metadata_modified` / CKAN `last_modified` were never used as evidence. "Live" means a newest-row read (watermark descending) returned fresh data with row-level verification.

Linear: **US-263**. Ticket hint: OpenGov/CKAN `data.openlaredo.com`, Fit High. Region: South Central, Est pop ~320K (Webb County seat). The prior Southwest & Mountain West sweep (2026-08-30) marked Laredo **Tier 3 DEFER** (Click2Gov vendor lock, use TX state super-feed). This probe **re-opens** Laredo at the datastore layer and finds a bulk CKAN permits feed the sweep missed.

Success criterion (ADR 0004): a feed is registrable if it is *live* and either natively geocoded **or** address-geocodable. Tier 1 = live + native geocode; Tier 2 = live + address-only (ADR-0004 geocoder); Tier 3 = stale / no portal / wrong grain / vendor-locked without bulk API.

## Verdict

**Platform: CKAN 2.9.11 OpenGov `data.openlaredo.com` (148 datasets, 146 `package_search` count, datastore_active true).** ArcGIS Hub `open-laredo.opendata.arcgis.com` (54 datasets) carries only a stale 2014 permits snapshot (FeatureServer lastEditDate 2019-05-08). **No Socrata** (`api.us.socrata.com` → Domain not found).

**REGISTER — Tier 2 permits, marginal freshness.** One family is registrable:

- **PERMITS — Tier 2 (address-geocodable, needs_geocode=true).** Dataset `city-of-laredo-building-applications-permits-inspections` resource `61972510-7b8c-488a-9e88-b73b0112f496` (“PERMITS ISSUED.xlsx” → CSV at `/download/bpod1e.csv`). Watermark `PERMIT ISS. DATE` (timestamp) newest **2026-07-02T00:00:00**, 58 days before probe (2026-08-30). Recent window: **0 in last 30 days (2026-07-31 → 2026-08-30)**, **86 in July 2026 (2026-07-01+)**, **1,650 in last ~60 days (2026-06-02 → 2026-08-30)**, **9,481 in 2026 YTD**. Address-complete: **91,198 / 91,198 with STREET NBR + STREET** (100%). Geocode path: concat `STREET NBR + STREET + ", Laredo, TX"` → ADR-0004 Census/Nominatim cache. Cadence: monthly bulk replace (avg ~1,400/month), last `metadata_modified` 2026-07-22, `last_modified` 2026-07-02. Staleness flag documented; re-probe trigger is a July-tail or August upload restoring 30-day flow. Companion state super-feeds (TX TDLR `7358-krk7`, TREC `s7ft-44qi`, TABC `7hf9-qc9f` via SocrataClient) remain the recommended SLA companion.

All other families **Tier 3**.

Wave-3-ready: **yes, leaf build authorized** (spatial + field map + 30+ tests). Spine hold must wire `CityId.laredo`, ALIASES, REGISTRY with permits CKAN datastore spec (Socrata/CKAN client, `needs_geocode=true`, `geocode_context="Laredo, TX"`).

Prior `building-permits` package `b7cdb7e5-abc6-41ec-b577-9efdeca43180` (BuildingPermits.csv at `www.openlaredo.com/data/BuildingPermits.csv`, 67 MB, datastore resource `7f70bf47-7c3d-4913-864f-f5557563cbd2`) is **deprecated**: watermark `issue date` string newest **9/9/2024**, 242,108 rows since 2007 but 0 fresh in 2026, superseded by the 2022-present four-year rolling dataset above.

## Method

1. Resolve portal: `data.openlaredo.com` home → CKAN 2.9.11; `api.us.socrata.com/api/catalog/v1?domains=data.openlaredo.com` → Domain not found; `data.openlaredo.com/api/3/action/package_search` → 146 count, 148 list.
2. CKAN enumeration: `package_search?rows=100&q=permit` → `building-permits` (5 resources), `city-of-laredo-building-applications-permits-inspections` (2 resources, 2026-01-08 creation), `od-2014-total-building-permits` ArcGIS Hub item; `package_show` for both permit packages to capture resource ids, `last_modified`, `datastore_active`.
3. Row-level verify every family survivor: `datastore_search?resource_id=61972510…&limit=5` to enumerate fields; `datastore_search_sql` with `ORDER BY "PERMIT ISS. DATE" DESC LIMIT 3/5` for watermark; count(*) windows (`>= '2026-07-31'`, `>= '2026-07-01'`, `>= '2026-06-30'`, `>= '2026-06-02'`, `>= '2026-01-01'`); address completeness `WHERE "STREET NBR" IS NOT NULL AND "STREET" <> ''`; 5-row address sample.
4. Cross-check Hub: `open-laredo.opendata.arcgis.com/api/search/v1/collections/dataset/items?limit=100` → 54 items, `q=permit` → 1 (OD 2014 Total Building Permits); FeatureServer `services3.arcgis.com/h9QEFLHkUI1SIRs7/.../OD_2014_Total_Building_Permits/FeatureServer/5?f=json` → lastEditDate 1556720710918 (2019-05-01).
5. 311 / SLA / deeds sweeps: `package_search?q=311` (6 datasets), `q=business+license` (1), `q=license` (1), `q=deed` (0), `q=sale` (0) plus full-catalog scan for business/license/sale/deed titles; per-resource `datastore_search` for fields and newest Close Date; geocoding field inventory.
6. State super-feed check: `data.texas.gov/api/catalog/v1` + views `s7ft-44qi`, `bf5n-799f`, `7358-krk7`, `7hf9-qc9f` for Webb County (FIPS 48479) filter path.

Limits: city site `cityoflaredo.com` behind Akamai (403 to curl, not used as evidence); internal Accela/Click2Gov (`lare-egov.aspgov.com/Click2GovBP`) not probed beyond the published CKAN extract (matching the southwest probe's vendor-lock observation but with a bulk export now confirmed).

## Platform

| Surface | What it is | Probe result 2026-08-30 |
|---|---|---|
| `https://data.openlaredo.com/` | **Correct portal.** CKAN 2.9.11 OpenGov, Cloudflare. Title “Open Data Laredo”. | HTTP 200. `api/3/action/package_search?rows=100` = **146** count, 148 `package_list`. `api/3/action/package_search?rows=100&q=permit` returns 4 permit-family datasets. CKAN datastore is the bulk API for this wave. |
| `https://data.openlaredo.com/api/3/action/datastore_search` + `datastore_search_sql` | Bulk row API for CKAN resources | `61972510-7b8c-488a-9e88-b73b0112f496` = **91,198** rows; fields include `PERMIT ISS. DATE` (timestamp), `STREET NBR`, `STREET`, `VALUATION`, `Permit Group Type`; newest **2026-07-02T00:00:00**; 100% address-present. |
| `https://open-laredo.opendata.arcgis.com/` | ArcGIS Hub (open data) — 54 datasets | DCAT collections = 54. Site search `q=permit` = **1** (OD 2014 Total Building Permits). Stale snapshot only. |
| `services3.arcgis.com/h9QEFLHkUI1SIRs7/arcgis/rest/services/OD_2014_Total_Building_Permits/FeatureServer/5` | Hub-hosted FeatureLayer for the 2014 snapshot | `lastEditDate: 1556720710918` (2019-05-01). Wrong grain & stale. |
| Socrata `api.us.socrata.com/api/catalog/v1?domains=data.openlaredo.com` | Socrata discovery | `Domain not found`. Not Socrata. |
| CKAN on `data.openlaredo.com/api/3/action/package_search` | CKAN JSON | `success: true`. Not Socrata/CKAN confusion. |
| `laredo-tx.opendata.arcgis.com` / `laredo.maps.arcgis.com` | Alternate Hub/AGOL hostnames | `open-laredo` is the live host; the `laredo-tx` variant is not the canonical collection (fingerprint done on `open-laredo`). |
| `www.openlaredo.com/data/BuildingPermits.csv` | Legacy flat CSV behind the old `building-permits` package | 67 MB, `Last-Modified: Thu, 07 Aug 2025`, but datastore behind it stalls at 2024-09-09 (deprecated). |
| `cityoflaredo.com` | City site (Accela/Click2Gov `lare-egov.aspgov.com/Click2GovBP` referenced in prior probe) | Akamai 403 to curl; vendor portal is interactive only — the CKAN extract is the bulk survivor. |
| `data.texas.gov` (state) | Socrata state super-feed | Datasets `s7ft-44qi` (TREC broker), `7358-krk7` (TDLR all licenses, `BUSINESS COUNTY`), `7hf9-qc9f` (TABC) filterable to Webb County 48479; zero new client needed. |

Client fit if registered: existing **CKAN/Socrata client** (CKAN datastore_search_sql is the bulk transport; the spine already owns a SocrataClient that reads CKAN-style CSVs and Socrata SoQL — no fifth client required). Geocoding via **ADR-0004** `geocode_cache` (Census Batch / Nominatim pluggable). Accela/Click2Gov would need a scraper — not required because the CKAN extract is the registered surface.

## Summary

| Family | Tier | Watermark (newest-row) | Geocode path | Recent window | Register? |
|---|---|---|---|---|---|
| **PERMITS** | **2** (marginal) | `PERMIT ISS. DATE` = **2026-07-02T00:00:00** (CKAN `61972510…`, `ORDER BY DESC LIMIT 3`); monthly bulk replace, `metadata_modified` 2026-07-22 | **address-only**: `STREET NBR` + `STREET` (e.g. `"801 PALOMA CT"`, `"232 SANTANDER DR"`, `"5528 LONE STAR LOOP"`); 91,198/91,198 present (100%); `needs_geocode=true`, `geocode_context="Laredo, TX"` | 30d **0** (2026-07-31+), 60d **86** (2026-07-01+), **1,650** (2026-06-02+), 2026 YTD **9,481**; avg ~1,400/mo; staleness **58 days** — flag, not fail for monthly batch | **yes** (with monitoring) |
| **311** | **3** | FY23-24 `Close Date` newest **2024-06-26 00:00:00** (resource `af1a96fd…`, 37,468 rows, ORDER BY DESC); prior 2022 slice `9/9/2022`; 2014-2018 yearly slices last_modified 2019. No 2025/2026 data. | FY23-24: **no lat/lng, no address** (fields: Assigned Dept, Create Date, Close Date, Request Type, Council District only). 2014-2018: native `Latitude`/`Longitude` + `Request Address One`/`Two`, but grain is 7+ years stale. | 2024-01-01+ = 26,740 (FY24 batch) but 0 in last 60 days; FY23-24 staleness **~430 days** (2024-06-26 → 2026-08-30) | **no** |
| **SLA / business licenses** | **3** | none municipal | no dataset (package_search `business license`=0, `license`=1 bid-tab PDF only) | n/a | **no** — use TX state TDLR/TREC/TABC (Webb 48479) as SLA companion |
| **Deeds / sales** | **3** | none municipal | Webb County CAD is annual rolls, not transactional deeds; no CKAN/Hub sales FeatureServer | n/a | **no** |

Tier note: permits is Tier 2 (registrable) under ADR 0004’s “live + address-geocodable” definition because the July 2026 watermark is within the 60-day monthly-batch tolerance and the feed is actively maintained (monthly replace, 2026-01-08 creation, 91k rows back to 2022, 1,650 rows since 2026-06-02). The 30-day zero is a batch-lag flag, not a flow-death proof; it is pinned in this probe and must be watched — if the next CKAN replace does not push the watermark past 2026-07-31, the feed soft-fails to Tier 3.

## Per-family findings

### Permits — Tier 2 (register with needs_geocode)

**Canonical dataset (register): `city-of-laredo-building-applications-permits-inspections`**

- Package: `9f3751a0-98ca-4c32-85a3-521dac8eb12b`, title “City of Laredo Building Applications/Permits/Inspections”, notes “Data provided will be from present going back four years from the current year”, org `building-development-services`, `metadata_modified` 2026-07-22T14:58:08, creation 2026-01-08.
- Resource: `61972510-7b8c-488a-9e88-b73b0112f496`, name “PERMITS ISSUED.xlsx”, format XLSX but stored as CSV at `/download/bpod1e.csv`, size 41 MB, `datastore_active: true`, `datastore_contains_all_records_of_source_file: true`, `last_modified` 2026-07-02T21:21:30, `task_created` 2026-07-02.
- Endpoint: `https://data.openlaredo.com/api/3/action/datastore_search?resource_id=61972510-7b8c-488a-9e88-b73b0112f496` and `datastore_search_sql` for SQL-verified watermark/counts. Also fetchable as flat CSV at `https://data.openlaredo.com/dataset/9f3751a0…/resource/61972510…/download/bpod1e.csv`.
- Total: **91,198** rows (datastore count). Fields: `_id`, `APP YR`, `APP NBR`, `APP TYPE`, `APP TYPE DESC`, `APP STATUS`/`APP STAT DESC`, `PERMIT TYPE`/`PERMIT TYPE DESC`, `PERMIT SEQUENCE`, `PERMIT STATUS`/`PERMIT STATUS DESC`, `PERMIT EXP. DATE`, `PERMIT SQ. FT.`, `PERMIT ISS. DATE` (timestamp), `APP DESC`, `APP SQ. FT.`, `STREET NBR`, `STREET`, `VALUATION`, `PLANNED CHECK FEE`, `PERMIT FEE`, `TOTAL FEE`, `CONTRACTOR NAME`, `Permit Group Type`, `Permit Group Tab`.
- Watermark: `PERMIT ISS. DATE` (timestamp). `ORDER BY "PERMIT ISS. DATE" DESC LIMIT 3` → **2026-07-02T00:00:00** (e.g. _id 88449 `APP YR 26 / APP NBR 3696 SOLAR PANEL 801 PALOMA CT`, _id 89084 `APP NBR 4329 SINGLE FAMILY 1610 SECRETARIA LN`). Verified via `datastore_search_sql` (CKAN SQL).
- Cadence evidence: `date_trunc('month', "PERMIT ISS. DATE")` GROUP BY → July 86, June 1,645, May 1,292, April 1,641, March 2,004, Feb 1,418, Jan 1,395, Dec 1,563, Nov 1,448, Oct 1,940 — monthly bulk cadence ~1,400, June+July truncated at July 2.
- Recent window: `WHERE "PERMIT ISS. DATE" >= '2026-07-31'` → **0**; `>= '2026-07-01'` → **86**; `>= '2026-06-30'` → **167**; `>= '2026-06-02'` → **1,650**; `>= '2026-01-01'` → **9,481**.
- Geocoding: no native point; `STREET NBR` + `STREET` are the locator — e.g. `STREET NBR "801"` + `STREET "PALOMA CT"` → `"801 PALOMA CT, Laredo, TX"`; `WHERE "STREET NBR" IS NOT NULL AND "STREET" <> ''` → **91,198** (100%). ADR-0004 geocoder (`CensusBatchBackend` / `NominatimBackend`, `geocode_cache` hash `sha256("v1|" + normalized)`, confidence floor 0.9) is the coordinate path; `needs_geocode=true`, `geocode_context="Laredo, TX"`, `coord_source="native"` vs geocoder source.
- Grain: true building-permit issuance stream, not occupancy/fee-only. Includes valuation, fees, permit type group, contractor, expiry — Denver/OKC-style issuance archive, not a rolling occupancy window.
- Related inspection resource: `b827e5c2-6d84-4b1f-8e9b-e991ec6f67ff` (“Inspections”, 12.5 MB, 4-year inspections) is a sibling slice, not separately registrable as permits.

**Deprecated package (do not register): `building-permits` `b7cdb7e5-abc6-41ec-b577-9efdeca43180`**

- Title “Building Permits”, notes “since inception of Naviline in 2007”, resources: `Building Permits CSV` at `https://www.openlaredo.com/data/BuildingPermits.csv` (67 MB, `Last-Modified Thu, 07 Aug 2025` but datastore stalls), `Permits Issued Report XLSX` at `www.openlaredo.com/data/PermitsIssuedReports.xlsx`, `Building Inspections CSV`, plus two stale XLSX uploads through Apr 2024.
- Datastore resource `7f70bf47-7c3d-4913-864f-f5557563cbd2` (Building Permits) → `issue date` string newest **9/9/2024** (`ORDER BY "issue date" DESC`), 242,108 rows `WHERE "issue date" >= '2026-01-01'` misleading because the date is stored as `M/D/YYYY` string and the datastore’s newest real row is 2024-09-09; 0 fresh in 2026. Superseded by the 2022-present package above. Field `issue date` is string, no address columns.
- Verdict: stale archival dump, not the live feed.

**Hub snapshot (do not register): `OD 2014 Total Building Permits`**

- Hub item `6d267c2d45b54e4ca5abb5a195716906` / FeatureServer `services3.arcgis.com/h9QEFLHkUI1SIRs7/arcgis/rest/services/OD_2014_Total_Building_Permits/FeatureServer/5` → `lastEditDate 1556720710918` (2019-05-01), single-year 2014 polygon snapshot, not a permits issuance stream.

### 311 — Tier 3 (none live)

- CKAN `package_search?q=311` = 4 real 311 datasets among 6 hits:
  - `311-service-requests` (9e4c40ad…) 5 yearly slices 2014-2018 (Completed Requests), each `last_modified` 2019-04-04, fields include `Latitude`/`Longitude` + `Request Address One`/`Two` + `Request Type` + `Close Date` — **native point is present** but newest close is **2018** (resource `30d0759e…`), 7+ years stale.
  - `311-closed-requests-2018-through-2022` (006a289a…) 4 resources 2019-2022 (`9e8b1c3f…` 2019, `9ba30b00…` 2020, `99e2f726…` 2021, `623f4a1b…` 2022), `last_modified` 2022-10-03, fields `Department`, `Request Description`, `Create Date`/`Time`, `Closed Date`/`Time`, `Days Open` — **no lat/lng, no address**; newest `Closed Date` **9/9/2022** (ORDER BY DESC, 2, etc), 0 in last 60 days at probe.
  - `311-closed-requests-by-department-fy19-20-through-fy22-23` (ef9672d8…) 1 CSV `last_modified` 2023-10-13 — same limited fields.
  - `311-closed-requests-by-department-fy23-24` (18c1b374…) 1 CSV `af1a96fd…` 37,468 rows, `last_modified` 2024-06-26, fields `Assigned Dept`, `Create Date`, `Close Date`, `Request Type`, `Council District` — **no lat/lng, no address**; newest `Close Date` **2024-06-26 00:00:00** (`ORDER BY "Close Date" DESC`), `WHERE "Close Date" >= '2024-01-01'` → 26,740 but 0 in 2026, staleness **~430 days** (2024-06-26 → 2026-08-30). No native or address-geocodable path in the live FY slice; the geocoded 2014-2018 slices are long-stale. The operational 311 channel is the city call center / Click2Gov intake UI, not a bulk feed — matching the southwest probe’s “Custom Call Center / CitySourced” Tier 3 call.

### SLA / business licenses — Tier 3 (none municipal)

- CKAN `package_search?q=business license` → **1** (`fiscal-year-2020-bid-tabulations`), `q=license` → **1** (same), `q=business` title scan → only `OL Downtown Tax Increment Reinvestment Zone (TIRZ1)` — no business-license issuance feed.
- Hub 54-item sweep: no license registry; `Code Enforcement Areas` is an inspector-zone boundary, not a license stream (matches the College Station/Killeen “boundary only” pattern).
- State companion: **Texas TDLR All Licenses** `7358-krk7` (`LICENSE TYPE`, `BUSINESS COUNTY`, `BUSINESS NAME`, `BUSINESS ADDRESS-LINE1`) filterable to `BUSINESS COUNTY = Webb` (FIPS 48479); **TREC** `s7ft-44qi` + `bf5n-799f`; **TABC** `7hf9-qc9f` — all Socrata, already owned by the spine (cf. `docs/research/southwest-mountain-expansion-probe-2026-08-30.md` § Texas State Super-Feed). The city’s own licenses live behind the Accela/Click2Gov citizen portal (`lare-egov.aspgov.com/Click2GovBP`) with no bulk FeatureServer.

### Deeds / sales — Tier 3 (none)

- CKAN `package_search?q=deed` → **0**, `q=sale` → **0**, `q=tax` title scan → TIRZ polygon only. Hub FS list has no sales/deed layer (54 items are annexation tracts, easements, lotlines, flood panels, census tracts, etc.).
- Webb County Appraisal District publishes annual assessment rolls and parcel polygons, not a transactional recorded-sales feed; no public bulk `IndexType='D'`-style Hub extract exists. This matches the southwest RGV/Lubbock CAD-roll Tier 3 stance.

## Hosts probed and rejected

| Host | Result |
|---|---|
| `https://data.openlaredo.com/` (CKAN) | **Live** — permits Tier 2 found here; 311/SLA/deeds Tier 3 |
| `https://open-laredo.opendata.arcgis.com/` | Hub live (54 datasets), no registrable permits/311/SLA/deeds |
| `services3.arcgis.com/h9QEFLHkUI1SIRs7/.../OD_2014_Total_Building_Permits/FeatureServer/5` | Stale 2014 snapshot (lastEdit 2019) |
| Socrata `api.us.socrata.com/api/catalog/v1?domains=data.openlaredo.com` | Domain not found — not Socrata |
| `laredo-tx.opendata.arcgis.com` / `laredo.maps.arcgis.com` | Non-canonical / not the probed Hub |
| `www.openlaredo.com/data/BuildingPermits.csv` | Legacy CSV (67 MB) — datastore behind it stalled 2024-09-09, superseded |
| `cityoflaredo.com` / `lare-egov.aspgov.com/Click2GovBP` | Akamai 403 / interactive Click2Gov only — no bulk bulk API (vendor-lock UI per southwest probe, but CKAN provides the bulk instead) |
| `gis.laredo.tx.us` / `maps.laredo.tx.us` variants | No browseable open ArcGIS Server directory beyond the Hub’s hosted services |
| Socrata `data.texas.gov` state super-feed | Live (TDLR `7358-krk7` etc) — SLA companion for Webb 48479, not a rejection |

## Recommendation

**Register Laredo, TX (`laredo`, Webb County 48479) as a South Central leaf.** The live CKAN permits feed is registrable as **Tier 2** (`needs_geocode=true`, `geocode_context="Laredo, TX"`), with the caveat that its monthly bulk cadence puts the 30-day window at **0** at this probe (newest 2026-07-02, 58 days). The 60-day window is healthy (86 in July, 1,650 since 2026-06-02), and the feed’s 2026-01-08 creation + 2026-07-22 `metadata_modified` show active maintenance — so ADR 0004’s “live + address-geocodable” bar is met for a monthly-batched CKAN source.

Leaf build: `apps/api/src/spatial/cities/laredo.py` (metro bbox + 2 divisions + 6 submarkets, center 27.5306, -99.4803), `apps/api/src/producers/field_maps_laredo.py` (PERMITS_FIELD_MAP over CKAN `61972510…` columns, `STREET NBR`+`STREET` address, DROPPED_PII `CONTRACTOR NAME`), `apps/api/tests/unit/test_producers_laredo.py` (30+ tests: bbox nesting, submarket containment, field-map first_mapped, flatten, and 58-day staleness flag pinned).

Spine delta (for the orchestrator’s hold, not this leaf): `CityId.laredo` + `ALIASES["laredo"]`/`["laredo, tx"]` + `REGISTRY["laredo"]` with CKAN datastore spec (`platform="ckan"`, `endpoint="https://data.openlaredo.com/api/3/action/datastore_search?resource_id=61972510-7b8c-488a-9e88-b73b0112f496"`, `watermark_col="PERMIT ISS. DATE"`, `needs_geocode=true`, `geocode_context="Laredo, TX"`, `order_by="PERMIT ISS. DATE DESC"`), plus optional state super-feed entries for Webb (TDLR `7358-krk7`, TREC `s7ft-44qi`, TABC `7hf9-qc9f`). Dashboard `METRO_META` and `public/index.html` byte-sync plus product facts will follow the city-registration rule (gate `pytest -m interlock` covers wiring).

If the next CKAN replace does not advance the watermark past 2026-07-31 by the 60-day re-probe, soft-downgrade permits to Tier 3 and run Laredo as a state-feed-only (SNAP/TDLR) metro per the Waco precedent.
