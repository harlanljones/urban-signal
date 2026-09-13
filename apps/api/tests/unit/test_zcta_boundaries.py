"""Unit tests for the TIGERweb ZCTA boundary client (US-440).

Network-free: ``_query`` is monkeypatched to return canned GeoJSON geometry
instead of hitting TIGERweb, mirroring how ``test_series_client.py`` stubs
the geography crosswalk's network calls. Disk caching is exercised against a
``tmp_path`` cache dir.
"""

import json

import pytest
from shapely.geometry import Polygon

from src.spatial.zcta_boundaries import ZctaBoundaryClient, _geometry_to_polygon

SQUARE_94610 = {
    "type": "Polygon",
    "coordinates": [[[-122.26, 37.80], [-122.26, 37.82], [-122.24, 37.82], [-122.24, 37.80], [-122.26, 37.80]]],
}

MULTIPOLYGON_WITH_SLIVER = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[-122.26, 37.80], [-122.26, 37.82], [-122.24, 37.82], [-122.24, 37.80], [-122.26, 37.80]]],
        # A tiny detached offshore sliver, much smaller than the mainland part.
        [[[-122.10, 37.70], [-122.10, 37.701], [-122.099, 37.701], [-122.099, 37.70], [-122.10, 37.70]]],
    ],
}


@pytest.fixture
def client(tmp_path, monkeypatch) -> ZctaBoundaryClient:
    c = ZctaBoundaryClient(cache_dir=tmp_path / "zcta_boundaries")
    return c


class TestGeometryConversion:
    def test_polygon_passthrough(self):
        poly = _geometry_to_polygon(SQUARE_94610)
        assert isinstance(poly, Polygon)
        assert poly.area > 0

    def test_multipolygon_keeps_largest_part(self):
        poly = _geometry_to_polygon(MULTIPOLYGON_WITH_SLIVER)
        assert isinstance(poly, Polygon)
        # The mainland square is vastly larger than the sliver.
        assert poly.area > 0.0003

    def test_invalid_geometry_returns_none(self):
        assert _geometry_to_polygon({"type": "Point", "coordinates": [0, 0]}) is None


class TestZctaBoundaryClient:
    def test_fetch_and_cache(self, client, monkeypatch):
        calls = []

        def fake_query(self, zctas):
            calls.append(list(zctas))
            return {"94610": SQUARE_94610}

        monkeypatch.setattr(ZctaBoundaryClient, "_query", fake_query)

        polygons = client.get_polygons(["94610"])
        assert set(polygons) == {"94610"}
        assert polygons["94610"].area > 0
        assert len(calls) == 1

        cache_file = client.cache_dir / "94610.geojson"
        assert cache_file.exists()
        assert json.loads(cache_file.read_text()) == SQUARE_94610

    def test_second_call_is_served_from_cache_without_network(self, client, monkeypatch):
        call_count = {"n": 0}

        def fake_query(self, zctas):
            call_count["n"] += 1
            return {z: SQUARE_94610 for z in zctas}

        monkeypatch.setattr(ZctaBoundaryClient, "_query", fake_query)

        client.get_polygons(["94610"])
        assert call_count["n"] == 1

        # A fresh client instance sharing the same cache_dir should not
        # re-query at all — proves the cache is disk-backed, not memo-only.
        fresh = ZctaBoundaryClient(cache_dir=client.cache_dir)
        monkeypatch.setattr(ZctaBoundaryClient, "_query", fake_query)
        polygons = fresh.get_polygons(["94610"])
        assert set(polygons) == {"94610"}
        assert call_count["n"] == 1

    def test_missing_zcta_is_cached_as_a_miss(self, client, monkeypatch):
        call_count = {"n": 0}

        def fake_query(self, zctas):
            call_count["n"] += 1
            return {}  # TIGERweb has no boundary for this (retired) ZCTA

        monkeypatch.setattr(ZctaBoundaryClient, "_query", fake_query)

        assert client.get_polygon("00000") is None
        assert client.get_polygon("00000") is None  # served from cached miss
        assert call_count["n"] == 1

    def test_offline_raises_on_cache_miss(self, tmp_path):
        offline_client = ZctaBoundaryClient(cache_dir=tmp_path / "empty", offline=True)
        with pytest.raises(FileNotFoundError):
            offline_client.get_polygons(["94610"])

    def test_offline_reads_a_warm_cache(self, tmp_path, monkeypatch):
        cache_dir = tmp_path / "warm"
        warm = ZctaBoundaryClient(cache_dir=cache_dir)

        def fake_query(self, zctas):
            return {"94610": SQUARE_94610}

        monkeypatch.setattr(ZctaBoundaryClient, "_query", fake_query)
        warm.get_polygons(["94610"])

        offline_client = ZctaBoundaryClient(cache_dir=cache_dir, offline=True)
        polygons = offline_client.get_polygons(["94610"])
        assert set(polygons) == {"94610"}
