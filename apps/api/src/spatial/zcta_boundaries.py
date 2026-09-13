"""ZCTA boundary polygons for the ZIP-to-H3 area-weighted join (US-440).

:mod:`src.spatial.geography_crosswalk` resolves a ZIP/ZCTA to its Census
Gazetteer **centroid** — enough to pick a city_id or tag one H3 cell, not
enough to area-weight a ZCTA across every hex it overlaps. This module fetches
the actual ZCTA polygon.

**Source.** The Census Bureau's TIGERweb ArcGIS REST service publishes ZCTA
boundaries as a queryable polygon layer with no key and no download of the
33,791-ZCTA national shapefile required —
``TIGERweb/tigerWMS_Current/MapServer/2`` ("2020 Census ZIP Code Tabulation
Areas"), verified live 2026-09-13 returning a Polygon geometry via a plain
``f=geojson`` GET filtered with ``ZCTA5 IN (...)``. This avoids adding a
shapefile-reading dependency (geopandas/fiona/pyshp are not in this project's
dependency set); ``shapely`` and ``httpx``, already dependencies, are
sufficient once the geometry is JSON.

Polygons are cached to disk exactly like
:class:`~src.spatial.geography_crosswalk.GeographyCrosswalk` — one small
GeoJSON file per ZCTA under ``data/crosswalk/zcta_boundaries/`` — so a warm
cache never touches the network, and ``offline=True`` fails readably instead
of hanging on a query.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon, shape

logger = logging.getLogger(__name__)

TIGERWEB_ZCTA_LAYER = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
    "tigerWMS_Current/MapServer/2/query"
)

DEFAULT_CACHE_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "crosswalk" / "zcta_boundaries"
)

# TIGERweb caps a query's IN-clause comfortably below its URL length limit;
# chunking mirrors ArcGISClient's parcel join (100 values per request).
_QUERY_CHUNK_SIZE = 100


def _cache_dir() -> Path:
    override = os.environ.get("URBAN_ZCTA_BOUNDARY_CACHE_DIR")
    return Path(override) if override else DEFAULT_CACHE_DIR


class ZctaBoundaryFetchError(RuntimeError):
    """Raised when TIGERweb is unreachable or returns an unusable payload."""


def _geometry_to_polygon(geometry: dict) -> Polygon | None:
    """Reduce a GeoJSON Polygon/MultiPolygon to one Polygon (largest ring set).

    A handful of ZCTAs (barrier islands, bay-adjacent ZIPs with a small
    offshore parcel) are MultiPolygon; the largest part is the ZCTA's mainland
    body and area-weighting against tiny detached slivers is not worth the
    added multi-part bookkeeping for a metro-scoped join.
    """
    try:
        geom = shape(geometry)
    except Exception:  # noqa: BLE001 — malformed TIGERweb geometry must not kill the join
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        parts = list(geom.geoms)
        if not parts:
            return None
        return max(parts, key=lambda p: p.area)
    return None


class ZctaBoundaryClient:
    """Fetches and caches ZCTA polygons from Census TIGERweb."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        offline: bool = False,
        timeout_seconds: float = 60.0,
    ):
        self.cache_dir = Path(cache_dir) if cache_dir else _cache_dir()
        self.offline = offline
        self.timeout = timeout_seconds
        self._memo: dict[str, Polygon | None] = {}

    def _cache_path(self, zcta: str) -> Path:
        return self.cache_dir / f"{zcta}.geojson"

    def _read_cache(self, zcta: str) -> dict | None:
        path = self._cache_path(zcta)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return None

    def _write_cache(self, zcta: str, geometry: dict | None) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._cache_path(zcta)
        # A ZCTA absent from TIGERweb (retired/invalid code) is cached as
        # `null` so a repeat lookup doesn't re-query it every run.
        path.write_text(json.dumps(geometry))

    def _query(self, zctas: list[str]) -> dict[str, dict]:
        import httpx

        escaped = ",".join(f"'{z}'" for z in zctas)
        params = {
            "where": f"ZCTA5 IN ({escaped})",
            "outFields": "ZCTA5",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        }
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(TIGERWEB_ZCTA_LAYER, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except Exception as exc:
            raise ZctaBoundaryFetchError(
                f"TIGERweb ZCTA query failed for {zctas}: {exc}"
            ) from exc

        features = payload.get("features") or []
        result: dict[str, dict] = {}
        for feature in features:
            props = feature.get("properties") or {}
            zcta = str(props.get("ZCTA5") or "").strip()
            geometry = feature.get("geometry")
            if zcta and geometry:
                result[zcta] = geometry
        return result

    def get_polygon(self, zcta: str) -> Polygon | None:
        """Return one ZCTA's polygon, or None if it has no TIGERweb boundary."""
        polygons = self.get_polygons([zcta])
        return polygons.get(zcta)

    def get_polygons(self, zctas: Iterable[str]) -> dict[str, Polygon]:
        """Return polygons for every ZCTA that has one, skipping the rest.

        Cache-first: a ZCTA already on disk (including a cached "no boundary"
        miss) never triggers a network call. Uncached ZCTAs are queried in
        batches and the whole batch (hits and misses) is written back so a
        rerun over the same ZIP set is fully offline.
        """
        zctas = list(dict.fromkeys(z for z in zctas if z))
        resolved: dict[str, Polygon] = {}
        to_fetch: list[str] = []

        for zcta in zctas:
            if zcta in self._memo:
                if self._memo[zcta] is not None:
                    resolved[zcta] = self._memo[zcta]
                continue
            cached = self._read_cache(zcta)
            if cached is not None or self._cache_path(zcta).exists():
                polygon = _geometry_to_polygon(cached) if cached else None
                self._memo[zcta] = polygon
                if polygon is not None:
                    resolved[zcta] = polygon
                continue
            to_fetch.append(zcta)

        if not to_fetch:
            return resolved

        if self.offline:
            raise FileNotFoundError(
                f"ZCTA boundary cache miss for {to_fetch} and offline=True — "
                f"prime the cache with ZctaBoundaryClient().get_polygons(...) "
                f"while online"
            )

        for start in range(0, len(to_fetch), _QUERY_CHUNK_SIZE):
            chunk = to_fetch[start : start + _QUERY_CHUNK_SIZE]
            geometries = self._query(chunk)
            for zcta in chunk:
                geometry = geometries.get(zcta)
                self._write_cache(zcta, geometry)
                polygon = _geometry_to_polygon(geometry) if geometry else None
                self._memo[zcta] = polygon
                if polygon is not None:
                    resolved[zcta] = polygon

        return resolved
