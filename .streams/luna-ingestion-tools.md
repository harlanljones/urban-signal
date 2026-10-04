# Stream log — luna-ingestion-tools — 2026-10-03

## Claim

- **Stream id:** luna-ingestion-tools
- **Leaf files I will create/edit:** `scripts/run_shadow_ingestion.py`, `scripts/probe_ingestion_store.py`, `scripts/validate_shadow_cycles.py`, `apps/api/tests/unit/test_shadow_ingestion_cli.py`, `apps/api/tests/unit/test_shadow_cycles.py`, `docs/research/shadow-ingestion-runbook.md`, `.streams/luna-ingestion-tools.md`, `.superpowers/sdd/durable-shadow-ingestion/tools-report.md`
- **Spine files I expect to need:** none; root owns workflow and dependency integration.

## Intent

Deliver safe operator tooling for local fixture, live shadow ingestion, replay, isolated store probing, and truthful scheduled-cycle validation. All live writes require a ready source contract and provider-backed readiness evidence, use explicit UTC as-of values, and fail closed on bounds or incomplete runs.

## Decisions

- 2026-10-03 — Honor root's fixed runner API and keep local fixtures explicitly local-only.

## Current step

Reading the plan and design, then inspecting the source/store implementation as it becomes available.

## Next step

Write behavior tests first, implement the three scripts and runbook, then focused tests and Ruff.

## Root integration handoff
Luna runner/tools interrupted by usage limit; root completed local integration and focused verification. See docs/research/shadow-ingestion-validation-2026-10-03.md for tests and operational gates. Root owns CLI/workflow/test integration and commits; no spine changes.
