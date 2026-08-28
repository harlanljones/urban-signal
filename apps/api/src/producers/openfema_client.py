"""OpenFemaClient — thin OData paginator over the FEMA open API (US-363 §1.4).

The closest of the four new components to an existing archetype: it satisfies
the ``PaginatingClient`` protocol so the shared machinery can drive it, with
OData's ``$top``/``$skip``/``$filter``/``$orderby`` standing in for Socrata's
``$limit``/``$offset``.

Verified live 2026-08-28 against ``NfipClaims`` **v3**:

    $inlinecount=allpages&$top=2&$select=id,dateOfLoss,state,censusGeoid
      &$filter=state eq 'NY' and dateOfLoss ge '2024-01-01'&$orderby=dateOfLoss
    -> metadata.count 1443, rows ordered ascending

Two version facts that are load-bearing:

* ``NfipClaims`` is **v3**. The v2 entity ``FimaNfipClaims`` is deprecated —
  frozen 2026-06-01, removal 2026-10-15 — and must never be built on.
* ``DisasterDeclarationsSummaries`` is **v2 only**; the v3 path 404s.

Rows come back under a key named after the entity (``{"metadata": {...},
"NfipClaims": [...]}``), which the client derives from the endpoint rather
than hard-coding, so a new entity needs no code change.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 1000
# OpenFEMA's documented ceiling per request.
MAX_PAGE_SIZE = 10000


class OpenFemaClient:
    """Paginates an OpenFEMA OData entity."""

    def __init__(self, timeout_seconds: float = 60.0, max_retries: int = 4):
        self.timeout = timeout_seconds
        self.max_retries = max_retries

    @staticmethod
    def entity_name(endpoint_url: str) -> str:
        """Derive the response key from the endpoint path.

        ``.../api/open/v3/NfipClaims`` -> ``NfipClaims``. Deriving it beats a
        lookup table: a new entity is then a config line, not a code change.
        """
        return endpoint_url.rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0]

    def _get(self, endpoint_url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        import httpx

        backoff = 1.0
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                    resp = client.get(
                        endpoint_url, params=params, headers={"Accept": "application/json"}
                    )
                    if resp.status_code == 200:
                        return resp.json()
                    if resp.status_code in (429, 503):
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                    resp.raise_for_status()
            except Exception as exc:
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"OpenFEMA request failed after {attempt} attempts: {exc}"
                    ) from exc
                time.sleep(backoff)
                backoff *= 2.0
        return {}

    def count(self, endpoint_url: str, where_clause: Optional[str] = None) -> int:
        """Row count for a filter, from ``metadata.count``."""
        params: Dict[str, Any] = {"$inlinecount": "allpages", "$top": 1}
        if where_clause:
            params["$filter"] = where_clause
        payload = self._get(endpoint_url, params)
        return int((payload.get("metadata") or {}).get("count") or 0)

    def paginate(
        self,
        endpoint_url: str,
        where_clause: Optional[str] = None,
        order_by: str = "id",
        batch_size: int = DEFAULT_PAGE_SIZE,
        max_records: Optional[int] = None,
        select: Optional[str] = None,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Yield batches of rows.

        ``order_by`` defaults to ``id`` rather than being left unset: OData
        paging by ``$skip`` over an unordered result is not stable, and a
        silently reshuffled page drops and duplicates rows.
        """
        key = self.entity_name(endpoint_url)
        page = min(max(int(batch_size), 1), MAX_PAGE_SIZE)
        skip = 0
        fetched = 0

        while True:
            take = page
            if max_records is not None:
                remaining = max_records - fetched
                if remaining <= 0:
                    return
                take = min(take, remaining)

            params: Dict[str, Any] = {"$top": take, "$skip": skip}
            if order_by:
                params["$orderby"] = order_by
            if where_clause:
                params["$filter"] = where_clause
            if select:
                params["$select"] = select

            payload = self._get(endpoint_url, params)
            rows = payload.get(key)
            if not isinstance(rows, list) or not rows:
                return

            yield rows
            fetched += len(rows)
            skip += len(rows)
            if len(rows) < take:
                return


def odata_date_filter(column: str, since: Any) -> str:
    """Build ``<column> ge '<iso date>'``.

    OpenFEMA compares dates as quoted ISO strings; an unquoted literal is a
    400. Accepts a date, datetime or ISO string.
    """
    text = getattr(since, "isoformat", lambda: str(since))()
    return f"{column} ge '{text[:10]}'"
