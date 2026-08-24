"""PostGIS Spatial Sync Consumer Worker."""

import logging
from typing import Any, Dict, List, Optional
from src.config import settings
from src.consumers.base_consumer import BaseKafkaConsumer
from src.features.pipeline import SpatialFeaturePipeline
from src.storage.postgis_sync import PostGISSpatialSync

logger = logging.getLogger(__name__)


class PostGISWorker:
    """Consumes raw municipal streams, enriched features, and catalyst alerts to persist in PostGIS."""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        postgis_sync: Optional[PostGISSpatialSync] = None,
        feature_pipeline: Optional[SpatialFeaturePipeline] = None,
    ):
        self.postgis_sync = postgis_sync or PostGISSpatialSync()
        self.feature_pipeline = feature_pipeline
        self.topics = [
            settings.topic_permits,
            settings.topic_311,
            settings.topic_sla,
            settings.topic_deeds,
            settings.topic_enriched_h3,
            settings.topic_catalyst_alerts,
        ]
        self.consumer = BaseKafkaConsumer(
            group_id="postgis-spatial-sync-workers",
            topics=self.topics,
            bootstrap_servers=bootstrap_servers,
        )
        self.postgis_sync.init_tables()

    def process_record(self, record: Dict[str, Any], topic: str, key: str):
        """Dispatch incoming Kafka message to PostGIS tables."""
        try:
            self.postgis_sync.sync_kafka_record(record, topic)
        except Exception as e:
            logger.exception("Error syncing Kafka record to PostGIS (topic=%s, key=%s): %s", topic, key, e)

    def sync_from_feature_pipeline(self):
        """Trigger sync from internal DuckDB analytical pipeline."""
        if self.feature_pipeline:
            self.postgis_sync.sync_from_duckdb(self.feature_pipeline)

    def start(self):
        """Start PostGIS streaming sync loop."""
        logger.info("Starting PostGIS Spatial Sync Consumer Worker...")
        self.consumer.start_consume_loop(
            record_handler=self.process_record,
            batch_size=100,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = PostGISWorker()
    worker.start()
