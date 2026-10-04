# M4 — Validate the shadow pilot

Date: 2026-10-03. Status: proposed. Dependency: M3 manual correctness/restore checks pass.

## Purpose

Establish acquisition correctness, daily reliability, source freshness and operational cost before using pilot features in the dashboard. Collect seven consecutive successful scheduled UTC daily cycles. Manual runs are supplementary evidence, not replacements for the scheduled reliability count. An unresolved failed/incomplete scheduled cycle resets the consecutive count after its cause is fixed.

## Evidence package

For each cycle retain workflow/run/source-contract IDs, source and parser versions, committed acquisition/feature manifest hashes, prior/current checkpoint versions, query bounds, as-of and separate freshness timestamps. Include complete/partial status, normalized row/key counts, rejects, corrections/tombstones, request/retry counts, compressed bytes, storage operations, durations and resource usage. Retain source receipts in authorized storage; Actions artifacts contain compact diagnostics without credentials or unrelated personal fields.

At each cycle's fixed as-of compare pilot outputs with an independent full rebuild of the same committed complete source history. Compare identity, counts, window membership and affected cells. Specify numeric tolerances only where computations require them, with justification; do not conceal missing rows behind aggregate tolerances. This verifies processing parity, not external publisher completeness, which M1's acquisition evidence must separately establish.

Exercise failures in deterministic fixtures: equal timestamps/pages, interrupted object and checkpoint commits, empty poll, schema drift, late correction, geometry move, deletion and dataset replacement. The absence of live corrections/deletions over seven days is not proof of their handling. Run time-window boundary fixtures and no-new-data-day decay fixtures for features with authoritative costs.

## Reliability and cost decision

Track acquisition freshness separately from source freshness. A stale upstream feed may yield a correctly processed acquisition; report it as stale rather than presenting daily publication as fresh source data. M1 defines source cadence and stale thresholds before the seven-day test begins. Alert on actionable failures through agreed destinations only; report unchanged conditions quietly if monitoring is later enabled.

Measure bootstrap once, daily deltas across all seven days, and at least one complete reconciliation. Project monthly usage using per-job-rounded Actions time, reconciliation cadence, retries, durable storage and retained backend services. Public standard-runner eligibility is recorded separately from storage and other bills. Compare GCP/AWS/Railway/Fly only with the same measured workload and current dated pricing.

Stay on Actions if measured work fits current runner/time/resource limits and verified source quotas with acceptable operational cost. Document a different executor only if measured limits or cost justify it. Executor changes must retain replay/commit semantics.

## Acceptance and failure outcome

- Seven consecutive scheduled successes and all boundary/replay/failure tests pass.
- Every cycle has complete lineage, accurate freshness and independent full-rebuild parity.
- At least one restore drill and complete reconciliation pass; retention supports replay.
- Costs and limits are measured, with bootstrap separated from recurring usage.
- Remaining source limitations, stale feeds and unsupported features are recorded in a go/no-go report.

Any correctness/completeness failure blocks M5 for the affected scope. A passing permit-only pilot does not approve complete dashboard predictions or infrastructure retirement.
