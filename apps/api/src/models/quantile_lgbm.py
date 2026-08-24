"""6-Month Horizon: LightGBM Quantile Regressors with Pinball Loss (alpha = 0.1, 0.5, 0.9)."""

from typing import Dict, List, Optional, Tuple
import lightgbm as lgb
import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "capex_density_decayed",
    "permit_count_60d",
    "permit_count_180d",
    "permit_velocity",
    "complaints_neglect_count",
    "complaints_qol_count",
    "shift_ratio_311",
    "sla_active_licenses",
    "sla_new_filings_90d",
    "deed_total_volume_180d",
    "deed_transaction_count_180d",
    "lims_score",
]


class LightGBMQuantilePredictor:
    """LightGBM Quantile Regression model for calibrated uncertainty intervals."""

    def __init__(self, quantiles: Optional[List[float]] = None):
        self.quantiles = quantiles or [0.1, 0.5, 0.9]
        self.models: Dict[float, lgb.Booster] = {}
        self.feature_names = FEATURE_COLUMNS

    def pinball_loss(self, y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
        """Compute pinball / quantile loss for given alpha."""
        residual = y_true - y_pred
        return float(np.mean(np.maximum(alpha * residual, (alpha - 1.0) * residual)))

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
    ) -> Dict[float, float]:
        """Train LightGBM regressors for each quantile alpha."""
        features = [col for col in self.feature_names if col in X_train.columns]
        val_losses = {}

        train_data = lgb.Dataset(X_train[features], label=y_train)
        val_data = lgb.Dataset(X_val[features], label=y_val, reference=train_data) if X_val is not None else None

        for alpha in self.quantiles:
            params = {
                "objective": "quantile",
                "alpha": alpha,
                "metric": "quantile",
                "learning_rate": learning_rate,
                "num_leaves": 31,
                "min_data_in_leaf": 10,
                "verbosity": -1,
                "n_jobs": 4,
            }

            valid_sets = [train_data]
            if val_data:
                valid_sets.append(val_data)

            booster = lgb.train(
                params,
                train_data,
                num_boost_round=n_estimators,
                valid_sets=valid_sets,
            )
            self.models[alpha] = booster

            if X_val is not None and y_val is not None:
                preds = booster.predict(X_val[features])
                loss = self.pinball_loss(y_val.to_numpy(), preds, alpha)
                val_losses[alpha] = loss
            else:
                preds = booster.predict(X_train[features])
                loss = self.pinball_loss(y_train.to_numpy(), preds, alpha)
                val_losses[alpha] = loss

        return val_losses

    def predict(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Predict p10, p50, p90 quantiles for input feature matrix."""
        features = [col for col in self.feature_names if col in X.columns]
        results = {}
        for alpha, booster in self.models.items():
            key = f"p{int(alpha * 100)}"
            results[key] = booster.predict(X[features])
        return results
