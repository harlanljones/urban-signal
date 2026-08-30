"""Unit tests for the US-404 MARTA station entrances/exits DatasetSpec dict.

The spec must construct as ``DatasetSpec`` with zero massaging
(``DatasetSpec(**spec)``), be keyless/snapshot-mode (no watermark), declare a
weekly cadence, and point at the live Socrata endpoint.
"""

from src.producers.marta_spec import (
    MARTA_ENTRANCES_EXITS_ENDPOINT,
    MARTA_ENTRANCES_EXITS_SPEC,
)
from src.spatial.city_registry import DatasetSpec


class TestMartaSpecShape:
    def test_constructs_as_dataset_spec_with_zero_massaging(self):
        spec = DatasetSpec(**MARTA_ENTRANCES_EXITS_SPEC)
        assert spec.endpoint == MARTA_ENTRANCES_EXITS_ENDPOINT

    def test_points_at_the_live_socrata_endpoint(self):
        assert "nwqk-3q5y" in MARTA_ENTRANCES_EXITS_ENDPOINT

    def test_keyless_snapshot_mode_with_no_watermark(self):
        spec = DatasetSpec(**MARTA_ENTRANCES_EXITS_SPEC)
        assert spec.platform == "socrata"
        assert spec.watermark_col == ""
        assert spec.ingestion_mode == "snapshot"

    def test_weekly_cadence(self):
        spec = DatasetSpec(**MARTA_ENTRANCES_EXITS_SPEC)
        assert spec.interval_seconds == 604800
        assert spec.expected_cadence_days == 7

    def test_producer_key_names_the_feed(self):
        assert DatasetSpec(**MARTA_ENTRANCES_EXITS_SPEC).producer_key == "marta_entrances_exits"

    def test_sited_rows_not_geocoded(self):
        spec = DatasetSpec(**MARTA_ENTRANCES_EXITS_SPEC)
        assert spec.needs_geocode is False
        assert spec.non_spatial is False

    def test_stable_row_id_for_churn_diff(self):
        assert ":id" in DatasetSpec(**MARTA_ENTRANCES_EXITS_SPEC).id_keys
