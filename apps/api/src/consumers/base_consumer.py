"""Base Kafka Consumer with Avro deserialization, batch polling, and graceful shutdown."""

import io
import json
import logging
import signal
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from confluent_kafka import Consumer, KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
import fastavro
from src.config import settings

logger = logging.getLogger(__name__)


class BaseKafkaConsumer:
    """Base Kafka Consumer managing subscription, Avro deserialization, and batch processing."""

    def __init__(
        self,
        group_id: str,
        topics: List[str],
        bootstrap_servers: Optional[str] = None,
        schema_file_path: Optional[Union[str, Path]] = None,
        auto_offset_reset: str = "earliest",
        max_poll_records: int = 500,
    ):
        self.group_id = group_id
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.max_poll_records = max_poll_records
        self.running = True

        self._ensure_topics_exist()

        self.conf = {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": self.group_id,
            "auto.offset.reset": auto_offset_reset,
            "enable.auto.commit": False,
            "max.poll.interval.ms": 300000,
            "session.timeout.ms": 45000,
        }
        self.consumer = Consumer(self.conf)
        self.parsed_schema = None
        self.schemas_by_topic: Dict[str, Any] = {}

        self._load_all_avro_schemas()
        if schema_file_path:
            self._load_schema(schema_file_path)

        self._setup_signals()

    def _load_all_avro_schemas(self):
        """Auto-discover and load schemas from schemas/avro directory mapped by topic name."""
        avro_dir = Path(__file__).parent.parent / "schemas" / "avro"
        topic_schema_map = {
            settings.topic_permits: "permit_event.avsc",
            settings.topic_311: "complaint_311_event.avsc",
            settings.topic_sla: "sla_license_event.avsc",
            settings.topic_deeds: "deed_event.avsc",
            settings.topic_street_cut: "street_cut_event.avsc",
            settings.topic_enriched_h3: "enriched_h3_feature.avsc",
            settings.topic_catalyst_alerts: "catalyst_alert.avsc",
            settings.topic_bank_branches: "bank_branch_event.avsc",
        }
        if avro_dir.exists():
            for topic, schema_name in topic_schema_map.items():
                schema_file = avro_dir / schema_name
                if schema_file.exists():
                    try:
                        with open(schema_file, "r", encoding="utf-8") as f:
                            raw = json.load(f)
                            self.schemas_by_topic[topic] = fastavro.parse_schema(raw)
                    except Exception as e:
                        logger.warning("Failed to load schema %s: %s", schema_name, e)

    def _ensure_topics_exist(self):
        """Pre-create subscribed topics if they don't already exist on the broker."""
        try:
            admin_client = AdminClient({"bootstrap.servers": self.bootstrap_servers})
            new_topics = [
                NewTopic(t, num_partitions=settings.kafka_topic_partitions, replication_factor=1)
                for t in self.topics
            ]
            futures = admin_client.create_topics(new_topics)
            for topic, future in futures.items():
                try:
                    # Topic provisioning is best-effort.  An unavailable broker must
                    # not prevent workers that are used for local processing/tests
                    # from being constructed indefinitely.
                    future.result(timeout=1.0)
                    logger.info("Created topic '%s'", topic)
                except KafkaException as e:
                    if e.args[0].code() != KafkaError.TOPIC_ALREADY_EXISTS:
                        logger.debug("Topic '%s' note: %s", topic, e)
                except Exception as e:
                    logger.debug("Topic '%s' provisioning timed out or failed: %s", topic, e)
        except Exception as e:
            logger.warning("Could not pre-verify/create topics: %s", e)

    def close(self):
        """Close the underlying Kafka consumer when a worker is not started."""
        self.running = False
        self.consumer.close()

    def _load_schema(self, schema_path: Union[str, Path]):
        with open(schema_path, "r", encoding="utf-8") as f:
            raw_schema = json.load(f)
            self.parsed_schema = fastavro.parse_schema(raw_schema)

    def _setup_signals(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        logger.info("Shutdown signal (%s) received. Exiting consumer loop...", sig)
        self.running = False

    def deserialize_payload(self, raw_bytes: bytes, topic: Optional[str] = None) -> Dict[str, Any]:
        """Deserialize raw message bytes via topic-specific Avro schema or JSON fallback."""
        if topic and topic in self.schemas_by_topic:
            try:
                buf = io.BytesIO(raw_bytes)
                return fastavro.schemaless_reader(buf, self.schemas_by_topic[topic])
            except Exception:
                pass

        if self.parsed_schema:
            try:
                buf = io.BytesIO(raw_bytes)
                return fastavro.schemaless_reader(buf, self.parsed_schema)
            except Exception:
                pass

        for schema in self.schemas_by_topic.values():
            try:
                buf = io.BytesIO(raw_bytes)
                return fastavro.schemaless_reader(buf, schema)
            except Exception:
                pass

        return json.loads(raw_bytes.decode("utf-8"))

    def start_consume_loop(
        self,
        record_handler: Callable[[Dict[str, Any], str, str], None],
        batch_size: int = 100,
        poll_timeout: float = 1.0,
    ):
        """Consume messages and process them via record_handler(record_dict, topic, key)."""
        logger.info("Subscribing consumer group '%s' to topics %s", self.group_id, self.topics)
        self.consumer.subscribe(self.topics)

        batch: List[Any] = []
        try:
            while self.running:
                msg = self.consumer.poll(timeout=poll_timeout)
                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    elif msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                        logger.warning("Topic not yet available (%s), continuing poll...", msg.error().str())
                        continue
                    else:
                        logger.error("Kafka consumer error: %s", msg.error())
                        break

                key = msg.key().decode("utf-8") if msg.key() else ""
                topic = msg.topic()

                try:
                    record = self.deserialize_payload(msg.value(), topic=topic)
                    record_handler(record, topic, key)
                    batch.append(msg)

                    if len(batch) >= batch_size:
                        self.consumer.commit(asynchronous=False)
                        batch.clear()

                except Exception as e:
                    logger.exception("Error processing message key %s from topic %s: %s", key, topic, e)

        finally:
            if batch:
                self.consumer.commit(asynchronous=False)
            self.consumer.close()
            logger.info("Consumer group '%s' shut down successfully.", self.group_id)
