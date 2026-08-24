"""Spatial enrichment consumer worker joining municipal raw streams to H3 grids and persisting to PostGIS/DuckDB."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd
from src.config import settings
from src.consumers.base_consumer import BaseKafkaConsumer
from src.features.pipeline import SpatialFeaturePipeline
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)


class SpatialEnrichmentWorker:
    """Consumes raw municipal streams, normalizes H3 coordinates, and sinks to analytical storage."""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        feature_pipeline: Optional[SpatialFeaturePipeline] = None,
    ):
        self.feature_pipeline = feature_pipeline or SpatialFeaturePipeline()
        self.indexer = H3SpatialIndexer()
        self.topics = [
            settings.topic_permits,
            settings.topic_311,
            settings.topic_sla,
            settings.topic_deeds,
        ]
        self.consumer = BaseKafkaConsumer(
            group_id=settings.cg_h3_enrichment,
            topics=self.topics,
            bootstrap_servers=bootstrap_servers,
        )

    def process_record(self, record: Dict[str, Any], topic: str, key: str):
        """Process incoming raw record and index into H3 hierarchy."""
        lat = record.get("latitude")
        lng = record.get("longitude")

        if lat is None or lng is None:
            logger.debug("Skipping non-geocoded record key=%s", key)
            return

        # Ensure H3 fields exist
        if not record.get("h3_res9"):
            hierarchy = self.indexer.get_multi_res_hierarchy(float(lat), float(lng))
            record.update(hierarchy)

        # Route to appropriate DuckDB / PostGIS table
        if topic == settings.topic_permits:
            df = pd.DataFrame([{
                "job_id": record.get("job_id"),
                "job_type": record.get("job_type"),
                "latitude": float(record["latitude"]),
                "longitude": float(record["longitude"]),
                "estimated_cost": float(record.get("estimated_cost", 0.0)),
                "issuance_date": pd.to_datetime(record.get("issuance_date") or datetime.now(timezone.utc)),
                "h3_res7": record.get("h3_res7"),
                "h3_res8": record.get("h3_res8"),
                "h3_res9": record.get("h3_res9"),
                "ingested_at": pd.to_datetime(record.get("ingested_at") or datetime.now(timezone.utc)),
            }])
            self.feature_pipeline.insert_permits(df)

        elif topic == settings.topic_311:
            df = pd.DataFrame([{
                "incident_id": record.get("incident_id"),
                "complaint_type": record.get("complaint_type"),
                "category": record.get("category", "OTHER"),
                "latitude": float(record["latitude"]),
                "longitude": float(record["longitude"]),
                "created_date": pd.to_datetime(record.get("created_date") or datetime.now(timezone.utc)),
                "h3_res7": record.get("h3_res7"),
                "h3_res8": record.get("h3_res8"),
                "h3_res9": record.get("h3_res9"),
                "ingested_at": pd.to_datetime(record.get("ingested_at") or datetime.now(timezone.utc)),
            }])
            self.feature_pipeline.insert_complaints(df)

        elif topic == settings.topic_sla:
            df = pd.DataFrame([{
                "license_id": record.get("license_id"),
                "license_type": record.get("license_type"),
                "latitude": float(record["latitude"]),
                "longitude": float(record["longitude"]),
                "effective_date": pd.to_datetime(record.get("effective_date") or datetime.now(timezone.utc)),
                "license_status": record.get("license_status", "ACTIVE"),
                "h3_res7": record.get("h3_res7"),
                "h3_res8": record.get("h3_res8"),
                "h3_res9": record.get("h3_res9"),
                "ingested_at": pd.to_datetime(record.get("ingested_at") or datetime.now(timezone.utc)),
            }])
            self.feature_pipeline.insert_sla(df)

        elif topic == settings.topic_deeds:
            df = pd.DataFrame([{
                "doc_id": record.get("doc_id"),
                "doc_type": record.get("doc_type"),
                "document_amount": float(record.get("document_amount", 0.0)),
                "recorded_date": pd.to_datetime(record.get("recorded_date") or datetime.now(timezone.utc)),
                "latitude": float(record["latitude"]) if record.get("latitude") else None,
                "longitude": float(record["longitude"]) if record.get("longitude") else None,
                "h3_res7": record.get("h3_res7"),
                "h3_res8": record.get("h3_res8"),
                "h3_res9": record.get("h3_res9"),
                "ingested_at": pd.to_datetime(record.get("ingested_at") or datetime.now(timezone.utc)),
            }])
            self.feature_pipeline.insert_deeds(df)

    def start(self):
        """Start the spatial enrichment consumer loop."""
        logger.info("Starting Spatial Enrichment Worker...")
        self.consumer.start_consume_loop(
            record_handler=self.process_record,
            batch_size=200,
        )

    def close(self):
        """Release Kafka and analytical resources owned by this worker."""
        self.consumer.close()
        close = getattr(self.feature_pipeline, "close", None)
        if close:
            close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = SpatialEnrichmentWorker()
    worker.start()
