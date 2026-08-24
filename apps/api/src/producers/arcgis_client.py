"""ArcGIS FeatureServer client with retry backoff, pagination, and query filtering.

Mirrors :class:`~src.producers.socrata_client.SocrataClient` so the two satisfy the
same ``PaginatingClient`` protocol in :mod:`src.spatial.city_registry` and are
interchangeable at the producer call sites.

Two things differ from Socrata and are handled here rather than by callers:

* **Paging.** ArcGIS pages with ``resultOffset``/``resultRecordCount`` and reports
  more-pages-available via ``exceededTransferLimit`` rather than by a short page.
  Layers cap a page at ``maxRecordCount`` (1000 for King County parcel sales), so a
  larger ``batch_size`` is silently truncated server-side.
* **Records.** A feature is ``{"attributes": {...}, "geometry": {...}}``. We flatten
  to the attributes dict so downstream row parsers see a Socrata-shaped record, and
  lift point geometry to ``latitude``/``longitude`` keys when present.

Date fields come back as epoch **milliseconds**; we convert them to ISO 8601 UTC
strings using the layer's own field metadata, which is fetched once and cached.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

import httpx


class ArcGISClient:
    """Robust client for ArcGIS REST FeatureServer / MapServer layer endpoints."""

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        max_retries: int = 4,
        return_geometry: bool = True,
    ):
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.return_geometry = return_geometry
        # layer_url -> {"date_fields": set[str], "oid_field": str, "max_record_count": int}
        self._layer_meta: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _normalize_layer_url(endpoint_url: str) -> str:
        """Strip a trailing ``/query`` so callers may pass either form."""
        return endpoint_url.rstrip("/").removesuffix("/query")

    def _request_json(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """GET a JSON payload with exponential backoff, raising on ArcGIS error bodies."""
        backoff = 1.0
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, params=params)
                    if resp.status_code == 429:
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                    resp.raise_for_status()
                    payload = resp.json()

                # ArcGIS reports failures in a 200 body, so this must be checked
                # explicitly rather than relying on the HTTP status alone.
                if isinstance(payload, dict) and "error" in payload:
                    err = payload["error"]
                    raise RuntimeError(
                        f"ArcGIS error {err.get('code')}: {err.get('message')} "
                        f"{'; '.join(err.get('details', []))}".strip()
                    )
                return payload
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Failed to fetch ArcGIS records after {attempt} attempts: {e}"
                    ) from e
                time.sleep(backoff)
                backoff *= 2.0

        return {}

    def get_layer_metadata(self, endpoint_url: str) -> Dict[str, Any]:
        """Fetch and cache a layer's date fields, OID field, and server page cap."""
        layer_url = self._normalize_layer_url(endpoint_url)
        if layer_url in self._layer_meta:
            return self._layer_meta[layer_url]

        payload = self._request_json(layer_url, {"f": "json"})
        fields = payload.get("fields") or []
        meta = {
            "date_fields": {
                f["name"] for f in fields if f.get("type") == "esriFieldTypeDate"
            },
            "oid_field": payload.get("objectIdField") or "OBJECTID",
            "max_record_count": int(payload.get("maxRecordCount") or 1000),
        }
        self._layer_meta[layer_url] = meta
        return meta

    @staticmethod
    def _epoch_ms_to_iso(value: Any) -> Any:
        """Convert an ArcGIS epoch-millisecond timestamp to an ISO 8601 UTC string."""
        if value is None or isinstance(value, str):
            return value
        try:
            return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError, OverflowError):
            return value

    def _flatten_feature(
        self, feature: Dict[str, Any], date_fields: set
    ) -> Dict[str, Any]:
        """Flatten one ArcGIS feature into a Socrata-shaped flat record."""
        record: Dict[str, Any] = dict(feature.get("attributes") or {})

        for name in date_fields:
            if name in record:
                record[name] = self._epoch_ms_to_iso(record[name])

        lng, lat = self._geometry_to_lng_lat(feature.get("geometry") or {})
        if lng is not None and lat is not None:
            record.setdefault("longitude", lng)
            record.setdefault("latitude", lat)

        return record

    @staticmethod
    def _geometry_to_lng_lat(geometry: Dict[str, Any]) -> tuple:
        """Reduce any ArcGIS geometry to a single representative ``(lng, lat)``.

        Downstream row parsers need one coordinate per record to derive H3 cells,
        but a layer may serve points, polylines, or polygons. Parcel layers such as
        King County's parcel sales serve polygons, so a lone ``x``/``y`` check would
        silently yield no coordinate at all and drop every row's H3 index.

        Coordinates are already WGS84 because every query requests ``outSR=4326``.
        """
        if "x" in geometry and "y" in geometry:
            return geometry["x"], geometry["y"]

        # Polygon rings and polyline paths share the same nested-coordinate shape.
        parts = geometry.get("rings") or geometry.get("paths") or []
        points = [pt for part in parts for pt in part if len(pt) >= 2]
        if not points:
            return None, None

        try:
            from shapely.geometry import Polygon

            if geometry.get("rings"):
                # The first ring is the exterior; interior rings are holes and do
                # not move the representative point meaningfully here.
                centroid = Polygon(geometry["rings"][0]).centroid
                return centroid.x, centroid.y
        except Exception:
            # Degenerate or self-intersecting rings fall through to the mean below.
            pass

        return (
            sum(pt[0] for pt in points) / len(points),
            sum(pt[1] for pt in points) / len(points),
        )

    # -------------------------------------------------------------------- fetch

    def fetch_records(
        self,
        endpoint_url: str,
        where_clause: Optional[str] = None,
        order_by: str = "",
        limit: int = 1000,
        offset: int = 0,
        select: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch a single page of flattened records from an ArcGIS layer."""
        records, _ = self._fetch_page(
            endpoint_url=endpoint_url,
            where_clause=where_clause,
            order_by=order_by,
            limit=limit,
            offset=offset,
            select=select,
        )
        return records

    def _fetch_page(
        self,
        endpoint_url: str,
        where_clause: Optional[str],
        order_by: str,
        limit: int,
        offset: int,
        select: Optional[str] = None,
    ) -> tuple:
        """Fetch one page, returning ``(records, exceeded_transfer_limit)``."""
        layer_url = self._normalize_layer_url(endpoint_url)
        meta = self.get_layer_metadata(layer_url)

        # ArcGIS requires a where clause; "1=1" is the canonical match-everything.
        params: Dict[str, Any] = {
            "f": "json",
            "where": where_clause or "1=1",
            "outFields": select or "*",
            "resultOffset": offset,
            "resultRecordCount": min(limit, meta["max_record_count"]),
            "returnGeometry": "true" if self.return_geometry else "false",
            "outSR": 4326,
        }
        # Paging is only stable under a deterministic sort; the OID field is the
        # one column guaranteed to be present and unique.
        params["orderByFields"] = order_by or meta["oid_field"]

        payload = self._request_json(f"{layer_url}/query", params)
        features = payload.get("features") or []
        records = [self._flatten_feature(f, meta["date_fields"]) for f in features]
        return records, bool(payload.get("exceededTransferLimit"))

    def paginate(
        self,
        endpoint_url: str,
        where_clause: Optional[str] = None,
        order_by: str = "",
        batch_size: int = 1000,
        max_records: Optional[int] = None,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Paginate an ArcGIS layer, yielding batches of flattened records."""
        offset = 0
        total_fetched = 0

        while True:
            fetch_limit = batch_size
            if max_records and (total_fetched + fetch_limit > max_records):
                fetch_limit = max_records - total_fetched
            if fetch_limit <= 0:
                break

            records, exceeded = self._fetch_page(
                endpoint_url=endpoint_url,
                where_clause=where_clause,
                order_by=order_by,
                limit=fetch_limit,
                offset=offset,
            )

            if not records:
                break

            yield records
            total_fetched += len(records)
            offset += len(records)

            if max_records and total_fetched >= max_records:
                break
            # Unlike Socrata, a short page is not proof of exhaustion: the server
            # caps pages at maxRecordCount and flags the truncation instead.
            if not exceeded and len(records) < fetch_limit:
                break
