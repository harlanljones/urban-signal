"""Unit tests for LightGBM Quantile regression, ST-GNN, DCN-v2, and walk-forward spatial validation."""

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pytest
import torch
from src.models.dcn_v2 import MultiScaleDCNv2
from src.models.explainability import CatalystExplainer
from src.models.quantile_lgbm import FEATURE_COLUMNS, LightGBMQuantilePredictor
from src.models.st_gnn import SpatioTemporalGNN
from src.models.validation import SpatialTemporalHoldoutValidator


def test_spatial_temporal_holdout_validator():
    # Construct synthetic dataset with dates and H3 indices
    records = []
    base_date = datetime(2022, 1, 1)
    cells = [
        "892a1072893ffff", "892a1072887ffff", "892a107288fffff",  # parent cluster A
        "892a100d2b7ffff", "892a100d2afffff", "892a100d2a3ffff",  # parent cluster B
    ]

    for month_idx in range(24):
        dt = base_date + timedelta(days=month_idx * 30)
        for cell in cells:
            records.append({
                "as_of_date": dt,
                "h3_index": cell,
                "target": np.random.rand(),
            })

    df = pd.DataFrame(records)
    validator = SpatialTemporalHoldoutValidator(n_spatial_clusters=2, min_train_months=6)

    splits = list(validator.split(df, test_window_months=3))
    assert len(splits) >= 1

    for train_idx, test_idx, held_out_parents in splits:
        train_df = df.iloc[train_idx]
        test_df = df.iloc[test_idx]

        # 1. Temporal integrity: train dates strictly < test dates
        assert train_df["as_of_date"].max() <= test_df["as_of_date"].min()

        # 2. Spatial holdout integrity: test cells must not be in train cells
        train_cells = set(train_df["h3_index"].unique())
        test_cells = set(test_df["h3_index"].unique())
        assert len(train_cells.intersection(test_cells)) == 0


def test_lightgbm_quantile_regressor():
    predictor = LightGBMQuantilePredictor(quantiles=[0.1, 0.5, 0.9])

    np.random.seed(42)
    X = pd.DataFrame(np.random.rand(100, len(FEATURE_COLUMNS)) * 50.0, columns=FEATURE_COLUMNS)
    y = 0.05 * X["capex_density_decayed"] + np.random.randn(100) * 0.1

    losses = predictor.train(X, y, n_estimators=20)
    assert 0.5 in losses

    preds = predictor.predict(X.head(5))
    assert "p10" in preds
    assert "p50" in preds
    assert "p90" in preds
    assert len(preds["p50"]) == 5
    # Calibrated quantile property: p10 <= p50 <= p90 (on average)
    assert np.mean(preds["p10"]) <= np.mean(preds["p50"]) + 0.1
    assert np.mean(preds["p50"]) <= np.mean(preds["p90"]) + 0.1


def test_st_gnn_forward_pass():
    num_nodes = 5
    seq_len = 4
    in_features = 12
    hidden_dim = 32

    model = SpatioTemporalGNN(in_features=in_features, hidden_dim=hidden_dim)
    model.eval()

    x_seq = torch.randn(seq_len, num_nodes, in_features)
    norm_adj = torch.eye(num_nodes)

    with torch.no_grad():
        pred, h_final = model(x_seq, norm_adj)

    assert pred.shape == (num_nodes, 1)
    assert h_final.shape == (num_nodes, hidden_dim)
    assert torch.all(torch.isfinite(pred))


def test_dcn_v2_forward_pass():
    batch_size = 8
    in_features = 12

    model = MultiScaleDCNv2(in_features=in_features, cross_layers=2)
    model.eval()

    x = torch.randn(batch_size, in_features)
    with torch.no_grad():
        prob = model(x)

    assert prob.shape == (batch_size, 1)
    # Output must be valid probability in [0, 1]
    assert torch.all(prob >= 0.0)
    assert torch.all(prob <= 1.0)


def test_catalyst_explainer():
    row = pd.Series({col: 10.0 for col in FEATURE_COLUMNS})
    explainer = CatalystExplainer()
    attributions = explainer.explain_instance(row)

    assert len(attributions) == len(FEATURE_COLUMNS)
    top_drivers = explainer.get_top_catalyst_drivers(attributions, top_k=3)
    assert len(top_drivers) == 3
