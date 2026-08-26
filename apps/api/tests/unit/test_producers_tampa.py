"""Unit tests for the Tampa registration and its producer wiring.

Tampa registers ONE feed (PERMITS — City of Tampa "Single Family Permits",
ArcGIS ``MapServer/32``) as a partial city, Austin/LA-style. SLA / 311 / DEEDS
were not verified in the repo research corpus and have no live confirmation, so
they are deliberately absent; ``get_tampa_dataset()`` raises a readable
``KeyError`` for them (mirroring the shared ``get_dataset`` contract).

These tests are SELF-CONTAINED: they import the leaf module's
``TAMPA_DATASETS`` / ``get_tampa_dataset`` directly and never touch
``REGISTRY`` / ``CityId.TAMPA`` (which the spine adds). They therefore pass
WITHOUT the spine being applied. The spine will later copy ``TAMPA_DATASETS``
into ``REGISTRY[CityId.TAMPA]`` and the registration-shape assertions here will
continue to hold.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_tampa import FIELD_MAP
from src.spatial.cities.tampa import (
    TAMPA_CITY_ID,
    TAMPA_DIVISION_BBOXES,
    TAMPA_DIVISIONS,
    TAMPA_METRO_BBOX,
    TAMPA_SUBMARKETS,
    get_tampa_dataset,
    is_in_tampa_metro,
)
from src.spatial.city_registry import FeedType


class TestTampaRegistration:
    def test_city_id_constant(self):
        assert TAMPA_CITY_ID == "tampa"

    def test_center_inside_metro_bbox(self):
        # Downtown Tampa (Channel District) sits well inside the metro bbox.
        assert is_in_tampa_metro(27.944, -82.444)

    def test_is_in_tampa_metro_rejects_missing_coordinates(self):
        assert is_in_tampa_metro(None, None) is False

    def test_is_in_tampa_metro_rejects_other_cities(self):
        assert is_in_tampa_metro(40.7128, -74.0060) is False   # NYC
        assert is_in_tampa_metro(30.2672, -97.7431) is False   # Austin

    def test_live_samples_sit_inside_the_metro_bbox(self):
        # Downtown, Hyde Park, Westshore, Brandon edge — all verified within the
        # declared metro extent.
        assert is_in_tampa_metro(27.948, -82.458)
        assert is_in_tampa_metro(27.935, -82.465)
        assert is_in_tampa_metro(27.955, -82.540)
        assert is_in_tampa_metro(27.940, -82.300)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in TAMPA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= TAMPA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= TAMPA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= TAMPA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= TAMPA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in TAMPA_SUBMARKETS.items():
            bbox = TAMPA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in TAMPA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(TAMPA_SUBMARKETS)

    def test_submarkets_carry_the_tampa_city_id(self):
        assert {m.city_id for m in TAMPA_SUBMARKETS.values()} == {"tampa"}

    def test_division_count_and_exactly_one_claim_invariant(self):
        assert len(TAMPA_DIVISIONS) == 7
        for div in TAMPA_DIVISIONS.values():
            assert div.city_id == "tampa"


class TestFeedRegistration:
    """Tampa is a one-feed partial city (PERMITS only)."""

    def test_exactly_one_feed_is_registered(self):
        from src.spatial.cities.tampa import TAMPA_DATASETS as D

        assert set(D) == {FeedType.PERMITS}

    def test_permits_spec_matches_published_schema(self):
        spec = get_tampa_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.watermark_col == "OPENED_DATE"
        assert spec.producer_key == "permits"
        assert spec.interval_seconds == 300.0
        # OBJECTID must NOT be in the job-id chain.
        assert "OBJECTID" not in spec.id_keys
        assert "B1_PER_ID" in spec.id_keys

    def test_arcgis_extras_pin_oid_field_and_page_cap(self):
        spec = get_tampa_dataset(FeedType.PERMITS)
        assert spec.extra.get("oid_field") == "OBJECTID"
        assert spec.extra.get("max_record_count") == 1000

    def test_field_map_is_embedded_and_matches_leaf_module(self):
        spec = get_tampa_dataset(FeedType.PERMITS)
        assert spec.extra.get("field_map") is FIELD_MAP

    @pytest.mark.parametrize("absent_feed", [FeedType.SLA, FeedType.COMPLAINTS_311, FeedType.DEEDS])
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        """SLA/311/DEEDS deliberately absent — not verified in research, no
        live confirmation. The error must name the city and available feeds."""
        with pytest.raises(KeyError, match=r"'tampa'.*available"):
            get_tampa_dataset(absent_feed)


class TestTampaFieldMap:
    """The leaf field map resolves Tampa's Accela-schema columns directly."""

    def test_job_id_resolves_from_b1_per_id(self):
        row = {"B1_PER_ID": "PER-2026-555", "B1_ALT_ID": "ALT-9"}
        assert first_mapped(row, FIELD_MAP, "job_id") == "PER-2026-555"

    def test_issuance_date_resolves_from_opened_date(self):
        row = {"OPENED_DATE": "2026-07-21T00:00:00.000Z"}
        assert first_mapped(row, FIELD_MAP, "issuance_date") == "2026-07-21T00:00:00.000Z"

    def test_job_type_falls_through_to_second_candidate(self):
        row = {"B1_PER_TYPE": "Building"}
        assert first_mapped(row, FIELD_MAP, "job_type") == "Building"

    def test_falsy_value_falls_through(self):
        row = {"B1_PER_ID": "", "B1_ALT_ID": "ALT-9"}
        assert first_mapped(row, FIELD_MAP, "job_id") == "ALT-9"


class TestTampaRowParsing:
    """Parser smoke tests. Without the spine, ``resolve_field_map('tampa', ...)``
    degrades to ``{}`` (no REGISTRY entry yet), so rows parse through the shared
    chains. The FIXTURE therefore carries both the Tampa field-map keys AND the
    shared-chain keys (permit_number / issuance_date / latitude / longitude) so
    the event is produced today; the field_map becomes authoritative post-spine.
    """

    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    @pytest.fixture
    def permit_row(self):
        # Synthetic Single Family Permits row reflecting the Accela schema
        # (B1_PER_ID family) plus the shared-chain keys the parser needs today.
        return {
            "B1_PER_ID": "PER-2026-555",
            "B1_ALT_ID": "ALT-9",
            "APPLICATION_STATUS": "Issued",
            "OPENED_DATE": "2026-07-21T00:00:00.000Z",
            "B1_WORK_FLOW": "New Construction",
            "permit_number": "TPA-2026-555",
            "issuance_date": "2026-07-21T00:00:00.000Z",
            "latitude": "27.948",
            "longitude": "-82.458",
            "SITE_ADDRESS": "123 Ashley Dr, Tampa, FL",
            "ZIP_CODE": "33602",
            "zipcode": "33602",
        }

    def test_permit_parses_and_ids_from_chain_today(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="tampa")
        assert ev is not None
        # Today (no field_map) the chain resolves job_id from permit_number.
        assert ev.job_id == "TPA-2026-555"

    def test_permit_reads_coordinates(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="tampa")
        assert ev.latitude == pytest.approx(27.948)
        assert ev.longitude == pytest.approx(-82.458)

    def test_permit_issuance_date_parses(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="tampa")
        assert str(ev.issuance_date).startswith("2026-07-21")

    def test_permit_zipcode_maps(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="tampa")
        assert ev.zipcode == "33602"

    def test_permit_live_fixture_is_inside_the_metro_bbox(self, permit_row):
        assert is_in_tampa_metro(float(permit_row["latitude"]), float(permit_row["longitude"]))
