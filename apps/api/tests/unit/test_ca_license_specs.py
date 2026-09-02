"""Tests for the US-420 California state license spec dicts.

The spec dicts must construct as ``DatasetSpec`` with zero massaging, and
the field maps must resolve through the SLA producer's row parser.
"""



from src.producers import ca_license_specs as specs
from src.producers import field_maps_ca_licenses as maps
from src.spatial.city_registry import DatasetSpec


def test_abc_spec_constructs():
    spec = DatasetSpec(**specs.abc_spec(["ALAMEDA"]))
    assert spec.platform == "csv"
    assert spec.ingestion_mode == "snapshot"
    assert spec.needs_geocode is True
    assert spec.zip_member == "ABC-DailyDataExport.csv"
    assert spec.expected_cadence_days == 7
    assert spec.producer_key == "sla"
    assert "ALAMEDA" in spec.where


def test_cslb_spec_constructs():
    spec = DatasetSpec(**specs.cslb_spec(["ALAMEDA"]))
    assert spec.platform == "csv"
    assert spec.ingestion_mode == "snapshot"
    assert spec.needs_geocode is True
    assert spec.expected_cadence_days == 90
    assert spec.producer_key == "sla"


def test_field_maps_present():
    assert "ca_abc" in maps.FIELD_MAPS
    assert "ca_cslb" in maps.FIELD_MAPS


def test_abc_field_map_has_canonical_keys():
    keys = {"license_id", "license_type", "premises_name", "dba",
            "address_street", "status", "borough", "zipcode"}
    assert keys.issubset(maps.CA_ABC_FIELD_MAP)


def test_cslb_field_map_has_canonical_keys():
    keys = {"license_id", "license_type", "premises_name",
            "address_street", "status", "borough"}
    assert keys.issubset(maps.CA_CSLB_FIELD_MAP)