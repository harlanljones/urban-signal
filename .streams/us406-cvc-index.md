# Stream log — us406-cvc-index — 2026-08-30

## Claim

- **Stream id:** us406-cvc-index
- **Leaf files I will create/edit:**
  - `apps/api/src/features/cvc_index.py` (create)
  - `apps/api/tests/unit/test_cvc_index.py` (create)
- **Spine files I expect to need:** NONE — leaf-only phase
  - Confirmed: no edits to config.py, city_registry.py, series_registry.py, scheduler.py, or any spine-manifest file

## Intent

Build the Commercial Vitality Churn (CVC) composite index computation module
for US-406. The module cross-corroborates three independent per-H3
business-formation/destruction signals — SLA license churn (90d), POI net
churn (90d, `poi_opened`−`poi_closed`), and ZBP YoY establishment+employment
growth (ZIP→H3 via `dynamic_spatial_fallback`) — plus SBA approvals and FMCSA
carrier adds as corroboration weights, to emit a `cvc_score`,
`cvc_confidence` (1–3 = number of agreeing sources), and `sources` list. Pure
feature-store computation, no new event schema, no spine edits. Unit-tested
against fixture data covering all-agree / partial-agree / single-source /
missing-input / suppression-flag / zero-value scenarios.

## Decisions

- 2026-08-30 — Claimed stream. Leaf-only: `src/features/cvc_index.py` + unit test only.
- 2026-08-30 — ZBP growth: pure-math helper `compute_zbp_growth` honors suppression
  flags (D/S/N/X/V/Z) → withheld cells propagate as `None`, counted, never zeroed;
  aligns with `src/spatial/zbp_signal.py` flag set.
- 2026-08-30 — SBA corroboration accepts a plain count (full weight) or a per-program
  mapping (`{"504": n, "7a": m}` / `{"fixed_asset": n, "working_capital": m}`);
  504 (fixed-asset) at 1.0, 7(a) working capital at 0.5.
- 2026-08-30 — Confidence = number of non-zero churn sources agreeing with consensus
  direction (0 when no churn source; 1 when all neutral). SLA+POI agree bonus only
  fires when both are present, non-zero, same sign.
- 2026-08-30 — Added `normalize_sla_license_namespace` to strip `tabc:`/`wa_li:`/etc
  prefixes before cross-registry churn aggregation.
- 2026-08-30 — Default baselines are reference (res-8-ish) distributions, overridable
  via `weights=`/`baselines=` kwargs.

## Current step

Done — both leaf files written, tests pass, ruff clean.

## Next step

Report back; leave work uncommitted (per stream discipline).
