"""Regression coverage for per-engine prediction and SHAP vector reuse."""

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, RLock

import numpy as np
import pytest

from src.models.quantile_lgbm import FEATURE_COLUMNS
from src.serving.engine import MultiHorizonInferenceEngine


class _Predictor:
    def __init__(self):
        self.calls = 0

    def predict(self, frame):
        self.calls += 1
        value = float(frame.iloc[0]["lims_score"])
        return {
            "p10": [value / 1000],
            "p50": [value / 100],
            "p90": [value / 10],
        }


class _Session:
    def __init__(self, value):
        self.calls = 0
        self.value = value

    def run(self, _outputs, _inputs):
        self.calls += 1
        return [np.array([[self.value]], dtype=np.float32)]


class _Explainer:
    def __init__(self):
        self.calls = 0

    def explain_instance(self, row):
        self.calls += 1
        return {"lims_score": float(row["lims_score"])}


class _Lims:
    def __init__(self):
        self.calls = 0

    def compute_scaled_lims(self, **kwargs):
        self.calls += 1
        return float(kwargs["shift_ratio_311"])


class _Metrics:
    def __init__(self):
        self.counts = {}

    def increment(self, name, count=1):
        self.counts[name] = self.counts.get(name, 0) + count


def _engine(cache_predictions=True):
    engine = MultiHorizonInferenceEngine.__new__(MultiHorizonInferenceEngine)
    engine.cache_predictions = cache_predictions
    engine.metrics = _Metrics()
    engine._prediction_cache = OrderedDict()
    engine._explanation_cache = OrderedDict()
    engine._prediction_cache_lock = RLock()
    engine._explanation_cache_lock = RLock()
    engine.lgbm_predictor = _Predictor()
    engine.dcn_session = _Session(0.42)
    engine.st_gnn_session = _Session(0.24)
    engine.explainer = _Explainer()
    engine.lims_calc = _Lims()
    engine.indexer = type(
        "Indexer", (), {"h3_to_latlng": lambda _self, h3: (float(ord(h3[-1])), 1.5)}
    )()
    return engine


def _features(**overrides):
    values = {column: 0.0 for column in FEATURE_COLUMNS}
    values.update({"lims_score": 80.0, "shift_ratio_311": 1.0})
    values.update(overrides)
    return values


def _model_calls(engine):
    return engine.lgbm_predictor.calls + engine.dcn_session.calls + engine.st_gnn_session.calls


def test_identical_vector_reuses_model_and_shap_across_cells_but_assembles_cell_fields():
    engine = _engine()
    features = _features()

    first = engine.predict_cell_features("cell-a", features)
    second = engine.predict_cell_features("cell-b", features)

    assert _model_calls(engine) == 3
    assert engine.explainer.calls == 1
    assert (first["h3_index"], second["h3_index"]) == ("cell-a", "cell-b")
    assert first["centroid_lat"] != second["centroid_lat"]
    assert first["inference_latency_ms"] >= 0
    assert second["inference_latency_ms"] >= 0


def test_changed_capex_and_lims_vector_on_same_cell_executes_model_again():
    engine = _engine()
    first = engine.predict_cell_features("cell-a", _features(lims_score=80.0, capex_density_decayed=1_000_000))
    second = engine.predict_cell_features("cell-a", _features(lims_score=81.0, capex_density_decayed=2_000_000))

    assert _model_calls(engine) == 6
    assert first["delta_6m_p50"] != second["delta_6m_p50"]
    assert first["lims_score"] == 80.0
    assert second["lims_score"] == 81.0


def test_fallback_lims_is_assembled_per_request_even_when_model_vector_hits_cache():
    engine = _engine()
    features = _features(lims_score=0.0, shift_ratio_311=1.0)

    first = engine.predict_cell_features("cell-a", features, include_shap=False)
    second = engine.predict_cell_features("cell-b", features, include_shap=False)

    assert engine.lims_calc.calls == 2
    assert first["lims_score"] == second["lims_score"] == 1.0
    assert _model_calls(engine) == 3


def test_missing_features_and_explicit_zero_defaults_share_vector_key():
    engine = _engine()
    missing = {"lims_score": 80.0, "shift_ratio_311": 1.0}
    explicit = _features()

    engine.predict_cell_features("cell-a", missing, include_shap=False)
    engine.predict_cell_features("cell-b", explicit, include_shap=False)

    assert _model_calls(engine) == 3


def test_shap_can_be_added_after_prediction_and_returned_dicts_are_independent():
    engine = _engine()
    no_shap = engine.predict_cell_features("cell-a", _features(), include_shap=False)
    with_shap = engine.predict_cell_features("cell-a", _features(), include_shap=True)

    assert _model_calls(engine) == 3
    assert engine.explainer.calls == 1
    assert no_shap["shap_attributions"] is None
    assert with_shap["shap_attributions"] == {"lims_score": 80.0}
    with_shap["shap_attributions"]["lims_score"] = 999
    again = engine.predict_cell_features("cell-b", _features(), include_shap=True)
    assert again["shap_attributions"] == {"lims_score": 80.0}


def test_disabled_cache_recomputes_and_cache_can_be_cleared_or_enabled():
    engine = _engine(cache_predictions=False)
    engine.predict_cell_features("cell-a", _features(), include_shap=False)
    engine.predict_cell_features("cell-b", _features(), include_shap=False)
    assert _model_calls(engine) == 6

    engine.cache_predictions = True
    engine.predict_cell_features("cell-a", _features(), include_shap=False)
    engine.predict_cell_features("cell-b", _features(), include_shap=False)
    assert _model_calls(engine) == 9
    engine.clear_prediction_caches()
    engine.predict_cell_features("cell-c", _features(), include_shap=False)
    assert _model_calls(engine) == 12


def test_concurrent_same_vector_mixed_shap_flags_compute_each_layer_once():
    engine = _engine()
    barrier = Barrier(16)

    def predict(i):
        barrier.wait()
        return engine.predict_cell_features(f"cell-{i}", _features(), include_shap=i % 2 == 0)

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(predict, range(16)))

    assert _model_calls(engine) == 3
    assert engine.explainer.calls == 1
    assert all((result["shap_attributions"] is not None) == (i % 2 == 0) for i, result in enumerate(results))


def test_prediction_lru_is_bounded_at_16384_entries():
    engine = _engine()
    for value in range(16_385):
        engine._predict_values(tuple([float(value)] + [0.0] * (len(FEATURE_COLUMNS) - 1)))

    assert len(engine._prediction_cache) == 16_384


def test_shap_lru_is_bounded_at_16384_entries():
    engine = _engine()
    for value in range(16_385):
        engine._explain_values(tuple([float(value)] + [0.0] * (len(FEATURE_COLUMNS) - 1)))

    assert len(engine._explanation_cache) == 16_384


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_feature_inputs_are_rejected(bad_value):
    engine = _engine()
    with pytest.raises(ValueError, match="finite"):
        engine.predict_cell_features("cell-a", _features(lims_score=bad_value))


def test_cached_and_uncached_engine_outputs_match_except_latency():
    cached = _engine(cache_predictions=True)
    uncached = _engine(cache_predictions=False)
    inputs = [("cell-a", _features()), ("cell-b", _features())]

    cached_results = [cached.predict_cell_features(h3, features) for h3, features in inputs]
    uncached_results = [uncached.predict_cell_features(h3, features) for h3, features in inputs]

    for cached_result, uncached_result in zip(cached_results, uncached_results):
        cached_result.pop("inference_latency_ms")
        uncached_result.pop("inference_latency_ms")
        assert cached_result == uncached_result


def test_metrics_count_model_work_and_each_cache_hit_at_boundary():
    engine = _engine()
    engine.predict_cell_features("cell-a", _features())
    engine.predict_cell_features("cell-b", _features())

    assert engine.metrics.counts == {
        "inference_calls": 1,
        "shap_calls": 1,
        "prediction_cache_hits": 1,
        "shap_cache_hits": 1,
    }
