"""SHAP (SHapley Additive exPlanations) attribution module for catalyst driver decomposition."""


import lightgbm as lgb
import numpy as np
import pandas as pd
import shap

from src.models.quantile_lgbm import FEATURE_COLUMNS


class CatalystExplainer:
    """Computes SHAP values and identifies primary municipal catalyst drivers for individual parcels."""

    def __init__(self, booster: lgb.Booster | None = None):
        self.booster = booster
        self.explainer = None
        if booster:
            self.explainer = shap.TreeExplainer(booster)

    def fit_explainer(self, booster: lgb.Booster):
        """Fit TreeSHAP explainer on trained LightGBM model."""
        self.booster = booster
        self.explainer = shap.TreeExplainer(booster)

    def explain_instance(self, feature_row: pd.Series) -> dict[str, float]:
        """Compute SHAP attribution values for a single parcel/cell instance."""
        if self.explainer is None:
            # Fallback heuristic attribution based on normalized feature magnitudes
            cols = [col for col in FEATURE_COLUMNS if col in feature_row.index]
            vals = feature_row[cols].to_dict()
            total = sum(abs(float(v)) for v in vals.values()) or 1.0
            return {k: round(float(v) / total * 100.0, 2) for k, v in vals.items()}

        df_row = pd.DataFrame([feature_row[FEATURE_COLUMNS]])
        shap_values = self.explainer.shap_values(df_row)

        if isinstance(shap_values, list):
            # For multi-output / quantiles, take median
            shap_array = shap_values[0][0]
        elif isinstance(shap_values, np.ndarray):
            shap_array = shap_values[0] if shap_values.ndim == 2 else shap_values

        attributions = {}
        for col, val in zip(FEATURE_COLUMNS, shap_array):
            attributions[col] = round(float(val), 4)

        return attributions

    def get_top_catalyst_drivers(
        self,
        attributions: dict[str, float],
        top_k: int = 4,
    ) -> list[dict[str, float]]:
        """Sort and return top positive catalyst drivers."""
        sorted_drivers = sorted(
            attributions.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        return [{k: v} for k, v in sorted_drivers[:top_k]]

    @staticmethod
    def attribution_drift(current: dict[str, float], baseline: dict[str, float]) -> float:
        """Maximum relative TreeSHAP weight change; >25% requires model review."""
        keys = set(current) | set(baseline)
        return max((abs(current.get(k, 0.0) - baseline.get(k, 0.0)) /
                    max(abs(baseline.get(k, 0.0)), 1e-12) for k in keys), default=0.0)

    @classmethod
    def requires_attribution_review(cls, current: dict[str, float], baseline: dict[str, float]) -> bool:
        return cls.attribution_drift(current, baseline) > 0.25
