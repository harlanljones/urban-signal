"""Feature aggregation consumer worker emitting enriched H3 records and catalyst alerts.

US-108 / ADR 0008: consumes the four feature-relevant raw topics under
consumer group `cg_inference`, inserts each live record into the aggregation
pipeline's raw table, then recomputes and re-emits the touched H3 cell subject
to a per-cell cooldown. Backfill-marked records are skipped entirely; failures
route straight to the shared DLQ with the cell cooldown set before compute
(poison-message protection). Single-instance by construction.
"""

import logging
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from prometheus_client import Counter

from src.config import settings
from src.consumers.base_consumer import BaseKafkaConsumer
from src.features.pipeline import SpatialFeaturePipeline
from src.producers.base_producer import BaseKafkaProducer
from src.schemas.models import CatalystAlert, EnrichedH3Feature
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)

BACKFILL_SKIPPED = Counter(
    "urban_signal_aggregation_backfill_skipped_records_total",
    "Raw records skipped by aggregation because source_mode == backfill",
)
ABSORBED_RECORDS = Counter(
    "urban_signal_aggregation_absorbed_records_total",
    "Records absorbed because their cell is inside the aggregation cooldown window",
    ["city_id", "feed"],
)


class CellCooldownStore:
    """Bounded in-memory per-cell cooldown deadlines (ADR 0008 §2/§4).

    try_acquire claims a compute slot for the cell. The deadline is written
    *before* compute runs, so a consistently-failing cell DLQs at most one
    record per cooldown window instead of poisoning every record on topic.
    """

    def __init__(self, cooldown_seconds: int, max_cells: int = 10_000):
        self.cooldown_seconds = cooldown_seconds
        self.max_cells = max_cells
        self._hot_until: "OrderedDict[str, float]" = OrderedDict()

    def try_acquire(self, cell_key: str) -> bool:
        now = time.monotonic()
        deadline = self._hot_until.get(cell_key)
        if deadline is not None:
            if deadline > now:
                self._hot_until.move_to_end(cell_key)
                return False
            del self._hot_until[cell_key]
        self._hot_until[cell_key] = now + self.cooldown_seconds
        while len(self._hot_until) > self.max_cells:
            self._hot_until.popitem(last=False)
        return True

    def is_hot(self, cell_key: str) -> bool:
        deadline = self._hot_until.get(cell_key)
        return deadline is not None and deadline > time.monotonic()


class FeatureAggregationWorker:
    """Computes rolling spatio-temporal features and emits enriched records and catalyst alerts."""

    # Feature-relevant raw topics only (ADR 0008 §1): crime stays excluded
    # until it clears ablation (US-71); street-cut/evictions are context-only.
    # topic → feed label mapping for metrics/logs.
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        feature_pipeline: Optional[SpatialFeaturePipeline] = None,
        city_id: str = "nyc",
        cooldown_seconds: Optional[int] = None,
    ):
        self.feature_pipeline = feature_pipeline or SpatialFeaturePipeline()
        self.city_id = city_id
        self.indexer = H3SpatialIndexer()

        self.topics = [
            settings.topic_permits,
            settings.topic_311,
            settings.topic_sla,
            settings.topic_deeds,
        ]
        self.FEED_BY_TOPIC = {
            settings.topic_permits: "permits",
            settings.topic_311: "311",
            settings.topic_sla: "sla",
            settings.topic_deeds: "deeds",
        }

        self.consumer = BaseKafkaConsumer(
            group_id=settings.cg_inference,
            topics=self.topics,
            bootstrap_servers=bootstrap_servers,
        )

        self.cooldown = CellCooldownStore(
            cooldown_seconds if cooldown_seconds is not None else settings.aggregation_cell_cooldown_seconds
        )

        # Producer for enriched features & alerts
        enriched_schema = Path(__file__).parent.parent / "schemas" / "avro" / "enriched_h3_feature.avsc"
        self.enriched_producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=enriched_schema,
        )

        alert_schema = Path(__file__).parent.parent / "schemas" / "avro" / "catalyst_alert.avsc"
        self.alert_producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=alert_schema,
        )

    def process_and_emit_cell(
        self,
        h3_index: str,
        resolution: int = 9,
        as_of_date: Optional[datetime] = None,
        city_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compute enriched feature dict for H3 cell and publish to Kafka."""
        if as_of_date is None:
            as_of_date = datetime.now(timezone.utc)
        effective_city_id = city_id or self.city_id

        feat_dict = self.feature_pipeline.compute_h3_cell_features(
            h3_index=h3_index,
            resolution=resolution,
            as_of_date=as_of_date,
        )

        # Emit enriched feature event. Keyed city_id:h3_index (US-72, scaling
        # notes): all records for one cell share a partition so per-cell
        # ordering survives as the topic count and partition count grow.
        enriched_feature = EnrichedH3Feature(
            city_id=effective_city_id,
            h3_index=h3_index,
            h3_resolution=resolution,
            timestamp=as_of_date,
            capex_density_decayed=feat_dict["capex_density_decayed"],
            permit_count_60d=feat_dict["permit_count_60d"],
            permit_count_180d=feat_dict["permit_count_180d"],
            permit_velocity=feat_dict["permit_velocity"],
            complaints_neglect_count=feat_dict["complaints_neglect_count"],
            complaints_qol_count=feat_dict["complaints_qol_count"],
            shift_ratio_311=feat_dict["shift_ratio_311"],
            sla_active_licenses=feat_dict["sla_active_licenses"],
            sla_new_filings_90d=feat_dict["sla_new_filings_90d"],
            sla_move_ins_90d=feat_dict.get("sla_move_ins_90d", 0),
            sla_move_outs_90d=feat_dict.get("sla_move_outs_90d", 0),
            deed_total_volume_180d=feat_dict["deed_total_volume_180d"],
            deed_transaction_count_180d=feat_dict["deed_transaction_count_180d"],
            lims_score=feat_dict["lims_score"],
            created_at=datetime.now(timezone.utc),
        )

        self.enriched_producer.produce(
            topic=settings.topic_enriched_h3,
            key=f"{effective_city_id}:{h3_index}",
            payload=enriched_feature,
        )

        # Check for Catalyst Alert condition (LIMS > threshold)
        if feat_dict["lims_score"] >= settings.lims_threshold:
            lat, lng = self.indexer.h3_to_latlng(h3_index)
            alert = CatalystAlert(
                city_id=effective_city_id,
                alert_id=f"alert-{uuid.uuid4().hex[:8]}",
                h3_index=h3_index,
                h3_resolution=resolution,
                lims_score=feat_dict["lims_score"],
                predicted_delta_6m=round(feat_dict["lims_score"] * 0.002, 4),
                predicted_delta_12m=round(feat_dict["lims_score"] * 0.0035, 4),
                macro_outperformance_prob_18m=round(min(feat_dict["lims_score"] / 100.0 * 1.1, 0.99), 4),
                centroid_lat=lat,
                centroid_lng=lng,
                timestamp=datetime.now(timezone.utc),
            )
            self.alert_producer.produce(
                topic=settings.topic_catalyst_alerts,
                key=h3_index,
                payload=alert,
            )
            logger.info("Emitted Catalyst Alert for %s (LIMS=%.2f)", h3_index, feat_dict["lims_score"])

        return feat_dict

    def process_record(self, record: Dict[str, Any], topic: str, key: str):
        """Aggregation trigger path for one raw record (ADR 0008 §1).

        Never raises: any failure routes the raw record straight to the
        shared DLQ so a bad row cannot stall the consume loop.
        """
        try:
            if record.get("source_mode") == "backfill":
                BACKFILL_SKIPPED.inc()
                logger.debug("Skipping backfill record key=%s topic=%s", key, topic)
                return

            h3_cell = record.get("h3_res9")
            if not h3_cell:
                logger.debug("Skipping record without h3_res9 key=%s topic=%s", key, topic)
                return

            feed = self.FEED_BY_TOPIC.get(topic, topic)
            cell_key = f"{self.city_id}:{h3_cell}"

            self._insert_record(topic, record)

            if not self.cooldown.try_acquire(cell_key):
                ABSORBED_RECORDS.labels(city_id=self.city_id, feed=feed).inc()
                logger.debug("Cell %s hot; absorbed record key=%s feed=%s", h3_cell, key, feed)
                return

            self.process_and_emit_cell(h3_index=h3_cell, resolution=9, city_id=self.city_id)
        except Exception as e:
            logger.exception("Aggregation failed for key %s from topic %s: %s", key, topic, e)
            self.enriched_producer.route_to_dlq(
                failed_topic=topic,
                key=key,
                payload=record,
                error_msg=str(e),
            )

    def _insert_record(self, topic: str, record: Dict[str, Any]):
        """Insert the raw record into the pipeline's raw table for its feed."""
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
                "expiration_date": pd.to_datetime(record.get("expiration_date")) if record.get("expiration_date") else None,
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
        """Start the feature aggregation consumer loop."""
        logger.info(
            "Starting Feature Aggregation Worker (group=%s, topics=%s, cooldown=%ss)...",
            settings.cg_inference,
            self.topics,
            self.cooldown.cooldown_seconds,
        )
        self.consumer.start_consume_loop(
            record_handler=self.process_record,
            batch_size=100,
        )

    def close(self):
        """Release Kafka, producer, and analytical resources owned by this worker."""
        self.consumer.close()
        self.enriched_producer.flush()
        self.alert_producer.flush()
        close = getattr(self.feature_pipeline, "close", None)
        if close:
            close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = FeatureAggregationWorker()
    worker.start()
