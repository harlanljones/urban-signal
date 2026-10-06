# Stream log — luna-interaction-sweep — 2026-10-06

## Claim

- **Stream id:** luna-interaction-sweep
- **Leaf files I will create/edit:** `.streams/luna-interaction-sweep.md` only; investigation evidence under `/workspace/bug-sweep/interaction/`
- **Spine files I expect to need:** none

## Intent

Sweep production city selection/search, city switching, comparisons, favorites and filters, and mobile panel interactions for reproducible bugs. Report confirmed triggers, evidence, impact, and a narrow fix proposal; implementation and tests remain with the root agent until assigned.

## Decisions

- 2026-10-06 — Initial scope was read-only; root explicitly assigned the coordinate-search fix in `apps/api/src/serving/dashboard.py` and focused regressions in `apps/dashboard/tests/selection-race.test.js`. Do not export the static copy or commit.
- 2026-10-06 — Production `0,-75` is accepted by H3 resolution and reaches `/api/v1/predict` when manually supplied with H3 (`8966cec1557ffff`), which returns the expected no-precomputed-cell 404. The UI issues no request and leaves the inspector empty because `if (lat && lng)` rejects zero latitude.
- 2026-10-06 — Production `40,` and `north,-73` cause an H3 range exception before any prediction request; `91,-73` causes an unhandled MapLibre invalid-latitude error before prediction. Add validation before H3 resolution or map movement, with a toast and no replacement of the accepted selection.

## Current step

Assigned fix and regression tests are complete. The focused selection-race suite passes 13/13 after observing expected RED failures for both the search handler and zero-axis lookup helpers. `git diff --check` is clean.

## Next step

Root owns static export, integrated suite, and preflight. No further edits in this stream.
