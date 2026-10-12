# Daily GitHub Actions backend optimization — 2026-10-03

Phase 1 keeps Cloudflare Workers and web apps, daily 06:00 UTC freshness, and full snapshot publication. The source remains the existing synthetic/default model and registry features; this is a compute optimization, not durable municipal ingestion or a model-quality change.

## Changes and rollout

- Snapshot engines reuse predictions and SHAP explanations for the complete ordered 12-feature vector, with separate bounded 16,384-entry caches, concurrent miss protection and detached results. Every H3 identity, centroid, fallback LIMS, threshold and latency is assembled per request. Direct serving-engine construction keeps caching disabled by default.
- Builder metrics capture initialization, city inference, cell inference/SHAP, ranking/LOD, serialization, total duration, execution/cache counters, key/byte totals, context availability/age and completion status. Metrics stay outside KV.
- `batch-push-deploy / validate` remains. Main pushes and pull requests validate code; only the schedule or an explicit main dispatch publishes snapshots. Dashboard code releases validate and deploy independently, without building a fresh snapshot. Cloudflare credentials are confined to the write jobs, with separate non-canceling concurrency groups.
- New cities or incompatible schemas require a compatible reader release, then a manual main snapshot refresh, then coverage verification. Roll back caching with `--no-prediction-cache`; revert the workflow split commit to restore the former combined schedule/release pipeline if necessary.

## Method

Run from repository root:

```sh
TMPDIR=/workspace/test-tmp PYTHONPATH=apps/api \
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
apps/api/.venv/bin/python scripts/benchmark_snapshot.py \
  --out /workspace/backend-phase1/benchmark-no-context.json \
  --runs 3 --cache-mode compare
```

The final measurement runs alone after test jobs finish. The environment is Linux x86_64, Python 3.12.14, with a two-CPU cgroup quota and 8 GiB memory limit. It uses one initialized engine, unchanged weights and registry inputs across three cache-disabled, three cold-cache and three warm-cache builds. It covers every production city with the deployed workflow's default coverage and legacy-key settings. Initialization is recorded separately; daily Actions benefit should be assessed from the cold-cache result. Warm trials do not imply persistence between runners.

The comparator walks every logical KV payload, preserves array order, and checks predictions, SHAP, features, ranks, source dates, H3/key coverage and metadata. Only `inference_latency_ms` and known manifest/cell-index/national-index generation clocks are excluded. Manifest key byte lengths are validated against the actual compact JSON payload on each side before excluding those derived lengths from cross-run equality; latency is repeated in grids and catalysts as well as cells. Invalid byte metadata still fails comparison.

The benchmark records HEAD/tree and dirty status. Commit `b945892` contains the exact measured implementation; its code-file hashes match the companion evidence. Subsequent engine cleanup changes imports and type annotations only, without changing inference or cache behavior. Companion source SHA-256 evidence identifies the exact edited implementation. RSS is a Linux process-lifetime high-water mark from one reused process; its mode observations cannot support a claim about per-mode RAM savings. Cache misses for distinct vectors share a lock, so results apply to the present repeated-vector workload and should be remeasured if inputs become mostly unique.

## Validation and limits

Root verification passed cache/concurrency/isolation tests, quantile calibration, snapshot reach, full snapshot export, metrics, optional context and workflow routing suites. All 91 dashboard tests, the zoom regressions, root build/typecheck/lint, and complete `scripts/verify_cicd_preflight.py` passed. Independent Luna review found no unresolved correctness or workflow-routing issue. A regression specifically checks that latency-derived grid/catalyst byte differences compare equal and corrupted byte metadata fails.

The latest successful optional Bay Area context run was `36456726693` (2026-09-28). Its artifact download was blocked by the environment's network policy at the artifact storage host. These measurements therefore cover the supported no-context fallback; context presence, missing-table behavior and joining/ranking remain covered by tests. Fresh snapshot generation time is recorded separately from context source age. No production snapshot or deployment was triggered by this phase.

## Measured results

[Raw nine-run measurements](gh-actions-backend-benchmark-2026-10-03.json) and [source SHA-256 identities](gh-actions-backend-source-sha256-2026-10-03.json) accompany this report. All six cold/warm versus uncached semantic comparisons passed without differences.

| Cache configuration | Three durations (seconds) | Median seconds | Model executions | SHAP executions |
|---|---|---:|---:|---:|
| Disabled | 52.603, 53.761, 54.100 | 53.761 | 22,929 | 11,691 |
| Enabled, cold | 10.495, 10.400, 9.966 | 10.400 | 1,564 | 1,562 |
| Enabled, warm | 6.302, 5.598, 5.112 | 5.598 | 0 | 0 |

Cold-cache builder time fell 80.7% (53.761 → 10.400 seconds), a 5.17× speedup. Initialization took 2.693 seconds and is unchanged; adding that shared observation gives approximately 56.454 versus 13.092 seconds, a 76.8% reduction. Per-build initialization stages report near zero because they receive the shared initialized engine.

All nine builds retain 157 cities, 13,154 KV keys, 11,185 cells and 504 legacy/res-9 tiles. The cell pass contains 1,559 distinct normalized vectors. Whole-build model executions fall 93.2% (22,929 → 1,564); SHAP executions fall 86.6% (11,691 → 1,562). Cold builds record 21,365 prediction hits and 10,129 SHAP hits. Warm trials execute neither model nor explainer; this is reuse within one engine, not persistence between daily runners.

Median city inference falls 18.391 → 3.543 seconds; cell inference/SHAP falls 31.557 → 2.621 seconds. Complete ranking/LOD remains (0.182 versus 0.177 seconds). Serialization timing covers per-key serialization/writes; total also includes bulk serialization, assembly and remaining bookkeeping. Payloads range 70,787,178–70,792,428 bytes because latency changes serialized widths. Each manifest byte length is validated.

Process lifetime peak RSS reaches 1,380.535 MiB. Sequential comparison payloads and allocator retention prevent attributing mode observations to independent RAM usage. No cache RAM-saving claim is made.

## Usage and recommendation

Keep GitHub Actions. Standard hosted runner compute for this public repository remains eligible for $0 billing. Local measurements imply approximately 21.7 fewer builder minutes over 30 daily builds, excluding dependencies, setup, uploads and runner overhead. New production job durations are not measured yet.

Prior production builders took 98.04 seconds / 1,434,812 KiB and 91.79 seconds / 1,434,256 KiB. Runner/thread settings and startup weights differ, so the local result cannot be treated as a percentage improvement over those production references. Use the paired same-environment comparison above.

Removing the daily Worker deploy avoids its previously measured 53–59-second job (26.5–29.5 elapsed minutes over 30 refreshes). A code-only release avoids the previously measured 168–177-second snapshot job and 13,154 KV writes. Relevant releases now have two independent validation paths, so net release-runner savings need production measurements.

Full daily publication remains approximately 394,620 KV writes for 30 refreshes, before manual runs. There is no daily KV-write or new storage saving in phase 1. No measured cost reason supports moving to GCP, AWS, Railway or Fly.io now. Stop at this bounded phase and remeasure with real durable ingestion before considering persistent models or incremental publication.

## Dense-metro autoresearch harness — 2026-10-11

The previous `bash autoresearch.sh` entrypoint measured dense publication;
the current entrypoint selects the tile-loader workload documented below.
The Python harness's default mode retains that original workload, pinning all
157 metros and 53,799 bounded res-9 cells in
`scripts/autoresearch_coverage.json` and performing three full dense snapshots
with cold prediction caches, real seeded synthetic models in a temporary
directory, res-7/8/9 LOD publication, per-cell shards and release twins. It
omits the optional legacy monolithic cell key, national input and Bay Area
context. It does not ingest municipal feeds or publish to Cloudflare.

The primary metric, `snapshot_ms`, is median build time excluding model
initialization and correctness verification. Secondary metrics report model
initialization, process-lifetime peak RSS, bulk/manifest/res-9 tile bytes,
metro/cell counts, and `client_parse_merge_ms`: Bun CPU time for parsing the
exported tiles and executing the shipped dashboard's `mergeTilePayload`.
The client benchmark includes repeated tile loads and validates deduplication;
it is not browser rendering, network latency, or a Core Web Vitals measurement.

Network connections are rejected in the Python workload; random seeds,
thread settings, CPU inference provider and publication metadata clock are
fixed. Coverage, cell shards, percentile bounds and all LOD indexes are checked.
Logical predictions, SHAP, geometry, tiles, catalogs and catalysts must match
across trials and the pinned `scripts/autoresearch_semantic.sha256`, excluding
only measured inference latency. Bulk byte counts retain latency-width noise.
Harness and pinned fixtures are immutable during optimization; coverage or
schema changes require an explicit new baseline. The historical measurements
above use a different workload and are not directly comparable.

### Optimization results

The 20-run segment retained changes in `snapshot_builder.py`, `publication.py`
and `serving/engine.py`; during that segment, dashboard source and benchmark workload remained
unchanged. Each registered artifact is serialized once for both disk and KV.
Publication latency is normalized during JSON decoding, and the canonical
encoder rejects non-finite values without a separate recursive traversal.
Identical raw publication values share canonicalization and hashing.
Float-only prediction/SHAP caches return detached dictionary copies, and scalar
feature validation avoids NumPy allocations. Dense-grid metadata is normalized
once per submarket per build. Ordered cell inference avoids per-cell futures
and contention on the caches. Bulk staging is released before planning objects;
compact bulk separators remove exactly 447,371 transport whitespace bytes at
this fixed key count without changing the embedded logical payload strings.

| Metric | Official baseline, run 1 | Final verification, run 20 |
|---|---:|---:|
| Snapshot median, ms | 18,400.440 | 12,606.354 |
| Client parse/merge median, ms | 58.564 | 82.694 |
| Process-lifetime peak RSS, MiB | 2,976.652 | 2,983.828 |

The final verification is 31.5% faster for the snapshot workload. The best
retained observation was 11,957.576 ms in run 17; another unchanged-code
replication measured 12,165.995 ms in run 19. All benchmark runs matched the
pinned semantic fingerprint and retained 157 metros, 53,799 cells and all
three metro LOD levels. No new city was registered and nothing was deployed.

Client timing was worse in the final observation despite unchanged dashboard
code; no web-rendering or client-speed improvement is established. Peak RSS
did not improve. These measurements do not establish live ingestion throughput,
cloud billing savings, production latency or model quality. Serial inference
is beneficial for this repeated-vector workload; mostly-unique production
vectors require a separate measurement before generalizing the result.

The targeted engine-cache, publication, publisher, snapshot export, metrics,
reach and client contract suites passed. The harness exercised full real-model
publication repeatedly; report-only publication IDs, legacy-cell compatibility,
national inputs and optional context remain covered by the contract suites.

### Production publication cutover

The 2026-10-11 scheduled refresh failed before uploading because its legacy
`cells/index` value was 36,446,037 bytes, above both the 20 MiB build budget and
the 25 MiB KV hard limit. The production workflow now passes
`--skip-legacy-cells`: every `cells/{h3}` shard and its release twin remains,
but the obsolete monolithic value is omitted. The deployed reader checks the
per-cell shard first. Size guards and required national coverage are unchanged.

The first corrected refresh built successfully but Wrangler could not read the
whole bulk file: Node rejected strings above `0x1fffffe8` characters before any
KV upload. Both legacy/release-twin and content-addressed uploads now use
`scripts/upload_snapshot_bulk.py`, staging files capped at 10,000 entries and
50 MiB before invoking Wrangler. The promotion pointer is isolated in the final
file and is never uploaded after a data-batch failure. `--dry-run` stages and
validates the same batches without remote writes. The builder and upload guards
remain enabled; no payload, metro, or required national layer is dropped.

## Tile loading autoresearch harness — 2026-10-11

`bash autoresearch.sh` now selects `--tile-loading` on the existing offline
snapshot harness. It prepares one fixed, semantically verified 157-metro dense
snapshot outside the primary timer; running the Python harness without this
flag retains the three-build backend workload.

`scripts/autoresearch_tile_loader.ts` executes the shipped dashboard's queue,
JSON parsing, H3 merge, LOD staging, and GeoJSON source preparation. Each metro
gets a fresh loader and a fixed sequence of resolutions 7, 8, 9, 9, 7: initial
load, refinement, a cached repeat view, and a return to the coarse view. Parent
inventories come from the published manifest, and distance sorting uses real
H3 centroids and metro camera centers. Every final source submission must retain
all expected cells, properties, and geometry. Unexpected retries fail the run.

The primary `tile_load_cpu_ms` is the median of five complete 785-step
traversals after one warmup. VM construction, file reads, model initialization,
snapshot generation, and semantic verification are excluded from this timer.
Request count, response bytes, and source-submission count are secondary
metrics. HTTP responses are replayed from the generated snapshot without live
network access; the MapLibre boundary captures source data rather than invoking
a GPU. Animations are disabled using the shipped reduced-motion path. This is
a client CPU benchmark, not browser paint, network latency, or Core Web Vitals.

The replay freezes each feature's measured `inference_latency_ms` telemetry
to zero before response serialization. Prediction values and geometry are
unchanged; this removes build-speed-dependent digit widths from the timed JSON
workload. Raw snapshot preparation byte metrics may still vary with telemetry.

Two consecutive invocations exited successfully with identical replay bytes
(104,923,069), requests (629), source submissions (628), and tile workload
SHA-256 `d8052e4a05b73106987293093087d2666a02bb04e54ab2b7fe4855c8b9be7fc9`.
The harness pins this checksum and rejects input drift before timing.
