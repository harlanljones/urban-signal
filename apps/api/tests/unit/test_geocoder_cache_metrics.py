"""Tests for geocoder cache hit-rate tracking/logging (US-441, ADR 0004)."""

import pytest
from sqlalchemy import create_engine

from src.spatial.geocoder import Geocoder, GeoPoint, PostgresGeocodeCache


@pytest.fixture
def cache():
    engine = create_engine("sqlite:///:memory:")
    pgc = PostgresGeocodeCache(engine)
    pgc.ensure_table()
    return pgc


class FakeBackend:
    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls: list[str] = []

    def geocode(self, normalized):
        self.calls.append(normalized)
        return self.answers.get(normalized)


class TestCacheHitRate:
    def test_starts_at_zero_with_no_lookups(self, cache):
        geocoder = Geocoder(cache, FakeBackend())
        assert geocoder.cache_hit_rate() == 0.0

    def test_first_lookup_of_new_address_is_a_miss(self, cache):
        backend = FakeBackend({"123 MAIN ST": GeoPoint(1.0, 2.0, 0.95, "fake")})
        geocoder = Geocoder(cache, backend)
        geocoder.geocode("123 Main St")
        assert geocoder.cache_hit_rate() == 0.0
        assert backend.calls == ["123 MAIN ST"]

    def test_repeat_lookup_is_a_hit_and_skips_backend(self, cache):
        backend = FakeBackend({"123 MAIN ST": GeoPoint(1.0, 2.0, 0.95, "fake")})
        geocoder = Geocoder(cache, backend)
        geocoder.geocode("123 Main St")
        geocoder.geocode("123 Main St")
        # 1 miss (first call) + 1 hit (second call) = 0.5 hit rate.
        assert geocoder.cache_hit_rate() == pytest.approx(0.5)
        assert backend.calls == ["123 MAIN ST"]  # backend hit only once

    def test_hit_rate_across_mixed_addresses(self, cache):
        backend = FakeBackend(
            {
                "123 MAIN ST": GeoPoint(1.0, 2.0, 0.95, "fake"),
                "456 OAK AVE": GeoPoint(3.0, 4.0, 0.95, "fake"),
            }
        )
        geocoder = Geocoder(cache, backend)
        geocoder.geocode("123 Main St")  # miss
        geocoder.geocode("456 Oak Ave")  # miss
        geocoder.geocode("123 Main St")  # hit
        geocoder.geocode("123 Main St")  # hit
        assert geocoder.cache_hit_rate() == pytest.approx(0.5)

    def test_geocode_many_records_hits_and_misses(self, cache):
        backend = FakeBackend(
            {
                "123 MAIN ST": GeoPoint(1.0, 2.0, 0.95, "fake"),
                "456 OAK AVE": GeoPoint(3.0, 4.0, 0.95, "fake"),
            }
        )
        geocoder = Geocoder(cache, backend)
        geocoder.geocode("123 Main St")  # miss, cached
        geocoder.geocode_many(["123 Main St", "456 Oak Ave"])  # 1 hit, 1 miss
        assert geocoder.cache_hit_rate() == pytest.approx(1.0 / 3.0)

    def test_definitive_miss_is_still_a_cache_hit_on_replay(self, cache):
        """A frozen miss (ADR 0004) answers from cache without a backend call."""
        backend = FakeBackend({})  # backend has nothing for any address
        geocoder = Geocoder(cache, backend)
        geocoder.geocode("999 Nowhere Rd")  # miss: backend called, returns None, frozen
        assert len(backend.calls) == 1
        geocoder.geocode("999 Nowhere Rd")  # replay: answered from the frozen miss
        assert len(backend.calls) == 1  # backend not called again
        assert geocoder.cache_hit_rate() == pytest.approx(0.5)
