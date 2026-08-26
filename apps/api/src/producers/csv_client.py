"""CSVClient: ingest flat open-data CSV files (San Diego, US-91).

Static-CSV portals (``seshat.datasd.org``) publish no Socrata/ArcGIS/CARTO/CKAN
API — the file is the feed. This leaf client downloads the file once and applies
watermark filtering client-side, matching the ``paginate(...)`` generator
interface the scheduler and producers expect.

The endpoint is a year-scoped file (``approvals_issued_2026_datasd.csv``), so
the server-side watermark predicate the scheduler renders (``col > '<hw>'``) is
evaluated locally against the ISO date strings in the downloaded rows.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Generator
from typing import Any, Dict, List, Optional

import httpx

_CMP = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(>=|<=|>|<|=|!=)\s*'([^']*)'\s*$")
_IS_NULL = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+is\s+not\s+null\s*$", re.IGNORECASE)


def _row_matches(where_clause: str | None, row: Dict[str, Any]) -> bool:
    """Client-side predicate over one parsed row (ANSI/SODA-style clauses)."""
    if not where_clause:
        return True
    for part in where_clause.split(" AND "):
        # The scheduler wraps base_where / the job where clause in parentheses
        # before joining, so a bare predicate arrives as "(valid = 'Y')".
        part = part.strip()
        if len(part) >= 2 and part.startswith("(") and part.endswith(")"):
            part = part[1:-1].strip()
        m = _CMP.match(part)
        if m:
            col, op, literal = m.group(1), m.group(2), m.group(3)
            value = row.get(col)
            if value is None:
                return False
            s = str(value).strip()
            if op == ">":
                if not s > literal:
                    return False
            elif op == ">=":
                if not s >= literal:
                    return False
            elif op == "<":
                if not s < literal:
                    return False
            elif op == "<=":
                if not s <= literal:
                    return False
            elif op == "=":
                if not s == literal:
                    return False
            elif op == "!=":
                if not s != literal:
                    return False
        else:
            m2 = _IS_NULL.match(part)
            if m2 and row.get(m2.group(1)) in (None, ""):
                return False
    return True


class CSVClient:
    """Download-and-filter client for static CSV feeds."""

    def __init__(self, http_client: Optional[httpx.Client] = None):
        self.http = http_client or httpx.Client(timeout=180.0, follow_redirects=True)

    def paginate(
        self,
        endpoint_url: str,
        where_clause: Optional[str] = None,
        order_by: str = "",
        batch_size: int = 1000,
        max_records: Optional[int] = None,
        select: Optional[str] = None,
        id_col: Optional[str] = None,
        **kwargs: Any,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Download the CSV once and yield batches of filtered rows."""
        response = self.http.get(endpoint_url)
        response.raise_for_status()

        reader = csv.DictReader(io.StringIO(response.text))
        # Municipal CSVs ship UPPERCASE headers; normalize so field maps and
        # the shared parser fallback chains (all lowercase) apply uniformly.
        if reader.fieldnames:
            reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
        selected_cols = (
            [c.strip().lower() for c in select.split(",") if c.strip()] if select else None
        )

        rows: List[Dict[str, Any]] = []
        for row in reader:
            if not _row_matches(where_clause, row):
                continue
            if selected_cols:
                row = {k: row[k] for k in selected_cols if k in row}
            rows.append(row)

        if order_by:
            m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(ASC|DESC)?\s*$", order_by, re.IGNORECASE)
            col = m.group(1).lower() if m else order_by.strip().lower()
            if m and m.group(2) and m.group(2).upper() == "DESC":
                rows.sort(key=lambda r: str(r.get(col, "")), reverse=True)
            else:
                rows.sort(key=lambda r: str(r.get(col, "")))

        total = 0
        batch: List[Dict[str, Any]] = []
        for row in rows:
            batch.append(row)
            total += 1
            if len(batch) >= batch_size:
                yield batch
                batch = []
            if max_records and total >= max_records:
                break
        if batch:
            yield batch