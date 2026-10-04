# Dashboard selection and tile recovery validation

Fixed three reproduced defects: stale prediction replies overwriting newer selections, catalyst highlighting lagging the accepted selection, and failed incoming tiles remaining stalled indefinitely. Selection generation guards cover metro/national inspection, coordinate/H3 search, clearing, direct selection and mobile inspector dismissal. Tile loading preserves outgoing coverage, retries at 500/1500/4000 ms, stops after three retries, and offers an accessible manual Retry action.

Luna implemented both streams and independently reviewed the integration with no blockers.

## Verification

- Dashboard suite: 110 passed; typecheck and Worker build dry run passed.
- API serving suite: 38 passed. Required CI/CD preflight passed, including the API interlock gate, cross references, facts, product lint, dashboard export and Ruff.
- Chromium opened `https://us-dash.harlanljones.com/?city=nyc`, substituting only navigation HTML with the candidate export. Production APIs and map services remained in use; delays and failures were injected only in the test browser. This verifies the candidate, not a deployed change. No local server was used.
- Correct first and second catalyst highlighting; reversed successful/failed prediction replies preserve the latest selection; clearing prevents delayed reopening.
- Two transient tile failures recover without camera movement. Exhausted retries stop automatically; the Retry control is reachable on a 390px mobile viewport with the inspector open and successfully reloads tiles. Healthy status is hidden; no browser page errors occurred.

Browser results/screenshots and verification logs are under `/workspace/dashboard-recovery-validation/`. Source HTML and exported static HTML are synchronized. No production deployment or live ingestion activation was performed.
