"""Small keyed REST client for NREL AFDC station snapshots (US-363 §1.5)."""

from __future__ import annotations

from typing import Any


class NrelAfdcClient:
    def __init__(self, api_key: str | None = None, page_size: int = 1000, timeout_seconds: float = 60.0):
        from src.config import settings

        self.api_key = api_key or settings.nrel_api_key
        self.page_size = max(1, min(page_size, 2000))
        self.timeout = timeout_seconds

    @staticmethod
    def rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows = payload.get("fuel_stations")
        return rows if isinstance(rows, list) else []

    @staticmethod
    def diff(previous: dict[str, dict[str, Any]], current: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [row for station_id, row in current.items() if station_id not in previous]

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        import httpx

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()

    def paginate(self, endpoint: str, fuel_type_code: str = "ELEC", max_records: int | None = None):
        offset = 0
        fetched = 0
        while True:
            limit = self.page_size if max_records is None else min(self.page_size, max_records - fetched)
            if limit <= 0:
                return
            payload = self._get(endpoint, {"api_key": self.api_key, "fuel_type_code": fuel_type_code, "limit": limit, "offset": offset})
            page = self.rows(payload)
            if not page:
                return
            yield page
            fetched += len(page)
            offset += len(page)
            if len(page) < limit:
                return
