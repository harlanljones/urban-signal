"""Partition-count wiring across settings, consumer auto-provisioning, and Strimzi manifests.

US-69 drift reconciliation: the scaling plan targets >= 12 partitions on
raw.municipal.*; the compose broker was bumped manually while the manifests
(6/6/3/3) and the consumer creation default (3) still disagreed.
"""

import re
from pathlib import Path
from unittest.mock import MagicMock

from src.config import settings

REPO_ROOT = Path(__file__).resolve().parents[4]
STRIMZI_MANIFEST = REPO_ROOT / "deploy" / "k8s" / "kafka" / "kafka-topics.yaml"

RAW_TOPICS = (
    "raw.municipal.permits",
    "raw.municipal.311",
    "raw.municipal.sla",
    "raw.municipal.deeds",
)


def _strimzi_declared_partitions() -> dict[str, int]:
    text = STRIMZI_MANIFEST.read_text()
    declared: dict[str, int] = {}
    for block in text.split("---"):
        name = re.search(r"topicName:\s*(\S+)", block)
        parts = re.search(r"partitions:\s*(\d+)", block)
        if name and parts:
            declared[name.group(1)] = int(parts.group(1))
    return declared


def test_partition_default_meets_scaling_plan_target():
    assert settings.kafka_topic_partitions >= 12, (
        "expansion roadmap scaling note requires >= 12 partitions on raw topics"
    )


def test_consumer_provisions_topics_with_configured_partition_count(monkeypatch):
    from src.consumers import base_consumer as bc

    admin = MagicMock()
    admin.create_topics.return_value = {}
    monkeypatch.setattr(bc, "AdminClient", lambda *_: admin)
    monkeypatch.setattr(bc, "Consumer", lambda *_: MagicMock())

    consumer = bc.BaseKafkaConsumer(group_id="partition-wiring-test", topics=list(RAW_TOPICS))
    consumer.close()

    created = admin.create_topics.call_args[0][0]
    assert {t.topic for t in created} == set(RAW_TOPICS)
    off_plan = sorted(t.topic for t in created if t.num_partitions != settings.kafka_topic_partitions)
    assert not off_plan, f"topics provisioned off the configured partition count: {off_plan}"


def test_strimzi_manifest_matches_configured_count_for_every_raw_topic():
    declared = _strimzi_declared_partitions()
    missing = [t for t in RAW_TOPICS if t not in declared]
    assert not missing, f"raw topics absent from {STRIMZI_MANIFEST.name}: {missing}"

    drifted = {
        t: p for t, p in declared.items() if t in RAW_TOPICS and p != settings.kafka_topic_partitions
    }
    assert not drifted, (
        f"Strimzi declarations drifted from the consumer provisioning count "
        f"({settings.kafka_topic_partitions}): {drifted}. "
        f"Production-as-declared must meet the >= 12 partition target."
    )
