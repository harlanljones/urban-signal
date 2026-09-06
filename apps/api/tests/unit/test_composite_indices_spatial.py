"""US-405 — Spatial composite indices module tests.

Tests the interface and convenience helpers in src.spatial.composite_indices:
re-exports of SBCAI, AISI, WCS, and compute_all_composite_indices_for_h3.
"""

import pytest

from src.spatial.composite_indices import (
    AISI_BASELINES,
    AISI_SOURCES,
    AISI_WEIGHTS,
    SBCAI_BASELINES,
    SBCAI_SOURCES,
    SBCAI_WEIGHTS,
    WCS_BASELINES,
    WCS_SOURCES,
    WCS_WEIGHTS,
    compute_aisi_for_h3,
    compute_all_composite_indices_for_h3,
    compute_sbcai_for_h3,
    compute_wcs_for_h3,
)

H3 = "892a1072893ffff"


def test_reexported_functions_work_directly():
    sbcai_res = compute_sbcai_for_h3(H3, sba_loan_per_estab=5.0, income=100_000.0)
    assert sbcai_res["h3_index"] == H3
    assert "sbcai_score" in sbcai_res
    assert sbcai_res["sbcai_confidence"] == 2

    aisi_res = compute_aisi_for_h3(H3, anchor_density=2.0, food_access=3.0)
    assert aisi_res["h3_index"] == H3
    assert "aisi_score" in aisi_res
    assert aisi_res["aisi_confidence"] == 2

    wcs_res = compute_wcs_for_h3(H3, work_from_home=0.2, active_transport=0.1)
    assert wcs_res["h3_index"] == H3
    assert "wcs_score" in wcs_res
    assert wcs_res["wcs_confidence"] == 2


def test_compute_all_composite_indices_for_h3():
    sbcai_in = {
        "sba_loan_per_estab": 5.0,
        "bank_branch_density": 4.0,
        "credit_denial_rate": 0.3,
        "snap_density": 3.0,
        "income": 100_000.0,
    }
    aisi_in = {
        "anchor_density": 2.0,
        "medical_density": 3.0,
        "food_access": 4.0,
        "anchor_churn": 0.5,
        "crime_rate": 0.30,
    }
    wcs_in = {
        "jobs_housing_imbalance": 1.0,
        "work_from_home": 0.2,
        "active_transport": 0.1,
        "ev_readiness": 3.0,
        "commute_time": 2.0,
    }

    all_res = compute_all_composite_indices_for_h3(
        H3,
        sbcai_inputs=sbcai_in,
        aisi_inputs=aisi_in,
        wcs_inputs=wcs_in,
        sbcai_band_cutpoints=[0.5, 1.0, 2.0, 3.0],
    )

    assert all_res["h3_index"] == H3
    assert "sbcai" in all_res
    assert "aisi" in all_res
    assert "wcs" in all_res

    assert all_res["sbcai"]["sbcai_confidence"] == 5
    assert all_res["sbcai"]["band"] == 4
    assert all_res["aisi"]["aisi_confidence"] == 5
    assert all_res["wcs"]["wcs_confidence"] == 5


def test_weights_and_baselines_constants():
    assert sum(SBCAI_WEIGHTS.values()) == pytest.approx(1.0)
    assert sum(AISI_WEIGHTS.values()) == pytest.approx(1.0)
    assert sum(WCS_WEIGHTS.values()) == pytest.approx(1.0)

    assert len(SBCAI_BASELINES) == 5
    assert len(AISI_BASELINES) == 5
    assert len(WCS_BASELINES) == 5

    assert set(SBCAI_SOURCES.values()) == {"sba", "fdic", "hmda", "snap", "acs"}
    assert set(AISI_SOURCES.values()) == {"nces", "nppes", "snap", "anchor_churn", "crime"}
    assert set(WCS_SOURCES.values()) == {"lodes", "acs", "bike_ped", "ev"}
