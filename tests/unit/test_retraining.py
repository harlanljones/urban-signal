"""Unit tests for Automated Walk-Forward Model Retraining Pipeline."""

from unittest.mock import MagicMock, patch

import duckdb
import numpy as np
import pandas as pd
import pytest

from src.models.dcn_v2 import MultiScaleDCNv2
from src.models.quantile_lgbm import FEATURE_COLUMNS, LightGBMQuantilePredictor
from src.models.retraining_job import run_retraining_job
from src.models.st_gnn import SpatioTemporalGNN
from src.models.trainer import ModelTrainer


@pytest.fixture
def trainer(tmp_path):
    return ModelTrainer(
        output_dir=str(tmp_path / "models_storage"),
        minio_bucket="test-urban-features",
        device="cpu",
        n_spatial_clusters=2,
        min_train_months=6,
    )


@pytest.fixture
def synthetic_df(trainer):
    return trainer.prepare_synthetic_training_data(
        n_cells=8,
        n_months=18,
        seed=123,
    )


def test_prepare_synthetic_training_data(trainer):
    df = trainer.prepare_synthetic_training_data(n_cells=6, n_months=14)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 6 * 14
    for col in FEATURE_COLUMNS:
        assert col in df.columns
    assert "target_6m" in df.columns
    assert "target_12m" in df.columns
    assert "target_18m" in df.columns
    assert "as_of_date" in df.columns
    assert "h3_index" in df.columns


def test_train_lightgbm_quantiles(trainer, synthetic_df):
    features = [c for c in FEATURE_COLUMNS if c in synthetic_df.columns]
    X_train = synthetic_df[features].iloc[:80]
    y_train = synthetic_df["target_6m"].iloc[:80]
    X_val = synthetic_df[features].iloc[80:]
    y_val = synthetic_df["target_6m"].iloc[80:]

    predictor, val_losses = trainer.train_lightgbm_quantiles(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        n_estimators=30,
    )

    assert isinstance(predictor, LightGBMQuantilePredictor)
    assert 0.1 in val_losses
    assert 0.5 in val_losses
    assert 0.9 in val_losses

    preds = predictor.predict(X_val.head(5))
    assert "p10" in preds and "p50" in preds and "p90" in preds
    assert len(preds["p50"]) == 5


def test_train_st_gnn(trainer, synthetic_df):
    model, final_loss = trainer.train_st_gnn(
        df_train=synthetic_df.iloc[:60],
        target_col="target_12m",
        seq_len=4,
        hidden_dim=32,
        epochs=5,
        batch_size=16,
    )

    assert isinstance(model, SpatioTemporalGNN)
    assert isinstance(final_loss, float)
    assert np.isfinite(final_loss)


def test_train_dcn_v2(trainer, synthetic_df):
    model, final_loss = trainer.train_dcn_v2(
        df_train=synthetic_df.iloc[:60],
        target_col="target_18m",
        cross_layers=2,
        epochs=5,
        batch_size=16,
    )

    assert isinstance(model, MultiScaleDCNv2)
    assert isinstance(final_loss, float)
    assert np.isfinite(final_loss)


def test_run_walk_forward_cross_validation(trainer, synthetic_df):
    val_summary = trainer.run_walk_forward_cross_validation(
        df=synthetic_df,
        test_window_months=3,
    )

    assert "total_folds" in val_summary
    assert val_summary["total_folds"] >= 1
    assert "avg_lgbm_p50_mae" in val_summary
    assert "avg_st_gnn_test_mae" in val_summary
    assert "avg_dcn_v2_test_bce" in val_summary

    for fold in val_summary["folds"]:
        assert fold["train_size"] > 0
        assert fold["test_size"] > 0
        assert fold["held_out_h3_7_parents_count"] > 0


def test_upload_model_artifacts_to_minio(trainer, tmp_path):
    mock_file1 = tmp_path / "model1.onnx"
    mock_file1.write_bytes(b"dummy onnx content")
    mock_file2 = tmp_path / "model2.onnx"
    mock_file2.write_bytes(b"dummy onnx content 2")

    with patch("src.models.trainer.Minio") as mock_minio_cls:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_minio_cls.return_value = mock_client

        uploaded = trainer.upload_model_artifacts_to_minio(
            version="20260819",
            file_paths=[mock_file1, mock_file2],
            bucket_name="test-bucket",
        )

        mock_client.bucket_exists.assert_called_once_with("test-bucket")
        mock_client.make_bucket.assert_called_once_with("test-bucket")
        assert mock_client.fput_object.call_count == 2
        assert len(uploaded) == 2
        assert "models/model1.onnx" in uploaded


def test_load_features_from_duckdb(trainer, synthetic_df):
    con = duckdb.connect(":memory:")
    con.register("synthetic_temp", synthetic_df)
    con.execute("CREATE TABLE feature_store_h3 AS SELECT * FROM synthetic_temp")

    loaded_df = trainer.load_features_from_duckdb(con, table_name="feature_store_h3")
    assert len(loaded_df) == len(synthetic_df)
    assert set(synthetic_df.columns).issubset(set(loaded_df.columns))


def test_full_retraining_pipeline_e2e(trainer, synthetic_df, tmp_path):
    with patch.object(trainer, "upload_model_artifacts_to_minio", return_value=["models/st_gnn_vtest.onnx"]):
        report = trainer.run_retraining_pipeline(
            df=synthetic_df,
            version="test_v1",
            export_onnx=True,
            upload_to_minio=True,
            epochs_gnn=2,
            epochs_dcn=2,
            n_estimators_lgbm=10,
        )

    assert report["version"] == "test_v1"
    assert "cross_validation" in report
    assert "final_losses" in report
    assert len(report["exported_artifacts"]) >= 2
    assert "benchmarks" in report

    # Check generated files in output_dir
    assert (trainer.output_dir / "st_gnn_vtest_v1.onnx").exists()
    assert (trainer.output_dir / "dcn_v2_vtest_v1.onnx").exists()
    assert (trainer.output_dir / "st_gnn_12m.onnx").exists()
    assert (trainer.output_dir / "dcn_v2_macro.onnx").exists()
    assert (trainer.output_dir / "retraining_report_vtest_v1.json").exists()


def test_retraining_job_cli(tmp_path):
    with patch("src.models.retraining_job.ModelTrainer") as mock_trainer_cls:
        mock_trainer = MagicMock()
        mock_trainer.run_retraining_pipeline.return_value = {
            "version": "cli_test_v1",
            "cross_validation": {
                "avg_lgbm_p50_mae": 0.0123,
                "avg_st_gnn_test_mae": 0.0234,
            },
        }
        mock_trainer_cls.return_value = mock_trainer

        ret = run_retraining_job(
            version="cli_test_v1",
            export_onnx=True,
            upload_to_minio=False,
            epochs_gnn=1,
            epochs_dcn=1,
            n_estimators_lgbm=5,
        )

        assert ret == 0
        mock_trainer.run_retraining_pipeline.assert_called_once()
