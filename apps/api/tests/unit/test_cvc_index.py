"""US-406 — Commercial Vitality Churn (CVC) composite index unit tests.

Pure-math coverage of ``compute_cvc_for_h3``: corroboration math,
all/partial/single-source scenarios, missing-input abstinence, ZBP
suppression handling, zero values, confidence logic, and the SLA license
namespace normalization that gates cross-registry aggregation.
"""

from typing import Any

import pytest

from src.features.cvc_index import (
    BONUS_FMCSA,
    BONUS_SBA,
    BONUS_SLA_POI_AGREE,
    compute_cvc_for_h3,
    compute_zbp_growth,
    normalize_sla_license_namespace,
)

H3 = "892a1072893ffff"


def cvc(
    sla: float | None,
    poi: float | None,
    zbp: float | None,
    sba: Any = None,
    fmcsa: float | None = None,
    **kwargs,
) -> dict[str, Any]:
    return compute_cvc_for_h3(H3, sla, poi, zbp, sba_approvals=sba, fmcsa_adds=fmcsa, **kwargs)


def test_all_sources_agree_direction_positive():
    result = cvc(sla=5.0, poi=10.0, zbp=0.05, sba={"504": 1, "7a": 1}, fmcsa=2.0)
    assert result["h3_index"] == H3
    assert result["cvc_confidence"] == 3
    assert "sla" in result["sources"]
    assert "poi" in result["sources"]
    assert "zbp" in result["sources"]
    assert "sba" in result["sources"]
    assert "fmcsa" in result["sources"]
    # z_total = 1.0*0.4 + 1.0*0.3 + 0.5*0.3 = 0.85
    # bonuses = 0.3 (sla+poi) + 0.2 (sba) + 0.1 (fmcsa) = 0.6
    assert result["cvc_score"] == pytest.approx(0.85 + BONUS_SLA_POI_AGREE + BONUS_SBA + BONUS_FMCSA)


def test_all_sources_agree_direction_negative():
    result = cvc(sla=-5.0, poi=-10.0, zbp=-0.05)
    assert result["cvc_confidence"] == 3
    # z_total = -1.0*0.4 - 1.0*0.3 - 0.5*0.3 = -0.85; sla+poi agree bonus still +0.3
    assert result["cvc_score"] == pytest.approx(-0.85 + BONUS_SLA_POI_AGREE)


def test_sla_poi_disagree_gets_no_pair_bonus():
    result = cvc(sla=5.0, poi=-10.0, zbp=0.0)
    assert result["bonuses"]["sla_poi_agree"] == 0.0
    # directions +1, -1, 0 -> no consensus -> confidence 1 (at least one source)
    assert result["cvc_confidence"] == 1


def test_partial_agree_two_sources():
    result = cvc(sla=5.0, poi=10.0, zbp=None)
    assert result["cvc_confidence"] == 2
    assert "zbp" not in result["sources"]
    # weights renormalized: sla 0.4/0.7, poi 0.3/0.7
    # z_total = 1.0*(0.4/0.7) + 1.0*(0.3/0.7) = 1.0
    assert result["cvc_score"] == pytest.approx(1.0 + BONUS_SLA_POI_AGREE)


def test_single_source_no_corroboration():
    result = cvc(sla=5.0, poi=None, zbp=None)
    assert result["cvc_confidence"] == 1
    assert result["sources"] == ["sla"]
    # z_total = 1.0 (single source, full weight); no pair bonus, no sba/fmcsa
    assert result["cvc_score"] == pytest.approx(1.0)
    assert any("missing inputs" in c for c in result["caveats"])


def test_no_sources_returns_zero_confidence_and_zero_score():
    result = cvc(None, None, None)
    assert result["cvc_confidence"] == 0
    assert result["cvc_score"] == 0.0
    assert result["sources"] == []


def test_sba_program_breakdown_weights_504_over_7a():
    result = cvc(sla=1.0, poi=1.0, zbp=0.0, sba={"504": 1, "7a": 2})
    sba = result["components"]["sba_approvals"]
    # 1 * 1.0 (504) + 2 * 0.5 (7a) = 2.0
    assert sba["weighted_count"] == pytest.approx(2.0)
    assert sba["fixed_asset"] == 1
    assert sba["working_capital"] == 2
    assert result["bonuses"]["sba"] == BONUS_SBA
    assert any("504 fixed-asset" in c for c in result["caveats"])


def test_sba_plain_count_available():
    result = cvc(sla=1.0, poi=1.0, zbp=0.0, sba=3)
    assert result["bonuses"]["sba"] == BONUS_SBA
    assert result["components"]["sba_approvals"]["available"] is True


def test_sba_zero_is_not_available():
    result = cvc(sla=1.0, poi=1.0, zbp=0.0, sba=0)
    assert result["bonuses"]["sba"] == 0.0
    assert result["components"]["sba_approvals"]["available"] is False
    assert "sba" not in result["sources"]


def test_fmcsa_adds_weighted_low():
    result = cvc(sla=1.0, poi=1.0, zbp=0.0, fmcsa=5.0)
    assert result["bonuses"]["fmcsa"] == BONUS_FMCSA
    assert any("FMCSA trucking" in c for c in result["caveats"])


def test_fmcsa_zero_is_not_available():
    result = cvc(sla=1.0, poi=1.0, zbp=0.0, fmcsa=0.0)
    assert result["bonuses"]["fmcsa"] == 0.0
    assert "fmcsa" not in result["sources"]


def test_poi_lag_caveat_surfaced_when_poi_present():
    result = cvc(sla=1.0, poi=1.0, zbp=0.0)
    assert any("35-day lag" in c for c in result["caveats"])


def test_zbp_suppression_propagates_as_missing():
    result = cvc(sla=1.0, poi=1.0, zbp=None)
    assert result["components"]["zbp_growth"]["available"] is False
    assert result["cvc_confidence"] == 2
    assert any("suppressed or withheld" in c for c in result["caveats"])


def test_zero_values_are_neutral_not_negative():
    result = cvc(sla=0.0, poi=0.0, zbp=0.0)
    assert result["cvc_score"] == 0.0
    assert result["cvc_confidence"] == 1  # sources present but all neutral


def test_custom_baselines_and_weights():
    weights = {"sla_churn_90d": 0.5, "poi_delta_90d": 0.5, "zbp_growth": 0.0}
    baselines = {"sla_churn_90d": (0.0, 10.0), "poi_delta_90d": (0.0, 10.0)}
    result = cvc(sla=10.0, poi=10.0, zbp=0.0, weights=weights, baselines=baselines)
    # z_sla = z_poi = 1.0, renormalized 0.5/1.0 each -> z_total = 1.0
    assert result["cvc_score"] == pytest.approx(1.0 + BONUS_SLA_POI_AGREE)


def test_confidence_counts_only_agreeing_nonzero_sources():
    # Two sources positive, one missing -> confidence 2
    assert cvc(sla=1.0, poi=2.0, zbp=None)["cvc_confidence"] == 2
    # All three positive -> confidence 3
    assert cvc(sla=1.0, poi=2.0, zbp=0.01)["cvc_confidence"] == 3
    # One positive, one negative, one neutral -> no consensus -> 1
    assert cvc(sla=1.0, poi=-2.0, zbp=0.0)["cvc_confidence"] == 1


@pytest.mark.parametrize(
    "value,expected",
    [
        ("tabc:MB", "MB"),
        ("wa_li:12345", "12345"),
        ("sla:RETAIL", "RETAIL"),
        ("MB", "MB"),
        ("", None),
        (None, None),
        ("TABC:MB", "MB"),
    ],
)
def test_normalize_sla_license_namespace(value, expected):
    assert normalize_sla_license_namespace(value) == expected


def test_compute_zbp_growth_with_establishments_and_employment():
    growth, suppressed = compute_zbp_growth(
        current_estab=120.0, prior_estab=100.0, current_emp=240.0, prior_emp=200.0
    )
    assert suppressed == 0
    # estab = (120-100)/(100+1) = 20/101 ≈ 0.1980
    # emp   = (240-200)/(200+1) = 40/201 ≈ 0.1990
    # blended = 0.6*0.1980 + 0.4*0.1990 ≈ 0.1984
    assert growth == pytest.approx(0.1984, rel=1e-3)


def test_compute_zbp_growth_suppression_returns_none_and_counts():
    growth, suppressed = compute_zbp_growth(current_estab="D", prior_estab=100.0)
    assert growth is None
    assert suppressed == 1


def test_compute_zbp_growth_prior_zero_is_flat_or_missing():
    # 0 -> 0 is flat (no growth), not an error
    growth, suppressed = compute_zbp_growth(current_estab=0.0, prior_estab=0.0)
    assert growth == 0.0
    assert suppressed == 0
    # 10 -> 0 is not a valid ratio -> missing
    growth, suppressed = compute_zbp_growth(current_estab=10.0, prior_estab=0.0)
    assert growth is None


def test_zbp_flag_strings_preserve_true_zero():
    growth, suppressed = compute_zbp_growth(current_estab="0", prior_estab="5")
    assert growth is not None
    assert suppressed == 0


def test_return_shape_has_required_keys():
    result = cvc(sla=1.0, poi=1.0, zbp=0.01)
    assert set(result) >= {"cvc_score", "cvc_confidence", "sources"}
    assert isinstance(result["cvc_score"], float)
    assert isinstance(result["cvc_confidence"], int)
    assert isinstance(result["sources"], list)
