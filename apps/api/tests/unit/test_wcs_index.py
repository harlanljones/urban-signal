"""US-405 — Workforce Commute-Shed Score (WCS) unit tests.

Pure-math coverage of ``compute_wcs_for_h3``: all/partial/no-coverage
scenarios, the reciprocal inversions (jobs-housing imbalance, commute time)
including the non-positive guard, confidence-as-coverage, and the
index-specific caveats.
"""

from typing import Any

import pytest

from src.features.wcs_index import WCS_WEIGHTS, compute_wcs_for_h3

H3 = "892a1072893ffff"
UNIT_BASELINES = {
    "jobs_housing_imbalance": (0.0, 1.0),
    "work_from_home": (0.0, 1.0),
    "active_transport": (0.0, 1.0),
    "ev_readiness": (0.0, 1.0),
    "commute_time": (0.0, 1.0),
}


def wcs(
    imbalance: float | None = None,
    wfh: float | None = None,
    active: float | None = None,
    ev: float | None = None,
    commute: float | None = None,
    **kwargs,
) -> dict[str, Any]:
    return compute_wcs_for_h3(
        H3,
        jobs_housing_imbalance=imbalance,
        work_from_home=wfh,
        active_transport=active,
        ev_readiness=ev,
        commute_time=commute,
        **kwargs,
    )


def test_all_components_present():
    result = wcs(imbalance=1.0, wfh=0.2, active=0.1, ev=3.0, commute=2.0, baselines=UNIT_BASELINES)
    # imbalance reciprocal -> 1.0; commute reciprocal -> 0.5
    # 0.30*1.0 + 0.15*0.2 + 0.25*0.1 + 0.15*3.0 + 0.15*0.5 = 0.88
    assert result["wcs_score"] == pytest.approx(0.88)
    assert result["wcs_confidence"] == 5
    assert result["coverage"] == pytest.approx(1.0)
    assert set(result["sources"]) == {"lodes", "acs", "bike_ped", "ev"}
    assert result["components"]["jobs_housing_imbalance"]["oriented"] == pytest.approx(1.0)
    assert result["components"]["commute_time"]["oriented"] == pytest.approx(0.5)


def test_reciprocal_inverts_shorter_commute_is_better():
    # Two cells differing only in commute time: a shorter commute must score
    # strictly higher after the reciprocal transform.
    short = wcs(imbalance=1.0, wfh=0.1, active=0.05, ev=1.0, commute=20.0, baselines=UNIT_BASELINES)
    long = wcs(imbalance=1.0, wfh=0.1, active=0.05, ev=1.0, commute=60.0, baselines=UNIT_BASELINES)
    assert short["wcs_score"] > long["wcs_score"]


def test_nonpositive_reciprocal_is_missing_not_zero():
    # A zero commute time cannot be oriented -> treated as missing, never a 0
    # that would dominate the weighted z-sum.
    result = wcs(imbalance=1.0, wfh=0.1, active=0.05, ev=1.0, commute=0.0, baselines=UNIT_BASELINES)
    assert result["components"]["commute_time"]["available"] is False
    assert result["components"]["commute_time"]["oriented"] is None
    assert result["wcs_confidence"] == 4
    assert any("missing inputs lower confidence: commute_time" in c for c in result["caveats"])


def test_partial_coverage_renormalizes():
    result = wcs(imbalance=1.0, wfh=0.2, active=0.1, baselines=UNIT_BASELINES)
    # ev & commute missing -> renormalize over 0.30+0.15+0.25=0.70
    # 0.30*1/0.7 + 0.15*0.2/0.7 + 0.25*0.1/0.7 = 0.4286+0.0429+0.0357 = 0.5071
    assert result["wcs_score"] == pytest.approx(0.5071, rel=1e-3)
    assert result["wcs_confidence"] == 3
    assert result["coverage"] == pytest.approx(0.6)


def test_no_coverage_returns_zero():
    result = wcs()
    assert result["wcs_score"] == 0.0
    assert result["wcs_confidence"] == 0
    assert result["sources"] == []


def test_weights_sum_is_unit():
    assert sum(WCS_WEIGHTS.values()) == pytest.approx(1.0)


def test_caveats_are_conditional():
    result = wcs(imbalance=1.0, wfh=0.1)
    assert any("LODES is 2023 vintage" in c for c in result["caveats"])
    assert any("jobs-housing balance is misleading" in c for c in result["caveats"])
    # No imbalance -> the res-7 caveat must not fire.
    result = wcs(wfh=0.1, active=0.05)
    assert any("LODES is 2023 vintage" in c for c in result["caveats"])
    assert not any("jobs-housing balance is misleading" in c for c in result["caveats"])


def test_return_shape_has_required_keys():
    result = wcs(imbalance=1.0, wfh=0.1)
    assert set(result) >= {"wcs_score", "wcs_confidence", "sources", "components"}
    assert isinstance(result["wcs_score"], float)
    assert isinstance(result["wcs_confidence"], int)
