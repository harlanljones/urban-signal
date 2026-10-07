# Recon: coverage/publication spec seams — implementation state (2026-10-07)

Read-only recon for the coverage/national publication spec. No source edits. All line refs from working tree at HEAD (branch main).

## 1. Manifest shape — GET /api/v1/manifest

- Built in `apps/api/src/export/snapshot_builder.py:781-811` (`build_snapshot`), written to `dist/manifest.json`, registered as KV key `manifest` via `register()` (snapshot_builder.py:811).
- Exact fields (snapshot_builder.py:781-800):
  - `generated_at` (ISO UTC), `app_version` (installed package version, fallback `"2.0.0"` — snapshot_builder.py:832-838), `cities`, `resolution` (9), `k_ring` (1), `catalyst_threshold` (84.0), `counts` (per-city), `cells`, `cells_sharded`, `keys` (key -> `{bytes}` for every published KV key), `tile_resolution` (5), `tile_index` (legacy res-9 parent map), `tile_indexes` (`{"7"/"8"/"9": parent -> {count, cities, bbox}}`), `lod` (`{resolutions: [7,8,9], tile_parent_res: {"7":4,"8":4,"9":5}}`), `metro_index` (per-city `{city_id, name, bbox, center}`).
  - Conditional: `national` block (`{"generated_at", "resolutions": {"4"/"5"/"6": {count, chunks}}}`) only when `--national-dir` supplied and data exists (snapshot_builder.py:775-777, 801-802); `context_layers` block only when `--context-dir` carries a table (803-804).
- **No `snapshot_id`, no coverage fields anywhere in the manifest today.**
- Client-side TS mirror: `apps/dashboard/src/index.ts:101-145` (`Manifest`, `TileIndexEntry`, `MetroMeta` — no snapshot_id/coverage fields).
- Edge route: `apps/dashboard/src/index.ts:1559-1572` — serves KV `manifest` value verbatim, ETag `"<sha256-32>"`, 304 support, `cache-control: public, max-age=300`, `x-snapshot-created: manifest.generated_at` (1442-1447). Manifest isolate-cache TTL 60 s (`MANIFEST_TTL_MS`, index.ts:53); stale-beats-404 fallback (index.ts:304-317).
- **Storage: Workers KV only.** Single binding `SNAPSHOT` in `apps/dashboard/wrangler.jsonc` (id `cea91d937ff344bf9ae70f62734f5ae5`); static HTML via `ASSETS` binding. **No R2 bucket/binding exists** in the repo (grep for R2/bucket across apps/dashboard and workflows: nothing). The docstring in national_builder.py:28-30 says "the monthly workflow uploads the build tree under its artifact key (R2)" — **no such monthly workflow exists** (`.github/workflows/` = batch-push.yml, bay-area-context.yml, feed-staleness.yml, rejection-recheck.yml only).

## 2. National layer

### Edge worker routes (exist, in TS worker)
- `GET /api/v1/national` — index: `apps/dashboard/src/index.ts:1637-1644` → `fetchNationalIndex` (snapshot.ts:222-226) reads KV key `national/index`; 404 `{error: "No national layer snapshot published."}` when absent. Index doc shape (snapshot.ts:212-218): `{generated_at, resolutions: {"<res>": {count, byte_size, sha256, parents: string[], generated_at}}}`. Note: `_publish_national_layers` also writes a richer per-parent `chunks` map (`{bytes, sha256, rows}`) into the same index doc (snapshot_builder.py:520-536), which the TS interface does not declare (harmless, extra field).
- `GET /api/v1/national/{res}?parents=<csv>` — chunks: index.ts:1649-1668. Contract: res ∈ {4,5,6} (`NATIONAL_RESOLUTIONS`, snapshot.ts:208), parents comma-separated 15-char hex res-3 indexes, **max 64 parents per request** (`MAX_NATIONAL_PARENTS_PER_REQUEST = 64`, snapshot.ts:210, enforced index.ts:1659-1661). Response `{res, count, cols, rows: unknown[][], missing: string[]}` (snapshot.ts:228-262), ETag + 304, 400 on invalid res/malformed/oversized parents.
- KV chunk keys: `national/{res}/{parent}` (snapshot_builder.py:490, 510). Chunk payload written by `_publish_national_layers` (snapshot_builder.py:440-536): `{res, parent, year, signal_source, cols: ["h3","jobs","workers","jobs_pct","workers_pct"], rows: [...]}` rows-of-arrays; empty (all-null) chunks are NOT published; per-chunk budget `NATIONAL_MAX_CHUNK_BYTES = 5 MiB` (snapshot_builder.py:88, enforced 512-518).

### FastAPI serving API
- `apps/api/src/serving/router.py` has **no manifest and no national endpoints** (routes: /cities, /submarkets, /spatial/divisions, /predict, /predict/batch, /catalysts, /grid, /predictions/submarket/{name}, /dashboard/metrics, /hex/{h3_index}/features — router.py:113-434). National is edge-worker-only.

### Why production 404s national
- The route + client both exist and are tested, but **`batch-push.yml:119-122` runs snapshot_builder WITHOUT `--national-dir`**: `python -m src.export.snapshot_builder --out dist --context-dir build/context`. So `national/*` keys are never in KV → `fetchNationalIndex` returns its error → edge 404s. National parity: national_builder's `current.json` pointer is written into the local build tree (national_builder.py:530-576) but never uploaded anywhere by any workflow.

### Client chunk-request path (browser, inline in `apps/api/src/serving/dashboard.py`)
- `updateNationalOverlay()` (dashboard.py:1932-1991): fires below `ZOOM_FLOOR = 6` (1805); picks res by zoom (`nationalResForZoom`, 1900-1904: <5→4, <8→5, else 6); computes res-3 parents covering bounds by lat/lng sampling (1906-1925); filters against a **client cache Map only** (`nationalCache` 1819-1823) — **there is NO availability gating from the manifest, no check of `manifest.national`, no use of the national/index parents list, no manifest-derived skip**.
- Batching: batches of **24** (`BATCH = 24`, dashboard.py:1955) — *smaller* than the API's 64 cap; fired with a single `Promise.all` over ALL batches concurrently (1959-1980) — **no concurrency cap**. Plain `fetch` (1963), `if (!resp.ok) return;` — **no retry, no timeout, no AbortController, no generation guard**, negative results are simply not cached (parent remains uncached → refetched next pan).
- Debounced 250 ms (`scheduleNationalLoad`, 1927-1930). Client row→feature conversion `nationalRowsToFeatures` (1995-2029) honors the honesty rule (skips null-percentile rows).
- Contrast: metro LOD tile loader *does* have a generation guard — `tileLoadGeneration` (1798, captured 3064, compared 3070) plus concurrency-2 worker pool (`TILE_FETCH_CONCURRENCY = 2`, 3054-3061) and manifest-tile_index gating (3023-3047). The national path lacks all of this.

## 3. Client request behavior vs the spec's 8 behaviors

Existing (metro gridtiles path, dashboard.py:2975-3104):
- Debounce 220 ms (2980-2983), manifest tile_index whitelist (3034-3037), concurrency 2 (1804), batch 32/request (1803), generation guard `tileLoadGeneration` (1798/3064/3070), in-flight dedupe via `tilesInFlight` Set (1796, 3057-3077), negative "fetched" marking of absent parents after a *successful* response (3072-3073), LRU feature eviction at 120k (3106-3126).

Missing vs spec (national path + globally):
- No dedupe keyed by snapshot_id+resolution+parent (no snapshot_id exists anywhere in the client or API — grep over apps/api/src, apps/dashboard/src, scripts: zero hits; only unrelated `test_snapshot_ids_survive_other_feeds_churn` in apps/api/tests/unit/test_scheduler.py:213).
- No negative caching of empty chunks (failing fetch leaves parent uncached-and-refetchable; metro path marks fetched only on success).
- No retry/backoff anywhere (no retry logic in dashboard.py; retries exist nowhere client-side).
- No manifest refresh interval — `fetchManifest()` (2503-2528) runs once on DOMContentLoaded (2574). No 5-min refresh, no version mismatch check (manifest `app_version` is never compared client-side).
- No timeout/AbortController on any client fetch (manifest, gridtiles, national, predict, catalysts).

## 4. snapshot_builder.py — CLI & artifacts

CLI (`main`, snapshot_builder.py:841-897): `--out` (default `dist`), `--cities` (nargs, default `SUPPORTED_CITIES` = full CityId registry, line 63), `--skip-legacy-cells`, `--national-dir` (857-864), `--require-national` (865-872), `--context-dir` (873-880), `--dense-metro` (881-885). Constants (63-89): DEFAULT_RESOLUTION=9, DEFAULT_K_RING=1, CATALYST_THRESHOLD=84.0, TILE_RESOLUTION=5, LOD_RESOLUTIONS=coverage.METRO_LOD_RESOLUTIONS=(7,8,9), LOD_TILE_PARENT_RES={7:4,8:4,9:5}, MAX_KV_VALUE_BYTES=20 MiB, MAX_MANIFEST_BYTES=10 MiB, MAX_BULK_BYTES=512 MiB.

Artifacts → `dist/` + KV keys via `register()` (620-629, each ≤20 MiB, collected into `kv-bulk.json` for `wrangler kv bulk put --binding SNAPSHOT`):
- `grid/{city}`, `catalysts/{city}`, `submarkets/{city}`, per-cell `cells/{h3}` (+ `cells/index_meta`, legacy `cells/index` unless `--skip-legacy-cells`), `gridtiles_res{7|8|9}/{parent}` + legacy `gridtiles/{parent}` shim for res 9 (732-767), `catalysts/index`, `national/index` + `national/{res}/{parent}` (via `_publish_national_layers` when `--national-dir`), `manifest`.
- `dense_metro` swaps res-9 render set to `coverage.metro_cells` k_ring=3 bounded 1.5 km (571-602, `_dense_metro_grid` at 342).
- `require_national` (`_require_national_block`, 547-569): fails closed if no national block published or missing any of res 4/5/6.
- Percentile pipeline: `_apply_percentile_normalization` per publish set (667-681), LOD aggregates res 8/7 (674-681).
- CI usage: batch-push.yml:122 (no --national-dir, no --dense-metro, no --metrics-out — **`--metrics-out` does not exist**). Workflow then uploads `dist/` artifact (124-128) and pushes `dist/kv-bulk.json` to KV (135-137).

## 5. national_builder.py

- Builds Census LEHD LODES8 (WAC/RAC C000) per-hex nationwide signals at `DEFAULT_RESOLUTIONS = (4,5,6)` (72), states = 51 (50+DC, 79-133), year default 2023. `BUILDER_REVISION = "1"` (75).
- Output tree (17-22): `dist/national/res{res}/{res3_parent}.parquet` (columns `res3_parent` + `h3_index, res5_parent, res4_parent, jobs_c000, workers_c000, blocks_wac, blocks_rac, jobs_c000_national_pct, workers_c000_national_pct, year, signal_source` — 138-149, 478), `res{res}/report.json` (499-518: generated_at, signal_source, builder_revision, year, resolution, cells, states_requested/with_wac/with_rac, hexes_with_jobs/workers, total_jobs/workers, chunks {name:size}, chunks_sha256, states report), `national/manifest.json` (626-676: aggregate, `sha256` over concatenated chunk bytes, `checksum_verified: True`, `lodes_version: "v8"`, `artifacts` per-res summary), `national/current.json` promotion pointer (560-574: `artifact_key = "national/{signal_source}/{year}/{sha256}"`, sha256, signal_source, builder_revision, lodes_version, year, resolutions, promoted_at).
- `promote_national` (530-576): validates checksum_verified + ≥1 data chunk with ≥1 measured hex per resolution before writing current.json; refuses otherwise (fail-closed promotion).
- CLI (`main`, 679-719): `--out`, `--resolutions`, `--year`, `--states`, `--cache-dir` (default `data/national/lodes`), `--no-verify-checksums`, `--no-promote`.
- Download integrity: per-state `lodes_<st>.sha256sum` verified (177-210). Not invoked by any workflow currently.

## 6. Tests

API (PYTHONPATH=apps/api, pytest):
- `apps/api/tests/unit/test_interlock_gate.py` — `TestSpineCoverage` (manifest paths exist, every spine file has SPINE_INVARIANTS coverage, 330-353); `TestDashboardWiring` (METRO_META from get_dashboard_html vs REGISTRY, byte-synced `apps/dashboard/public/index.html` static copy, snapshot export covers every registered city, 359-504); `TestNationalWiring` (506-600): national fixture → `build_snapshot(national_dir=...)` publishes manifest `national` block + `national/index` key within NATIONAL_MAX_CHUNK_BYTES; worker `index.ts` contains `/api/v1/national/` route + `fetchNationalIndex`; `snapshot.ts` contains `kvJson(env, "national/index")`. Runs in CI via `pytest -q -m interlock` (batch-push.yml:71).
- `test_export_snapshot.py` — manifest shape, cells sharding, national publish/absence/budget/require-national (233-348), percentile properties/rank spaces, LOD tiles/parents/percentiles, `test_dense_metro_flag_renders_continuous_grid` (605), `test_dense_grid_features_have_coverage_source` (627), context layers join (672-706), catalysts/metro_index.
- `test_national_builder.py` — aggregation, WAC/RAC independence, ranks, end-to-end build, no-data reports, promote pointer/empty-build/missing-manifest rejections, unknown states, manifest sha256.
- `test_coverage.py` — `metro_cells` (k1/k3 counts, bounded ≤1.5 km, unknown city raises), `assign_cell`, `aggregate_values` (raw averaging), `parent_cells`, transport-free features.
- `test_snapshot_reach.py`, `test_national_grid.py`, `test_gbfs_and_national_feeds.py`, `test_scheduler_national_feeds.py` also exist.
- **No tests exist for the browser client logic in serving/dashboard.py's inline JS** (no dashboard.py JS unit tests; coverage is static-source assertions via interlock).

Dashboard (bun): `apps/dashboard/tests/index.test.ts` (worker routes: manifest/tile index, gridtiles res 7/8/9 incl. legacy shim + ETag, national index + chunks + ETag + invalid res/parents 529-615, cities/aliases, discovery surface, MCP) and `snapshot.test.ts` (queryCatalysts/Submarkets policy parity, lookupPrediction sharding, fetchNationalIndex/Rows, fetchGridTiles — 190-260).

`scripts/verify_cicd_preflight.py` (178 lines): sequential gates via `_run` — dashboard↔product-site cross-reference (registry vs METRO_META in get_dashboard_html() AND static public/index.html vs product facts.json), then runs the CI-equivalent checks (pytest interlock, export_dashboard, ruff, bun build/typecheck/lint). Exit 0 = all green; first failure aborts.

## 7. Storage / versioning

- KV namespace `SNAPSHOT` (wrangler.jsonc:7-12), mutable logical keys, **no key versioning**: every publish overwrites `manifest`, `grid/{city}`, etc. No `releases/{snapshot_id}/` pattern, no `snapshot/current` pointer, no `snapshot_id` query param on any route (grep: zero hits in api src, dashboard src, workflows). The only versioned-key machinery anywhere is national_builder's `artifact_key = national/<signal_source>/<year>/<sha256>` + `national/current.json` (never uploaded — see §1/§2).
- ETag scheme: sha256(raw value) first 32 hex chars, quoted (index.ts:263-282); manifests cached in-isolate 60 s (index.ts:53, 304-317); responses `cache-control: public, max-age=300`.

## 8. Dashboard UI attach points

- Legend card: `apps/api/src/serving/dashboard.py:1705-1717` — `.map-legend-card` with `#legend-metric-title`, `.legend-bar` (gradient from `HEX_RAMP`), `#legend-ticks`, `.legend-note` rows: baseline key (1715), `#legend-no-data` row (1716, shown only for context metrics, toggled in `updateMetric` ~3249-3251), `#legend-attribution` (1717; populated from `context_layers.attribution` at 3252-3256; a second `.legend-attribution.context-sources` is rendered inside the inspector's Bay Area context block at 3790). A national "coverage/source strip" and "context legend" would attach around these rows / in `updateMetric` (~3235-3285) and `regenerateLegend` (~3292-3307).
- Metric selection: `#metric-select` dropdown + `updateMetric()` (~3235-3285); context metrics from `manifest.context_layers.metrics` populate the select via `populateContextMetrics` (2508; `CONTEXT_METRICS` map at 1784).
- Mobile: `.mobile-toolbar` nav (1637, CSS 1422/1514), `wireMobileChrome()` (2569), panels include search/layers/inspector; inspector right sidebar `.sidebar-right` with `#inspector-content` (2566-2568, empty-state CSS 1074-1120; mobile: inspector becomes an overlay sheet, CSS ~1513). Coverage/source strip would attach to the inspector render path (`handleHexSelection` / context block at ~3760-3791).
- Camera/metro index: chips rendered from manifest `metro_index` (`renderMetroChips` 2575; METRO_META comes from REGISTRY via `get_dashboard_html()` per interlock US-427).

## 9. Interlock vs spine

- `docs/agents/spine-manifest.txt`: config.py, spatial/city_registry.py, spatial/cities/__init__.py, geo_utils.py, submarkets.py, producers/{scheduler,dob_permits_producer,complaints_311_producer,sla_licenses_producer,deeds_acris_producer,accela_client}.py.
- **None of the spec's seams are spine.** `spatial/coverage.py`, `export/snapshot_builder.py`, `export/national_builder.py`, `serving/dashboard.py`, `dashboard/src/snapshot.ts`, `dashboard/src/index.ts`, `.github/workflows/batch-push.yml` are all leaves — editable in parallel, no gate needed. (The interlock gate still *asserts on* dashboard.py/index.ts/snapshot.ts content, so edits must keep the interlock tests passing: byte-synced `apps/dashboard/public/index.html` regenerated via `scripts/export_dashboard.py` after any dashboard.py change.)

## 10. Test / build commands

- API tests: `PYTHONPATH=apps/api .venv/bin/python -m pytest apps/api/tests/unit` (CI pattern batch-push.yml:69-72; interlock subset: `pytest -q -m interlock apps/api/tests/unit/test_interlock_gate.py`). Env: `uv pip install -e "apps/api[dev]"` (batch-push.yml:60-62).
- Dashboard: from repo root `bun run build && bun run typecheck && bun run lint` (batch-push.yml:80); package-local `apps/dashboard/package.json` scripts: `test` = `bun test tests`, `build` = `wrangler deploy --dry-run --outdir dist`, `typecheck` = `tsc --noEmit`, `deploy` = `wrangler deploy`, `dev` = `wrangler dev`.
- Full pre-flight: `python3 scripts/verify_cicd_preflight.py` (mandatory per AGENTS.md before ending a task).

## Key deltas the spec must account for

1. National route exists & is tested end-to-end (worker + snapshot.ts + interlock), but production 404s purely because batch-push.yml never passes `--national-dir` and no workflow builds/uploads national artifacts; there is no R2 binding at all.
2. No snapshot_id / versioned publication exists anywhere; only national_builder's sha256 artifact_key + current.json pointer, which is local-only.
3. National client fetch path has none of the metro path's guards (no concurrency cap, no generation guard, no retry, no negative caching, no availability gating from manifest; batch size 24 vs API cap 64).
4. Client manifest fetch is one-shot on load; no periodic refresh or app_version comparison.
5. coverage.py already exports `metro_cells` / `aggregate_values` seams (dense metro + LOD) but has no per-city "availability/coverage" publication for the manifest.
