# Durable shadow ingestion implementation plan

> **For agentic workers:** Use subagent-driven-development; the user explicitly selected Luna subagents. Root coordinates shared interfaces, integration and commits.

**Goal:** Implement source validation, durable storage adapters, replayable permit-only shadow ingestion and validation tooling. Keep Cloudflare serving and the current production snapshot intact.

**Architecture:** An independent `src.ingestion` package commits projected source pages before cursors, restores committed runs, and computes complete permit-only baselines at a fixed UTC as-of. Local storage supplies real crash/concurrency tests; an optional S3-compatible adapter must pass a real provider probe before live scheduling. Source guarantees remain explicit runtime gates. No synthetic prediction promotion or backend retirement can bypass the milestone specs.

**Tech stack:** Python 3.12, httpx, H3, standard-library file locking/JSON/hashing; optional boto3 for a verified S3/R2 target; GitHub Actions manual shadow workflow.

## Global constraints and execution rulings

- Specs: `2026-10-03-backend-milestones.md` and its M1–M6 linked designs, plus `daily-ingestion-pilot.md`.
- User authorizes implementation using Luna; proceed through reversible local work without another plan-approval question.
- M1/M2 are independent leaf tasks and can run in parallel; shared interfaces below are fixed before dispatch. Root owns integration and git commits, avoiding shared-index races.
- No live source guarantee or storage verification may be fabricated. Local fixtures do not satisfy remote guarantees. Live acquisition must fail closed while required evidence is unverified.
- Source contract evidence gathering and infrastructure inventory can proceed read-only. No outbound alerts, production KV changes, deployment, shutdown or deletion occurs in this implementation.
- Seven scheduled cycles, additional feeds/model readiness and service-owner retirement evidence require elapsed time/access. Implement their tools and explicit gates; report the remaining operational requirements truthfully.
- User selected a dedicated Cloudflare R2 bucket. Implement R2-compatible storage; runtime credential inventory is empty. Local tests cannot establish actual provider readiness.

## Task 1: Source contract and validation (Luna source)

Files: `apps/api/src/ingestion/source.py`, `apps/api/tests/unit/test_ingestion_source.py`, `docs/research/nyc-permit-source-contract.json`, `docs/research/nyc-permit-source-validation.md`, projected fixture under `apps/api/tests/fixtures/ingestion/nyc-permits.json`.

Interface: `SourceContract.from_dict(data)`; `.assert_ready()` rejects unverified required guarantees; `.to_dict()`. `SocrataPermitSource(contract, client=None).iter_pages(cursor=None, upper_bound=None)` uses explicit safe field projection and proven pagination rules; configurable injected httpx client for tests. Define exact public signatures and record them for root before implementation. Include source/version/identity/update/pagination/completeness evidence in the contract. Do not make current feed readiness true based only on small samples.

Write tests first for identity collisions, timestamp/page boundary continuation, bounded retries, incomplete acquisition and readiness rejection. Inspect bounded public queries and publisher docs; commit only projected nonpersonal fixture/evidence. Record unresolved source guarantees and fallback options.

## Task 2: Durable stores (Luna storage)

Files: `apps/api/src/ingestion/store.py`, `apps/api/tests/unit/test_ingestion_store.py`, `docs/research/ingestion-storage-readiness.md`.

Interface: `LocalObjectStore(root)` and `S3ObjectStore(client,bucket,prefix)` expose `put_immutable(key,bytes,sha256)->None`, `get_verified(key,sha256)->bytes`, `read_checkpoint(key)->tuple[dict|None,str|None]`, `compare_and_swap_checkpoint(key,expected_version,body)->str`. Use `CheckpointConflict` and `IntegrityError` exceptions. JSON serialization is deterministic UTF-8 with sorted keys/compact separators. Versions are opaque; `None` means absent.

Local store must have process-safe locking, atomic replacement and path containment, immutable-object hash validation, and CAS including absent-writer races. S3 uses real conditional request primitives (`IfNoneMatch`/`IfMatch`) only where supported; no read-then-unconditional-write emulation. Inject the client; root supplies optional boto3 loader and credential wiring. Write real local race/corruption/interruption tests first and adapter error-contract tests. Remote provider probe remains required before live execution.

## Task 3: Commit, replay, normalization and daily baseline (root + Luna runner after interfaces settle)

Files: `apps/api/src/ingestion/runner.py`, tests `test_ingestion_runner.py`, `scripts/run_shadow_ingestion.py`. Root defines brief from actual Task 1/2 interfaces before dispatch.

Persist immutable projected pages, complete manifest and acquisition cursor in that order. Restore the full committed lineage for replay. Reject incomplete extraction, ambiguous IDs/schema, unsafe time/geometry and invalid lineage. Content-hash upserts use scoped identity; corrections move contributions, deletions require a complete reconciliation. Feature pointer is independent of acquisition checkpoint. Full permit baseline includes UTC-inclusive 60/90/180/360-day counts, existing 60/180 velocity semantics, missing-cost provenance and fixed-as-of replay. Empty polls recompute windows. No model predictions or alerts.

Tests must demonstrate interrupted commit/replay, stale CAS, corrupt/missing objects, duplicate/corrected/moved/deleted rows, future records, UTC boundaries, empty day, and independent full-rebuild parity. Bootstrap/full reconciliation and delta runs have explicit completeness contracts; capped polls cannot authorize deletion.

## Task 4: Validation tooling and manual workflow (Luna verification tooling)

Files: `scripts/validate_shadow_cycles.py`, tests `test_shadow_cycles.py`, `.github/workflows/shadow-ingestion.yml`, `docs/research/shadow-ingestion-runbook.md`.

Accept seven consecutive scheduled UTC daily cycles only with complete lineage, parity/freshness/source evidence; manual cycles do not satisfy scheduled reliability. Emit measured bootstrap/delta/reconciliation storage/request/time usage and reset the run streak on failed scheduled cycles. Workflow starts manual-only/main-only, with job-scoped storage credentials, no production KV/webhook capability, noncancelled concurrency, explicit source-ready and provider-verified gates. Scheduling is enabled only after manual real-store restore and source validation; do not add an automatically active cron.

## Task 5: Independent review and full verification (fresh Luna review)

Review each task and whole diff for spec compliance and correctness, focusing on manifest-before-cursor commits, first-writer races, source completeness, scoped identity, replay parity, time windows, unsafe paths and shadow-only permissions. Fix findings with regression tests. Run focused ingestion suites and full repo CI/CD preflight; broaden existing suite where shared behavior changes. Commit verified implementation and record operational blockers against M1–M6 without claiming deployed or seven-day-validated completion.

## Review focus

Tests cover: partial/capped source mistaken for complete; same timestamp across pages; object/manifest/checkpoint interruption and first-writer races; historical correction/move/deletion with full rebuild parity; and empty successful days with changing windows. M5/M6 remain gated by actual model/feed/user requirements rather than a stub implementation.
