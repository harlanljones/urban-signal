"""Unit tests for Redfin/Zillow signal reconciliation (US-440)."""

from datetime import date

import pytest

from src.features.market_reconciliation import (
    DEFAULT_RECONCILIATION_WEIGHTS,
    ReconciliationWeights,
    build_hex_monthly_series,
    momentum_diff,
    reconcile_series,
    reconcile_value,
)
from src.spatial.zip_h3_join import ZipHexWeight

JAN = date(2026, 1, 1)
FEB = date(2026, 2, 1)
MAR = date(2026, 3, 1)


class TestReconcileValue:
    def test_default_sale_price_weights(self):
        weights = DEFAULT_RECONCILIATION_WEIGHTS["sale_price"]
        result = reconcile_value(1000000.0, 900000.0, weights)
        # 0.6 * 1,000,000 + 0.4 * 900,000
        assert result == pytest.approx(960000.0)

    def test_rent_is_zillow_only_by_default(self):
        weights = DEFAULT_RECONCILIATION_WEIGHTS["rent"]
        result = reconcile_value(2000.0, 2500.0, weights)
        assert result == pytest.approx(2500.0)

    def test_missing_redfin_falls_back_to_zillow_full_value(self):
        weights = DEFAULT_RECONCILIATION_WEIGHTS["sale_price"]
        result = reconcile_value(None, 900000.0, weights)
        # Must not be discounted to 40% of 900,000 just because only one
        # source reported.
        assert result == pytest.approx(900000.0)

    def test_missing_zillow_falls_back_to_redfin_full_value(self):
        weights = DEFAULT_RECONCILIATION_WEIGHTS["sale_price"]
        result = reconcile_value(1000000.0, None, weights)
        assert result == pytest.approx(1000000.0)

    def test_both_missing_is_none(self):
        result = reconcile_value(None, None, DEFAULT_RECONCILIATION_WEIGHTS["sale_price"])
        assert result is None

    def test_custom_precedence_weights(self):
        custom = ReconciliationWeights(weights={"sale_price": (0.2, 0.8)})
        result = reconcile_value(1000000.0, 900000.0, custom.for_family("sale_price"))
        assert result == pytest.approx(0.2 * 1000000.0 + 0.8 * 900000.0)

    def test_unregistered_family_defaults_to_source_a_only(self):
        weights = ReconciliationWeights().for_family("unknown_family")
        assert weights == (1.0, 0.0)


class TestReconcileSeries:
    def test_blends_overlapping_periods_and_keeps_source_only_periods(self):
        redfin = {"94610": {JAN: 1000000.0, FEB: 1100000.0}}
        zillow = {"94610": {JAN: 900000.0, MAR: 1200000.0}}
        result = reconcile_series(redfin, zillow, family="sale_price")
        assert result["94610"][JAN] == pytest.approx(960000.0)  # blended
        assert result["94610"][FEB] == pytest.approx(1100000.0)  # redfin only
        assert result["94610"][MAR] == pytest.approx(1200000.0)  # zillow only

    def test_zctas_present_in_only_one_source_are_included(self):
        redfin = {"94610": {JAN: 1000000.0}}
        zillow = {"95113": {JAN: 800000.0}}
        result = reconcile_series(redfin, zillow, family="sale_price")
        assert set(result) == {"94610", "95113"}


class TestBuildHexMonthlySeries:
    def test_intensive_series_across_months(self):
        # One hex touched by two ZCTAs at hex_fraction .7/.3.
        weights_by_hex = {
            "hex1": {
                "94601": ZipHexWeight(hex_fraction=0.7, zcta_fraction=0.01),
                "94610": ZipHexWeight(hex_fraction=0.3, zcta_fraction=0.02),
            }
        }
        values = {
            "94601": {JAN: 900000.0, FEB: 920000.0},
            "94610": {JAN: 1300000.0, FEB: 1350000.0},
        }
        series = build_hex_monthly_series(weights_by_hex, values, intensive=True)
        assert set(series["hex1"]) == {JAN, FEB}
        expected_jan = (900000.0 * 0.7 + 1300000.0 * 0.3) / 1.0
        assert series["hex1"][JAN] == pytest.approx(expected_jan)

    def test_extensive_series_sums_allocated_shares(self):
        weights_by_hex = {
            "hex1": {
                "94601": ZipHexWeight(hex_fraction=0.7, zcta_fraction=0.10),
                "94610": ZipHexWeight(hex_fraction=0.3, zcta_fraction=0.05),
            }
        }
        values = {"94601": {JAN: 100.0}, "94610": {JAN: 200.0}}
        series = build_hex_monthly_series(weights_by_hex, values, intensive=False)
        assert series["hex1"][JAN] == pytest.approx(100.0 * 0.10 + 200.0 * 0.05)

    def test_hex_with_no_data_that_month_is_absent(self):
        weights_by_hex = {"hex1": {"94601": ZipHexWeight(hex_fraction=1.0, zcta_fraction=1.0)}}
        values = {"94601": {JAN: 900000.0}}  # no FEB
        series = build_hex_monthly_series(weights_by_hex, values, intensive=True)
        assert JAN in series["hex1"]
        assert FEB not in series["hex1"]

    def test_twelve_months_of_history_round_trips(self):
        months = [date(2025, m if m <= 12 else m - 12, 1) for m in range(3, 15)]
        assert len(months) == 12
        weights_by_hex = {"hex1": {"94601": ZipHexWeight(hex_fraction=1.0, zcta_fraction=1.0)}}
        values = {"94601": {m: 1000000.0 + i * 1000 for i, m in enumerate(months)}}
        series = build_hex_monthly_series(weights_by_hex, values, intensive=True)
        assert len(series["hex1"]) == 12


class TestMomentumDiff:
    def test_first_period_has_no_delta(self):
        series = {JAN: 1000000.0, FEB: 1050000.0, MAR: 1020000.0}
        diffs = momentum_diff(series)
        assert JAN not in diffs
        assert diffs[FEB] == pytest.approx(50000.0)
        assert diffs[MAR] == pytest.approx(-30000.0)

    def test_single_period_yields_no_diffs(self):
        assert momentum_diff({JAN: 1000000.0}) == {}

    def test_empty_series_yields_no_diffs(self):
        assert momentum_diff({}) == {}
