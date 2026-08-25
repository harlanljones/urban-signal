# ADR 0008: Realtime Aggregation & Catalyst-Alert Dispatch Path

**Status:** Accepted
**Date:** 2026-08-24
**Scope:** urban-signal
**Supersedes:** —
**Companion:** US-112 (Wayfinder map); US-108 implements the aggregation
consume loop; US-104 backfill; decisions recorded per ticket in
US-113/114/115/116/117/118

## Context

The feature-aggregation and catalyst-alert path is library-only: nothing
consumes the raw municipal topics to compute per-cell features on a trigger,
and nothing reads `alerts.catalyst` for webhook dispatch (`cg_alerts` is
defined but unused; `postgis_worker` only persists). The 2026-08-23 signal
survey and US-108 require a decided design before the staging path
(worker → alerts topic → dispatcher → webhook) can go live. A Wayfinder map
(US-112) resolved the design decisions by grilling (HITL); this ADR records
the decided contract so US-108 can implement it.

## Decision

Six decisions, resolved on the map's tickets, form the contract.

### 1. Aggregation trigger loop (US-113)

A new consume loop subscribes the four feature-relevant raw topics
(`raw.municipal.permits`, `.311`, `.sla`, `.deeds`) under consumer group
`cg_inference` (`ml-inference-workers`), a config-driven topic list mirroring
`SpatialEnrichmentWorker` — no new producer. **Crime is excluded** until it
clears ablation (US-71) and becomes a feature. Per record, in order: skip if
`source_mode == "backfill"` (count `urban_signal_aggregation_backfill_skipped_records_total`);
skip if no `h3_res9` (null-coord sources have no cell to aggregate); insert
the record into the aggregation pipeline's raw table (the pipeline needs the
row before its window queries run); then trigger `process_and_emit_cell` for
the cell subject to the cooldown.

### 2. Per-cell aggregation cadence (US-114)

`aggregation_cell_cooldown_seconds: int = 300` bounds recompute to once per
5 min per hot cell (≈5 DuckDB window queries per cell make per-record
triggering too expensive). A record touching a hot cell is **absorbed** —
recompute skipped, no enriched emit, no alert re-check; alert suppression
rides the same window. Absorbs are counted
(`urban_signal_aggregation_absorbed_records_total{city_id, feed}`) with a
debug-level log. Enriched records are emitted only on an actual compute.

The aggregation worker is **single-instance by construction**: its DuckDB
feature pipeline and cooldown store are in-memory. `--scale N` is not a
supported mode (each instance would hold a partial feature store), so the
per-instance cooldown is accepted as documented; scaling requires a shared
feature store (out of scope). The roadmap's `city_id+h3` raw-key direction is
a future precondition if a shared store ever lands, not a change made here.

### 3. Backfill interaction (US-115)

Every raw event carries `source_mode` (`"live"` / `"backfill"`, default
`"live"`) threaded through parse → avro → raw topic; the scheduler's producers
emit `"live"`, the backfill loader passes `"backfill"`. The aggregation loop
skips backfill-marked records entirely, so a flood of historical records
neither recomputes cells nor emits alert storms. No global alert-suppression
switch (coarse — could swallow a live alert during a long backfill).
Backfill keeps seeding the durable watermark (US-106, never lowers); live
must not reprocess the backfilled window. PostGIS persists backfill records
for parity (INSERT OR REPLACE is idempotent); aggregation and backfill
coverage are separate by design (batch `snapshot_builder` owns backfill
coverage).

### 4. Failure and DLQ semantics (US-116)

Aggregation and dispatch failures route **straight to the shared
`topic_dlq`** via `BaseKafkaProducer.route_to_dlq` (same envelope, key
`dlq:<failed_topic>:<key>`, `failed_topic` = the raw topic or
`alerts.catalyst`). No retry loop — the architecture has none, batch-commit
advances offsets, and failures are deterministic bugs best surfaced on the
DLQ. A failing cell or webhook never kills the loop (per-record
try/except → DLQ → continue). **Poison-message protection**: the cell's
cooldown timestamp is set *before* compute, so a consistently-failing cell
emits at most one DLQ record per cooldown window; the cooldown store is
bounded (capped with eviction).

### 5. Catalyst alert emission contract (US-117)

`catalyst_alert.avsc` gains `city_id` with `default: "nyc"` (backward-
compatible Avro evolution). This was not cosmetic: the model carried
`city_id` but the avsc did not, so `fastavro` rejected every emitted alert as
an unknown field and routed the lot to the DLQ — the gap made the topic empty
in practice. `top_catalyst_drivers` stays model-only (default `[]`); the
webhook payload needs no driver breakdown. Re-alert emission is suppressed
for a cell already alerted within the cell cooldown window.

### 6. Alert dispatcher consumer (US-118)

A new `src/consumers/alert_dispatcher_worker.py` on group `webhook-dispatchers`
(`cg_alerts`), its own compose service. Per message, construct a
`CatalystAlert` (reading `city_id` from the now-complete avro) and run
`WebhookDispatcher.dispatch_alert` via `asyncio.run` (the loop is sync),
wrapped in try/except → straight-to-DLQ → continue. The alert-state store is
`JsonAlertStateStore` at a configured path (restart-safe calibration gate,
shared with the serving/calibration writes); the daily budget stays in-memory
`CityAlertBudget` (restart resets the counter — acceptable for a throttle,
budget is not a safety gate). Calibration/budget skips are not failures.

## Resolved fog (formerly map "Not yet specified")

- **Coexistence with `snapshot_builder`:** the batch Workers-KV path (dashboard
  catalyst list) and the streaming webhook path are complementary surfaces —
  no dedup contract needed; both are driven by the same LIMS threshold.
- **Multi-city fan-out:** aggregation is single-instance (one group owns all
  partitions); the dispatcher's per-city calibration gate + daily budget
  already key on `city_id`; one consumer group covers all 17 cities.

## Alternatives Considered

- **Dedicated backfill topics** (`raw.backfill.*`): rejected — the backfill
  loader reuses the scheduler's producers/topics/keys, and a parallel topic
  set would double the surface and split parity/enrichment paths. An event
  field (`source_mode`) lets each consumer choose its policy.
- **Retry loops / redelivery for failed records:** rejected — no retry
  machinery exists, batch-commit advances offsets, and failures are
  deterministic bugs; the DLQ is the surface.
- **Global alert-suppression switch during backfill:** rejected — coarse and
  could swallow a real live alert; the per-record source-mode skip is precise.
- **Partition-keying cells (`city:h3`) for the aggregation loop:** rejected
  for now — the worker is single-instance by construction (in-memory store),
  and cross-topic cell locality isn't guaranteed even with cell keys; kept as
  a future precondition for a shared store.

## Consequences

- US-108 implements the aggregation consume loop against this contract; AC#1
  (trigger semantics + topic contract) is satisfied by this ADR.
- Adding `city_id` to the alert avsc is the fix that makes `alerts.catalyst`
  carry real alerts; existing on-topic records deserialize with the default.
- The dispatcher service reads calibration from a durable JSON store; budget
  resets on restart (documented).
- Any new signal family (street-cut, evictions, STR) joins the trigger loop
  only after clearing its ablation gate, mirroring crime's exclusion.