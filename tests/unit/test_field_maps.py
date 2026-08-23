"""Unit tests for the per-city field-mapping table used by the shared parsers.

A city registers `DatasetSpec.extra["field_map"]` — canonical event field to
candidate row keys, dotted paths indexing nested containers. Parsers consult
the map for the resolved city before falling back to their generic chains.
These tests pin the mechanism and the tightened chicago 311 sniff that Austin's
`sr_number`-carrying rows used to trip.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped, resolve_field_map
from src.spatial.city_registry import REGISTRY, CityId, FeedType


class TestFirstMapped:
    def test_plain_key_hit(self):
        assert first_mapped({"a": "1"}, {"f": ["a", "b"]}, "f") == "1"

    def test_first_listed_key_wins(self):
        row = {"b": "second", "a": "first"}
        assert first_mapped(row, {"f": ["a", "b"]}, "f") == "first"

    def test_falls_through_to_later_candidate(self):
        assert first_mapped({"b": "x"}, {"f": ["a", "b"]}, "f") == "x"

    def test_miss_returns_none(self):
        assert first_mapped({}, {"f": ["a"]}, "f") is None

    def test_unknown_canonical_is_ignored(self):
        assert first_mapped({"a": "1"}, {}, "f") is None

    def test_falsy_values_are_skipped_like_chains_do(self):
        """Chain parity: a mapped key holding "" must fall through, not win."""
        assert first_mapped({"a": ""}, {"f": ["a", "b"]}, "f") is None
        row = {"a": "", "b": "real"}
        assert first_mapped(row, {"f": ["a", "b"]}, "f") == "real"

    def test_dotted_path_indexes_nested_container(self):
        row = {"location_1": {"latitude": "34.05"}}
        assert first_mapped(row, {"latitude": ["location_1.latitude"]}, "latitude") == "34.05"

    def test_dotted_path_missing_container_or_field_returns_none(self):
        assert first_mapped({}, {"latitude": ["location_1.latitude"]}, "latitude") is None
        assert (
            first_mapped({"location_1": None}, {"latitude": ["location_1.latitude"]}, "latitude")
            is None
        )
        assert (
            first_mapped({"location_1": {}}, {"latitude": ["location_1.latitude"]}, "latitude")
            is None
        )

    def test_multiple_canonicals_consulted_in_order(self):
        row = {"lat": "1.0"}
        assert first_mapped(row, {"longitude": ["lon"], "latitude": ["lat"]}, "longitude", "latitude") == "1.0"


class TestResolveFieldMap:
    def test_registered_city_with_a_map_returns_it(self):
        fmap = resolve_field_map("los_angeles", FeedType.COMPLAINTS_311)
        assert fmap.get("incident_id") == ["casenumber", "srnumber"]
        assert fmap.get("latitude") == ["geolocation__latitude__s"]

    def test_unknown_city_returns_empty(self):
        assert resolve_field_map("atlantis", FeedType.PERMITS) == {}

    def test_registered_city_without_the_feed_returns_empty(self):
        """LA has no DEEDS feed; its map lookup must degrade, not raise."""
        assert resolve_field_map("los_angeles", FeedType.DEEDS) == {}

    def test_registered_feed_without_a_map_returns_empty(self):
        assert resolve_field_map("nyc", FeedType.PERMITS) == {}


class TestMapOverridesChains:
    """End-to-end: a registered map beats the parser's generic chain."""

    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def _with_nyc_map(self, monkeypatch, field_map):
        reg = REGISTRY[CityId.NYC]
        spec = reg.datasets[FeedType.PERMITS]
        monkeypatch.setitem(
            spec.extra,
            "field_map",
            field_map,
        )

    def test_mapped_job_id_beats_chain(self, permits, monkeypatch):
        self._with_nyc_map(
            monkeypatch,
            {"job_id": ["local_job_key"], "latitude": ["y_lat"], "longitude": ["y_lng"]},
        )
        row = {
            "job__": "chain-would-pick-this",
            "local_job_key": "map-wins",
            "y_lat": "40.7128",
            "y_lng": "-74.0060",
        }
        ev = permits.parse_socrata_row(row, city_id="nyc")
        assert ev.job_id == "map-wins"

    def test_dotted_coordinate_path_parses(self, permits, monkeypatch):
        self._with_nyc_map(
            monkeypatch,
            {
                "job_id": ["job_number"],
                "latitude": ["the_geom.latitude"],
                "longitude": ["the_geom.longitude"],
            },
        )
        row = {
            "job_number": "NYC-1",
            "the_geom": {"latitude": "40.7128", "longitude": "-74.0060"},
        }
        ev = permits.parse_socrata_row(row, city_id="nyc")
        assert ev.latitude == pytest.approx(40.7128)
        assert ev.longitude == pytest.approx(-74.0060)

    def test_unmapped_fields_still_fall_back_to_chains(self, permits, monkeypatch):
        self._with_nyc_map(monkeypatch, {"job_id": ["missing_key"]})
        row = {
            "job__": "NYC-2",
            "latitude": "40.7128",
            "longitude": "-74.0060",
            "issuance_date": "2026-01-15T00:00:00.000",
        }
        ev = permits.parse_socrata_row(row, city_id="nyc")
        assert ev.job_id == "NYC-2"
        assert str(ev.issuance_date).startswith("2026-01-15")


class TestLa311RunsThroughItsMap:
    """The Wave-A LA spellings now live in the registry entry, not the chains."""

    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_myla311_row_still_parses_identically(self, complaints):
        row = {
            "casenumber": "01-20260823-0001234",
            "type": "Bulky Items",
            "createddate": "2026-08-23T08:31:00.000",
            "closeddate": "2026-08-23T14:02:00.000",
            "zipcode__c": "90029",
            "geolocation__latitude__s": "34.08921",
            "geolocation__longitude__s": "-118.27152",
        }
        ev = complaints.parse_socrata_row(row, city_id="los_angeles")
        assert ev is not None
        assert ev.incident_id == "01-20260823-0001234"
        assert ev.zipcode == "90029"
        assert str(ev.created_date).startswith("2026-08-23")

    def test_la_spellings_are_gone_from_shared_chains(self):
        """Guard against regression-by-re-addition: the value-lookup spellings
        belong to the registry entry now. (`casenumber`/`srnumber` legitimately
        remain in the autodetect branch — sniffing is key-presence, which maps
        do not cover.)"""
        import inspect

        from src.producers import complaints_311_producer

        source = inspect.getsource(complaints_311_producer)
        for la_only in (
            "geolocation__latitude__s",
            "geolocation__longitude__s",
            "zipcode__c",
            "requesttype",
            '"createddate"',
            '"closeddate"',
        ):
            assert la_only not in source, f"{la_only} crept back into the shared parser"


class TestChicago311SniffTightening:
    """`sr_number` alone no longer means chicago — Austin 311 carries it too."""

    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_bare_sr_number_row_no_longer_autodetects_chicago(self, complaints):
        austin_shaped = {
            "sr_number": "24-00001234",
            "sr_type_desc": "Code Complaint",
            "sr_created_date": "2026-08-01T10:00:00.000",
            "latitude": "30.2672",
            "longitude": "-97.7431",
        }
        assert complaints.parse_socrata_row(austin_shaped).city_id != "chicago"

    def test_chicago_rows_with_corroborating_markers_still_detect(self, complaints):
        chicago_row = {
            "sr_number": "SR24-00112233",
            "sr_type": "Sanitation Code Violation",
            "ward": "27",
            "created_date": "2026-08-01T10:00:00.000",
            "latitude": "41.8781",
            "longitude": "-87.6298",
        }
        assert complaints.parse_socrata_row(chicago_row).city_id == "chicago"

    def test_sr_type_marker_alone_suffices_for_chicago(self, complaints):
        chicago_row = {
            "sr_number": "SR24-00112234",
            "sr_type": "Rodent Baiting",
            "created_date": "2026-08-01T10:00:00.000",
            "latitude": "41.8781",
            "longitude": "-87.6298",
        }
        assert complaints.parse_socrata_row(chicago_row).city_id == "chicago"
