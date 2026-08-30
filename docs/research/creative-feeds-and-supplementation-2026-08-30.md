# Creative feeds, derived signals, and gap supplementation — 2026-08-30

**Date of survey: 2026-08-30.** Four parallel research subagents, each scoped to a
theme the prior sweeps do NOT cover: (A) derived composite indices built by
COMBINING datasets already in scope; (B) environmental / remote-sensing / climate
context feeds; (C) mobility / transit / freight context feeds; (D) creative
supplementation methods for the registered metros that carry zero or one core
feed. Prior research was read first and not duplicated (`new-sources-sweep-2026-08-27.md`
rounds 1–2, `data-coverage-sweep-2026-08-25.md`, `current-city-feed-gaps.md`,
`metro-expansion-and-new-signals.md`, the federal validations, the wave probes).

Every endpoint/release below was fetched live by the subagent on 2026-08-30
unless marked *unverified*; sandbox-blocked hosts are flagged per-item. Re-probe
before registering — the repo's standing rule about quietly retired endpoints
applies doubly to non-municipal publishers.

## 0. Headline verdicts

### New live-verified REGISTER-now feeds (zero-to-small new machinery)

| # | Source | Signal | Tier | ETL cost | License | Stream |
|---|--------|--------|------|----------|---------|--------|
| 1 | **FTA NTD Complete Monthly Ridership** `8bui-9xvu` (datahub.transportation.gov Socrata) | transit system health, monthly UPT/VRM/VRH, every US agency → all registered metros | context series | zero new machinery (SocrataClient + SeriesSpec) | public domain | C |
| 2 | **NOAA GHCN-D daily station data** | per-station TMAX/TMIN/PRCP daily, keyless JSON, 132k stations; nearest-station→hex crosswalk | context covariate | low (new thin client or SeriesSpec) | public domain | B |
| 3 | **EPA AirNow AQI** | hourly AQI/O3/PM2.5 per metro (point monitors), small JSON | context covariate | low (thin client) | public domain (free key) | B |
| 4 | **USDM U.S. Drought Monitor** (weekly county shapefile/JSON) | county-level D0–D4 drought | context covariate | low (shapefile→county overlay, no raster reader) | public domain | B |
| 5 | **NWS api.weather.gov** (gridpoint forecast + alerts) | real-time heat/cold/flood alerts per metro | context covariate | low (keyless JSON) | public domain | B |
| 6 | **NOAA NCEI Storm Events** (annual CSV, lat/lon + damage $) | storm damage distress per metro | context/event | zero new machinery (CSVClient, SNAP pattern) | public domain | B |
| 7 | **USGS NWIS stream gauges** (bbox query) | flood/streamflow context | context covariate | low (bbox batch) | public domain | B |
| 8 | **MTA subway GTFS-RT service alerts** | station-level service disruptions (keyless — corrects the prior "key-gated" note) | context covariate | low (MBTA protobuf pattern already in-repo) | public domain | C |
| 9 | **GTFS static** via MobilityDatabase (1,182 US feeds) | stop density + service frequency per hex; join to LODES → jobs accessible | context covariate + derived | new `GtfsStaticClient` (bulk parse) | CC BY 3.0 | C |
| 10 | **MARTA station entrances/exits** `nwqk-3q5y` | station-level weekly ridership (Atlanta) | context feature | zero new machinery (SocrataClient) | Atlanta open data | C |
| 11 | **TX TREC broker/sales-agent licenses** `s7ft-44qi` | SLA substitute for all 9 feedless TX metros (real-occupation, daily, county-resolvable) | existing `SLALicenseEvent` | zero new machinery (SocrataClient + DatasetSpec) | TX open-data | D |
| 12 | **TX TREC initial-license applications** `bf5n-799f` | SLA *flow* (formation leading indicator), TX cohort | existing `SLALicenseEvent` | zero new machinery | TX open-data | D |
| 13 | **TX TDLR All Licenses** `7358-krk7` | contractor/trades SLA slice, TX cohort | existing `SLALicenseEvent` | zero new machinery (`MMDDCCYY` text watermark) | TX open-data | D |
| 14 | **FL Statewide Cadastral** `Florida_Statewide_Cadastral/FS/0` | PERMITS substitute via `NCONST_VAL`/`DEL_VAL`/year-built cohort for 7 FL metros | context covariate (annual, assessment-derived) | low (one ArcGIS spec) | FL public | D |
| 15 | **Buncombe County NC Property roll + `Stamps`→price** (`opendata/FeatureServer/1`) | DEEDS substitute for Asheville (roll-grade, priced via NC excise stamps `×500`) | snapshot roll | low (ArcGIS spec) | county public | D |
| 16 | **EIA API v2** (state-level electricity retail prices/RTO) | CRE operating-expense proxy | context series | low (thin client, free key) | public domain | B |
| 17 | **NASA POWER** (gridded daily meteorology, point API) | daily T2M/PRECTOTCORR per metro centroid, keyless JSON | context series | zero new machinery | public domain | B |

### Derived composite indices (transformations + combinations — Stream A)

Ten proposals, all feature-store additions (no new event schemas except where
noted). Ranked by coverage × feasibility:

| # | Index | Inputs (municipal + national) | Substitutes | Universal (all 62)? |
|---|-------|------------------------------|-------------|----------------------|
| A2 | **Commercial Vitality Churn (CVC)** | SLA + POI deltas (FSQ) + ZBP + SBA + FMCSA, cross-corroborated | missing SLA feed | Yes (≥2 sources everywhere) |
| A8 | **Small Business Credit Access (SBCAI)** | SBA + FDIC + HMDA + ZBP + ACS + SNAP | missing credit/lending signal | **Yes** |
| A9 | **Anchor Institution Stability (AISI)** | NCES schools + NPPES + SNAP + ACS + crime | missing stability feed | **Yes** |
| A10 | **Workforce Commute-Shed (WCS)** | LODES + ACS + bike/ped + GBFS + EV | missing commute/15-min-city feed | **Yes** (LODES+ACS core) |
| A6 | **Housing Market Tightness (HMTI)** | deeds + HMDA + Zillow ZHVI/ZORI + ACS + HUD-USPS | missing days-on-market/absorption | Needs deeds |
| A3 | **Displacement Pressure (DPI)** | evictions + deeds + ACS + HMDA + ZORI + HUD-USPS | missing displacement feed | Needs evictions/deeds |
| A5 | **Environmental Compliance Risk (ECRS)** | ECHO + NFIP + FEMA disasters + energy benchmark + violations + ACS | missing environmental-risk feed | Partial (3 national legs) |
| A1 | **Construction-to-Occupancy Pipeline** | permits + deeds + energy benchmark + ZBP + bike/ped | missing CO/utility-hookup feed | Needs energy benchmark |
| A4 | **Infrastructure Investment Proxy (IIP)** | street cuts + permits + NREL EV + GBFS + energy benchmark | missing capital-budget feed | Partial (permits-only) |
| A7 | **Mobility & Foot Traffic Vitality (MFTI)** | bike/ped + GBFS + POI + 311 + TLC | missing foot-traffic vendor | Partial (POI+311) |

### Environmental/remote-sensing verdicts (Stream B)

| Source | Verdict | Notes |
|---|---|---|
| NASA Black Marble VNP46A2/A3 (daily/monthly night lights, 500 m) | **REGISTER (deferred to raster platform)** | leading economic-activity proxy; needs Earthdata login + HDF5 raster → same spine gap as NLCD |
| NOAA UHI Mapping Campaign (~60 cities, ~1 m air temp) | **PROBE (locate archive)** | one-shot public-domain UHI covariate for ~half the registered metros; heat.gov/CPO blocked from sandbox |
| PurpleAir community sensors | **PROBE (legal)** | CC BY-ND: H3 aggregation is a derivative work — written clearance needed |
| NASA POWER | REGISTER (above) | free, keyless, daily point meteorology |
| NOAA tide gauges | REGISTER (coastal metros) | 6-min water level, flood-frequency leading indicator |
| GRACE-FO groundwater / AIRS / CPC 0.25° / EIA-930 BA-level | **SKIP** | too coarse for sub-city |
| MODIS NDVI / Landsat LST | **DEFER** | same raster-platform spine gap as NLCD |

### Mobility/transit verdicts (Stream C)

| Source | Verdict | Notes |
|---|---|---|
| FTA NTD monthly | REGISTER (above) | zero machinery, national |
| GTFS static (MobilityDatabase) | REGISTER (above) | new `GtfsStaticClient`; accessibility covariate |
| MTA subway alerts | REGISTER (above) | keyless (corrects prior sweep) |
| MARTA entrances/exits | REGISTER (above) | Atlanta |
| CTA / LA Metro / 511 SF / WMATA / SEPTA GTFS-RT | **SKIP** | each key-gated; GTFS static gives the same service-frequency signal cheaper |
| NPMRDS/INRIX congestion | **PROBE** (NPMRDS free version on datahub.transportation.gov; else CA PeMS) | commercial ($50k/yr) out; free travel-time exists but verification pending |
| BTS freight index, CFS, AAR, parking occupancy | **SKIP / PROBE** | national-grain or stale; parking feeds weak |

### Supplementation methods for feedless metros (Stream D)

The gap profile: **24 registered metros carry exactly one core feed; 21 are
SLA-only; ~18 are fed only by the national SNAP-retailer supplement (i.e. zero
municipal feed).** No universal open, transaction-grade substitute exists for
any of the four feeds. Honest tiers:

1. **Real county transaction feeds** — exist only for a minority: Buncombe NC
   (Asheville, roll + `Stamps`×500 price reconstruction, live), Maricopa AZ
   sales affidavits (Phoenix, transaction-grade, in-repo probe). TX CAD portals,
   Onondaga, Hinds, Calcasieu, Charleston SC, Marion FL → **no open feed**.
2. **State registries** (SLA-side) — TX TREC stock + flow + TDLR cover all nine
   feedless TX metros at county resolution with zero new client machinery.
   Louisiana ATC *unverified* (host blocked). Other states are transactional
   portals, not bulk feeds.
3. **Derived indicator stacks** — the only universal answer for PERMITS (tax-roll
   new-construction/year-built cohorts; FL Statewide Cadastral is the cleanest
   single instance) and for EVICTIONS (deed/foreclosure velocity + vacancy +
   code-enforcement + FEMA claims, calibrated — never masquerades as a raw count).
4. **311** — no national substitute; SeeClickFix API is now key-gated (403 live).
   Per-city rediscovery of code-enforcement/violations layers on existing portals
   is the only play.

**Refused techniques:** nearest-jurisdiction substitution (fabricates geography —
`city_for_point` resolves only inside bboxes) and scraping SPA CAD portals
(unmaintainable).

### Ranked top gap-fillers by impact × feasibility (Stream D)

1. TX TREC broker/sales-agent `s7ft-44qi` (9 TX metros gain real SLA)
2. TX TREC initial-license applications `bf5n-799f` (formation leading indicator)
3. TX TDLR All Licenses `7358-krk7` (contractor/trades slice)
4. FL Statewide Cadastral (7 FL metros gain a construction covariate)
5. Buncombe roll + `Stamps`→price (Asheville gains DEEDS)
6. Maricopa Sales Affidavits (Phoenix gains transaction-grade DEEDS)
7. National license stack extension (FMCSA/NPPES/SNAP — every feedless metro ≥2 SLA families)
8. Eviction Lab county data + ETS (county eviction context; registration/license-gated)
9. Code-enforcement/violations rediscovery (311-derived, per-city)
10. HUD USPS vacancy/no-stat + Overture footprint diff (construction-vs-longevity context)

**Honest bottom line:** no currently-feedless metro reaches 4/4 from these ten.
311 and PERMITS have no universal open substitute. Asheville and Phoenix reach
2–3 feeds; the nine TX metros go from SNAP-only to a three-registry occupation
stack; Jackson MS / Lake Charles / Monroe / Fort Smith / Jonesboro / Charleston SC /
Alexandria / Buffalo / Syracuse / Lexington / Toledo / Dayton remain
represented only via national-masked + derived-index treatments.

## 1. Method and limits

- Stream A grounded every proposal in actual registered sources (read
  `national_feeds.py`, `hmda_metrics.py`, `zbp_signal.py`, `acs_pipeline.py`,
  `epa_echo.py`, feature/graph builders) rather than inventing columns. Failure
  modes per index reflect real known defects (century-typo watermarks, POI
  release lag, suppression flags, HMDA leaf-not-wired, GISETC).
- Streams B/C/D fetched endpoints live; sandbox-blocked hosts are listed per
  item (fcc.gov, developer.nrel.gov from prior sweeps; here transit.dot.gov,
  fhwa.dot.gov, api.goswift.ly, heat.gov, cpo.noaa.gov, LA ATC, Texas CAD
  portals, SeeClickFix).
- Watermark/text-format traps flagged where found (TDLR `MMDDCCYY`, NY mixed
  permit-date formats).

## 2. New ETL components (design sketches)

### 2.1 `GtfsStaticClient` (Stream C)
- Pull the MobilityDatabase US GTFS-schedule catalog (keyless API or the GitHub
  mirror), download each operator's `google_transit.zip` in scope, parse
  `stops.txt`/`routes.txt`/`stop_times.txt`/`trips.txt`/`calendar.txt`.
- Emit per-hex covariates: `stop_density`, `service_frequency` (daily departures),
  `route_count`, filtered by metro bbox intersection. Quarterly refresh (GTFS
  static changes slowly). Join with LODES job counts → jobs-accessible-within-800m.

### 2.2 AirNow/GHCN-D/weather thin clients (Stream B)
- **GHCN-D**: `ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=...`
  keyless JSON; nearest-station→hex crosswalk; daily TMAX/TMIN/PRCP.
- **AirNow**: `airnowapi.org/aq/observation/zipCode/current/` (free key), hourly.
- **NWS**: `api.weather.gov/points/{lat},{lon}` → forecast + `alerts/active`; keyless.
- All three are context covariates on `EnrichedH3Feature`; no new event schemas.

### 2.3 County-roll price reconstruction (Stream D, DEEDS substitute)
- Buncombe: `SalePrice` is zeroed on the live layer, but NC excise-tax `Stamps`
  ($1.00 per $500 or fraction) is populated on 76,977 / 135,239 parcels.
  Reconstructed price ≈ `Stamps × 500` — proportional on large sales, overstates
  small/fraction sales. Snapshot mode; `Instrument`/`Reason` filter for
  non-arm's-length. This is the "roll-without-price ≠ deeds" exception SF/LA
  precedent warns about, *partially* restored.

### 2.4 TX state-registry SLA specs (Stream D)
- Three Socrata specs (`s7ft-44qi`, `bf5n-799f`, `7358-krk7`), daily, county-name
  resolution via `geography_crosswalk` → county covariates (not H3 points —
  label honestly). TDLR needs format-aware `MMDDCCYY` watermark parsing.

## 3. Spine impact (read before implementing)

Per `docs/agents/parallel-streams.md`: nearly everything above is leaf-shaped
(DatasetSpec / thin client / feature-store / macro-series). The two exceptions:

1. **Stream A** composite indices all write `EnrichedH3Feature` keys and most add
   a per-city `macro_series` row — feature-store additions only. A4 needs
   `InfrastructureEvent` (NREL EV decision US-371 pending); A8 needs
   `SbaLoanEvent` + `BankBranchEvent`; A9 needs `AnchorInstitutionEvent`;
   HMDA/ECHO/LODES national legs must be live before the indices that depend on
   them. Only A8, A9, A10 are buildable today from already-registered sources.
2. **Stream B** rasters (Black Marble, MODIS, Landsat) all wait on the same
   raster-platform gap as NLCD — defer until that spine decision lands.
3. **Dashboard wiring** — the AGENTS.md city-registration rule applies by analogy:
   a new signal that isn't on the dashboard isn't shipped. Any city that gains a
   new feed from Stream D (e.g. Asheville DEEDS-roll, FL metros construction
   proxy) must show it on the map in the same spine hold, or the interlock gate
   (`pytest -m interlock`) stays red.

## 4. Recommended order

1. **Stream D #1–#4** (TX TREC/TDLR + FL Cadastral — live-verified, zero-new-client,
   covers the largest feedless cohort in one hold).
2. **Stream B** GHCN-D + AirNow + NWS + USDM + Storm Events (keyless/CSV, national,
   feeds every feedless metro a climate/weather signal).
3. **Stream C** FTA NTD via SeriesClient (zero machinery), then MARTA, then
   `GtfsStaticClient` + MTA alerts.
4. **Stream A** A8 (SBCAI) → A9 (AISI) → A10 (WCS) → A2 (CVC) — the universal
   indices, then the deeds/evictions-gated ones (A6, A3) as those feeds land.
5. **Stream D #5–#6** (Buncombe roll, Maricopa affidavits) as DEEDS supplements.
6. **Deferred/probe**: Black Marble + MODIS/Landsat (after raster platform),
   NOAA UHI archive location, NPMRDS free travel-time, Eviction Lab licensing.
