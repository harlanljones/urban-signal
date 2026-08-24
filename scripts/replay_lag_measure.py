"""Time-based consumer lag sampler for Urban Signal Kafka topics (US-69).

Measures per-partition consumer lag in SECONDS for the production consumer
groups on the raw.municipal.* topics:

    lag_seconds(partition) = wall_clock_now
                             - produce_timestamp of the message at the
                               group's committed offset for that partition

A partition with zero backlog reports 0 s. Prints one JSON array per sample.

Run on the host against the staging compose stack:

    KAFKA_BOOTSTRAP_SERVERS=localhost:9092 python scripts/replay_lag_measure.py

Used by the 2x replay load test in ``docs/replay-lag-verification.md``.
"""

from __future__ import annotations

import json
import os
import time

from confluent_kafka import Consumer, TopicPartition
from confluent_kafka._model import ConsumerGroupTopicPartitions
from confluent_kafka.admin import AdminClient, OffsetSpec

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
GROUPS = ["h3-enrich-workers", "postgis-spatial-sync-workers"]
RAW_TOPICS = [
    "raw.municipal.permits",
    "raw.municipal.311",
    "raw.municipal.sla",
    "raw.municipal.deeds",
]


def partitions_of(admin: AdminClient, topic: str) -> list[int]:
    md = admin.list_topics(topic=topic, timeout=10)
    t = md.topics.get(topic)
    if not t:
        return []
    return sorted(p.id for p in t.partitions.values())


def committed_offsets(admin: AdminClient, group: str) -> dict[tuple[str, int], int]:
    res = admin.list_consumer_group_offsets([ConsumerGroupTopicPartitions(group_id=group)])
    out: dict[tuple[str, int], int] = {}
    for _, future in res.items():
        try:
            result = future.result(timeout=15)
        except Exception:  # noqa: BLE001  # a missing group must not fail the sample
            continue
        for tp in result.topic_partitions:
            if tp.offset is None:
                continue
            out[(tp.topic, tp.partition)] = tp.offset
    return out


def log_end_offsets(admin: AdminClient, topic: str) -> dict[int, int]:
    parts = {TopicPartition(topic, p): OffsetSpec.latest() for p in partitions_of(admin, topic)}
    fut = admin.list_offsets(parts)
    out: dict[int, int] = {}
    for tp, f in fut.items():
        res = f.result(timeout=15)
        out[tp.partition] = res.offset
    return out


def first_msg_ts(reader: Consumer, topic: str, partition: int, offset: int) -> int | None:
    reader.assign([TopicPartition(topic, partition)])
    reader.poll(0.1)
    reader.seek(TopicPartition(topic, partition, offset))
    deadline = time.time() + 5
    while time.time() < deadline:
        m = reader.poll(0.5)
        if m is not None:
            return m.timestamp()[1]
    return None


def sample() -> dict[str, dict[tuple[str, int], dict[str, object]]]:
    admin = AdminClient({"bootstrap.servers": BOOTSTRAP})
    reader = Consumer({"bootstrap.servers": BOOTSTRAP, "group.id": f"lag-reader-{int(time.time() * 1000)}"})
    groups: dict[str, dict[tuple[str, int], dict[str, object]]] = {}
    for group in GROUPS:
        committed = committed_offsets(admin, group)
        per_partition: dict[tuple[str, int], dict[str, object]] = {}
        for topic in RAW_TOPICS:
            for part, leo in log_end_offsets(admin, topic).items():
                key = (topic, part)
                co = committed.get(key)
                if co is None:
                    continue
                if co >= leo:
                    per_partition[key] = {"lag_records": 0, "lag_seconds": 0.0}
                    continue
                cts = first_msg_ts(reader, topic, part, co)
                if cts is None:
                    per_partition[key] = {"lag_records": leo - co, "lag_seconds": None}
                    continue
                lag_s = max(0.0, (time.time() * 1000.0 - cts) / 1000.0)
                per_partition[key] = {"lag_records": leo - co, "lag_seconds": round(lag_s, 1)}
        groups[group] = per_partition
    reader.close()
    return groups


def main() -> int:
    rows = []
    for group, parts in sample().items():
        lag_secs = [p["lag_seconds"] for p in parts.values() if p["lag_seconds"] is not None]
        lag_recs = sum(int(p["lag_records"]) for p in parts.values())
        p95 = 0.0
        if lag_secs:
            lag_secs_sorted = sorted(lag_secs)
            p95 = lag_secs_sorted[int(0.95 * (len(lag_secs_sorted) - 1))]
        rows.append(
            {
                "group": group,
                "ts": time.time(),
                "partitions_with_lag": len([p for p in parts.values() if p["lag_records"] > 0]),
                "total_lag_records": lag_recs,
                "p95_lag_seconds": round(p95, 1),
                "max_lag_seconds": round(max(lag_secs), 1) if lag_secs else 0.0,
                "lag_seconds_list": lag_secs,
            }
        )
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())