"""Excel workbook client for static municipal XLS/XLSX feeds.

The client filters, orders and caps a workbook's rows itself, as the CSV
client does a file's. A spec whose watermark column holds dates as text
(MyGov's report workbooks write ``09/30/2026`` and ``08/31/2026 at 4:31
PM``) declares their format, and the client compares and sorts that column
as dates: as text, ``01/05/2027`` sorts below ``09/30/2026``. A
``point_col`` holding each row's point as one ``lat, lon`` value, or ``lon,
lat`` with ``point_lon_first``, gives the row its ``latitude`` and
``longitude``.
"""

from __future__ import annotations

import html
import re
from collections.abc import Generator, Iterator
from datetime import datetime
from io import BytesIO
from typing import Any
from urllib.parse import urljoin

import httpx
import pandas as pd

from src.producers.csv_client import (
    _row_matches,
    _split_point,
    _typed_value,
    resolve_relative_dates,
)
from src.producers.xlsx_reader import is_xlsx, iter_xlsx_rows

_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def _normalize_column(name: Any) -> str:
    """Normalize spreadsheet headers to the identifier form used by field maps."""
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def _date_key(value: Any, fmt: str) -> tuple[bool, datetime | None]:
    """Sort key for a text date in ``fmt``; one the format cannot read sorts
    before every date."""
    parsed = _typed_value(value, fmt)
    return (parsed is not None, parsed)


def _workbook_rows(content: bytes, where_clause: str | None, **watermark: Any) -> Iterator[dict[str, Any]]:
    """Every row of a workbook's first sheet that passes ``where_clause``.

    An .xlsx workbook is streamed a row at a time and its dates arrive as ISO
    8601 strings, as the ArcGIS and CSV clients deliver theirs; a legacy .xls
    goes through pandas and xlrd. ``watermark`` (the column, its text format
    and its sentinels) compares that column as dates.
    """
    if is_xlsx(content):
        for row in iter_xlsx_rows(BytesIO(content), rename=_normalize_column):
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
            if _row_matches(where_clause, row, **watermark):
                yield row
        return
    frame = pd.read_excel(BytesIO(content), engine="xlrd")
    frame = frame.rename(columns={column: _normalize_column(column) for column in frame.columns})
    frame = frame.where(pd.notna(frame), None)
    for row in frame.to_dict(orient="records"):
        if _row_matches(where_clause, row, **watermark):
            yield row


class ExcelClient:
    """Download a workbook once, normalize rows, and yield filtered batches."""

    def __init__(self, http_client: httpx.Client | None = None):
        self.http = http_client or httpx.Client(timeout=180.0, follow_redirects=True)
        # The ETag and Last-Modified of each workbook last read in full, so an
        # unchanged file answers 304 instead of downloading again.
        self._validators: dict[str, dict[str, str]] = {}

    def resolve_link(self, page_url: str, pattern: str) -> str:
        """The newest file ``page_url`` links whose URL matches ``pattern``.

        Richmond's assessor renames its transfers workbook with each monthly
        release (``Assessor_Transfers_2026-09-23.xlsx``), and its media page
        links the current one. Dated names sort by date, so the greatest
        match is the newest.
        """
        response = self.http.get(page_url)
        response.raise_for_status()
        matcher = re.compile(pattern)
        links = {}
        for href in _HREF.findall(response.text):
            url = urljoin(page_url, html.unescape(href))
            found = matcher.search(url)
            if found:
                links[url] = found.group(0)
        if not links:
            raise ValueError(f"{page_url} links no file matching {pattern!r}")
        return max(links, key=links.__getitem__)

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
        link_pattern: str | None = None,
        **kwargs: Any,
    ) -> Generator[list[dict[str, Any]], None, None]:
        del id_col
        watermark_col = _normalize_column(kwargs.get("watermark_col") or "") or None
        watermark_format = kwargs.get("watermark_format")
        point_col = _normalize_column(kwargs.get("point_col") or "") or None
        point_lon_first = bool(kwargs.get("point_lon_first"))
        url = self.resolve_link(endpoint_url, link_pattern) if link_pattern else endpoint_url
        response = self.http.get(url, headers=self._validators.get(url, {}))
        if response.status_code == 304:
            return
        response.raise_for_status()

        selected_cols = (
            [_normalize_column(column) for column in select.split(",") if column.strip()]
            if select
            else None
        )
        where = _normalize_where(resolve_relative_dates(where_clause))
        rows = list(
            _workbook_rows(
                response.content,
                where,
                watermark_col=watermark_col,
                watermark_format=watermark_format,
                watermark_exclude=kwargs.get("watermark_exclude") or [],
            )
        )
        if selected_cols:
            rows = [{key: row[key] for key in selected_cols if key in row} for row in rows]
        if point_col:
            for row in rows:
                row.update(_split_point(row.get(point_col), point_lon_first))

        if order_by:
            match = re.match(
                r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(ASC|DESC)?\s*$",
                order_by,
                re.IGNORECASE,
            )
            column = _normalize_column(match.group(1) if match else order_by)
            reverse = bool(match and match.group(2) and match.group(2).upper() == "DESC")
            if column == watermark_col and watermark_format:
                rows.sort(key=lambda row: _date_key(row.get(column), watermark_format), reverse=reverse)
            else:
                rows.sort(key=lambda row: str(row.get(column) or ""), reverse=reverse)

        truncated = bool(max_records and len(rows) > max_records)
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

        # Remember the file only once every row was handed over: a poll that
        # stopped early, or was capped short, reads it again next time.
        if not truncated:
            validators = {
                header: value
                for header, value in (
                    ("If-None-Match", response.headers.get("ETag")),
                    ("If-Modified-Since", response.headers.get("Last-Modified")),
                )
                if isinstance(value, str) and value
            }
            if validators:
                self._validators[url] = validators


def _normalize_where(where_clause: str | None) -> str | None:
    """Normalize simple scheduler predicates to the spreadsheet header form."""
    if not where_clause:
        return None
    return re.sub(r"\b([A-Za-z][A-Za-z0-9 ]*)\b(?=\s*(?:>=|<=|!=|=|>|<))", lambda m: _normalize_column(m.group(1)), where_clause)
