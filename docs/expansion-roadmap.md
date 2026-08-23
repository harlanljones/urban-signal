# Expansion Roadmap: 5 → 17 metros

**Status:** Approved plan · **Created:** 2026-08-23 · **Horizon:** ~5 weeks (target finish 2026-09-26)
**Scope:** New Orleans, Norfolk, Detroit, Austin, Philadelphia, Cincinnati, Baton Rouge, Washington DC, Boston, Denver, Baltimore, Montgomery County MD
**Evidence base:** `docs/research/{new-orleans-austin-verification,socrata-sweep,non-socrata-platforms,metro-expansion-and-new-signals,current-city-feed-gaps}.md` — every endpoint below was live-probed 2026-08-23.

---

## Contents

1. [Program targets and strict metrics](#1-program-targets-and-strict-metrics)
2. [Architecture deltas](#2-architecture-deltas)
3. [Wave sequence](#3-wave-sequence)
4. [Per-city registration contracts](#4-per-city-registration-contracts)
5. [Orchestration mechanics](#5-orchestration-mechanics)
6. [Model and alerting gates](#6-model-and-alerting-gates)
7. [Risk register](#7-risk-register)
8. [Runbooks](#8-runbooks)

---

## 1 · Program targets and strict metrics

### 1.1 Terminal state (all numbers are exit criteria)

| Metric | Baseline (2026-08-23) | Target | Verified by |
|---|---|---|---|
| Registered cities | 5 | **17** | `len(REGISTRY)` + interlock closure |
| Live feed jobs | 19 | **57** | scheduler job table |
| Endpoints by platform | Socrata 18 / ArcGIS 1 | Socrata 36 / ArcGIS 14 / CARTO 4 / CKAN 3 | registry audit test |
| Platform clients in prod | socrata, arcgis | + **carto**, **ckan** | client contract tests |
| Field-map entries (data, not code) | 8 (LA only) | **~60** | per-city fixture tests |
| Parser chain terms added during program | — | **≤ 6 total** (vs 38+ the old way) | source diff audit at close-out |
| Torn-write incidents | 0 since Wave A | **0** | dispatch log |
| Stream yield (durable artifact ÷ dispatched) | 5/5, 1/1, 1/1 | **≥ 0.85 every wave** | `.streams/dispatch-log.md` |
| Spine share of delivered lines per wave | Wave B ≈ 78% (mechanism wave) | **≤ 20% for city waves** | `scripts/interlock_gap.py <base>` pre-dispatch |

### 1.2 Per-city acceptance gates (Definition of Done — all must pass)

A city is "registered" only when **every** line below is checked. No partial credit; a city failing any gate after spine application must be fixed or reverted within the same wave (`docs/agents/parallel-streams.md` torn-write rule).

| # | Gate | Threshold | Method |
|---|---|---|---|
| G1 | Interlock invariants | green | `pytest -m interlock` after each spine edit |
| G2 | Full unit suite | green, no skips added | `pytest` before wave close-out |
| G3 | Geography module | metro bbox ⊃ division bboxes ⊃ submarkets | containment invariant + `test_producers_<city>.py` geometry tests |
| G4 | Fixture fidelity | ≥ 1 real captured row per registered feed; parse asserts on id/watermark/coords/type | fixtures recorded from live API into test file |
| G5 | Live parse rate | ≥ 99% of newest 500 rows/feed produce events (point-geocoded feeds); ≥ 95% (address-geocoded); drop rate ≤ published geocode gap + 2pp | staging backfill probe script |
| G6 | Backfill parity | ingested count ≥ 99% of source `$select=count(*)` within probed window | same probe |
| G7 | Freshness lag | source `rowsUpdatedAt`/`lastEditDate` → Postgres row p95 < 15 min for ≤300 s-interval feeds over a 24 h soak | staging metrics |
| G8 | Pipeline hygiene | DLQ rate < 0.5%/feed first week; duplicate events < 0.1%; null-H3 share ≤ geocode gap (deeds-class may be 100% null where documented, e.g. Cook County sales) | Kafka/PostGIS counters |
| G9 | Division resolution | ≥ 90% of geocoded rows resolve to a declared division | PostGIS group-by audit |
| G10 | Docs | README coverage-table row; dashboard selector row applied by integrator; research doc cross-linked | integrator checklist |

### 1.3 Program-level quality metrics (weekly scorecard)

| Metric | Target | Alarm |
|---|---|---|
| Feed staleness (newest watermark age) | ≤ 7 d for every registered feed | > 7 d pages via Wave-R monitor |
| Source retirement detection | < 7 d (KC pause went unseen ≈ 9 mo) | weekly probe cron, Wave R |
| Consumer lag p95 at 2× replay load | < 60 s | load test once after Wave C2, once after C4 |
| Alert volume per new city | ≤ pooled existing-city p95 alert rate | auto-throttle until §6 calibration passes |
| Research-doc drift | endpoints re-probed ≤ 72 h before their implementation wave begins | orchestrator checklist per wave |

---

## 2 · Architecture deltas

The streaming topology (Kafka topics → H3 enrichment → PostGIS/DuckDB/MinIO → ONNX serving) does not change. Five bounded extensions are required; each lands as its own gated spine stream or leaf client module. Decisions recorded in **ADR 0002** (`docs/adr/0002-multi-platform-expansion.md`).

### D1 · Client routing extension (spine: `scheduler.py`, small)

Today `_client_for(meta)` returns `arcgis` if platform says so, else `socrata` (src/producers/scheduler.py:208). Extend to a dict dispatch `{platform: client_attr}` raising a readable error for unregistered platforms, so `carto` and `ckan` route without further scheduler edits.

### D2 · New paginating clients (leaf modules + tests)

| Client | Est. LOC | Pagination model | Unlocks | Contract-test requirements |
|---|---|---|---|---|
| `carto_client.py` | 120–180 | SQL keyset paging (`ORDER BY updated_at, cartodb_id`) | Philadelphia (4 feeds) | sentinel-date exclusion (`document_date < '3200-01-01'`), rate limit, keyset stability under writes |
| `ckan_client.py` | 150–200 | `datastore_search` offset + optional SQL | Boston (3 feeds) | year-resource rollover hook, datastore vs file-resource rejection |

Both are new files ⇒ **leaf work**; only D1 wiring touches spine.

### D3 · Year-slice endpoints (spine: `city_registry.py` `DatasetSpec` semantics)

DC permits/311 and Boston 311 publish one layer/resource **per year**. Add `extra={"endpoint_by_year": {"2026": ".../FeatureServer/18", ...}, "rollover": "manual-verify"}` resolved by the scheduler at poll time; December staging dry-run with frozen clock becomes an annual automated check. Watermark switches layers at rollover — job metric resets to zero and must re-baseline.

### D4 · Snapshot ingestion mode (producers, guarded)

Baton Rouge business registry has **no watermark column**. `extra={"ingestion_mode": "snapshot"}` ⇒ full-pull diff against stored ids instead of watermark-incremental. Parity metric: daily row-count drift ≤ 0.1%.

### D5 · Per-city field maps (already shipped, Wave B)

All city-specific column spellings enter as `DatasetSpec.extra["field_map"]` data. Budgets from research: NOLA ~19 entries, Austin ~7, Norfolk ~4, Detroit ~6 (incl. uppercase-coordinate spellings), DC ~6 (uppercase + non-standard), Denver ~4, Baltimore ~4, MontCo ~2, Cincinnati ~2, Baton Rouge ~5, Philadelphia ~4, Boston ~4. Parser-chain growth stays ≤ 6 terms program-wide.

### Scaling notes (infra checklist, not code)

- All feeds share four raw topics (`raw.municipal.*`). At 57 jobs, raise partitions ≥ 12 and key by `city_id+h3` to preserve per-cell ordering; verify consumer lag p95 < 60 s under 2× replay (§1.3).
- KEDA consumer autoscaling thresholds unchanged; observe one soak before Wave C3.
- Export snapshot + dashboard selector scale linearly: integrator applies per wave pair.

---

## 3 · Wave sequence

Dependency-driven; two implementation streams per wave maximum (the pattern's demonstrated safe concurrency), leaves parallel, spine serial. Calendar assumes ≥ 2 stream-days/wave-day capacity starting 2026-08-24; compression lever in §5.4.

| Wave | Dates (target) | Streams | Delivers | Prereqs | Exit criteria |
|---|---|---|---|---|---|
| **C1** | Aug 24–27 | `city-new-orleans` ∥ `city-norfolk`; serial spine holds between | NOLA (4 feeds) + Norfolk (4) → 9 cities, 33 feeds | none (Socrata + field maps ready) | DoD G1–G10 ×2; interlock_gap spine-share ≤ 20% |
| **C2** | Aug 28–31 | `city-detroit` ∥ `city-austin` | Detroit (4, ArcGIS) + Austin (2) → 11 cities, 39 feeds | none | DoD ×2; first 2×-replay lag test < 60 s |
| **F** | Sep 1–3 | `foundations` (D1+D3+D4 spine, one hold) then `carto-client` ∥ `ckan-client` leaves | routing dict, year-slice support, snapshot mode, both clients | C2 closed | client contract tests green incl. sentinel + rollover cases; D-gates in `tests/unit/test_scheduler.py` |
| **C3** | Sep 4–8 | `city-philadelphia` ∥ `city-dc` | Philadelphia (4, CARTO) + DC (4, year-slice) → 13 cities, 47 feeds | F | DoD ×2; DC December-rollover dry-run green |
| **C4** | Sep 9–12 | `city-cincinnati` ∥ `city-baton-rouge` | Cincinnati (3) + Baton Rouge (3, snapshot) → 15 cities, 53 feeds | F | DoD ×2; BR snapshot parity ≤ 0.1% drift × 3 days |
| **C5** | Sep 14–17 | `city-boston` ∥ `city-denver` | Boston (3, CKAN) + Denver (2–3) → 16 cities, 52–53 feeds | F | DoD ×2; CKAN year-resource rollover dry-run |
| **C6** | Sep 18–22 | `city-baltimore` ∥ `city-montgomery-co` | Baltimore (3) + MontCo (2; MC311 excluded — no coordinates) → **17 cities, 57–58 feeds** | F | DoD ×2 |
| **R** | rolling, starts with C1 | `reliability` (leaf scripts + config) | weekly staleness-probe cron (recipe: `$select=count(*)` + newest-by-watermark per feed, alarm > 7 d); NYC text-watermark normalization spike (`issuance_date` mixed formats → typed compare) | none | monitor catches a deliberately-staled fixture within one run |
| **M** | after each pair | `model-refresh` (leaf notebooks/training runs) | walk-forward retrain including new-city H3-7 block holdouts; per-city calibration report; alert unlock per §6 | prior wave closed | pinball p50 within ±10% pooled baseline per city |

Contingency swaps (if a feed dies inside its wave — re-probe rule §5.3): next-ranked verified candidates are Orlando (2/4), Prince George's Co (near-miss), Everett WA (small), Mesa (rejected—aggregates). Alameda transfer feed re-checks annually.

---

## 4 · Per-city registration contracts

Exact spec each city stream implements (feeds, ids, watermarks, map budgets). IDs from the 2026-08-23 probes; re-probe is part of the wave's phase-1 claim.

| City (job_suffix) | Feeds → datasets (watermark) | Platform | field_map budget | Known quirks that tests must pin |
|---|---|---|---|---|
| **New Orleans** `nola` | PERMITS `rcm3-fn58` (`issuedate`) · 311 `2jgv-pqrq` (`date_created` — corrected from probe; survey's `createddate` was wrong) · SLA `hjcd-grvu` (`businessstartdate`) · DEEDS `hpm5-48nj` (`sale_date`, NORA caveat comment) | socrata ×4 | ~19 | permits `location_1` container; `pin` must NOT reach job-id chain; licenses leak ~18% out-of-parish rows + future-dated max 2027-02; deeds have no price (amount=0.0 accepted); 311 ~4% zero-coords (null-island guard covers) |
| **Norfolk** `norfolk` | PERMITS `fahm-yuh4` (`issue_date`) · DEEDS `qva7-tzrf` FY27 sales (`transfer_date`) | socrata ×2 | ~5 | 311 `nbyu-xjez` + licenses `dpi6-sct5` DEFERRED — no coordinates (address string / none), need geocoding capability; sales keyed addr+GPIN with null-H3 events like Cook County; rotate FY dataset ID each July |
| **Detroit** `detroit` | PERMITS BSEED FeatureServer · 311 Improve Detroit · SLA Business Licenses (Current) · DEEDS Assessor Property Sales | arcgis ×4 | ~6 | DateOnly fields arrive `"YYYY-MM-DD"` strings (epoch converter no-op — pin this); licenses layer modified-date granularity |
| **Austin** `austin` | PERMITS `quv8-5ckq` (`issue_date`) · 311 `xwdj-i9he` (`sr_created_date`) | socrata ×2 | ~7 | partial city like LA (SLA/DEEDS absent w/ TABC comment); sr_number sniff regression test mandatory; domain outside discovery mesh |
| **Philadelphia** `philly` | PERMITS `permits` · 311 `public_cases_fc` · SLA `business_licenses` · DEEDS `rtt_summary` | carto ×4 | ~4 | CartoClient prereq; sentinel dates (yr 3200/9798) filtered in watermark queries; rtt includes mortgages (~1.16M real docs) |
| **Cincinnati** `cinci` | PERMITS `uhjb-xac9` (`issued`) · 311 `gcej-gmiw` (`created_on`) · SLA `ehdi-ajku` | socrata ×3 | ~2 | no sales; address-geocoded permits (G5 threshold 95%) |
| **Baton Rouge** `brla` | PERMITS daily permits · 311 `7ixm-mnvx` (`createddate`) · SLA `xw6s-bcqm` snapshot | socrata ×3 | ~5 | D4 snapshot mode prereq for licenses |
| **Washington DC** `dc` | PERMITS 2026 layer · 311 2026 layer · SLA Basic Business Licenses (non-spatial) · DEEDS CAMA sales (non-spatial→parcel join) | arcgis ×4 | ~6 | D3 year-slice prereq; uppercase coords; licenses/sales need geocoding story before H3 (G8 null-share documented) |
| **Boston** `boston` | PERMITS approved-building (660k) · 311 current-year resource · SLA Licensing Board (narrow) | ckan ×3 | ~4 | CKANClient prereq; year-resource rollover (D3); no sales |
| **Denver** `denver` | PERMITS res+comm construction · 311 ODC table | arcgis ×2 | ~4 | licenses lack issue dates (skip, revisit); sales ungeocoded (skip); numeric yyyymmdd reception dates; $0 inter-city transfers filtered |
| **Baltimore** `baltimore` | PERMITS Housing&Building 2019– · 311 current-year · SLA Liquor Licenses (narrow, WA-LCB precedent) | arcgis ×3 | ~4 | year rollover on 311; narrow liquor feed pinned as notifications-grade |
| **Montgomery Co.** `montgomery` | PERMITS point-geocoded families · SLA liquor licensees | socrata ×2 | ~2 | **MC311 excluded**: zip-only, fails G5 by construction; document exclusion in registry comment |

Feed totals: 38 new jobs → 57 program target (±2 if Denver/Baltimore third feeds pass their G5 probes).

---

## 5 · Orchestration mechanics

### 5.1 Stream protocol (unchanged from ADR 0001 / parallel-streams.md)

Claim → build (leaf only) → interlock (spine, one stream at a time, never park a torn write). Claim file is the first action; findings land in files the moment they're learned; orchestrator appends dispatch-log rows at launch and close-out.

### 5.2 Wave checklist (orchestrator, strict order)

1. Re-probe every dataset ID in §4 table for the wave's cities (≤ 72 h stale allowed).
2. `python scripts/interlock_gap.py <base>` — require projected spine-share ≤ 20% for city waves; higher ⇒ merge streams.
3. Dispatch leaves; record claims.
4. On each leaf completion: orchestrator applies that city's spine delta **serially** (enum member, aliases, registry entry, config endpoints, map entries) → `pytest -m interlock` → full suite → integrator doc/dashboard updates → commit if policy allows.
5. Close-out: yield row, metric scorecard update, M-wave trigger.

### 5.3 Drift rules

- Any dataset retired/staled between probe and implementation ⇒ swap from contingency list or descope that feed; never register a known-stale endpoint (LA/KC precedent).
- Schema drift discovered mid-build ⇒ capture row in fixtures, extend that city's `field_map`, keep parser untouched unless the term is genuinely multi-city.

### 5.4 Capacity levers

- Compression: C4+C5 can run as three-stream weeks (leaves only) if both interlock-gap projections stay ≤ 20%.
- Decompression: any G-gate failure holds its whole wave; a red invariant is finished-or-reverted, never parked.

---

## 6 · Model and alerting gates

Adding 12 cities changes feature distributions; LIMS z-scores and the quantile/GNN/DCN stack must not silently mis-calibrate.

| Gate | Rule |
|---|---|
| Warm-up state | New city ships with `alert_enabled=false`; dashboard shows "calibrating" badge |
| Calibration unlock | After ≥ 60 days of features: per-city walk-forward pinball p50 within ±10% of pooled baseline AND LIMS decile spread ≥ 0.5× pooled spread ⇒ flip `alert_enabled=true` |
| Holdout discipline | Every retrain includes new cities as H3-7 spatial-block holdouts (existing leakage protocol); no city enters training without passing G5–G8 |
| Alert budget | Post-unlock: catalyst alerts per city-day ≤ pooled p95; webhook dispatcher per-city rate limiter added in Wave R |
| Attribution sanity | TreeSHAP weight drift per feature ≤ 25% relative post-expansion, else model review before unlocking more cities |

---

## 7 · Risk register

| # | Risk | Likelihood | Impact | Mitigation | Trigger response |
|---|---|---|---|---|---|
| R1 | Feed retires/pauses mid-program (KC 9-mo precedent; LA relapse) | High | Medium | §5.2(1) re-probe; Wave-R weekly monitor from day 1 | swap contingency city; alarm < 7 d |
| R2 | Portal exits discovery/aggregator mesh (Austin did) | Medium | Low | we consume direct resource URLs, not catalogs | no action unless URL dies |
| R3 | Year-slice rollover breaks DC/Boston ingestion at New Year | Certain (if unmitigated) | Medium | D3 templates + December frozen-clock dry-run + runbook §8.2 | rollover drill fails ⇒ manual layer bump runbook |
| R4 | Snapshot mode double-counts BR businesses | Medium | Medium | id-set diff ingest; 0.1% parity gate × 3 days before close | revert to incremental-less registration (drop feed) |
| R5 | Sentinel/dirty dates poison watermarks (Philly yr-3200; NYC mixed-format text) | High | Medium | client-level filters; NYC normalization spike in Wave R; typed watermark compare | any watermark regression ⇒ freeze poll, repair, replay |
| R6 | Concurrent-spine torn write | Low (protocol proven) | High | serial holds, ≤ 2 streams, interlock gate per edit | finish-or-revert; incident logged with duration |
| R7 | Model miscalibration across 17 markets | Medium | High | §6 warm-up/calibration/unlock ladder; holdout discipline | gate blocks public alerts, product unaffected |
| R8 | Rate limits across 38 new endpoints | Medium | Medium | SOCRATA_APP_TOKEN required in staging; per-client backoff already built | 429 rate > 1% ⇒ interval_seconds tuning per feed |
| R9 | Dashboard/export bloat at 17 metros | Medium | Low | integrator applies per wave-pair; selector tested at 17 in C6 | lazy-load city presets if DOM > budget |
| R10 | Agent-stream silent failure (F2, seen 2026-08-23) | Medium | Medium | dispatch-log yield accounting; takeover trail files | yield < 0.85 ⇒ orchestration retro before next wave |

---

## 8 · Runbooks

### 8.1 Register-a-city (per stream, condensed)

1. Claim `.streams/city-<id>.md`; re-probe §4 IDs; capture ≥ 1 fixture row per feed into `tests/unit/test_producers_<city>.py`.
2. Leaf: author `src/spatial/cities/<city>.py` (METRO_BBOX, DIVISION_BBOXES, DIVISIONS, SUBMARKETS — hand-authored, the bulk of the work), producer tests incl. quirks column, G5/G6 probe script run.
3. Hand to orchestrator for serial spine: enum, aliases, REGISTRY entry (partial sets welcome; `get_dataset` errors stay readable), config endpoints, `field_map`.
4. Gates G1–G10; integrator README/dashboard row.

### 8.2 Annual year-rollover (DC, Boston; Minneapolis if ever added)

Staging: frozen-clock test advances to Jan 2 ⇒ scheduler must resolve next-year layer/resource, reset watermark baseline, emit `rollover` metric event. Manual fallback: append mapping in `DatasetSpec.extra["endpoint_by_year"]`, restart scheduler job, verify newest-row probe. Drill runs every December 15.

### 8.3 Weekly staleness probe (Wave R deliverable)

For every registered feed: fetch newest-by-watermark row (format-aware for text watermarks) + `rowsUpdatedAt`/`lastEditDate`; emit per-feed age metric; page if > 7 days. Recipe identical to `current-city-feed-gaps.md` Method section; lives in `scripts/feed_staleness_probe.py` (new leaf) wired to the existing Prometheus/webhook path.

---

## Scorecard

Updated per wave close-out in `.streams/dispatch-log.md`; program rollup maintained at the bottom of this file.

| Wave | Cities cum. | Feeds cum. | Yield | Spine share | Incidents |
|---|---|---|---|---|---|
| baseline | 5 | 19 | — | — | 1 (pre-ADR) |
| A+B (pre-program) | 5 | 21 | 1.0 | high (by design: repairs + mechanism) | 0 |
| C1 | 7 | 27 | 2/2 | ~10% projected | 0 |
| C2 | 9 | 33 | 2/2 | ~10% projected | 0 (1 gate catch: arcgis client routing) |
| C2 | | | | | |
| F | | | | | |
| C3 | | | | | |
| C4 | | | | | |
| C5 | | | | | |
| C6 | | | | | |
