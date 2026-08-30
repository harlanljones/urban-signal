"""Unit tests for the US-398 FL Statewide Cadastral spec.

The spec dicts must construct as ``DatasetSpec`` with zero massaging, and the
field map must expose the expected canonical keys.  ``FL_COUNTY_CODE_TO_FIPS``
must cover every FL county.
"""

from src.producers import field_maps_fl_cadastral as maps
from src.producers import fl_cadastral_spec as specs
from src.spatial.city_registry import DatasetSpec


class TestSpecShape:
    def test_spec_constructs_as_dataset_spec(self):
        spec = specs.fl_cadastral_spec(42)
        assert DatasetSpec(**spec) is not None

    def test_spec_is_snapshot_with_annual_cadence(self):
        spec = specs.fl_cadastral_spec(1)
        assert spec["ingestion_mode"] == "snapshot"
        assert spec["expected_cadence_days"] == 365
        assert spec["watermark_col"] == ""

    def test_spec_has_arcgis_platform(self):
        spec = specs.fl_cadastral_spec(1)
        assert spec["platform"] == "arcgis"
        assert spec["oid_field"] == "OBJECTID"

    def test_spec_carries_county_where_clause(self):
        spec = specs.fl_cadastral_spec(48)
        assert "CO_NO = 48" in spec["where"]
        assert "ASMNT_YR = 2025" in spec["where"]

    def test_spec_is_permits_topic(self):
        spec = specs.fl_cadastral_spec(1)
        assert spec["producer_key"] == "permits"
        assert spec["topic"] is not None

    def test_different_counties_produce_different_where_clauses(self):
        spec_a = specs.fl_cadastral_spec(1)
        spec_b = specs.fl_cadastral_spec(48)
        assert spec_a["where"] != spec_b["where"]


class TestFieldMap:
    def test_field_map_has_permit_canonical_keys(self):
        expected = {"job_id", "issuance_date", "cost", "bbl", "borough", "status"}
        assert set(maps.FL_CADASTRAL_FIELD_MAP) == expected

    def test_job_id_resolves_via_objectid(self):
        assert "OBJECTID" in maps.FL_CADASTRAL_FIELD_MAP["job_id"]

    def test_bbl_is_parcel_id(self):
        assert "PARCEL_ID" in maps.FL_CADASTRAL_FIELD_MAP["bbl"]

    def test_borough_is_county_code(self):
        assert "CO_NO" in maps.FL_CADASTRAL_FIELD_MAP["borough"]

    def test_cost_is_new_construction_value(self):
        assert "NCONST_VAL" in maps.FL_CADASTRAL_FIELD_MAP["cost"]

    def test_issuance_date_is_year_built(self):
        assert "EFF_YR_BLT" in maps.FL_CADASTRAL_FIELD_MAP["issuance_date"]


class TestCountyFipsMapping:
    def test_all_keys_are_integers(self):
        for k in maps.FL_COUNTY_CODE_TO_FIPS:
            assert isinstance(k, int)

    def test_all_values_are_5_digit_fips(self):
        for v in maps.FL_COUNTY_CODE_TO_FIPS.values():
            assert len(v) == 5
            assert v.isdigit()
            assert v.startswith("12")

    def test_covers_67_fl_counties(self):
        assert len(maps.FL_COUNTY_CODE_TO_FIPS) == 67

    def test_field_maps_cover_the_ticket_registry(self):
        assert set(maps.FIELD_MAPS) == {"fl_cadastral"}

    def test_known_metro_counties_resolve(self):
        # Ocala → Marion (FIPS 12083)
        assert maps.FL_COUNTY_CODE_TO_FIPS[42] == "12083"
        # Orlando → Orange (FIPS 12095)
        assert maps.FL_COUNTY_CODE_TO_FIPS[48] == "12095"
        # Tallahassee → Leon (FIPS 12073)
        assert maps.FL_COUNTY_CODE_TO_FIPS[37] == "12073"