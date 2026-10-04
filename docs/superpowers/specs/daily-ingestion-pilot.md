# Durable daily ingestion pilot

Date: 2026-10-03. Status: proposed shadow pilot; source and storage gates outstanding. Companion: [evidence-backed inventory](../../research/daily-ingestion-inventory.md). This specification is not authorization to provision storage, switch dashboard inputs or retire streaming services.

Detailed milestone specifications and dependencies: [backend milestone index](2026-10-03-backend-milestones.md). This document remains the shared pilot durability and replay contract.

## Goal and scope

Acquire one enabled NYC permit feed daily with replayable history, explicit source freshness and crash-safe checkpoints. Use GitHub Actions for execution and retain Cloudflare web apps. Start with permit counts/velocity and provenance; do not advertise capex, trained predictions or complete LIMS from this source. Its schema lacks estimated cost, and the other feature-relevant feeds are outside this first pilot.

Exact input: `nyc / permits`, scheduler job `permits`, Socrata dataset `ipu4-2q9a`, `https://data.cityofnewyork.us/resource/ipu4-2q9a.json`. Build an independent acquisition path rather than invoking the Kafka scheduler on a disposable runner. Shadow output cannot send outbound alerts or replace production KV features.

## Preconditions before the implementation plan

- Verify uniqueness/nullability and persistence of `permit_si_no` or a documented composite business key. A raw Socrata `:id` can remain acquisition metadata; do not assume it survives full dataset replacement. Reject ambiguous IDs instead of silently selecting one job row.
- Verify source-supported `:updated_at` filtering, timestamp precision, deterministic secondary ordering and continuation through equal timestamps. Confirm what changes trigger updates, including corrections to old issuance dates and moved geometry. Prove pagination using adjacent bounded pages and a reconciliation fixture.
- Establish deletion detection and publisher replacement behavior. No tested deletion stream exists. Require a **complete**, validated reconciliation before inferring tombstones; partial downloads never imply deletions. If the source offers no consistent snapshot/export, define a proven acquisition/reconciliation strategy before proceeding.
- Determine supported request/page limits, app-token availability, 429/backoff policy and bounded bootstrap size. The observed 3,990,806 rows make an arbitrary 500/5,000-row cap inadequate for completeness.
- Identify the actual storage account, authorized bucket/prefix, credentials, retention and supported conditional-write API. **Recommend Cloudflare R2** for immutable raw objects next to existing hosting; S3 is an alternative if an existing approved durable store is available. Neither is approved or provisioned by this spec. Verify conditional request semantics in the chosen API, rather than assuming every S3-compatible operation behaves identically.
- Inventory live alert consumers and retained infrastructure separately. This pilot requires no Kafka/PostGIS shutdown.

## Durable data contract

Identity is `(city_id, feed_id, source_record_id)`, with source dataset/release identity recorded separately. Preserve original business and source row IDs; never upsert all permits by bare `job__`. Normalized records carry event time, source update time, acquisition time, UTC as-of, content hash, geometry/H3, parser version, original source reference and validation status. Store only needed public columns; exclude names/phone details unrelated to features.

Suggested object namespace: `ingestion/v1/nyc/permits/ipu4-2q9a/`. Raw page objects are immutable and content-addressed. A run manifest contains source query bounds, page hashes/byte counts, row counts, schema/version, completeness status and source freshness. A checkpoint contains committed run-manifest identity, source cursor, dataset identity and generation/version.

Commit protocol:

1. Read the committed checkpoint/version; establish an explicit UTC run as-of and source-supported extraction bounds.
2. Fetch/project/validate pages with deterministic continuation, bounded retries and quota handling. Write raw objects and verify acknowledged hashes/lengths.
3. Commit an immutable run manifest **only after all required pages are durable**. Incomplete or capped runs cannot declare reconciliation complete.
4. Advance the checkpoint using a verified conditional write against the prior version. A conflict loses the commit and leaves the old checkpoint valid. GitHub workflow concurrency is useful but does not replace storage-side conflict protection.
5. Rebuild normalized state from committed manifests using scoped-ID/content-hash upserts. Replaying the same run is idempotent; a corrected row updates its old and new affected cells. Only a successful complete reconciliation can authorize tombstones.

The checkpoint must never outrun durable raw data. Crashes can leave harmless orphan objects/manifests, which retention cleanup handles later. Actions caches/artifacts are diagnostic outputs, not the checkpoint or historical source of truth.

Do not pick a universal overlap interval. Set correction overlap and reconciliation cadence from verified source semantics, with tests documenting the supported lateness bound. If those guarantees cannot be established, prefer validated full acquisition to a cursor that silently misses history; measure whether bootstrap/reconciliation needs a different executor.

## Feature baseline and publication boundary

Restore committed history into a temporary analytical store; use city/feed-scoped keys. Recompute the full pilot feature baseline at the same explicit UTC as-of every day, including successful no-new-data days. Preserve the existing 60/90/180/360-day windows and 180-day capex decay semantics wherever authoritative cost data eventually exists. Keep missing cost explicit; never convert missing costs into evidence of zero investment.

Source-age reporting distinguishes dataset publication, newest source update, event-time coverage, successful acquisition and feature as-of. Emit quarantined/null-geometry counts, acquisition completeness, row/key counts, pagination/replay statistics, storage bytes/requests and phase duration/RSS. A green job without complete data is insufficient.

Shadow outputs use their own versioned prefix and cannot overwrite dashboard KV keys, infer alerts or change synthetic map inputs. A later integration plan must separately cover the remaining feeds, cost-bearing joins, trained model bundle, provenance, coverage and rollback; it cannot claim that this permit-only pilot completes the municipal dashboard.

## Required verification

| Case | Acceptance behavior |
| --- | --- |
| Equal update timestamps spanning pages | Every ID appears exactly once in normalized state; continuation neither skips nor loops. |
| Same ID, changed content / late historical correction | Upsert applies the correction even when event time predates the prior cursor. |
| Moved geometry / removed record | Old and new cells match a full rebuild; tombstones require complete reconciliation. |
| Interrupted page, manifest or checkpoint writes | Replay recovers; old checkpoint remains valid until durable commit; conditional conflicts cannot advance it. |
| Empty successful poll | Commit/report successful acquisition without losing source coverage; daily window features still recompute. |
| Truncated snapshot, schema drift, missing IDs | Fail completeness, quarantine diagnostics and preserve committed state; no mass deletions. |
| 60/90/180/360-day cutoffs and no-new-data capex decay | Fixed UTC fixtures match the full baseline at boundaries, including the chosen inclusive/exclusive policy. |
| Dataset replacement / changed row IDs | Proven business-key/release policy prevents duplicate history or destructive reconciliation. |
| Retries / throttling / authorization failures | Bounded request behavior, truthful failure status and no checkpoint advance on incomplete acquisition. |
| Replay and full-rebuild parity | Same committed inputs/as-of yield equal normalized state and features; duplicates have no effect. |

Use deterministic local object-store and source fixtures first; verify the actual storage conditional-write primitive in an isolated authorized prefix before scheduling. Seven successful daily **shadow** cycles must include replay, boundary/failure checks, full-rebuild parity, source-age evidence and measured cost/storage. If corrections/deletions do not occur during those days, exercise them in fixtures rather than declaring live coverage proven.

## Handoff

Write the implementation plan after the source guarantees and authorized durable store are identified. Sequence acquisition/state correctness, full-baseline verification, then isolated daily scheduling. Decide on Actions versus another executor using measured bootstrap/delta/reconciliation runtime and resource requirements. Keep infrastructure retirement and production feature integration as separate reversible migrations with owners, data-retention evidence and rollback.
