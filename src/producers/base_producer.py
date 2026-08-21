"""Base Kafka Producer with Avro serialization, schema enforcement, and Dead-Letter Queue (DLQ) routing."""

import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union
from confluent_kafka import Producer
import fastavro
from pydantic import BaseModel
from src.config import settings

logger = logging.getLogger(__name__)


class BaseKafkaProducer:
    """Base Kafka Producer handling Avro serialization, key partitioning, and DLQ routing."""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        schema_file_path: Optional[Union[str, Path]] = None,
        dlq_topic: Optional[str] = None,
    ):
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.dlq_topic = dlq_topic or settings.topic_dlq

        self.conf = {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": f"{settings.service_name}-producer",
            "acks": "all",
            "retries": 5,
            "retry.backoff.ms": 300,
            "compression.type": "lz4",
            "linger.ms": 20,
            "batch.size": 65536,
        }
        self.producer = Producer(self.conf)
        self.parsed_schema = None

        if schema_file_path:
            self._load_schema(schema_file_path)

    def _load_schema(self, schema_path: Union[str, Path]):
        """Load and parse Avro schema file."""
        with open(schema_path, "r", encoding="utf-8") as f:
            raw_schema = json.load(f)
            self.parsed_schema = fastavro.parse_schema(raw_schema)

    def serialize_avro(self, record: Dict[str, Any]) -> bytes:
        """Serialize dictionary record into binary Avro."""
        if not self.parsed_schema:
            raise ValueError("Avro schema not loaded for producer")

        buf = io.BytesIO()
        fastavro.schemaless_writer(buf, self.parsed_schema, record)
        return buf.getvalue()

    def _delivery_report(self, err, msg):
        """Kafka delivery callback."""
        if err is not None:
            logger.error("Message delivery failed: %s", err)
        else:
            logger.debug("Message delivered to %s [%d] at offset %d", msg.topic(), msg.partition(), msg.offset())

    def produce(
        self,
        topic: str,
        key: str,
        payload: Union[Dict[str, Any], BaseModel],
        headers: Optional[Dict[str, str]] = None,
    ):
        """Produce typed message to Kafka or route to DLQ on schema failure."""
        try:
            if isinstance(payload, BaseModel):
                record_dict = payload.model_dump(mode="json")
            else:
                record_dict = payload

            if self.parsed_schema:
                serialized_bytes = self.serialize_avro(record_dict)
            else:
                serialized_bytes = json.dumps(record_dict).encode("utf-8")

            kafka_headers = [(k, v.encode("utf-8")) for k, v in (headers or {}).items()]

            self.producer.produce(
                topic=topic,
                key=key.encode("utf-8"),
                value=serialized_bytes,
                headers=kafka_headers,
                callback=self._delivery_report,
            )
            self.producer.poll(0)

        except Exception as e:
            logger.warning("Serialization/Produce failed for key %s: %s. Routing to DLQ.", key, e)
            self.route_to_dlq(
                failed_topic=topic,
                key=key,
                payload=payload,
                error_msg=str(e),
            )

    def route_to_dlq(
        self,
        failed_topic: str,
        key: str,
        payload: Any,
        error_msg: str,
    ):
        """Send malformed/failed payload to Dead-Letter Queue."""
        try:
            dlq_record = {
                "source_platform": settings.service_name,
                "failed_topic": failed_topic,
                "key": str(key),
                "error": error_msg,
                "raw_payload": str(payload),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
            self.producer.produce(
                topic=self.dlq_topic,
                key=f"dlq:{failed_topic}:{key}".encode("utf-8"),
                value=json.dumps(dlq_record).encode("utf-8"),
                callback=self._delivery_report,
            )
            self.producer.poll(0)
        except Exception as dlq_err:
            logger.critical("Failed to dispatch message to DLQ %s: %s", self.dlq_topic, dlq_err)

    def flush(self, timeout: float = 10.0):
        """Flush Kafka producer buffer."""
        self.producer.flush(timeout)
