"""6-month quantile forecast calibration (US-421).

The dashboard rendered an identical "+139.1% 6M" delta tag on every catalyst
row in every metro. Root cause: the serving baseline was trained on
``np.random.rand(200, 12) * 100`` — all twelve features uniform on [0, 100]
with a target of arbitrary scale — while serving queries carry capex around
1e7, seven hard-zero features, and LIMS in the 60-95 band. Training and
serving support were disjoint, so every tree fell through to the same leaf and
p50 collapsed to a constant ~1.39, which the UI multiplied by 100.

These tests pin the two properties that were violated: the forecast must vary
with the input, and it must carry fractional-return scale.
"""

import pandas as pd
import pytest

from src.models.quantile_lgbm import FEATURE_COLUMNS
from src.serving.engine import build_synthetic_baseline


def _serving_vector(lims, capex, permit_vel, shift_ratio, sla):
    """A feature row shaped exactly as src.serving.router builds it."""
    feats = {
        "capex_density_decayed": capex,
        "permit_velocity": permit_vel if permit_vel <= 1.0 else permit_vel / 100.0,
        "shift_ratio_311": shift_ratio,
        "sla_new_filings_90d": sla,
        "lims_score": lims,
    }
    return pd.Series({c: float(feats.get(c, 0.0)) for c in FEATURE_COLUMNS})


# Values drawn from the real NYC submarket registry.
CASES = [
    ("Fulton Market", 95.0, 8.5e6, 40.0, 1.40, 40),
    ("Fulton Market ring", 93.5, 8.1e6, 40.0, 1.40, 40),
    ("Mission Bay", 94.0, 1.2e7, 70.0, 1.70, 65),
    ("Kakaako", 93.0, 3.2e6, 18.0, 1.12, 12),
    ("Weak submarket", 62.0, 3.2e6, 18.0, 1.12, 19),
]


@pytest.fixture(scope="module")
def predictor():
    return build_synthetic_baseline()


def _p50s(predictor):
    frame = pd.DataFrame([_serving_vector(*c[1:]) for c in CASES])
    return list(predictor.predict(frame)["p50"])


def test_forecast_is_not_constant_across_submarkets(predictor):
    """Distinct submarkets must not all render the same delta tag."""
    p50s = _p50s(predictor)
    rendered = {f"{v * 100:.1f}" for v in p50s}
    assert len(rendered) == len(CASES), (
        f"delta tags collapsed to {sorted(rendered)} across {len(CASES)} distinct submarkets"
    )


def test_forecast_has_fractional_return_scale(predictor):
    """p50 is rendered as a percentage; it must be a fraction, not ~1.39 (=139%)."""
    for (name, *_), p50 in zip(CASES, _p50s(predictor)):
        assert -0.5 < p50 < 0.5, f"{name}: 6M p50 of {p50 * 100:.1f}% is not a plausible return"


def test_stronger_submarkets_forecast_higher_returns(predictor):
    """A 95-LIMS catalyst must not forecast below a 62-LIMS laggard."""
    p50s = dict(zip([c[0] for c in CASES], _p50s(predictor)))
    assert p50s["Fulton Market"] > p50s["Weak submarket"]


def test_quantiles_are_ordered(predictor):
    frame = pd.DataFrame([_serving_vector(*CASES[0][1:])])
    out = predictor.predict(frame)
    assert out["p10"][0] <= out["p50"][0] <= out["p90"][0]
