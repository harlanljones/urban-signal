# M3 — Build daily shadow ingestion

Date: 2026-10-03. Status: proposed. Dependencies: accepted M1 source contract and verified M2 storage.

## Purpose and boundary

Run daily NYC permit acquisition, durable commit and full feature aggregation on Actions. Emit isolated shadow outputs with alerts disabled. Preserve existing dashboard publication. This is permit-only ingestion; it does not supply complete LIMS, costs or a trained model.

## Components and interfaces

- Acquisition adapter consumes M1's versioned contract and a committed cursor, returning projected pages plus completeness/query-bound evidence.
- Commit coordinator writes immutable raw pages/manifests and uses M2's conditional checkpoint boundary.
- Normalizer reads committed manifests, validates schema and upserts by `(city, feed, source_record_id)` plus content hash. Keep source dataset/release identity and parser version.
- Aggregator restores committed normalized history and computes the full pilot feature baseline at one explicit UTC as-of.
- Runner emits a versioned shadow feature manifest and diagnostic metrics; it receives no outbound alert or production KV capability.

Suggested invocation contract: source contract/version, UTC as-of, authorized shadow prefix and mode (`bootstrap`, `daily`, `reconcile`, `replay`). Exact CLI/module locations belong in the implementation plan. Replay fixes source manifests and as-of; it must not fetch changing live data implicitly.

## Run semantics

Acquire using verified source-supported bounds/continuation. Persist all required raw pages before committing a manifest and advancing the acquisition checkpoint. Capped, failed or inconsistent extraction leaves the prior cursor valid. Quarantine malformed projected rows with reasons; M1 defines whether a row error prevents completeness, and dropped rows cannot disappear silently.

Acquisition progress and feature readiness are distinct: an aggregation failure after a successful acquisition commit must be replayable from its manifests. Advance a shadow feature pointer only after normalized-state and full-baseline validation succeeds; do not roll back or falsify acquisition progress.

Corrections upsert regardless of old issuance time. Moved records update both former and new cell contributions. Deletions require M1's validated complete reconciliation. Never hydrate the existing unscoped in-memory tables without fixing the pilot's identity projection.

Recompute relevant windows daily, including empty successful polls. Preserve exact UTC boundaries from existing feature definitions and document them in fixtures. No-new-data does not mean unchanged features. Expose missing costs explicitly and calculate only supported permit features.

Actions workflow uses main-only manual/scheduled execution, non-cancelling single-writer concurrency and bounded timeout/retries informed by measurement. First prove manual replay/restore; enable daily scheduling afterward. Break a large bootstrap into resumable acquisition units if source consistency permits; otherwise evaluate a batch executor without changing the storage contract.

## Acceptance

- A cold runner completes acquisition, restore and full-baseline computation using durable state only.
- Replay of committed manifests at the same as-of yields identical normalized records/features.
- Equal timestamps, interruptions, corrected/moved/deleted rows, schema drift, caps and checkpoint conflicts satisfy the shared pilot test matrix.
- UTC window-boundary and no-new-data-day fixtures pass; duplicate IDs do not inflate counts.
- Each run reports source ages, completeness, quarantine counts, rows, hashes, storage requests/bytes, phase time and resource use.
- Shadow outputs cannot send alerts or overwrite production KV keys; intentional failure retains the previous valid shadow feature pointer.
