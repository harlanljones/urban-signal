"""Unit tests for the ACS baseline rollup leaf module (US-166)."""

from src.spatial.acs_baseline import (
    ACS_BASELINE_FEATURES,
    BGRow,
    aggregate_blockgroup_to_h3,
    block_fips_to_bg,
    ratio_with_moe,
    sum_with_moe,
    weighted_median_approx,
)


def test_sum_with_moe_quadrature():
    est, moe = sum_with_moe([10.0, 20.0], [2.0, 4.0])
    assert est == 30.0
    # sqrt(2^2 + 4^2) = sqrt(20) ~= 4.4721
    assert abs(moe - 20 ** 0.5) < 1e-9


def test_sum_with_moe_empty():
    est, moe = sum_with_moe([], [])
    assert est == 0.0 and moe == 0.0


def test_ratio_with_moe_zero_denominator():
    ratio, moe = ratio_with_moe(5.0, 1.0, 0.0, 0.0)
    assert ratio == 0.0 and moe == 0.0


def test_ratio_with_moe_known_case():
    # 50 / 200 = 0.25; numerator MOE 5, denominator MOE 10
    ratio, moe = ratio_with_moe(50.0, 5.0, 200.0, 10.0)
    assert abs(ratio - 0.25) < 1e-9
    # SE = sqrt((5/1.645)^2/200^2 + 50^2*(10/1.645)^2/200^4)
    # ~ 0.0076 -> MOE ~ 0.0125
    assert moe > 0.0 and moe < 0.05


def test_weighted_median_approx():
    # weighted mean of 100 (w=1) and 200 (w=3) -> (100+600)/4 = 175
    assert weighted_median_approx([100.0, 200.0], [1.0, 3.0]) == 175.0
    # None entries are skipped
    assert weighted_median_approx([100.0, None], [1.0, 3.0]) == 100.0
    # all None -> 0.0
    assert weighted_median_approx([None], [1.0]) == 0.0


def test_block_fips_to_bg():
    assert block_fips_to_bg("220710001001001") == "220710001001"
    # 15-digit validation
    try:
        block_fips_to_bg("22071")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_aggregate_sum_and_ratio_and_median():
    # Two block groups in the same H3 cell.
    rows = [
        BGRow(
            "220710001001",
            {
                "B01003_001E": (100.0, 10.0),
                "B25003_001E": (40.0, 3.0),   # total units
                "B25003_002E": (24.0, 2.0),   # owner-occupied
                "B19013_001E": (50000.0, 4000.0),  # median income
                "B19013_001M": (40.0, 0.0),        # weight proxy (count-ish)
            },
        ),
        BGRow(
            "220710001002",
            {
                "B01003_001E": (200.0, 15.0),
                "B25003_001E": (60.0, 4.0),
                "B25003_002E": (36.0, 3.0),
                "B19013_001E": (70000.0, 5000.0),
                "B19013_001M": (60.0, 0.0),
            },
        ),
    ]

    def bg_to_h3(_bg: str) -> str:
        return "cellX"

    result = aggregate_blockgroup_to_h3(rows, bg_to_h3)
    assert len(result) == 1
    cell = result[0]
    assert cell.h3_index == "cellX"

    # total_population: sum 100+200 = 300, MOE sqrt(10^2+15^2)=~18.03
    pop_est, pop_moe = cell.features["total_population"]
    assert pop_est == 300.0
    assert abs(pop_moe - (100 + 225) ** 0.5) < 1e-9

    # owner_occupied_share: (24+36)/(40+60) = 0.6
    share_est, share_moe = cell.features["owner_occupied_share"]
    assert abs(share_est - 0.6) < 1e-9
    assert share_moe > 0.0

    # median_household_income: weighted approx (50000*40 + 70000*60)/100 = 62000
    med_est, med_moe = cell.features["median_household_income"]
    assert abs(med_est - 62000.0) < 1e-9
    assert med_moe == 0.0  # documented approximation carries no MOE


def test_aggregate_splits_cells():
    rows = [
        BGRow("220710001001", {"B01003_001E": (10.0, 1.0)}),
        BGRow("220710002001", {"B01003_001E": (20.0, 2.0)}),
    ]

    def bg_to_h3(bg: str) -> str:
        return {"220710001001": "a", "220710002001": "b"}[bg]

    result = aggregate_blockgroup_to_h3(rows, bg_to_h3)
    assert {c.h3_index for c in result} == {"a", "b"}


def test_catalog_is_coherent():
    for name, f in ACS_BASELINE_FEATURES.items():
        if f.agg == "ratio":
            assert f.numerator_var and f.denominator_var
        elif f.agg == "sum":
            assert f.estimate_var and f.moe_var
        elif f.agg == "weighted_median_approx":
            assert f.estimate_var and f.weight_var
