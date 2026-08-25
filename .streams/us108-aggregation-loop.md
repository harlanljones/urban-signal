# Stream log — us108-aggregation-loop — 2026-08-24

## Claim

- **Stream id:** `us108-aggregation-loop`
- **Leaf files I will create/edit:**
  - `apps/api/src/consumers/feature_aggregation_worker.py` (consume loop, cooldown store, DLQ, metrics, `start()`/`__main__`)
  - `apps/api/src/consumers/alert_dispatcher_worker.py` (NEW — US-118 decision service; needed for US-108 AC#3)
  - `apps/api/src/schemas/avro/catalyst_alert.avsc` (add `city_id` default `nyc` — US-117 decision)
  - `apps/api/tests/unit/test_feature_aggregation_worker.py` (NEW)
  - `apps/api/tests/unit/test_alert_dispatcher_worker.py` (NEW)
  - `docker-compose.yml` (add `alert-dispatcher-worker` service; aggregation service entry already exists)
  - `.streams/us108-aggregation-loop.md`
- **Spine files I expect to need:** `apps/api/src/config.py` (two additive fields: `aggregation_cell_cooldown_seconds=300`, `alert_state_file=""`)

## Intent

US-108 AC#2/#3 against ADR 0008: consume loop on permits/311/sla/deeds under
`cg_inference`; per-record skip-backfill → skip-no-h3 → insert → cooldown-gated
`process_and_emit_cell`; straight-to-DLQ on failure with cooldown-set-before-compute
poison protection; bounded cooldown store; counters per ADR names; avsc `city_id`
fix so alerts stop DLQ'ing; dispatcher worker on `cg_alerts` closing
worker → alerts topic → dispatcher → webhook.

## Decisions

- source_mode threading through producers (US-115 contract) is NOT implemented
  anywhere yet (grep clean); out of scope here — the loop reads
  `record.get("source_mode")` defensively, absent ⇒ live (safe default).
- Re-alert suppression rides the cooldown window inherently: enriched/alert emit
  only happens inside a gated compute.
- Crime/street-cut/evictions excluded from the trigger list (ADR: four topics only).
- Verified empirically: fastavro drops unknown fields on write, so
  `top_catalyst_drivers` stays model-only naturally — no producer-side stripping.
- Dispatcher fake in tests must be `AsyncMock` (loop uses `asyncio.run`).

## Outcome

- Interlock: `pytest -m interlock` → **20 passed** after the config.py spine edit.
- Full suite: **807 passed, 3 skipped** (live probes disabled by env).
- Compose config validated (`docker compose config -q` OK).
- AC#1 ✓ (ADR 0008), AC#2 ✓ (loop + 23 new offline tests), AC#3 ⏳ code-complete,
  pending staging deploy of `feature-aggregation-worker` + `alert-dispatcher-worker`.

## Current step

Complete. Linear updated with evidence comment; ticket left In Progress until
staging end-to-end is observed (AC#3).

## Next step

If resumed: verify AC#3 in staging (compose up both workers; watch
`alerts.catalyst` → webhook POST; DLQ counters stay flat), then resolve US-108.
