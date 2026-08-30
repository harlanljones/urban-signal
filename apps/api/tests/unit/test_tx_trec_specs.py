"""Unit tests for the US-397 TX TREC/TDLR license registries.

The spec dicts must construct as ``DatasetSpec`` with zero massaging, and
every registry must parse through the unmodified ``SLALicensesProducer`` row
path (``resolve_field_map`` patched to return the registry's map;
``needs_geocode`` is the spine's wiring). County-only sources produce
null-coordinate events (the DC Basic Business Licenses precedent).
"""

from unittest.mock import patch

import pytest

from src.producers import field_maps_tx_trec as maps
from src.producers import tx_trec_specs as specs
from src.spatial.city_registry import DatasetSpec

_REGISTRY_KEYS = (
    "tx_trec_broker",
    "tx_trec_app",
    "tx_tdlr",
)

_NAMESPACES = {
    "tx_trec_broker": "trec_broker:",
    "tx_trec_app": "trec_app:",
    "tx_tdlr": "tdlr:",
}

_TICKET_4X4 = {
    "tx_trec_broker": "s7ft-44qi",
    "tx_trec_app": "bf5n-799f",
    "tx_tdlr": "7358-krk7",
}

_WATERMARK_COLS = {
    "tx_trec_broker": "updated",
    "tx_trec_app": "updated",
    "tx_tdlr": ":updated_at",
}


def _build_specs():
    return {
        "tx_trec_broker": specs.tx_trec_broker_spec("Travis"),
        "tx_trec_app": specs.tx_trec_app_spec("Travis"),
        "tx_tdlr": specs.tx_tdlr_spec("TRAVIS"),
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
    def test_endpoint_carries_the_ticket_dataset_and_namespace(self, key):
        spec = _SPECS[key]
        assert _TICKET_4X4[key] in spec["endpoint"], key
        assert f"'{_NAMESPACES[key]}' ||" in spec["endpoint"], key

    def test_field_maps_cover_exactly_the_ticket_registries(self):
        assert set(maps.FIELD_MAPS) == set(_REGISTRY_KEYS)

    @pytest.mark.parametrize("key", _REGISTRY_KEYS)
    def test_every_map_namespaces_license_type(self, key):
        assert maps.FIELD_MAPS[key]["license_type"] == ["license_type_ns"]

    @pytest.mark.parametrize("key", _REGISTRY_KEYS)
    def test_watermark_column_name(self, key):
        spec = _SPECS[key]
        assert spec["watermark_col"] == _WATERMARK_COLS[key], key


class TestParseThroughRealProducer:
    def test_trec_broker_row(self, sla_producer):
        row = {
            "license_number": "856984-SA",
            "license_type_ns": "trec_broker:Sales Agent",
            "original_license_date": "2026-01-14T00:00:00.000",
            "license_expiration_date": "2028-01-25T00:00:00.000",
            "full_name": "LIZANDRO ROMERO",
            "status": "Active",
            "county": "Travis",
        }
        ev = _parse(sla_producer, "tx_trec_broker", row)
        assert ev is not None
        assert ev.license_id == "856984-SA"
        assert ev.license_type == "trec_broker:Sales Agent"
        assert ev.premises_name == "LIZANDRO ROMERO"
        assert ev.license_status == "Active"
        assert ev.borough == "Travis"
        assert ev.effective_date is not None
        assert ev.expiration_date is not None
        assert ev.latitude is None
        assert ev.longitude is None

    def test_trec_broker_row_without_county_uses_row_value(self, sla_producer):
        row = {
            "license_number": "856984-SA",
            "license_type_ns": "trec_broker:Sales Agent",
            "original_license_date": "2026-01-14T00:00:00.000",
            "license_expiration_date": "2028-01-25T00:00:00.000",
            "full_name": "LIZANDRO ROMERO",
            "status": "Active",
            "county": "Bell",
        }
        ev = _parse(sla_producer, "tx_trec_broker", row)
        assert ev.borough == "Bell"

    def test_trec_app_row(self, sla_producer):
        row = {
            "application_id": "26-020065-SA-APP",
            "license_type_ns": "trec_app:Sales Agent",
            "date_application_received": "2026-08-30T00:00:00.000",
            "date_application_expires": "2027-08-30T00:00:00.000",
            "county": "Travis",
        }
        ev = _parse(sla_producer, "tx_trec_app", row)
        assert ev is not None
        assert ev.license_id == "26-020065-SA-APP"
        assert ev.license_type == "trec_app:Sales Agent"
        assert ev.borough == "Travis"
        assert ev.effective_date is not None
        assert ev.expiration_date is not None
        assert ev.latitude is None
        assert ev.longitude is None

    def test_tdlr_row(self, sla_producer):
        row = {
            "license_number": "76115",
            "license_type_ns": "tdlr:A/C Technician",
            "license_expiration_date_mmddccyy": "10/20/2026",
            "owner_name": "BARKS, DAVID A",
            "business_name": "BARKS, DAVID A",
            "business_county": "YOAKUM",
        }
        ev = _parse(sla_producer, "tx_tdlr", row)
        assert ev is not None
        assert ev.license_id == "76115"
        assert ev.license_type == "tdlr:A/C Technician"
        assert ev.premises_name == "BARKS, DAVID A"
        assert ev.dba == "BARKS, DAVID A"
        assert ev.borough == "YOAKUM"
        assert ev.expiration_date is not None
        assert ev.latitude is None
        assert ev.longitude is None

    def test_tdlr_mmddccyy_parse_via_producer(self, sla_producer):
        row = {
            "license_number": "99999",
            "license_type_ns": "tdlr:Plumber",
            "license_expiration_date_mmddccyy": "12/31/2027",
            "owner_name": "TEST PLUMBER",
            "business_name": "TEST PLUMBER INC",
            "business_county": "TRAVIS",
        }
        ev = _parse(sla_producer, "tx_tdlr", row)
        assert ev is not None
        assert ev.expiration_date is not None
        assert ev.expiration_date.year == 2027
        assert ev.expiration_date.month == 12
        assert ev.expiration_date.day == 31