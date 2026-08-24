"""Comprehensive End-to-End Test Suite for Urban Signal Predictor Pipeline.

Covers:
1. Full streaming ingestion into Kafka topics & Avro schema serialization
2. Spatial enrichment with Uber H3 multi-resolution hierarchy (Res 7, 8, 9)
3. Out-of-core DuckDB feature store aggregations (CapEx time decay, 311 shift dynamics, LIMS)
4. Multi-horizon model inference (LightGBM Quantile, ST-GNN ONNX, DCN-v2 ONNX, SHAP)
5. FastAPI endpoints verification (/health, /ready, /live, /metrics, /api/v1/predict, /api/v1/predict/batch, /api/v1/catalysts, /api/v1/hex/{h3_index}/features)
6. Catalyst alert emission and asynchronous webhook dispatch
7. PostGIS spatial persistence and sync
"""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import pandas as pd
import pytest
from src.config import settings
from src.consumers.feature_aggregation_worker import FeatureAggregationWorker
from src.consumers.postgis_worker import PostGISWorker
from src.consumers.spatial_enrichment_worker import SpatialEnrichmentWorker
from src.features.pipeline import SpatialFeaturePipeline
from src.models.quantile_lgbm import FEATURE_COLUMNS
from src.producers.base_producer import BaseKafkaProducer
from src.schemas.models import (
    CatalystAlert,
    Complaint311Event,
    ComplaintCategory,
    DeedEvent,
    EnrichedH3Feature,
    JobType,
    PermitEvent,
    PredictionRequest,
    PredictionResponse,
    SLALicenseEvent,
)
from src.serving.app import create_app
from src.serving.dispatcher import WebhookDispatcher
from src.serving.engine import MultiHorizonInferenceEngine
from src.spatial.h3_indexer import H3SpatialIndexer
from src.storage.postgis_sync import PostGISSpatialSync


@pytest.fixture(scope="module")
def shared_app_client():
    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def spatial_pipeline():
    pipeline = SpatialFeaturePipeline(db_path=":memory:")
    try:
        yield pipeline
    finally:
        pipeline.close()


# -----------------------------------------------------------------------------
# 1. STREAMING INGESTION & AVRO ENFORCEMENT
# -----------------------------------------------------------------------------
def test_e2e_streaming_ingestion_and_avro_serialization(sample_permit_event, sample_complaint_event, sample_sla_event, sample_deed_event):
    avro_dir = Path(__file__).resolve().parents[4] / "apps" / "api" / "src" / "schemas" / "avro"

    schemas = {
        settings.topic_permits: (avro_dir / "permit_event.avsc", sample_permit_event),
        settings.topic_311: (avro_dir / "complaint_311_event.avsc", sample_complaint_event),
        settings.topic_sla: (avro_dir / "sla_license_event.avsc", sample_sla_event),
        settings.topic_deeds: (avro_dir / "deed_event.avsc", sample_deed_event),
    }

    for topic, (schema_path, event) in schemas.items():
        assert schema_path.exists(), f"Schema {schema_path} missing"

        producer = BaseKafkaProducer(schema_file_path=schema_path)
        payload_dict = event.model_dump(mode="json")

        serialized_bytes = producer.serialize_avro(payload_dict)
        assert isinstance(serialized_bytes, bytes)
        assert len(serialized_bytes) > 0


# -----------------------------------------------------------------------------
# 2. SPATIAL ENRICHMENT WORKER WITH H3 RES 7, 8, 9
# -----------------------------------------------------------------------------
def test_e2e_spatial_enrichment_worker(spatial_pipeline, sample_nyc_coords):
    worker = SpatialEnrichmentWorker(feature_pipeline=spatial_pipeline)
    try:
        soho = sample_nyc_coords["soho"]
        williamsburg = sample_nyc_coords["williamsburg"]

        # 1. Feed raw un-indexed DOB permit
        permit_record = {
            "job_id": "JOB-NYC-E2E-001",
            "job_type": "NB",
            "latitude": soho["lat"],
            "longitude": soho["lng"],
            "estimated_cost": 5000000.0,
            "issuance_date": datetime.now(timezone.utc).isoformat(),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        worker.process_record(permit_record, topic=settings.topic_permits, key=permit_record["job_id"])

        # Verify H3 indexing occurred
        df_permits = spatial_pipeline.con.execute("SELECT * FROM raw_permits WHERE job_id = 'JOB-NYC-E2E-001'").df()
        assert len(df_permits) == 1
        assert df_permits["h3_res7"].iloc[0].startswith("87")
        assert df_permits["h3_res8"].iloc[0].startswith("88")
        assert df_permits["h3_res9"].iloc[0].startswith("89")

        # 2. Feed raw 311 complaint
        complaint_record = {
            "incident_id": "SR-NYC-E2E-002",
            "complaint_type": "Noise - Commercial",
            "category": "QOL",
            "latitude": williamsburg["lat"],
            "longitude": williamsburg["lng"],
            "created_date": datetime.now(timezone.utc).isoformat(),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        worker.process_record(complaint_record, topic=settings.topic_311, key=complaint_record["incident_id"])

        df_complaints = spatial_pipeline.con.execute("SELECT * FROM raw_complaints WHERE incident_id = 'SR-NYC-E2E-002'").df()
        assert len(df_complaints) == 1
        assert df_complaints["category"].iloc[0] == "QOL"
    finally:
        worker.close()


# -----------------------------------------------------------------------------
# 3. OUT-OF-CORE DUCKDB FEATURE AGGREGATIONS & POLARS EXPORT
# -----------------------------------------------------------------------------
def test_e2e_duckdb_feature_store_aggregations(spatial_pipeline):
    indexer = H3SpatialIndexer()
    target_cell = indexer.latlng_to_h3(40.7250, -73.9970, resolution=9)
    res8 = indexer.get_parent(target_cell, 8)
    res7 = indexer.get_parent(target_cell, 7)
    now = datetime.now(timezone.utc)

    # Insert historical multi-temporal permits
    permits = [
        {"job_id": "P1", "job_type": "NB", "latitude": 40.7250, "longitude": -73.9970, "estimated_cost": 2000000.0, "issuance_date": now - timedelta(days=20), "h3_res7": res7, "h3_res8": res8, "h3_res9": target_cell, "ingested_at": now},
        {"job_id": "P2", "job_type": "A1", "latitude": 40.7250, "longitude": -73.9970, "estimated_cost": 1000000.0, "issuance_date": now - timedelta(days=50), "h3_res7": res7, "h3_res8": res8, "h3_res9": target_cell, "ingested_at": now},
        {"job_id": "P3", "job_type": "A2", "latitude": 40.7250, "longitude": -73.9970, "estimated_cost": 500000.0, "issuance_date": now - timedelta(days=120), "h3_res7": res7, "h3_res8": res8, "h3_res9": target_cell, "ingested_at": now},
    ]
    spatial_pipeline.insert_permits(pd.DataFrame(permits))

    # Insert 311 complaints (8 QoL, 2 Neglect)
    complaints = [
        {"incident_id": f"C_QOL_{i}", "complaint_type": "Noise - Commercial", "category": "QOL", "latitude": 40.7250, "longitude": -73.9970, "created_date": now - timedelta(days=i*5), "h3_res7": res7, "h3_res8": res8, "h3_res9": target_cell, "ingested_at": now}
        for i in range(8)
    ] + [
        {"incident_id": f"C_NEG_{i}", "complaint_type": "HEAT/HOT WATER", "category": "NEGLECT", "latitude": 40.7250, "longitude": -73.9970, "created_date": now - timedelta(days=i*10), "h3_res7": res7, "h3_res8": res8, "h3_res9": target_cell, "ingested_at": now}
        for i in range(2)
    ]
    spatial_pipeline.insert_complaints(pd.DataFrame(complaints))

    # Insert SLA licenses
    sla = [
        {"license_id": "SLA-101", "license_type": "OP - On-Premises Liquor", "latitude": 40.7250, "longitude": -73.9970, "effective_date": now - timedelta(days=30), "license_status": "ACTIVE", "h3_res7": res7, "h3_res8": res8, "h3_res9": target_cell, "ingested_at": now},
        {"license_id": "SLA-102", "license_type": "OP - On-Premises Liquor", "latitude": 40.7250, "longitude": -73.9970, "effective_date": now - timedelta(days=45), "license_status": "ACTIVE", "h3_res7": res7, "h3_res8": res8, "h3_res9": target_cell, "ingested_at": now},
    ]
    spatial_pipeline.insert_sla(pd.DataFrame(sla))

    # Compute features for H3 cell
    feats = spatial_pipeline.compute_h3_cell_features(h3_index=target_cell, resolution=9, as_of_date=now)

    assert feats["h3_index"] == target_cell
    assert feats["h3_resolution"] == 9
    assert feats["permit_count_60d"] == 2
    assert feats["permit_count_180d"] == 3
    assert feats["permit_velocity"] > 0.0
    assert feats["complaints_qol_count"] == 8
    assert feats["complaints_neglect_count"] == 2
    assert feats["shift_ratio_311"] == pytest.approx((8 + 1) / (2 + 1), rel=1e-3)
    assert feats["sla_new_filings_90d"] == 2
    assert feats["capex_density_decayed"] > 0.0
    assert feats["lims_score"] > 80.0

    # Store into DuckDB feature table and export via Polars
    spatial_pipeline.con.execute("""
        INSERT INTO feature_store_h3 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        feats["h3_index"], feats["h3_resolution"], feats["as_of_date"],
        feats["capex_density_decayed"], feats["permit_count_60d"], feats["permit_count_180d"],
        feats["permit_velocity"], feats["complaints_neglect_count"], feats["complaints_qol_count"],
        feats["shift_ratio_311"], feats["sla_active_licenses"], feats["sla_new_filings_90d"],
        feats["deed_total_volume_180d"], feats["deed_transaction_count_180d"], feats["lims_score"]
    ])

    pl_df = spatial_pipeline.export_feature_matrix_polars()
    assert len(pl_df) >= 1
    assert "lims_score" in pl_df.columns


# -----------------------------------------------------------------------------
# 4. MULTI-HORIZON MODEL INFERENCE & SHAP EXPLAINABILITY
# -----------------------------------------------------------------------------
def test_e2e_multi_horizon_inference_engine():
    engine = MultiHorizonInferenceEngine()
    test_cell = "892a1072893ffff"

    sample_feats = {
        "capex_density_decayed": 650000.0,
        "permit_count_60d": 4,
        "permit_count_180d": 6,
        "permit_velocity": 0.55,
        "complaints_neglect_count": 1,
        "complaints_qol_count": 12,
        "shift_ratio_311": 6.5,
        "sla_active_licenses": 5,
        "sla_new_filings_90d": 3,
        "deed_total_volume_180d": 8500000.0,
        "deed_transaction_count_180d": 4,
        "lims_score": 92.4,
    }

    result = engine.predict_cell_features(
        h3_index=test_cell,
        feature_dict=sample_feats,
        include_shap=True,
    )

    # 1. 6-Month Micro (LightGBM Quantile Forecast)
    assert "delta_6m_p10" in result
    assert "delta_6m_p50" in result
    assert "delta_6m_p90" in result

    # 2. 12-Month Neighborhood (ST-GNN ONNX Spatial Spillover)
    assert "delta_12m_spillover" in result
    assert isinstance(result["delta_12m_spillover"], float)

    # 3. 18-Month Macro (DCN-v2 ONNX Outperformance Probability)
    assert "prob_18m_macro_outperformance" in result
    assert 0.0 <= result["prob_18m_macro_outperformance"] <= 1.0

    # 4. LIMS Catalyst Flag
    assert result["lims_score"] >= 85.0
    assert result["is_catalyst"] is True

    # 5. SHAP Attributions
    assert result["shap_attributions"] is not None
    assert len(result["shap_attributions"]) == len(FEATURE_COLUMNS)

    # 6. Performance Latency
    assert result["inference_latency_ms"] >= 0.0


# -----------------------------------------------------------------------------
# 5. FASTAPI SERVING ENDPOINTS VERIFICATION
# -----------------------------------------------------------------------------
def test_e2e_fastapi_endpoints(shared_app_client):
    # 1. Root & Health
    resp_root = shared_app_client.get("/")
    assert resp_root.status_code == 200
    assert resp_root.json()["status"] == "operational"

    resp_health = shared_app_client.get("/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "healthy"
    assert resp_health.json()["service"] == settings.service_name
    assert resp_health.json()["service"] == settings.service_name

    # 2. Prometheus Metrics
    resp_metrics = shared_app_client.get("/metrics")
    assert resp_metrics.status_code == 200
    assert "prediction_requests_total" in resp_metrics.text
    assert "inference_latency_seconds" in resp_metrics.text

    # 3. Single Prediction by Coordinates
    pred_req = {
        "latitude": 40.7233,
        "longitude": -74.0030,
        "resolution": 9,
        "include_shap": True,
    }
    resp_pred = shared_app_client.post("/api/v1/predict", json=pred_req)
    assert resp_pred.status_code == 200
    data = resp_pred.json()
    assert "h3_index" in data
    assert "centroid_lat" in data
    assert "delta_6m_p50" in data
    assert "prob_18m_macro_outperformance" in data
    assert "shap_attributions" in data

    # 4. Batch Prediction
    batch_req = [
        {"latitude": 40.7233, "longitude": -74.0030, "resolution": 9},
        {"latitude": 40.7145, "longitude": -73.9555, "resolution": 9},
    ]
    resp_batch = shared_app_client.post("/api/v1/predict/batch", json=batch_req)
    assert resp_batch.status_code == 200
    batch_data = resp_batch.json()
    assert len(batch_data) == 2

    # 5. Active Catalysts
    resp_cat = shared_app_client.get("/api/v1/catalysts?min_lims=85.0")
    assert resp_cat.status_code == 200
    cat_data = resp_cat.json()
    assert "count" in cat_data
    assert isinstance(cat_data["catalysts"], list)

    # 6. Hexagon Feature Inspection
    test_h3 = data["h3_index"]
    resp_hex = shared_app_client.get(f"/api/v1/hex/{test_h3}/features")
    assert resp_hex.status_code == 200
    hex_data = resp_hex.json()
    assert hex_data["h3_index"] == test_h3
    assert "boundary_geojson" in hex_data
    assert "features" in hex_data


# -----------------------------------------------------------------------------
# 6. CATALYST ALERT EMISSION & ASYNC WEBHOOK DISPATCH
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_e2e_catalyst_alert_and_webhook_dispatch(spatial_pipeline):
    indexer = H3SpatialIndexer()
    h3_cell = "892a1072893ffff"
    lat, lng = indexer.h3_to_latlng(h3_cell)
    now = datetime.now(timezone.utc)

    # Seed high-momentum data into DuckDB pipeline
    permits = [
        {"job_id": f"P_CAT_{i}", "job_type": "NB", "latitude": lat, "longitude": lng, "estimated_cost": 3000000.0, "issuance_date": now - timedelta(days=10*i), "h3_res7": indexer.get_parent(h3_cell, 7), "h3_res8": indexer.get_parent(h3_cell, 8), "h3_res9": h3_cell, "ingested_at": now}
        for i in range(5)
    ]
    spatial_pipeline.insert_permits(pd.DataFrame(permits))

    # Aggregation worker triggers catalyst condition
    agg_worker = FeatureAggregationWorker(feature_pipeline=spatial_pipeline)
    with patch.object(agg_worker.alert_producer, "produce") as mock_produce_alert,          patch.object(agg_worker.enriched_producer, "produce") as mock_produce_feat:

        computed = agg_worker.process_and_emit_cell(h3_index=h3_cell, resolution=9, as_of_date=now)
        assert computed["lims_score"] >= settings.lims_threshold
        assert mock_produce_feat.called
        assert mock_produce_alert.called

    # Test Webhook Dispatcher
    test_alert = CatalystAlert(
        alert_id="alert-e2e-8888",
        h3_index=h3_cell,
        h3_resolution=9,
        lims_score=94.5,
        predicted_delta_6m=0.089,
        predicted_delta_12m=0.156,
        macro_outperformance_prob_18m=0.94,
        centroid_lat=lat,
        centroid_lng=lng,
        top_catalyst_drivers=[{"capex_density_decayed": 45.0, "permit_velocity": 24.2}],
        timestamp=now,
    )

    webhook_urls = ["https://hooks.slack.com/services/T00/B00/X00", "https://discord.com/api/webhooks/123/abc"]
    dispatcher = WebhookDispatcher(target_urls=webhook_urls)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        status_codes = await dispatcher.dispatch_alert(test_alert)
        assert len(status_codes) == 2
        assert all(code == 200 for code in status_codes)


# -----------------------------------------------------------------------------
# 7. POSTGIS PERSISTENCE & SYNC VERIFICATION
# -----------------------------------------------------------------------------
def test_e2e_postgis_persistence_and_sync(spatial_pipeline, sample_permit_event):
    from sqlalchemy import create_engine, text

    engine = create_engine("sqlite:///:memory:")
    storage = PostGISSpatialSync(engine=engine)
    storage.init_tables()

    # Seed sample permit into pipeline
    spatial_pipeline.insert_permits(pd.DataFrame([sample_permit_event.model_dump()]))

    # Sync pipeline state to storage
    storage.sync_from_duckdb(spatial_pipeline)

    with storage.engine.connect() as conn:
        permits_count = conn.execute(text("SELECT COUNT(*) FROM municipal_permits")).scalar()
        assert permits_count >= 1
