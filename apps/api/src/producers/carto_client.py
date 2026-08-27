"""CARTO SQL API client with retry backoff, keyset pagination, and sentinel-date filtering.

Mirrors :class:`~src.producers.socrata_client.SocrataClient` and
:class:`~src.producers.arcgis_client.ArcGISClient` so all three satisfy the same
``PaginatingClient`` protocol in :mod:`src.spatial.city_registry` and are
interchangeable at the producer call sites.

Design decisions specific to CARTO:

* **Endpoint identity.** A CARTO dataset lives at ``(domain, table)`` — e.g.
  ``("phl.carto.com", "permits")``. The protocol passes a single ``endpoint_url``
  string, so this client accepts three equivalent spellings:

  - ``carto://<domain>/<table>``  (URI form, preferred: self-contained)
    e.g. ``carto://phl.carto.com/permits``
  - ``https://<domain>[/api/v2/sql]`` (base/domain URL form; pass ``table=``)
  - ``<domain>`` (bare domain; pass ``table=``)

  In all cases requests go to ``GET {scheme}://{domain}/api/v2/sql?q=...``.

* **Keyset paging, never OFFSET.** Philadelphia's largest tables mutate mid-scan,
  so OFFSET paging silently skips or repeats rows. Each page continues from the
  last-seen keyset tuple::

      WHERE (order_col, id_col) > (<last_order_value>, <last_id>)
      ORDER BY order_col ASC, id_col ASC LIMIT n

  The tie-breaker ``id_col`` defaults to ``cartodb_id``, which every CARTO table
  carries. Callers override per-table columns via kwargs (a future Philadelphia
  registration carries them through ``DatasetSpec``, e.g.
  ``order_by="permitissuedate", id_col="cartodb_id"``).

* **Sentinel dates.** Several Philly tables contain impossible years (3200,
  9798) in their issue/document date columns, and NULLs are common. Both break
  keyset ordering on a date column, so when the order column looks like a date
  (name contains ``date``) the client emits, unless told otherwise::

      <col> IS NOT NULL AND <col> >= '1900-01-01' AND <col> < '2101-01-01'

  This exact text is applied to every page's WHERE clause so the keyset cursor
  and the caller's watermark see the same filtered window. Pass
  ``exclude_sentinel_dates=False`` to disable (e.g. non-date order columns).

* **Auth.** The CARTO SQL API used here is anonymous — no secrets exist, hence
  nothing secret can be logged.
"""

import logging
import time
from typing import Any, Dict, Generator, List, Optional

import httpx

logger = logging.getLogger(__name__)

SQL_API_PATH = "/api/v2/sql"


class CartoClient:
    """Robust client for municipal CARTO SQL API endpoints (e.g. phl.carto.com)."""

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        max_retries: int = 4,
        id_col: str = "cartodb_id",
    ):
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.id_col = id_col

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _parse_endpoint(endpoint_url: str, table: Optional[str]) -> tuple:
        """Resolve an endpoint spelling into ``(sql_api_base_url, table_name)``."""
        if endpoint_url.startswith("carto://"):
            rest = endpoint_url[len("carto://"):]
            domain, _, uri_table = rest.partition("/")
            if not domain or not uri_table:
                raise ValueError(
                    f"carto:// endpoint must be carto://<domain>/<table>, got {endpoint_url!r}"
                )
            if table and table != uri_table:
                raise ValueError(
                    f"Conflicting tables: {table!r} vs URI's {uri_table!r}"
                )
            return f"https://{domain}{SQL_API_PATH}", uri_table

        if endpoint_url.startswith(("http://", "https://")):
            # Accept either a bare origin or an already-resolved SQL path.
            base = endpoint_url.rstrip("/")
            for suffix in ("/api/v2/sql", "/api/v2/sql/"):
                if base.endswith(suffix):
                    base = base[: -len(suffix)]
                    break
            if not table:
                raise ValueError(
                    f"CARTO table name required when endpoint_url has no "
                    f"'carto://' prefix: {endpoint_url!r}"
                )
            return f"{base}{SQL_API_PATH}", table

        # Bare domain form.
        domain = endpoint_url.rstrip("/")
        if not table:
            raise ValueError(
                f"CARTO table name required when endpoint_url is a bare domain: "
                f"{endpoint_url!r}"
            )
        return f"https://{domain}{SQL_API_PATH}", table

    @staticmethod
    def _quote(value: Any) -> str:
        """Quote a literal for the SQL keyset predicate (single-quote escaping)."""
        return "'" + str(value).replace("'", "''") + "'"

    @staticmethod
    def _looks_like_date_column(column: str) -> bool:
        return "date" in column.lower()

    def _sentinel_filter(self, order_col: str, exclude_sentinel_dates: Optional[bool]) -> Optional[str]:
        """WHERE fragment excluding NULLs and impossible years on a date order column.

        Emits exactly::

            <col> IS NOT NULL AND <col> >= '1900-01-01' AND <col> < '2101-01-01'

        ISO-timestamp strings compare correctly lexicographically against these
        bounds, which keeps the filter index-friendly and avoids timestamp casts.
        """
        if exclude_sentinel_dates is None:
            exclude_sentinel_dates = self._looks_like_date_column(order_col)
        if not exclude_sentinel_dates:
            return None
        return (
            f"{order_col} IS NOT NULL "
            f"AND {order_col} >= '1900-01-01' AND {order_col} < '2101-01-01'"
        )

    def _build_query(
        self,
        table: str,
        order_col: str,
        id_col: str,
        direction: str,
        where_clause: Optional[str],
        limit: int,
        last_keyset: Optional[tuple],
        select: Optional[str] = None,
    ) -> str:
        parts = [f"({order_col} IS NOT NULL)"]
        if where_clause:
            parts.append(f"({where_clause})")
        if last_keyset is not None:
            last_order, last_id = last_keyset
            comparator = "<" if direction == "DESC" else ">"
            parts.append(
                f"({order_col}, {id_col}) {comparator} ({self._quote(last_order)}, "
                f"{self._quote(last_id)})"
            )

        where_sql = " AND ".join(parts)
        select_sql = select or "*"
        return (
            f"SELECT {select_sql} FROM {table} WHERE {where_sql} "
            f"ORDER BY {order_col} {direction}, {id_col} {direction} LIMIT {limit}"
        )

    def _request_json(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """GET a JSON payload with exponential backoff on 429/5xx and network errors."""
        backoff = 1.0
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, params=params)
                    if resp.status_code == 429:
                        logger.warning(
                            "CARTO rate limited (attempt %d/%d); backing off %.1fs",
                            attempt, self.max_retries, backoff,
                        )
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                    resp.raise_for_status()
                    return resp.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code if e.response is not None else None
                if status is not None and 500 <= status < 600 and attempt < self.max_retries:
                    logger.warning(
                        "CARTO %d server error (attempt %d/%d); backing off %.1fs",
                        status, attempt, self.max_retries, backoff,
                    )
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise RuntimeError(
                    f"Failed to fetch CARTO records after {attempt} attempts: {e}"
                ) from e
            except httpx.RequestError as e:
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Failed to fetch CARTO records after {attempt} attempts: {e}"
                    ) from e
                time.sleep(backoff)
                backoff *= 2.0

        raise RuntimeError(f"Failed to fetch CARTO records after {self.max_retries} attempts")

    def _fetch_rows(
        self,
        sql_api_url: str,
        q: str,
    ) -> List[Dict[str, Any]]:
        """Execute one SQL-API query, returning its flat row dicts.

        Tolerates malformed responses: a missing/non-dict ``rows`` array yields [],
        and non-dict entries inside the array are dropped rather than crashing the
        whole scan.
        """
        payload = self._request_json(sql_api_url, {"q": q})
        rows = payload.get("rows") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            logger.warning("CARTO response missing 'rows' array for query: %s", q)
            return []
        return [row for row in rows if isinstance(row, dict)]

    # -------------------------------------------------------------------- fetch

    def fetch_records(
        self,
        endpoint_url: str,
        table: Optional[str] = None,
        where_clause: Optional[str] = None,
        order_by: str = "",
        batch_size: int = 1000,
        max_records: Optional[int] = None,
        select: Optional[str] = None,
        id_col: Optional[str] = None,
        exclude_sentinel_dates: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch the first page of records from a CARTO table."""
        gen = self.paginate(
            endpoint_url=endpoint_url,
            table=table,
            where_clause=where_clause,
            order_by=order_by,
            batch_size=batch_size,
            max_records=max_records,
            select=select,
            id_col=id_col,
            exclude_sentinel_dates=exclude_sentinel_dates,
        )
        try:
            return next(gen)
        except StopIteration:
            return []

    def paginate(
        self,
        endpoint_url: str,
        table: Optional[str] = None,
        where_clause: Optional[str] = None,
        order_by: str = "",
        batch_size: int = 1000,
        max_records: Optional[int] = None,
        select: Optional[str] = None,
        id_col: Optional[str] = None,
        exclude_sentinel_dates: Optional[bool] = None,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Paginate a CARTO table via keyset paging, yielding batches of flat row dicts.

        ``order_by`` defaults to ``updated_at`` when unset (the most common
        mutation-tracking column); Philadelphia registrations should carry the
        real per-table column through ``DatasetSpec``. Sentinel filtering
        auto-enables for date-named order columns (see module docstring).
        """
        sql_api_url, resolved_table = self._parse_endpoint(endpoint_url, table)
        order_spec = (order_by or "updated_at").strip()
        order_parts = order_spec.rsplit(None, 1)
        if len(order_parts) == 2 and order_parts[1].upper() in {"ASC", "DESC"}:
            order_col, direction = order_parts[0], order_parts[1].upper()
        else:
            order_col, direction = order_spec, "ASC"
        id_column = id_col or self.id_col

        total_fetched = 0
        last_keyset: Optional[tuple] = None

        while True:
            fetch_limit = batch_size
            if max_records and (total_fetched + fetch_limit > max_records):
                fetch_limit = max_records - total_fetched
            if fetch_limit <= 0:
                break

            q = self._build_query(
                table=resolved_table,
                order_col=order_col,
                id_col=id_column,
                direction=direction,
                where_clause=self._join_where(where_clause, order_col, exclude_sentinel_dates),
                limit=fetch_limit,
                last_keyset=last_keyset,
                select=select,
            )
            records = self._fetch_rows(sql_api_url, q)

            if not records:
                break

            yield records
            total_fetched += len(records)

            # Advance the keyset cursor from the final row of the page.
            tail = records[-1]
            last_keyset = (tail.get(order_col), tail.get(id_column))

            if max_records and total_fetched >= max_records:
                break
            if len(records) < fetch_limit:
                break

    def _join_where(
        self,
        where_clause: Optional[str],
        order_col: str,
        exclude_sentinel_dates: Optional[bool],
    ) -> Optional[str]:
        """Combine caller WHERE with the sentinel filter (exact text documented)."""
        fragments = []
        if where_clause:
            fragments.append(where_clause)
        sentinel = self._sentinel_filter(order_col, exclude_sentinel_dates)
        if sentinel:
            fragments.append(sentinel)
        return " AND ".join(fragments) if fragments else None
