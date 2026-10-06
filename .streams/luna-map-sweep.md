# Stream log — luna-map-sweep — 2026-10-06

## Claim

- **Stream id:** luna-map-sweep
- **Leaf files I created/edited:** `apps/api/src/serving/dashboard.py`, `apps/dashboard/tests/national-overlay.test.js`, `.streams/luna-map-sweep.md`
- **Spine files:** none

## Intent

Fix the confirmed national overlay bug where null percentile values are coerced to numeric zero and let an empty-percentile H3 row through. Add a regression test against the actual embedded helper, preserve legitimate zero percentiles, run focused and dashboard tests, and leave export/commit to the root agent.

## Decisions

- 2026-10-06 — Investigation remained read-only beyond this claim log until the null-percentile finding was reproduced.
- 2026-10-06 — Extracted production `nationalRowsToFeatures` returned a row with both percentile fields null because `Number(null) === 0`; builder output can contain per-metric nulls for rows with the other metric present.
- 2026-10-06 — Root assigned narrow ownership: helper in dashboard.py and new test file `apps/dashboard/tests/national-overlay.test.js`; no export or commit.
- 2026-10-06 — Changed the helper to accept a percentile only when the original value is non-null, non-undefined, and numerically finite. Added regression cases for both-null, valid 0, and valid 75.
- 2026-10-06 — Test-first evidence: focused test failed because `no-percentile` was returned before the fix; focused test then passed. Full dashboard suite passed: 115 tests.

## Current step

Work is complete; reporting paths, evidence, and verification to root.

## Next step

Root integrates the helper/test and owns dashboard export and any shared-file coordination.
