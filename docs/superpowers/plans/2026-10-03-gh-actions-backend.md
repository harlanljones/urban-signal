# Daily GitHub Actions Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce repeated daily snapshot compute and publication work while retaining Cloudflare web hosting and Worker HTTP/MCP read APIs.

**Architecture:** First instrument the existing batch job, decouple daily data publication from code releases, and memoize cell-independent inference within each build. Keep global ranking and full daily publication intact. Treat deterministic model bundles and versioned incremental publication as optional later releases, and durable municipal ingestion as a separately scoped migration.

**Tech Stack:** GitHub Actions, Python 3.12, LightGBM, PyTorch/ONNX Runtime, SHAP, H3, Polars, Bun/TypeScript, Cloudflare Workers/KV; optional R2/S3-compatible durable storage only for a later ingestion pilot.

**Spec:** `docs/superpowers/specs/2026-10-03-gh-actions-backend-design.md`

## Execution status — 2026-10-10

Tasks 1–4 were implemented and measured on 2026-10-03. See [results and limits](../../research/gh-actions-backend-benchmark-2026-10-03.md). Tasks 5–8 (deterministic bundles, report-only publication plans, version-pinned reads, and pointer-last publication) are now implemented. Task 9 remains the separate ingestion pilot in `docs/superpowers/specs/daily-ingestion-pilot.md`. The seeded bundle is a synthetic baseline revision and is not a trained model.

## Global Constraints

- Daily dashboard freshness remains the target; run the scheduled refresh at `06:00 UTC` and surface the last successful snapshot time.
- Preserve Cloudflare web hosting and existing Worker HTTP/MCP endpoint paths, response fields, filtering, H3 coverage, SHAP availability, and percentile semantics.
- Phase 1 introduces no new always-on service or storage service.
- Preserve Python `3.12` in GitHub Actions and the repository Bun/Node toolchain.
- Keep the complete res-9/res-8/res-7 ranking pass over the full selected city population.
- Synthetic/default model outputs must remain identified as synthetic/default; optimization is not a model-quality upgrade.
- Do not retire streaming alerts or infrastructure until dependencies, ownership, retained data, and replacement behavior are verified.
- No implementation, production publication, deployment, infrastructure deletion, or commit is authorized by this planning deliverable alone.

## Review Focus

- Same H3 with different catalyst/grid vectors must produce the correct separate scores: Task 3 tests full vector keys and no aliasing.
- Overlapping SHAP/non-SHAP thread-pool requests must compute each core/explanation once and preserve each response's identity: Task 3 tests races, upgrades, and eviction.
- UI-only changes and manually dispatched non-main refs must not publish daily data accidentally: Task 2 tests workflow event/ref cases and coordinated city releases.
- Missing or stale context and advancing time must not become false cache hits or false freshness claims: Tasks 1, 4, and 6 test metadata and as-of invalidation.
- Partial uploads, cold edge caches, deleted keys, and stale pointers must never combine releases: Tasks 6–8 test failure injection and rollback; KV global atomicity is explicitly not claimed.

---

## Scope, ordering, and file boundaries

**Execute Tasks 1–4 as the first release after approval to implement.** They are sequential because instrumentation and the engine interface define the benchmark. Use native inline execution for this small phase unless the user chooses otherwise; one final independent review is proportionate. No new dependencies or shared-spine edits should be needed. Claim files before implementation; if a spine edit becomes necessary, follow `docs/agents/parallel-streams.md` and its interlock gate.

Tasks 5–8 are optional subsequent releases, not automatic scope expansion. Task 9 is an inventory/spec deliverable that precedes a separate ingestion implementation plan. Do not charge a backend rewrite to a roughly 92–98-second builder optimization.

Existing responsibilities remain: engine owns model execution; snapshot builder owns assembly/ranking; Worker query modules own read semantics; workflows own cadence and release triggers. New modules are narrowly scoped: build metrics, model bundle validation, canonical publication planning, and a Worker release resolver. Avoid a general pipeline framework.

Run commands from repository root unless otherwise stated. Examples use `apps/api/.venv/bin/python`; CI uses its configured `.venv/bin/python`. Existing dependency installation is required. Commits below are execution milestones, not actions to perform during planning.

### Task 1: Establish stage measurements and a repeatable output comparator

**Files:**
- Create `apps/api/src/export/snapshot_metrics.py`, `scripts/benchmark_snapshot.py`, `apps/api/tests/unit/test_snapshot_metrics.py`.
- Modify `apps/api/src/export/snapshot_builder.py` (`build_snapshot`, `main`), `.github/workflows/batch-push.yml` (usage summary/artifact steps), `apps/api/tests/unit/test_export_snapshot.py`.

**Interfaces:**
- `SnapshotMetrics.stage(name: str)` returns a context manager; `increment(name: str, count: int = 1) -> None`; `write(path: Path) -> None`. JSON schema `1` uses `durations_seconds`, `counters`, `artifacts`, `provenance` objects; counters are thread-safe.
- Extend `build_snapshot(..., metrics: SnapshotMetrics | None = None)` and CLI `--metrics-out PATH`. No metrics path means no metrics file. Metrics never become a KV key.
- Benchmark CLI: `--out PATH --runs 3 --context-dir PATH` (context optional), then Task 3 adds cache modes. Output contains input/commit identities, raw runs, medians, peak RSS observations, and a semantic comparison result.

- [ ] Add failing tests `test_metrics_cover_stages_without_kv_keys`, `test_counters_are_thread_safe`, `test_missing_context_is_explicit`, `test_comparator_detects_prediction_rank_or_coverage_change`. Assert every required stage exists, 100 concurrent increments yield 100, no metrics entry enters `kv-bulk.json`, missing context records absence, and altered numeric predictions/ranks/keys fail equality.
- [ ] Run `PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest -q apps/api/tests/unit/test_snapshot_metrics.py apps/api/tests/unit/test_export_snapshot.py`; confirm new assertions fail before implementation.
- [ ] Implement metrics around model initialization, city inference, cell inference/SHAP, ranking/LOD, serialization, and total. Record key/byte counts by logical prefix, optional context revision/age, and mode `synthetic-default`. Emit summaries in `finally` on failure with explicit incomplete status; do not call failures successful builds.
- [ ] Implement benchmark input freezing and recursive comparison. Ignore only `inference_latency_ms`, manifest/index generation clock fields, and benchmark run metadata; retain source dates, features, predictions, ranks, SHAP, array order, and all key sets. Use the same initialized weights for paired output comparison; do not compare independently randomized neural engines.
- [ ] Update Actions summary/artifacts to preserve `build/snapshot-metrics.json` alongside resources, retaining seven days. Distinguish planned writes from successful upload counts. Run the targeted tests; inspect a small-city dry build and its JSON metrics.
- [ ] Commit as `chore: measure snapshot stages and output equivalence`.

### Task 2: Separate daily publication from dashboard releases

**Files:**
- Modify `.github/workflows/batch-push.yml`.
- Create `.github/workflows/dashboard-deploy.yml`, `apps/api/tests/unit/test_workflow_routing.py`.

**Interfaces:**
- Existing workflow/check name remains `batch-push-deploy` / `validate`; snapshot only accepts `schedule` or `workflow_dispatch` on `refs/heads/main`.
- New `dashboard-deploy` runs on relevant main pushes/manual main dispatch, validates then deploys static assets/Worker without a snapshot dependency. Both workflows use separate concurrency groups; production snapshot cancellation remains disabled.

- [ ] Add failing routing tests covering PR, ordinary push, scheduled main, manual main, manual non-main, docs-only change, dashboard-only change, and a registry/catalog change. Assert only schedule/manual main can mutate snapshot KV; dashboard release includes zoom/interlock/web checks and can use an existing snapshot; no Cloudflare secrets appear in PR validation jobs. Use PyYAML's safe parsing with a loader that does not reinterpret the YAML `on` key as a boolean.
- [ ] Run `PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest -q apps/api/tests/unit/test_workflow_routing.py`; confirm failures.
- [ ] Move deployment into its own workflow. Retain existing push/PR validation tests and branch-protection check name. Use Python snapshot/interlock validation on schedule/manual refresh; keep complete web validation on code releases. Scope secrets to jobs requiring writes. Include release trigger paths `apps/dashboard/**`, `apps/api/src/serving/dashboard.py`, `apps/api/src/spatial/**`, `scripts/export_dashboard.py`, `packages/**`, `package.json`, `bun.lock*`, `turbo.json`, and the deployment workflow.
- [ ] Run routing tests, inspect conditions including transitive skip behavior, then `node --test apps/dashboard/tests/grid-zoom.test.js`. Document compatible-reader-first/manual-refresh ordering for registry or schema changes in the design rollout section.
- [ ] Commit as `ci: decouple daily snapshots from dashboard releases`. After implementation review, verify one UI-only release performs no snapshot build/upload and one manual main refresh performs no Worker deploy. Do not trigger remote runs during planning.

### Task 3: Reuse identical model and SHAP computations per build

**Files:**
- Modify `apps/api/src/serving/engine.py`, `apps/api/src/export/snapshot_builder.py`, `scripts/benchmark_snapshot.py`.
- Create `apps/api/tests/unit/test_engine_prediction_cache.py`.
- Extend `apps/api/tests/unit/test_export_snapshot.py` and `apps/api/tests/unit/test_engine_quantile_calibration.py` if their fixtures need the added optional interface.

**Interfaces:**
- Extend `MultiHorizonInferenceEngine.__init__(model_dir: str | None = None, *, cache_predictions: bool = False, metrics: SnapshotMetrics | None = None)`.
- Internal `_feature_key(feature_dict: dict[str, Any]) -> tuple[float, ...]`, `_predict_values(vector: tuple[float, ...]) -> dict[str, float]`, `_explain_values(vector: tuple[float, ...]) -> dict[str, float]` separate model values from existing per-cell assembly.
- Preserve `predict_cell_features(h3_index, feature_dict, include_shap=True)` and existing injected StubEngine support. `build_snapshot(..., cache_predictions: bool = True)` passes the option only when constructing its own engine; document that an injected engine owns its configuration. CLI `--no-prediction-cache` disables construction-time caching.

- [ ] Add failing tests for repeated vectors across two H3 cells (one model execution, distinct H3/centroids); same H3 with changed capex/LIMS (two executions); default/missing feature equivalence; SHAP false→true upgrade (one prediction and one explanation); no returned-dict aliasing; LRU bound 16,384; and non-finite snapshot inputs rejected.
- [ ] Add a barrier-based concurrent test with 16 same-vector callers, mixed SHAP flags: exactly one core computation and one explanation, each returned SHAP flag respected. Add a test comparing cached/uncached all fields except measured latency on fixed real model weights; keep tiny fixtures for runtime.
- [ ] Run `PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest -q apps/api/tests/unit/test_engine_prediction_cache.py`; confirm behavior fails before refactoring.
- [ ] Implement ordered 12-feature normalization, separate bounded LRU maps with miss locks, defensive result copies, and live per-cell assembly. Keep model/config immutable for the engine lifetime. Increment prediction/SHAP execution and cache counters at the work boundary, not at the wrapper call. Do not change rounding, fallback LIMS computation, threshold behavior, or model initialization in this task.
- [ ] Enable only snapshot-created engine caches by default. Extend benchmark with `--cache-mode off|on|compare`; compare paired outputs using the same weights, then measure three warm/cold runs for each configuration. Existing thread pool stays bounded as before.
- [ ] Run cache, quantile calibration, snapshot export, snapshot reach, and interlock tests. Require semantic equality and reduced execution counts; report runtime/memory rather than asserting timing in unit tests.
- [ ] Commit as `perf: reuse snapshot prediction and explanation vectors`.

### Task 4: Validate and close the bounded phase

**Files:**
- Create `docs/research/gh-actions-backend-benchmark-2026-10-03.md` (use actual validation date if execution occurs later).
- Modify only phase-1 files if verification discovers a defect.

**Interfaces:**
- Consumes metrics schema/comparator and workflow routing from Tasks 1–3; produces a measured recommendation to stop or proceed to optional work.

- [ ] Run a complete fixed-input benchmark with baseline cache disabled and optimized cache enabled, three cold/warm runs each. Use all production cities, identical context artifact, current production CLI flags, CPU settings, and model weights. Record semantic equality, execution counts, total/stage medians, peak RSS, output key counts and bytes; run a no-context case as a supported fallback.
- [ ] Run `PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest -q apps/api/tests/unit/test_engine_prediction_cache.py apps/api/tests/unit/test_engine_quantile_calibration.py apps/api/tests/unit/test_export_snapshot.py apps/api/tests/unit/test_snapshot_reach.py apps/api/tests/unit/test_workflow_routing.py`, `bun run --cwd apps/dashboard test`, `node --test apps/dashboard/tests/grid-zoom.test.js`, `bun run build`, `bun run typecheck`, `bun run lint`, and `python3 scripts/verify_cicd_preflight.py`. Fix attributable failures; report environment limitations separately.
- [ ] Record measured savings against the prior 98.04-second / 1,434,812-KiB and fresh 91.79-second / 1,434,256-KiB references, and the same-environment uncached benchmark; runner differences make those separate comparisons. Do not attribute planned KV reductions to phase 1, which still uploads every daily key. Compute savings per avoided code-only refresh separately.
- [ ] Verify freshness reporting distinguishes last successful generated snapshot from stale/missing source context. Record rollback command `--no-prediction-cache` and workflow revert procedure.
- [ ] Commit benchmark evidence as `docs: record daily backend optimization results`. Obtain implementation review before production release. Stop here unless optional work is separately selected.

## Optional release A: deterministic model persistence

### Task 5: Build and validate reusable model bundles

**Files:**
- Create `apps/api/src/models/bundle.py`, `apps/api/tests/unit/test_model_bundle.py`, `apps/api/constraints/snapshot-models.txt`.
- Modify `apps/api/src/serving/engine.py`, `apps/api/src/models/quantile_lgbm.py` (explicit training seed/config), `.github/workflows/batch-push.yml`.

**Interfaces:**
- `bundle_fingerprint() -> str` hashes model code/config, ordered features, exact relevant dependency versions, OS/architecture/Python, seed `42`.
- `ensure_synthetic_bundle(root: Path) -> Path` returns a verified immutable bundle directory, constructing atomically on a miss.
- `load_bundle(path: Path) -> ModelBundle` validates hashes/schema/provenance before exposing three LightGBM boosters and two ONNX paths. `ModelBundle` is a dataclass with `model_id: str`, `provenance: str`, `quantiles: dict[float, lgb.Booster]`, `dcn_path: Path`, `gnn_path: Path`.

- [ ] Add failing tests for cold/warm equality, partial/corrupt bundles, changed ordered features/dependency fingerprint/seed, concurrent construction, and trained-bundle rejection without synthetic fallback. Assert loading a valid bundle invokes neither training nor ONNX export. Freeze actual resolved supported CPU model dependencies into the constraints file rather than inventing version pins in the plan.
- [ ] Run `PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest -q apps/api/tests/unit/test_model_bundle.py`; confirm failures.
- [ ] Implement synthetic construction under isolated NumPy/Torch seed `42`, three `Booster.save_model` text artifacts, ONNX exports, final manifest checksums, and temp-directory rename. Refit the SHAP explainer against the loaded median booster. Keep provenance explicit. Treat this seeded neural baseline revision separately from the cache performance change in review.
- [ ] Restore/save only derived bundle caches using exact fingerprints; validate on every restore and rebuild invalid synthetic caches. Benchmark cold/warm model initialization and full-output equivalence; run quantile/cache/snapshot tests and full preflight.
- [ ] Commit as `perf: load validated deterministic model bundles`. Release only after reviewing synthetic baseline output changes. Retain uncached bundle reconstruction as rollback; do not enable automatic trained-model retraining.

## Optional release B: incremental immutable publication

### Task 6: Produce content-addressed publication plans in report-only mode

**Files:**
- Create `apps/api/src/export/publication.py`, `apps/api/tests/unit/test_publication.py`.
- Modify `apps/api/src/export/snapshot_builder.py` and metrics/benchmark modules from Task 1.

**Interfaces:**
- `canonical_bytes(payload: Any) -> bytes` uses sorted object keys, compact JSON, preserved array order, and rejects non-finite numbers.
- `plan_publication(entries: list[dict[str, str]], previous: dict[str, Any] | None, metadata: dict[str, Any]) -> PublicationPlan` returns a dataclass containing `snapshot_id`, immutable `manifest`, `objects` keyed by SHA-256, and `reuse_candidates`. Candidates require publisher verification; they are not proven remote objects.
- Manifest schema `1` records `model_id`, `feature_schema_version`, `as_of`, source revisions, parent release and `keys: {logical_key: {sha256, bytes}}`; it excludes its own logical `manifest` key.

- [ ] Add failing tests for identical stable inputs, changed model/features/context/day, removed keys, NaN rejection, and a two-city change that alters the other city's national percentile at each LOD. Check that time decay/window changes cannot be masked by stable raw-record hashes.
- [ ] Implement canonical serialization and report-only planning. In the planned versioned payload only, use documented `inference_latency_ms: 0.0` for precomputed results and preserve source/as-of timestamps; metadata clocks remain truthful. Keep the live legacy upload unchanged during measurement. Daily input identities include as-of for time-dependent features; full ranking runs unconditionally.
- [ ] Run `PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest -q apps/api/tests/unit/test_publication.py apps/api/tests/unit/test_export_snapshot.py`; run two stable-day and changed-day dry plans. Record reused/changed objects and estimated metadata writes against actual output sizes.
- [ ] Commit as `feat: report content-addressed snapshot publication plans`. Proceed only if the measured reuse/cost justifies additional reader complexity.

### Task 7: Add complete version-pinned Worker reads

**Files:**
- Create `apps/dashboard/src/release.ts`, `apps/dashboard/tests/release.test.ts`.
- Modify `apps/dashboard/src/index.ts`, `apps/dashboard/src/snapshot.ts`, `apps/dashboard/tests/index.test.ts`, `apps/dashboard/tests/snapshot.test.ts`, `apps/api/src/serving/dashboard.py`; regenerate `apps/dashboard/public/index.html` with the export script.

**Interfaces:**
- `resolveRelease(env: Env, requestedId?: string): Promise<ReleaseContext | null>` reads one pointer/manifest; null means no version pointer and permits legacy mode. `ReleaseContext` holds snapshot ID, optional previous ID, and logical key map.
- `readReleaseJson(env: Env, release: ReleaseContext, key: string): Promise<unknown>` checks membership, immutable hash and JSON; unavailable/corrupt data raises a typed `ReleaseUnavailable` error. Never falls back to legacy keys.
- `withRelease<T>(env, requestedId, query: (release: ReleaseContext | null) => Promise<T>): Promise<{value: T; snapshotId: string | null}>` resolves once; an unpinned query retries the whole callback on previous release once; pinned queries surface `503` on release unavailability. No release fallback on legitimate absent logical keys.

- [ ] Add failing tests with current/previous manifests and fake KV propagation gaps. Assert an unpinned multi-key query is entirely old or entirely new; pinned missing objects return `503`; deleted logical keys cannot leak old data; cold/malformed pointers fail closed; cache entries use physical hash; no-pointer fixtures preserve existing HTTP/MCP behavior.
- [ ] Implement resolver and pass one context through every HTTP/MCP query path, including multi-parent grid/national reads, cell batches, global catalyst index, and discovery manifests. Add `x-snapshot-id` plus optional `snapshot=<id>`/MCP snapshot argument. Preserve existing error semantics for unsupported cities and valid missing cells; differentiate those from missing release data.
- [ ] Pin dashboard requests to its manifest snapshot ID, retain the existing view while a refresh is incomplete, and swap on successful complete tile loading. Do not silently retry a pinned tile against another version. Test a pointer change mid-pan/refresh and rollback to previous release; regenerate static HTML.
- [ ] Run `bun run --cwd apps/dashboard test`, dashboard zoom tests, web typecheck/build/lint, snapshot tests, and full preflight. Deploy the compatible reader before switching publishers, after release approval; absent-pointer mode leaves current snapshots readable.
- [ ] Commit as `feat: read complete versioned snapshots at the edge`.

### Task 8: Publish immutable objects and switch the pointer last

**Files:**
- Create `scripts/publish_snapshot.py`, `apps/api/tests/unit/test_publish_snapshot.py`.
- Modify `.github/workflows/batch-push.yml` and optional publication metrics from Task 6.

**Interfaces:**
- `publish(plan: PublicationPlan, store: SnapshotStore, *, expected_current: str | None) -> PublishReceipt`; `SnapshotStore` protocol exposes `get(key)`, `put_many(entries)`, `put(key, value)`. Receipt includes acknowledged object/manifest/pointer writes and bytes. CLI defaults to dry-run and requires explicit `--publish` in the production job.
- Key formats are `objects/<sha256>`, `releases/<snapshot_id>`, `snapshot/current`; pointer stores schema version/current/previous IDs. Production workflow is the single writer; abort if the current pointer differs from the expected parent before switching. KV has no compare-and-swap, so serialize every authorized publisher/rollback in that same concurrency group.

- [ ] Add failure injection tests after each object chunk, after manifest upload, before pointer write, and on pointer failure. Assert no pointer changes until uploads/manifest succeed, retry is idempotent, removed logical keys remain absent, remote missing reuse candidates are reuploaded, and a stale expected parent aborts. Test rollback pointer selection and preservation of old-format artifact.
- [ ] Implement upload chunks of at most 1,000 entries and at most 10 MiB combined serialized bytes, with a singleton allowed for an individually valid object up to the existing 20 MiB budget. Retry bounded failures (three attempts with backoff), validate acknowledgements, and write immutable manifest then pointer separately. Never claim these writes prove global KV propagation; Task 7 handles reader availability.
- [ ] Use prior published manifest and remote checks for candidate reuse; if prior state is unavailable, reupload all required objects safely. Keep seven days of legacy bulk artifacts for rollback and leave mutable legacy keys untouched during versioned publishing. No object garbage collection in this release.
- [ ] Run publisher/publication/Worker tests and full preflight. Exercise interrupted publication and pointer rollback against a staging namespace with the same reader before production. Measure write reduction alongside extra read costs and storage growth. Verify a pinned map refresh and HTTP/MCP consistency during the staged switch.
- [ ] Commit as `feat: publish snapshot deltas with versioned rollback`. Roll back the pointer via the serialized publisher; legacy Worker rollback first requires restoring a complete old-format snapshot. Add mark/sweep GC only in a later review if storage monitoring warrants it.

## Separate ingestion migration

### Task 9: Establish the pilot's facts before an implementation plan

**Files:**
- Create `docs/research/daily-ingestion-inventory.md` and `docs/superpowers/specs/daily-ingestion-pilot.md` at execution time.
- Inspect, do not modify in this task: `apps/api/src/producers/scheduler.py`, `watermarks.py`, `dob_permits_producer.py`, `apps/api/src/features/pipeline.py`, `apps/api/src/consumers/feature_aggregation_worker.py`, `alert_dispatcher_worker.py`, and `docs/adr/0008-realtime-aggregation-and-alert-dispatch.md`.

**Interfaces:**
- Produces an evidence-backed selection of one enabled NYC permit source/endpoint/job ID and a read-only infrastructure/dependency/cost inventory. The pilot uses durable raw pages and checkpoints with `(city, feed, source ID)` identities, as specified in the design; it does not call the existing Kafka scheduler on an ephemeral runner and declare durability solved.

- [ ] Inventory actual deployed services, consumers, data volumes, source freshness, state locations, and alert users with read-only tools. Record unknowns explicitly; do not infer idle deployment from repository files.
- [ ] Validate the chosen feed's stable ID, update-time semantics, pagination boundaries, correction/delete visibility, rate limits, and complete snapshot/reconciliation support. Choose source-supported overlap/reconciliation rules from those findings, not an arbitrary universal watermark policy.
- [ ] Write the pilot spec with exact source identifiers, durable R2/S3 checkpoint contract, conditional writes, raw-manifest-before-cursor commit, replay/content-hash upserts, scoped IDs, explicit UTC as-of, full baseline aggregation, and disabled outbound alerts. Specify tests for equal timestamps, interrupted writes, empty successful polls, late updates, moved/deleted rows, truncated snapshots, 60/90/180/360-day boundaries, and capex decay on no-new-data days.
- [ ] Set acceptance to seven successful daily shadow cycles plus replay/boundary/failure tests, full-rebuild feature parity, source-age reporting, and storage/cost evidence. Write a separate implementation plan after the spec identifies these concrete inputs and approved storage; do not modify synthetic map features or decommission services in this task.
- [ ] Commit only the inventory/spec as `docs: scope durable daily ingestion pilot`; return measured recommendations and retained streaming-alert dependencies. Infrastructure retirement requires its own reversible migration and data-retention plan.

## Self-review and handoff

Spec coverage maps to Tasks 1–4 for the recommended release, Task 5 for model bundles, Tasks 6–8 for optional immutable publication, and Task 9 for the deliberately separate ingestion migration. Tests cover all five review-focus conditions at their owning boundaries. Numeric invariants and interfaces above are consistent with the design. The current plan creates no production changes and makes no measured-savings claim.

Review Tasks 1–4 first. Preserve daily freshness, benchmark the result, and choose later work from evidence rather than implementing all phases by default.
