"""Unit tests for PostgreSQL / PostGIS Spatial Persistence & Sync Worker."""

import json
from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from src.config import settings
from src.consumers.postgis_worker import PostGISWorker
from src.features.pipeline import SpatialFeaturePipeline
from src.schemas.models import (
    CatalystAlert,
    Complaint311Event,
    ComplaintCategory,
    DeedEvent,
    JobType,
    PermitEvent,
    SLALicenseEvent,
)
from src.storage.postgis_sync import PostGISSpatialSync


@pytest.fixture
def in_memory_storage():
    engine = create_engine("sqlite:///:memory:")
    sync = PostGISSpatialSync(engine=engine)
    sync.init_tables()
    return sync


def test_postgis_ddl_and_indices():
    statements = PostGISSpatialSync.get_postgis_ddl_statements()
    full_ddl = " ".join(statements)

    # 1. PostGIS Extension
    assert "CREATE EXTENSION IF NOT EXISTS postgis;" in statements

    # 2. Table definitions
    assert "municipal_permits" in full_ddl
    assert "municipal_311_complaints" in full_ddl
    assert "municipal_sla_licenses" in full_ddl
    assert "municipal_deeds" in full_ddl
    assert "feature_store_h3_spatial" in full_ddl
    assert "catalyst_alerts" in full_ddl

    # 3. Spatial GiST Indices
    assert "USING GIST (geom)" in full_ddl
    assert "USING GIST (centroid)" in full_ddl
    assert "idx_permits_geom" in full_ddl
    assert "idx_complaints_geom" in full_ddl
    assert "idx_sla_geom" in full_ddl
    assert "idx_deeds_geom" in full_ddl
    assert "idx_feature_h3_geom" in full_ddl
    assert "idx_catalyst_alerts_centroid" in full_ddl

    # 4. Temporal BRIN Indices
    assert "USING BRIN (issuance_date)" in full_ddl
    assert "USING BRIN (created_date)" in full_ddl
    assert "USING BRIN (effective_date)" in full_ddl
    assert "USING BRIN (recorded_date)" in full_ddl
    assert "USING BRIN (as_of_date)" in full_ddl
    assert "USING BRIN (timestamp)" in full_ddl

    # 5. Multi-City city_id Indices
    assert "idx_permits_city_id" in full_ddl
    assert "idx_complaints_city_id" in full_ddl
    assert "idx_sla_city_id" in full_ddl
    assert "idx_deeds_city_id" in full_ddl
    assert "idx_feature_city_id" in full_ddl
    assert "idx_alerts_city_id" in full_ddl


def test_sync_permits(in_memory_storage, sample_permit_event):
    df = pd.DataFrame([sample_permit_event.model_dump()])
    in_memory_storage.sync_permits(df)

    with in_memory_storage.engine.connect() as conn:
        res = conn.execute(text("SELECT job_id, city_id, estimated_cost, geom_wkt, h3_res9 FROM municipal_permits")).fetchall()
        assert len(res) == 1
        assert res[0][0] == sample_permit_event.job_id
        assert res[0][1] == "nyc"
        assert res[0][2] == sample_permit_event.estimated_cost
        assert "POINT" in res[0][3]
        assert res[0][4] == sample_permit_event.h3_res9


def test_sync_complaints(in_memory_storage, sample_complaint_event):
    df = pd.DataFrame([sample_complaint_event.model_dump()])
    in_memory_storage.sync_complaints(df)

    with in_memory_storage.engine.connect() as conn:
        res = conn.execute(text("SELECT incident_id, city_id, category, geom_wkt FROM municipal_311_complaints")).fetchall()
        assert len(res) == 1
        assert res[0][0] == sample_complaint_event.incident_id
        assert res[0][1] == "nyc"
        assert res[0][2] == sample_complaint_event.category.value
        assert "POINT" in res[0][3]


def test_sync_sla(in_memory_storage, sample_sla_event):
    df = pd.DataFrame([sample_sla_event.model_dump()])
    in_memory_storage.sync_sla(df)

    with in_memory_storage.engine.connect() as conn:
        res = conn.execute(text("SELECT license_id, city_id, license_status, geom_wkt FROM municipal_sla_licenses")).fetchall()
        assert len(res) == 1
        assert res[0][0] == sample_sla_event.license_id
        assert res[0][1] == "nyc"
        assert res[0][2] == "ACTIVE"
        assert "POINT" in res[0][3]


def test_sync_deeds(in_memory_storage, sample_deed_event):
    df = pd.DataFrame([sample_deed_event.model_dump()])
    in_memory_storage.sync_deeds(df)

    with in_memory_storage.engine.connect() as conn:
        res = conn.execute(text("SELECT doc_id, city_id, document_amount, geom_wkt FROM municipal_deeds")).fetchall()
        assert len(res) == 1
        assert res[0][0] == sample_deed_event.doc_id
        assert res[0][1] == "nyc"
        assert res[0][2] == sample_deed_event.document_amount
        assert "POINT" in res[0][3]


def test_sync_features(in_memory_storage):
    now = datetime.now(timezone.utc)
    features_df = pd.DataFrame([{
        "h3_index": "892a1072893ffff",
        "city_id": "nyc",
        "h3_resolution": 9,
        "as_of_date": now,
        "capex_density_decayed": 125000.0,
        "permit_count_60d": 3,
        "permit_count_180d": 8,
        "permit_velocity": 0.35,
        "complaints_neglect_count": 2,
        "complaints_qol_count": 10,
        "shift_ratio_311": 3.6667,
        "sla_active_licenses": 4,
        "sla_new_filings_90d": 2,
        "deed_total_volume_180d": 4500000.0,
        "deed_transaction_count_180d": 2,
        "lims_score": 88.5,
    }])

    in_memory_storage.sync_features(features_df)

    with in_memory_storage.engine.connect() as conn:
        res = conn.execute(text("SELECT h3_index, city_id, lims_score, centroid_wkt, geom_wkt FROM feature_store_h3_spatial")).fetchall()
        assert len(res) == 1
        assert res[0][0] == "892a1072893ffff"
        assert res[0][1] == "nyc"
        assert res[0][2] == 88.5
        assert "POINT" in res[0][3]
        assert "POLYGON" in res[0][4]


def test_sync_catalyst_alerts(in_memory_storage):
    alert = {
        "alert_id": "alert-test-001",
        "city_id": "nyc",
        "h3_index": "892a1072893ffff",
        "h3_resolution": 9,
        "lims_score": 91.2,
        "predicted_delta_6m": 0.082,
        "predicted_delta_12m": 0.145,
        "macro_outperformance_prob_18m": 0.92,
        "top_catalyst_drivers": [{"feature": "capex_density_decayed", "attribution": 42.1}],
        "centroid_lat": 40.7250,
        "centroid_lng": -73.9970,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    in_memory_storage.sync_catalyst_alerts([alert])

    with in_memory_storage.engine.connect() as conn:
        res = conn.execute(text("SELECT alert_id, city_id, lims_score, centroid_wkt FROM catalyst_alerts")).fetchall()
        assert len(res) == 1
        assert res[0][0] == "alert-test-001"
        assert res[0][1] == "nyc"
        assert res[0][2] == 91.2
        assert "POINT" in res[0][3]


def test_multi_city_permits_batch_and_query(in_memory_storage):
    nyc_permit = PermitEvent(
        city_id="nyc",
        job_id="NYC-JOB-001",
        job_type=JobType.NB,
        borough="MANHATTAN",
        latitude=40.7128,
        longitude=-74.0060,
        estimated_cost=2500000.0,
        issuance_date=datetime.now(timezone.utc),
        h3_res9="892a1072893ffff",
    )
    chicago_permit = PermitEvent(
        city_id="chicago",
        job_id="CHI-PERMIT-001",
        job_type=JobType.NB,
        borough="LOOP",
        latitude=41.8781,
        longitude=-87.6298,
        estimated_cost=3100000.0,
        issuance_date=datetime.now(timezone.utc),
        h3_res9="89275936477ffff",
    )

    in_memory_storage.insert_permits_batch([nyc_permit, chicago_permit])

    # Query all permits for NYC
    nyc_results = in_memory_storage.get_permits_by_city("nyc")
    assert len(nyc_results) == 1
    assert nyc_results[0]["job_id"] == "NYC-JOB-001"
    assert nyc_results[0]["city_id"] == "nyc"

    # Query all permits for Chicago
    chi_results = in_memory_storage.get_permits_by_city("chicago")
    assert len(chi_results) == 1
    assert chi_results[0]["job_id"] == "CHI-PERMIT-001"
    assert chi_results[0]["city_id"] == "chicago"

    # Query by H3 index with city filter
    nyc_h3 = in_memory_storage.query_permits_by_h3("892a1072893ffff", resolution=9, city_id="nyc")
    assert len(nyc_h3) == 1
    assert nyc_h3[0]["job_id"] == "NYC-JOB-001"

    chi_h3 = in_memory_storage.query_permits_by_h3("89275936477ffff", resolution=9, city_id="chicago")
    assert len(chi_h3) == 1
    assert chi_h3[0]["job_id"] == "CHI-PERMIT-001"


def test_multi_city_complaints_batch_and_query(in_memory_storage):
    nyc_complaint = Complaint311Event(
        city_id="nyc",
        incident_id="NYC-311-001",
        complaint_type="Noise - Residential",
        category=ComplaintCategory.QOL,
        latitude=40.7128,
        longitude=-74.0060,
        created_date=datetime.now(timezone.utc),
        h3_res9="892a1072893ffff",
    )
    chicago_complaint = Complaint311Event(
        city_id="chicago",
        incident_id="CHI-311-001",
        complaint_type="Building Violation",
        category=ComplaintCategory.NEGLECT,
        latitude=41.8781,
        longitude=-87.6298,
        created_date=datetime.now(timezone.utc),
        h3_res9="89275936477ffff",
    )

    in_memory_storage.insert_complaints_batch([nyc_complaint, chicago_complaint])

    nyc_res = in_memory_storage.get_complaints_by_city("nyc")
    assert len(nyc_res) == 1
    assert nyc_res[0]["incident_id"] == "NYC-311-001"
    assert nyc_res[0]["city_id"] == "nyc"

    chi_res = in_memory_storage.get_complaints_by_city("chicago")
    assert len(chi_res) == 1
    assert chi_res[0]["incident_id"] == "CHI-311-001"
    assert chi_res[0]["city_id"] == "chicago"

    nyc_by_h3 = in_memory_storage.query_complaints_by_h3("892a1072893ffff", city_id="nyc")
    assert len(nyc_by_h3) == 1
    assert nyc_by_h3[0]["incident_id"] == "NYC-311-001"

    chi_by_h3 = in_memory_storage.query_complaints_by_h3("89275936477ffff", city_id="chicago")
    assert len(chi_by_h3) == 1
    assert chi_by_h3[0]["incident_id"] == "CHI-311-001"


def test_multi_city_sla_batch_and_query(in_memory_storage):
    nyc_sla = SLALicenseEvent(
        city_id="nyc",
        license_id="NYC-SLA-001",
        license_type="On-Premises Liquor",
        premises_name="NYC Bar",
        latitude=40.7128,
        longitude=-74.0060,
        h3_res9="892a1072893ffff",
    )
    chicago_sla = SLALicenseEvent(
        city_id="chicago",
        license_id="CHI-LIQ-001",
        license_type="Tavern",
        premises_name="Chicago Tavern",
        latitude=41.8781,
        longitude=-87.6298,
        h3_res9="89275936477ffff",
    )

    in_memory_storage.insert_sla_batch([nyc_sla, chicago_sla])

    nyc_sla_res = in_memory_storage.get_sla_by_city("nyc")
    assert len(nyc_sla_res) == 1
    assert nyc_sla_res[0]["license_id"] == "NYC-SLA-001"
    assert nyc_sla_res[0]["city_id"] == "nyc"

    chi_sla_res = in_memory_storage.get_sla_by_city("chicago")
    assert len(chi_sla_res) == 1
    assert chi_sla_res[0]["license_id"] == "CHI-LIQ-001"
    assert chi_sla_res[0]["city_id"] == "chicago"

    nyc_sla_h3 = in_memory_storage.query_sla_by_h3("892a1072893ffff", city_id="nyc")
    assert len(nyc_sla_h3) == 1
    assert nyc_sla_h3[0]["license_id"] == "NYC-SLA-001"


def test_multi_city_deeds_batch_and_query(in_memory_storage):
    nyc_deed = DeedEvent(
        city_id="nyc",
        doc_id="NYC-DEED-001",
        doc_type="DEED",
        document_amount=5000000.0,
        recorded_date=datetime.now(timezone.utc),
        latitude=40.7128,
        longitude=-74.0060,
        h3_res9="892a1072893ffff",
    )
    chicago_deed = DeedEvent(
        city_id="chicago",
        doc_id="CHI-DEED-001",
        doc_type="DEED",
        document_amount=3200000.0,
        recorded_date=datetime.now(timezone.utc),
        latitude=41.8781,
        longitude=-87.6298,
        h3_res9="89275936477ffff",
    )

    in_memory_storage.insert_deeds_batch([nyc_deed, chicago_deed])

    nyc_deeds = in_memory_storage.get_deeds_by_city("nyc")
    assert len(nyc_deeds) == 1
    assert nyc_deeds[0]["doc_id"] == "NYC-DEED-001"
    assert nyc_deeds[0]["city_id"] == "nyc"

    chi_deeds = in_memory_storage.get_deeds_by_city("chicago")
    assert len(chi_deeds) == 1
    assert chi_deeds[0]["doc_id"] == "CHI-DEED-001"
    assert chi_deeds[0]["city_id"] == "chicago"

    nyc_deed_h3 = in_memory_storage.query_deeds_by_h3("892a1072893ffff", city_id="nyc")
    assert len(nyc_deed_h3) == 1
    assert nyc_deed_h3[0]["doc_id"] == "NYC-DEED-001"


def test_multi_city_features_and_alerts_query(in_memory_storage):
    now = datetime.now(timezone.utc)
    features = [
        {
            "h3_index": "892a1072893ffff",
            "city_id": "nyc",
            "h3_resolution": 9,
            "as_of_date": now,
            "lims_score": 85.0,
        },
        {
            "h3_index": "89275936477ffff",
            "city_id": "chicago",
            "h3_resolution": 9,
            "as_of_date": now,
            "lims_score": 79.5,
        },
    ]
    in_memory_storage.insert_h3_features(features)

    # Query features by H3 index and city
    nyc_feats = in_memory_storage.get_features_for_h3("892a1072893ffff", city_id="nyc")
    assert len(nyc_feats) == 1
    assert nyc_feats[0]["city_id"] == "nyc"
    assert nyc_feats[0]["lims_score"] == 85.0

    chi_feats = in_memory_storage.get_features_for_h3("89275936477ffff", city_id="chicago")
    assert len(chi_feats) == 1
    assert chi_feats[0]["city_id"] == "chicago"
    assert chi_feats[0]["lims_score"] == 79.5

    # Insert catalyst alerts
    alerts = [
        {
            "alert_id": "NYC-ALERT-001",
            "city_id": "nyc",
            "h3_index": "892a1072893ffff",
            "lims_score": 92.0,
            "predicted_delta_6m": 0.09,
            "predicted_delta_12m": 0.16,
            "macro_outperformance_prob_18m": 0.94,
            "centroid_lat": 40.7128,
            "centroid_lng": -74.0060,
        },
        {
            "alert_id": "CHI-ALERT-001",
            "city_id": "chicago",
            "h3_index": "89275936477ffff",
            "lims_score": 88.0,
            "predicted_delta_6m": 0.07,
            "predicted_delta_12m": 0.13,
            "macro_outperformance_prob_18m": 0.89,
            "centroid_lat": 41.8781,
            "centroid_lng": -87.6298,
        },
    ]
    in_memory_storage.insert_catalyst_alerts(alerts)

    nyc_alerts = in_memory_storage.get_recent_alerts(city_id="nyc")
    assert len(nyc_alerts) == 1
    assert nyc_alerts[0]["alert_id"] == "NYC-ALERT-001"
    assert nyc_alerts[0]["city_id"] == "nyc"

    chi_alerts = in_memory_storage.get_recent_alerts(city_id="chicago")
    assert len(chi_alerts) == 1
    assert chi_alerts[0]["alert_id"] == "CHI-ALERT-001"
    assert chi_alerts[0]["city_id"] == "chicago"

    all_alerts = in_memory_storage.get_recent_alerts()
    assert len(all_alerts) == 2


def test_sync_from_duckdb(in_memory_storage, sample_permit_event, sample_complaint_event, sample_sla_event, sample_deed_event):
    pipeline = SpatialFeaturePipeline(db_path=":memory:")
    pipeline.insert_permits(pd.DataFrame([sample_permit_event.model_dump()]))
    pipeline.insert_complaints(pd.DataFrame([sample_complaint_event.model_dump()]))
    pipeline.insert_sla(pd.DataFrame([sample_sla_event.model_dump()]))
    pipeline.insert_deeds(pd.DataFrame([sample_deed_event.model_dump()]))

    # Compute features for H3 cell
    feats = pipeline.compute_h3_cell_features(sample_permit_event.h3_res9, resolution=9)
    pipeline.con.execute("""
        INSERT INTO feature_store_h3 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        feats["h3_index"], feats["h3_resolution"], feats["as_of_date"],
        feats["capex_density_decayed"], feats["permit_count_60d"], feats["permit_count_180d"],
        feats["permit_velocity"], feats["complaints_neglect_count"], feats["complaints_qol_count"],
        feats["shift_ratio_311"], feats["sla_active_licenses"], feats["sla_new_filings_90d"],
        feats["deed_total_volume_180d"], feats["deed_transaction_count_180d"], feats["lims_score"]
    ])

    in_memory_storage.sync_from_duckdb(pipeline)

    with in_memory_storage.engine.connect() as conn:
        permits_cnt = conn.execute(text("SELECT COUNT(*) FROM municipal_permits")).scalar()
        complaints_cnt = conn.execute(text("SELECT COUNT(*) FROM municipal_311_complaints")).scalar()
        sla_cnt = conn.execute(text("SELECT COUNT(*) FROM municipal_sla_licenses")).scalar()
        deeds_cnt = conn.execute(text("SELECT COUNT(*) FROM municipal_deeds")).scalar()
        features_cnt = conn.execute(text("SELECT COUNT(*) FROM feature_store_h3_spatial")).scalar()

        assert permits_cnt == 1
        assert complaints_cnt == 1
        assert sla_cnt == 1
        assert deeds_cnt == 1
        assert features_cnt == 1


def test_sync_kafka_record(in_memory_storage, sample_permit_event, sample_complaint_event):
    in_memory_storage.sync_kafka_record(sample_permit_event.model_dump(), settings.topic_permits)
    in_memory_storage.sync_kafka_record(sample_complaint_event.model_dump(), settings.topic_311)

    with in_memory_storage.engine.connect() as conn:
        p_cnt = conn.execute(text("SELECT COUNT(*) FROM municipal_permits")).scalar()
        c_cnt = conn.execute(text("SELECT COUNT(*) FROM municipal_311_complaints")).scalar()
        assert p_cnt == 1
        assert c_cnt == 1

