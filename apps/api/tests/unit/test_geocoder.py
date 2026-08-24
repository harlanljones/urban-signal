"""Unit tests for the Wave G1 geocoder (ADR 0004).

Cache tests run against in-memory SQLite; the cache DDL is dialect-aware and
production runs on Postgres. Backend interactions are stubbed — no network.
"""

import pytest
from sqlalchemy import create_engine, text

from src.spatial.geocoder import (
    Geocoder,
    GeoPoint,
    NominatimBackend,
    PostgresGeocodeCache,
    address_hash,
    normalize_address,
)


@pytest.fixture
def cache():
    engine = create_engine("sqlite:///:memory:")
    pgc = PostgresGeocodeCache(engine)
    pgc.ensure_table()
    return pgc


class FakeBackend:
    """Records calls so tests can assert the provider was (not) hit."""

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls: list[str] = []

    def geocode(self, normalized):
        self.calls.append(normalized)
        return self.answers.get(normalized)


class TestNormalization:
    def test_deterministic_and_version_stamped(self):
        import hashlib

        from src.spatial.geocoder import NORM_VERSION

        address = "8020 Meadow Creek Road, Norfolk, VA"
        normalized = normalize_address(address)
        once = address_hash(normalized)
        again = address_hash(normalize_address(address))
        assert once == again != ""
        # The hash covers the normalization version: changing normalization
        # invalidates every cached coordinate by construction.
        assert once == hashlib.sha256(f"{NORM_VERSION}|{normalized}".encode()).hexdigest()

    def test_strips_units_punctuation_and_whitespace(self):
        # v2 removes the designator + value pair IN PLACE: a mid-string unit
        # no longer amputates the city/state tail (US-74 DC finding).
        assert (
            normalize_address("5214 Norvella Ave., Apt 3B; Norfolk, VA")
            == "5214 NORVELLA AVE NORFOLK VA"
        )
        assert normalize_address("100 Main St #4") == "100 MAIN ST"
        assert normalize_address("100 Main ST UNIT B") == "100 MAIN ST"

    def test_mid_string_unit_keeps_the_city_tail(self):
        # The exact DC failure shape from the US-74 leaf probe: tail-truncation
        # turned this resolvable address into a TIGER miss.
        assert (
            normalize_address("7701 Georgia Ave NW, Ste 102, Washington, DC 20012")
            == "7701 GEORGIA AVE NW WASHINGTON DC 20012"
        )
        # Trailing designator with no value token still collapses cleanly.
        assert normalize_address("10 Oak St Apt") == "10 OAK ST"
        assert normalize_address("") == ""
        assert normalize_address(None) == ""


class TestCacheReplayGuarantee:
    def test_first_answer_is_frozen_forever(self, cache):
        backend = FakeBackend(
            {"100 MAIN ST": GeoPoint(36.9, -76.2, 0.95, "nominatim:way")}
        )
        geocoder = Geocoder(cache, backend, confidence_floor=0.9)

        first = geocoder.geocode("100 Main St")
        assert first is not None and first.lat == 36.9

        # Provider data drifts, the cache does not: a changed backend answer
        # is invisible because the provider is never consulted again.
        backend.answers["100 MAIN ST"] = GeoPoint(99.0, 99.0, 1.0, "nominatim:way")
        second = geocoder.geocode("100 MAIN st".lower())
        assert second.lat == 36.9
        assert backend.calls == ["100 MAIN ST"]

    def test_definitive_misses_are_cached_too(self, cache):
        backend = FakeBackend({"200 GHOST RD": None})
        geocoder = Geocoder(cache, backend, confidence_floor=0.9)
        assert geocoder.geocode("200 Ghost Rd") is None
        assert geocoder.geocode("200 ghost rd") is None
        assert backend.calls.count("200 GHOST RD") == 1


class TestConfidenceGating:
    def test_below_floor_resolves_none_but_keeps_raw_value(self, cache):
        backend = FakeBackend(
            {"300 AREA WAY": GeoPoint(36.9, -76.2, 0.5, "nominatim:node")}
        )
        strict = Geocoder(cache, backend, confidence_floor=0.9)
        assert strict.geocode("300 Area Way") is None

        # Raw value is immutable in cache; policy can re-evaluate at read time.
        lenient = Geocoder(cache, FakeBackend(), confidence_floor=0.25)
        relaxed = lenient.geocode("300 Area Way")
        assert relaxed is not None and relaxed.confidence == 0.5

    def test_exact_passes_floor(self, cache):
        backend = FakeBackend(
            {"400 EXACT ST": GeoPoint(-76.2, 36.9, 1.0, "census:exact")}
        )
        assert Geocoder(cache, backend).geocode("400 Exact St") is not None


class TestBatchPath:
    def test_batch_backend_receives_only_uncached(self, cache):
        class BatchBackend:
            def __init__(self):
                self.batches = []

            def geocode_many(self, pairs):
                self.batches.append(list(pairs))
                return {
                    digest: GeoPoint(10.0 + i, 20.0 + i, 0.95, "census:exact")
                    for i, (digest, _norm) in enumerate(pairs)
                }

        backend = BatchBackend()
        geocoder = Geocoder(cache, backend)
        warm = geocoder.geocode("1 WARM AVE")  # populates nothing; different addr below
        addresses = [f"{n} BATCH ST" for n in range(50, 60)]
        resolved = geocoder.geocode_many(addresses)
        assert all(point is not None for point in resolved)
        assert len(backend.batches) == 1 and len(backend.batches[0]) == 10

        # Second pass: everything cache-hits, provider untouched.
        again = geocoder.geocode_many(addresses)
        assert [p.confidence for p in again] == [p.confidence for p in resolved]
        assert len(backend.batches) == 1
        assert warm is None  # never asked the backend

    def test_sequential_fallback_for_backends_without_batches(self, cache):
        class SingleOnly(FakeBackend):
            pass

        backend = SingleOnly({f"{n} SOLO ST": GeoPoint(1.0, 2.0, 0.95, "x") for n in range(3)})
        resolved = Geocoder(cache, backend).geocode_many(["0 Solo St", "1 solo st", "2 SOLO st"])
        assert all(point is not None for point in resolved)


class TestProviderOutages:
    def test_backend_exception_degrades_without_caching(self, cache):
        class ExplodingBackend:
            def geocode(self, normalized):
                raise RuntimeError("provider down")

        geocoder = Geocoder(cache, ExplodingBackend())
        assert geocoder.geocode("500 Down St") is None
        rows = cache.engine.connect().execute(
            text("SELECT COUNT(*) FROM geocode_cache")
        ).scalar()
        assert rows == 0  # outage must not freeze as a miss


class TestNominatimParsing:
    def test_corroboration_scoring(self, monkeypatch):
        backend = NominatimBackend(min_interval_seconds=0.0)

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return [
                    {
                        "lat": "36.92",
                        "lon": "-76.23",
                        "osm_type": "way",
                        "display_name": "8020, Meadow Creek Road, Norfolk, VA",
                    }
                ]

        captured = {}

        def fake_get(url, params=None):
            captured["q"] = params["q"]
            return FakeResponse()

        monkeypatch.setattr(backend._client, "get", fake_get)
        hit = backend.geocode("8020 MEADOW CREEK ROAD NORFOLK VA")
        assert hit.confidence == 0.95 and hit.source.startswith("nominatim:")

        miss = backend.geocode("999 NOWHERE STREET NORFOLK VA")
        assert miss.confidence < 0.9  # uncorroborated area guess


class TestCensusParsing:
    def test_tiger_match_is_full_confidence(self, monkeypatch):
        from src.spatial.geocoder import CensusBackend

        backend = CensusBackend(min_interval_seconds=0.0)

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "result": {
                        "addressMatches": [
                            {
                                "coordinates": {"x": -76.27, "y": 36.878},
                                "matchedAddress": "3039 VENDOME TER, NORFOLK, VA",
                            }
                        ]
                    }
                }

        monkeypatch.setattr(backend, "_last_call", 0.0)
        monkeypatch.setattr(
            "src.spatial.geocoder.httpx.get", lambda *a, **k: FakeResponse()
        )
        point = backend.geocode("3039 VENDOME PLACE NORFOLK VA")
        assert point is not None
        assert (point.lat, point.lon) == (36.878, -76.27)
        assert point.confidence == 1.0 and point.source == "census:tiger"

    def test_no_matches_is_a_miss(self, monkeypatch):
        from src.spatial.geocoder import CensusBackend

        backend = CensusBackend(min_interval_seconds=0.0)

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"result": {"addressMatches": []}}

        monkeypatch.setattr(
            "src.spatial.geocoder.httpx.get", lambda *a, **k: FakeResponse()
        )
        assert backend.geocode("NOWHERE") is None

    def test_settings_backend_selection(self, monkeypatch):
        from unittest.mock import MagicMock

        from src.spatial import geocoder as module

        monkeypatch.setattr(module, "_geocoder_singleton", None)
        monkeypatch.setattr(module, "PostgresGeocodeCache", lambda uri: MagicMock())
        monkeypatch.setattr("src.config.settings.geocode_backend", "census")
        assert isinstance(module.get_geocoder().backend, module.CensusBackend)
        monkeypatch.setattr(module, "_geocoder_singleton", None)
        monkeypatch.setattr("src.config.settings.geocode_backend", "nominatim")
        assert isinstance(module.get_geocoder().backend, module.NominatimBackend)
        monkeypatch.setattr(module, "_geocoder_singleton", None)
