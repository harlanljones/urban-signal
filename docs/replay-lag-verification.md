# US-69: Kafka partitioning + 2× replay consumer-lag verification

Verification run **2026-08-24** against the live staging compose stack
(`docker compose`, single KRaft broker). Closes the two infra-checklist items
from `docs/expansion-roadmap.md` §2 "Scaling notes" and §1.3.

## 1 · Measured partition count and keying strategy

### Partition count (live broker)

`kafka-topics --describe` / `kafka-get-offsets` on the running broker:

| Topic | Partitions | Replication |
|---|---|---|
| `raw.municipal.permits` | **12** | 1 |
| `raw.municipal.311` | **12** | 1 |
| `raw.municipal.sla` | **12** | 1 |
| `raw.municipal.deeds` | **12** | 1 |
| `enriched.spatial.h3` | 12 | 1 |
| `alerts.catalyst` | 3 | 1 |
| `dlq.schema.failures` | 1 | 1 |

Plan target **≥ 12 partitions for the four raw topics → met on the compose stack.**

**Declaration drift (finding):** three different partition counts exist depending on
which layer you read:

- Live broker (compose): **12** for every raw topic.
- `deploy/k8s/kafka/kafka-topics.yaml` (Strimzi, production target): `raw.municipal.permits` = **6**, `raw.municipal.311` = **6**, `raw.municipal.sla` = **3**, `raw.municipal.deeds` = **3**.
- Consumer code default (`apps/api/src/consumers/base_consumer.py:81` `_ensure_topics_exist`): creates new topics with **3** partitions.

Production-as-declared would NOT meet the ≥ 12 target; only the manually configured
compose broker does. Reconcile the Strimzi manifests (and the consumer default)
before Wave 2 / signal expansion.

### Keying strategy (source)

Producers key every raw record as `"{city_id}:{record_id}"`:

- `apps/api/src/producers/dob_permits_producer.py:375` → `f"{event.city_id}:{event.job_id}"`
- `apps/api/src/producers/complaints_311_producer.py:337` → `f"{event.city_id}:{event.incident_id}"`
- `apps/api/src/producers/sla_licenses_producer.py:340` → `f"{event.city_id}:{event.license_id}"`
- `apps/api/src/producers/deeds_acris_producer.py:339` → `f"{event.city_id}:{event.doc_id}"`
- `scripts/backfill_loader.py:178` → `f"{resolved_city}:{job_id|incident_id|license_id|doc_id|rec_id}"`

Plan target **`city_id+h3` keying → NOT implemented.** The record id (not the H3
cell) drives partition placement, so per-cell ordering is not preserved at the raw
topic level. This is a deviation from the scaling note.

**Observed partition skew (finding):** log-end offsets are concentrated on exactly
partitions 0/1/2 of every raw topic, with the rest near-empty:

| Topic | Partitions 0/1/2 (log-end) | Partitions 3–11 (log-end) |
|---|---|---|
| `raw.municipal.311` | ~1.37 M each | ~1.9 k each |
| `raw.municipal.deeds` | ~790 k each | ~1.4 k each |
| `raw.municipal.permits` | ~28 k each | ~1.8 k each |
| `raw.municipal.sla` | ~40 k each | ~2 k each |

Two full-history backfill loads landed almost entirely on three partitions, which is
only possible if those loads used coarse/constant keys (hash → 3 partitions). The
skew is consistent with the keying deviation above and concentrates the entire
backfill drain burden on a few consumers.

## 2 · 2× replay consumer-lag test

Target (§1.3): **consumer lag p95 < 60 s at 2× replay load.**

### Method

- **Baseline consumption rate** `R`: measured on `h3-enrich-workers` as
  `7,600 records / 20 s ≈ 380 rec/s`.
- **Replay rate**: `2R = 760 rec/s`.
- **Replay**: re-published the newest tail of all four raw topics
  (`scripts/replay_load.py --rate 760`) using the deployed producer keys and raw
  Avro bytes — 70,967 messages over ~92 s at an achieved 770 rec/s. This exercises
  the same downstream path as a backfill.
- **Lag measurement** (`scripts/replay_lag_measure.py`): per-partition time-based
  lag = age of the message at the group's committed offset (produce timestamp via
  `Consumer.seek` + read, `AdminClient` committed offsets and log-end), sampled
  repeatedly from the production groups `h3-enrich-workers` and
  `postgis-spatial-sync-workers`.

### Observed p95 lag (seconds)

| Phase | `h3-enrich-workers` p95 | `postgis-spatial-sync-workers` p95 |
|---|---|---|
| Baseline (pre-replay, 11 samples) | 6,822 – 7,099 s | 6,661 – 6,943 s |
| During 2× replay + drain (7 samples) | 7,420 – 7,607 s | 7,307 – 7,490 s |

Peak total backlog during the test: ~3.9 M records (`h3-enrich-workers`).
Max single-partition lag reached ~11,743 s (~3.3 h).

### Result

**Target missed by ~125×.** p95 consumer lag is ~110–127 minutes, not < 60 s.

- The dominant contributor is a **pre-existing multi-million-record backlog** (prior
  full-history backfills of 311/deeds) that the groups are still draining at
  ~380 rec/s.
- The 2× replay adds a fresh tail faster than the groups consume, so p95 rises
  ~500–700 s over the test window.
- No consumer errors or DLQ traffic were observed during the replay (worker logs
  clean).

Per US-69 acceptance, **this missed target gates further feed growth** (Wave 2 /
signal-expansion tickets) until the backlog is drained and the keying/partition
declaration drift in §1 is reconciled.

## Reproducing

```bash
# 1. Baseline consumption rate (records / 20 s)
docker exec urbansignal-kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 --describe --group h3-enrich-workers

# 2. Replay at 2x baseline (~380 rec/s baseline -> ~760 rec/s)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
  python scripts/replay_load.py --rate 760 --per-partition 5000 --max-records 250000

# 3. Sample time-based lag in a loop during the replay
while true; do
  KAFKA_BOOTSTRAP_SERVERS=localhost:9092 python scripts/replay_lag_measure.py
  sleep 15
done
```

Aggregate the `p95_lag_seconds` across samples and compare against the 60 s target.