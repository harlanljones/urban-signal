# Stream log — tile-recovery — 2026-10-04

## Claim

- **Stream id:** tile-recovery
- **Leaf files I will create/edit:** `apps/api/src/serving/dashboard.py` (tile state block, loader region, and dedicated `#tile-loader-status` HTML/CSS only), `apps/dashboard/tests/grid-zoom.test.js`, `.streams/tile-recovery.md`
- **Spine files I expect to need:** none

## Intent

Recover failed LOD tile requests with bounded retries and backoff, clear status and exhausted-state messaging, cancellation of obsolete retry bookkeeping on LOD changes, and stale-response rejection while preserving the global concurrency limit. Verify generation changes, reversals, partial batches, successful empty responses, and HTTP failures with deterministic fake timers.

## Decisions

- 2026-10-04 — Copied the required template before inspecting implementation files. Root confirmed ownership of a dedicated accessible loader status element and its styles.
- 2026-10-04 — Added bounded per-parent backoff, generation cancellation, HTTP/malformed-payload retry handling, explicit exhausted retry, mobile-live status, and successful-empty settlement. Healthy nonempty loads leave the dedicated banner hidden while the legend carries coverage state.

## Current step

Focused tests and all dashboard tests pass against the Python source. Root is reviewing mobile drawer visibility separately.

## Next step

Wait for root integration/browser review; make any loader-scope fixes, then report validation.
