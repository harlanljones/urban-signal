"""Excel workbook client for static municipal XLS/XLSX feeds."""

from __future__ import annotations

import re
from collections.abc import Generator
from io import BytesIO
from typing import Any

import httpx
import pandas as pd

from src.producers.csv_client import _row_matches


def _normalize_column(name: Any) -> str:
    """Normalize spreadsheet headers to the identifier form used by field maps."""
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


class ExcelClient:
    """Download a workbook once, normalize rows, and yield filtered batches."""

    def __init__(self, http_client: httpx.Client | None = None):
        self.http = http_client or httpx.Client(timeout=180.0, follow_redirects=True)

    def paginate(
        self,
        endpoint_url: str,
        where_clause: str | None = None,
        order_by: str = "",
        batch_size: int = 1000,
        max_records: int | None = None,
        select: str | None = None,
        id_col: str | None = None,
        fallback_endpoints: list[str] | None = None,
        **kwargs: Any,
    ) -> Generator[list[dict[str, Any]], None, None]:
        del id_col, kwargs
        response = self.http.get(endpoint_url)
        response.raise_for_status()
        frame = pd.read_excel(BytesIO(response.content), engine="xlrd")
        frame = frame.rename(columns={column: _normalize_column(column) for column in frame.columns})
        frame = frame.where(pd.notna(frame), None)

        selected_cols = (
            [_normalize_column(column) for column in select.split(",") if column.strip()]
            if select
            else None
        )
        rows = frame.to_dict(orient="records")
        rows = [row for row in rows if _row_matches(_normalize_where(where_clause), row)]
        if selected_cols:
            rows = [{key: row[key] for key in selected_cols if key in row} for row in rows]

        if order_by:
            match = re.match(
                r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(ASC|DESC)?\s*$",
                order_by,
                re.IGNORECASE,
            )
            column = _normalize_column(match.group(1) if match else order_by)
            reverse = bool(match and match.group(2) and match.group(2).upper() == "DESC")
            rows.sort(key=lambda row: str(row.get(column) or ""), reverse=reverse)

        batch: list[dict[str, Any]] = []
        for total, row in enumerate(rows, start=1):
            batch.append(row)
            if len(batch) >= batch_size:
                yield batch
                batch = []
            if max_records and total >= max_records:
                break
        if batch:
            yield batch


def _normalize_where(where_clause: str | None) -> str | None:
    """Normalize simple scheduler predicates to the spreadsheet header form."""
    if not where_clause:
        return None
    return re.sub(r"\b([A-Za-z][A-Za-z0-9 ]*)\b(?=\s*(?:>=|<=|!=|=|>|<))", lambda m: _normalize_column(m.group(1)), where_clause)
