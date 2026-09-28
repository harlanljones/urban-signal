# Signal Roadmap: from registered feeds to proven forecasts

> **Status:** Draft for review · **Created:** 2026-09-27 · **Reviewed:** 2026-09-28 against `11b612f`
> **Baseline:** 156 registered metros (`REGISTRY` and `facts.json`; README and
> `PRODUCT.md` still say 101)
> **Prioritization lens (proposed):** Evidence before features. The expansion
> waves (`expansion-roadmap*.md`) made ingestion broad; this roadmap makes the
> forecasting claim true, measurable, and explainable, then extends it.
>
> **Linear tracking:** parent not yet created. One sub-issue per phase below.
>
> **[TBD: …]** marks text lost when the draft was pasted; only the author can
> fill it in.

---

## 0 · Why this roadmap exists

The README says Urban Signal predicts appreciation (Δ ln P) 6 to 18 months ahead
of public market listings. `PRODUCT.md` requires every product and model claim
to "remain traceable to repository evidence." As of `11b612f` the repo cannot yet
support that claim:

| Finding | Evidence |
|---|---|
| No code builds forward price labels. `target_6m`, `target_12m`, and `target_18m` appear only in the trainer and its test. | `git grep target_6m` → `apps/api/src/models/trainer.py`, `apps/api/tests/unit/test_retraining.py` |
| When targets are absent, the trainer uses a feature as the target (`df[features[0]] * 0.01` for 6m, `features[0]` itself for 12m and 18m). No label-less run finishes: with ≥ 18 months of history the walk-forward CV raises `KeyError: 'target_6m'`, and with less the 18m head fails because its BCE target is outside [0, 1]. | `trainer.py:573–590`; the CV reads targets unguarded at `:414`. Reproduced 2026-09-28 on the synthetic frame with its target columns dropped. |
| Retraining without `--duckdb-path` trains on `prepare_synthetic_training_data()` (12 synthetic NYC cells). | `retraining_job.py`, `trainer.py` |
| Nothing writes the `feature_store_h3` table that `--duckdb-path` reads, and no job builds a feature history. The live aggregation worker publishes current-date features to Kafka and skips backfill records. | `features/pipeline.py:148` creates the table; no code inserts into it. `consumers/feature_aggregation_worker.py:216` |
| What the API and the map serve is not a trained model. At boot the engine fits a LightGBM to synthetic rows with a hand-written target and serves untrained ST-GNN and DCN-v2 graphs; nothing loads the retraining job's artifacts. Snapshot cells are scored from hand-authored submarket values (`base_lims`, `capex`, …), not from `feature_store_h3`. | `serving/engine.py:50`, `:110–134`; `serving/router.py:266`, `:333–338`, called by `export/snapshot_builder.py`; `base_lims=` appears in 155 files under `spatial/cities/` |
| Catalyst alerts fill their forecast fields with LIMS times a constant: 6m = LIMS × 0.002, 12m = LIMS × 0.0035, 18m = min(LIMS / 100 × 1.1, 0.99). | `consumers/feature_aggregation_worker.py:193–195` |
| The ST-GNN is trained without neighbours or history: identity adjacency, a scaled copy of the current row as its sequence, and a one-node ONNX export. `H3HexGraphBuilder` exists, but nothing uses it. | `trainer.py:296–304`, `:438`, `:606`; `spatial/graph_builder.py` |
| The walk-forward split has no embargo. Training rows run up to the test cutoff, so once labels are real their h-month windows overlap the test period. | `models/validation.py:58–59` |
| Alert calibration fails open. The dispatcher checks it only for 20 hard-coded cities, so 136 of 156 metros dispatch alerts uncalibrated, and nothing outside tests builds a `CalibrationReport`. | `serving/dispatcher.py:19–48`; `calibration_report()` in `models/calibration.py` has no callers |
| No backtest report, baseline comparison, or lead-time measurement exists in `docs/`. | `docs/`, `docs/research/` |

What is in place, and is reused below:

- `SpatialTemporalHoldoutValidator`: walk-forward split with H3-7 cluster holdouts (`models/validation.py`). It needs an embargo before it can score real labels (see above).
- `CalibrationReport` / `CityAlertState`: per-city warm-up, pinball, and LIMS-decile gates (`models/calibration.py`). The types exist; no job computes a report from data yet.
- The Redfin/Zillow reconciled per-hex monthly series (US-440, `features/market_reconciliation.py`), currently wired only into the Bay Area export. That export keeps only the latest print per ZCTA (`latest_per_zcta`), so no price history is stored anywhere yet.
- Price-bearing deeds in some metros (51 of 156 register a deeds feed; see README §1 feed table). The two named in this draft, NYC ACRIS (`bnx9-e6tj`) and Cook County sales (`wvhk-k5uv`), carry prices but no coordinates or parcel join, so the enrichment worker drops them (`spatial_enrichment_worker.py:72–76`). `raw_deeds` also stores no parcel ID, which repeat sales need.
- `SpatialFeaturePipeline.compute_h3_cell_features(as_of_date=…)`, which can compute a hex's features at a past date and is the starting point for a feature history.
- `H3HexGraphBuilder` (`spatial/graph_builder.py`) for real GNN adjacency.
- TreeSHAP attribution (`CatalystExplainer`), today fitted to the boot-time synthetic LightGBM, and the snapshot/export path.

---

## 1 · Program targets and strict metrics

| Metric | Baseline (2026-09-27) | Target | Verified by |
|---|---|---|---|
| Metros with real forward labels (≥ 1 horizon) | 0 | Every metro with a Zillow/Redfin series or price-bearing deeds | Label coverage table (P0) |
| Models trained on real labels | 0 of 3 horizons | 3 of 3, and serving loads them | The retraining report records its label source; the synthetic fallback is disabled outside tests; `engine.py` loads the artifacts the report names |
| Map and alert scores computed from ingested data | 0 metros (submarket baselines) | Every metro with a feature history | Snapshot test: no score reads `base_lims`; alert test: forecast fields come from the models (P0) |
| Published backtest vs naive baselines | none | One report per horizon and metro tier | `docs/research/lead-time-evidence.md` (P1) |
| Measured LIMS lead time | unmeasured | Reported with a CI; claim wording matches the measurement | Event-study plot + table (P1) |
| Scored hexes whose score cites source records | 0 | 100% of scored hexes on the dashboard | Inspector drawer E2E test (P2) |
| Alert confidence levels | binary per-city enable, checked for 20 of 156 metros | Per-alert act / review / escalate for every metro | Dispatcher payload contract test (P3) |

**Claim rule (new):** until P1 publishes, README and product copy that states a
lead time ("6 to 18 months ahead") is reworded as a design target, not a
measured result. P1 decides the final wording from the measured number.
The rule covers `README.md` §1, `promo/urban-signal-promo/` (`BRIEF.md`,
`index.tsx`), and `urban_signal_prospectus_k8s_kafka.md`. The prospectus also
states results that no report backs: "> 82%" directional delta accuracy, an
out-of-fold directional R² > 0.65, and "backtested 12-month appreciation
accuracy > 80%" (lines 26 and 181). Those numbers come out now rather than
waiting for P1, since nothing in the repo backs them.

---

## 2 · Phases

**Dependency order:** P0 → P1 → {P3, P5}; P2 and P4 can start in parallel; P6 needs P0.

P2 and P4 can start now, but neither can finish alone. P2's record trail and
coverage gaps depend on nothing, but its SHAP shares and gate S1 need scores
computed from ingested data, which P0 delivers. P4's probe and extractor can
begin now, but N3 needs the P1 harness. P3 also needs P0's model outputs in the
alert payload, since today's forecast fields are LIMS times a constant.

### P0 · Real forward labels (prerequisite)

**Goal:** every training row carries a real Δ ln P at 6, 12, and 18 months,
with its source recorded, and what the API, map, and alerts serve comes from
models trained on those rows.

**Scope:**

0. Build a point-in-time feature history: run `compute_h3_cell_features` at
   each month-end per metro and write `feature_store_h3`. Count each record
   from the date it became public, not its event date (Milwaukee permits
   publish about 2.3 months late, Cleveland's about 10 days; README §1).
   Feeds that publish only a rolling window (Dayton's 90-day 311; Tulsa's,
   El Paso's and Dallas's ~30-day 311; San José's last-30-days permits) have
   no history to rebuild, so those metros accrue it from now on and L1 says so.
1. Build a per-hex monthly price index per metro:
   - Primary: the US-440 reconciled Zillow ZHVI / Redfin series via the
     ZIP-to-H3 area-weighted join, extended to every metro Zillow covers.
     Keep the full monthly history; the Bay Area export keeps only the
     latest print. §4 asks whether labels should use the blend or ZHVI alone.
   - Secondary: a repeat-sales index from price-bearing deeds where volume
     supports it (report the minimum-sales threshold used). This needs a
     parcel ID in `raw_deeds` and a parcel join for coordinate-less feeds
     such as ACRIS and Cook County, as DC's `parcel_join` already does.
2. Compute `target_{6,12,18}m = ln P(t+h) − ln P(t)` at each `as_of_date`. The
   18-month horizon is binary (> 15% outperformance vs metro), per README §3.
   Define outperformance exactly, for example as hex Δ ln P minus metro
   Δ ln P above ln 1.15; the synthetic generator uses absolute appreciation
   above 0.15 instead.
3. Write labels into `feature_store_h3` with a `label_source` column
   (`zillow_redfin` or `repeat_sales`) and the date each label became
   knowable (`as_of_date + h` plus the index's publication lag).
4. In `trainer.py`: remove the `features[0] * 0.01` fallback (raise instead),
   and keep synthetic data test-only (`prepare_synthetic_training_data` behind
   an explicit flag that only tests set). Train the ST-GNN on real neighbours
   (`H3HexGraphBuilder`) and real monthly history. That fixes its training
   inputs, not its architecture (§3).
5. Serve what was trained. The engine loads the retraining job's artifacts
   instead of fitting a synthetic LightGBM and exporting untrained graphs;
   the snapshot scores hexes from `feature_store_h3` instead of submarket
   `base_lims`; and the alert worker fills its forecast fields from the
   models. §4 asks how to roll the map change out.

**Acceptance gates:**

- **L1:** a label coverage table per metro: hexes labelled, months covered, and source.
- **L2:** no label uses information after `as_of_date + h` (a leakage test checks the label windows).
- **L3:** `run_retraining_job()` without `--duckdb-path` fails loudly instead of training on synthetic data.
- **L4:** metros without any price series are listed explicitly, not dropped
  (the honest-coverage rule in `PRODUCT.md`).
- **L5:** the snapshot and alert tests in §1 pass for every metro with a feature history.

**Touches spine:** `config.py` (label settings), and possibly `scheduler.py`
(a monthly price-index build). Hold a spine lease. The pipeline, trainer,
engine, snapshot, and alert-worker changes are all leaf files.

### P1 · Lead-time evidence

**Goal:** show, per horizon and metro tier, whether the signal beats naive
forecasts and by how many months LIMS leads prices.

**Scope:**

1. Baselines: (a) a random walk (Δ = 0), (b) the metro-wide change applied to
   every hex, (c) momentum (the trailing 6–12-month change in the same hex),
   (d) the lagged sales-comps median. The model must beat (c): momentum is the
   honest bar for "leading."
2. Backtest: reuse `SpatialTemporalHoldoutValidator`. Report pinball loss (6m),
   Huber loss (12m), and AUC/Brier (18m), each with its fold-level mean and spread.
   First add an embargo of h months plus the label's publication lag between
   train and test, and group the spatial holdout by the label's source ZIP:
   area-weighted ZIP labels are shared across H3-7 parents, so an H3-7
   holdout alone leaks.
3. Event study: for hexes crossing LIMS ≥ `lims_threshold`, trace the excess
   Δ ln P at lags −12 … +24 months against matched non-crossing hexes (same
   metro, similar pre-trend). The lag where the excess becomes significant is
   the measured lead time. ZHVI is smoothed and seasonally adjusted, which
   delays turning points and flatters any leading indicator, so check the
   lead against a transaction index too (FHFA purchase-only HPI, already in
   `SERIES_REGISTRY`, or P0's repeat sales).
4. Ablation: drop one signal family at a time (permits, **[TBD: the rest of
   the family list; the paste kept only the final word, "density"]**) to show
   which ones actually lead.
5. Publish `docs/research/lead-time-evidence.md` with the plots and tables, and
   update the README claim to match.

**Acceptance gates:**

- **E1:** every metric is reported side by side with its baselines; no model number stands alone.
- **E2:** a pre-trend check passes (no significant excess before the crossing), or the report says so.
- **E3:** results are split by metro tier: 4-feed and partial; metros without labels are listed as excluded.
  On 2026-09-28, counting permits, 311, licenses, and deeds, 16 metros have
  all four, 86 have two or three, 53 have one, and one has none.
- **E4:** negative or null results are published, not dropped.

Leaf work (a new module, e.g. `models/evaluation.py`, plus a docs file).

### P2 · Source trail per hexagon

**Goal:** any score on the map can answer "how do you know?"

**Scope:**

1. For each scored hex, persist the top-N contributing source records (permit
   numbers, 311 ticket IDs, license IDs), their source dataset, and their
   open-data platform URLs. This builds on the geocoder provenance flag that
   already rides through `spatial_enrichment_worker.py`. The flag
   (`coord_source`) is set on the in-flight record but dropped at the DuckDB
   sink, and the raw tables keep record IDs without a city, dataset, or
   `coord_source` column, so this step starts with a schema change in
   `features/pipeline.py`.
2. Inspector drawer: show the SHAP share per signal family and the top records
   behind each family, each linking to the city's open-data row.
3. Show coverage gaps explicitly ("no 311 feed for this metro"), so a missing
   feed is never read as "zero complaints."

**Pattern reference:** Chronon's `chronon-provenance` (citations plus explicit
unknowns). Borrow the pattern; don't take a cross-repo dependency.

**Acceptance gates:**

- **S1:** 100% of hexes that show a score have ≥ 1 cited record per contributing family, or an explicit "no feed" marker.
- **S2:** every link resolves (a sampled link check in CI, **[TBD: the rest of this line was lost]**).

The weekly `feed-staleness` workflow is a better home for the S2 check than the
deploy gate, so a portal outage can't block a deploy.

### P3 · Alert confidence levels

**Goal:** replace the single LIMS ≥ 85 cutoff with per-alert confidence levels.

Today `CalibrationReport.alert_enabled` turns alerts on or off for a whole city.
Extend this to each alert:

| Level | Condition (initial values) | Dispatch |
|---|---|---|
| act | City calibrated, 6m quantile interval excludes zero, and **[TBD: second condition; the paste kept only "…ds for this metro tier"]** | webhook |
| review | Score ≥ threshold, but the interval straddles zero or attribution drift > 0.25 | digest only |
| escalate | Score ≥ threshold, driven by one family > **[TBD: share]** of the attribution (a likely single-source spike) | human check |

In practice the dispatcher consults `alert_enabled` for only 20 hard-coded
cities and no job computes a report, so P3 starts by failing closed for every
metro and adding the job that builds each `CalibrationReport` from the P1
backtest. The act and review rows also need the 6m quantile interval in the
alert payload, which today carries only point values.

**Acceptance gates:**

- **A1:** the dispatcher payload carries the level, its reason, and **[TBD: third field]** (contract test).
- **A2:** the per-level hit rate is back-tested using the P1 harness; `act` must outperform `review`.

**Touches spine:** `config.py` (level thresholds).

### P4 · Entitlement pipeline

**Goal:** capture rezonings, variances, and site-plan approvals. These come
6–24 months before building permits and are the largest untapped source of
lead time.

**Scope:**

1. Probe: for the 10 largest registered metros, find where planning-commission
   and BZA agendas and minutes are published (Legistar, Granicus, PrimeGov,
   static PDFs). Record this in `docs/research/entitlement-sources.md`, using
   the same tiering as the Wave-3 re-probe.
2. Extract with an LLM into a typed `EntitlementEvent` (address, application
   type, units, decision, date), then geocode via ADR 0004.
3. Add a new Kafka topic `raw.municipal.entitlements` and a per-hex
   entitlement-activity feature.
4. Measure the gain with the P1 harness (the P1 ablation run with and without
   the new feature).

**Acceptance gates:**

- **N1:** ≥ 90% field accuracy on a 200-item hand-labelled set.
- **N2:** every extracted event keeps the source PDF URL and page (feeds P2).
- **N3:** the feature is added to LIMS only if P1 shows a measurable gain; otherwise it ships as context.

**Needs an ADR:** LLM extraction on the ingestion path (model pinning and
replay determinism).

**Touches spine:** `config.py` (the topic setting; every topic lives there) and
`scheduler.py` (the producer job).

### P5 · What-if scenarios

**Goal:** planners can place a hypothetical catalyst (a transit station or a
large rezoning) and see the predicted spillover.

**Scope:** inject synthetic events into one hex's features and run the 12m
ST-GNN forward. Show the spread across neighbouring hexes with its uncertainty,
and label the output "model scenario," never a forecast.

**Acceptance gates:**

- **W1:** the scenario API is read-only and separate from the forecast path.
- **W2:** each scenario is back-tested against ≥ 3 real historical catalysts
  (e.g. a past rail station opening) before launch.

Depends on P0 (a real-label GNN) and P1 (a GNN that beats its baselines).
It also needs P0's ST-GNN training fix: with identity adjacency the model has
no path for spillover between hexes, so a scenario would change only the hex
it was placed in.

### P6 · Displacement risk lens

**Goal:** read the same signals from the tenant side, for community
organisations and city agencies.

**Constraint:** the asymmetry rule (see `evictions_producer.py`): a
single-metro feed must not drive cross-city scores. NYC evictions stay as
context. Build the lens from inputs with national coverage: ACS rent burden
and tenure (`docs/research/acs-baseline-evaluation.md`), HMDA
(`spatial/hmda_metrics.py`), and P0's rent series (ZORI).

Before building on those inputs:

- HMDA is a leaf-only feasibility helper, not an ingested feed. Registering it
  needs a new `FeedType` and producer (`hmda_metrics.py` docstring), which
  touches `city_registry.py` on the spine.
- ACS and HMDA arrive by block group or tract, and they roll up honestly only
  to res 7 (`DEFAULT_ROLLUP_RESOLUTION = 7` in `hmda_metrics.py`), so the lens
  is a res-7 layer. Live ACS rows need `CENSUS_API_KEY`.
- `cost_burden_30pct_share` in `spatial/acs_baseline.py` divides `B25070_010E`
  by the total. That cell is the ≥ 50% bucket, so the feature measures severe
  burden, not ≥ 30%. Fix or rename it before D1.

**Scope:** a vulnerability index (rent burden × renter share) crossed with LIMS
momentum gives a displacement-pressure score per hex, shown as a separate layer.

**Acceptance gates:**

- **D1:** the method doc names every input, its coverage, and its known biases.
- **D2:** the layer is validated against NYC evictions as an out-of-sample check, never as a training input.

---

## 3 · Out of scope

- New metro registrations (these stay in the expansion roadmap waves).
- Model architecture changes before P1: prove the current three horizons first.
- Parcel-level valuation (the hex is the product's unit).

---

## 4 · Open decisions

1. **Label source for P0.** The draft makes the US-440 blend primary (Redfin
   0.6 / Zillow 0.4 for sale prices). When one source is missing, the blend
   falls back to the other, which shifts that ZIP's level in the month the
   source drops out, and the shift reads as a real Δ ln P. Redfin's ZIP
   tracker was last modified 2026-06-02 (its `Last-Modified` header, checked
   2026-09-28), so that switch is already under way. Recommendation: label
   from ZHVI alone and keep Redfin as a cross-check.
2. **Rolling out P0 step 5 on the map.** Scoring hexes from `feature_store_h3`
   instead of submarket values changes every metro's map. Recommendation: switch
   per metro as each gets a feature history, behind a flag, and keep a
   horizon's forecast fields hidden or marked uncalibrated until it passes
   P1's E1.
3. **The five [TBD] lines:** the P1 ablation family list, the end of P2's S2,
   the second `act` condition in P3, the `escalate` share in P3, and the third
   field in P3's A1.
