"""ONNX Runtime CUDA / CPU inference engine and multi-horizon model orchestrator."""

import copy
import logging
import time
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Any

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

# ---------------------------------------------------------------------------
# Synthetic serving baseline (US-421)
# ---------------------------------------------------------------------------
#
# No trained 6-month model is persisted anywhere in this repo; the serving
# engine stands one up at boot. The previous baseline sampled all twelve
# FEATURE_COLUMNS uniformly on [0, 100] and fit an arbitrary-scale target.
# Real serving rows look nothing like that: `router.get_active_catalysts` and
# `get_grid_geojson` populate only five of the twelve columns (the other seven
# default to 0.0 because no submarket-level source exists for them), capex
# arrives around 3e6-1.4e7, and LIMS sits in the 60-95 band. Training on a
# disjoint support made every tree fall through to one leaf, so p50 was a
# constant ~1.39 that the dashboard rendered as "+139.1% 6M" on every row.
#
# The sampler below mirrors the serving row shape exactly — same five populated
# columns, same ranges, same seven zeros — and the target carries fractional
# 6-month return semantics so the dashboard's `value * 100` renders a
# percentage rather than a three-digit number.
SYNTHETIC_TRAINING_ROWS = 4000
SYNTHETIC_SEED = 42
PREDICTION_CACHE_MAXSIZE = 16_384

# Feature ranges taken from the submarket registry (src/spatial/submarkets.py).
_LIMS_RANGE = (55.0, 97.0)
_CAPEX_RANGE = (2.0e6, 1.6e7)
_PERMIT_VEL_RANGE = (0.10, 0.80)   # router divides raw velocity by 100
_SHIFT_RATIO_RANGE = (1.00, 1.85)
_SLA_RANGE = (5.0, 95.0)


def build_synthetic_baseline(
    n_rows: int = SYNTHETIC_TRAINING_ROWS,
    seed: int = SYNTHETIC_SEED,
    n_estimators: int = 200,
    lgb_seed: int | None = None,
) -> LightGBMQuantilePredictor:
    """Fit the boot-time quantile baseline on serving-shaped synthetic rows.

    Returns a predictor whose p10/p50/p90 outputs are fractional 6-month
    returns that vary with the input row.
    """
    rng = np.random.default_rng(seed)

    lims = rng.uniform(*_LIMS_RANGE, n_rows)
    capex = rng.uniform(*_CAPEX_RANGE, n_rows)
    permit_vel = rng.uniform(*_PERMIT_VEL_RANGE, n_rows)
    shift_ratio = rng.uniform(*_SHIFT_RATIO_RANGE, n_rows)
    sla = rng.uniform(*_SLA_RANGE, n_rows)

    frame = pd.DataFrame(
        {col: np.zeros(n_rows, dtype=float) for col in FEATURE_COLUMNS}
    )
    frame["lims_score"] = lims
    frame["capex_density_decayed"] = capex
    frame["permit_velocity"] = permit_vel
    frame["shift_ratio_311"] = shift_ratio
    frame["sla_new_filings_90d"] = sla

    # Fractional 6-month return: a ~-2%..+18% band led by LIMS, with capex
    # density, permit velocity and 311 shift as secondary lifts.
    target = (
        -0.02
        + 0.14 * ((lims - _LIMS_RANGE[0]) / (_LIMS_RANGE[1] - _LIMS_RANGE[0]))
        + 0.03 * (capex / _CAPEX_RANGE[1])
        + 0.04 * permit_vel
        + 0.02 * (shift_ratio - 1.0)
        + 0.01 * (sla / _SLA_RANGE[1])
        + rng.normal(0.0, 0.012, n_rows)
    )

    predictor = LightGBMQuantilePredictor()
    predictor.train(frame, pd.Series(target), n_estimators=n_estimators, seed=lgb_seed)
    return predictor


class MultiHorizonInferenceEngine:
    """Orchestrates real-time multi-horizon predictions across LightGBM, ST-GNN, and DCN-v2 models."""

    def __init__(
        self,
        model_dir: str | None = None,
        *,
        cache_predictions: bool = False,
        metrics: Any = None,
        model_bundle: str | Path | None = None,
    ):
        self.cache_predictions = cache_predictions
        self.metrics = metrics
        self.model_bundle_id: str | None = None
        self.model_provenance = "synthetic-default"
        self._prediction_cache: OrderedDict[tuple[float, ...], dict[str, float]] = OrderedDict()
        self._explanation_cache: OrderedDict[tuple[float, ...], dict[str, float]] = OrderedDict()
        self._prediction_cache_lock = RLock()
        self._explanation_cache_lock = RLock()
        self.model_dir = Path(model_dir or settings.onnx_model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.indexer = H3SpatialIndexer()
        self.lims_calc = LIMSCalculator()
        self.explainer = CatalystExplainer()

        # Models
        self.lgbm_predictor = LightGBMQuantilePredictor()
        self.dcn_session: ort.InferenceSession | None = None
        self.st_gnn_session: ort.InferenceSession | None = None

        if model_bundle is not None:
            # bundle.py imports this module's synthetic baseline, so the import
            # stays inside the method to avoid a cycle at module load.
            from src.models.bundle import load_bundle

            self._init_from_bundle(load_bundle(Path(model_bundle), expected_provenance="synthetic"))
        else:
            self._init_models()

    def _increment_metric(self, name: str) -> None:
        """Increment an optional snapshot counter without importing its module."""
        if self.metrics is not None:
            self.metrics.increment(name, count=1)

    @staticmethod
    def _feature_key(feature_dict: dict[str, Any]) -> tuple[float, ...]:
        """Return the normalized, ordered serving vector used by all models."""
        vector = tuple(float(feature_dict.get(column, 0.0)) for column in FEATURE_COLUMNS)
        if not np.isfinite(vector).all():
            raise ValueError("feature inputs must be finite")
        return vector

    def clear_prediction_caches(self) -> None:
        """Drop cached model values while keeping this engine's weights intact."""
        with self._prediction_cache_lock:
            self._prediction_cache.clear()
        with self._explanation_cache_lock:
            self._explanation_cache.clear()

    def _predict_values(self, vector: tuple[float, ...]) -> dict[str, float]:
        """Return model-only outputs, reusing identical feature vectors when enabled."""
        if self.cache_predictions:
            with self._prediction_cache_lock:
                cached = self._prediction_cache.get(vector)
                if cached is not None:
                    self._prediction_cache.move_to_end(vector)
                    self._increment_metric("prediction_cache_hits")
                    return copy.deepcopy(cached)
                values = self._compute_prediction_values(vector)
                self._prediction_cache[vector] = copy.deepcopy(values)
                if len(self._prediction_cache) > PREDICTION_CACHE_MAXSIZE:
                    self._prediction_cache.popitem(last=False)
                return copy.deepcopy(values)
        return self._compute_prediction_values(vector)

    def _compute_prediction_values(self, vector: tuple[float, ...]) -> dict[str, float]:
        row = pd.Series(dict(zip(FEATURE_COLUMNS, vector)))
        df_input = pd.DataFrame([row])
        self._increment_metric("inference_calls")

        lgbm_preds = self.lgbm_predictor.predict(df_input)
        delta_p10 = float(lgbm_preds.get("p10", [0.0])[0])
        delta_p50 = float(lgbm_preds.get("p50", [0.0])[0])
        delta_p90 = float(lgbm_preds.get("p90", [0.0])[0])

        feat_arr = df_input.to_numpy(dtype=np.float32)
        dcn_out = self.dcn_session.run(None, {"features": feat_arr})[0]
        prob_18m = float(dcn_out[0][0])

        seq_input = np.repeat(feat_arr[np.newaxis, :, :], 4, axis=0)
        adj_input = np.eye(1, dtype=np.float32)
        h_input = np.zeros((1, 64), dtype=np.float32)
        gnn_out = self.st_gnn_session.run(None, {
            "x_seq": seq_input,
            "norm_adj": adj_input,
            "h_prev": h_input,
        })[0]
        delta_12m = float(gnn_out[0][0])
        return {
            "delta_6m_p10": round(delta_p10, 4),
            "delta_6m_p50": round(delta_p50, 4),
            "delta_6m_p90": round(delta_p90, 4),
            "delta_12m_spillover": round(delta_12m, 4),
            "prob_18m_macro_outperformance": round(prob_18m, 4),
        }

    def _explain_values(self, vector: tuple[float, ...]) -> dict[str, float]:
        """Return SHAP values for one vector with an independent bounded cache."""
        if self.cache_predictions:
            with self._explanation_cache_lock:
                cached = self._explanation_cache.get(vector)
                if cached is not None:
                    self._explanation_cache.move_to_end(vector)
                    self._increment_metric("shap_cache_hits")
                    return copy.deepcopy(cached)
                values = self._compute_explanation_values(vector)
                self._explanation_cache[vector] = copy.deepcopy(values)
                if len(self._explanation_cache) > PREDICTION_CACHE_MAXSIZE:
                    self._explanation_cache.popitem(last=False)
                return copy.deepcopy(values)
        return self._compute_explanation_values(vector)

    def _compute_explanation_values(self, vector: tuple[float, ...]) -> dict[str, float]:
        self._increment_metric("shap_calls")
        row = pd.Series(dict(zip(FEATURE_COLUMNS, vector)))
        return copy.deepcopy(self.explainer.explain_instance(row))

    def _init_models(self):
        """Initialize or train default synthetic weights for immediate serving."""
        # Train baseline LightGBM model over the support serving actually queries
        self.lgbm_predictor = build_synthetic_baseline()
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

    def _init_from_bundle(self, bundle: Any) -> None:
        """Load a verified synthetic bundle. Does not train or export ONNX."""
        self.lgbm_predictor = LightGBMQuantilePredictor()
        self.lgbm_predictor.models = dict(bundle.quantiles)
        self.explainer.fit_explainer(self.lgbm_predictor.models[0.5])
        self.model_bundle_id = bundle.model_id
        self.model_provenance = bundle.provenance
        providers = [settings.onnx_execution_provider, "CPUExecutionProvider"]
        avail = [p for p in providers if p in ort.get_available_providers()]
        if not avail:
            avail = ["CPUExecutionProvider"]
        self.dcn_session = ort.InferenceSession(str(bundle.dcn_path), providers=avail)
        self.st_gnn_session = ort.InferenceSession(str(bundle.gnn_path), providers=avail)
        logger.info(
            "Inference engine loaded bundle %s (%s) via %s",
            bundle.model_id,
            bundle.provenance,
            avail[0],
        )

    def predict_cell_features(
        self,
        h3_index: str,
        feature_dict: dict[str, Any],
        include_shap: bool = True,
    ) -> dict[str, Any]:
        """Execute multi-horizon inference for a single H3 cell."""
        t0 = time.perf_counter()

        vector = self._feature_key(feature_dict)
        model_values = self._predict_values(vector)

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
            shap_vals = self._explain_values(vector)

        lat, lng = self.indexer.h3_to_latlng(h3_index)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "h3_index": h3_index,
            "resolution": 9,
            "centroid_lat": lat,
            "centroid_lng": lng,
            "lims_score": lims_val,
            **model_values,
            "is_catalyst": is_catalyst,
            "shap_attributions": shap_vals,
            "inference_latency_ms": round(latency_ms, 2),
        }
