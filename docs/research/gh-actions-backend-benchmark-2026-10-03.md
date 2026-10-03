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

The benchmark records HEAD/tree and dirty status. Commit `a38bf9c` contains the exact measured implementation; its code-file hashes match the companion evidence. Subsequent engine cleanup changes imports and type annotations only, without changing inference or cache behavior. Companion source SHA-256 evidence identifies the exact edited implementation. RSS is a Linux process-lifetime high-water mark from one reused process; its mode observations cannot support a claim about per-mode RAM savings. Cache misses for distinct vectors share a lock, so results apply to the present repeated-vector workload and should be remeasured if inputs become mostly unique.

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
