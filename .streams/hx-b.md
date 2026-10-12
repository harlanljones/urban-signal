# Stream log — hx-b — 2026-10-12

## Claim
- **Stream id:** `hx-b` (ROADMAP.md HX-B1/B2/B3/B4/B5/B7; orchestrator-owned; delegated agents hit 429 quota)

## Decisions (all driven by measurement)
- **k-ring stays authoritative; no clipping to anchors.** Clipping would drop 5,948 of 54,172 published cells (11%), up to 71% in small metros. Spec §3.0 rewritten.
- **Ownership is a flag, not a removal.** `coverage_plan.plan_all()` gives each cell exactly one owning metro (nearest submarket, ties by city id). Builder `_cell_owners` applies the same rule in tile bucketing and cell shards, replacing first-city-wins. Verified by diffing old vs new snapshots: 181 of 373 contested cells change owner, all contested, all to an equal-or-nearer submarket; per-metro grids differ only by two added properties; geometry, LOD 7/8, catalysts, submarkets unchanged.
- **Honesty is 3% measured / 97% interpolated** (1,631 / 52,541). Client marks measured cells (outline + legend row) and states provenance in popup/inspector, instead of dimming the interpolated majority.
- Additive properties `coverage_label`, `in_anchor`; legacy `coverage_source` kept one release. Cost: +2.98 MB replay bytes (+3.0%), +17.8 MB bulk (+3.1%). Remove `coverage_source` once clients are confirmed off it.
- Rebaselined (HX-B7): tile workload sha e089578a..., semantic sha 90ca4436...; coverage fixture unchanged (INV-6 holds for all 157). Benchmark median 155.8 ms on new fixture (+3% vs 151.0, matches payload growth).
- Deleted `test_national_overlay_hands_off_to_metro_at_the_zoom_floor` (pinned source wording; behavior now covered by `national-overlay.test.js`).
- Mistake caught: a rejected over-long commit message left staged files that rode into the next commit (Stage A `1bdc17b` contains tiers + worker fix + bridge band).

## Open
HX-B6 (worker types for new properties; types already permissive), HX-B8 (single `displayResForZoom` + clamp; underlay approach already avoids the tier seam, and detail res is fixed at 9 until Stage D).
