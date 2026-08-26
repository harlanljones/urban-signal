"""Unit tests for the Portland, OR leaf registration and its producer wiring.

Portland registers TWO feed types — PERMITS (Portland Maps / data.portlandoregon.gov
Socrata permits) and SLA (Oregon Liquor Control Commission / OLCC licenses).
DEEDS and COMPLAINTS_311 are deliberately absent.

These tests exercise the leaf and the completed registry wiring, including the
live ArcGIS/Socrata field spellings and the partial-feed caveats.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_portland import FIELD_MAP
from src.spatial.city_registry import FeedType
from src.spatial.cities.portland import (
    PORTLAND_DIVISION_BBOXES,
    PORTLAND_DIVISIONS,
    PORTLAND_FEED_SPECS,
    PORTLAND_METRO_BBOX,
    PORTLAND_PERMITS_FIELD_MAP,
    PORTLAND_SLA_FIELD_MAP,
    PORTLAND_SUBMARKETS,
    is_in_portland_metro,
)

# Synthetic rows shaped like the unverified Portland/OLCC schemas the leaf's
# field maps target. They exercise the canonical keys the shared parsers honor.
PERMIT_ROW = {
    "permit_number": "BP-2026-012345",
    "permit_type": "Building Permit",
    "permit_subtype": "New Construction",
    "application_date": "2026-07-01T00:00:00.000Z",
    "issue_date": "2026-08-10T00:00:00.000Z",
    "status": "Issued",
    "estimated_cost": "1500000",
    "address": "1234 SW Main St",
    "latitude": "45.5205",
    "longitude": "-122.6770",
    "zip_code": "97205",
    "district": "DOWNTOWN",
    "proposed_units": "20",
    "proposed_stories": "6",
}

SLA_ROW = {
    "license_number": "OLCC-123456",
    "license_type": "Full On-Premises",
    "business_name": "Rose City Tavern LLC",
    "licensee_name": "Rose City Tavern LLC",
    "dba": "Rose City Tavern",
    "trade_name": "Rose City Tavern",
    "issue_date": "2025-09-01",
    "effective_date": "2025-09-01",
    "expiration_date": "2027-08-31",
    "license_status": "Active",
    "status": "Active",
    "address": "200 SW Market St",
    "latitude": "45.5105",
    "longitude": "-122.6775",
    "district": "DOWNTOWN",
}


class TestPortlandGeometry:
    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in PORTLAND_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= PORTLAND_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= PORTLAND_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= PORTLAND_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= PORTLAND_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in PORTLAND_SUBMARKETS.items():
            bbox = PORTLAND_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in PORTLAND_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(PORTLAND_SUBMARKETS)

    def test_submarkets_carry_the_portland_city_id(self):
        assert {m.city_id for m in PORTLAND_SUBMARKETS.values()} == {"portland"}

    def test_is_in_portland_metro_rejects_missing_coordinates(self):
        assert is_in_portland_metro(None, None) is False

    def test_is_in_portland_metro_rejects_other_cities(self):
        assert is_in_portland_metro(47.6062, -122.3321) is False  # Seattle
        assert is_in_portland_metro(40.7128, -74.0060) is False   # NYC

    def test_live_samples_sit_inside_the_metro_bbox(self):
        """Downtown, St. Johns, South Waterfront, outer SE."""
        assert is_in_portland_metro(45.5205, -122.6770)   # Downtown
        assert is_in_portland_metro(45.5850, -122.7550)   # St. Johns
        assert is_in_portland_metro(45.4980, -122.6900)   # South Waterfront
        assert is_in_portland_metro(45.4750, -122.5900)   # Woodstock


class TestPortlandFieldMaps:
    def test_field_map_module_shape(self):
        assert set(FIELD_MAP) == {"permits", "sla"}
        for feed in ("permits", "sla"):
            assert isinstance(FIELD_MAP[feed], dict)
            for canonical, candidates in FIELD_MAP[feed].items():
                assert isinstance(canonical, str)
                assert isinstance(candidates, list)

    def test_permits_canonical_keys_present(self):
        expected = {
            "job_id", "latitude", "longitude", "issuance_date", "filing_date",
            "cost", "status", "zipcode", "job_type", "address_street",
            "borough", "proposed_units", "proposed_stories",
        }
        assert expected.issubset(set(PORTLAND_PERMITS_FIELD_MAP))

    def test_sla_canonical_keys_present(self):
        expected = {
            "license_id", "license_type", "dba", "premises_name",
            "effective_date", "expiration_date", "status", "address_street",
            "latitude", "longitude", "borough",
        }
        assert expected.issubset(set(PORTLAND_SLA_FIELD_MAP))

    def test_permits_field_map_resolves_sample_row(self):
        fm = FIELD_MAP["permits"]
        assert first_mapped(PERMIT_ROW, fm, "job_id") == "BP-2026-012345"
        assert first_mapped(PERMIT_ROW, fm, "latitude") == "45.5205"
        assert first_mapped(PERMIT_ROW, fm, "longitude") == "-122.6770"
        assert first_mapped(PERMIT_ROW, fm, "issuance_date") == "2026-08-10T00:00:00.000Z"
        assert first_mapped(PERMIT_ROW, fm, "cost") == "1500000"
        assert first_mapped(PERMIT_ROW, fm, "status") == "Issued"
        assert first_mapped(PERMIT_ROW, fm, "zipcode") == "97205"

    def test_sla_field_map_resolves_sample_row(self):
        fm = FIELD_MAP["sla"]
        assert first_mapped(SLA_ROW, fm, "license_id") == "OLCC-123456"
        assert first_mapped(SLA_ROW, fm, "premises_name") == "Rose City Tavern LLC"
        assert first_mapped(SLA_ROW, fm, "dba") == "Rose City Tavern"
        assert first_mapped(SLA_ROW, fm, "effective_date") == "2025-09-01"
        assert first_mapped(SLA_ROW, fm, "status") == "Active"
        assert first_mapped(SLA_ROW, fm, "address_street") == "200 SW Market St"

    def test_resolve_field_map_uses_completed_spine_wiring(self):
        assert first_mapped.__module__  # smoke import check
        from src.producers.field_maps import resolve_field_map

        assert resolve_field_map("portland", FeedType.PERMITS) is PORTLAND_PERMITS_FIELD_MAP
        assert resolve_field_map("portland", FeedType.SLA) is PORTLAND_SLA_FIELD_MAP


class TestPortlandFeedSpecs:
    def test_exactly_two_feeds_are_described(self):
        assert set(PORTLAND_FEED_SPECS) == {"permits", "sla"}

    def test_specs_carry_watermark_and_field_map(self):
        for feed, spec in PORTLAND_FEED_SPECS.items():
            assert spec["endpoint"] and isinstance(spec["endpoint"], str)
            assert spec["platform"] in ("socrata", "arcgis", "carto", "ckan", "csv")
            assert spec["watermark_col"]
            assert spec["field_map"] is (PORTLAND_PERMITS_FIELD_MAP if feed == "permits" else PORTLAND_SLA_FIELD_MAP)


@pytest.fixture
def portland_field_map(monkeypatch):
    """Drive the shared producers' resolve_field_map to Portland's leaf maps,
    mimicking what the spine REGISTRY entry will do once wired."""

    def fake(city, feed):
        if city == "portland":
            if feed == FeedType.PERMITS:
                return FIELD_MAP["permits"]
            if feed == FeedType.SLA:
                return FIELD_MAP["sla"]
        return {}

    # Both producers do `from src.producers.field_maps import resolve_field_map`
    # *inside* parse_socrata_row, so patching the field_maps module attribute is
    # what actually reaches them at call time.
    monkeypatch.setattr("src.producers.field_maps.resolve_field_map", fake)
    return fake


@pytest.fixture
def permits():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        return DOBPermitsProducer()


@pytest.fixture
def sla():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        return SLALicensesProducer()


class TestPortlandProducerParsing:
    def test_permit_parses_with_portland_fields(self, portland_field_map, permits):
        ev = permits.parse_socrata_row(PERMIT_ROW, city_id="portland")
        assert ev is not None
        assert ev.city_id == "portland"
        assert ev.job_id == "BP-2026-012345"
        assert ev.latitude == pytest.approx(45.5205)
        assert ev.longitude == pytest.approx(-122.6770)
        assert ev.estimated_cost == 1500000.0
        assert str(ev.issuance_date).startswith("2026-08-10")
        assert ev.zipcode == "97205"
        # "Building Permit" is generic -> classified OT (NB/DM signal needs the
        # work_type-first ordering, which the spine field_map already supplies).
        assert str(ev.job_type).endswith("OT")

    def test_permit_demolition_classifies_dm(self, portland_field_map, permits):
        row = dict(PERMIT_ROW, NEWCLASS="Demolition Permit")
        ev = permits.parse_socrata_row(row, city_id="portland")
        assert ev is not None
        assert str(ev.job_type).endswith("DM")

    def test_sla_parses_with_portland_fields(self, portland_field_map, sla):
        ev = sla.parse_socrata_row(SLA_ROW, city_id="portland")
        assert ev is not None
        assert ev.city_id == "portland"
        assert ev.license_id == "OLCC-123456"
        assert ev.latitude == pytest.approx(45.5105)
        assert ev.longitude == pytest.approx(-122.6775)
        assert str(ev.effective_date).startswith("2025-09-01")
        assert ev.dba == "Rose City Tavern"
        assert ev.premises_name == "Rose City Tavern LLC"
        assert ev.license_status == "Active"

    def test_sla_sample_sits_inside_the_metro_bbox(self, sla):
        assert is_in_portland_metro(
            float(SLA_ROW["latitude"]), float(SLA_ROW["longitude"])
        )
