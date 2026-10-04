# Dashboard polish validation

Implemented the accepted production audit on `feat/dashboard-ui-polish`. Luna implemented offline fixtures and the initial UI, then reached its usage limit. Root finished the grid lifecycle and UI integration; a fresh Luna reviewer subsequently found no blocking correctness defects, including in the mobile padding and comparison range changes.

## Browser verification boundary

Browser checks use `https://us-dash.harlanljones.com/?city=nyc`, with only the main HTML document substituted by the candidate export. Tile, manifest, catalyst and map requests use production services. This previews candidate code without a local server or deployment; it does not mean production contains this release.

Screenshots, scripts and receipts are outside the repository in `/workspace/ui-polish-validation/`. Baseline evidence remains in `/workspace/us-dash-ui-audit/`.

## Results

- Full API suite: **6,138 passed, 2 skipped, 7 live probes deselected**. Existing dependency warnings remain. Final UI-only mobile padding/comparison range additions additionally passed **100 serving/interlock/feed tests**, the dashboard suite and repository preflight.
- Dashboard suite: **95 passed**, including outgoing-grid retention, failed partial-batch retry, stale-generation rejection, reversal, hysteresis and actual polygon geometry/unchanged values.
- Dashboard TypeScript check and Worker build dry run passed.
- CI/CD preflight passed: interlock, cross-reference, product facts, product lint, dashboard export and Ruff.
- Browser checks passed: city search/favorites/Escape, two comparison pins with forecast ranges and truthful unavailable drivers/source age, threshold/reset, 3D strength, fixed geographic selection and original inspector record through zoom, settled single resolution without outgoing ghosts, mobile navigation separation/expansion/2D, selected-point visibility above the sheet, and reduced-motion bypass. Direct mobile catalyst navigation reaches the intended zoom 12.9; sheet padding waits for the camera flight to finish. No page errors were recorded.

## Behavior and limits

Outgoing cells remain visible until every required incoming parent has successfully settled. Failed batches leave the outgoing grid intact and retry when the viewport updates. The 260 ms handoff morphs actual polygons and preserves properties; combined batches above 2,500 features use an opacity handoff to bound polygon work. Reduced motion skips the handoff. Metric/height changes use 380 ms paint transitions.

Selection keeps its geographic anchor and original inspector/comparison record; only the map outline follows the display resolution. Forecasts are explicitly estimates, source age is unknown, and snapshot time is publication time. No model/source verification or backend activation is implied.

Screenshots and sampled state checks do not establish frame rate, all transient frames, or full accessibility compliance. Live ingestion, R2 provisioning and production deployment remain separate operational work.
