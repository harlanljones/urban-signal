"""Unit tests for the Louisville registration leaf (US-148).

Louisville is a TWO-FEED partial city like Los Angeles and Austin:
COMPLAINTS_311 (Louisville Metro open-data 311 service requests) and SLA
(Kentucky Alcoholic Beverage Control liquor-license feed). DEEDS/PERMITS are
deliberately absent in this phase.

Producer tests confirm the existing ArcGIS-capable 311 and SLA producers carry
the live Louisville field spellings with no new archetype.
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
            "service_request_id": "SR-BAPT-26-130398",
            "latitude": "38.2470",
            "longitude": "-85.7450",
            "service_name": "Large Item Appointment",
            "requested_datetime": "2026-08-22T10:00:00.000",
            "council_district": "4",
            "zip_code": "40202",
        }
        fm = FIELD_MAP["COMPLAINTS_311"]
        assert first_mapped(row, fm, "incident_id") == "SR-BAPT-26-130398"
        assert first_mapped(row, fm, "latitude") == "38.2470"
        assert first_mapped(row, fm, "complaint_type") == "Large Item Appointment"
        assert first_mapped(row, fm, "borough") == "4"
        assert first_mapped(row, fm, "zipcode") == "40202"

    def test_first_mapped_resolves_ky_abc_sla_columns(self):
        row = {
            "LicenseNumber": "056-TL-222451",
            "latitude": "38.2600",
            "longitude": "-85.6500",
            "IssueDate": "2026-07-01",
            "LicenseType": "On-Premises Retail (DR)",
            "Licensee": "The Louisville Bar Co",
            "DBA": "LouBar",
            "PremisesStreet": "123 Bardstown Rd",
            "Status": "Active",
            "County": "Jefferson",
        }
        fm = FIELD_MAP["SLA"]
        assert first_mapped(row, fm, "license_id") == "056-TL-222451"
        assert first_mapped(row, fm, "effective_date") == "2026-07-01"
        assert first_mapped(row, fm, "license_type") == "On-Premises Retail (DR)"
        assert first_mapped(row, fm, "premises_name") == "The Louisville Bar Co"
        assert first_mapped(row, fm, "dba") == "LouBar"
        assert first_mapped(row, fm, "borough") == "Jefferson"

    def test_missing_key_falls_through_to_none(self):
        assert first_mapped({"ticket_id": ""}, FIELD_MAP["COMPLAINTS_311"], "incident_id") is None


class TestLouisvilleProducerCarry:
    """Confirm the existing producers carry Louisville.

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

    def test_live_arcgis_311_shape_uses_louisville_field_map(self, complaints):
        event = complaints.parse_socrata_row(
            {
                "service_request_id": "SR-BAPT-26-130398",
                "requested_datetime": "2026-08-23T04:00:00+00:00",
                "service_name": "Large Item Appointment",
                "status_description": "OPEN",
                "address": "2920 BRINKEY WAY 4",
                "latitude": 38.20796097,
                "longitude": -85.64085684,
                "zip_code": "40218",
                "council_district": "10",
            },
            city_id="louisville",
        )
        assert event is not None
        assert event.incident_id == "SR-BAPT-26-130398"
        assert event.complaint_type == "Large Item Appointment"
        assert event.latitude == pytest.approx(38.20796097)

    def test_live_arcgis_abc_shape_uses_louisville_field_map(self, sla):
        event = sla.parse_socrata_row(
            {
                "LicenseNumber": "056-TL-222451",
                "LicenseType": "Special Temporary License",
                "Licensee": "SIX ROW EVENTS, LLC",
                "DBA": "Bud Tent and Hitching Post",
                "PremisesStreet": "937 Phillips Ln",
                "County": "Jefferson",
                "Status": "Active",
                "IssueDate": "2026-08-22T00:00:00+00:00",
                "ExpiryDate": "2026-08-30T00:00:00+00:00",
                "Latitude": 38.195082,
                "Longitude": -85.7398905,
            },
            city_id="louisville",
        )
        assert event is not None
        assert event.license_id == "056-TL-222451"
        assert event.license_type == "Special Temporary License"
        assert event.latitude == pytest.approx(38.195082)


class TestLouisvilleSupplementalFeeds:
    """Exercise the US-265 ArcGIS supplements through existing producers."""

    @pytest.fixture
    def crime(self):
        with patch("src.producers.crime_incidents_producer.BaseKafkaProducer"):
            from src.producers.crime_incidents_producer import CrimeIncidentsProducer

            return CrimeIncidentsProducer()

    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    @pytest.fixture
    def street_cut(self):
        with patch("src.producers.street_cut_permits_producer.BaseKafkaProducer"):
            from src.producers.street_cut_permits_producer import StreetCutPermitsProducer

            return StreetCutPermitsProducer()

    def test_crime_arcgis_shape_geocodes_and_preserves_louisville(self, crime):
        row = {
            "incident_number": "LMPD-2026-0001",
            "offense_code_name": "BURGLARY",
            "date_occurred": "2026-08-22T04:00:00+00:00",
            "date_reported": "2026-08-23T04:00:00+00:00",
            "block_address": "100 BLOCK S 4TH ST",
        }
        with patch(
            "src.spatial.geocoder.geocode_row_if_declared",
            return_value=(38.2527, -85.7585),
        ):
            event = crime.parse_socrata_row(row, city_id="louisville")

        assert event is not None
        assert event.city_id == "louisville"
        assert event.incident_id == "LMPD-2026-0001"
        assert event.offense_type == "BURGLARY"
        assert event.latitude == pytest.approx(38.2527)
        assert event.longitude == pytest.approx(-85.7585)

    def test_active_permit_arcgis_shape_preserves_louisville(self, permits):
        event = permits.parse_socrata_row(
            {
                "PERMIT_NUMBER": "BP-2026-0042",
                "PROJECT_COSTS": "125000",
                "LATITUDE": 38.2600,
                "LONGITUDE": -85.6500,
                "ISSUE_DATE": "2026-08-21T04:00:00+00:00",
                "PERMIT_TYPE": "NEW CONSTRUCTION",
            },
            city_id="louisville",
        )

        assert event is not None
        assert event.city_id == "louisville"
        assert event.job_id == "BP-2026-0042"
        assert event.latitude == pytest.approx(38.2600)
        assert event.longitude == pytest.approx(-85.6500)
        assert event.estimated_cost == pytest.approx(125000)

class TestLouisvilleSpineRegistration:
    def test_registered_feeds_and_scope(self):
        from src.spatial.city_registry import CityId, FeedType, REGISTRY, normalize_city

        assert normalize_city("louisville ky") is CityId.LOUISVILLE
        reg = REGISTRY[CityId.LOUISVILLE]
        assert set(reg.datasets) == {
            FeedType.COMPLAINTS_311,
            FeedType.SLA,
            FeedType.PERMITS,
            FeedType.CRIME,
            FeedType.STREET_CUT,
        }
        assert reg.datasets[FeedType.COMPLAINTS_311].platform == "arcgis"
        assert reg.datasets[FeedType.SLA].where == "County = 'Jefferson'"

    def test_county_filter_reaches_scheduler_base_where(self):
        from src.producers.scheduler import MunicipalIngestionScheduler

        sched = MunicipalIngestionScheduler()
        lou_jobs = [k for k in sched.job_metadata if "louisville" in k and k.startswith("sla")]
        assert lou_jobs, "expected a louisville SLA job in the scheduler"
        meta = sched.job_metadata[lou_jobs[0]]
        # `where` is the canonical key the scheduler folds into base_where and
        # ANDs with the watermark clause; the old `where_clause` key was dead.
        assert meta["base_where"] == "County = 'Jefferson'"

    def test_unverified_families_remain_absent(self):
        from src.spatial.city_registry import CityId, FeedType, get_dataset

        # Permits/crime/street-cut registered since; deeds remains unverified.
        with pytest.raises(KeyError, match="no.*feed"):
            get_dataset(CityId.LOUISVILLE, FeedType.DEEDS)
