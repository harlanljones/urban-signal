# Daily GitHub Actions backend: staged design

Date: 2026-10-03. Status: proposed; planning only. Daily dashboard freshness is approved. Cloudflare web applications and Worker HTTP/MCP read APIs remain the serving tier.

## Recommendation

Ship a small first phase: measure the stages, separate code release from daily data refresh, and reuse predictions within each snapshot build. Evaluate the result before funding durable model bundles or incremental publication. Moving real municipal ingestion off continuously running infrastructure is a separate migration with a shadow pilot, not an incidental change to the snapshot job.

Do not add a new database, queue, container platform, or permanent service for phase 1. Do not start another daily retraining job: the present boot-time models are synthetic/default baselines, not evidence of a production-trained model pipeline.

## Verified baseline

Inspected local commit `28aca91b2f552ce406c59d801a7248806fcf21e6`; parent verified its code tree matches merged main `bc2f10b2ac718dbe0212aa60f3aabb9caa3d9ca1` (PR 123). The previous and fresh production resource artifacts report:

| Measurement | Previous run | Fresh merged-main run 37143313867 |
|---|---:|---:|
| Builder elapsed time (`/usr/bin/time`) | 98.04 seconds | 91.79 seconds |
| Peak resident memory | 1,434,812 KiB / 1,401.18 MiB | 1,434,256 KiB / 1,400.64 MiB |
| Planned KV entries | 13,154 | 13,154 |
| Unique cell predictions | 11,185 | 11,185 |
| Grid tiles (legacy res-9 index) | not extracted | 504 |
| Bulk JSON bytes | 72,454,303 / 69.10 MiB | 72,517,302 / 69.16 MiB |
| 30 daily builder executions, arithmetic projection | 49.02 minutes | 45.90 minutes |
| 30 full daily uploads, arithmetic projection | 394,620 planned writes; 2.17 GB payload | 394,620 planned writes; 2.18 GB payload |

The approximately 110-second interval between logged build-step timestamps includes overhead and is not the measured builder duration. Build projections exclude environment setup, validation, upload, artifacts, deployment, retries, other workflows, and runner billing rules. Planned writes do not prove successful remote writes. No optimization savings have been measured yet. The [fresh merged-main verification run](https://github.com/harlanljones/urban-signal/actions/runs/37143313867) completed all jobs; production `/health` reported healthy with `snapshot_created=2026-10-03T18:16:30.747218+00:00`. Its resource artifact is `11281740729`, compared with prior artifact `11280524134`. These are two runs of the same code tree; the duration difference is run variability, not an optimization result. Standard hosted Actions runners for this public repository may incur no runner charge under GitHub eligibility rules, so report minutes and avoid invented dollar savings. Cloudflare usage/pricing must be checked before converting planned writes to money.

### What executes today

- `.github/workflows/batch-push.yml` validates push/PR/scheduled/manual runs. Non-PR runs rebuild every city, upload the complete KV bulk file, then deploy the dashboard Worker. Nightly `06:00 UTC` scheduling already exists. Matching UI/API/script pushes also trigger the expensive refresh.
- `apps/api/src/export/snapshot_builder.py` calls router endpoints with synthetic features from submarket metadata. Grid inference excludes SHAP, catalysts include it, and a second per-cell pass repeats prediction with SHAP. The second pass is already threaded (up to eight workers); concurrency is not a new optimization.
- `apps/api/src/serving/engine.py::_init_models` fits three synthetic LightGBM quantiles, creates default PyTorch DCN/ST-GNN models, exports ONNX, and opens sessions every engine initialization. LightGBM's training data seed is fixed; neural weight initialization is not explicitly seeded. A populated ONNX directory currently does not bypass initialization.
- Neighboring grid cells share feature vectors. Catalyst vectors can differ from grid vectors at the same H3 address. Caching by cell alone would change predictions. Responses contain variable `inference_latency_ms`, which also prevents byte-identical outputs.
- Percentiles are recomputed over all exported metros, separately for resolutions 9, 8, and 7. A change in one city can alter national percentiles and serialized tiles in other cities.
- Weekly `.github/workflows/bay-area-context.yml` already separates slow context acquisition from daily serving. The daily workflow consumes its latest successful artifact; context download is optional. The inspected production command does not pass `--national-dir`, `--require-national`, or `--dense-metro`; preserve those choices in the optimization benchmark.
- `apps/dashboard/src/index.ts` and `snapshot.ts` read mutable logical KV keys, with isolate caches and legacy cell fallback. A bulk upload has no multi-key transaction. Registering `manifest` last in a file is not a publication commit guarantee.
- Municipal polling, Kafka consumers, feature aggregation, PostGIS persistence, and alert dispatch are separate code paths. The scheduler saves high watermarks to a local JSON file; snapshot deduplication remains in memory. `SpatialFeaturePipeline` defaults to an in-memory DuckDB database. These are not an end-to-end durable daily pipeline on ephemeral Actions runners.

## Global constraints

- Daily dashboard freshness remains the target; run the scheduled refresh at `06:00 UTC` and surface the last successful snapshot time.
- Preserve Cloudflare web hosting and existing Worker HTTP/MCP endpoint paths, response fields, filtering, H3 coverage, SHAP availability, and percentile semantics.
- Phase 1 introduces no new always-on service or storage service.
- Preserve Python `3.12` in GitHub Actions and the repository Bun/Node toolchain.
- Keep the complete res-9/res-8/res-7 ranking pass over the full selected city population.
- Synthetic/default model outputs must remain identified as synthetic/default; optimization is not a model-quality upgrade.
- Do not retire streaming alerts or infrastructure until dependencies, ownership, retained data, and replacement behavior are verified.
- No implementation, production publication, deployment, infrastructure deletion, or commit is authorized by this planning deliverable alone.

## Phase 1: bounded, measurable changes

### Instrument costs and correctness

Add `build/snapshot-metrics.json` outside `dist/` (never upload it to KV). Record schema version, commit/tree identity, model mode, city/cell counts, elapsed seconds for model initialization, city inference, cell inference/SHAP, ranking/LOD, serialization, and total; record inference/SHAP call counts, unique normalized vectors, cache hits, and bulk/key bytes by family. Keep `/usr/bin/time` as the peak RSS authority. Counters used by the threaded pass must be thread-safe.

Measure complete job durations from Actions independently of builder stage timers. Store successful upload key/byte totals only after upload exit success, and label them separately from plans. Expose actual source/context age independently of snapshot generation time. Retain seven days of benchmark artifacts initially, matching existing retention.

Benchmark uncached and cached paths using the same model instances/weights, source files, city set, build timestamp, CPU settings, and context artifact. Compare every semantic value, key, coverage count, and percentile; ignore only measured latency and run metadata explicitly listed by the comparator. Use three warm and three cold runs when evaluating an optimization, not repeated daily experiments. Record setup time and model initialization separately. No percentage speedup is promised; a 25% builder reduction is a useful target, not a reason to expand scope if the avoided workflows already meet the user's goal.

### Separate code validation/release from data refresh

Keep the existing `batch-push-deploy` validation check name for branch protection compatibility. Change its snapshot job to scheduled or explicit `workflow_dispatch` only; remove its daily Worker deployment job. Keep validation on push/PR and a lightweight Python snapshot/interlock gate on daily/manual publication. Move dashboard code deployment into `.github/workflows/dashboard-deploy.yml`, after its own required web/interlock checks, with no dependency on a snapshot job.

Release triggers include Worker/dashboard files, `serving/dashboard.py`, registry/coverage files that generate dashboard catalogs, the dashboard export script, shared web packages, root package/lock/toolchain files, and the deployment workflow. Validate all code changes normally. Ordinary model/feed/exporter changes enter the next daily snapshot; a manual refresh is available for an immediate correction. New cities and incompatible snapshot schema changes are coordinated releases: compatible reader first, manual snapshot second, visibility verification third. UI releases continue to use the last successful snapshot. Do not silently publish an unvalidated schema.

Keep one production snapshot concurrency group with `cancel-in-progress: false`; use an independent dashboard deployment group. Scope Cloudflare secrets to publication/deployment jobs, never PR validation. Retain `workflow_dispatch` from main for recovery, and reject production publication from other refs. Preserve all existing zoom, interlock, web, and source tests in the appropriate jobs.

### Reuse inference inside one build

Refactor the engine internally into feature-only prediction, feature-only explanation, and per-cell assembly. Keep `predict_cell_features(h3_index, feature_dict, include_shap=True)` behavior and positional compatibility. Add an opt-in constructor parameter `cache_predictions=False`; the snapshot builder enables it by default and exposes `--no-prediction-cache` as a comparison/rollback switch. Live serving defaults remain unchanged.

Use normalized values in the exact ordered `FEATURE_COLUMNS` vector as the cache key. Defaults and float conversion match the existing engine; reject non-finite values before snapshot publication. Model sessions, feature semantics, and LIMS threshold are immutable during a cache-enabled engine lifetime. Keep a bounded LRU of 16,384 vectors for scores and explanations independently; serialize misses with locks to avoid duplicate work in the existing thread pool. Cache only cell-independent values, never H3, centroid, resolution, caller metadata, latency, or mutable response dictionaries. Return copies. SHAP is computed once when first requested, without repeating already-cached prediction. Calls without SHAP remain without explanations. Do not derive catalysts by copying grid predictions.

This removes redundant LightGBM/ONNX work and repeated SHAP on identical vectors without changing model weights or publishing fewer keys. Avoid matrix-batching the ST-GNN in this phase: its node axis and graph semantics require separate equivalence work. Avoid increasing thread counts before measuring oversubscription with LightGBM/ONNX internal threads.

### Phase 1 acceptance and rollback

Unit tests establish cached/uncached equality, score/SHAP miss counts, distinct catalyst vectors, correct per-cell identity, thread safety, and bounded caches. Existing snapshot, percentile, coverage, Worker HTTP/MCP, and zoom regressions pass. Required CI/CD preflight passes in a complete environment. Compare full outputs on a fixed input; rerun production only through the release process after implementation review.

A prevented code-only refresh avoids one full upload (baseline 13,154 planned writes and 69.10 MiB) and approximately one 92–98-second builder execution plus measured setup/upload/deployment time. Daily refreshes still write all keys in this phase. Inference reuse savings remain unknown until measured. No idle-infrastructure dollar savings are attributable to this phase.

Rollback inference with `--no-prediction-cache`; revert the workflow split if release triggers fail, retaining manual refresh. No data migration is required.

## Phase 2: optional model bundles and safe incremental publication

Start only after phase 1 measurements. These are separate reviewable changes; they are not necessary to deliver the cheap phase.

### Deterministic model bundles

Create a versioned bundle containing three LightGBM text models, both ONNX files, and a manifest with artifact SHA-256s, ordered features, synthetic/trained provenance, architecture/config hashes, exact relevant dependency versions, and construction seed. Use seed `42` for synthetic NumPy/Torch construction in an isolated RNG context. Freeze supported CPU inference dependencies in a constraints file. Cold construction and verified bundle loading must return equal published predictions. A corrupt/mismatched derived cache rebuilds a complete bundle; never mix files from versions. A trained bundle is explicit and immutable; no silent fallback to synthetic weights when a trained bundle was requested.

Actions cache may accelerate rebuilding a deterministic derived bundle, but is not its provenance authority or a durable ingestion store. Scope cache keys to OS/architecture/Python, relevant pinned dependencies, feature schema, model/config/source digest. No broad restore key may load unchecked weights. Moving from today's random neural defaults to a seeded bundle changes outputs; assess and document that synthetic baseline revision separately from cache equivalence. Actual retraining remains a separate manual or justified cadence job using validated data and the existing `models/retraining_job.py` boundary.

### Hash complete outputs, then publish a version

First use hashes in report-only mode; full rebuilding is affordable at today's measured scale. Canonical payload serialization sorts object keys, preserves array order, rejects NaN, and retains data timestamps. Volatile inference timings leave persisted payload semantics: retain the numeric field as `0.0` for precomputed results and document that sentinel; real timing stays in build metrics. `generated_at` remains truthful in the manifest; stable data objects retain their own source/as-of timestamp rather than a freshly stamped build clock. Any time-dependent feature includes the UTC as-of day in its input identity. Never discard a date just to improve cache hits.

Use content-addressed KV objects `objects/<sha256>`, immutable release manifests `releases/<snapshot_id>`, and one small `snapshot/current` pointer carrying current and previous release IDs. A release manifest maps every logical key to object hash/byte size, excludes itself from that mapping, and records `model_id`, `feature_schema_version`, `as_of`, source revisions, and parent version. Hash the canonical release body to derive `snapshot_id`. Changed cells do not imply only changed tiles: always rerank all populations and hash the resulting full outputs. A removed logical key is absent in the new manifest, even when old immutable bytes remain stored.

Upload missing objects in retryable chunks, verify acknowledged write counts and checksums through the publication tool, write the immutable manifest, then update the pointer separately. Discover reused objects from the last successfully published manifest and explicit remote existence checks after any cache/state uncertainty. A report or local Actions cache is never proof that remote data exists. Do not write new mutable logical keys during a versioned publish.

**Consistency limit:** Workers KV is eventually consistent. A pointer update is a logical commit, not a globally atomic multi-key transaction; acknowledgement or a single read probe cannot prove every edge has every object. Resolve one release per request, key isolate caches by physical object hash, and fetch all dependencies from that release. If an unpinned request cannot obtain its complete data, restart the entire request against the previous release. Pinned requests return retryable `503` on missing/corrupt release data rather than mixing versions. A cold isolate with no readable version also returns `503`.

Expose an additive snapshot ID in the manifest/response header and accept `snapshot=<id>` on related reads. Update the dashboard to pin each map load/refresh to its manifest ID, keep the previous rendered view while retrying an unavailable release, and swap only after the required new tiles load. HTTP and MCP share the resolver, including batch tool calls. Preserve legacy mutable-key reads only when the version pointer is absent during migration, never as a per-object fallback inside a versioned release. The legacy reader remains the rollback target until the new publisher and reader pass failure injection tests.

Do not garbage-collect immutable data in the initial rollout. Later retain current/previous and at least seven days of release manifests, mark every referenced object, and delete only unreferenced objects older than 30 days with a dry-run report first. Monitor storage growth before enabling this maintenance. Pointer rollback selects an existing complete release without recomputing. Reverting to a legacy Worker requires a complete old-format bulk snapshot; retain that artifact during the migration window.

This can reduce stable-day writes sharply, but metadata, time windows, model revisions, and global ranks determine the true number. Report full-key count, reused objects, changed objects, metadata writes, upload bytes, KV read amplification, and added storage. Do not promise zero daily writes or a fixed savings percentage.

## Phase 3: separately scoped durable ingestion pilot

The goal is eventually Actions → durable source state/raw partitions → daily features → snapshot → Cloudflare reads. First inventory actual running infrastructure, consumers, credentials, costs, retention obligations, and alert users. Repository code alone cannot establish which services are deployed or idle. Keep weekly/annual source-specific acquisition cadences; daily freshness does not mean refetching slow national data daily.

Prototype one enabled NYC permit feed in shadow mode. Reuse its existing registry metadata, source client, normalizer, and typed watermark helpers, but add an explicit file/object-store sink rather than constructing every Kafka-backed producer. Persist normalized raw partitions and feed checkpoints in a durable R2/S3-compatible bucket; local DuckDB is rebuildable from those objects. No Actions cache/artifact is authoritative. A checkpoint records source/config version, committed object hashes, cursor `(typed watermark, stable source ID)`, source revision, and source observation time.

Write immutable raw pages and a complete ingest manifest before advancing the checkpoint; use conditional checkpoint writes and one writer per feed. An interruption after raw writes replays idempotently; an interruption before durable raw writes cannot advance the cursor. Upsert by `(city, feed, source ID)` with a normalized-content hash, preserving corrections and old/new cell assignments. Use overlap polling only when the source supports meaningful update timestamps; sources without update/delete guarantees need complete periodic reconciliation. Do not claim all historic corrections are captured by an arbitrary overlap window. Equal timestamps must page by stable ID and never skip a saturated watermark boundary. Treat truncated snapshots as incomplete and never infer deletions from them.

Aggregate with an explicit UTC `as_of` and durable raw history sufficient for current 60/90/180/360-day windows and capex decay. Dirty cells include inserts, updates, removals, both sides of moved coordinates, time-window expirations, and decay changes even on a no-new-record day. Initially recompute the small pilot fully each day and compare it with incremental results; correctness precedes dirty-set optimization. City-scoped raw identities need isolation because current DuckDB tables primarily key records by source ID alone. Model/schema/source revisions invalidate affected results. Recompute national percentiles over the complete resulting population.

Run at least seven successful daily shadow cycles plus frozen-time boundary, replay, interruption, and late-correction tests. Validate coverage, source freshness, feature parity against full rebuilds, storage growth, and API data provenance. Do not replace synthetic map inputs with a partly populated feed and call it feature parity; switching to real inputs changes the product/model data distribution and is a separate rollout decision. Suppress outbound alerts in the pilot.

Streaming alerts remain separate. Daily dashboard approval does not waive sub-day alerts. Only after inventory and parity evidence should a follow-on plan retire each unused poller, broker/consumer, feature service, or database. Take restorable state exports, record dependencies, and verify cloud billing after shutdown; retain or separately redesign alert delivery with durable deduplication/outbox semantics. No infrastructure deletion is included in this plan.

## Delivery gates

1. Phase 1 is the recommended implementation scope now. Stop and report measured cost/latency improvements.
2. Model persistence is justified by measured initialization cost and reproducibility needs; incremental publication is justified by observed write cost and reuse ratio. Review them separately.
3. Durable ingestion requires its own implementation plan after the infrastructure/feed inventory. The pilot design above is a boundary and acceptance contract, not a claim that migration is implemented or ready for all cities.
