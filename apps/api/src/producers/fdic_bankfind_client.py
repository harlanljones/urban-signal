"""Keyed REST client for the FDIC BankFind API (US-379)."""

from __future__ import annotations

from typing import Any

import httpx

FDIC_MAX_PAGE_SIZE = 10000


def _upper_key(key):
    return str(key).strip().upper()


class FdicBankFindClient:
    """Offset pagination over api.fdic.gov/banks/{locations,sod,history}."""

    def __init__(self, base_url="https://api.fdic.gov/banks", page_size=FDIC_MAX_PAGE_SIZE,
                 timeout_seconds=60):
        self.base_url = base_url.rstrip("/")
        self.page_size = max(1, min(page_size, FDIC_MAX_PAGE_SIZE))
        self.timeout = timeout_seconds

    @staticmethod
    def rows(payload):
        data = payload.get("data")
        return [entry["data"] for entry in data] if isinstance(data, list) else []

    @staticmethod
    def total(payload):
        for source in (payload.get("meta"), payload.get("totals")):
            if isinstance(source, dict):
                val = source.get("total") or source.get("count")
                if isinstance(val, int):
                    return val
        return 0

    @staticmethod
    def normalize_row(row):
        return {str(k).strip().upper(): v for k, v in row.items()}

    @staticmethod
    def field(row, name, default=None):
        """Case-insensitive field access with alias candidates."""
        lowered = row.get(name)
        if lowered is not None:
            return lowered
        upper = name.upper()
        if upper in row:
            return row[upper]
        return default

    def _get(self, endpoint, params=None):
        url = endpoint if str(endpoint).startswith("http") else f"{self.base_url}/{endpoint}"
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    def paginate(self, endpoint, filters=None, fields=None, sort_by=None,
                 sort_order=None, max_records=None):
        """Yield normalized (uppercase-keyed) row batches, one server page each."""
        offset = 0
        fetched = 0
        while True:
            limit = self.page_size if max_records is None else min(self.page_size, max_records - fetched)
            if limit <= 0:
                return
            params = {"limit": limit, "offset": offset, "format": "json"}
            if fields:
                params["fields"] = ",".join(fields)
            if sort_by:
                params["sort_by"] = sort_by
            if sort_order:
                params["sort_order"] = sort_order
            payload = self._get(endpoint, params=params)
            page = self.rows(payload)
            if not page:
                return
            yield [self.normalize_row(row) for row in page]
            fetched += len(page)
            offset += len(page)
            if len(page) < limit:
                return
