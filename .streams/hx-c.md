# Stream log — hx-c — 2026-10-12

## Claim
- **Stream id:** `hx-c` (ROADMAP.md HX-C1..C7; ADR-0010 Stage C: Regional cutover, immutable generations, incremental refresh)

## Decisions & Verification
- **HX-C1 (Promotion Gate):** `apps/api/src/export/regions.py` implements `promote_region()` with real chunk sha256 verification at promote time, exact golden count comparison, `MEASURED_FLOOR_RATIO = 0.8` (refuses feed outages), rebaseline reason enforcement, and atomic `os.replace` swap with previous pointer retention. 18 tests in `test_regions.py`.
- **HX-C2 (Publication Pointers):** `apps/api/src/export/publication.py` emits `regions/{region_id}/gen/{generation}` manifests and `regions/{region_id}/current` pointers. If projected boot manifest exceeds 8 MiB (under 10 MiB cap), region index overflows to `manifest/regions`. Global `snapshot/current` promoted last.
- **HX-C3 (Region Builder & Incremental Refresh):** `apps/api/src/export/snapshot_builder.py` computes rank epoch breakpoints (101 quantiles per metric per resolution). `--previous-regions <path>` compares `region_input_hash()`: skipped regions reuse existing manifests, pointers, and chunks without re-prediction. Verified by unit test: unchanged-input run rebuilds 0 regions (`regions_rebuilt == 0`, `regions_skipped == len(cities)`).
- **HX-C4 (Worker Regional Reads):** `apps/dashboard/src/index.ts` and `release.ts` resolve logical keys to region generation manifests and content-addressed objects (`objects/{sha256}`). Fails closed with 503 + `Retry-After: 5` on missing chunks without cross-generation fallback.
- **HX-C5 (Workflow Incremental & DG-5 Prune):** `.github/workflows/batch-push.yml` fetches previous snapshot artifacts before build and passes `--previous-regions`. `scripts/prune_snapshot_releases.py` prunes stale regional generations outside DG-5 `{current, previous}` while retaining active pointers.
- **HX-C6 (Failure-Domain Drill):** `scripts/region_failure_drill.py` and `test_region_failure_drill.py` verify that corrupted chunks or dropped measured cells trigger `PromotionRefused` while keeping the pointer on the previous valid generation.
- **HX-C7 (Client Schema v2 & Regional Retention):** `apps/api/src/serving/dashboard.py` accepts `coverage.schema_version <= 2`. `changedRegionIds()` updates only changed regions on manifest refresh; unchanged regions are retained in active and inactive LOD caches. Legend displays rank epoch date when older than snapshot (DG-10).
