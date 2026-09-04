"""Unit tests for the US-421 Colorado DORA license registries.

The spec dicts must construct as ``DatasetSpec`` with zero massaging, and
every registry must parse through the unmodified ``SLALicensesProducer`` row
path (``resolve_field_map`` patched to return the registry's map). Both
registries are city-name-only sources (no lat/lng, no street address), so
they declare ``needs_geocode=True`` (the spine's wiring) — this test proves
the parse path, not the geocode call itself. Mirrors
``test_tx_trec_specs.py`` (US-397).
"""

from unittest.mock import patch

import pytest

from src.producers import co_dora_specs as specs
from src.producers import field_maps_co_dora as maps
from src.spatial.city_registry import DatasetSpec

_REGISTRY_KEYS = (
    "co_dora_occupational",
    "co_dora_realestate",
)

_NAMESPACES = {
    "co_dora_occupational": "co_occ:",
    "co_dora_realestate": "co_re:",
}

_TICKET_4X4 = {
    "co_dora_occupational": "7s5z-vewr",
    "co_dora_realestate": "4zse-6bnw",
}

_WATERMARK_COLS = {
    "co_dora_occupational": "licensefirstissuedate",
    "co_dora_realestate": "",
}

_INGESTION_MODES = {
    "co_dora_occupational": "incremental",
    "co_dora_realestate": "snapshot",
}


def _build_specs():
    return {
        "co_dora_occupational": specs.co_dora_occupational_spec("Boulder"),
        "co_dora_realestate": specs.co_dora_realestate_spec("Fort Collins"),
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
    def test_endpoint_carries_the_dataset_and_namespaces(self, key):
        spec = _SPECS[key]
        assert _TICKET_4X4[key] in spec["endpoint"], key
        assert f"'{_NAMESPACES[key]}' ||" in spec["endpoint"], key
        assert "licensee_name_ns" in spec["endpoint"], key

    def test_field_maps_cover_exactly_the_ticket_registries(self):
        assert set(maps.FIELD_MAPS) == set(_REGISTRY_KEYS)

    @pytest.mark.parametrize("key", _REGISTRY_KEYS)
    def test_every_map_namespaces_license_type_and_name(self, key):
        assert maps.FIELD_MAPS[key]["license_type"] == ["license_type_ns"]
        assert maps.FIELD_MAPS[key]["premises_name"] == ["licensee_name_ns"]

    @pytest.mark.parametrize("key", _REGISTRY_KEYS)
    def test_watermark_column_name(self, key):
        assert _SPECS[key]["watermark_col"] == _WATERMARK_COLS[key], key

    @pytest.mark.parametrize("key", _REGISTRY_KEYS)
    def test_ingestion_mode(self, key):
        assert _SPECS[key]["ingestion_mode"] == _INGESTION_MODES[key], key

    @pytest.mark.parametrize("key", _REGISTRY_KEYS)
    def test_needs_geocode_with_co_context(self, key):
        spec = _SPECS[key]
        assert spec["needs_geocode"] is True, key
        assert spec["geocode_context"] == "CO", key

    @pytest.mark.parametrize("key", _REGISTRY_KEYS)
    def test_where_clause_slices_on_city(self, key):
        spec = _SPECS[key]
        assert spec["where"].startswith("city = '"), key


class TestParseThroughRealProducer:
    def test_occupational_individual_row(self, sla_producer):
        row = {
            "lastname": "Atkinson",
            "firstname": "Erin",
            "city": "Boulder",
            "mailzipcode": "80304",
            "license_type_ns": "co_occ:APN",
            "licensenumber": "991717",
            "licensefirstissuedate": "2015-04-07T00:00:00.000",
            "licenseexpirationdate": "2027-09-30T00:00:00.000",
            "licensestatusdescription": "Active",
            "licensee_name_ns": "Erin Atkinson",
        }
        ev = _parse(sla_producer, "co_dora_occupational", row)
        assert ev is not None
        assert ev.license_id == "991717"
        assert ev.license_type == "co_occ:APN"
        assert ev.premises_name == "Erin Atkinson"
        assert ev.license_status == "Active"
        assert ev.borough == "Boulder"
        assert ev.effective_date is not None
        assert ev.expiration_date is not None
        assert ev.latitude is None
        assert ev.longitude is None

    def test_occupational_entity_row(self, sla_producer):
        row = {
            "entityname": "1013 Barbershop LLC",
            "city": "Fort Collins",
            "mailzipcode": "80525",
            "license_type_ns": "co_occ:REG",
            "licensenumber": "2000033895",
            "licensefirstissuedate": "2021-06-01T00:00:00.000",
            "licensestatusdescription": "Active",
            "licensee_name_ns": "1013 Barbershop LLC",
        }
        ev = _parse(sla_producer, "co_dora_occupational", row)
        assert ev is not None
        assert ev.premises_name == "1013 Barbershop LLC"
        assert ev.borough == "Fort Collins"

    def test_realestate_row(self, sla_producer):
        row = {
            "lastname": "Markus",
            "firstname": "Jennifer",
            "city": "Boulder",
            "zipcode": "80301",
            "license_type_ns": "co_re:Associate Level Real Estate Broker",
            "licensenumber": "100095811",
            "licensefirstissuedate": "11/10/2021",
            "licenseexpirationdate": "12/31/2028",
            "licensestatus": "Active",
            "licensee_name_ns": "Jennifer Markus",
        }
        ev = _parse(sla_producer, "co_dora_realestate", row)
        assert ev is not None
        assert ev.license_id == "100095811"
        assert ev.license_type == "co_re:Associate Level Real Estate Broker"
        assert ev.premises_name == "Jennifer Markus"
        assert ev.license_status == "Active"
        assert ev.borough == "Boulder"
        assert ev.effective_date is not None
        assert ev.effective_date.year == 2021
        assert ev.effective_date.month == 11
        assert ev.expiration_date is not None
        assert ev.latitude is None
        assert ev.longitude is None
