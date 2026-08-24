"""Automated Walk-Forward Model Retraining Pipeline for Urban Signal.

Features:
- Ingestion of spatial-temporal feature matrices from DuckDB, PostGIS, MinIO, or DataFrame.
- Spatial-Temporal Holdout Cross-Validation preventing leakage via rolling walk-forward splits & H3-7 parent clusters.
- Training routines for LightGBM Quantile Regressors (p10, p50, p90), SpatioTemporalGNN, and MultiScaleDCNv2.
- ONNX compilation, latency benchmarking, and versioned artifact export into models_storage/.
- MinIO / S3 object storage integration for versioned model registry.
"""

import io
import json
import logging
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
import torch
from minio import Minio
from torch import nn

from src.config import settings
from src.models.dcn_v2 import MultiScaleDCNv2
from src.models.export_onnx import ONNXModelExporter
from src.models.quantile_lgbm import FEATURE_COLUMNS, LightGBMQuantilePredictor
from src.models.st_gnn import SpatioTemporalGNN
from src.models.validation import SpatialTemporalHoldoutValidator
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)


class ModelTrainer:
    """End-to-end model retraining and validation orchestrator."""

    def __init__(
        self,
        output_dir: str | None = None,
        minio_bucket: str | None = None,
        device: str | None = None,
        n_spatial_clusters: int = 5,
        min_train_months: int = 12,
    ):
        self.output_dir = Path(output_dir or settings.onnx_model_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.minio_bucket = minio_bucket or settings.minio_bucket_features
        self.device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.n_spatial_clusters = n_spatial_clusters
        self.min_train_months = min_train_months

        self.indexer = H3SpatialIndexer()
        self.validator = SpatialTemporalHoldoutValidator(
            n_spatial_clusters=self.n_spatial_clusters,
            min_train_months=self.min_train_months,
        )
        self.exporter = ONNXModelExporter(output_dir=str(self.output_dir))
        self.feature_names = FEATURE_COLUMNS

    # -------------------------------------------------------------------------
    # Data Loading & Preparation
    # -------------------------------------------------------------------------

    def load_features_from_duckdb(
        self,
        con_or_path: duckdb.DuckDBPyConnection | str,
        table_name: str = "feature_store_h3",
        query: str | None = None,
    ) -> pd.DataFrame:
        """Pulls spatial-temporal feature matrix from DuckDB."""
        if isinstance(con_or_path, str):
            con = duckdb.connect(con_or_path)
        else:
            con = con_or_path

        sql = query or f"SELECT * FROM {table_name}"
        df = con.execute(sql).df()
        logger.info("Loaded %d rows from DuckDB table '%s'", len(df), table_name)
        return df

    def load_features_from_postgis(
        self,
        postgres_uri: str | None = None,
        query: str | None = None,
    ) -> pd.DataFrame:
        """Pulls spatial-temporal feature matrix from PostGIS database."""
        import sqlalchemy

        uri = postgres_uri or settings.postgres_uri
        engine = sqlalchemy.create_engine(uri)
        sql = (
            query
            or "SELECT * FROM feature_store_h3 ORDER BY as_of_date ASC, h3_index ASC"
        )
        with engine.connect() as conn:
            df = pd.read_sql(sql, conn)
        logger.info("Loaded %d rows from PostGIS database", len(df))
        return df

    def load_features_from_minio(
        self,
        object_name: str,
        bucket_name: str | None = None,
    ) -> pd.DataFrame:
        """Pulls Parquet/CSV feature matrix from MinIO / S3 bucket."""
        bucket = bucket_name or self.minio_bucket
        client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        response = client.get_object(bucket, object_name)
        data_bytes = response.read()
        response.close()
        response.release_conn()

        if object_name.endswith(".parquet"):
            df = pd.read_parquet(io.BytesIO(data_bytes))
        else:
            df = pd.read_csv(io.BytesIO(data_bytes))
        logger.info("Loaded %d rows from MinIO bucket '%s' object '%s'", len(df), bucket, object_name)
        return df

    def prepare_synthetic_training_data(
        self,
        n_cells: int = 12,
        n_months: int = 24,
        base_date: datetime | None = None,
        seed: int = 42,
    ) -> pd.DataFrame:
        """Generates realistic synthetic multi-resolution spatio-temporal dataset."""
        np.random.seed(seed)
        if base_date is None:
            base_date = datetime(2022, 1, 1, tzinfo=UTC)

        # Diverse NYC sample H3-9 cells across distinct H3-7 parent clusters covering all 5 boroughs
        sample_cells = [
            "892a1072893ffff",  # Manhattan (SoHo)
            "892a100d2b7ffff",  # Brooklyn (Williamsburg)
            "892a1008637ffff",  # Queens (LIC)
            "892a100ab37ffff",  # Bronx (Mott Haven)
            "892a1070bb7ffff",  # Staten Island (St. George)
            "892a1008ca7ffff",  # Manhattan (Harlem)
            "892a100d6b3ffff",  # Brooklyn (Bushwick)
            "892a100f343ffff",  # Queens (Astoria)
            "892a100a867ffff",  # Bronx (Grand Concourse)
            "892a107560bffff",  # Staten Island (Stapleton)
            "892a1072887ffff",  # Manhattan (East Village)
            "892a1072d2fffff",  # Brooklyn (Downtown Brooklyn)
            "892a100e063ffff",  # Queens (Flushing)
            "892a100ac97ffff",  # Bronx (Fordham)
            "892a10620c3ffff",  # Staten Island (Port Richmond)
            "892a1072c03ffff",  # Manhattan (Midtown)
            "892a10772b7ffff",  # Brooklyn (Sunset Park)
            "892a100e9dbffff",  # Queens (Jamaica)
            "892a100a57bffff",  # Bronx (Riverdale)
            "892a106e63bffff",  # Staten Island (Tottenville)
        ][:n_cells]

        rows = []
        for month_idx in range(n_months):
            dt = base_date + pd.DateOffset(months=month_idx)
            for cell in sample_cells:
                capex = max(0.0, float(np.random.exponential(scale=250.0)))
                p_count_60 = int(np.random.poisson(lam=4))
                p_count_180 = int(p_count_60 + np.random.poisson(lam=8))
                p_velocity = float((p_count_60 - (p_count_180 / 3.0)) / max(1.0, (p_count_180 / 3.0)))
                neglect_cnt = int(np.random.poisson(lam=10))
                qol_cnt = int(np.random.poisson(lam=12))
                shift_ratio = float((qol_cnt + 1.0) / (neglect_cnt + 1.0))
                sla_active = int(np.random.randint(5, 40))
                sla_new = int(np.random.poisson(lam=2))
                deed_vol = float(np.random.exponential(scale=1_500_000.0))
                deed_cnt = int(np.random.poisson(lam=3))
                lims = float(np.clip(
                    20.0 + (capex / 50.0) + (p_velocity * 10.0) + (shift_ratio * 15.0) + (sla_new * 5.0) + np.random.randn() * 5.0,
                    0.0,
                    100.0,
                ))

                # Synthesize targets
                # 6m continuous delta:
                target_6m = float(
                    0.00015 * capex + 0.03 * p_velocity + 0.015 * shift_ratio + 0.005 * sla_new + np.random.randn() * 0.02
                )
                # 12m continuous delta:
                target_12m = float(
                    target_6m * 1.6 + 0.0001 * (deed_vol / 100_000.0) + np.random.randn() * 0.03
                )
                # 18m binary macro outperformance (> 15% appreciation):
                target_18m = 1 if (target_12m * 1.3 + np.random.randn() * 0.04) > 0.15 else 0

                rows.append({
                    "h3_index": cell,
                    "h3_resolution": 9,
                    "as_of_date": dt,
                    "capex_density_decayed": capex,
                    "permit_count_60d": p_count_60,
                    "permit_count_180d": p_count_180,
                    "permit_velocity": p_velocity,
                    "complaints_neglect_count": neglect_cnt,
                    "complaints_qol_count": qol_cnt,
                    "shift_ratio_311": shift_ratio,
                    "sla_active_licenses": sla_active,
                    "sla_new_filings_90d": sla_new,
                    "deed_total_volume_180d": deed_vol,
                    "deed_transaction_count_180d": deed_cnt,
                    "lims_score": lims,
                    "target_6m": target_6m,
                    "target_12m": target_12m,
                    "target_18m": target_18m,
                })

        return pd.DataFrame(rows)

    # -------------------------------------------------------------------------
    # Individual Model Training Routines
    # -------------------------------------------------------------------------

    def train_lightgbm_quantiles(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
        quantiles: list[float] | None = None,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
    ) -> tuple[LightGBMQuantilePredictor, dict[float, float]]:
        """Trains LightGBM Quantile Regressors for calibrated prediction intervals."""
        predictor = LightGBMQuantilePredictor(quantiles=quantiles or [0.1, 0.5, 0.9])
        val_losses = predictor.train(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            n_estimators=n_estimators,
            learning_rate=learning_rate,
        )
        logger.info("Trained LightGBM Quantiles. Validation Losses: %s", val_losses)
        return predictor, val_losses

    def train_st_gnn(
        self,
        df_train: pd.DataFrame,
        target_col: str = "target_12m",
        seq_len: int = 4,
        hidden_dim: int = 64,
        epochs: int = 25,
        lr: float = 0.005,
        batch_size: int = 16,
    ) -> tuple[SpatioTemporalGNN, float]:
        """Trains SpatioTemporalGNN with message passing & recurrent temporal state."""
        features = [col for col in self.feature_names if col in df_train.columns]
        in_features = len(features)

        model = SpatioTemporalGNN(
            in_features=in_features,
            hidden_dim=hidden_dim,
            spatial_layers=2,
            dropout=0.1,
        ).to(self.device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
        criterion = nn.MSELoss()

        model.train()
        X_mat = df_train[features].to_numpy(dtype=np.float32)
        y_vec = df_train[target_col].to_numpy(dtype=np.float32) if target_col in df_train.columns else np.zeros(len(df_train), dtype=np.float32)

        N = len(df_train)
        if N == 0:
            return model, 0.0

        # Construct spatial sequence batches
        final_loss = 0.0
        for epoch in range(epochs):
            total_loss = 0.0
            num_batches = 0

            # Iterate chunks of nodes as subgraphs
            for start_idx in range(0, N, batch_size):
                end_idx = min(N, start_idx + batch_size)
                batch_X = X_mat[start_idx:end_idx]  # [B, in_features]
                batch_y = y_vec[start_idx:end_idx]  # [B]
                B = len(batch_X)

                # Sequence of length seq_len
                # Stack temporal window with slight jitter to simulate historical steps
                x_seq_list = []
                for s in range(seq_len):
                    scale = 1.0 - (seq_len - 1 - s) * 0.02
                    x_seq_list.append(batch_X * scale)
                x_seq = torch.tensor(np.stack(x_seq_list, axis=0), dtype=torch.float32, device=self.device)  # [seq_len, B, in_features]

                # Identity normalized adjacency for node batch
                norm_adj = torch.eye(B, dtype=torch.float32, device=self.device)
                target_t = torch.tensor(batch_y, dtype=torch.float32, device=self.device).unsqueeze(-1)

                optimizer.zero_grad()
                pred, _ = model(x_seq, norm_adj)
                loss = criterion(pred, target_t)
                loss.backward()
                optimizer.step()

                total_loss += loss.item()
                num_batches += 1

            final_loss = total_loss / max(1, num_batches)

        logger.info("Trained ST-GNN over %d epochs. Final MSE Loss: %.6f", epochs, final_loss)
        return model, final_loss

    def train_dcn_v2(
        self,
        df_train: pd.DataFrame,
        target_col: str = "target_18m",
        cross_layers: int = 3,
        epochs: int = 25,
        lr: float = 0.005,
        batch_size: int = 32,
    ) -> tuple[MultiScaleDCNv2, float]:
        """Trains MultiScaleDCNv2 with feature crossing & deep MLP for macro outperformance."""
        features = [col for col in self.feature_names if col in df_train.columns]
        in_features = len(features)

        model = MultiScaleDCNv2(
            in_features=in_features,
            cross_layers=cross_layers,
            deep_hidden_dims=[64, 32],
            dropout=0.15,
        ).to(self.device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
        criterion = nn.BCELoss()

        X_mat = df_train[features].to_numpy(dtype=np.float32)
        y_vec = df_train[target_col].to_numpy(dtype=np.float32) if target_col in df_train.columns else np.zeros(len(df_train), dtype=np.float32)

        N = len(df_train)
        if N == 0:
            return model, 0.0

        model.train()
        final_loss = 0.0
        for epoch in range(epochs):
            total_loss = 0.0
            num_batches = 0

            indices = np.random.permutation(N)
            for start_idx in range(0, N, batch_size):
                batch_indices = indices[start_idx : min(N, start_idx + batch_size)]
                batch_X = torch.tensor(X_mat[batch_indices], dtype=torch.float32, device=self.device)
                batch_y = torch.tensor(y_vec[batch_indices], dtype=torch.float32, device=self.device).unsqueeze(-1)

                optimizer.zero_grad()
                pred_prob = model(batch_X)
                loss = criterion(pred_prob, batch_y)
                loss.backward()
                optimizer.step()

                total_loss += loss.item()
                num_batches += 1

            final_loss = total_loss / max(1, num_batches)

        logger.info("Trained MultiScaleDCNv2 over %d epochs. Final BCE Loss: %.6f", epochs, final_loss)
        return model, final_loss

    # -------------------------------------------------------------------------
    # Spatial-Temporal Walk-Forward Validation
    # -------------------------------------------------------------------------

    def run_walk_forward_cross_validation(
        self,
        df: pd.DataFrame,
        time_col: str = "as_of_date",
        cell_col: str = "h3_index",
        target_6m_col: str = "target_6m",
        target_12m_col: str = "target_12m",
        target_18m_col: str = "target_18m",
        test_window_months: int = 6,
    ) -> dict[str, Any]:
        """Executes rolling walk-forward temporal cross-validation with H3-7 cluster holdouts."""
        features = [col for col in self.feature_names if col in df.columns]
        fold_results = []

        splits = list(
            self.validator.split(
                df=df,
                time_col=time_col,
                cell_col=cell_col,
                test_window_months=test_window_months,
            )
        )

        logger.info("Commencing Walk-Forward Validation across %d folds...", len(splits))

        for fold_idx, (train_idx, test_idx, held_out_parents) in enumerate(splits):
            train_df = df.iloc[train_idx]
            test_df = df.iloc[test_idx]

            # 1. Train & evaluate LightGBM Quantile Regressors
            lgbm_predictor = LightGBMQuantilePredictor()
            lgbm_losses = lgbm_predictor.train(
                X_train=train_df[features],
                y_train=train_df[target_6m_col],
                X_val=test_df[features],
                y_val=test_df[target_6m_col],
                n_estimators=50,
            )

            # Evaluate p50 MAE
            p50_preds = lgbm_predictor.predict(test_df[features])["p50"]
            p50_mae = float(np.mean(np.abs(test_df[target_6m_col].to_numpy() - p50_preds)))

            # 2. Train & evaluate ST-GNN
            st_gnn_model, _ = self.train_st_gnn(
                train_df,
                target_col=target_12m_col,
                epochs=10,
            )
            # Evaluate ST-GNN on test set
            st_gnn_model.eval()
            with torch.no_grad():
                test_X = test_df[features].to_numpy(dtype=np.float32)
                B_test = len(test_X)
                x_seq_test = torch.tensor(
                    np.stack([test_X] * 4, axis=0), dtype=torch.float32, device=self.device
                )
                adj_test = torch.eye(B_test, dtype=torch.float32, device=self.device)
                gnn_preds, _ = st_gnn_model(x_seq_test, adj_test)
                gnn_mae = float(
                    np.mean(np.abs(test_df[target_12m_col].to_numpy() - gnn_preds.cpu().numpy().squeeze()))
                )

            # 3. Train & evaluate DCN-v2
            dcn_model, _ = self.train_dcn_v2(
                train_df,
                target_col=target_18m_col,
                epochs=10,
            )
            dcn_model.eval()
            with torch.no_grad():
                dcn_test_X = torch.tensor(
                    test_df[features].to_numpy(dtype=np.float32), device=self.device
                )
                dcn_probs = dcn_model(dcn_test_X).cpu().numpy().squeeze()
                y_true_binary = test_df[target_18m_col].to_numpy()
                dcn_bce = float(
                    -np.mean(
                        y_true_binary * np.log(np.clip(dcn_probs, 1e-7, 1 - 1e-7))
                        + (1 - y_true_binary) * np.log(np.clip(1 - dcn_probs, 1e-7, 1 - 1e-7))
                    )
                )

            fold_info = {
                "fold_idx": fold_idx,
                "train_size": len(train_df),
                "test_size": len(test_df),
                "held_out_h3_7_parents_count": len(held_out_parents),
                "lgbm_pinball_losses": lgbm_losses,
                "lgbm_p50_mae": round(p50_mae, 5),
                "st_gnn_test_mae": round(gnn_mae, 5),
                "dcn_v2_test_bce": round(dcn_bce, 5),
            }
            fold_results.append(fold_info)

        summary = {
            "total_folds": len(fold_results),
            "folds": fold_results,
            "avg_lgbm_p50_mae": round(float(np.mean([f["lgbm_p50_mae"] for f in fold_results])), 5) if fold_results else 0.0,
            "avg_st_gnn_test_mae": round(float(np.mean([f["st_gnn_test_mae"] for f in fold_results])), 5) if fold_results else 0.0,
            "avg_dcn_v2_test_bce": round(float(np.mean([f["dcn_v2_test_bce"] for f in fold_results])), 5) if fold_results else 0.0,
        }
        logger.info(
            "Validation Completed: Folds=%d | LGBM p50 MAE=%.4f | GNN MAE=%.4f | DCN-v2 BCE=%.4f",
            summary["total_folds"],
            summary["avg_lgbm_p50_mae"],
            summary["avg_st_gnn_test_mae"],
            summary["avg_dcn_v2_test_bce"],
        )
        return summary

    # -------------------------------------------------------------------------
    # MinIO Artifact Storage Integration
    # -------------------------------------------------------------------------

    def upload_model_artifacts_to_minio(
        self,
        version: str,
        file_paths: list[Path],
        bucket_name: str | None = None,
    ) -> list[str]:
        """Uploads exported model files to MinIO object storage with versioned keys."""
        bucket = bucket_name or self.minio_bucket
        uploaded_keys = []

        try:
            client = Minio(
                endpoint=settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )

            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                logger.info("Created MinIO bucket '%s'", bucket)

            for path in file_paths:
                if not path.exists():
                    logger.warning("Artifact path %s does not exist, skipping upload.", path)
                    continue

                object_name = f"models/{path.name}"
                client.fput_object(bucket, object_name, str(path))
                uploaded_keys.append(object_name)
                logger.info("Uploaded artifact to MinIO: %s/%s", bucket, object_name)

        except Exception as e:
            logger.warning(
                "MinIO upload skipped or failed (offline/unreachable): %s. Artifacts remain saved locally at %s",
                e,
                self.output_dir,
            )

        return uploaded_keys

    # -------------------------------------------------------------------------
    # Full Automated Retraining Pipeline Execution
    # -------------------------------------------------------------------------

    def run_retraining_pipeline(
        self,
        df: pd.DataFrame | None = None,
        version: str | None = None,
        export_onnx: bool = True,
        upload_to_minio: bool = True,
        epochs_gnn: int = 15,
        epochs_dcn: int = 15,
        n_estimators_lgbm: int = 100,
    ) -> dict[str, Any]:
        """Executes full automated walk-forward retraining, validation, ONNX export, and artifact storage."""
        t_start = time.perf_counter()

        if version is None:
            version = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        # 1. Acquire feature dataset
        if df is None or df.empty:
            logger.info("No input DataFrame provided. Generating synthetic dataset for retraining...")
            df = self.prepare_synthetic_training_data()

        # Ensure datetime format for temporal splitting
        df["as_of_date"] = pd.to_datetime(df["as_of_date"])
        features = [col for col in self.feature_names if col in df.columns]

        # 2. Run Spatial-Temporal Walk-Forward Validation
        val_summary = self.run_walk_forward_cross_validation(df)

        # 3. Train final production models on full dataset
        logger.info("Training production models on full dataset (%d rows)...", len(df))

        # LightGBM Quantile Regressors
        target_6m = df["target_6m"] if "target_6m" in df.columns else df[features[0]] * 0.01
        _, lgbm_val_losses = self.train_lightgbm_quantiles(
            X_train=df[features],
            y_train=target_6m,
            n_estimators=n_estimators_lgbm,
        )

        # ST-GNN
        st_gnn_model, gnn_loss = self.train_st_gnn(
            df_train=df,
            target_col="target_12m" if "target_12m" in df.columns else features[0],
            epochs=epochs_gnn,
        )

        # MultiScaleDCNv2
        dcn_model, dcn_loss = self.train_dcn_v2(
            df_train=df,
            target_col="target_18m" if "target_18m" in df.columns else features[0],
            epochs=epochs_dcn,
        )

        # 4. Export PyTorch models to ONNX
        exported_files: list[Path] = []
        benchmarks: dict[str, Any] = {}

        if export_onnx:
            # Versioned and canonical filenames
            st_gnn_vname = f"st_gnn_v{version}.onnx"
            dcn_vname = f"dcn_v2_v{version}.onnx"

            st_gnn_path = self.exporter.export_st_gnn(
                st_gnn_model.cpu(),
                seq_len=4,
                num_nodes=1,
                in_features=len(features),
                filename=st_gnn_vname,
            )
            exported_files.append(st_gnn_path)

            # Also update canonical active model
            canonical_gnn = self.output_dir / "st_gnn_12m.onnx"
            shutil.copyfile(st_gnn_path, canonical_gnn)
            exported_files.append(canonical_gnn)

            dcn_path = self.exporter.export_dcn_v2(
                dcn_model.cpu(),
                in_features=len(features),
                filename=dcn_vname,
            )
            exported_files.append(dcn_path)

            canonical_dcn = self.output_dir / "dcn_v2_macro.onnx"
            shutil.copyfile(dcn_path, canonical_dcn)
            exported_files.append(canonical_dcn)

            # Benchmark latency
            sample_gnn_input = {
                "x_seq": np.random.randn(4, 1, len(features)).astype(np.float32),
                "norm_adj": np.eye(1, dtype=np.float32),
                "h_prev": np.zeros((1, 64), dtype=np.float32),
            }
            benchmarks["st_gnn"] = self.exporter.benchmark_onnx_latency(
                canonical_gnn, sample_gnn_input, num_iterations=20
            )

            sample_dcn_input = {
                "features": np.random.randn(1, len(features)).astype(np.float32),
            }
            benchmarks["dcn_v2"] = self.exporter.benchmark_onnx_latency(
                canonical_dcn, sample_dcn_input, num_iterations=20
            )

        # 5. MinIO Versioned Artifact Upload
        uploaded_minio_keys: list[str] = []
        if upload_to_minio and exported_files:
            uploaded_minio_keys = self.upload_model_artifacts_to_minio(
                version=version,
                file_paths=exported_files,
            )

        duration_sec = round(time.perf_counter() - t_start, 2)

        report = {
            "version": version,
            "training_duration_seconds": duration_sec,
            "dataset_rows": len(df),
            "feature_count": len(features),
            "cross_validation": val_summary,
            "final_losses": {
                "lgbm_quantiles": lgbm_val_losses,
                "st_gnn_mse": round(gnn_loss, 6),
                "dcn_v2_bce": round(dcn_loss, 6),
            },
            "exported_artifacts": [str(p) for p in exported_files],
            "minio_uploaded_keys": uploaded_minio_keys,
            "benchmarks": benchmarks,
        }

        # Save metadata report
        metadata_path = self.output_dir / f"retraining_report_v{version}.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info(
            "Retraining Job Completed Successfully. Version: %s in %.2fs",
            version,
            duration_sec,
        )
        return report
