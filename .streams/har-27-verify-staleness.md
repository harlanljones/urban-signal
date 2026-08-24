# Stream log — verify-staleness — 2026-08-23

## Claim

- **Stream id:** `verify-staleness` / HJ-27
- **Leaf files I will create/edit:** `scripts/feed_staleness_probe.py`, `apps/api/tests/unit/test_feed_staleness_probe.py`, `.github/workflows/feed-staleness.yml`, `docs/research/current-city-feed-gaps.md`, `.streams/har-27-verify-staleness.md`
- **Spine files I expect to need:** none

## Intent

Finish the feed-staleness monitor verification: prove a deliberately stale fixture is detected, prove webhook payload delivery at the test seam, document what staging verification can and cannot establish, and leave runnable focused-test/Ruff evidence.

## Decisions

- 2026-08-23 — Scope is limited to the monitor, its focused tests/workflow/documentation, and this stream trail; city registry, dashboard, and model files are out of scope.
- 2026-08-23 — Graph project `home-harlan-dev-urban-signal` is ready at generation `2026-08-24T03:21:14Z`; all claimed source/docs paths have no recorded coverage gaps.
- 2026-08-23 — Strengthened the stale fixture to 13 days old, verified webhook fan-out to two endpoints, and documented that staging delivery requires a manual workflow run with repository secrets.

## Current step

Focused verification is complete; reviewing the final diff and preserving unrelated worktree edits.

## Next step

Hand off the focused test/Ruff/compile/diff-check evidence; staging webhook delivery remains an explicitly documented manual limitation.
