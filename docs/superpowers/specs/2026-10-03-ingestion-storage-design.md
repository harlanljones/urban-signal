# M2 — Establish durable ingestion storage

Date: 2026-10-03. Status: proposed. Dependencies: M1 sizing and identity decisions; [shared pilot contract](daily-ingestion-pilot.md).

## Purpose and choice

Provide durable raw history and conflict-safe checkpoints independent of ephemeral Actions runners. Recommend R2 alongside existing Cloudflare hosting. Use an existing authorized S3 store if it offers the required semantics and ownership with less setup. Actions artifacts/caches are diagnostic storage, not ingestion state. Account, bucket, credential access and retention are not yet established.

## Contract

Use `ingestion/v1/nyc/permits/ipu4-2q9a/` as a proposed isolated namespace, finalized with the actual account owner. Store immutable content-addressed projected raw pages, immutable run manifests, versioned normalized/feature outputs and a small mutable checkpoint. Keep production KV publication credentials separate from shadow storage access.

The adapter exposes operations equivalent to `put_immutable(key, bytes, sha256)`, `get_verified(key, sha256)`, `read_checkpoint() -> (body, version)`, and `compare_and_swap_checkpoint(expected_version, body)`. Exact SDK/API methods are selected only after verifying the chosen provider's behavior. Handle absent checkpoints explicitly: two simultaneous initial writers cannot both commit. Never emulate a conditional write with separate read and unconditional put.

Raw writes must be acknowledged and hash/length verified before a complete run manifest is committed. Checkpoint advancement references that immutable manifest and atomically compares the prior generation/version. A conflict leaves the prior committed lineage authoritative; orphan objects are recoverable diagnostic state. Workflow concurrency complements this storage boundary.

## Access, retention and recovery

Record storage owner/account/region where relevant, approved prefix, selected API, least-privilege credentials and credential rotation procedure without committing secrets. Use main-only scheduled execution and prevent untrusted PR jobs from receiving write credentials.

Before enabling lifecycle policies, agree a retention schedule supporting at least the feature-history windows, seven-cycle pilot evidence and rollback/replay needs. Referenced committed pages/manifests cannot expire while retained outputs depend on them. Define how checkpoints, tombstones and normalized state survive raw retention; archive/export policy must make a complete restore possible. Provider versioning is an optional extra, not the commit mechanism.

Measure compressed bytes, object count and read/write/list requests separately for bootstrap, daily delta and reconciliation. Report prices with provider/date/free-tier assumptions; no inferred current bill. Cleanup of unreferenced shadow objects follows a documented grace period and never targets production namespaces.

## Acceptance

- Actual authorized target and API recorded; conditional writes verified in an isolated prefix.
- Tests cover initial-writer race, stale-generation conflict, interrupted upload/manifest/checkpoint, corrupted bytes, authorization failure and concurrent writers.
- A fresh runner restores complete committed state without caches or diagnostic artifacts.
- Retention/lifecycle design preserves committed lineage, with a restore drill and measured storage/request costs.
- No production KV writes occur during storage verification.

M2 blocks live shadow scheduling until access and semantics are verified. Local fake-store fixtures can support development but cannot satisfy the provider test.
