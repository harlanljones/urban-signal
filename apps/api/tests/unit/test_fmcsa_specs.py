"""Unit tests for the US-373 FMCSA national carrier flow."""

from unittest.mock import MagicMock, patch

import pytest

from src.spatial.city_registry import DatasetSpec

from src.producers.fmcsa_specs import (
    FMCSA_AUTHHIST_SPEC,
    FMCSA_CENSUS_SPEC,
    FMCSA_CARRIER_JOINBACK_RESOURCE,
    FMCSA_OOS_SPEC,
)


FROZEN_LEGACY_DATASETS = ("6eyk-hxee", "9mw4-x3tu")

CENSUS_ROW = {
    "dot_number": "1234567",
    "legal_name": "ACME FREIGHT LLC",
    "dba_name": "ACME TRUCKING",
    "status_code": "A",
    "add_date": "20260715",
    "phy_street": "100 MAIN ST",
    "phy_city": "DALLAS",
    "phy_state": "TX",
    "phy_zip": "75201",
    "phy_cnty": "113",
}

AUTHHIST_ROW = {
    "usdot_number": "1234567",
    "op_auth_type": "HOUSETOMOVE",
    "op_auth_status": "I",
    "status_change_date": "20260820",
}

OOS_ROW = {
    "dot_number": "1234567",
    "legal_name": "ACME FREIGHT LLC",
    "status": "I",
    "oos_date": "2026-08-25",
    "rescind_date": "",
}


class TestSpecShape:
    @pytest.mark.parametrize("spec", [FMCSA_CENSUS_SPEC, FMCSA_AUTHHIST_SPEC, FMCSA_OOS_SPEC])
    def test_spec_constructs_as_dataset_spec(self, spec):
        assert DatasetSpec(**spec) is not None

    @pytest.mark.parametrize("spec", [FMCSA_CENSUS_SPEC, FMCSA_AUTHHIST_SPEC, FMCSA_OOS_SPEC])
    def test_never_builds_on_frozen_legacy_datasets(self, spec):
        for frozen in FROZEN_LEGACY_DATASETS:
            assert frozen not in spec["endpoint"]

    def test_joinback_resource_is_the_motus_carrier_file(self):
        assert "inys-ebih" in FMCSA_CARRIER_JOINBACK_RESOURCE

    @pytest.mark.parametrize("spec", [FMCSA_CENSUS_SPEC, FMCSA_AUTHHIST_SPEC, FMCSA_OOS_SPEC])
    def test_census_watermark_is_add_date_and_incremental(self, spec):
        assert spec["watermark_col"]
        assert spec["needs_geocode"] is True


class TestJoinBack:
    def test_authhist_row_acquires_census_address(self):
        from src.producers.carrier_license_producer import CarrierLicenseProducer

        producer = CarrierLicenseProducer()
        producer.load_census_addresses([[CENSUS_ROW]])
        merged = producer._joinback("fmcsa_authhist", dict(AUTHHIST_ROW))
        assert merged["phy_street"] == "100 MAIN ST"
        assert merged["phy_city"] == "DALLAS"

    def test_oos_row_joinback_keeps_source_fields(self):
        from src.producers.carrier_license_producer import CarrierLicenseProducer

        producer = CarrierLicenseProducer()
        producer.load_census_addresses([[CENSUS_ROW]])
        merged = producer._joinback("fmcsa_oos", dict(OOS_ROW))
        assert merged["status"] == "I"
        assert merged["phy_state"] == "TX"

    def test_census_rows_pass_through_unchanged(self):
        from src.producers.carrier_license_producer import CarrierLicenseProducer

        producer = CarrierLicenseProducer()
        assert producer._joinback("fmcsa_census", dict(CENSUS_ROW)) == CENSUS_ROW


class TestParseThroughSlaPath:
    def _producer(self):
        from src.producers.carrier_license_producer import CarrierLicenseProducer

        sla = MagicMock()
        # parse_socrata_row is the real path; patch only resolve_field_map.
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            real = SLALicensesProducer()
        producer = CarrierLicenseProducer(sla=real)
        producer.load_census_addresses([[CENSUS_ROW]])
        return producer

    def test_census_row_parses_to_sla_event(self):
        producer = self._producer()
        counts = producer.run_spec("fmcsa_census", batches=[[CENSUS_ROW]])
        assert counts["events"] == 1
        assert counts["unparsed"] == 0

    def test_authhist_row_parses_after_joinback(self):
        producer = self._producer()
        counts = producer.run_spec("fmcsa_authhist", batches=[[AUTHHIST_ROW]])
        assert counts["events"] == 1

    def test_oos_row_parses_after_joinback(self):
        producer = self._producer()
        counts = producer.run_spec("fmcsa_oos", batches=[[OOS_ROW]])
        assert counts["events"] == 1

    def test_unsited_rows_stream_as_national(self):
        producer = self._producer()
        counts = producer.run_spec("fmcsa_census", batches=[[CENSUS_ROW]])
        # No geocoder injected: the row cannot be sited, so it stays national
        # rather than guessing a coordinate.
        assert counts["national"] == 1
        assert counts["in_metro"] == 0

    def test_geocoded_row_in_metro_takes_metro_city_id(self):
        producer = self._producer()
        producer.geocoder = MagicMock()
        producer.geocoder.geocode.return_value = MagicMock(lat=32.7767, lon=-96.797)
        producer.crosswalk = MagicMock()
        producer.crosswalk.city_for_point.return_value = "dallas"
        counts = producer.run_spec("fmcsa_census", batches=[[CENSUS_ROW]])
        assert counts["in_metro"] == 1
        assert counts["national"] == 0
