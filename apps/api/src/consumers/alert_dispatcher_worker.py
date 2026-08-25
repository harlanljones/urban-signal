"""Catalyst-alert webhook dispatcher consumer (ADR 0008 §6).

Consumes `alerts.catalyst` on consumer group `cg_alerts` and dispatches each
alert through `WebhookDispatcher` (calibration gate + daily budget + webhook
fan-out). Calibration/budget skips are not failures; any real failure routes
the raw record straight to the shared DLQ and the loop continues.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from src.config import settings
from src.consumers.base_consumer import BaseKafkaConsumer
from src.producers.base_producer import BaseKafkaProducer
from src.schemas.models import CatalystAlert
from src.serving.alert_state import JsonAlertStateStore
from src.serving.dispatcher import WebhookDispatcher

logger = logging.getLogger(__name__)


class AlertDispatcherWorker:
    """Bridges the streaming alerts topic to the webhook dispatch path."""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        dispatcher: Optional[WebhookDispatcher] = None,
        state_store: Optional[Any] = None,
    ):
        if dispatcher is not None:
            self.dispatcher = dispatcher
        else:
            if state_store is None and settings.alert_state_file:
                state_store = JsonAlertStateStore(settings.alert_state_file)
            self.dispatcher = WebhookDispatcher(state_store=state_store)

        self.consumer = BaseKafkaConsumer(
            group_id=settings.cg_alerts,
            topics=[settings.topic_catalyst_alerts],
            bootstrap_servers=bootstrap_servers,
        )
        self.dlq_producer = BaseKafkaProducer(bootstrap_servers=bootstrap_servers)

    def process_record(self, record: Dict[str, Any], topic: str, key: str):
        """Dispatch one catalyst alert. Never raises: failures go to the DLQ."""
        try:
            # Filter to known fields so forward-compatible schema evolution on
            # the topic cannot crash construction.
            alert = CatalystAlert(**{k: v for k, v in record.items() if k in CatalystAlert.model_fields})
            asyncio.run(self.dispatcher.dispatch_alert(alert))
        except Exception as e:
            logger.exception("Alert dispatch failed key=%s: %s", key, e)
            self.dlq_producer.route_to_dlq(
                failed_topic=topic,
                key=key,
                payload=record,
                error_msg=str(e),
            )

    def start(self):
        """Start the alert dispatcher consume loop."""
        logger.info(
            "Starting Alert Dispatcher Worker (group=%s, topic=%s)...",
            settings.cg_alerts,
            settings.topic_catalyst_alerts,
        )
        self.consumer.start_consume_loop(
            record_handler=self.process_record,
            batch_size=100,
        )

    def close(self):
        """Release Kafka resources owned by this worker."""
        self.consumer.close()
        self.dlq_producer.flush()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = AlertDispatcherWorker()
    worker.start()
