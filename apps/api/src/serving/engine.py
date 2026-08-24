"""ONNX Runtime CUDA / CPU inference engine and multi-horizon model orchestrator."""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import onnxruntime as ort
import pandas as pd
from src.config import settings
from src.features.lims_calculator import LIMSCalculator
from src.models.dcn_v2 import MultiScaleDCNv2
from src.models.explainability import CatalystExplainer
from src.models.export_onnx import ONNXModelExporter
from src.models.quantile_lgbm import FEATURE_COLUMNS, LightGBMQuantilePredictor
from src.models.st_gnn import SpatioTemporalGNN
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)


class MultiHorizonInferenceEngine:
    """Orchestrates real-time multi-horizon predictions across LightGBM, ST-GNN, and DCN-v2 models."""

    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = Path(model_dir or settings.onnx_model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.indexer = H3SpatialIndexer()
        self.lims_calc = LIMSCalculator()
        self.explainer = CatalystExplainer()

        # Models
        self.lgbm_predictor = LightGBMQuantilePredictor()
        self.dcn_session: Optional[ort.InferenceSession] = None
        self.st_gnn_session: Optional[ort.InferenceSession] = None

        self._init_models()

    def _init_models(self):
        """Initialize or train default synthetic weights for immediate serving."""
        # Train baseline LightGBM model
        np.random.seed(42)
        dummy_X = pd.DataFrame(np.random.rand(200, len(FEATURE_COLUMNS)) * 100.0, columns=FEATURE_COLUMNS)
        dummy_y = (
            0.0001 * dummy_X["capex_density_decayed"]
            + 0.05 * dummy_X["permit_velocity"]
            + 0.02 * dummy_X["shift_ratio_311"]
            + np.random.randn(200) * 0.01
        )
        self.lgbm_predictor.train(dummy_X, dummy_y, n_estimators=50)
        self.explainer.fit_explainer(self.lgbm_predictor.models[0.5])

        # Export and load DCN-v2 ONNX model
        dcn_model = MultiScaleDCNv2(in_features=len(FEATURE_COLUMNS))
        exporter = ONNXModelExporter(output_dir=str(self.model_dir))
        dcn_onnx_path = exporter.export_dcn_v2(dcn_model, in_features=len(FEATURE_COLUMNS))

        # Select execution provider
        providers = [settings.onnx_execution_provider, "CPUExecutionProvider"]
        avail = [p for p in providers if p in ort.get_available_providers()]
        if not avail:
            avail = ["CPUExecutionProvider"]

        self.dcn_session = ort.InferenceSession(str(dcn_onnx_path), providers=avail)

        # Export and load ST-GNN ONNX model
        st_gnn_model = SpatioTemporalGNN(in_features=len(FEATURE_COLUMNS))
        gnn_onnx_path = exporter.export_st_gnn(st_gnn_model, seq_len=4, num_nodes=1, in_features=len(FEATURE_COLUMNS))
        self.st_gnn_session = ort.InferenceSession(str(gnn_onnx_path), providers=avail)

        logger.info("Inference engine initialized with ONNX provider: %s", avail[0])

    def predict_cell_features(
        self,
        h3_index: str,
        feature_dict: Dict[str, Any],
        include_shap: bool = True,
    ) -> Dict[str, Any]:
        """Execute multi-horizon inference for a single H3 cell."""
        t0 = time.perf_counter()

        # Build feature vector
        row = pd.Series({col: float(feature_dict.get(col, 0.0)) for col in FEATURE_COLUMNS})
        df_input = pd.DataFrame([row])

        # 1. 6-Month LightGBM Quantile Forecast
        lgbm_preds = self.lgbm_predictor.predict(df_input)
        delta_p10 = float(lgbm_preds.get("p10", [0.0])[0])
        delta_p50 = float(lgbm_preds.get("p50", [0.0])[0])
        delta_p90 = float(lgbm_preds.get("p90", [0.0])[0])

        # 2. 18-Month DCN-v2 Macro Outperformance Probability
        feat_arr = df_input.to_numpy(dtype=np.float32)
        dcn_out = self.dcn_session.run(None, {"features": feat_arr})[0]
        prob_18m = float(dcn_out[0][0])

        # 3. 12-Month ST-GNN Spatial Spillover Forecast
        seq_input = np.repeat(feat_arr[np.newaxis, :, :], 4, axis=0)  # [4, 1, in_features]
        adj_input = np.eye(1, dtype=np.float32)
        h_input = np.zeros((1, 64), dtype=np.float32)
        gnn_out = self.st_gnn_session.run(None, {
            "x_seq": seq_input,
            "norm_adj": adj_input,
            "h_prev": h_input,
        })[0]
        delta_12m = float(gnn_out[0][0])

        # 4. LIMS Score & Catalyst Flag
        lims_val = float(feature_dict.get("lims_score", 0.0))
        if lims_val == 0.0:
            lims_val = self.lims_calc.compute_scaled_lims(
                capex=float(feature_dict.get("capex_density_decayed", 0.0)),
                permit_velocity=float(feature_dict.get("permit_velocity", 0.0)),
                shift_ratio_311=float(feature_dict.get("shift_ratio_311", 1.0)),
                sla_activations=float(feature_dict.get("sla_new_filings_90d", 0.0)),
            )

        is_catalyst = lims_val >= settings.lims_threshold

        # 5. SHAP Attributions
        shap_vals = None
        if include_shap:
            shap_vals = self.explainer.explain_instance(row)

        lat, lng = self.indexer.h3_to_latlng(h3_index)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "h3_index": h3_index,
            "resolution": 9,
            "centroid_lat": lat,
            "centroid_lng": lng,
            "lims_score": lims_val,
            "delta_6m_p10": round(delta_p10, 4),
            "delta_6m_p50": round(delta_p50, 4),
            "delta_6m_p90": round(delta_p90, 4),
            "delta_12m_spillover": round(delta_12m, 4),
            "prob_18m_macro_outperformance": round(prob_18m, 4),
            "is_catalyst": is_catalyst,
            "shap_attributions": shap_vals,
            "inference_latency_ms": round(latency_ms, 2),
        }
