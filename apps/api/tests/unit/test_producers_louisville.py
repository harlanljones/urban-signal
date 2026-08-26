"""Unit tests for the Louisville registration leaf (US-148).

Louisville is a TWO-FEED partial city like Los Angeles and Austin:
COMPLAINTS_311 (Louisville Metro open-data 311 service requests) and SLA
(Kentucky Alcoholic Beverage Control liquor-license feed). DEEDS/PERMITS are
deliberately absent in this phase.

These tests are deliberately spine-free: they import only the leaf modules
(``src.spatial.cities.louisville`` and ``src.producers.field_maps_louisville``)
plus the shared, non-spine field-map helper. They PASS before the orchestrator
applies the interlock spine (REGISTRY / ALIASES / CityId additions). Once the
spine lands, ``resolve_field_map("louisville", ...)`` will return these maps
instead of degrading to {}.

Producer smoke tests confirm the existing Socrata-backed 311 and SLA producers
already CARRY Louisville with no new archetype — passing city_id explicitly
exercises the shared chains, which is exactly what the registry entry will
select at interlock.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_louisville import FIELD_MAP
from src.spatial.cities.louisville import (
    LOUISVILLE_DIVISION_BBOXES,
    LOUISVILLE_DIVISIONS,
    LOUISVILLE_METRO_BBOX,
    LOUISVILLE_SUBMARKETS,
    is_in_louisville_metro,
)


class TestLouisvilleGeometry:
    def test_metro_bbox_contains_the_city_center(self):
        assert LOUISVILLE_METRO_BBOX["min_lat"] <= 38.2527 <= LOUISVILLE_METRO_BBOX["max_lat"]
        assert LOUISVILLE_METRO_BBOX["min_lng"] <= -85.7585 <= LOUISVILLE_METRO_BBOX["max_lng"]

    def test_is_in_louisville_metro_rejects_missing_coordinates(self):
        assert is_in_louisville_metro(None, None) is False

    def test_is_in_louisville_metro_rejects_other_cities(self):
        assert is_in_louisville_metro(40.7128, -74.0060) is False   # NYC
        assert is_in_louisville_metro(29.9511, -90.0715) is False    # New Orleans

    def test_live_samples_sit_inside_the_metro_bbox(self):
        """Verified neighborhood anchors: downtown, Highlands, St. Matthews, Portland."""
        assert is_in_louisville_metro(38.2570, -85.7580)   # Downtown
        assert is_in_louisville_metro(38.2350, -85.6850)   # Highlands
        assert is_in_louisville_metro(38.2600, -85.6500)   # St. Matthews
        assert is_in_louisville_metro(38.2650, -85.8000)   # Portland

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in LOUISVILLE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= LOUISVILLE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= LOUISVILLE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= LOUISVILLE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= LOUISVILLE_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in LOUISVILLE_SUBMARKETS.items():
            bbox = LOUISVILLE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in LOUISVILLE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(LOUISVILLE_SUBMARKETS)

    def test_submarkets_carry_the_louisville_city_id(self):
        assert {m.city_id for m in LOUISVILLE_SUBMARKETS.values()} == {"louisville"}

    def test_division_count_matches_submarket_partition(self):
        assert len(LOUISVILLE_DIVISIONS) == 6


class TestLouisvilleFieldMaps:
    def test_field_map_covers_both_registered_feeds(self):
        assert set(FIELD_MAP) == {"COMPLAINTS_311", "SLA"}

    @pytest.mark.parametrize("feed", ["COMPLAINTS_311", "SLA"])
    def test_field_map_structure_is_canonical_to_candidate_lists(self, feed):
        for canonical, candidates in FIELD_MAP[feed].items():
            assert isinstance(candidates, list)
            assert all(isinstance(c, str) for c in candidates)

    def test_311_field_map_covers_all_consumed_canonical_keys(self):
        expected = {
            "incident_id", "latitude", "longitude", "complaint_type",
            "created_date", "closed_date", "incident_address", "borough",
            "zipcode", "status",
        }
        assert expected.issubset(set(FIELD_MAP["COMPLAINTS_311"]))

    def test_sla_field_map_covers_all_consumed_canonical_keys(self):
        expected = {
            "license_id", "latitude", "longitude", "effective_date",
            "expiration_date", "license_type", "premises_name", "dba",
            "address_street", "status", "borough",
        }
        assert expected.issubset(set(FIELD_MAP["SLA"]))

    def test_first_mapped_resolves_louisville_311_columns(self):
        row = {
            "ticket_id": "SR-2026-000123",
            "latitude": "38.2470",
            "longitude": "-85.7450",
            "ticket_type": "Pothole",
            "created_at": "2026-08-22T10:00:00.000",
            "neighborhood": "NuLu",
            "zip_code": "40202",
        }
        fm = FIELD_MAP["COMPLAINTS_311"]
        assert first_mapped(row, fm, "incident_id") == "SR-2026-000123"
        assert first_mapped(row, fm, "latitude") == "38.2470"
        assert first_mapped(row, fm, "complaint_type") == "Pothole"
        assert first_mapped(row, fm, "borough") == "NuLu"
        assert first_mapped(row, fm, "zipcode") == "40202"

    def test_first_mapped_resolves_ky_abc_sla_columns(self):
        row = {
            "license_number": "KY-ABC-5541",
            "latitude": "38.2600",
            "longitude": "-85.6500",
            "issue_date": "2026-07-01",
            "license_type": "On-Premises Retail (DR)",
            "premise_name": "The Louisville Bar Co",
            "dba_name": "LouBar",
            "street_address": "123 Bardstown Rd",
            "license_status": "ACTIVE",
            "city": "Louisville",
        }
        fm = FIELD_MAP["SLA"]
        assert first_mapped(row, fm, "license_id") == "KY-ABC-5541"
        assert first_mapped(row, fm, "effective_date") == "2026-07-01"
        assert first_mapped(row, fm, "license_type") == "On-Premises Retail (DR)"
        assert first_mapped(row, fm, "premises_name") == "The Louisville Bar Co"
        assert first_mapped(row, fm, "dba") == "LouBar"
        assert first_mapped(row, fm, "borough") == "Louisville"

    def test_missing_key_falls_through_to_none(self):
        assert first_mapped({"ticket_id": ""}, FIELD_MAP["COMPLAINTS_311"], "incident_id") is None


class TestLouisvilleProducerCarry:
    """Confirm the existing Socrata-backed producers already carry Louisville.

    No new archetype is required: passing city_id explicitly exercises the
    shared chains, exactly what the registry entry selects at interlock.
    """

    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_311_row_carries_through_shared_producer(self, complaints):
        row = {
            "id": "SR-2026-000123",
            "ticket_id": "SR-2026-000123",
            "latitude": "38.2470",
            "longitude": "-85.7450",
            "ticket_type": "Pothole",
            "created_at": "2026-08-22T10:00:00.000",
            "status": "Open",
        }
        event = complaints.parse_socrata_row(row, city_id="louisville")
        assert event is not None
        assert event.city_id == "louisville"
        assert event.latitude == pytest.approx(38.2470)
        assert event.longitude == pytest.approx(-85.7450)

    def test_sla_row_carries_through_shared_producer(self, sla):
        row = {
            "license_id": "KY-ABC-5541",
            "license_number": "KY-ABC-5541",
            "latitude": "38.2600",
            "longitude": "-85.6500",
            "issue_date": "2026-07-01",
            "license_type": "On-Premises Retail (DR)",
            "license_status": "ACTIVE",
        }
        event = sla.parse_socrata_row(row, city_id="louisville")
        assert event is not None
        assert event.city_id == "louisville"
        assert event.latitude == pytest.approx(38.2600)
        assert event.longitude == pytest.approx(-85.6500)
        assert event.license_id == "KY-ABC-5541"
