# Stream log — luna-workflows — 2026-10-03

## Claim

- **Stream id:** `luna-workflows`
- **Leaf files:** `.github/workflows/batch-push.yml`, `.github/workflows/dashboard-deploy.yml`, `apps/api/tests/unit/test_workflow_routing.py`, `.streams/luna-workflows.md`.
- **Additional report:** `/workspace/backend-phase1/task-2-report.md`.
- **Spine files:** none.

## Intent

Split the daily snapshot/KV refresh from dashboard code releases. Cover event, ref, path, secret, validation and dependency routing with tests before editing workflows.

## Decisions

- 2026-10-03 — Parse GitHub Actions YAML with a safe loader that retains the literal `on` key.
- 2026-10-03 — No README edits are in this stream's assigned file set; workflow path filters will omit README/docs paths.
- 2026-10-03 — Keep the `batch-push-deploy / validate` PR check and its code-only web/zoom gates; schedule/manual runs use only the Python snapshot/interlock gate.
- 2026-10-03 — Registry/schema rollout order is recorded in the design spec: compatible reader, manual snapshot refresh, then visibility verification.

## Current step

Workflow split and routing checks are complete. Snapshot publication is main-only on the 06:00 UTC schedule or manual dispatch; dashboard deployment has its own validated main release workflow and concurrency group.

## Next step

Root integration and broad preflight remain. No remote workflows were triggered.
