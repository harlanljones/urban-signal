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

## Defects found 2026-10-13 — the regional read path is inert in production

Measured on a real `build_snapshot` (`cities=["nyc"]`, `--dense-metro`), not inferred. These are
why Stage C is "built and tested" but not "live"; each needs its own change and cannot be fixed
by enabling anything alone.

1. **No `regions/*` key is ever published.** `kv-bulk.json` contains **0** keys under `regions/`
   while `manifest.regions` names 157 generations. Cause: `_write_publication_plan` passes
   `manifest["regions"]` (a `region_id -> generation` **string** map) as `metadata["regions"]`, and
   `plan_publication`'s string branch only fills `regions_map` — the dict branch that emits
   `regions/{id}/gen/{gen}` and `regions/{id}/current` never runs. The generation manifests and
   pointers are staged to disk by `promote_region` and then dropped. Consequence: the worker's
   `loadRegionManifest` always misses and every read falls back to the release path; the DG-5 prune
   has no region keys to prune; `manifest.regions` is client-only metadata.
2. **Region chunk shas do not match the published objects.** For `grid/nyc` the region manifest
   records `062bc6f3…` (1,926,716 B) while the uploaded content-addressed object is `48cb80e6…`
   (1,875,028 B). Two independent causes: (a) `stage_region` hashes
   `json.dumps(payload, separators=(",",":"))` (unsorted) while `plan_publication` hashes
   `canonical_bytes` (sorted keys); (b) `_bucket_grid_tiles` mutates the grid features in place
   (`props["city_name"] = …`) *after* `register("grid/{city}", …)` has already serialized them, so
   the region chunk serializes different content for the same logical key. Enabling region pointers
   before fixing this would return 503s from `readObjectEntry` (object missing) and would serve two
   different `grid/{city}` payloads depending on path.
3. **The region chunk set does not match what the reader resolves.** A metro region manifest holds
   `grid/`, `catalysts/`, `submarkets/` plus **1,846 `cells/*` entries**, and **no `gridtiles_*`
   keys at all**. `resolveLogicalKeyRegion` returns `null` for `cells/` (no cell→owner map exists)
   and the reader never looks up tiles through a region, so ~1,846 of the 1,849 entries per metro
   (~5 MB across the registry) are published and never read, while the dominant read path (tiles —
   all 472 benchmark requests) never touches a region pointer. Spec §4.1's shared-parent ownership
   rule ("the region contributing more cells owns the parent, the other lists `shared_parents`") is
   not implemented; `_bucket_grid_tiles` merges across cities before any region split.

Fix order (each verifiable on its own): align the chunk encoding and capture the registered payload
at `register()` time → emit region manifests/pointers via `bulk_entries` → implement §4.1 parent
ownership so tiles resolve per region → then drop or map the `cells/*` region entries.

### Fixed 2026-10-13 (`693b688`)

All three, in the order above, with the tile half deliberately deferred:

- **One hashing pass.** `plan_publication` split into `hash_entries` (objects + logical key index)
  and `build_manifest`; `plan_publication` is their composition, so existing callers are unchanged.
  The builder hashes once, before Region staging, and builds each Region chunk map from
  `objects[keys[logical]["sha256"]]` — the same bytes the release publishes. Chunk shas now resolve
  by construction, and there is no second canonicalization pass: the build stays cost-neutral
  (measured: `snapshot_ms` unchanged, `peak_rss_mib` +178 MB because the object table is now
  materialized before Region staging instead of at the very end).
- **Real manifests, real pointers.** The published `regions/<id>/gen/<generation>` value is the
  staged `RegionManifest` (with `chunks`), not the ad-hoc meta dict that preceded it — the worker
  requires `region_id` and `chunks` and would have rejected the dict. `regions/<id>/current` carries
  `{current, previous, golden_count, promoted_at}`. The registered manifest *entry* is hashed rather
  than the live dict, because `register()` appends `keys["manifest"]` after serializing.
- **Only exclusively-owned keys.** A Region manifest lists `grid/`, `catalysts/` and `submarkets/`
  for its metro. Tile parents are shared between metros (§4.1) and cell shards have no resolvable
  owner, so both stay on the release path; this also removed ~1,846 unreadable `cells/*` entries per
  metro.
- **Prune.** `prune_snapshot_releases.py` now lists the `regions/` prefix (it only ever listed
  `releases/`, so no region generation was ever judged stale) and reads the builder's compact
  `dist/region-pointers.json` sidecar rather than the ~570 MB versioned bulk. `read_region_pointers_from_bulk`
  is deleted with its test.

Still open, and now the only thing between this and per-region tile addressing: §4.1 parent
ownership (`shared_parents`, "the region contributing more cells owns it"). Until that lands, tiles
resolve through the release manifest as before — which is why no read behaviour changed, and why the
Client benchmark's request profile is untouched.

### Also fixed 2026-10-13 — the incremental path could not see change (`b503776`, `50d0500`)

Wiring the pointers exposed that `regions_skipped` was structurally guaranteed to be 0 in production.
Four independent causes, each measured:

1. **Wrong engine attribute.** The hash read `getattr(engine, "model_id", "default")`, but the engine
   exposes `model_bundle_id` — so the model was pinned to the literal `"default"` and a retrain would
   have rebuilt nothing. Now reads `model_bundle_id`, falling back to `model_provenance`.
2. **A national key that never exists.** `national_block.get("checksum")` — `_publish_national_layers`
   returns `{generated_at, resolutions}`, so the national input was always `None`. Now fingerprints
   the national artifact's own manifest `sha256`, read early from `national_dir`.
3. **Detection hashed differently from recording.** Skip detection ran without `context_sha`/
   `national_sha` and used `plan_hash="sparse"` where staging recorded `"sparse-{golden_count}"`, so a
   non-dense build could never skip and a dense build could skip a region whose context had changed.
   Both sites now call one `region_hash()`; a sparse build rebuilds rather than skipping on a hash
   that could never match.
4. **CI restored nothing.** `batch-push` runs validation on every push and *succeeds* without
   artifacts, so "the latest successful run" routinely had no `snapshot` artifact to download.
   `gh run download` failed instantly behind `continue-on-error`, `build/previous-snapshot/regions`
   never existed, `--previous-regions` was never passed, and the run reported `157 rebuilt / 0
   skipped`. Now selects the newest run that actually has a `snapshot` artifact, and logs which
   refresh mode the build is in.

The old test for this could not fail — a Region generation is a hash over chunk content, so a rebuild
of identical content reuses the same id. The tests now assert the `regions_rebuilt`/`regions_skipped`
counters, which discriminate: unchanged inputs skip 157, a changed `model_bundle_id` rebuilds 157.

Note the first publish after any input-hash formula change is necessarily a full rebuild, because the
previous generation recorded a digest computed the old way. Steady-state skipping is one run later.



