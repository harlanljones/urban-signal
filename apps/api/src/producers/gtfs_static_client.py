"""GtfsStaticClient — MobilityDatabase catalog → GTFS static schedule → per-H3 covariates (US-403).

Queries the MobilityDatabase catalog (keyless), downloads in-scope operators'
``google_transit.zip``, parses the five required GTFS files (stops, routes,
trips, stop_times, calendar), and emits per-H3 covariates:

*   ``stop_density`` — number of stops in the effective hex
*   ``service_frequency`` — average daily departures from stops in the hex
*   ``route_count`` — number of distinct routes serving the hex

Quarterly refresh. All output rides as ``EnrichedH3Feature`` context covariates
(no new event schema). Uses the existing ``parse_gtfs_stops`` from
``ntd_transit`` and ``H3SpatialIndexer`` for spatial tagging.
"""

from __future__ import annotations

import csv
import io
import os
import tempfile
from collections.abc import Callable, Iterable
from typing import Any
from zipfile import ZipFile

from src.spatial.h3_indexer import H3SpatialIndexer
from src.spatial.ntd_transit import parse_gtfs_stops

# A bounding box is {min_lat, max_lat, min_lon, max_lon}.
Bbox = dict[str, float]

_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _in_bbox(lat: float, lon: float, bbox: Bbox | None) -> bool:
    """True when the coordinate falls inside the bounding box (inclusive)."""
    if bbox is None:
        return True
    return (
        bbox["min_lat"] <= lat <= bbox["max_lat"]
        and bbox["min_lon"] <= lon <= bbox["max_lon"]
    )


def _feed_bbox(feed: dict[str, Any]) -> Bbox | None:
    """First bounding box reported on a MobilityDatabase feed record."""
    locations = feed.get("locations") or []
    for loc in locations:
        bb = loc.get("bounding_box")
        if isinstance(bb, dict) and all(k in bb for k in ("min_lat", "max_lat", "min_lon", "max_lon")):
            return {
                "min_lat": float(bb["min_lat"]),
                "max_lat": float(bb["max_lat"]),
                "min_lon": float(bb["min_lon"]),
                "max_lon": float(bb["max_lon"]),
            }
    return None


def _bboxes_overlap(a: Bbox, b: Bbox) -> bool:
    return not (
        a["max_lat"] < b["min_lat"]
        or a["min_lat"] > b["max_lat"]
        or a["max_lon"] < b["min_lon"]
        or a["min_lon"] > b["max_lon"]
    )


class GtfsStaticClient:
    """Thin client that downloads GTFS static feeds and produces per-H3 covariates.

    The catalog fetch and zip download hit real HTTP endpoints. Parsing is pure:
    ``parse_feed_zip`` accepts zip bytes directly, so all logic is testable offline.
    """

    CATALOG_URL = (
        "https://api.mobilitydata.org/v1/feeds"
        "?location.country_code=US&data_type=gtfs"
    )
    """Keyless MobilityDatabase v1 catalogue for US GTFS-schedule feeds."""

    def __init__(
        self,
        indexer: Callable[[float, float], dict[str, str]] | None = None,
        timeout_seconds: float = 60.0,
    ):
        self._indexer = indexer or H3SpatialIndexer.get_multi_res_hierarchy
        self.timeout = timeout_seconds

    # ------------------------------------------------------------------ #
    # HTTP ingestion  (mock these in tests)                               #
    # ------------------------------------------------------------------ #

    def fetch_catalog(self) -> list[dict[str, Any]]:
        """GET the MobilityDatabase catalog, return the feed records."""
        import httpx

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as cl:
            resp = cl.get(self.CATALOG_URL)
            resp.raise_for_status()
            data = resp.json()
        feeds: list[dict[str, Any]] = data if isinstance(data, list) else data.get("data", [])
        return feeds

    def download_zip(self, url: str) -> bytes:
        """GET ``url`` and return the raw zip bytes.

        ``url`` is the feed's ``urls.direct_download`` (``google_transit.zip``).
        """
        import httpx

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as cl:
            resp = cl.get(url)
            resp.raise_for_status()
            return resp.content

    # ------------------------------------------------------------------ #
    # feed selection  (bbox filtering)                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def select_feeds_for_bboxes(
        catalog: list[dict[str, Any]],
        bboxes: Iterable[Bbox] | None = None,
    ) -> list[dict[str, Any]]:
        """Feeds whose bounding box overlaps any of the given metro bboxes.

        When ``bboxes`` is empty/None the whole catalog is returned (the caller
        may defer filtering to stop level instead).
        """
        if not bboxes:
            return list(catalog)
        hits: list[dict[str, Any]] = []
        for feed in catalog:
            fb = _feed_bbox(feed)
            if fb is None:
                continue
            for mb in bboxes:
                if _bboxes_overlap(fb, mb):
                    hits.append(feed)
                    break
        return hits

    @staticmethod
    def get_download_url(feed: dict[str, Any]) -> str | None:
        """Extract the ``direct_download`` URL from a catalog feed record."""
        urls = feed.get("urls") or {}
        return urls.get("direct_download") or urls.get("static_current")

    @staticmethod
    def get_provider_name(feed: dict[str, Any]) -> str:
        """Human-readable operator label."""
        prov = feed.get("provider") or {}
        return str(prov.get("name") or feed.get("id", "unknown"))

    # ------------------------------------------------------------------ #
    # GTFS parsing  (pure — accepts zip bytes)                            #
    # ------------------------------------------------------------------ #

    @classmethod
    def parse_feed_zip(cls, zip_bytes: bytes) -> dict[str, Any]:
        """Parse a GTFS static zip, return an intermediate feed summary.

        Result keys: ``stops`` (list of ``(stop_id, lat, lng, name)`` tuples),
        ``routes``, ``trips``, ``stop_times``, ``calendar`` (lists of dicts).
        """
        fd, path = tempfile.mkstemp(suffix=".zip")
        try:
            os.write(fd, zip_bytes)
            os.close(fd)
            stops = parse_gtfs_stops(path)
            with ZipFile(path) as z:
                routes = cls._read_csv(z, "routes.txt")
                trips = cls._read_csv(z, "trips.txt")
                stop_times = cls._read_csv(z, "stop_times.txt")
                calendar = cls._read_csv(z, "calendar.txt")
        finally:
            os.unlink(path)
        return {
            "stops": stops,
            "routes": routes,
            "trips": trips,
            "stop_times": stop_times,
            "calendar": calendar,
        }

    @staticmethod
    def _read_csv(zf: ZipFile, name: str) -> list[dict[str, str]]:
        if name not in zf.namelist():
            return []
        with zf.open(name) as f:
            return list(csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace")))

    # ------------------------------------------------------------------ #
    # covariate computation  (pure)                                       #
    # ------------------------------------------------------------------ #

    @classmethod
    def compute_covariates(
        cls,
        feed: dict[str, Any],
        bbox: Bbox | None = None,
        indexer: Callable[[float, float], dict[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        """Per-H3 covariates from one parsed feed.

        Each output dict carries:
            h3_res7, h3_res8, h3_res9, effective_h3, effective_resolution,
            stop_density, service_frequency, route_count.
        Stops outside *bbox* (when given) are excluded.
        """
        indexer = indexer or H3SpatialIndexer.get_multi_res_hierarchy
        stops = feed.get("stops") or []
        trips = feed.get("trips") or []
        stop_times = feed.get("stop_times") or []
        calendar = feed.get("calendar") or []

        service_days = cls._service_day_map(calendar)  # service_id -> days/week

        trip_route: dict[str, str] = {}
        trip_service: dict[str, str] = {}
        for t in trips:
            tid = (t.get("trip_id") or "").strip()
            if not tid:
                continue
            trip_route[tid] = (t.get("route_id") or "").strip()
            trip_service[tid] = (t.get("service_id") or "").strip()

        # Average daily departures per stop: for each stop_time, weight the
        # departure by (active days that trip's service runs / 7).
        departures: dict[str, float] = {}
        for st in stop_times:
            tid = (st.get("trip_id") or "").strip()
            sid = (st.get("stop_id") or "").strip()
            if not tid or not sid:
                continue
            svc = trip_service.get(tid)
            weight = service_days.get(svc, 7.0) / 7.0 if svc else 1.0
            departures[sid] = departures.get(sid, 0.0) + weight

        # Map each stop_id -> effective hex and accumulate stop-level stats.
        # Track which routes serve each stop (via stop_times -> trip -> route).
        stop_routes: dict[str, set[str]] = {}
        for st in stop_times:
            tid = (st.get("trip_id") or "").strip()
            sid = (st.get("stop_id") or "").strip()
            if not tid or not sid:
                continue
            rid = trip_route.get(tid)
            if rid:
                stop_routes.setdefault(sid, set()).add(rid)

        tally: dict[str, dict[str, Any]] = {}
        for stop_id, lat, lng, _name in stops:
            if not _in_bbox(lat, lng, bbox):
                continue
            hierarchy = indexer(lat, lng)
            prior = tally.get(hierarchy["h3_res9"], {}).get("stop_density", 0)
            effective, eff_res = H3SpatialIndexer.dynamic_spatial_fallback(
                hierarchy["h3_res9"], prior + 1
            )
            bucket = tally.setdefault(
                effective,
                {
                    "h3_res7": hierarchy["h3_res7"],
                    "h3_res8": hierarchy["h3_res8"],
                    "h3_res9": hierarchy["h3_res9"],
                    "effective_h3": effective,
                    "effective_resolution": eff_res,
                    "stop_density": 0,
                    "service_frequency": 0.0,
                    "route_count": 0,
                },
            )
            bucket["stop_density"] += 1
            bucket["service_frequency"] += departures.get(stop_id, 0.0)
            bucket["route_count"] += len(stop_routes.get(stop_id, set()))

        return list(tally.values())

    @staticmethod
    def _service_day_map(calendar_rows: list[dict[str, Any]]) -> dict[str, float]:
        """``service_id`` → average days per week (0.0–7.0)."""
        result: dict[str, float] = {}
        for row in calendar_rows:
            sid = (row.get("service_id") or "").strip()
            if not sid:
                continue
            count = sum(1 for d in _WEEKDAYS if str(row.get(d, "0")).strip() == "1")
            result[sid] = float(count)
        return result
