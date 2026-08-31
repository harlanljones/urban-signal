"""US-405 — Small Business Credit Access Index (SBCAI) unit tests.

Pure-math coverage of ``compute_sbcai_for_h3``: all/partial/no-coverage
scenarios, weight renormalization, the HMDA denial-term complement inversion,
confidence-as-coverage, quintile banding, and the index-specific caveats.
"""

from typing import Any

import pytest

from src.features.sbcai_index import (
    SBCAI_WEIGHTS,
    compute_sbcai_for_h3,
)

H3 = "892a1072893ffff"


def sbcai(
    sba: float | None = None,
    branch: float | None = None,
    denial: float | None = None,
    snap: float | None = None,
    income: float | None = None,
    **kwargs,
) -> dict[str, Any]:
    return compute_sbcai_for_h3(
        H3,
        sba_loan_per_estab=sba,
        bank_branch_density=branch,
        credit_denial_rate=denial,
        snap_density=snap,
        income=income,
        **kwargs,
    )


def test_all_components_present_using_default_baselines():
    result = sbcai(sba=5.0, branch=4.0, denial=0.3, snap=3.0, income=100_000.0)
    assert result["h3_index"] == H3
    # z's with defaults: sba=5, branch=4, denial complement 0.7 -> z=1.0,
    # snap=3, income=1.2
    # 0.25*5 + 0.20*4 + 0.20*1.0 + 0.15*3 + 0.20*1.2 = 2.94
    assert result["sbcai_score"] == pytest.approx(2.94)
    assert result["sbcai_confidence"] == 5
    assert result["coverage"] == pytest.approx(1.0)
    assert set(result["sources"]) == {"sba", "fdic", "hmda", "snap", "acs"}
    assert result["components"]["credit_denial_rate"]["oriented"] == pytest.approx(0.7)


def test_denial_term_inverts_lower_rate_is_better():
    # Two cells differing only in denial rate: a lower denial rate must score
    # strictly higher, proving the complement orientation.
    low = sbcai(sba=2.0, branch=2.0, denial=0.1, snap=2.0, income=80_000.0)
    high = sbcai(sba=2.0, branch=2.0, denial=0.4, snap=2.0, income=80_000.0)
    assert low["sbcai_score"] > high["sbcai_score"]


def test_missing_hmda_drops_term_and_renormalizes():
    result = sbcai(sba=5.0, branch=4.0, snap=3.0, income=100_000.0)
    # denial (0.20 weight) missing -> renormalize over remaining 0.80
    # 0.25*5/0.8 + 0.20*4/0.8 + 0.15*3/0.8 + 0.20*1.2/0.8 = 3.425
    assert result["sbcai_score"] == pytest.approx(3.425)
    assert result["sbcai_confidence"] == 4
    assert result["coverage"] == pytest.approx(0.8)
    assert "hmda" not in result["sources"]
    assert any("missing inputs lower confidence: credit_denial_rate" in c for c in result["caveats"])
    # The HMDA caveat is only emitted when the denial term is actually present.
    assert not any("HMDA is leaf-only" in c for c in result["caveats"])


def test_no_coverage_returns_zero():
    result = sbcai()
    assert result["sbcai_score"] == 0.0
    assert result["sbcai_confidence"] == 0
    assert result["sources"] == []
    assert any("missing inputs lower confidence" in c for c in result["caveats"])


def test_weights_sum_is_unit():
    assert sum(SBCAI_WEIGHTS.values()) == pytest.approx(1.0)


def test_quintile_banding():
    result = sbcai(
        sba=5.0,
        branch=4.0,
        denial=0.3,
        snap=3.0,
        income=100_000.0,
        band_cutpoints=[0.5, 1.0, 2.0, 3.0],
    )
    # score 2.94 -> band 4 (>=2.0, <3.0)
    assert result["band"] == 4


def test_caveat_surfaces_sba_and_hmda_when_present():
    result = sbcai(sba=2.0, branch=2.0, denial=0.2, snap=2.0, income=70_000.0)
    assert any("gross_approval != disbursed" in c for c in result["caveats"])
    assert any("HMDA is leaf-only" in c for c in result["caveats"])


def test_custom_baselines_and_weights():
    result = sbcai(
        sba=2.0,
        branch=2.0,
        denial=0.2,
        snap=2.0,
        income=70_000.0,
        baselines={
            "sba_loan_per_estab": (0.0, 1.0),
            "bank_branch_density": (0.0, 1.0),
            "credit_denial_rate": (0.5, 0.20),
            "snap_density": (0.0, 1.0),
            "income": (0.0, 1.0),
        },
    )
    # denial complement 0.8 -> z=(0.8-0.5)/0.2=1.5; income 70000 -> z=70000.
    # Assert only the denial orientation, not the huge income term.
    assert result["components"]["credit_denial_rate"]["oriented"] == pytest.approx(0.8)


def test_return_shape_has_required_keys():
    result = sbcai(sba=1.0, branch=1.0, snap=1.0)
    assert set(result) >= {"sbcai_score", "sbcai_confidence", "sources", "components"}
    assert isinstance(result["sbcai_score"], float)
    assert isinstance(result["sbcai_confidence"], int)
