# Shadow ingestion implementation validation

Implemented on `feat/durable-shadow-ingestion`; local development only. Dedicated R2 is selected, but no bucket credentials/provider verification or live source readiness has been established.

## Verification

- Final focused ingestion/source/store/runner/CLI/cycle/workflow suites: 82 passed.
- Existing workflow-routing suite: seven passed. Changed ingestion code/scripts/tests pass Ruff; required CI/CD preflight passes.
- Local CLI bootstrap and fixed-as-of replay retain exactly the same two normalized records and one cell's features. An empty daily poll retains history and recomputes expired windows.
- Actual boto3/botocore 1.43.108 service model and Stubber accept `IfMatch`/`IfNoneMatch` for PutObject. This is SDK evidence, not proof of R2 enforcement.
- Full API command: 6092 passed, two skipped, seven deselected, seven failed and 38 errors. Initial errors involved denied sockets and the read-only DuckDB cache directory. A targeted rerun with those permissions yielded 78 passed and five failures. The remaining `TestCrosswalkForFema` cases in unchanged `test_gbfs_and_national_feeds.py` attempt network access prohibited by the repository unit-test network guard. The full suite is not green; no ingestion failures were observed. Local logs: `/workspace/ingestion-validation/`.

## Review and remaining gates

Luna source and storage implementations received independent scoped review. Findings fixed include source field projection, bounds/typing, terminal-empty-page cursor retention, and the local-store private-root boundary. Runner/tools streams hit the account usage limit before final handoff; root continued integration and regression fixes, including commit-head capture, JSON-safe receipts, provider probe checks, and retaining future records during replay. Do not describe the entire branch as independently reviewed.

The new manual-only/main-only workflow separates shadow R2 credentials from production publication and blocks live acquisition on the unready source contract. Push/PR validation runs the new tests without enabling shadow scheduling.

M1 still needs source-wide identity/update/reconciliation/capacity evidence. M2 needs the dedicated bucket, least-privilege access, real conditional-write probe and retention/restore decisions. M3's local implementation is available; live readiness depends on M1/M2. M4 tooling exists, but seven real scheduled cycles and independent rebuild evidence have not occurred. M5 real prediction promotion and M6 service retirement remain separate unfulfilled gates. The current CLI buffers acquired rows/history under a configured cap; full-feed bootstrap capacity must be measured or acquisition redesigned before a four-million-row operational run.

[Operator runbook](shadow-ingestion-runbook.md) · [Milestone specs](../superpowers/specs/2026-10-03-backend-milestones.md)
