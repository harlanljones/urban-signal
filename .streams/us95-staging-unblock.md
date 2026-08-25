# Stream log — us95-staging-unblock — 2026-08-24

## Claim

- **Stream id:** `us95-staging-unblock`
- **Leaf files edited:**
  - `apps/api/tests/unit/test_kafka_partition_wiring.py` (NEW)
  - `deploy/k8s/kafka/kafka-topics.yaml`
  - `docs/replay-lag-verification.md`, `docs/expansion-roadmap.md` (scorecard note)
- **Spine files edited:** `apps/api/src/config.py` (one additive field:
  `kafka_topic_partitions=12`) and `apps/api/src/consumers/base_consumer.py`
  (uses the setting instead of hardcoded 3) — additive, gate run below.
- **Note:** found stale `.streams/us108-aggregation-loop.md` claim with no
  dispatch-log entry (per parallel-streams.md = never ran); no leaf edits from
  it exist in this worktree. Left untouched for its owner.

## Outcome

US-69 gating-finding remainder closed:

1. Consumer backlog drained (measured live): h3-enrich-workers total lag ~1.2k
   records (fresh tail only), postgis group ~0.3k — vs ~3.9M peak in US-69.
2. Partition declaration drift reconciled: Strimzi raw topics 6/6/3/3 → 12;
   consumer auto-provision default 3 → `settings.kafka_topic_partitions` (12);
   regression test locks settings == manifest == provisioning count.
3. Keying deviation already resolved by decision: ADR 0008 rejects `city_id+h3`
   raw-keying while the aggregation worker is single-instance.

Gates: `pytest -m interlock` 20 passed; full unit suite 777 passed / 3 skipped
(live probes); ruff clean on touched files (pre-existing debt elsewhere
unchanged, verified against HEAD).

## Next step

Frontier for US-95's operational tail: implement US-108 (consume loop +
alert dispatcher worker per ADR 0008) so features aggregate in staging and the
60-day warm-up clocks can start. Then start the G7 24h freshness soak clock.
