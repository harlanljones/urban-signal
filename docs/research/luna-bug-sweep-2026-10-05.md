# Luna bug sweep

Three Luna streams investigated map loading, dashboard interactions and Worker snapshot queries. Work started from deployed PR #126 (`d4c4b70`). Existing baseline: 110 dashboard tests passed; production browser checks for selection races, highlighting and tile recovery passed.

## Confirmed findings

- Valid zero-axis coordinates were silently ignored. Production search for `0,-75` sent no prediction request, while H3 resolution and a direct API request accepted the coordinate (404 for missing snapshot coverage). Truthiness guards treated zero as missing.
- Malformed coordinates escaped the search handler as unhandled errors. Production `40,` and `north,-73` caused an H3 error; `91,-73` caused a MapLibre invalid-latitude error. Validation must happen before H3 conversion, camera movement and selection-generation changes.
- Division filtering normalized the request but left stored display labels unchanged. A failing source-level query test stored `Central / Downtown` and returned zero results for its matching lowercase filter. Both catalyst and submarket queries share this defect.
- National overlay conversion accepted rows with both percentile fields null because `Number(null)` becomes zero. An extracted-helper reproduction confirmed this against the builder's nullable-rank contract. Legitimate zero percentiles must remain supported.

These are targeted correctness fixes. No speculative national-overlay race change, registry change, or ingestion activation is included. Production requests used for investigation were read-only; request failures/delays were injected only in test browsers. Candidate browser validation uses the production URL with only the navigation HTML replaced by the candidate export, without a local server.

## Verification

- Final dashboard suite: 116 passed, 0 failed. Typecheck and Worker build dry run passed; the Node zoom-test command passed.
- API serving suite: 38 passed. Full required CI/CD preflight passed, including interlock, cross references, facts, product lint, dashboard byte-sync and Ruff.
- Independent Luna review found no actionable blockers and ran 102 focused tests successfully.
- Chromium candidate checks at the production URL accepted `0,-75`, `40,0`, `0,0` and a valid H3 cell. Malformed, extra-component, out-of-range, partially numeric and invalid H3 inputs issued no prediction request and preserved the accepted selection. National conversion skipped null-only rows and preserved zero or one available percentile. No page errors occurred.
- These checks validate the candidate against production APIs, not a deployed change. The baseline deployed regression suite also passed before edits.

Artifacts are under `/workspace/bug-sweep/`. No production deployment was performed.
