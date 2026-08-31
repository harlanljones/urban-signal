"""US-405 — Anchor Institution Stability Index (AISI) unit tests.

Pure-math coverage of ``compute_aisi_for_h3``: all/partial/no-coverage
scenarios, the anchor-churn and crime-rate complement inversions,
confidence-as-coverage, and the index-specific caveats.
"""

from typing import Any

import pytest

from src.features.aisi_index import AISI_WEIGHTS, compute_aisi_for_h3

H3 = "892a1072893ffff"
UNIT_BASELINES = {
    "anchor_density": (0.0, 1.0),
    "medical_density": (0.0, 1.0),
    "food_access": (0.0, 1.0),
    "anchor_churn": (0.0, 1.0),
    "crime_rate": (0.0, 1.0),
}


def aisi(
    anchor: float | None = None,
    medical: float | None = None,
    food: float | None = None,
    churn: float | None = None,
    crime: float | None = None,
    **kwargs,
) -> dict[str, Any]:
    return compute_aisi_for_h3(
        H3,
        anchor_density=anchor,
        medical_density=medical,
        food_access=food,
        anchor_churn=churn,
        crime_rate=crime,
        **kwargs,
    )


def test_all_components_present():
    result = aisi(anchor=2.0, medical=3.0, food=4.0, churn=0.5, crime=0.30, baselines=UNIT_BASELINES)
    # anchor 2, medical 3, food 4, churn complement 0.5, crime complement 0.70
    # 0.25*2 + 0.20*3 + 0.15*4 + 0.20*0.5 + 0.20*0.70 = 1.94
    assert result["aisi_score"] == pytest.approx(1.94)
    assert result["aisi_confidence"] == 5
    assert result["coverage"] == pytest.approx(1.0)
    assert set(result["sources"]) == {"nces", "nppes", "snap", "anchor_churn", "crime"}
    assert result["components"]["anchor_churn"]["oriented"] == pytest.approx(0.5)
    assert result["components"]["crime_rate"]["oriented"] == pytest.approx(0.70)


def test_churn_and_crime_invert_lower_is_better():
    # Lower churn / lower crime -> higher stability score.
    stable = aisi(anchor=2.0, medical=2.0, food=2.0, churn=0.1, crime=0.05, baselines=UNIT_BASELINES)
    unstable = aisi(anchor=2.0, medical=2.0, food=2.0, churn=0.6, crime=0.40, baselines=UNIT_BASELINES)
    assert stable["aisi_score"] > unstable["aisi_score"]


def test_partial_coverage_renormalizes():
    result = aisi(anchor=2.0, medical=3.0, food=4.0, baselines=UNIT_BASELINES)
    # churn & crime missing -> renormalize over 0.25+0.20+0.15=0.60
    # 0.25*2/0.6 + 0.20*3/0.6 + 0.15*4/0.6 = 0.8333+1.0+1.0 = 2.8333
    assert result["aisi_score"] == pytest.approx(2.8333, rel=1e-3)
    assert result["aisi_confidence"] == 3
    assert result["coverage"] == pytest.approx(0.6)
    assert "snap" in result["sources"]
    assert any("missing inputs lower confidence: anchor_churn, crime_rate" in c for c in result["caveats"])


def test_no_coverage_returns_zero():
    result = aisi()
    assert result["aisi_score"] == 0.0
    assert result["aisi_confidence"] == 0
    assert result["sources"] == []


def test_weights_sum_is_unit():
    assert sum(AISI_WEIGHTS.values()) == pytest.approx(1.0)


def test_caveats_are_conditional():
    # No medical term -> the NPPES caveat must not fire.
    result = aisi(anchor=1.0, food=1.0)
    assert any("NCES school data" in c for c in result["caveats"])
    assert not any("NPPES" in c for c in result["caveats"])
    # With medical present -> NPPES caveat fires.
    result = aisi(anchor=1.0, medical=1.0, food=1.0)
    assert any("NPPES" in c for c in result["caveats"])


def test_return_shape_has_required_keys():
    result = aisi(anchor=1.0, food=1.0)
    assert set(result) >= {"aisi_score", "aisi_confidence", "sources", "components"}
    assert isinstance(result["aisi_score"], float)
    assert isinstance(result["aisi_confidence"], int)
