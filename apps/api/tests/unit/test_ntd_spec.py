"""Unit tests for the US-402 NTD Complete Monthly Ridership SeriesSpec dict.

The spec must construct as ``SeriesSpec`` with zero massaging (``SeriesSpec(**spec)``),
be keyless so it can run unattended, declare a weekly cadence and the correct
SODA endpoint, and expose each of the four NTD measures with its own unit.
"""

import pytest

from src.producers.ntd_spec import (
    NTD_FIELDS,
    NTD_MEASURES,
    NTD_MONTHLY_RIDERSHIP_ENDPOINT,
    NTD_MONTHLY_RIDERSHIP_SPEC,
    PROFILE_SOCRATA,
    ntd_ridership_spec,
)
from src.producers.series_client import SeriesSpec


class TestNtdSpecShape:
    def test_constructs_as_series_spec_with_zero_massaging(self):
        spec = SeriesSpec(**NTD_MONTHLY_RIDERSHIP_SPEC)
        assert spec.series_id == "ntd_upt"
        assert spec.source == "ntd"

    def test_constructs_for_every_measure(self):
        for measure in NTD_MEASURES:
            spec = SeriesSpec(**ntd_ridership_spec(measure))
            assert spec.series_id == f"ntd_{measure}"
            assert spec.value_col == measure
            assert spec.unit == NTD_MEASURES[measure]

    def test_unknown_measure_is_a_readable_error(self):
        with pytest.raises(ValueError, match="unknown NTD measure"):
            ntd_ridership_spec("nope")

    def test_keyless_and_attribution_free(self):
        for measure in NTD_MEASURES:
            spec = SeriesSpec(**ntd_ridership_spec(measure))
            assert spec.auth == "none"
            assert spec.auth_env is None

    def test_points_at_the_live_socrata_endpoint(self):
        assert "8bui-9xvu" in NTD_MONTHLY_RIDERSHIP_ENDPOINT
        assert SeriesSpec(**NTD_MONTHLY_RIDERSHIP_SPEC).dataset_id == NTD_MONTHLY_RIDERSHIP_ENDPOINT

    def test_weekly_cadence(self):
        assert SeriesSpec(**NTD_MONTHLY_RIDERSHIP_SPEC).cadence_days == 7

    def test_monthly_period_keyed_by_date_column(self):
        spec = SeriesSpec(**NTD_MONTHLY_RIDERSHIP_SPEC)
        assert spec.period_type == "month"
        assert spec.period_cols == ["date"]

    def test_geography_is_the_uza_name_column(self):
        spec = SeriesSpec(**NTD_MONTHLY_RIDERSHIP_SPEC)
        assert spec.geography_level == "metro"
        assert spec.geography_col == "uza_name"
        assert spec.metro_col == "uza_name"

    def test_full_ingestion_not_append_only(self):
        # NTD reissues and revises history ("Adjustments and Estimates"); the
        # store must full-diff, never append-only.
        assert SeriesSpec(**NTD_MONTHLY_RIDERSHIP_SPEC).ingestion_mode == "full"

    def test_socrata_profile_declared_but_not_yet_dispatched(self):
        assert PROFILE_SOCRATA == "socrata"
        assert SeriesSpec(**NTD_MONTHLY_RIDERSHIP_SPEC).profile == PROFILE_SOCRATA

    def test_fields_cover_the_documented_columns(self):
        assert set(NTD_FIELDS) >= {
            "ntd_id",
            "agency",
            "uza_name",
            "mode",
            "tos",
            "date",
            "upt",
            "vrm",
            "vrh",
            "voms",
        }

    def test_units_match_the_four_measures(self):
        assert NTD_MEASURES == {
            "upt": "unlinked_passenger_trips",
            "vrm": "vehicle_revenue_miles",
            "vrh": "vehicle_revenue_hours",
            "voms": "vehicles_max_service",
        }


class TestNtdParseCompat:
    """The date column must parse through the existing SeriesClient period parser."""

    def test_iso_date_column_normalizes_to_month_start(self):
        from datetime import date

        from src.producers.series_client import parse_period

        assert parse_period("2026-06-01") == date(2026, 6, 1)

    def test_upt_value_coerces_through_to_float(self):
        from src.producers.series_client import to_float

        assert to_float("9876543") == pytest.approx(9876543.0)
        assert to_float("") is None
