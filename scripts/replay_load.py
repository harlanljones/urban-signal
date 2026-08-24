"""Controlled Kafka replay at a fixed produce rate (US-69 2x replay load test).

Reads the newest ``--per-partition`` messages from each raw.municipal.* topic
and re-publishes them (same key, same raw Avro value bytes) at a paced rate so
the topic tails grow at ``--rate`` records/second.  Re-publishing with the
deployed producer keys means partition placement follows the live keying
strategy — the replay exercises the same downstream path as a backfill.

Run on the host against the staging compose stack:

    KAFKA_BOOTSTRAP_SERVERS=localhost:9092 python scripts/replay_load.py \
        --rate 760 --per-partition 5000 --max-records 250000

Method and results live in ``docs/replay-lag-verification.md``.
"""

from __future__ import annotations

import argparse
import os
import time

from confluent_kafka import OFFSET_BEGINNING, Consumer, Producer, TopicPartition
from confluent_kafka.admin import AdminClient, OffsetSpec

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPICS = [
    "raw.municipal.permits",
    "raw.municipal.311",
    "raw.municipal.sla",
    "raw.municipal.deeds",
]


def collect(reader: Consumer, topic: str, per_partition: int) -> list[tuple[bytes, bytes, str]]:
    """Collect the newest ``per_partition`` messages of each partition of ``topic``."""
    md = reader.list_topics(topic=topic, timeout=10)
    parts = sorted(md.topics[topic].partitions)
    admin = AdminClient({"bootstrap.servers": BOOTSTRAP})
    fut = admin.list_offsets({TopicPartition(topic, p): OffsetSpec.latest() for p in parts})
    ends = {tp.partition: f.result(timeout=15).offset for tp, f in fut.items()}

    collected: list[tuple[bytes, bytes, str]] = []
    for p in parts:
        start = max(OFFSET_BEGINNING, ends[p] - per_partition)
        reader.assign([TopicPartition(topic, p)])
        reader.poll(0.1)
        reader.seek(TopicPartition(topic, p, start))
        count = 0
        empty_streak = 0
        while count < per_partition and empty_streak < 8:
            m = reader.poll(0.5)
            if m is None:
                empty_streak += 1
                continue
            if m.error():
                break
            collected.append((m.key(), m.value(), topic))
            count += 1
            empty_streak = 0
    return collected


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rate", type=float, required=True, help="target produce rate, records/sec")
    ap.add_argument("--per-partition", type=int, default=5000, help="newest messages to replay per partition")
    ap.add_argument("--max-records", type=int, default=250000, help="hard cap on total replayed messages")
    args = ap.parse_args(argv)

    reader = Consumer({"bootstrap.servers": BOOTSTRAP, "group.id": f"replay-reader-{int(time.time() * 1000)}"})
    prod = Producer({"bootstrap.servers": BOOTSTRAP})

    msgs: list[tuple[bytes, bytes, str]] = []
    for topic in TOPICS:
        msgs += collect(reader, topic, args.per_partition)
    reader.close()
    print(f"collected {len(msgs)} messages", flush=True)
    if not msgs:
        return 1

    total = min(len(msgs), args.max_records)
    msgs = msgs[:total]
    print(f"replaying {total} messages at {args.rate:.0f} rec/s", flush=True)

    start = time.time()
    produced = 0
    for key, value, topic in msgs:
        prod.produce(topic, key=key, value=value)
        produced += 1
        if produced % 1000 == 0:
            prod.poll(0)
            elapsed = time.time() - start
            target_done = elapsed * args.rate
            if produced > target_done:
                time.sleep((produced - target_done) / args.rate)
            print(f"produced {produced}/{total} ({produced / elapsed:.1f} rec/s)", flush=True)
    prod.flush()
    elapsed = time.time() - start
    print(f"done: {produced} messages in {elapsed:.1f}s ({produced / elapsed:.1f} rec/s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())