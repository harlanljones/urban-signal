"""Automated Retraining Job Runner and CLI Entrypoint.

Can be scheduled via Kubernetes CronJob, Airflow, or standalone systemd/cron timers.
"""

import argparse
import json
import logging
import sys

from src.models.trainer import ModelTrainer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_retraining_job(
    version: str | None = None,
    export_onnx: bool = True,
    upload_to_minio: bool = True,
    duckdb_path: str | None = None,
    epochs_gnn: int = 15,
    epochs_dcn: int = 15,
    n_estimators_lgbm: int = 100,
) -> int:
    """Executes model retraining job."""
    logger.info("Initializing Retraining Job...")
    trainer = ModelTrainer()

    df = None
    if duckdb_path:
        logger.info("Loading feature data from DuckDB database: %s", duckdb_path)
        df = trainer.load_features_from_duckdb(duckdb_path)

    report = trainer.run_retraining_pipeline(
        df=df,
        version=version,
        export_onnx=export_onnx,
        upload_to_minio=upload_to_minio,
        epochs_gnn=epochs_gnn,
        epochs_dcn=epochs_dcn,
        n_estimators_lgbm=n_estimators_lgbm,
    )

    logger.info(
        "Retraining completed with status SUCCESS. Version: %s | LGBM MAE: %.4f | ST-GNN MAE: %.4f",
        report["version"],
        report["cross_validation"]["avg_lgbm_p50_mae"],
        report["cross_validation"]["avg_st_gnn_test_mae"],
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Urban Predictor Walk-Forward Model Retraining Job")
    parser.add_argument("--version", type=str, default=None, help="Explicit model version string")
    parser.add_argument("--no-onnx", action="store_true", help="Disable ONNX model compilation")
    parser.add_argument("--no-minio", action="store_true", help="Disable MinIO / S3 artifact upload")
    parser.add_argument("--duckdb-path", type=str, default=None, help="Path to DuckDB database")
    parser.add_argument("--epochs-gnn", type=int, default=15, help="ST-GNN training epochs")
    parser.add_argument("--epochs-dcn", type=int, default=15, help="DCN-v2 training epochs")
    parser.add_argument("--n-estimators-lgbm", type=int, default=100, help="LightGBM estimators")

    args = parser.parse_args()

    exit_code = run_retraining_job(
        version=args.version,
        export_onnx=not args.no_onnx,
        upload_to_minio=not args.no_minio,
        duckdb_path=args.duckdb_path,
        epochs_gnn=args.epochs_gnn,
        epochs_dcn=args.epochs_dcn,
        n_estimators_lgbm=args.n_estimators_lgbm,
    )
    sys.exit(exit_code)
