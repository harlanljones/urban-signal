"""Offline tests for the FeatureAggregationWorker consume loop (US-108, ADR 0008)."""

import io
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import fastavro
import h3
import pytest

from src.config import settings
from src.consumers.feature_aggregation_worker import CellCooldownStore, FeatureAggregationWorker
from src.features.pipeline import SpatialFeaturePipeline
from src.schemas.models import CatalystAlert

CELL = h3.latlng_to_cell(40.7233, -74.0030, 9)
CELL_B = h3.latlng_to_cell(40.7145, -73.9555, 9)


def _feat_dict(lims_score: float = 10.0) -> dict:
    return {
        "capex_density_decayed": 1000.0,
        "permit_count_60d": 1,
        "permit_count_180d": 2,
        "permit_velocity": 0.5,
        "complaints_neglect_count": 0,
        "complaints_qol_count": 1,
        "shift_ratio_311": 2.0,
        "sla_active_licenses": 3,
        "sla_new_filings_90d": 1,
        "sla_move_ins_90d": 0,
        "sla_move_outs_90d": 0,
        "deed_total_volume_180d": 500000.0,
        "deed_transaction_count_180d": 1,
        "lims_score": lims_score,
    }


def _permit_record(cell: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "job_id": f"J-{uuid.uuid4().hex[:6]}",
        "job_type": "New Building",
        "latitude": 40.7233,
        "longitude": -74.0030,
        "estimated_cost": 250000.0,
        "issuance_date": now.isoformat(),
        "h3_res7": h3.cell_to_parent(cell, 7),
        "h3_res8": h3.cell_to_parent(cell, 8),
        "h3_res9": cell,
        "ingested_at": now.isoformat(),
    }


@pytest.fixture
def worker():
    with (
        patch("src.consumers.feature_aggregation_worker.BaseKafkaConsumer"),
        patch("src.consumers.feature_aggregation_worker.BaseKafkaProducer"),
    ):
        pipeline = MagicMock()
        pipeline.compute_h3_cell_features.return_value = _feat_dict()
        w = FeatureAggregationWorker(feature_pipeline=pipeline)
    w.enriched_producer = MagicMock()
    w.alert_producer = MagicMock()
    return w


class TestConsumeLoop:
    def test_live_record_inserts_then_computes_and_emits_enriched(self, worker):
        worker.process_record(_permit_record(CELL), settings.topic_permits, "k1")

        worker.feature_pipeline.insert_permits.assert_called_once()
        worker.feature_pipeline.compute_h3_cell_features.assert_called_once()
        call = worker.feature_pipeline.compute_h3_cell_features.call_args
        assert call.kwargs["h3_index"] == CELL
        assert call.kwargs["resolution"] == 9
        assert worker.enriched_producer.produce.call_count == 1
        assert worker.alert_producer.produce.call_count == 0

    def test_second_record_in_window_is_absorbed(self, worker):
        worker.process_record(_permit_record(CELL), settings.topic_permits, "k1")
        worker.process_record(_permit_record(CELL), settings.topic_permits, "k2")

        # Insert happens before the gate (pipeline needs the row); compute
        # and enriched emit happen only once per cooldown window.
        assert worker.feature_pipeline.insert_permits.call_count == 2
        assert worker.feature_pipeline.compute_h3_cell_features.call_count == 1
        assert worker.enriched_producer.produce.call_count == 1

    def test_backfill_marked_record_skipped_entirely(self, worker):
        record = _permit_record(CELL)
        record["source_mode"] = "backfill"
        worker.process_record(record, settings.topic_permits, "k1")

        worker.feature_pipeline.insert_permits.assert_not_called()
        worker.feature_pipeline.compute_h3_cell_features.assert_not_called()
        worker.enriched_producer.produce.assert_not_called()

    def test_record_without_h3_skipped(self, worker):
        record = _permit_record(CELL)
        record.pop("h3_res9")
        worker.process_record(record, settings.topic_permits, "k1")

        worker.feature_pipeline.insert_permits.assert_not_called()
        worker.feature_pipeline.compute_h3_cell_features.assert_not_called()
        worker.enriched_producer.produce.assert_not_called()

    def test_compute_failure_routes_raw_record_to_dlq(self, worker):
        worker.feature_pipeline.compute_h3_cell_features.side_effect = RuntimeError("duckdb exploded")
        worker.process_record(_permit_record(CELL), settings.topic_permits, "k1")

        worker.enriched_producer.route_to_dlq.assert_called_once()
        kwargs = worker.enriched_producer.route_to_dlq.call_args.kwargs
        assert kwargs["failed_topic"] == settings.topic_permits
        assert kwargs["key"] == "k1"

    def test_failing_cell_cooldowns_before_compute_poison_protection(self, worker):
        worker.feature_pipeline.compute_h3_cell_features.side_effect = RuntimeError("boom")
        worker.process_record(_permit_record(CELL), settings.topic_permits, "k1")
        worker.process_record(_permit_record(CELL), settings.topic_permits, "k2")

        # Cooldown was set before the first (failing) compute: at most one
        # DLQ record per cell per window; the second record is absorbed.
        assert worker.enriched_producer.route_to_dlq.call_count == 1
        assert worker.feature_pipeline.compute_h3_cell_features.call_count == 1

    def test_failure_does_not_kill_loop_next_cell_computes(self, worker):
        worker.feature_pipeline.compute_h3_cell_features.side_effect = [
            RuntimeError("boom"),
            _feat_dict(),
        ]
        worker.process_record(_permit_record(CELL), settings.topic_permits, "k1")
        worker.process_record(_permit_record(CELL_B), settings.topic_permits, "k2")

        assert worker.feature_pipeline.compute_h3_cell_features.call_count == 2
        assert worker.enriched_producer.produce.call_count == 1

    def test_catalyst_alert_emitted_above_threshold(self, worker):
        worker.feature_pipeline.compute_h3_cell_features.return_value = _feat_dict(lims_score=99.0)
        worker.process_record(_permit_record(CELL), settings.topic_permits, "k1")

        assert worker.alert_producer.produce.call_count == 1
        kwargs = worker.alert_producer.produce.call_args.kwargs
        assert kwargs["topic"] == settings.topic_catalyst_alerts
        alert_payload = kwargs["payload"]
        assert isinstance(alert_payload, CatalystAlert)
        assert alert_payload.city_id == "nyc"

    def test_realert_suppressed_within_window(self, worker):
        worker.feature_pipeline.compute_h3_cell_features.return_value = _feat_dict(lims_score=99.0)
        worker.process_record(_permit_record(CELL), settings.topic_permits, "k1")
        worker.process_record(_permit_record(CELL), settings.topic_permits, "k2")

        # Alert suppression rides the same cooldown window as recompute.
        assert worker.alert_producer.produce.call_count == 1


class TestInsertMapping:
    """The loop must land rows in each raw table before its window queries run."""

    @pytest.fixture
    def real_worker(self):
        with (
            patch("src.consumers.feature_aggregation_worker.BaseKafkaConsumer"),
            patch("src.consumers.feature_aggregation_worker.BaseKafkaProducer"),
            patch.object(SpatialFeaturePipeline, "compute_h3_cell_features", return_value=_feat_dict()),
        ):
            w = FeatureAggregationWorker(feature_pipeline=SpatialFeaturePipeline())
        w.enriched_producer = MagicMock()
        w.alert_producer = MagicMock()
        yield w
        w.close()

    def _count(self, worker, table: str) -> int:
        return worker.feature_pipeline.con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def test_permit_row_lands_in_duckdb(self, real_worker):
        real_worker.process_record(_permit_record(CELL), settings.topic_permits, "k1")
        assert self._count(real_worker, "raw_permits") == 1

    def test_deed_row_without_coordinates_lands_in_duckdb(self, real_worker):
        record = {
            "doc_id": "D-1",
            "doc_type": "DEED",
            "document_amount": 1200000.0,
            "recorded_date": datetime.now(timezone.utc).isoformat(),
            "h3_res7": h3.cell_to_parent(CELL, 7),
            "h3_res8": h3.cell_to_parent(CELL, 8),
            "h3_res9": CELL,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        real_worker.process_record(record, settings.topic_deeds, "k1")
        assert self._count(real_worker, "raw_deeds") == 1

    def test_unknown_topic_record_still_gated_but_not_inserted(self, real_worker):
        record = _permit_record(CELL)
        real_worker.process_record(record, "raw.municipal.unknown", "k1")
        assert self._count(real_worker, "raw_permits") == 0


class TestCellCooldownStore:
    def test_acquire_then_block_then_expire(self):
        store = CellCooldownStore(cooldown_seconds=60)
        assert store.try_acquire("a") is True
        assert store.is_hot("a") is True
        assert store.try_acquire("a") is False

        store2 = CellCooldownStore(cooldown_seconds=0)
        assert store2.try_acquire("a") is True
        assert store2.is_hot("a") is False
        assert store2.try_acquire("a") is True

    def test_bounded_with_eviction(self):
        store = CellCooldownStore(cooldown_seconds=60, max_cells=3)
        for i in range(5):
            assert store.try_acquire(f"cell-{i}") is True
        assert len(store._hot_until) == 3
        # Oldest entries were evicted; newest survive.
        assert store.is_hot("cell-4") is True
        assert store.is_hot("cell-0") is False


class TestCatalystAlertAvscContract:
    """US-117: avsc gains city_id — without it fastavro rejected every alert to the DLQ."""

    AVSC = Path(__file__).parents[2] / "src" / "schemas" / "avro" / "catalyst_alert.avsc"

    def test_model_round_trips_through_avro_schema(self):
        schema = fastavro.parse_schema(json.loads(self.AVSC.read_text()))
        alert = CatalystAlert(
            city_id="chicago",
            alert_id="alert-test",
            h3_index=CELL,
            lims_score=90.0,
            predicted_delta_6m=0.18,
            predicted_delta_12m=0.31,
            macro_outperformance_prob_18m=0.95,
            centroid_lat=40.7233,
            centroid_lng=-74.003,
            timestamp=datetime.now(timezone.utc),
        )
        buf = io.BytesIO()
        fastavro.schemaless_writer(buf, schema, alert.model_dump(mode="json"))

        record = fastavro.schemaless_reader(io.BytesIO(buf.getvalue()), schema)
        assert record["city_id"] == "chicago"
        assert record["alert_id"] == "alert-test"

    def test_old_payload_without_city_id_deserializes_with_default(self):
        schema = fastavro.parse_schema(json.loads(self.AVSC.read_text()))
        legacy = {
            "alert_id": "legacy-1",
            "h3_index": CELL,
            "lims_score": 88.0,
            "predicted_delta_6m": 0.17,
            "predicted_delta_12m": 0.30,
            "macro_outperformance_prob_18m": 0.94,
            "centroid_lat": 40.7,
            "centroid_lng": -74.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        buf = io.BytesIO()
        fastavro.schemaless_writer(buf, schema, legacy)

        record = fastavro.schemaless_reader(io.BytesIO(buf.getvalue()), schema)
        assert record["city_id"] == "nyc"
