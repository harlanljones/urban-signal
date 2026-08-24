"""CKAN datastore client with retry backoff, pagination, and where-clause translation.

Mirrors :class:`~src.producers.socrata_client.SocrataClient` so it satisfies the
same ``PaginatingClient`` protocol the scheduler's ``poll_job`` uses
(``paginate(endpoint_url, where_clause, order_by, batch_size, max_records)``)
and is interchangeable with the Socrata/ArcGIS clients at producer call sites.

**Endpoint URI convention.** Callers pass ``ckan://<host>/<resource_id>`` —
e.g. ``ckan://data.boston.gov/6ddcd912-32a0-43df-9908-63574f8c7e77`` for Boston's
Approved Building Permits. The client parses this into
``https://<host>/api/3/action/datastore_search`` (or ``datastore_search_sql``
when a watermark-style range filter is needed) with ``resource_id=<id>``.
Optional query params on the URI are preserved as hints; the recognized one is:

* ``year_field`` — marks the resource set as year-sliced (see ``resolve_resource``).

**Where-clause translation.** The scheduler emits Socrata-ish plain SQL
fragments like ``issued_date > '2026-08-20T00:00:00'``, AND-combined. CKAN's
``filters`` parameter supports *exact-match only* — a range operator there is
rejected server-side ("Invalid query"; verified live against data.boston.gov).
So the client parses each ``<field> OP '<value>'`` term (OP ∈ =, !=, >, >=, <, <=):

* all-equality clauses → ``datastore_search`` + ``filters={"field": "value"}``
  (verified live: exact-match filters succeed);
* any clause containing a range/comparison operator → ``datastore_search_sql``
  with a quoted WHERE fragment (verified live: ``WHERE issued_date > '...'
  ORDER BY "_id" LIMIT n OFFSET m`` succeeds on Boston permits).

Anything unparseable is passed through to ``datastore_search_sql`` verbatim so
operators can hand-write richer SQL if needed.

**Paging & termination.** ``datastore_search`` pages via ``limit``/``offset``
and reports the row count in ``result.total`` — used to stop exactly at
exhaustion. ``datastore_search_sql`` honors LIMIT/OFFSET but returns no total,
so termination there is the sibling-standard short-page rule.

**Non-datastore resources are rejected explicitly.** A resource that is not
datastore-active (a file dump — PDF/CSV download) makes CKAN answer HTTP 200
with ``{"success": false, "error": {"__type": "Not Found Error", ...}}``.
The client raises a readable :class:`ValueError` naming the resource as a file
dump with no streaming path (San-Diego-style rejection), never an opaque error.

**Year-resource rollover.** Datasets like Boston 311 publish one resource per
calendar year. Construct with ``resource_by_year={"2026": "<res>", ...}`` and
an optional default ``resource_id``; ``resolve_resource(today)`` mirrors
:func:`src.spatial.city_registry.resolve_endpoint` semantics: newest year not
in the future, else the lexicographically latest entry.
"""

import json
import re
import time
from datetime import date
from typing import Any, Dict, Generator, List, Optional, Tuple
from urllib.parse import parse_qs, urlsplit

import httpx


class CkanError(RuntimeError):
    """A CKAN action call failed after retries or returned an API-level error."""


class NonDatastoreResourceError(ValueError):
    """The target resource is not datastore-active (file dump; no streaming path)."""


# A single Socrata-ish predicate: field OP 'value' (double-quoted values also OK).
_TERM_RE = re.compile(
    r"""^\s*(?P<field>"?[\w]+"?)\s*
        (?P<op>>=|<=|!=|<>|=|>|<)\s*
        (?P<value>'[^']*'|"[^"]*")\s*$""",
    re.VERBOSE,
)


def _parse_where_terms(where_clause: str) -> Optional[List[Tuple[str, str, str]]]:
    """Split an AND-combined where clause into ``(field, op, value)`` terms.

    Returns None when any part does not fit the simple grammar — callers then
    pass the clause through to ``datastore_search_sql`` verbatim.
    """
    parts = [p.strip() for p in re.split(r"\bAND\b", where_clause, flags=re.IGNORECASE) if p.strip()]
    terms = []
    for part in parts:
        m = _TERM_RE.match(part)
        if not m:
            return None
        value = m.group("value")[1:-1]
        op = "!=" if m.group("op") == "<>" else m.group("op")
        terms.append((m.group("field").strip('"'), op, value))
    return terms


class CkanClient:
    """Robust client for CKAN datastore endpoints (api/3/action)."""

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        max_retries: int = 4,
        api_key: Optional[str] = None,
        scheme: str = "https",
        resource_by_year: Optional[Dict[int, str]] = None,
    ):
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.api_key = api_key
        self.scheme = scheme
        self.resource_by_year = dict(resource_by_year or {})

    # ------------------------------------------------------------------ parsing

    @staticmethod
    def parse_endpoint(endpoint_url: str) -> Tuple[str, str, Dict[str, str]]:
        """Parse ``ckan://<host>/<resource_id>[?k=v...]`` → (action_base_url, resource_id, params).

        ``action_base_url`` is e.g. ``https://data.boston.gov/api/3/action``.
        """
        split = urlsplit(endpoint_url)
        if split.scheme != "ckan":
            raise ValueError(
                f"CkanClient expects a ckan:// URI of the form "
                f"'ckan://<host>/<resource_id>', got {endpoint_url!r}"
            )
        path = split.path.strip("/")
        if not split.netloc or not path:
            raise ValueError(
                f"CkanClient expects a ckan:// URI of the form "
                f"'ckan://<host>/<resource_id>', got {endpoint_url!r}"
            )
        resource_id = path.split("/")[0]
        params = {k: v[-1] for k, v in parse_qs(split.query).items()}
        base = f"{split.scheme}://{split.netloc}".replace("ckan://", "", 1)
        base_url = f"https://{base}" if "://" not in base else base
        return f"{base_url}/api/3/action", resource_id, params

    def resolve_resource(self, today: Optional[Any] = None) -> Optional[str]:
        """Resolve the current-year resource id from ``resource_by_year``.

        Mirrors ``city_registry.resolve_endpoint``: newest year not in the
        future, else the lexicographically latest entry. Returns None when no
        year map is configured.
        """
        if not self.resource_by_year:
            return None
        if today is None:
            today = date.today()
        year = getattr(today, "year", None)
        if year is None:
            year = int(str(today)[:4])
        for candidate in range(year, -1, -1):
            if candidate in self.resource_by_year:
                return self.resource_by_year[candidate]
        return self.resource_by_year[max(self.resource_by_year)]

    # ------------------------------------------------------------------ transport

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = self.api_key
        return headers

    def _request_json(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """GET a JSON payload with exponential backoff on 429/5xx/network errors."""
        backoff = 1.0
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, params=params, headers=self._headers())
                    if resp.status_code == 429 or resp.status_code >= 500:
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                    resp.raise_for_status()
                    payload = resp.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_err = e
                if attempt == self.max_retries:
                    raise CkanError(
                        f"Failed to fetch CKAN records after {attempt} attempts: {e}"
                    ) from e
                time.sleep(backoff)
                backoff *= 2.0
                continue

            # CKAN reports API-level failures in a 200 body.
            if isinstance(payload, dict) and payload.get("success") is False:
                err = payload.get("error") or {}
                message = err.get("message") if isinstance(err, dict) else None
                err_type = err.get("__type") if isinstance(err, dict) else None
                if err_type == "Not Found Error" and "Resource" in str(message):
                    raise NonDatastoreResourceError(
                        f"CKAN resource is not datastore-active — it is a file dump "
                        f"(PDF/CSV download) with no streaming path: {message}. "
                        f"Register a datastore-active resource instead."
                    )
                raise CkanError(f"CKAN API error ({err_type}): {message}")
            return payload
        raise CkanError(f"Failed to fetch CKAN records after {self.max_retries} attempts: {last_err}")

    # ------------------------------------------------------------------ fetching

    def fetch_records(
        self,
        endpoint_url: str,
        where_clause: Optional[str] = None,
        order_by: str = "_id",
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Fetch a single page of records, choosing search vs search_sql by clause shape."""
        action_base, resource_id, _uri_params = self.parse_endpoint(endpoint_url)
        if order_by == ":id":
            order_by = "_id"

        terms = _parse_where_terms(where_clause) if where_clause else []
        use_sql = (
            terms is None
            or any(op not in ("=",) for _, op, _ in terms)
        )

        if use_sql:
            sql = f'SELECT * FROM "{resource_id}"'
            if terms is None:
                sql += f" WHERE {where_clause}"
            elif terms:
                conds = [
                    f'"{field}" {"!=" if op == "!=" else op} \'{value}\''
                    for field, op, value in terms
                ]
                sql += " WHERE " + " AND ".join(conds)
            order = order_by or "_id"
            if not order.startswith('"'):
                order = ", ".join(f'"{c.strip()}"' for c in order.split(","))
            sql += f" ORDER BY {order} LIMIT {int(limit)} OFFSET {int(offset)}"
            payload = self._request_json(f"{action_base}/datastore_search_sql", {"sql": sql})
            return list(payload["result"]["records"])

        params: Dict[str, Any] = {
            "resource_id": resource_id,
            "limit": int(limit),
            "offset": int(offset),
        }
        if order_by and order_by != ":id":
            params["sort"] = order_by
        if terms:
            params["filters"] = json.dumps({f: v for f, _, v in terms})
        payload = self._request_json(f"{action_base}/datastore_search", params)
        return list(payload["result"]["records"])

    def _total_records(self, endpoint_url: str) -> Optional[int]:
        """Best-effort row count via a limit=0 datastore_search probe."""
        action_base, resource_id, _ = self.parse_endpoint(endpoint_url)
        try:
            payload = self._request_json(
                f"{action_base}/datastore_search",
                {"resource_id": resource_id, "limit": 0},
            )
            return int(payload["result"].get("total"))
        except (CkanError, KeyError, TypeError, ValueError):
            return None

    def paginate(
        self,
        endpoint_url: str,
        where_clause: Optional[str] = None,
        order_by: str = "_id",
        batch_size: int = 1000,
        max_records: Optional[int] = None,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Yield batches of records, terminating on exhaustion or max_records.

        ``order_by`` defaults to the datastore's stable ``_id`` key (the CKAN
        analogue of Socrata's ``:id``); a ``":id"`` passed by Socrata-shaped
        callers is normalized to it.
        """
        if order_by == ":id":
            order_by = "_id"
        total = None if where_clause else self._total_records(endpoint_url)
        offset = 0
        total_fetched = 0

        while True:
            fetch_limit = batch_size
            if max_records is not None and total_fetched + fetch_limit > max_records:
                fetch_limit = max_records - total_fetched
            if fetch_limit <= 0:
                break

            records = self.fetch_records(
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

            if max_records is not None and total_fetched >= max_records:
                break
            if total is not None and offset >= total:
                break
            if len(records) < fetch_limit:
                break
