"""Bay511Client — 511.org SF Bay Area regional GTFS datafeeds → merged feed (US-442).

Queries the 511.org ``/transit/datafeeds`` catalog (keyed — a free developer
token from 511.org), downloads each of the ~32 covered operators' GTFS static
zip (BART, SFMTA Muni, VTA, AC Transit, Caltrain, SamTrans, Golden Gate
Transit, SMART, WestCAT, Wheels, Tri-Delta, County Connection, and the rest of
the regional roster), and merges them into one region-wide feed dict shaped
like ``GtfsStaticClient.parse_feed_zip``'s output (``stops``/``routes``/
``trips``/``stop_times``/``calendar``) so the same GTFS-parsing and
`transit_accessibility` scoring code paths handle it unchanged.

HTTP calls (``fetch_catalog``, ``download_zip``) are thin and mocked in tests;
catalog normalization and the multi-operator merge are pure and tested
offline. Per-operator zip parsing is delegated to
``GtfsStaticClient.parse_feed_zip`` rather than reimplemented, since 511's
GTFS zips share the same five-file schema.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from src.producers.gtfs_static_client import GtfsStaticClient


class Bay511Client:
    """Thin client over the 511.org regional transit datafeeds catalog."""

    DATAFEEDS_URL = "https://api.511.org/transit/datafeeds"

    def __init__(self, api_key: str, timeout_seconds: float = 60.0):
        self.api_key = api_key
        self.timeout = timeout_seconds

    # ------------------------------------------------------------------ #
    # HTTP ingestion  (mock these in tests)                               #
    # ------------------------------------------------------------------ #

    def fetch_catalog(self) -> list[dict[str, str]]:
        """GET the 511 datafeeds catalog and return normalized feed entries."""
        import httpx

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as cl:
            resp = cl.get(self.DATAFEEDS_URL, params={"api_key": self.api_key})
            resp.raise_for_status()
            data = resp.json()
        return self.parse_catalog(data)

    def download_zip(self, url: str) -> bytes:
        """GET ``url`` and return the raw GTFS zip bytes for one operator."""
        import httpx

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as cl:
            resp = cl.get(url)
            resp.raise_for_status()
            return resp.content

    # ------------------------------------------------------------------ #
    # catalog normalization  (pure)                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def parse_catalog(data: Any) -> list[dict[str, str]]:
        """Normalize the 511 ``/transit/datafeeds`` JSON into a flat feed list.

        511 nests one ``OperatorFeeds`` entry per operator, each carrying an
        ``Operator`` record (``Id``/``Name``) and one or more per-feed download
        records (``Uri``/``Url``). Field names and nesting have varied across
        511 API revisions, so this is deliberately defensive: it also accepts
        a bare list of feed dicts, singular (non-list) feed blocks, and either
        casing of the download-url key. Returns
        ``[{"operator_id", "operator_name", "url"}, ...]``, dropping any entry
        that has no resolvable download URL.
        """
        operator_feeds = data.get("OperatorFeeds") if isinstance(data, Mapping) else data
        entries: list[dict[str, str]] = []
        for of in operator_feeds or []:
            operator = of.get("Operator") or {}
            op_id = str(operator.get("Id") or of.get("OperatorReference") or of.get("Id") or "").strip()
            op_name = str(operator.get("Name") or of.get("OperatorName") or op_id or "unknown")

            feeds = of.get("OperatorFeed") or of.get("Feeds") or of.get("Feed")
            if feeds is None:
                continue
            if isinstance(feeds, Mapping):
                feeds = [feeds]
            for f in feeds:
                url = f.get("Uri") or f.get("Url") or f.get("uri") or f.get("url")
                if not url:
                    continue
                entries.append({"operator_id": op_id or op_name, "operator_name": op_name, "url": url})
        return entries

    # ------------------------------------------------------------------ #
    # multi-operator merge  (pure)                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def merge_operator_feeds(named_feeds: Mapping[str, Mapping[str, Any]]) -> dict[str, list[Any]]:
        """Merge parsed per-operator GTFS feed dicts into one region-wide feed.

        Every ``stop_id``/``route_id``/``trip_id``/``service_id`` is prefixed
        with ``f"{operator_name}:"`` because independent Bay Area operators
        frequently reuse small numeric GTFS ids (two agencies both publishing
        a ``stop_id`` of ``"1"``); merging without namespacing would silently
        collapse distinct stops/trips/services from different operators onto
        each other. The result has the same shape as
        ``GtfsStaticClient.parse_feed_zip``'s output, so it is a drop-in input
        to ``transit_accessibility.score_feed``.
        """
        merged: dict[str, list[Any]] = {"stops": [], "routes": [], "trips": [], "stop_times": [], "calendar": []}
        for operator_name, feed in named_feeds.items():
            prefix = f"{operator_name}:"

            for stop_id, lat, lng, name in feed.get("stops") or []:
                merged["stops"].append((f"{prefix}{stop_id}" if stop_id else stop_id, lat, lng, name))

            for row in feed.get("routes") or []:
                r = dict(row)
                if r.get("route_id"):
                    r["route_id"] = f"{prefix}{r['route_id']}"
                r["operator"] = operator_name
                merged["routes"].append(r)

            for row in feed.get("trips") or []:
                r = dict(row)
                if r.get("trip_id"):
                    r["trip_id"] = f"{prefix}{r['trip_id']}"
                if r.get("route_id"):
                    r["route_id"] = f"{prefix}{r['route_id']}"
                if r.get("service_id"):
                    r["service_id"] = f"{prefix}{r['service_id']}"
                merged["trips"].append(r)

            for row in feed.get("stop_times") or []:
                r = dict(row)
                if r.get("trip_id"):
                    r["trip_id"] = f"{prefix}{r['trip_id']}"
                if r.get("stop_id"):
                    r["stop_id"] = f"{prefix}{r['stop_id']}"
                merged["stop_times"].append(r)

            for row in feed.get("calendar") or []:
                r = dict(row)
                if r.get("service_id"):
                    r["service_id"] = f"{prefix}{r['service_id']}"
                merged["calendar"].append(r)
        return merged

    # ------------------------------------------------------------------ #
    # end-to-end pipeline                                                 #
    # ------------------------------------------------------------------ #

    def fetch_all_operator_feeds(
        self,
        download_fn: Callable[[str], bytes] | None = None,
        catalog_fn: Callable[[], list[dict[str, str]]] | None = None,
    ) -> dict[str, list[Any]]:
        """Catalog -> download each operator zip -> parse -> merge into one region-wide feed.

        ``catalog_fn``/``download_fn`` override the network calls (injected in
        tests); by default they hit ``fetch_catalog``/``download_zip``.
        """
        catalog = (catalog_fn or self.fetch_catalog)()
        downloader = download_fn or self.download_zip
        named_feeds: dict[str, dict[str, Any]] = {}
        for entry in catalog:
            zip_bytes = downloader(entry["url"])
            named_feeds[entry["operator_name"]] = GtfsStaticClient.parse_feed_zip(zip_bytes)
        return self.merge_operator_feeds(named_feeds)
