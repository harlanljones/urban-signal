# Stream log — luna-ingestion-store — 2026-10-03

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** `luna-ingestion-store`
- **Leaf files I will create/edit:** `apps/api/src/ingestion/store.py`, `apps/api/tests/unit/test_ingestion_store.py`, `docs/research/ingestion-storage-readiness.md`, `.streams/luna-ingestion-store.md`
- **Spine files I expect to need:** none

## Intent

Implement local crash/concurrency-safe storage and injected S3-compatible storage with strict immutable hashing and conditional checkpoint writes; test contract and document provider readiness honestly.

## Decisions

<Appended as made. Findings go here the moment they are learned (F5) —
not at the end.>

- 2026-10-03 — Dedicated Cloudflare R2 selected; credentials are not configured. Remote writes/provisioning are outside this stream. Official R2 API docs returned HTTP 403 from this environment, so conditional-write behavior is recorded as unverified.
- 2026-10-03 — Implemented S3 conditional `IfNoneMatch`/`IfMatch` operations with post-write verification and no unconditional fallback. Provider rejection propagates fail-closed.
- 2026-10-03 — Checkpoint JSON rejects non-finite numbers; tests import via `src.ingestion.store` to preserve the repository package namespace.
- 2026-10-03 — Local roots are created with `0700`; preexisting roots must be owned by the current user and not group/other writable. This trusted-owner boundary avoids a complex dirfd implementation and documents same-UID races as outside the threat model.

## Current step

Local and injected S3 adapters are implemented; 24 focused tests and Ruff pass.

## Next step

Root integration and full preflight remain; live use also requires an R2 account, the isolated conditional-write probe, and fresh-runner restore evidence.
