# Stream log — us405-composite-indices — 2026-08-30

## Claim

- **Stream id:** us405-composite-indices
- **Leaf files I will create/edit:**
  - `apps/api/src/features/index_math.py` (create — shared composite engine)
  - `apps/api/src/features/sbcai_index.py` (create)
  - `apps/api/src/features/aisi_index.py` (create)
  - `apps/api/src/features/wcs_index.py` (create)
  - `apps/api/tests/unit/test_index_math.py` (create)
  - `apps/api/tests/unit/test_sbcai_index.py` (create)
  - `apps/api/tests/unit/test_aisi_index.py` (create)
  - `apps/api/tests/unit/test_wcs_index.py` (create)
- **Spine files I expect to need:** NONE — leaf-only phase
  - Confirmed: `src/features/*` is NOT in `docs/agents/spine-manifest.txt`; no
    edits to config.py, city_registry.py, series_registry.py, dashboard.py, or
    any spine file. Aligns with the US-406 CVC precedent (leaf-only module + test).

## Intent

Build the three universal derived composite indices from US-405 / the
2026-08-30 research evidence §0 (Stream A A8/A9/A10): **SBCAI** (Small
Business Credit Access), **AISI** (Anchor Institution Stability), **WCS**
(Workforce Commute-Shed Score). Pure feature-store compositing math over
already-registered national inputs — no new event schemas, no spine changes —
emitting `<key>_score`, `<key>_confidence`, ``coverage``, `sources`,
`components`, and `caveats` per H3 cell. Wiring into the feature-aggregation
worker and per-city ``macro_series`` rows is intentionally deferred: the
dependent legs (US-361 ACS, US-378 SbaLoanEvent, US-379 BankBranchEvent,
US-374 NPPES, HMDA/ECHO/LODES live) are not yet landed, so the compositing
module honors the "emit the index minus missing terms with a confidence field"
path.

## Decisions

- 2026-08-30 — Claimed stream, leaf-only. Added a shared engine
  `index_math.compute_weighted_index` so the three indices don't triple a
  z-sum renormalization; each index module declares weights/baselines/
  orientation/caveats and calls the engine.
- 2026-08-30 — Orientation is explicit because a composite must be monotone in
  the target direction: `complement` (1 - x) for credit-denial / anchor-churn /
  crime-rate; `reciprocal` (1 / x) for jobs-housing-imbalance / commute-time.
  A non-positive reciprocal input is treated as missing (never zeroed as +inf).
- 2026-08-30 — Baselines are on the **oriented** (post-transform) scale, per the
  CVC precedent; callers may override `weights=`/`baselines=`.
- 2026-08-30 — Confidence = count of present component terms (coverage), not a
  churn-style direction vote: these indices are non-negative attribute blends
  where "present vs missing" is the meaningful confidence signal. Matches the
  ticket's "emit index minus missing terms with a confidence field."
- 2026-08-30 — SBCAI quintile-bands via `band_cutpoints` (defaults to no band;
  only SBCAI in the evidence doc is described as quintile-banded).
- 2026-08-30 — Caveats are conditional on the presence of the relevant term
  (e.g. HMDA-denial caveat only fires when the denial term is present), so a
  missing term never claims a caveat for a term that isn't there.

## Current step

Done — four leaf modules + four unit-test modules written; 43 tests green
(existing test_cvc_index.py included); ruff clean. `pytest -m interlock` green;
dashboard↔product cross-ref green. Work left uncommitted (per stream discipline).

## Next step

Wire the phase-2/3 integration once the dependency feeds land (US-361, US-378,
US-379, US-374, HMDA/ECHO/LODES live): extend the feature-aggregation worker to
compute SBCAI/AISI/WCS per H3, store under explicit feature keys, and add the
per-city `macro_series` rows. Then run full CI/CD preflight.
