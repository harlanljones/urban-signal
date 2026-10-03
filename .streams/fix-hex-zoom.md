# Stream log — fix-hex-zoom — 2026-10-03

## Claim
- Stream id: fix-hex-zoom
- Leaf files: apps/api/src/serving/dashboard.py, apps/dashboard/public/index.html, apps/dashboard/tests/grid-zoom.test.js
- Spine files: none

## Intent
Fix mixed or missing metro hexagons when changing zoom resolution and prevent stale requests from restoring old grid cells.

## Decisions
- res7 and res8 share res4 parents but fetched/in-flight tracking ignores resolution. Render source accumulates features from all LODs. Generation exists but is never incremented.
- On LOD transition, reset the displayed grid and fetched parents; generation isolates outstanding requests. Keep global concurrency accounting so old requests can settle safely.

## Current step
Implementation and focused verification complete. Canonical dashboard exported with the existing API virtualenv.
- Four named loader regressions pass via `node apps/dashboard/tests/grid-zoom.test.js` (first three observed failing before the fix).
- 25 interlock checks pass, including exact canonical/exported HTML byte sync.
- Dashboard/product cross-reference passes.
- Ruff on dashboard.py and git diff --check pass.
- Required full preflight stops at product facts:check: Bun is unavailable. The full dashboard Bun suite and product checks cannot run in this environment.

## Next step
Install/provide Bun through an environment with working networking, then rerun full preflight and dashboard suite. Browser/live deployment confirmation remains unverified; no deployment was performed.
