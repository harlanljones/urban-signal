# Stream log — migration-apps-api — 2026-08-23

## Claim

- **Stream id:** `migration-apps-api`
- **Leaf files I will create/edit:** `apps/api/**`, `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `uv.lock`, `.github/workflows/**`, `deploy/k8s/**`, `PLAN.md`, `GATES-HAR-41.md`
- **Spine files I expect to need:** all Python core files move beneath `apps/api`; no concurrent stream is authorized

## Intent

Make `apps/api` the canonical home of the Python core, preserving imports and behavior while updating all checked-in execution surfaces and proving the move with the migration gates.

## Decisions

- 2026-08-23 — Preserve the existing `src` package namespace inside `apps/api` to keep the migration mechanical and reduce runtime risk.
- 2026-08-23 — Keep root `scripts/` as orchestration tools; they will invoke the migrated package explicitly.

## Current step

Migration complete; package, tests, manifests, CI, containers, deployment environment, and path-sensitive tests now target `apps/api`. Linear HAR-41 is Done.

## Next step

No further work in this stream. Serving/e2e checks need Kafka at `localhost:9092`.
