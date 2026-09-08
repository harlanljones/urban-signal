"""Unit tests for the US-377 childcare licensing specs and field maps.

Proves the childcare specs construct as DatasetSpec with zero massaging,
every registry parses through the unmodified SLALicensesProducer row path,
and normalize_status/passes_care_filter helpers work as specified.
"""

from unittest.mock import patch

import pytest

from src.producers import childcare_specs as specs
from src.producers import field_maps_childcare as maps
from src.spatial.city_registry import DatasetSpec

_REGISTRY_KEYS = (
    "tx_hhsc_ccl",
    "ny_ocfs",
    "nyc_dohmh",
    "dc_child_dev",
)

_SOCRATA_REGISTRIES = (
    "tx_hhsc_ccl",
    "ny_ocfs",
    "nyc_dohmh",
)

_NAMESPACES = {
    "tx_hhsc_ccl": "tx_ccl:",
    "ny_ocfs": "ny_ocfs:",
    "nyc_dohmh": "nyc_cc:",
}

_TICKET_ENDPOINTS = {
    "tx_hhsc_ccl": "bc5r-88dy",
    "ny_ocfs": "cb42-qumz",
    "nyc_dohmh": "gy3q-4tzp",
    "dc_child_dev": "MapServer/33",
}


def _build_specs():
    return {
        "tx_hhsc_ccl": specs.tx_hhsc_ccl_spec("TRAVIS"),
        "ny_ocfs": specs.ny_ocfs_spec("BRO"),
        "nyc_dohmh": specs.NYC_DOHMH_SPEC,
        "dc_child_dev": specs.DC_CHILD_DEV_SPEC,
    }


_SPECS = _build_specs()


@pytest.fixture(scope="module")
def sla_producer():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        yield SLALicensesProducer()


def _parse(sla_producer, key, row):
    with patch(
        "src.producers.field_maps.resolve_field_map",
        return_value=maps.FIELD_MAPS[key],
    ):
        return sla_producer.parse_socrata_row(row, city_id=key)


class TestSpecShape:
    @pytest.mark.parametrize("key", _REGISTRY_KEYS)
    def test_spec_constructs_as_dataset_spec(self, key):
        assert DatasetSpec(**_SPECS[key]) is not None

    @pytest.mark.parametrize("key", _REGISTRY_KEYS)
    def test_endpoint_matches_ticket_source(self, key):
        spec = _SPECS[key]
        assert _TICKET_ENDPOINTS[key] in spec["endpoint"], key

    @pytest.mark.parametrize("key", _SOCRATA_REGISTRIES)
    def test_socrata_endpoints_namespace_license_type(self, key):
        spec = _SPECS[key]
        assert f"'{_NAMESPACES[key]}' ||" in spec["endpoint"], key

    def test_field_maps_cover_all_registries(self):
        assert set(maps.FIELD_MAPS) == set(_REGISTRY_KEYS)


class TestParseThroughRealProducer:
    def test_tx_hhsc_ccl_row(self, sla_producer):
        row = {
            "operation_id": "123456",
            "operation_number": "78910",
            "license_type_ns": "tx_ccl:Licensed Child Care Center",
            "type_of_issuance": "Licensed Child Care Center",
            "issuance_date": "2026-01-15T00:00:00.000",
            "administrator_director_name": "JANE DOE",
            "operation_name": "SUNSHINE ACADEMY",
            "address_line": "123 MAIN ST",
            "operation_status": "Y",
            "city": "Austin",
            "location_address_geo": {
                "latitude": "30.2672",
                "longitude": "-97.7431",
            },
        }
        ev = _parse(sla_producer, "tx_hhsc_ccl", row)
        assert ev is not None
        assert ev.license_id == "123456"
        assert ev.license_type == "tx_ccl:Licensed Child Care Center"
        assert ev.dba == "SUNSHINE ACADEMY"
        assert ev.premises_name == "JANE DOE"
        assert ev.address == "123 MAIN ST"
        assert ev.latitude == pytest.approx(30.2672)
        assert ev.longitude == pytest.approx(-97.7431)
        assert ev.borough == "Austin"

    def test_ny_ocfs_row(self, sla_producer):
        row = {
            "facility_id": "890123",
            "license_type_ns": "ny_ocfs:Day Care Center",
            "program_type": "Day Care Center",
            "license_issue_date": "2025-09-01T00:00:00.000",
            "license_expiration_date": "2027-09-01T00:00:00.000",
            "provider_name": "BUFFALO CHILD CARE INC",
            "facility_name": "BUFFALO EARLY LEARNING",
            "street_address_ns": "456 ELM ST",
            "street_name": "ELM ST",
            "facility_status": "License",
            "latitude": "42.8864",
            "longitude": "-78.8784",
            "county": "Erie",
        }
        ev = _parse(sla_producer, "ny_ocfs", row)
        assert ev is not None
        assert ev.license_id == "890123"
        assert ev.license_type == "ny_ocfs:Day Care Center"
        assert ev.dba == "BUFFALO EARLY LEARNING"
        assert ev.premises_name == "BUFFALO CHILD CARE INC"
        assert ev.address == "456 ELM ST"
        assert ev.latitude == pytest.approx(42.8864)
        assert ev.longitude == pytest.approx(-78.8784)
        assert ev.borough == "Erie"

    def test_nyc_dohmh_row(self, sla_producer):
        row = {
            "dcid": "DC12345",
            "permit_number": "PERM-999",
            "license_type_ns": "nyc_cc:Child Care - Center",
            "facility_type": "Child Care - Center",
            "program_name": "MANHATTAN PRESCHOOL",
            "address": "789 BROADWAY",
            "latitude": "40.7128",
            "longitude": "-74.0060",
            "borough": "Manhattan",
        }
        ev = _parse(sla_producer, "nyc_dohmh", row)
        assert ev is not None
        assert ev.license_id == "DC12345"
        assert ev.license_type == "nyc_cc:Child Care - Center"
        assert ev.dba == "MANHATTAN PRESCHOOL"
        assert ev.address == "789 BROADWAY"
        assert ev.latitude == pytest.approx(40.7128)
        assert ev.longitude == pytest.approx(-74.0060)
        assert ev.borough == "Manhattan"

    def test_dc_child_dev_feature(self, sla_producer):
        row = {
            "OBJECTID": 101,
            "LICENSE_NUMBER": "CDC-456",
            "LICENSE_TYPE": "Full License",
            "LICENSE_ISSUE_DATE": "2023-11-15T00:00:00.000",
            "LICENSE_EXPIRATION_DATE": "2024-11-15T00:00:00.000",
            "NAME": "CAPITOL HILL LEARNING CENTER",
            "ADDRESS": "100 EAST CAPITOL ST",
            "LATITUDE": 38.8899,
            "LONGITUDE": -77.0090,
        }
        ev = _parse(sla_producer, "dc_child_dev", row)
        assert ev is not None
        assert ev.license_id == "CDC-456"
        assert ev.license_type == "Full License"
        assert ev.dba == "CAPITOL HILL LEARNING CENTER"
        assert ev.address == "100 EAST CAPITOL ST"
        assert ev.latitude == pytest.approx(38.8899)
        assert ev.longitude == pytest.approx(-77.0090)


class TestHelpers:
    def test_normalize_status_nyc_always_active(self):
        assert maps.normalize_status("nyc_dohmh", None) == "ACTIVE"
        assert maps.normalize_status("nyc_dohmh", "") == "ACTIVE"
        assert maps.normalize_status("nyc_dohmh", "anything") == "ACTIVE"

    def test_normalize_status_tx_temporarily_closed(self):
        assert maps.normalize_status("tx_hhsc_ccl", "Y", temporarily_closed="YES") == "INACTIVE"
        assert maps.normalize_status("tx_hhsc_ccl", "Y", temporarily_closed="NO") == "ACTIVE"
        assert maps.normalize_status("tx_hhsc_ccl", "N", temporarily_closed="NO") == "INACTIVE"

    def test_normalize_status_ny_ocfs(self):
        assert maps.normalize_status("ny_ocfs", "License") == "ACTIVE"
        assert maps.normalize_status("ny_ocfs", "Registration") == "ACTIVE"
        assert maps.normalize_status("ny_ocfs", "Suspended") == "INACTIVE"
        assert maps.normalize_status("ny_ocfs", "Pending Revocation") == "INACTIVE"

    def test_normalize_status_dc(self):
        assert maps.normalize_status("dc_child_dev", "Full License") == "ACTIVE"
        assert maps.normalize_status("dc_child_dev", "Restricted") == "ACTIVE"
        assert maps.normalize_status("dc_child_dev", "Temporary Closure") == "INACTIVE"

    def test_passes_care_filter(self):
        tx_excluded_care = {"care_type": "Residential Treatment Center"}
        tx_excluded_op = {"operation_type": "Child Placing Agency"}
        tx_valid = {"care_type": "Licensed Center", "operation_type": "Child Care Center"}
        ny_row = {"care_type": "Residential Treatment Center"}

        assert maps.passes_care_filter("tx_hhsc_ccl", tx_excluded_care) is False
        assert maps.passes_care_filter("tx_hhsc_ccl", tx_excluded_op) is False
        assert maps.passes_care_filter("tx_hhsc_ccl", tx_valid) is True
        assert maps.passes_care_filter("ny_ocfs", ny_row) is True
