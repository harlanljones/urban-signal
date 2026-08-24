"""Socrata SODA API client with retry backoff, pagination, and query filtering."""

import time
from typing import Any, Dict, Generator, List, Optional
import httpx
from src.config import settings


class SocrataClient:
    """Robust client for municipal Socrata SODA OpenData endpoints."""

    def __init__(
        self,
        app_token: Optional[str] = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 4,
    ):
        self.app_token = app_token or settings.socrata_app_token
        self.timeout = timeout_seconds
        self.max_retries = max_retries

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.app_token:
            headers["X-App-Token"] = self.app_token
        return headers

    def fetch_records(
        self,
        endpoint_url: str,
        where_clause: Optional[str] = None,
        order_by: str = ":id",
        limit: int = 1000,
        offset: int = 0,
        select: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch a single page of records from Socrata SODA endpoint with exponential backoff."""
        params: Dict[str, Any] = {
            "$limit": limit,
            "$offset": offset,
            "$order": order_by,
        }
        if where_clause:
            params["$where"] = where_clause
        if select:
            params["$select"] = select

        headers = self._get_headers()
        backoff = 1.0

        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(endpoint_url, params=params, headers=headers)
                    if resp.status_code == 200:
                        return resp.json()
                    elif resp.status_code == 429:
                        # Rate limit hit - backoff
                        time.sleep(backoff)
                        backoff *= 2.0
                    else:
                        resp.raise_for_status()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                if attempt == self.max_retries:
                    raise RuntimeError(f"Failed to fetch Socrata records after {attempt} attempts: {e}") from e
                time.sleep(backoff)
                backoff *= 2.0

        return []

    def paginate(
        self,
        endpoint_url: str,
        where_clause: Optional[str] = None,
        order_by: str = ":id",
        batch_size: int = 1000,
        max_records: Optional[int] = None,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Paginates through Socrata datasets yielding batches of records."""
        offset = 0
        total_fetched = 0

        while True:
            fetch_limit = batch_size
            if max_records and (total_fetched + fetch_limit > max_records):
                fetch_limit = max_records - total_fetched

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

            if max_records and total_fetched >= max_records:
                break
            if len(records) < fetch_limit:
                # Last page reached
                break
