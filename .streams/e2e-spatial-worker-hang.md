# Stream log — e2e-spatial-worker-hang — 2026-08-23

## Claim

- **Stream id:** `e2e-spatial-worker-hang`
- **Leaf files I will create/edit:** `tests/e2e/test_pipeline_e2e.py`, plus any directly scoped e2e fixture/worker lifecycle files discovered during diagnosis
- **Spine files I expect to need:** none

## Intent

Make `tests/e2e/test_pipeline_e2e.py::test_e2e_spatial_enrichment_worker` terminate deterministically by fixing only its e2e fixtures/worker lifecycle/resource cleanup, or the narrowly necessary production bug.

## Decisions

- 2026-08-23 — Ownership is limited to the named e2e hang and termination behavior.
- 2026-08-23 — Reproduction showed `AdminClient.create_topics()` waiting forever in `future.result()` while no Kafka broker was available. Added a one-second bound per best-effort topic-provisioning future, plus worker/pipeline close paths and fixture cleanup.

## Current step

Focused test passes with bounded Kafka provisioning waits; final diff is limited to the worker, consumer, pipeline, and target e2e fixture/test (unrelated worktree changes remain untouched).

## Next step

Completed focused verification. Report that Kafka is optional for this local processing test but required for `start()`/live consumption.
