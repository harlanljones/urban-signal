# Stream log — luna-metrics — 2026-10-03

## Claim

- **Stream id:** `luna-metrics`
- **Leaf files I will create/edit:** `apps/api/src/export/snapshot_metrics.py`, `apps/api/src/export/snapshot_builder.py`, `scripts/benchmark_snapshot.py`, `apps/api/tests/unit/test_snapshot_metrics.py`, `apps/api/tests/unit/test_export_snapshot.py`, `.streams/luna-metrics.md`
- **Spine files I expect to need:** none

## Intent

Instrument snapshot build stages and key/byte families, write failure-safe metrics outside KV, and provide a paired cached/uncached benchmark with semantic output comparison. Keep benchmark scope to phase one.

## Decisions

- 2026-10-03 — Metrics schema is version 1 with thread-safe counters, duration stages, artifacts, and synthetic-default provenance.

## Current step

Implementation and focused verification are complete for metrics, builder instrumentation/cache wiring, and benchmark comparison. The all-city compare3 benchmark is coordinated with the root agent.

## Next step

Root runs the all-city compare3 benchmark and appends its result to the task report.

## Completed

- Metrics use schema 1, thread-safe counters, copied snapshots, commit/tree/dirty-worktree provenance, context metadata age, and table availability validated by the builder's actual `load_context` result.
- Snapshot builder instruments required stages and prefix key/byte totals, emits incomplete failure summaries, attaches metrics to supplied engines, defaults newly created engines to cached predictions, and supports `--no-prediction-cache`.
- Builder records distinct normalized feature vectors; model call and cache-hit counters come from the engine to avoid double counting.
- Benchmark compares same-engine off/on outputs recursively, preserves slash-key index clock handling, exits nonzero on semantic mismatch, runs cache modes in cold/warm order, records context input hashes and process-lifetime RSS labels, and limits retained output to baseline bulk files.
- Focused verification: 8 selected pytest cases passed; Ruff passed on all owned Python files.
- Full-city compare3 was not run in this stream; root is coordinating that run.
