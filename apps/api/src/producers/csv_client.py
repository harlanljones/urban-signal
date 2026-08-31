"""CSVClient: ingest flat open-data CSV files (San Diego, US-91).

Static-CSV portals (``seshat.datasd.org``) publish no Socrata/ArcGIS/CARTO/CKAN
API — the file is the feed. This leaf client downloads the file once and applies
watermark filtering client-side, matching the ``paginate(...)`` generator
interface the scheduler and producers expect.

The endpoint is a year-scoped file (``approvals_issued_2026_datasd.csv``), so
the server-side watermark predicate the scheduler renders (``col > '<hw>'``) is
evaluated locally against the ISO date strings in the downloaded rows.

Pass ``zip_member='2026.csv'`` to read one named member out of a zip endpoint
(St. Louis CSB ``csb.zip``). The scheduler does not yet forward that kwarg —
wiring it is a later spine hold.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Generator
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

_CMP = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(>=|<=|>|<|=|!=)\s*'([^']*)'\s*$")
_IS_NULL = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+is\s+not\s+null\s*$", re.IGNORECASE)
_NOT_IN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+NOT\s+IN\s*\(([^)]*)\)\s*$", re.IGNORECASE)


def _normalize_header(name: str) -> str:
    """Normalize municipal CSV headers to the producer field-map convention."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _decode_csv_bytes(raw: bytes) -> str:
    """Decode a municipal CSV payload, preferring UTF-8 with a Latin-1 fallback."""
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _read_zip_member(payload: bytes, member: str) -> str:
    """Extract one named CSV member from a zip (St. Louis CSB ``csb.zip`` / ``{year}.csv``).

    ``member`` is a filename such as ``2026.csv``. A basename match is accepted
    when the archive nests the year file under a folder.
    """
    name = str(member).strip()
    if not name or name.lower() in {"true", "1", "yes"}:
        raise ValueError(
            "zip_member must be a member filename (e.g. '2026.csv'), not a boolean flag"
        )
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise ValueError("CSV endpoint declared zip_member but the body is not a zip") from exc
    with archive:
        names = archive.namelist()
        chosen = name if name in names else None
        if chosen is None:
            wanted = name.rsplit("/", 1)[-1].lower()
            matches = [
                n
                for n in names
                if n.rsplit("/", 1)[-1].lower() == wanted and not n.endswith("/")
            ]
            if not matches:
                raise FileNotFoundError(
                    f"zip member {name!r} not in archive; members={names}"
                )
            chosen = matches[0]
        return _decode_csv_bytes(archive.read(chosen))


def _typed_value(value: Any, fmt: str | None) -> datetime | None:
    if not value or not fmt:
        return None
    try:
        return datetime.strptime(str(value).strip(), fmt)
    except (TypeError, ValueError):
        return None


def _row_matches(
    where_clause: str | None,
    row: Dict[str, Any],
    *,
    watermark_col: str | None = None,
    watermark_format: str | None = None,
    watermark_exclude: List[str] | None = None,
) -> bool:
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
            col, op, literal = _normalize_header(m.group(1)), m.group(2), m.group(3)
            value = row.get(col)
            if value is None:
                return False
            s = str(value).strip()
            if col == _normalize_header(watermark_col or "") and watermark_format:
                if s in (watermark_exclude or []):
                    return False
                parsed_value = _typed_value(s, watermark_format)
                parsed_literal = _typed_value(literal, watermark_format)
                if parsed_value is None or parsed_literal is None:
                    return False
                left, right = parsed_value, parsed_literal
            else:
                left, right = s, literal
            if op == ">":
                if not left > right:
                    return False
            elif op == ">=":
                if not left >= right:
                    return False
            elif op == "<":
                if not left < right:
                    return False
            elif op == "<=":
                if not left <= right:
                    return False
            elif op == "=":
                if not left == right:
                    return False
            elif op == "!=":
                if not left != right:
                    return False
        else:
            m2 = _IS_NULL.match(part)
            if m2 and row.get(_normalize_header(m2.group(1))) in (None, ""):
                return False
            m3 = _NOT_IN.match(part)
            if m3:
                col = _normalize_header(m3.group(1))
                excluded = {item.strip().strip("'") for item in m3.group(2).split(",")}
                if str(row.get(col, "")).strip() in excluded:
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
        fallback_endpoints: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Download the CSV once and yield batches of filtered rows.

        Some ArcGIS Hub items expose both a download route and the underlying
        item-data route. Keep the primary URL first, but allow a registration
        to carry an explicitly verified fallback when the Hub proxy fails.
        """
        last_error: Exception | None = None
        for candidate in [endpoint_url, *(fallback_endpoints or [])]:
            try:
                response = self.http.get(candidate)
                response.raise_for_status()
                break
            except (httpx.HTTPError, OSError) as exc:
                last_error = exc
        else:
            if last_error is not None:
                raise last_error
            raise RuntimeError("CSV endpoint list is empty")

        zip_member = kwargs.get("zip_member")
        delimiter = kwargs.get("delimiter", ",")
        if zip_member:
            csv_text = _read_zip_member(response.content, zip_member)
        else:
            csv_text = response.text
        reader = csv.DictReader(io.StringIO(csv_text), delimiter=delimiter)
        # Municipal CSVs use title case, spaces, and punctuation inconsistently;
        # normalize them so shared field maps apply uniformly.
        if reader.fieldnames:
            reader.fieldnames = [_normalize_header(name) for name in reader.fieldnames]
        selected_cols = (
            [_normalize_header(c) for c in select.split(",") if c.strip()] if select else None
        )
        watermark_col = _normalize_header(kwargs.get("watermark_col") or "") or None
        watermark_format = kwargs.get("watermark_format")
        watermark_exclude = kwargs.get("watermark_exclude") or []

        rows: List[Dict[str, Any]] = []
        for row in reader:
            if not _row_matches(
                where_clause,
                row,
                watermark_col=watermark_col,
                watermark_format=watermark_format,
                watermark_exclude=watermark_exclude,
            ):
                continue
            if selected_cols:
                row = {k: row[k] for k in selected_cols if k in row}
            rows.append(row)

        if order_by:
            m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(ASC|DESC)?\s*$", order_by, re.IGNORECASE)
            col = _normalize_header(m.group(1)) if m else _normalize_header(order_by)
            typed_sort = col == watermark_col and watermark_format

            def sort_key(row: Dict[str, Any]) -> Any:
                if typed_sort:
                    return _typed_value(row.get(col), watermark_format) or datetime.min
                return str(row.get(col, ""))

            if m and m.group(2) and m.group(2).upper() == "DESC":
                rows.sort(key=sort_key, reverse=True)
            else:
                rows.sort(key=sort_key)

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
