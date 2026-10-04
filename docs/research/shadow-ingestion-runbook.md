# NYC permit shadow ingestion runbook

Status: implementation tooling only. The checked-in NYC permit contract is not ready for live acquisition: required identity, update-time, stable pagination, snapshot, reconciliation, replacement, and request-limit guarantees remain unverified. Do not enable a schedule or treat local fixtures as source evidence.

## Modes and boundaries

`run_shadow_ingestion.py` requires an explicit UTC `--as-of` and one of `bootstrap`, `daily`, `reconcile`, or `replay`. Live acquisition loads the checked-in source contract and calls `assert_ready()` before opening the source. Local fixture use requires `--local-root`; its output labels provenance `local_fixture` and it cannot serve as proof of remote completeness. The default record cap is 250,000 rows and the maximum is 4,000,000. A page that crosses the cap aborts before the runner commits a manifest or cursor. Raise the cap only after estimating memory and runtime for the chosen runner.

The R2 bucket must already exist and be dedicated to shadow artifacts. These scripts never create a bucket. Keep the runner namespace under `ingestion/v1/nyc/permits/ipu4-2q9a/shadow/`; live runner objects use its `data/` child. Set only `INGESTION_R2_ACCESS_KEY_ID`, `INGESTION_R2_SECRET_ACCESS_KEY`, and an explicit endpoint. Never place credentials in command arguments, receipts, workflow output, or cycle evidence.

## Verify storage before live runs

Run `python scripts/probe_ingestion_store.py --bucket "$BUCKET" --endpoint "$ENDPOINT" --prefix ingestion/v1/nyc/permits/ipu4-2q9a/shadow/ --receipt-output /tmp/ingestion-probe.json`. The probe writes into a new UUID child under `probes/`; it does not clean up or reuse the prefix. It tests absent-checkpoint CAS, accepted and stale IfMatch writes, rejected immutable overwrites, a two-client creation race, integrity reads, and restore from a newly constructed client. Preserve the receipt for at most 24 hours. It binds the bucket, endpoint, authorized base prefix, probe prefix, object and checkpoint SHA-256 values, timestamp, and probe identifier.

A live run rechecks receipt age, configured target and namespace, then fetches and hashes both probe objects from the provider using a fresh client. A `verified` JSON field alone is insufficient. Example:

```bash
python scripts/run_shadow_ingestion.py \
  --mode daily --as-of 2026-10-03T03:00:00Z \
  --bucket "$BUCKET" --endpoint "$ENDPOINT" \
  --prefix ingestion/v1/nyc/permits/ipu4-2q9a/shadow/ \
  --provider-receipt /tmp/ingestion-probe.json
```

Use `--local-root /tmp/permit-shadow --fixture apps/api/tests/fixtures/ingestion/shadow-permits.json` for offline runner checks. Local runs never contact Socrata or R2. `replay` reads committed manifests and recomputes at the supplied as-of without querying Socrata; live replay still checks the provider receipt before reading remote state.

## Interpret run evidence

Store the emitted JSON result as a compact run artifact. Preserve source contract/version, acquisition and feature manifest hashes, query bounds, checkpoint lineage, source and parser versions, row/reject/correction counts, freshness timestamps, request/retry counts, compressed bytes, storage requests/bytes, and phase duration when available. A failure or a record cap must stay visible as incomplete. Do not infer full-source completeness from exhaustion of a bounded delta query. Full reconciliation and tombstones require verified source evidence that the current source contract does not yet provide.

For M4, keep a dated JSON list of cycle evidence and run:

```bash
python scripts/validate_shadow_cycles.py cycle-evidence.json \
  --cadence-hours 24 --max-source-age-seconds 86400
```

Set these limits from the documented publisher cadence and stale threshold before the first scheduled cycle. Each scheduled item needs complete acquisition and feature manifests, source-contract hash and measured age, prior/current checkpoint versions, query bounds, provider probe receipt evidence, measured usage, and an independent full rebuild with matching identity/count/window/cell parity hashes. The validator counts only consecutive scheduled UTC cycles. Manual cycles do not advance or reset the schedule streak; any scheduled failure, missing evidence, stale source or cadence gap resets the streak. Seven recent scheduled successes are required. Fixture tests for pagination ties, interruption, empty days, corrections, moves, deletes, replacement and time boundaries remain necessary regardless of live observations.

## Scheduling and rollout

Keep workflow execution manual-only until the source contract is independently verified, a real R2 probe passes, manual cold restore and replay pass, and bootstrap/delta/reconciliation usage has been measured. Do not add an automatic schedule, production KV capability, alerts, dashboard feature promotion, or service retirement through this runbook. Permit counts are not complete predictions, cost coverage, or evidence to retire the streaming path.
