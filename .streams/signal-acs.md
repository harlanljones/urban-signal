# Stream log — signal-acs — 2026-08-26

## Claim

- **Stream id:** `signal-acs`
- **Leaf files I will create/edit:** `docs/research/acs-baseline-evaluation.md`, `apps/api/src/spatial/acs_baseline.py` (only if warranted, with test `apps/api/tests/unit/test_acs_baseline.py`)
- **Spine files I expect to need:** none (read-only evaluation + self-contained leaf module)

## Intent

Evaluate the Census American Community Survey (ACS) as a source of *neighborhood
baseline features* (demographics, income, housing, commute) for Urban Signal — the
soft, structural context layer behind the hardcoded submarket baselines
(`base_lims`, `capex`, `permit_vel`, `shift_ratio`, `sla`). Produce an evaluation
with evidence (source, geography, cadence, candidate features), a proposed baseline
feature set, risks (latency, margin-of-error at small geographies), and a verdict
(adopt/reject/defer). Optionally ship a self-contained leaf module that maps
block-group ACS estimates to H3 cells with correct MOE propagation. No spine edits.

## Decisions

- 2026-08-26 — ACS **data** API now requires a free Census Data API key ("Missing Key"
  response on a live `acs5` query). Metadata endpoints remain keyless. Flagged as a
  config/secret dependency for the adopting stream.
- 2026-08-26 — 2023 Census Gazetteer **dropped block-group centroids** (only tracts,
  places, ZCTA, counties remain, verified by listing + downloading `2023_Gaz_tracts_*
  .zip` which has `INTPTLAT`/`INTPTLONG`). BG geolocation must reuse the LODES
  crosswalk block internal points (12-char prefix of `tabblk2020`) or a TIGER BG
  shapefile — not a new source.
- 2026-08-26 — Every ACS estimate ships a 90% MOE (`*_001M`); the central risk is MOE at
  block-group scale. Solved by H3 res 7–9 rollup + `dynamic_spatial_fallback`, with MOE
  propagated by the Census quadrature (sum) / ratio formulas; medians aggregated as a
  weighted mean (documented approximation).
- 2026-08-26 — ACS 5-year lags ~12 months (2023 5-year released Dec 2024), far fresher
  than LODES' ~28 months, and is non-synthetic (survey estimates), unlike LODES.
- 2026-08-26 — **Verdict: ADOPT (trailing context/baseline layer)**, conditional on a
  free API key + H3 rollup. Best-fit source to replace/calibrate hardcoded `SubmarketMeta`
  baselines (`base_lims`, `capex`, `permit_vel`, `shift_ratio`, `sla`). Not a `FeedType`/
  LIMS term. Wrote `acs_baseline.py` (catalog + MOE math + BG→H3 aggregation) and
  `test_acs_baseline.py` (9 tests, all pass via `uv run pytest`). No spine edits.

## Current step

Phase 2 complete. Leaf deliverables written and tested. Awaiting commit (blocked by env
policy) — see report.

## Next step

Run the commits below on `feat/acs`. If adopted later, the adopting stream adds the API
key (config.py secret) and wires block-group→H3 resolution into `SubmarketMeta` baselines
(spine work, out of this leaf's scope).
