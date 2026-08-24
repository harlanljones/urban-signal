# Current-city feed gaps

**Date of survey: 2026-08-23.** Every endpoint below was probed live on that date
with real HTTP GETs against the exact endpoints named in `src/config.py` /
`src/spatial/city_registry.py`. "updated" is the dataset's own refresh stamp
(`rowsUpdatedAt` via `/api/views/<id>.json`, or the ArcGIS service's
`lastEditDate`); "newest record" is the max value of each feed's registered
watermark column, fetched row-by-row rather than trusted from metadata. Three
registered endpoints are broken or dead, one more is stale, and Los Angeles's
311 feed has quietly come back to life under a new name.

## Method, and its limits

Freshness probes hit each resource URL directly (`$select=count(*)`, then
newest-row-by-watermark). Catalog discovery used two paths: the federated API
(`api.us.socrata.com/api/catalog/v1`) for city domains, and — where a domain is
absent from federation — the portal's own legacy search
(`/api/search/views.json`) plus `/api/views/<id>.json`. **data.sfgov.org returns
zero results from the federated catalog** (its self-hosted catalog indexes only
5 datasets), so any survey relying on `api.us.socrata.com` alone would wrongly
conclude SF publishes nothing; the same applies to data.lacounty.gov, which is
no longer Socrata at all but an ArcGIS Hub portal (searched here via its DCAT
feed, 1,109 datasets, and the ArcGIS Online item search).

Text-typed watermarks can defeat naive `max()` probes: NYC's permit dates are
stored as text in two formats (ISO through mid-2020, `MM/DD/YYYY` after), so a
lexicographic max reports 2020 even though August 2026 records exist. Where a
probe looked wrong, the column was re-checked with format-aware queries or a
column-type dump before calling it stale. Anything not probed directly is
marked unverified below.

## Recommendation

**Fix the three broken registrations first** — they are config-line changes,
not features: repoint SF deeds `5cei-gny5` → `wv5m-vpq2` (the current ID serves
*Eviction Notices*), SF permits `i98e-46e2` → `i98e-djp9`, and Chicago deeds
`x5kz-z7if` (deleted by Cook County) → `wvhk-k5uv`. Second, register the newly
live LA 311 feed (`2cy6-i7zn`) — it is real-time, 93.8% geocoded, and needs
only six parser fallbacks. Skip an LA deeds feed entirely: no open
transaction-level source exists at city, county, or ArcGIS level (evidence
below), and the Assessor parcel-roll table that does exist carries no sale
price. Watch King County parcel sales — its layer has not refreshed since
2025-11-28.

## Workstream 3 — freshness audit of all registered feeds

Probed 2026-08-23. "watermark" is the column registered in `REGISTRY`.

| City | Feed | Dataset | Updated | Rows | Newest record (watermark) | Verdict |
|---|---|---|---|---|---|---|
| NYC | Permits | `ipu4-2q9a` DOB Permit Issuance | 2026-08-22 | 3,990,090 | `issuance_date` 08/21/**2026** | Live, but see caveat |
| NYC | 311 | `erm2-nwe9` | 2026-08-23 | 22,230,330 | 2026-08-22T02:20Z | Live |
| NYC | SLA | `9s3h-dpkz` NY SLA Active Licenses | 2026-08-23 | 60,064 | `effectivedate` 2029-09-01 (future-dated) | Live snapshot |
| NYC | Deeds | `bnx9-e6tj` ACRIS Real Property Master | 2026-08-10 | 17,065,090 | `recorded_datetime` 2026-07-31 | Live (monthly batches) |
| Chicago | Permits | `ydr8-5enu` | 2026-08-22 | 845,130 | `issue_date` 2026-08-21 | Live |
| Chicago | 311 | `v6vf-nfxy` | 2026-08-23 | 14,516,734 | `created_date` 2026-08-23T15:14Z | Live |
| Chicago | SLA | `r5kz-chrr` Business Licenses | 2026-08-22 | 1,204,676 | `date_issued` 2026-08-21 | Live |
| Chicago | Deeds | `x5kz-z7if` Cook County Property Transfers | — | — | — | **DEAD — `dataset.missing`** |
| SF | Permits | `i98e-46e2` | — | — | — | **DEAD ID — `not_found`** (successor `i98e-djp9` live) |
| SF | 311 | `vw6y-z8j6` | 2026-08-23 | 8,859,274 | `requested_datetime` 2026-08-22T23:58Z | Live |
| SF | SLA | `g8m3-pdis` Registered Business Locations | 2026-08-23 | 365,731 | `location_start_date` 2028-02-26 (future-dated) | Live snapshot |
| SF | Deeds | `5cei-gny5` "Assessor Historical Secured Property" | 2026-08-23 | 48,879 | no `closed_roll_year` col | **WRONG DATASET — serves Eviction Notices** |
| Seattle | Permits | `76t5-zqzr` SDCI Building Permits | 2026-08-23 | 192,511 | `issueddate` 2026-08-21 | Live |
| Seattle | 311 | `5ngg-rpne` Customer Service Requests | 2026-08-23 | 2,471,337 | `createddate` 2026-08-23T02:53Z | Live |
| Seattle | SLA | `vgcw-qfjm` WA LCB Local Authority Letters | 2026-08-23 | **23** | `applicationdate` 2026-08-17 | Live but tiny (see note) |
| Seattle | Deeds | ArcGIS KC `PARCEL_SALES3YR_AREA_287/0` | 2025-11-28 | 110,857 | `SaleDate` 2025-11-20; zero 2026 sales | **STALE ~9 months** |
| LA | Permits | `pi9x-tg5x` LADBS Permits Issued | 2026-08-17 | 406,916 | `issue_date` 2026-08-15 | Live |
| LA | SLA | `6rrh-rzua` Listing of Active Businesses | 2026-08-15 | 633,782 | `location_start_date` 2026-12-31 (future-dated) | Live snapshot |

Notes on the flagged rows:

- **NYC permits caveat.** `issuance_date` is a *text* column with mixed
  formats: rows through 2020-06-05 are ISO (`2020-06-05`), later rows are
  `MM/DD/YYYY` (verified: newest row `08/21/2026`, run date 2026-08-22).
  Year-suffix census: 69,308 rows end in 2021, down to 5,039 ending in 2026.
  Any consumer comparing `issuance_date > '<date>'` lexicographically will
  silently miss every post-2020 permit (`"08/21/2026"` sorts before
  `"2020-06-05"`). Same defect applies if a scheduler uses the registered
  `watermark_col` for incremental fetches. `dobrundate` is properly typed
  calendar_date and current.
- **WA LCB `vgcw-qfjm`** is a notifications feed ("local authority letters"
  for pending applications), not a license registry — 23 rows total, posted
  dates current (2026-08-20). Healthy for what it is, but volume-dependent
  analytics should not expect more.
- **KC sales staleness.** Layer `lastEditDate` ≈ 2025-11-28, newest `SaleDate`
  2025-11-20, zero rows dated ≥ 2026-01-01 (18,754 rows in Jun–Dec 2025).
  Either publishing paused or excise filings lag ~9 months; both are worth an
  alarm. This is the only deeds-grade feed Seattle has.
- Snapshot-style feeds (NYC SLA, SF licenses, LA businesses) show future-dated
  effective/start dates by design; judge them by `rowsUpdatedAt`, all of which
  are ≤ 3 days old at probe time.

## Workstream 1a — LA 311 replacement found (and it's live)

The registry comment ("data.lacity.org carries only an archived 2013-2014
extract") is out of date. The city now publishes MyLA311 as yearly datasets,
and the current-year set is real-time:

| Feed | Dataset ID | Updated | Coordinates |
|---|---|---|---|
| 311 (current) | `2cy6-i7zn` MyLA311 Cases 2026 | 2026-08-23 | `geolocation__latitude__s`, `geolocation__longitude__s` (93.8% geocoded: 1,436,422 / 1,531,913) |
| 311 (backfill) | `73a2-6ar5` MyLA311 Cases March–December 2025 | 2026-08-23 | same schema |
| 311 (backfill) | `b7dx-7gc3` …Service Request Data 2024 | 2026-08-23 | `latitude`, `longitude` |
| 311 (backfill) | yearly sets 2015–2023 (`ms7h-a45h` … `4a4x-mna2`) | static | `latitude`, `longitude` |

`2cy6-i7zn`: 1,531,913 rows spanning 2026-01-01 → **2026-08-23T13:39Z**
(same-day freshness), refreshed today. This is a genuine relaunch, not an
archive. One wrinkle: `h73f-gn57` ("MyLA311 Service Request Data 2025",
423,053 rows) stops at 2025-11-03 and was superseded mid-series by
`73a2-6ar5`; prefer the "Cases" pair for anything recent.

**Schema change warning.** The 2026 set moved to a Salesforce-derived schema
(`__c` columns): id is `casenumber` (not `srnumber`), timestamps are
`createddate`/`closeddate` (no underscore), type is `type`, zip is
`zipcode__c`, and coordinates are `geolocation__latitude(s)` — not the
`latitude`/`longitude` of the older sets. See "what implementation costs".

## Workstream 1b — LA deeds substitute: none exists openly (recommend skip)

Searched, with evidence:

| Where | What was searched | Result |
|---|---|---|
| `data.lacity.org` (federated catalog) | sales / deeds / property terms | No property-sales dataset at all (city doesn't record deeds) |
| `data.lacounty.gov` | Full DCAT sweep (1,109 datasets) grep for sale/deed/transfer/escrow/excise | Only "Alcohol Beverage Sales Locations". Zero transaction datasets. Registrar-Recorder entries are electoral-boundary maps |
| `data.lacounty.gov` platform check | direct API probes | Portal left Socrata for ArcGIS Hub (`Cannot GET /api/catalog/v1`; opendata-ui assets) |
| ArcGIS Online item search | title:"parcel sales"+"los angeles"; title:"transfer tax"+"angeles" | Zero results each |
| LA County Assessor FeatureServices (below) | field-level inspection | Roll values and a last-recording date, **no sale price, no parties** |

Best available substitute, for honesty's sake — the King County precedent does
not carry over because the county omits price:

- **Assessor Parcel Data (Rolls 2021–2025)** — ArcGIS *table*
  `services.arcgis.com/RmCCgQtiZLDCtblq/.../Parcel_Data_2021_Table/FeatureServer/0`
  (AGOL item `70d93266f45a4080a97b285a471493cd`). 12,099,614 rows; per-parcel
  per-roll-year: `AIN`, `RollYear` (2021–2025), `RecordingDate` (max seen
  2025-04-02 within roll year 2025), `Roll_LandValue`/`Roll_ImpValue`/
  `Roll_TotalValue`, property attributes, and `CENTER_LAT`/`CENTER_LON`.
  Annual snapshot, one row per parcel — it can power assessed-value context
  but cannot produce a transaction amount or grantor/grantee.
- Secondary: **Assessor Parcel Change Data (Current)** (`Parcel_Change_File`,
  560,652 rows) tracks parcel splits/merges ("1 old ==> 10 new"), not ownership
  transfers, and its newest file is 2024-07-16 — stale anyway.

Verdict: leave `FeedType.DEEDS` unregistered for LA. Registering the roll
table would put annual assessment snapshots onto a topic keyed by recorded
transactions and pollute downstream deed analytics; if assessment context is
wanted, it deserves its own feed type.

## Workstream 2 — SF deeds upgrade assessment

Two findings, one embarrassing, one negative:

1. **The registration points at the wrong dataset entirely.** `5cei-gny5`
   currently serves **Eviction Notices** (48,879 rows, no
   `closed_roll_year`/parcel/value columns — the deeds producer would emit
   null-valued events keyed by eviction case fields). The actual Assessor
   dataset is **`wv5m-vpq2` "Assessor Historical Secured Property Tax Rolls"**:
   3,934,467 rows, rolls through `closed_roll_year` 2025, loaded 2026-06-26,
   geocoded (`the_geom` Point), carrying exactly the schema the producer's SF
   branch already parses (`parcel_number`, `block`, `lot`,
   `assessed_*_value`, `analysis_neighborhood`, `closed_roll_year`). The fix
   is one config line.
2. **No transaction-level upgrade exists on DataSF.** Searched the domain's
   legacy search for: building permits, secured property tax roll, assessor,
   sales, sales price property, recorded documents, recorded deeds documents,
   official records, property transfers, eviction. Nothing resembling recorded
   documents, transfer deeds, or excise-tax sales surfaced — nearest misses
   were Campaign Finance Transactions and "SF Absent Heirs". The roll's
   `current_sales_date` (last sale per parcel, no price, sample: 1996) is the
   only transaction signal SF publishes.

Verdict: repoint to `wv5m-vpq2` and keep treating SF as a roll-based city.
An honest "SF deeds = assessments, not sales" note belongs next to the
registry entry, as it does for LA.

## Adjacent finds worth registering while touching config

- **Chicago deeds replacement:** Cook County's `x5kz-z7if` is deleted, but
  **`wvhk-k5uv` "Assessor - Parcel Sales"** is live (updated 2026-08-19;
  2,686,366 rows; 30,669 sales dated 2026, newest 2026-07-14). Columns:
  `pin`, `sale_date`, `sale_price`, `doc_no`, `deed_type`, `seller_name`,
  `buyer_name`, `township_code`, `class`, `is_multisale`, `row_id`.
  **No coordinates** — location resolves only to township code, so H3 cells
  will be null (the deeds producer tolerates null lat/lng; the other three do
  not). Older Recorder-of-Deeds extracts on the county portal are 2011–2013
  relics — ignore them.
- **SF permits successor:** `i98e-djp9` "Building Permits" (1,294,263 rows,
  refreshed daily) is the base view the dead `i98e-46e2` presumably intended;
  `cw8k-gwb7` adds contractor/licence details and issued its newest permit
  2026-08-21T16:54. Column names match the existing SF fallback chain.
  `tyz3-vt28` "PermitSF Permitting Data" (4,296 rows) is a narrow new-system
  extract, not a substitute.

## What implementation costs

Config lines (in `src/config.py`) — cheapest, do first:

1. `socrata_sf_deeds_endpoint` → `https://data.sfgov.org/resource/wv5m-vpq2.json`
2. `socrata_sf_dob_endpoint` → `https://data.sfgov.org/resource/i98e-djp9.json`
3. `socrata_chicago_deeds_endpoint` → `https://datacatalog.cookcountyil.gov/resource/wvhk-k5uv.json`

Registry edits (`src/spatial/city_registry.py`):

4. Chicago DEEDS spec: `watermark_col="sale_date"`,
   `id_keys=["doc_no", "row_id", "pin"]`; keep platform socrata.
5. LA COMPLAINTS_311 spec: endpoint `2cy6-i7zn`, `watermark_col="createddate"`,
   `id_keys=["casenumber", "srnumber", "id"]`; rewrite the stale
   "archived 2013-2014" comment.

Producer fallbacks — `complaints_311_producer.py` `parse_socrata_row`, for LA:

- incident id chain: add `"casenumber"` (before `unique_key`) and `"srnumber"`
  for the 2015–2024 backfill sets
- lat/lng chains: add `"geolocation__latitude__s"` /
  `"geolocation__longitude__s"` (plus plain `latitude`/`longitude`, which the
  backfill sets already match)
- created-date chain: add `"createddate"`; closed-date chain: add
  `"closeddate"`
- complaint-type chain: `"type"` already matches the 2026 schema; add
  `"requesttype"` for pre-2025 backfills
- zipcode chain: add `"zipcode__c"`
- optional borough signal: `"locator_sr_neigborhood_council"` (sic)
- city sniffing (when `city_id` isn't passed): a `"casenumber"` /
  `"department_name__c"` branch resolving to `los_angeles`, placed before the
  SF heuristics

Producer fallbacks — `deeds_acris_producer.py`, for Chicago-on-`wvhk-k5uv`:

- doc-id chain: add `"doc_no"`, `"row_id"`
- recorded-date chain: add `"sale_date"` (chain currently stops at
  `transfer_date`/`SaleDate`)
- amount chain already catches lowercase `"sale_price"`; parties need
  `"seller_name"` / `"buyer_name"` (the grantor/grantee chains have
  `seller`/`Sellername` and `buyer`/`buyername`, but not the underscored
  forms Cook County uses)
- coordinates: none exist — events will carry null lat/lng and null H3; verify
  downstream consumers tolerate that (the KC ArcGIS path is the only current
  deeds source with geometry)

Monitoring (no code change required to start):

6. A weekly staleness check comparing each feed's `rowsUpdatedAt` /
   ArcGIS `lastEditDate` against now would have caught all four incidents in
   this survey: the Chicago deletion, both SF misregistrations, and the KC
   pause. The probe recipes are the `$select=count(*)` +
   newest-by-watermark calls described under Method.

The implemented monitor is `scripts/feed_staleness_probe.py`. Its focused
fixture test freezes the clock and deliberately makes both source metadata and
the newest watermark 13 days old, so the default seven-day threshold must page
the feed. Its webhook test uses two endpoints and verifies identical JSON is
posted to both. Pull requests run these tests and Ruff; scheduled or manually
dispatched workflow runs perform the live probe.

Staging webhook verification is intentionally not claimed by CI: the endpoint
URL(s) are supplied through the `WEBHOOK_ALERT_URLS` repository secret, and a
pull request has no safe, deterministic staging receiver to assert against.
Run the workflow manually with `dry_run=false` and a staging secret, then
confirm the returned HTTP status and receiver record. Use `dry_run=true` for a
live feed freshness check when delivery should not be attempted. A successful
unit test proves request construction and fan-out only; it does not prove
staging credentials, network reachability, or receiver-side acceptance.

Unverified / open questions, stated plainly: whether KC's sales pause is a
publishing lapse or a lag (needs a message to King County GIS — not probed);
whether `ipu4-2q9a`'s post-2020 rows are complete or exclude some DOB NOW-only
work types (the DOB NOW datasets `rbx6-tga4`/`w9ak-ipjd` were located but not
schema-audited); and whether `tyz3-vt28` PermitSF will become the canonical SF
permits feed once the PermitSF migration finishes.
