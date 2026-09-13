"""Tests for Bay Area permit momentum features (US-441)."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.features.bay_area_permit_momentum import (
    DEFAULT_HALFLIFE_DAYS,
    compute_bay_area_permit_hex_features,
    compute_capex_density_decayed,
    permit_velocity_60_180,
    residential_unit_delta,
)

AS_OF = datetime(2026, 9, 1, tzinfo=UTC)


class TestPermitVelocity6080:
    def test_ratio_formula(self):
        # 60d count 30, 180d count 60 -> baseline 20 -> 30/20 = 1.5
        assert permit_velocity_60_180(30, 60) == pytest.approx(1.5)

    def test_no_180d_history_returns_zero(self):
        assert permit_velocity_60_180(5, 0) == 0.0

    def test_steady_rate_yields_one(self):
        # 60d count == a third of 180d count -> steady rate, ratio 1.0
        assert permit_velocity_60_180(20, 60) == pytest.approx(1.0)


class TestCapexDensityDecayed:
    def test_default_halflife_is_60_days(self):
        assert DEFAULT_HALFLIFE_DAYS == 60.0

    def test_recent_permit_weighted_near_full_value(self):
        permits = [(1_000_000.0, AS_OF - timedelta(days=1))]
        density = compute_capex_density_decayed(permits, cell_area_km2=1.0, as_of_date=AS_OF)
        assert density == pytest.approx(1_000_000.0, rel=0.02)

    def test_halflife_halves_weight_at_exactly_halflife_days(self):
        permits = [(1_000_000.0, AS_OF - timedelta(days=60))]
        density = compute_capex_density_decayed(permits, cell_area_km2=1.0, as_of_date=AS_OF, halflife_days=60.0)
        assert density == pytest.approx(500_000.0, rel=1e-6)

    def test_configurable_halflife_overrides_default(self):
        permits = [(1_000_000.0, AS_OF - timedelta(days=30))]
        density_30_halflife = compute_capex_density_decayed(permits, 1.0, AS_OF, halflife_days=30.0)
        density_60_halflife = compute_capex_density_decayed(permits, 1.0, AS_OF, halflife_days=60.0)
        # Shorter half-life decays faster, so the 30-day-halflife density at
        # 30 days out should be lower (half its original value).
        assert density_30_halflife == pytest.approx(500_000.0, rel=1e-6)
        assert density_60_halflife > density_30_halflife


class TestResidentialUnitDelta:
    def test_net_new_units(self):
        assert residential_unit_delta(proposed_units=8, existing_units=2) == 6

    def test_teardown_rebuild_can_be_zero_or_negative(self):
        assert residential_unit_delta(proposed_units=1, existing_units=1) == 0
        assert residential_unit_delta(proposed_units=0, existing_units=4) == -4

    def test_missing_side_treated_as_zero(self):
        assert residential_unit_delta(proposed_units=3, existing_units=None) == 3
        assert residential_unit_delta(proposed_units=None, existing_units=2) == -2

    def test_both_missing_returns_none(self):
        assert residential_unit_delta(None, None) is None


class TestComputeBayAreaPermitHexFeatures:
    def _permits_df(self):
        return pd.DataFrame(
            [
                {
                    "h3_res9": "cell-a",
                    "estimated_cost": 500_000.0,
                    "issuance_date": AS_OF - timedelta(days=10),
                    "proposed_dwelling_units": 4,
                    "existing_dwelling_units": 1,
                },
                {
                    "h3_res9": "cell-a",
                    "estimated_cost": 200_000.0,
                    "issuance_date": AS_OF - timedelta(days=90),
                    "proposed_dwelling_units": 2,
                    "existing_dwelling_units": 0,
                },
                {
                    "h3_res9": "cell-a",
                    "estimated_cost": 100_000.0,
                    "issuance_date": AS_OF - timedelta(days=200),
                    "proposed_dwelling_units": None,
                    "existing_dwelling_units": None,
                },
                {
                    "h3_res9": "cell-b",
                    "estimated_cost": 9_000_000.0,
                    "issuance_date": AS_OF - timedelta(days=5),
                    "proposed_dwelling_units": 50,
                    "existing_dwelling_units": 0,
                },
            ]
        )

    def test_filters_to_requested_cell_and_window(self):
        feats = compute_bay_area_permit_hex_features(self._permits_df(), "cell-a", as_of_date=AS_OF)
        assert feats["h3_index"] == "cell-a"
        # 60d: only the -10d row; 180d: -10d and -90d rows (the -200d row is excluded).
        assert feats["permit_count_60d"] == 1
        assert feats["permit_count_180d"] == 2

    def test_velocity_matches_formula(self):
        feats = compute_bay_area_permit_hex_features(self._permits_df(), "cell-a", as_of_date=AS_OF)
        expected = permit_velocity_60_180(feats["permit_count_60d"], feats["permit_count_180d"])
        assert feats["permit_velocity_60_180"] == pytest.approx(expected)

    def test_residential_unit_delta_sums_across_cell_rows(self):
        feats = compute_bay_area_permit_hex_features(self._permits_df(), "cell-a", as_of_date=AS_OF)
        # (4 - 1) + (2 - 0) summed across the two rows with unit data = 5
        assert feats["residential_unit_delta"] == 5

    def test_empty_cell_returns_zeroed_features(self):
        feats = compute_bay_area_permit_hex_features(self._permits_df(), "cell-nowhere", as_of_date=AS_OF)
        assert feats["permit_count_60d"] == 0
        assert feats["permit_count_180d"] == 0
        assert feats["permit_velocity_60_180"] == 0.0
        assert feats["capex_density_decayed"] == 0.0
        assert feats["residential_unit_delta"] is None

    def test_configurable_halflife_propagates(self):
        feats = compute_bay_area_permit_hex_features(
            self._permits_df(), "cell-a", as_of_date=AS_OF, halflife_days=30.0
        )
        assert feats["capex_halflife_days"] == 30.0

    def test_other_cells_do_not_leak_into_result(self):
        feats = compute_bay_area_permit_hex_features(self._permits_df(), "cell-b", as_of_date=AS_OF)
        assert feats["residential_unit_delta"] == 50
