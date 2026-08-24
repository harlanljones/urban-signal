# Stream log — har-29-model-calibration — 2026-08-23

## Claim

- **Stream id:** har-29-model-calibration
- **Leaf files I will create/edit:** `apps/api/src/models/calibration.py`, `apps/api/src/serving/alert_state.py`, `apps/api/src/serving/dispatcher.py`, `apps/api/src/features/lims_calculator.py`, `apps/api/src/models/explainability.py`, focused tests under `apps/api/tests/unit/test_calibration.py`, `apps/api/tests/unit/test_dispatcher.py`, and this stream log; model-calibration documentation only under `docs/` if needed.
- **Spine files I expect to need:** none; I will not edit city registry or dashboard files.

## Intent

Implement the independent HJ-29 model slice end-to-end where the current architecture supports it: 60-day city warmup with alerts disabled, per-city pooled-baseline/pinball/LIMS unlock gates, TreeSHAP attribution drift review at a 25% threshold, and per-city alert budgets/rate limiting, with runnable focused evidence.

## Decisions

- 2026-08-23 — Ownership is limited to model calibration/reporting, alert state, attribution drift, dispatcher rate limiting, related tests/docs, and `.streams/har-29*.md`; registry/dashboard files are explicitly excluded.
- 2026-08-23 — Calibration uses inclusive feature-day coverage: the 60th observed calendar day satisfies warmup; pinball p50 must be ≤110% pooled baseline; LIMS decile spread must be ≥50% pooled spread; TreeSHAP drift strictly above 25% blocks unlock.
- 2026-08-23 — Dispatcher budget is an injectable, thread-safe in-memory per-city/day limiter (default 100 alerts/day). Persistence/config schema is not present in the current serving architecture and remains an integration decision for the parent stream.

## Current step

Implemented additive calibration, alert-state, attribution-drift, and dispatcher-budget primitives; focused tests exposed and corrected the inclusive 60-day boundary.

## Next step

Focused tests, Ruff, diff check, and graph coverage completed. Parent integration decision: wire `CityAlertState` into the feature/alert worker only once a trustworthy city-id propagation seam is selected; this stream does not edit registry/dashboard/spine files.
