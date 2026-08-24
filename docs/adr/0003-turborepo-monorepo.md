# ADR 0003: Turborepo Monorepo Adoption

**Status:** Accepted
**Date:** 2026-08-23
**Scope:** urban-signal (repository shape, JS toolchain)
**Supersedes:** —
**Companion:** HAR-35 (Linear), `docs/agents/parallel-streams.md`

## Context

The repository is a Python-first system (FastAPI serving, Kafka producers/consumers,
H3 spatial features, ONNX inference) with exactly one TypeScript package:
the Cloudflare edge worker (`workers/`, npm-managed) that serves the MapLibre
dashboard from Workers KV snapshots. A marketing/product site was approved next.
Three package ecosystems in one repo without a workspace layer would mean three
ad-hoc installs, no shared task graph, and no dependency dedup.

## Decision

Adopt **Turborepo** with **bun workspaces**, minimal-move:

- Root `package.json` + `turbo.json` manage `apps/*` and `packages/*` only.
- The Python core stays at the repository root (`src/`, `tests/`, `pyproject.toml`,
  `deploy/` untouched) — every path is a spine file per the interlock manifest,
  so moving it now would force a full-gate refactor for zero product value.
- `workers/` moves to `apps/edge/` (package `@urban-signal/edge`); CI
  (`batch-push.yml`) switches from `npm ci` to `bun install --frozen-lockfile`.
- Shared TypeScript config lives in `packages/typescript-config`.
- Full Python → `apps/api` migration is deferred (tracked as HAR-41).

Framework choice for the future site (`apps/web`, HAR-42): **Astro 5**. The
product surface already lives in FastAPI plus the KV-backed edge worker, so the
site stays content-first; MapLibre/h3-js demos fit as islands. Next.js was
rejected as overweight for a mostly-static surface until product features move
in-repo. Deploy target: Cloudflare, colocating site and edge worker on one
platform behind the existing batch-push pipeline.

## Consequences

- One lockfile (`bun.lock`) and one install for all JS work; turbo provides the
  shared build/lint/typecheck task graph and caching.
- Docker/k8s/pytest paths are untouched; `pytest -m interlock` remains valid —
  this conversion is entirely leaf-shaped.
- Mixed root layout (Python at root, JS under `apps/`) is accepted as temporary;
  resolving it is HAR-41's job, gated by the interlock rules.
- CI deploys run bun-installed, lockfile-pinned wrangler instead of ad-hoc npx.
