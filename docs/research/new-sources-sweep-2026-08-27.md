# New data sources sweep — 2026-08-27 (four parallel research streams)

**Date: 2026-08-27.** Method: four parallel research agents, each scoped to a source
category NOT covered by prior surveys (`metro-expansion-and-new-signals.md`,
`non-socrata-platforms.md`, `overture-maps-evaluation.md`, and the federal
validations — ECHO, HMDA, HUD-USPS, QCEW, BFS/ZBP/LODES, ACS, NLCD). Every
endpoint/release/terms page below was fetched live by the agent on 2026-08-27
unless marked *unverified*; two sandbox-blocked hosts (fcc.gov,
developer.nrel.gov) are flagged per-item. Re-probe before registering — the
repo's standing rule about quietly retired endpoints applies doubly to
non-municipal publishers, who change delivery channels without notice (FSQ did
exactly that in Oct 2025).

Complements, not duplicates: US-360 (Overture **buildings**), US-361 (ACS
**demographics** pilot), US-362 (NYC **TLC trips**) already cover their subjects.
This sweep adds four NEW signal families and one context-series family.

## 0. Headline verdicts

| # | Source | Signal | Tier | ETL cost | License | Verdict |
|---|--------|--------|------|----------|---------|---------|
| 1 | GBFS station-based bikeshare (Lyft/BCycle pool) | station installs/removals + live availability | **new event** + feature | new `SnapshotClient` | per-operator; Lyft pool commercial-OK | **REGISTER** |
| 2 | Foursquare OS Places (deltas) | business openings/closings, national | **new event** | new `poi_diff_producer` | Apache 2.0 | **REGISTER** |
| 3 | FEMA NFIP Claims v3 + Disaster Declarations | flood-loss distress | **new event** + context | new `OpenFemaClient` (thin) | public domain | **REGISTER** |
| 4 | NREL AFDC EV charging stations | new-infrastructure capex proxy | **new event** | new `NrelAfdcClient` | public domain (verify terms page) | **REGISTER** |
| 5 | Zillow ZORI/ZHVI/ZHVF + FHFA HPI + HUD SAFMR + ACS ZCTA | rent/value/income series | context (macro model) | new `SeriesClient` | Zillow ToU §4.C w/ attribution; rest public domain | **REGISTER** |
| 6 | USDA SNAP retailer locator | food-retail license churn | existing `SLALicenseEvent` | **zero new machinery** (CSVClient/ArcGISClient) | public domain | **REGISTER** |
| 7 | Building energy benchmarking NYC `5zyy-y8am` / CHI `xq83-jr8c` / SEA `teqw-tu6e` | building-stock performance | context feature | **zero new machinery** (SocrataClient) | city open-data terms | **REGISTER** |
| 8 | NYC bike/ped counts `ct66-47at` + SEA Fremont `65db-xm6k` | foot-traffic vitality | context feature | **zero new machinery** (SocrataClient) | NYC open data; WA public domain | **REGISTER** |
| 9 | Overture **places** changelog | cross-check for #2 | event (corroboration) | shares `poi_diff_producer` | CDLA-Permissive 2.0 / Apache-2.0 / CC0 mix | PROBE |
| 10 | OpenStreetMap osmchange diffs | openings/closings (independents) | event | diff client | ODbL — share-alike gate | PROBE (legal first) |
| 11 | All The Places weekly builds | chain openings, fast lag | event | shares `poi_diff_producer` | CC0 | PROBE (after #2) |
| 12 | FRED API | metro HPI/rent covariates | context | SeriesClient api profile | mixed (S&P ©) | PROBE (prefer FHFA) |
| 13 | Realtor.com / Redfin market CSVs | listing-side lead signals | context | SeriesClient bulk | **ToU bans ML/AI use** (Realtor); Redfin unverifiable | PROBE (written clearance) |
| 14 | FCC BDC | connectivity context | context | batch loader | public domain | PROBE (semiannual batch) |
| 15 | EIA-860M | grid capex | event (sparse) | ExcelClient + plant join | public domain | PROBE (tier-2) |
| 16 | LA small cells `7dww-jq9x`, GTFS-RT (MBTA pattern), SFMTA counts, BART exits, Citi/Divvy trip archives | misc | context/event | various | various | PROBE |
| — | Lime/Bird/Spin/Bolt GBFS, OpenChargeMap, OpenCorporates, Apartment List, FCC ASR, Google/Yelp/SafeGraph, LADOT counts | — | — | — | hostile ToU / paid / stale | **SKIP** (see §4) |

The round number: **eight register-now items, of which three need zero new
machinery.** The four new components are small and deliberately shaped to
unlock whole families, not single feeds.

## 1. New ETL components (the designs)

### 1.1 `SeriesClient` — aggregate series → macro/context store

**Problem it solves:** every market-series source is either a static bulk CSV
(Zillow, FHFA, Realtor) or a keyed non-paginating REST series API (HUD, FRED,
Census). None fits `PaginatingClient`, and none produces point events — rows
are keyed `(geography, period)`, which the per-topic producers cannot classify
or H3-tag.

**Contract** (one ~300-line component, three profiles):

- `SeriesSpec` (DatasetSpec-style): `source` (zillow|fhfa|hud|fred|census),
  `dataset_id` (URL or series/entity id), `auth` (none|bearer|api_key ref),
  `layout` (`wide_dates_as_columns` | `long_rows`), `geography_level`
  (metro|city|county|zip|neighborhood), `geography_col`, `period` +
  `period_type` (month|quarter|fiscal_year), `field_map`, `series_id`.
- **Geography crosswalk table** — the one shared reusable asset: metro/city
  name and CBSA code → `city_id`, plus ZIP/ZCTA → H3 res7/8/9 via centroid
  (HUD publishes a public-domain USPS ZIP crosswalk). `parcel_join` does not
  provide this; every series source needs it.
- **Output:** no Kafka event per row — upsert a `macro_series` store keyed
  `(city_id, series_id, geography_id, period)` with `value, ingested_at,
  source_vintage`; DCN-v2 macro model consumes it; ZIP→H3 join feeds
  `EnrichedH3Feature` covariates.
- **Revision handling is mandatory:** Zillow/FHFA/Realtor reissue and revise
  full history — `ingestion_mode: full` semantics, whole-file diff, upsert
  changed history, retain vintages. Watermark = max period per
  `(series_id, geography_id)` but never append-only.
- **Civility:** monthly cron aligned to publisher cadence (Zillow the 16th,
  FHFA release calendar, HUD annual Oct); ToUs prohibit aggressive automated
  querying.

### 1.2 `SnapshotClient` — live state feeds with no watermark (GBFS first)

**Problem it solves:** GBFS station feeds change state **in place** — no
watermark column exists; station installs/removals are visible only by diffing
snapshots. This archetype also fits LA small-cell `7dww-jq9x` (monthly, point,
attribute-poor) later.

**Contract:**

- `DatasetSpec` keys: `platform: snapshot`, `endpoint: <auto-discovery
  gbfs.json>`, `interval_seconds` (60–120 status / 3600 station_information),
  `feeds: [station_information, station_status]`, `ingestion_mode: snapshot`
  (idempotent upsert keyed `(system_id, feed, snapshot_ts)`), `state_store:`
  persisted station set + last status snapshot per `system_id`.
- Each poll: resolve discovery feed (follow `gbfs_versions`; pin v1.1/2.3/3.0
  dialects — verified live: Lyft 2.3, BCycle LA 1.1, publicbikesystem 3.0),
  fetch named feeds, validate required fields per version.
- **Diff station_id set vs state store → emit `StationChangeEvent`**
  (station_added/station_removed; id `system_id:station_id`; lat/lng → H3 via
  existing indexer; event_date = transition date). Status rows upsert into the
  state store for later per-hex aggregation (availability volatility,
  utilization, bike/dock turnover).
- Normalize operator quirks to DLQ: `num_docks_available=999999` sentinels,
  `last_reported=86400`, pre-activation stations (`is_installed=0`), null
  capacity on v1.1, city-centroid placeholder stations in free-floating feeds.
- **Per-operator license gate in config:** Lyft Citi Bike/Divvy/Bay Wheels +
  BCycle pool allowed (Lyft Data License Agreement grants product use;
  prohibits re-hosting raw data as a standalone dataset — verified today).
  **Lime/Bird/Spin/Bolt/Veo are barred** (internal-non-commercial-only,
  10-minute retention, no-database-augmentation clauses — verified today).
  We are the only historical archive of station_information, so the state
  store is itself the product.

### 1.3 `poi_diff_producer` — release-delta POI churn → `poi_change` event

**Problem it solves:** business move-in/out is our best derived signal but is
bound to municipal license feeds that don't exist in most metros. FSQ OS
Places publishes an explicit machine-readable churn channel nationally,
monthly, under Apache 2.0.

**Contract:**

- New archetype — **release-delta producer**, not a `PaginatingClient`:
  (1) resolve latest release id (FSQ `dt=`, Overture release tag, ATP run
  date); fetch **delta partitions only** (FSQ `deltas/parquet/` with
  `action ∈ {add,update,remove,merge}` + `redirect`; Overture
  `changelog/<REL>/theme=places/` with `change_type` partitions, rows carry
  `bbox` for server-side metro filtering); snapshot backfill once.
- (2) Join delta ids → place attributes; apply FSQ's documented
  non-commercial category exclusion list (38 ids) and
  `unresolved_flags ∋ closed` down-weighting; for Overture, require
  `operating_status → permanently_closed` flips (verified schema values:
  `open | temporarily_closed | permanently_closed`) and/or
  two-consecutive-delta corroboration — naive added/removed counts are
  GERS-matcher noise.
- (3) Classify `add|create → poi_opened`; `remove|merge(via redirect)|closed
  status → poi_closed`; event date = release date (documented detection-date
  bias — `date_closed` is a database date, not ground truth).
- (4) `city_id` by point-in-registered-metro-bbox (all sources carry lat/lon —
  no geocoding); H3 via existing indexer; null-geometry rows → DLQ.
- (5) Dedup `id_keys = (source, native_place_id)`; precedence FSQ > Overture >
  ATP > OSM; cross-source identity resolution (name+phone+geohash) deferred.
- **Emit as a new `poi_change` event — do NOT overload `SLALicenseEvent`.**
  A license is a government authorization; a POI detection is not. Conflating
  them corrupts the license-based move-in/out semantics. (SNAP data, §2.6,
  genuinely IS a license and enters through the existing license path.)

### 1.4 `OpenFemaClient` — thin OData client (closest to existing archetype)

- `PaginatingClient` impl over `https://www.fema.gov/api/open/v3/...`:
  `$filter=<watermark_col> ge <watermark>` + `$top/$skip` paged via
  `@odata.count`; no key.
- Serves two datasets: **NfipClaims** (v3 — v2 `FimaNfipClaims` is deprecated:
  frozen 2026-06-01, removed 2026-10-15, deprecation header verified live) and
  **DisasterDeclarationsSummaries** (still v2-only; v3 404s — verified).
- **Geometry caveat:** NFIP lat/lng is privacy-truncated to 0.1° — too coarse
  for res8/9. Tag hexes via `censusGeoid` (full tract GEOID, verified present)
  or ZIP centroid join instead of raw coordinates.

### 1.5 `NrelAfdcClient` — keyed REST + snapshot diff

- `developer.nrel.gov/api/alt-fuel-stations/v1.json` (free key), param
  `fuel_type_code=ELEC`; offset pagination; hourly rate cap is generous.
- Diff vs prior snapshot keyed by station `id` → emit opening events stamped
  `open_date` (fall back to first-seen `last_updated` where missing — verified
  spotty); carry port counts (`ev_level2_evse_num`, `ev_dc_fast_num`), access
  type, status transitions.
- Freshness verified via afdc.energy.gov ("last updated 8/27/2026") — the API
  host itself blocked the research sandbox; **spot-verify
  developer.nrel.gov/terms/ before build**.

## 2. Register-now detail (per source)

### 2.1 GBFS station-based bikeshare — `SnapshotClient` (§1.2)

Verified live today: NYC Citi Bike 2,508 stations; Chicago Divvy 2,050;
SF Bay Wheels 633 (incl. San Jose); LA Metro Bike 223; plus Blue Bikes (BOS),
Indego (PHL), BIKETOWN (PDX), Bublr (MKE), Pogoh (PIT), CapMetro (AUS),
MoGo (DET) — CoGo (CMH) timed out, probe at implementation. No operator-side
history: **we become the archive**. Trip-history archives (Citi/Divvy/Bay
Wheels monthly S3 CSVs) are a follow-on `CSVClient` registration after live
ingestion works.

### 2.2 Foursquare OS Places — `poi_diff_producer` (§1.3)

Delivery changed Oct 2025: Places Portal (free token) → Iceberg catalog;
Hugging Face parquet mirror as fallback (`release/dt=YYYY-MM-DD/`, 21 archived
releases 2024-12 → 2026-08, latest 2026-08-11 — verified). 109M places global;
US openings 30–62k/mo in recent releases; `date_created`/`date_closed`/
`unresolved_flags` columns. Apache 2.0 — cleanest license of any candidate.

### 2.3 FEMA NFIP Claims v3 + Disaster Declarations — `OpenFemaClient` (§1.4)

Claims: 2M+ rows, 84 fields, `dateOfLoss` event date, asOfDate 2026-08-03
(verified). Disasters: county-anchored (`placeCode`/`fipsCountyCode`),
lastRefresh 2026-08-20 — context flags per hex via county overlay.
Public domain (OpenFEMA terms; terms page Akamai-blocked from sandbox —
re-verify from a normal egress).

### 2.4 NREL AFDC EV charging — `NrelAfdcClient` (§1.5)

~80k+ US stations, point lat/long, `open_date`, continuous refresh. New-event
tier: infrastructure-investment capex proxy — the leading-indicator story the
permit feed tells, nationally, without a municipal portal.

### 2.5 Market series — `SeriesClient` (§1.1)

- **Zillow ZORI/ZHVI/ZHVF** — ZIP/neighborhood granularity, monthly on the
  16th (July 2026 verified live); ToU §4.C permits aggregate-data derivative
  works **with attribution on every surface** ("Data Provided by Zillow
  Group"); §5 bans automated queries against zillow.com proper — the research
  CSV host is the published download channel; keep the fetcher polite.
- **FHFA HPI** — public domain; master CSV
  `fhfa.gov/hpi/download/monthly/hpi_master.csv` + quarterly metro files;
  2026Q2 verified latest; annual county/ZIP3/ZIP5/tract files (XLSX).
- **HUD Small Area FMRs** — public domain; REST `huduser.gov/hudapi/public/fmr`
  (Bearer, 60 req/min, verified ToS) or FY26 XLSX bulk; ZIP-level 40th-pct
  rents; annual each Oct 1.
- **Census ACS ZCTA** (B25064/B25031/B19013) — public domain; API key now
  required (verified); annual 5-year vintage; static structural baseline the
  dynamic series trend away from. Coordinate with US-361 (tract-level
  demographic pilot) — same source, different tables/geography.
- FRED (S&P © on Case-Shiller), Realtor.com (ToU §"no ML/AI"), Redfin
  (license unverifiable) — see §3.

### 2.6 USDA SNAP retailer locator — zero new machinery

`SLALicenseEvent`-shaped: `license_id=retailer number`, `license_type` from
type field, `issued`=authorization start, `expiry`=authorization end, lat/lon
included (`needs_geocode: false`). Current CSV + ArcGIS Hub FeatureServer
(`usda-snap-retailers-usda-fns.hub.arcgis.com`); 2005–2025 historical zip
(22.9 MB, current as of 2025-12-31). Public domain. plugs the license-feed
gap in every small metro. Food-retail slice only — say so in feature names.

### 2.7 Building energy benchmarking trio — zero new machinery

SocrataClient + DatasetSpec, `needs_geocode: false` (lat/lng present):
NYC LL84 `5zyy-y8am` (max report_year 2024), Chicago `xq83-jr8c`
(max data_year 2023 — lags), Seattle `teqw-tu6e` (DataYear 2024 sampled live,
carries ENERGY STAR score, SiteEUI, GHG, compliancestatus). Annual cadence.
Per-hex context: mean SiteEUI, % non-compliant, % score<50, GHG YoY deltas.

### 2.8 Bike/ped counters — zero new machinery

NYC `ct66-47at` (15-min directional bike/ped, 41 sensors, same-day freshness
verified, depth to 2012) + sensor registry `6up2-gnw8` (lat/lon,
firstdata/lastdata); Seattle Fremont `65db-xm6k` (hourly, public domain,
~4-week lag). NYC ATR `7ym2-wayt` optional (7-month lag, EPSG:2263 `wktgeom`).
Feature tier: flow intensity per hex. Note for NYC: this is the foot-traffic
signal until TLC trip analytics (US-362) mature.

## 3. Probe-more (blocked, but valuable)

- **Overture places changelog** — free, keyless, license-clean (CDLA-2.0 /
  Apache-2.0 / CC0 mix, verified on the attribution page); `2026-08-19.0`
  release partitions verified. Role: **cross-check source inside
  poi_diff_producer**, corroborating FSQ churn. Buildings side is US-360.
- **OSM osmchange** — minutely diffs verified live (<1 min old); the only
  open source covering independents. Blocked on: ODbL share-alike review for
  anything OSM-derived that leaves the building (internal model features are
  low-risk; client-facing per-hex POI-churn scores trigger the duty), plus
  closure under-reporting (only 75k `opening_date` tags globally vs 7.2M
  shop tags — the diff is the signal, not tags).
- **All The Places** — CC0, weekly, 20M+ POIs; intended usage is
  build-over-build ID diff; ID churn per spider needs stability tracking.
  Adopt after FSQ, as the fast-lag chain accelerator.
- **FRED** — fallback HPI source; S&P © restricts redistribution of derived
  products; prefer FHFA.
- **Realtor.com / Redfin** — freshest listing-side lead signals (new listings,
  pending ratio, median DOM, hotness at ZIP level; Redfin adds neighborhood
  sales). Realtor ToU explicitly bans ML/AI training use; Redfin's license
  page 404s and downloads moved behind a JS modal (S3 listing 403).
  Written clearance (economics@realtor.com / econdata@redfin.com) before any
  model consumption; display-only use is the fallback.
- **FCC BDC** — semiannual structure-level broadband availability; batch
  context refresh, not an event pipeline; hosts bot-blocked the sandbox —
  confirm file layout manually first.
- **EIA-860M** — monthly grid-capex proxy; ExcelClient fits, but plant
  coordinates need an EIA-860 join; sparse by nature. Tier-2.
- **LA small cells `7dww-jq9x`** — monthly point layer, first-seen diffing via
  SnapshotClient once it exists.
- **MBTA GTFS-RT alerts** — key-less CDN pattern (`cdn.mbta.com/realtime/*.pb`,
  verified); MTA/CTA/BART are key-gated; low CRE signal-to-noise. Pattern
  probe only. (Transitland now 401s without registration.)
- **BART monthly station exits; SF SFMTA counts (likely ArcGIS — probe AGOL
  org); Citi/Divvy/Bay Wheels trip archives** — follow-ons.

## 4. Skip list (do not revisit without new evidence)

- **Dockless operator GBFS (Lime/Bird/Spin/Bolt/Veo)** — terms grant
  internal-non-commercial use only, ban derivative works/third-party
  aggregation/database augmentation, cap retention at 10 minutes. Hostile.
- **OpenChargeMap** — license unverifiable (login-walled), redundant with AFDC.
- **OpenCorporates** — paid (£2,250/yr entry), address-only, weaker proxy.
- **Apartment List** — personal-non-commercial ToU, no stable URL.
- **FCC ASR** — macro towers, wrong granularity for neighborhood momentum.
- **Google Places / Yelp / SafeGraph / Placer** — paid/closed.
- **LADOT counts** — static (2020), stale.
- **NYC street construction permits `tqtj-sjs8`** — already adjudicated by
  US-81: 2026 rows are address-only (wkt survives on 128 of 448k rows);
  blocked on geocoding. A research agent sampled a 2026 row carrying `wkt`;
  treat US-81's count as authoritative until re-audited.

## 5. Schema and spine impact (read before implementing)

Per `docs/agents/parallel-streams.md`, each new signal family costs spine
edits beyond its leaf client: `FeedType`/topic registration, Avro schema,
consumer wiring, `EnrichedH3Feature` keys, dashboard wiring (the AGENTS.md
city-registration rule applies by analogy — a new signal that isn't on the
dashboard isn't shipped), and `pytest -m interlock` green in the same spine
hold. Proposed event additions, cheapest first:

1. **No new event** — SNAP (reuses `SLALicenseEvent`), energy benchmarking +
   counters (context features on `EnrichedH3Feature`), series (macro store).
   Leaf-shaped; register first.
2. **One new event, shared shape** — `StationChangeEvent` (GBFS) and possibly
   a generic `InfrastructureEvent` (category: ev_station | small_cell |
   grid_capacity) to avoid four near-identical schemas. Decide the
   generic-vs-per-family question once, in one spine hold, before NREL lands.
3. **`poi_change` event** — own schema (opened/closed, source, category,
   confidence), plus `poi_opened_count`/`poi_closed_count`/net-churn feature
   keys mirroring the license move-in/out aggregation.
4. **`insurance_loss` / disaster context** — event date `dateOfLoss`, tract
   centroid → H3 tagging helper (`censusGeoid` path) is new shared machinery.

Suggested order: §2.6–2.8 (zero machinery) → `SeriesClient` (unlocks the
macro model) → `SnapshotClient`/GBFS → `poi_diff_producer`/FSQ →
`OpenFemaClient` → `NrelAfdcClient`.

## 6. Round two — five more streams (same day, 2026-08-27)

Five additional research agents swept: lending/credit/banking, healthcare
providers, education/civic anchors, state license registries, and
industrial/logistics. Same method — live endpoint/license verification —
with the round-one skip list enforced.

### 6.1 Verdict table

| # | Source | Signal | Tier | ETL cost | Verdict |
|---|--------|--------|------|----------|---------|
| 17 | State license registries: TX TABC `7hf9-qc9f` + pending apps `mxm5-tdpj`, WA L&I `m8qx-ubtq` + LCB letters `vgcw-qfjm`, OR CCB `g77e-6bhs` + OLCC apps `qad4-bnxp`, CO liquor `ier5-5ms2` (+`htyp-tqzh`), MO new-liquor `dymb-xy5c` | liquor + contractor license churn | existing `SLALicenseEvent` | **zero new machinery** (SocrataClient; one DatasetSpec per registry) | **REGISTER** — covers Seattle, Portland, Denver, Austin/Dallas/FW/El Paso, KC/StL |
| 18 | FMCSA Company Census `az4n-8mr2` + Motus AuthHist `yu5v-wbh6` + OOS orders `p2mt-9ige` (DOT Socrata) | logistics-business formation/exits, 2.23M active carriers, ~10–16k new regs/mo | existing `SLALicenseEvent` (carrier category) | zero new machinery; `needs_geocode` | **REGISTER** |
| 19 | NPPES NPI registry (weekly incremental zips + monthly deactivation report; ~8M providers) | medical-office openings/closings/moves | existing `SLALicenseEvent` (id = npi+address) | small `NppesDiffProducer` + geocode funnel | **REGISTER** |
| 20 | NCES CCD directory + EDGE geocodes | school open/close/reopen (explicit `UPDATED_STATUS_TEXT`, verified 767 new / 1,031 closed in 2023-24) | **new `AnchorInstitutionEvent`** | CSVClient/ExcelClient (annual zips) | **REGISTER** |
| 21 | Head Start service locations (daily CSV, lat/lon, status, funded slots) | childcare capacity churn | `AnchorInstitutionEvent` | CSVClient, trivial | **REGISTER** |
| 22 | State childcare licensing starter set: TX `bc5r-88dy`, NY `cb42-qumz`, NYC `gy3q-4tzp`, DC MapServer/33 | household-formation proxy | existing `SLALicenseEvent` | zero new machinery | **REGISTER** (PA/MA/DE/CO next) |
| 23 | SBA 504 + 7(a) FOIA loan files (quarterly CSV, as-of date in filename) | fixed-asset capex proxy, address-level | **new `SbaLoanEvent`** | CSVClient + tiny link resolver (HMDA pattern) | **REGISTER** |
| 24 | FDIC BankFind `/locations` (+`/sod` deposits) | branch openings (ESTYMD) + banking-access distress | **new `BankBranchEvent`** + context | generic REST paginating + snapshot diff | **REGISTER** |
| 25 | IMLS libraries PLS FY2024 + NCES EDGE postsec (IPEDS) | library/postsec anchor density | context | zero machinery | **REGISTER** (cheap) |
| 26 | HRSA health-center sites (daily, pre-geocoded, `Site Added to Scope this Date`) | clinic capacity openings | context → events later | zero machinery | PROBE (register as context) |
| 27 | CMS Care Compare + nursing-home ownership (monthly, dated `Association Date`) | facility context; investor turnover | context | zero machinery | PROBE |
| 28 | FRA grade crossings `fccg-bjqh` (242k, native lat/lng) | rail-served-site density | context, one-shot | zero machinery | REGISTER (trivial) |
| 29 | FFIEC CRA tract aggregates | small-biz credit supply | context | bot-walled (403 verified) — manual annual | PROBE |
| 30 | BTS port TEU (monthly series **stalled Sep 2022**), T-100 cargo, OZ flags, EPA ACRES (endpoint moved), SBA disaster loans (phase-2), PSS private schools, IMLS museums (n=1), NY mold licenses | misc | context | various | PROBE |
| — | Fannie/Freddie loan-level (gated/licensed), CMBS, OCC PDFs, CDFI, DEA (FOIA), SAMHSA, 211, CA ABC/CSLB + IDFPR + PA HIC + 16 other portal-only states, warehouse registries, Jason's Law | — | — | — | **SKIP** |

Round-two headline: **the license-family signal can go national almost for
free.** FMCSA (carriers), NPPES (medical offices), state registries (liquor +
contractors), childcare licensing, and SNAP (round one) all map onto the
existing `SLALicenseEvent` + move-in/out machinery — the state/metro
license-feed gap closes for ~10 more metros with DatasetSpec work only.

### 6.2 Design notes unique to round two

- **State registries (17):** `license_type` namespacing (`tabc:`, `wa_li:`,
  `or_ccb:` …) so flow features can distinguish registries; status semantics
  differ per state (TABC `primary_status` vs L&I status field vs CO
  expiry-date); two date-normalization cases (TDLR `MMDDCCYY` strings,
  combined city/state/zip). NY SLA upgrade path: migrate to the daily active
  registry `9s3h-dpkz` (georeference points) if the registered feed is the
  older quarterly list.
- **FMCSA (18):** `watermark_col=ADD_DATE` (YYYYMMDD, lexicographic-safe);
  PO-Box-heavy addresses → geocode with county-FIPS fallback; AuthHist turns
  exits into dated events (no diff artifacts); Motus `inys-ebih` carries
  addresses for the newest cohort; legacy `6eyk-hxee`/`9mw4-x3tu` are FROZEN
  (2026-05-14) — never build on them.
- **NPPES (19):** never stream the 1.1 GB monthly file — weekly incrementals
  are the stream, monthly is reconciliation; diff on `(npi, normalized
  practice address)` so relocations emit move-in/out; deactivation rows carry
  NPI+date only → resolve address from our own state store; ZIP-centroid →
  metro-bbox join first, geocode only the metro-filtered delta; API hides
  deactivations (enrichment only).
- **CCD/EDGE (20):** one pipeline, two files; emit events only for
  `UPDATED_STATUS_TEXT ≠ Open`; filter `RECON_STATUS`/Changed-Agency churn;
  "Future" status = pre-opening leading signal; ~8–12-month lag is inherent.
- **SBA (23):** quarterly filenames embed the as-of date → DatasetSpec needs a
  link-resolution step against the dataset page; `ingestion_mode: full`,
  dedupe on `LocationID`; address truncated (~35 chars) — geocode with
  zip+city fallback; recommend `SbaLoanEvent` over PermitEvent reuse.
- **FDIC (24):** openings dated via `ESTYMD`, closings are detection-dated
  (snapshot diff) with `/banks/history` `EFFYEAR` (year-granular) as
  corroboration; `SERVTYPE=11` filter for brick-and-mortar; lat/lng supplied.

### 6.3 Event-schema consolidation (supersedes §5's tentative list)

Round two reuses `SLALicenseEvent` for four more families, so the new-event
count is bounded at **four new Avro types across both rounds**:

1. **No new event** (DatasetSpec/field_map only): SNAP, childcare, state
   registries, FMCSA, NPPES, energy benchmarking, counters, series (macro
   store), FRA crossings, IMLS/IPEDS/HRSA context.
2. **`StationChangeEvent`** — GBFS (round one).
3. **`poi_change`** — FSQ/Overture/ATP/OSM (round one).
4. **`AnchorInstitutionEvent`** — CCD schools/charter + Head Start (+ IMLS
   branch diffs later). category: school|charter|head_start|library;
   event_type: opened|closed|reopened; capacity field for Head Start slots.
5. **`SbaLoanEvent` + `BankBranchEvent`** — round two's two genuinely
   loan/branch-shaped families (capex proxy, banking access). `insurance_loss`
   (round one) completes the set. Decide per-family vs a shared
   `InfrastructureEvent` once, in one spine hold (NREL ticket US-371).

Updated suggested order: round-one §2.6–2.8 zero-machinery items → round-two
zero-machinery wave (state registries 17, FMCSA 18, childcare 22, FRA 28) →
`SeriesClient` → `NppesDiffProducer` → `SnapshotClient`/GBFS →
`poi_diff_producer`/FSQ → `OpenFemaClient` → CCD/EDGE + Head Start → SBA →
FDIC → `NrelAfdcClient`.
