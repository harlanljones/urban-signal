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
A layer whose ``dateFieldsTimeReference`` names a zone reads ``where`` literals
in that zone, so the metadata also carries it (``time_zone``).
"""

import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional
from urllib.parse import quote

import httpx

# Field types a ``where`` clause compares as numbers. A quoted literal against
# one of them fails on some servers: Roanoke's parcel layer answers
# ``lrsn IN ('1116')`` with "Invalid data type for expression".
_NUMERIC_FIELD_TYPES = frozenset(
    {
        "esriFieldTypeOID",
        "esriFieldTypeSmallInteger",
        "esriFieldTypeInteger",
        "esriFieldTypeBigInteger",
        "esriFieldTypeSingle",
        "esriFieldTypeDouble",
    }
)

# Servers older than 11.x name a layer's zone in Windows terms only; each reads
# with daylight saving or without it, as the reference says.
_WINDOWS_TIME_ZONES = {
    "Eastern Standard Time": ("America/New_York", "Etc/GMT+5"),
    "Central Standard Time": ("America/Chicago", "Etc/GMT+6"),
    "Mountain Standard Time": ("America/Denver", "Etc/GMT+7"),
    "US Mountain Standard Time": ("America/Phoenix", "America/Phoenix"),
    "Pacific Standard Time": ("America/Los_Angeles", "Etc/GMT+8"),
    "Alaskan Standard Time": ("America/Anchorage", "Etc/GMT+9"),
    "Hawaiian Standard Time": ("Pacific/Honolulu", "Pacific/Honolulu"),
}
_UTC_ZONE_NAMES = frozenset(
    {"UTC", "Etc/UTC", "Coordinated Universal Time", "GMT", "Etc/GMT", "Greenwich Standard Time"}
)


def layer_time_zone(reference: Any) -> str | None:
    """The IANA zone a layer's ``dateFieldsTimeReference`` reads literals in.

    None means UTC: no reference, or a UTC one. DC's 311 layer declares
    ``America/New_York`` and reads ``date '2026-09-29'`` as 04:00 UTC.
    """
    if not isinstance(reference, dict):
        return None
    zone = reference.get("timeZoneIANA")
    if not zone:
        name = reference.get("timeZone")
        zones = _WINDOWS_TIME_ZONES.get(name)
        if zones is None:
            zone = name
        else:
            zone = zones[0] if reference.get("respectsDaylightSaving", True) else zones[1]
    if not zone or zone in _UTC_ZONE_NAMES:
        return None
    return zone


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
        # layer_url -> {"date_fields": set[str], "numeric_fields": set[str],
        #               "oid_field": str, "max_record_count": int, "time_zone": str | None}
        self._layer_meta: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _normalize_layer_url(endpoint_url: str) -> str:
        """Strip a trailing ``/query`` so callers may pass either form."""
        return endpoint_url.rstrip("/").removesuffix("/query")

    # ArcGIS Online and other IIS-fronted servers answer 404 to a GET whose
    # URL passes about 2,000 characters; Esri's own clients send such a query
    # as a POST, which every query operation accepts.
    _MAX_GET_URL = 2_000

    def _request_json(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """GET a JSON payload with exponential backoff, raising on ArcGIS error bodies.

        A query too long for a GET URL (a text watermark's list of dates) is
        POSTed as a form instead.
        """
        long_query = len(str(httpx.URL(url, params=params))) > self._MAX_GET_URL
        backoff = 1.0
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, data=params) if long_query else client.get(url, params=params)
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
        """Fetch and cache a layer's field types, OID field, page cap and time zone."""
        layer_url = self._normalize_layer_url(endpoint_url)
        if layer_url in self._layer_meta:
            return self._layer_meta[layer_url]

        payload = self._request_json(layer_url, {"f": "json"})
        fields = payload.get("fields") or []
        meta = {
            "date_fields": {
                f["name"] for f in fields if f.get("type") == "esriFieldTypeDate"
            },
            "numeric_fields": {
                f["name"] for f in fields if f.get("type") in _NUMERIC_FIELD_TYPES
            },
            "oid_field": payload.get("objectIdField") or "OBJECTID",
            "max_record_count": int(payload.get("maxRecordCount") or 1000),
            "time_zone": layer_time_zone(payload.get("dateFieldsTimeReference")),
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

    @staticmethod
    def _normalize_join_value(value: Any) -> str:
        """Normalize a parcel join key without changing its meaningful digits."""
        if isinstance(value, float) and value.is_integer():
            # A Double key column reads 1116.0 where an Integer one reads 1116.
            value = int(value)
        return " ".join(str(value or "").split()).upper()

    @staticmethod
    def _numeric_literal(value: Any) -> str | None:
        """A value as an unquoted number for a numeric ``IN``, or None if it is not one."""
        try:
            number = float(str(value).strip())
        except (TypeError, ValueError):
            return None
        if not math.isfinite(number):
            return None
        return str(int(number)) if number.is_integer() else repr(number)

    def fetch_centroid_index(
        self,
        endpoint_url: str,
        join_key: str,
        join_values: Optional[List[Any]] = None,
        batch_size: int = 1000,
        max_records: Optional[int] = None,
    ) -> Dict[str, tuple[float, float]]:
        """Fetch parcel polygons and return a normalized key-to-centroid index.

        When ``join_values`` is supplied, query only those parcels using bounded
        ``IN`` clauses. This keeps a CAMA deed run proportional to its sales
        page instead of downloading the entire parcel layer on every cycle.
        ``_fetch_page`` requests geometry and reduces each polygon to WGS84
        centroid coordinates before this method builds the lookup. Geometry is
        requested through ``returnGeometry``; it is not an attribute field in
        the ``outFields`` selection.
        """
        layer_url = self._normalize_layer_url(endpoint_url)
        values = list(join_values) if join_values is not None else None
        if values is not None:
            unique_values = []
            seen = set()
            for value in values:
                normalized = self._normalize_join_value(value)
                if normalized and normalized not in seen:
                    unique_values.append(str(value))
                    seen.add(normalized)
            values = unique_values
        if values == []:
            return {}

        index: Dict[str, tuple[float, float]] = {}
        fetched = 0

        def consume(records: List[Dict[str, Any]]) -> None:
            nonlocal fetched
            for record in records:
                key = self._normalize_join_value(record.get(join_key))
                lat = record.get("latitude")
                lng = record.get("longitude")
                if not key or lat is None or lng is None:
                    continue
                try:
                    index[key] = (float(lat), float(lng))
                except (TypeError, ValueError):
                    continue
                fetched += 1

        if values is None:
            offset = 0
            while True:
                fetch_limit = batch_size
                if max_records is not None:
                    fetch_limit = min(fetch_limit, max_records - fetched)
                if fetch_limit <= 0:
                    break
                records, exceeded = self._fetch_page(
                    endpoint_url=layer_url,
                    where_clause=None,
                    order_by="",
                    limit=fetch_limit,
                    offset=offset,
                    select=join_key,
                )
                if not records:
                    break
                before = fetched
                consume(records)
                offset += len(records)
                if max_records is not None and fetched >= max_records:
                    break
                if not exceeded and len(records) < fetch_limit:
                    break
                if fetched == before and len(records) == 0:
                    break
            return index

        # A text key takes quoted literals and a numeric key bare numbers.
        numeric = join_key in self.get_layer_metadata(layer_url).get("numeric_fields", ())
        if numeric:
            literals = [lit for lit in map(self._numeric_literal, values) if lit is not None]
        else:
            literals = ["'" + value.replace("'", "''") + "'" for value in values]
        for where in self._in_clauses(join_key, literals):
            offset = 0
            while True:
                fetch_limit = batch_size
                if max_records is not None:
                    fetch_limit = min(fetch_limit, max_records - fetched)
                if fetch_limit <= 0:
                    return index
                records, exceeded = self._fetch_page(
                    endpoint_url=layer_url,
                    where_clause=where,
                    order_by="",
                    limit=fetch_limit,
                    offset=offset,
                    select=join_key,
                )
                if not records:
                    break
                consume(records)
                offset += len(records)
                if max_records is not None and fetched >= max_records:
                    return index
                if not exceeded and len(records) < fetch_limit:
                    break
        return index

    # Keep each IN request well below URL limits: Richmond's ArcGIS Online host
    # answers 404 to a query URL past about 2,000 characters, which 100 quoted
    # 11-character parcel ids exceed.
    _IN_MAX_VALUES = 100
    _IN_MAX_ENCODED = 1_400

    @classmethod
    def _in_clauses(cls, join_key: str, literals: List[str]) -> Generator[str, None, None]:
        """``join_key IN (...)`` clauses over ``literals``, each within the limits."""
        chunk: List[str] = []
        size = len(quote(f"{join_key} IN ()"))
        for literal in literals:
            cost = len(quote(literal)) + 3  # the literal and its encoded comma
            if chunk and (len(chunk) >= cls._IN_MAX_VALUES or size + cost > cls._IN_MAX_ENCODED):
                yield f"{join_key} IN ({','.join(chunk)})"
                chunk, size = [], len(quote(f"{join_key} IN ()"))
            chunk.append(literal)
            size += cost
        if chunk:
            yield f"{join_key} IN ({','.join(chunk)})"

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
        if "features" not in payload:
            # A service root (``.../FeatureServer``) answers /query at HTTP 200
            # with its own description, ``{"layers": [...]}``. Read as an empty
            # page, that let five feeds report SUCCESS with zero rows.
            hint = " (a service root: the endpoint needs a layer index)" if "layers" in payload else ""
            raise RuntimeError(
                f"ArcGIS query on {layer_url} returned no features{hint}; keys: {sorted(payload)}"
            )
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
        select: Optional[str] = None,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Paginate an ArcGIS layer, yielding batches of flattened records.

        ``select`` is a comma-separated field list sent as ``outFields``, so a
        layer's owner and buyer columns can stay on the server; without it
        every column is read.
        """
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
                select=select,
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
