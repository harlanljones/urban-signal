"""Contract tests for Milwaukee's live US-220 CKAN supplementation leaf."""

from src.producers.field_maps_milwaukee_supplemental import FIELD_MAP
from src.spatial.cities.milwaukee import (
    MILWAUKEE_SUPPLEMENTAL_FEED_SPECS,
    MILWAUKEE_SUPPLEMENTAL_NOT_VIABLE,
)


def test_viable_candidates_have_ckan_specs_and_maps():
    assert set(FIELD_MAP) == {
        "fire_calls",
        "ems_calls",
        "vacant_buildings",
        "liquor_licenses",
        "delinquent_tax_accounts",
    }
    for name, spec in MILWAUKEE_SUPPLEMENTAL_FEED_SPECS.items():
        assert spec["endpoint"].startswith("ckan://data.milwaukee.gov/")
        assert spec["platform"] == "ckan"
        assert spec["watermark_col"]
        assert spec["id_keys"]
        assert FIELD_MAP[name]


def test_live_schema_spelling_is_pinned_for_each_candidate():
    assert FIELD_MAP["fire_calls"]["event_id"] == ["IncidentNumber"]
    assert FIELD_MAP["fire_calls"]["latitude"] == ["latitude"]
    assert FIELD_MAP["ems_calls"]["category"] == ["typ_eng"]
    assert FIELD_MAP["vacant_buildings"]["event_id"] == ["PARCELNBR", "_id"]
    assert FIELD_MAP["liquor_licenses"]["license_type"] == ["LIC_TYPE", "License Type Full Name"]
    assert FIELD_MAP["delinquent_tax_accounts"]["amount"] == ["Total Tax Principal"]


def test_non_viable_research_candidates_are_not_silently_registered():
    assert set(MILWAUKEE_SUPPLEMENTAL_NOT_VIABLE) == {"traffic_crashes", "zoning"}
    assert "zero records" in MILWAUKEE_SUPPLEMENTAL_NOT_VIABLE["traffic_crashes"]
    assert "not present" in MILWAUKEE_SUPPLEMENTAL_NOT_VIABLE["zoning"]


def test_address_only_candidates_declare_geocoding_context():
    for name in ("vacant_buildings", "liquor_licenses", "delinquent_tax_accounts"):
        extra = MILWAUKEE_SUPPLEMENTAL_FEED_SPECS[name]["extra"]
        assert extra["needs_geocode"] is True
        assert extra["geocode_context"] == "Milwaukee, WI"
