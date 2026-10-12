# Stream log — hx-a4 — 2026-10-12

## Claim

- **Stream id:** `hx-a4` (HX-A4 coverage.tiers + HX-A6 worker types + worker pin fix; ROADMAP.md)
- **Owner:** orchestrator (delegated agents failed with 429 quota errors)

## Current step

Complete.

## Decisions

Done.
- HX-A4: `_coverage_block` adds additive `tiers` (national lodes / urban_detail lims authority k_ring); schema_version stays 1; existing keys untouched.
- HX-A6: optional `coverage.tiers` in worker `Manifest` type; passthrough test.
- **Production bug (pre-existing, not from this work):** the client pins `snapshot_id` to the manifest's logical id (`r-YYYYMMDD-hash`) but the live release is addressed by sha. `withRelease` could not load that id, so reads fell to twin keys; parents with no hexes are never published (empty chunks publish nothing), so pinned reads returned 503 'generation not available' where unpinned reads return 200 + `missing`. Verified in production: the 7 failing NYC res-6 parents are exactly the unpinned `missing` list; z4.5 national view reported `failed` with 2,135 hexes drawn. Fix: `withRelease` resolves a pin that the current release's own manifest declares to the current release; `readSnapshotValue` treats a pin equal to the manifest's `snapshot_id` as the current release. Regression test in `release.test.ts` fails without the fix. A stale unrelated id still 503s (no cross-generation fallback).

## Next step

Stage A integration checkpoint (preflight + benchmark), then Stage B (HX-B1).
