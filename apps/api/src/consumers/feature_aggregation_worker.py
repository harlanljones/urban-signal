"""Feature aggregation consumer worker emitting enriched H3 records and catalyst alerts."""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.config import settings
from src.consumers.base_consumer import BaseKafkaConsumer
from src.features.pipeline import SpatialFeaturePipeline
from src.producers.base_producer import BaseKafkaProducer
from src.schemas.models import CatalystAlert, EnrichedH3Feature
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)


class FeatureAggregationWorker:
    """Computes rolling spatio-temporal features and emits enriched records and catalyst alerts."""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        feature_pipeline: Optional[SpatialFeaturePipeline] = None,
        city_id: str = "nyc",
    ):
        self.feature_pipeline = feature_pipeline or SpatialFeaturePipeline()
        self.city_id = city_id
        self.indexer = H3SpatialIndexer()

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
