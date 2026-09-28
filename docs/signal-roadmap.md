# Signal Roadmap: from registered feeds to proven forecasts

> **Status:** Draft for review · **Created:** 2026-09-27 · **Baseline:** 101 registered metros
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
| When targets are absent, the trainer uses a feature as the target (`df[features[0]] * 0.01`). | `trainer.py`, `run_retraining_pipeline` |
| Retraining without `--duckdb-path` trains on `prepare_synthetic_training_data()` (12 synthetic NYC cells). | `retraining_job.py`, `trainer.py` |
| No backtest report, baseline comparison, or lead-time measurement exists in `docs/`. | `docs/`, `docs/research/` |

What is in place, and is reused below:

- `SpatialTemporalHoldoutValidator`: walk-forward split with H3-7 cluster holdouts (`models/validation.py`).
- `CalibrationReport` / `CityAlertState`: per-city warm-up, pinball, and LIMS-decile gates (`models/calibration.py`).
- The Redfin/Zillow reconciled per-hex monthly series (US-440, `features/market_reconciliation.py`), currently wired only into the Bay Area export.
- Price-bearing deeds in some metros (NYC ACRIS, Cook County, and others; see README §1 feed table).
- TreeSHAP attribution (`CatalystExplainer`) and the snapshot/export path.

---

## 1 · Program targets and strict metrics

| Metric | Baseline (2026-09-27) | Target | Verified by |
|---|---|---|---|
| Metros with real forward labels (≥ 1 horizon) | 0 | Every metro with a Zillow/Redfin series or price-bearing deeds | Label coverage table (P0) |
| Models trained on real labels | 0 of 3 horizons | 3 of 3 | The retraining report records its label source; the synthetic fallback is disabled outside tests |
| Published backtest vs naive baselines | none | One report per horizon and metro tier | `docs/research/lead-time-evidence.md` (P1) |
| Measured LIMS lead time | unmeasured | Reported with a CI; claim wording matches the measurement | Event-study plot + table (P1) |
| Scored hexes whose score cites source records | 0 | 100% of scored hexes on the dashboard | Inspector drawer E2E test (P2) |
| Alert confidence levels | binary per-city enable | Per-alert act / review / escalate | Dispatcher payload contract test (P3) |

**Claim rule (new):** until P1 publishes, README and product copy that states a
lead time ("6 to 18 months ahead") is reworded as a design target, not a
measured result. P1 decides the final wording from the measured number.

---

## 2 · Phases

**Dependency order:** P0 → P1 → {P3, P5}; P2 and P4 can start in parallel; P6 needs P0.

### P0 · Real forward labels (prerequisite)

**Goal:** every training row carries a real Δ ln P at 6, 12, and 18 months,
with its source recorded.

**Scope:**

1. Build a per-hex monthly price index per metro:
   - Primary: the US-440 reconciled Zillow ZHVI / Redfin series via the
     ZIP-to-H3 area-weighted join, extended to every metro Zillow covers.
   - Secondary: a repeat-sales index from price-bearing deeds where volume
     supports it (report the minimum-sales threshold used).
2. Compute `target_{6,12,18}m = ln P(t+h) − ln P(t)` at each `as_of_date`. The
   18-month horizon is binary (> 15% outperformance vs metro), per README §3.
3. Write labels into `feature_store_h3` with a `label_source` column
   (`zillow_redfin` or `repeat_sales`).
4. In `trainer.py`: remove the `features[0] * 0.01` fallback (raise instead),
   and keep synthetic data test-only (`prepare_synthetic_training_data` behind
   an explicit flag that only tests set).

**Acceptance gates:**

- **L1:** a label coverage table per metro: hexes labelled, months covered, and source.
- **L2:** no label uses information after `as_of_date + h` (a leakage test checks the label windows).
- **L3:** `run_retraining_job()` without `--duckdb-path` fails loudly instead of training on synthetic data.
- **L4:** metros without any price series are listed explicitly, not dropped
  (the honest-coverage rule in `PRODUCT.md`).

**Touches spine:** `config.py` (label settings), and possibly `scheduler.py`
(a monthly price-index build). Hold a spine lease.

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
3. Event study: for hexes crossing LIMS ≥ `lims_threshold`, trace the excess
   Δ ln P at lags −12 … +24 months against matched non-crossing hexes (same
   metro, similar pre-trend). The lag where the excess becomes significant is
   the measured lead time.
4. Ablation: drop one signal family at a time (permits, **[TBD: the rest of
   the family list; the paste kept only the final word, "density"]**) to show
   which ones actually lead.
5. Publish `docs/research/lead-time-evidence.md` with the plots and tables, and
   update the README claim to match.

**Acceptance gates:**

- **E1:** every metric is reported side by side with its baselines; no model number stands alone.
- **E2:** a pre-trend check passes (no significant excess before the crossing), or the report says so.
- **E3:** results are split by metro tier: 4-feed and partial; metros without labels are listed as excluded.
- **E4:** negative or null results are published, not dropped.

Leaf work (a new module, e.g. `models/evaluation.py`, plus a docs file).

### P2 · Source trail per hexagon

**Goal:** any score on the map can answer "how do you know?"

**Scope:**

1. For each scored hex, persist the top-N contributing source records (permit
   numbers, 311 ticket IDs, license IDs), their source dataset, and their
   open-data platform URLs. This builds on the geocoder provenance flag that
   already rides through `spatial_enrichment_worker.py`.
2. Inspector drawer: show the SHAP share per signal family and the top records
   behind each family, each linking to the city's open-data row.
3. Show coverage gaps explicitly ("no 311 feed for this metro"), so a missing
   feed is never read as "zero complaints."

**Pattern reference:** Chronon's `chronon-provenance` (citations plus explicit
unknowns). Borrow the pattern; don't take a cross-repo dependency.

**Acceptance gates:**

- **S1:** 100% of hexes that show a score have ≥ 1 cited record per contributing family, or an explicit "no feed" marker.
- **S2:** every link resolves (a sampled link check in CI, **[TBD: the rest of this line was lost]**).

### P3 · Alert confidence levels

**Goal:** replace the single LIMS ≥ 85 cutoff with per-alert confidence levels.

Today `CalibrationReport.alert_enabled` turns alerts on or off for a whole city.
Extend this to each alert:

| Level | Condition (initial values) | Dispatch |
|---|---|---|
| act | City calibrated, 6m quantile interval excludes zero, and **[TBD: second condition; the paste kept only "…ds for this metro tier"]** | webhook |
| review | Score ≥ threshold, but the interval straddles zero or attribution drift > 0.25 | digest only |
| escalate | Score ≥ threshold, driven by one family > **[TBD: share]** of the attribution (a likely single-source spike) | human check |

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

### P6 · Displacement risk lens

**Goal:** read the same signals from the tenant side, for community
organisations and city agencies.

**Constraint:** the asymmetry rule (see `evictions_producer.py`): a
single-metro feed must not drive cross-city scores. NYC evictions stay as
context. Build the lens from inputs with national coverage: ACS rent burden
and tenure (`docs/research/acs-baseline-evaluation.md`), HMDA
(`spatial/hmda_metrics.py`), and P0's rent series (ZORI).

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
