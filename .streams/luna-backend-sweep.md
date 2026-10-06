# Stream log — luna-backend-sweep — 2026-10-06

## Claim

- **Stream id:** luna-backend-sweep
- **Leaf files I will create/edit:** `.streams/luna-backend-sweep.md`, `apps/dashboard/src/snapshot.ts`, `apps/dashboard/tests/snapshot.test.ts`
- **Spine files I expect to need:** none; review only

## Intent

Reproduce and fix the borough label normalization bug in the transport-free dashboard snapshot queries. Preserve existing case, space, and hyphen behavior while supporting labels that contain punctuation such as slashes.

## Decisions

- 2026-10-06 — Parent assigned exact test-first fix scope in `snapshot.ts` and `snapshot.test.ts`; no registry or external state involved.
- 2026-10-06 — RED reproduced: stored `Central / Downtown`, requested `central / downtown` returned an empty catalyst set because the stored label was not normalized.
- 2026-10-06 — GREEN fix: apply the existing borough normalizer to stored labels in both catalyst and submarket filtering; regression passes for both.
- 2026-10-06 — Dashboard typecheck passes. Full dashboard tests report 109 pass / 5 fail, with failures in the national overlay and selection-race files outside this change; focused snapshot test passes.

## Current step

Adding the failing regression case for a borough label containing a slash.

## Next step

Hand off fix and validation evidence to parent; no further backend sweep after the assigned bounded issue.
