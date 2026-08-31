"""US-405 — shared composite-index engine unit tests.

Pure-math coverage of ``index_math``: orientation transforms (none /
complement / reciprocal), z-score division-by-zero protection, quintile
banding, and ``compute_weighted_index`` over all/partial/no-coverage scenarios
with weight renormalization and confidence-as-coverage.
"""

import pytest

from src.features.index_math import (
    ORIENT_COMPLEMENT,
    ORIENT_NONE,
    ORIENT_RECIPROCAL,
    compute_weighted_index,
    orient,
    quintile_band,
    z_score,
)


def compute(values, **kwargs):
    weights = kwargs.pop("weights", {"a": 0.5, "b": 0.5})
    baselines = kwargs.pop("baselines", {"a": (0.0, 1.0), "b": (0.0, 1.0)})
    return compute_weighted_index(
        "892a1072893ffff",
        values,
        weights=weights,
        baselines=baselines,
        return_key="idx",
        label="Test Index",
        sources={"a": "alpha", "b": "beta"},
        **kwargs,
    )


def test_orient_none_passthrough():
    assert orient(5.0) == 5.0
    assert orient(5.0, ORIENT_NONE) == 5.0
    assert orient(None) is None


def test_orient_complement():
    assert orient(0.3, ORIENT_COMPLEMENT) == pytest.approx(0.7)
    assert orient(None, ORIENT_COMPLEMENT) is None


def test_orient_reciprocal():
    assert orient(2.0, ORIENT_RECIPROCAL) == pytest.approx(0.5)
    assert orient(None, ORIENT_RECIPROCAL) is None
    # Zero and negative have no meaningful reciprocal -> unorientable.
    assert orient(0.0, ORIENT_RECIPROCAL) is None
    assert orient(-1.0, ORIENT_RECIPROCAL) is None


def test_z_score_protects_against_zero_std():
    assert z_score(3.0, 0.0, 1.0) == pytest.approx(3.0)
    assert z_score(None) == 0.0
    assert z_score(3.0, 0.0, 0.0) == 0.0
    assert z_score(3.0, 1.0, 2.0) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "score,cutpoints,expected",
    [
        (-1.0, [0.0, 0.25, 0.5, 0.75], 1),
        (0.1, [0.0, 0.25, 0.5, 0.75], 2),
        (0.9, [0.0, 0.25, 0.5, 0.75], 5),
        # Equality with a cutpoint rolls to the next band.
        (0.25, [0.0, 0.25, 0.5, 0.75], 3),
    ],
)
def test_quintile_band(score, cutpoints, expected):
    assert quintile_band(score, cutpoints) == expected


def test_all_components_present():
    result = compute({"a": 2.0, "b": 4.0})
    # z_total = 0.5*2 + 0.5*4 = 3.0
    assert result["idx_score"] == pytest.approx(3.0)
    assert result["idx_confidence"] == 2
    assert result["coverage"] == pytest.approx(1.0)
    assert result["sources"] == ["alpha", "beta"]
    assert result["components"]["a"]["oriented"] == pytest.approx(2.0)
    assert result["components"]["b"]["weight"] == pytest.approx(0.5)


def test_partial_coverage_renormalizes_weights():
    result = compute({"a": 2.0, "b": None})
    # b missing -> a renormalized to weight 1.0 -> z_total = 2.0
    assert result["idx_score"] == pytest.approx(2.0)
    assert result["idx_confidence"] == 1
    assert result["coverage"] == pytest.approx(0.5)
    assert result["sources"] == ["alpha"]
    assert any("missing inputs lower confidence: b" in c for c in result["caveats"])


def test_zero_value_counts_as_available():
    result = compute({"a": 0.0, "b": 4.0})
    # a=0 is a legit present value (neutral), not absent.
    assert result["components"]["a"]["available"] is True
    assert result["idx_confidence"] == 2


def test_no_coverage_returns_zero_confidence():
    result = compute({"a": None, "b": None})
    assert result["idx_score"] == 0.0
    assert result["idx_confidence"] == 0
    assert result["coverage"] == pytest.approx(0.0)
    assert result["sources"] == []
    assert any("missing inputs lower confidence: a, b" in c for c in result["caveats"])


def test_complement_orientation():
    result = compute(
        {"a": 0.8, "b": None},
        weights={"a": 1.0, "b": 0.0},
        orientation={"a": ORIENT_COMPLEMENT},
        baselines={"a": (0.0, 1.0), "b": (0.0, 1.0)},
    )
    assert result["components"]["a"]["oriented"] == pytest.approx(0.2)
    assert result["idx_score"] == pytest.approx(0.2)


def test_reciprocal_orientation_guards_nonpositive():
    result = compute(
        {"a": 2.0, "b": None},
        weights={"a": 1.0, "b": 0.0},
        orientation={"a": ORIENT_RECIPROCAL},
        baselines={"a": (0.0, 1.0), "b": (0.0, 1.0)},
    )
    assert result["components"]["a"]["oriented"] == pytest.approx(0.5)
    assert result["idx_score"] == pytest.approx(0.5)


def test_return_shape():
    result = compute({"a": 1.0, "b": 1.0})
    assert set(result) >= {"idx_score", "idx_confidence", "sources", "components"}
    assert isinstance(result["idx_score"], float)
    assert isinstance(result["idx_confidence"], int)
