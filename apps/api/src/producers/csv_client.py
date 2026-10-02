"""CSVClient: ingest flat open-data CSV files (San Diego, US-91).

Static-CSV portals (``seshat.datasd.org``) publish no Socrata/ArcGIS/CARTO/CKAN
API — the file is the feed. This leaf client downloads the file once and applies
watermark filtering client-side, matching the ``paginate(...)`` generator
interface the scheduler and producers expect.

The endpoint is a year-scoped file (``approvals_issued_2026_datasd.csv``), so
the server-side watermark predicate the scheduler renders (``col > '<hw>'``) is
evaluated locally against the ISO date strings in the downloaded rows.

Pass ``zip_member='2026.csv'`` to read one named member out of a zip endpoint
(St. Louis CSB ``csb.zip``), and ``columns`` to name the fields of a file with
no header row (Pierce County's ``sale.txt``). The scheduler forwards both from
the spec.
"""

from __future__ import annotations

import codecs
import csv
import io
import re
import zipfile
from collections.abc import Generator, Iterable, Iterator
from datetime import UTC, datetime, timedelta
from itertools import chain, islice
from typing import Any

import httpx

_CMP = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(>=|<=|>|<|=|!=)\s*'([^']*)'\s*$")
_IS_NULL = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+is\s+not\s+null\s*$", re.IGNORECASE)
_NOT_IN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+NOT\s+IN\s*\(([^)]*)\)\s*$", re.IGNORECASE)
# The rolling window ArcGIS specs send server-side (``CURRENT_DATE - INTERVAL
# '180' DAY``); a file feed resolves it to a date before filtering rows.
_RELATIVE_DATE = re.compile(r"CURRENT_DATE\s*-\s*INTERVAL\s*'(\d+)'\s*DAY", re.IGNORECASE)
# ``CURRENT_DATE`` alone bounds a window above, so a sale keyed in the future
# (Alachua's Sales.txt holds one dated 2079) stays out of it.
_CURRENT_DATE = re.compile(r"\bCURRENT_DATE\b", re.IGNORECASE)
# One line with its ending: \r\n, \r or \n, as ``io.StringIO(text, newline="")``
# splits them, so the csv module ends rows on any of the three (Milwaukee's
# permits export uses bare \r).
_LINE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+")


def _lines(text: str) -> Iterator[str]:
    """The lines of ``text`` without a copy of it.

    StringIO holds four bytes a character: over 350 MB for Pierce County's
    89 MB sales file, on top of the text itself.
    """
    return (match.group(0) for match in _LINE.finditer(text))


def resolve_relative_dates(where_clause: str | None, today: Any = None) -> str | None:
    """Replace ``CURRENT_DATE - INTERVAL 'N' DAY`` with that day's quoted ISO
    date, and ``CURRENT_DATE`` alone with today's."""
    if not where_clause:
        return where_clause
    day = today or datetime.now(UTC).date()
    clause = _RELATIVE_DATE.sub(
        lambda m: f"'{(day - timedelta(days=int(m.group(1)))).isoformat()}'", where_clause
    )
    return _CURRENT_DATE.sub(f"'{day.isoformat()}'", clause)


def _normalize_header(name: str) -> str:
    """Normalize municipal CSV headers to the producer field-map convention."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _nonblank_rows(lines: Iterable[str], delimiter: str) -> Iterator[list[str]]:
    """The parsed rows of ``lines`` that hold at least one non-blank cell."""
    return (row for row in csv.reader(lines, delimiter=delimiter) if any(cell.strip() for cell in row))


def _rows_as_lines(rows: Iterable[list[str]], delimiter: str) -> Iterator[str]:
    """Each row written back as CSV, one physical line at a time."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    for row in rows:
        buffer.seek(0)
        buffer.truncate()
        writer.writerow(row)
        yield from _lines(buffer.getvalue())


def _without_preamble(lines: Iterator[str], delimiter: str = ",") -> tuple[Iterator[str], bool]:
    """``lines`` without a leading single-field preamble line, and whether one
    was dropped.

    Some CSV publishers (California ABC ``DailyExport-CSV.zip``) lead the real
    header with a metadata line that csv.DictReader would otherwise mistake for
    the field names: a one-field row whose next row carries multiple fields.
    Only the first two rows decide, so a file without one streams on
    untouched; parsing every row of Alachua County's 510,000 sales into lists
    took more memory than the file itself.
    """
    read: list[str] = []
    deciding = True

    def recorded() -> Iterator[str]:
        for line in lines:
            if deciding:
                read.append(line)
            yield line

    rows = _nonblank_rows(recorded(), delimiter)
    head = list(islice(rows, 2))
    deciding = False
    if len(head) == 2 and len(head[0]) == 1 and len(head[1]) > 1:
        # The rest of the file is written back without its blank rows, as
        # the whole text was before files were streamed.
        return _rows_as_lines(chain(head[1:], rows), delimiter), True
    return chain(read, lines), False


def _strip_preamble(text: str, delimiter: str = ",") -> str:
    """``text`` without a leading single-field preamble line, if one exists;
    returned unchanged when there is none."""
    lines, stripped = _without_preamble(_lines(text), delimiter)
    return "".join(lines) if stripped else text


def _decode_csv_bytes(raw: bytes) -> str:
    """Decode a municipal CSV payload, preferring UTF-8 with a Latin-1 fallback."""
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


# How much of a zip member to decompress at a time.
_CHUNK = 1 << 20


def _member_name(archive: zipfile.ZipFile, name: str) -> str:
    """The archive's own name for ``name``: the exact name, else the first
    member with the same basename."""
    names = archive.namelist()
    if name in names:
        return name
    wanted = name.rsplit("/", 1)[-1].lower()
    for candidate in names:
        if candidate.rsplit("/", 1)[-1].lower() == wanted and not candidate.endswith("/"):
            return candidate
    raise FileNotFoundError(f"zip member {name!r} not in archive; members={names}")


def _member_encoding(archive: zipfile.ZipFile, name: str) -> tuple[str, str]:
    """The encoding ``_decode_csv_bytes`` would choose for a member, and its
    error handler, found in one pass over the decompressed bytes without
    holding them: UTF-8 when every byte decodes, else cp1252, else UTF-8 with
    replacement characters."""
    decoders = {"utf-8": codecs.getincrementaldecoder("utf-8")(), "cp1252": codecs.getincrementaldecoder("cp1252")()}
    with archive.open(name) as raw:
        while decoders and (chunk := raw.read(_CHUNK)):
            for encoding, decoder in list(decoders.items()):
                try:
                    decoder.decode(chunk)
                except UnicodeDecodeError:
                    del decoders[encoding]
    for encoding, decoder in list(decoders.items()):
        try:
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            del decoders[encoding]
    if "utf-8" in decoders:
        return "utf-8-sig", "strict"
    if "cp1252" in decoders:
        return "cp1252", "strict"
    return "utf-8", "replace"


def _zip_member_lines(payload: bytes, member: str) -> Iterator[str]:
    """The lines of one named CSV member of a zip (St. Louis CSB ``csb.zip`` /
    ``{year}.csv``), decompressed and decoded as they are read.

    ``member`` is a filename such as ``2026.csv``. A basename match is accepted
    when the archive nests the year file under a folder. Polk County's sales
    member unpacks to 518 MB: read whole and then decoded, it took twice that
    on top of the download.
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
    try:
        chosen = _member_name(archive, name)
        encoding, errors = _member_encoding(archive, chosen)
    except BaseException:
        archive.close()
        raise
    return _member_lines(archive, chosen, encoding, errors)


def _member_lines(archive: zipfile.ZipFile, name: str, encoding: str, errors: str) -> Iterator[str]:
    with archive, archive.open(name) as raw:
        # newline="" ends lines on \r\n, \r or \n and keeps the endings, as
        # ``_lines`` does.
        yield from io.TextIOWrapper(raw, encoding=encoding, errors=errors, newline="")


def _read_zip_member(payload: bytes, member: str) -> str:
    """The text of one named CSV member of a zip; see ``_zip_member_lines``."""
    return "".join(_zip_member_lines(payload, member))


def _typed_value(value: Any, fmt: str | None) -> datetime | None:
    if not value or not fmt:
        return None
    try:
        return datetime.strptime(str(value).strip(), fmt)
    except (TypeError, ValueError):
        return None


def _iso_literal(literal: str) -> datetime | None:
    """A filter literal written as ISO 8601 rather than in the column's format.

    A feed that declares a format without the ``text`` type keeps its
    watermark, and starts its backfill window, as ISO (St. Louis permits);
    parsed only in the column's format, such a literal matched no row, so
    every poll after the first read nothing.
    """
    try:
        return datetime.fromisoformat(literal).replace(tzinfo=None)
    except ValueError:
        return None


def _row_matches(
    where_clause: str | None,
    row: dict[str, Any],
    *,
    watermark_col: str | None = None,
    watermark_format: str | None = None,
    watermark_exclude: list[str] | None = None,
) -> bool:
    """Client-side predicate over one parsed row (ANSI/SODA-style clauses).

    Supports top-level ``OR``: the clause is split on `` OR `` first; a row
    passes if any branch matches (all AND parts within the branch must match).
    """
    if not where_clause:
        return True
    clause = where_clause.strip()
    while clause.startswith("(") and clause.endswith(")"):
        depth = 0
        matched = False
        for i, ch in enumerate(clause):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    if i == len(clause) - 1:
                        matched = True
                    break
        if matched:
            clause = clause[1:-1].strip()
        else:
            break
    for branch in clause.split(" OR "):
        if _branch_matches(branch.strip(), row, watermark_col=watermark_col, watermark_format=watermark_format, watermark_exclude=watermark_exclude):
            return True
    return False


def _branch_matches(
    branch: str,
    row: dict[str, Any],
    *,
    watermark_col: str | None = None,
    watermark_format: str | None = None,
    watermark_exclude: list[str] | None = None,
) -> bool:
    """Evaluate one AND-separated clause: every part must match."""
    for part in branch.split(" AND "):
        part = part.strip()
        while part.startswith("(") and part.endswith(")"):
            depth = 0
            matched = False
            for i, ch in enumerate(part):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        if i == len(part) - 1:
                            matched = True
                        break
            if matched:
                part = part[1:-1].strip()
            else:
                break
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
                parsed_literal = _typed_value(literal, watermark_format) or _iso_literal(literal)
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
        columns = kwargs.get("columns")
        if zip_member:
            lines = _zip_member_lines(response.content, zip_member)
        else:
            lines = _lines(response.text)
        if columns:
            # A file with no header row: every line is a row, named by the
            # spec's columns, and there is no header for a preamble to hide.
            fieldnames: list[str] | None = list(columns)
        else:
            lines, _ = _without_preamble(lines, delimiter=delimiter)
            fieldnames = None
        reader = csv.DictReader(lines, fieldnames=fieldnames, delimiter=delimiter)
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
        where_clause = resolve_relative_dates(where_clause)

        rows: list[dict[str, Any]] = []
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

            def sort_key(row: dict[str, Any]) -> Any:
                if typed_sort:
                    return _typed_value(row.get(col), watermark_format) or datetime.min
                return str(row.get(col, ""))

            if m and m.group(2) and m.group(2).upper() == "DESC":
                rows.sort(key=sort_key, reverse=True)
            else:
                rows.sort(key=sort_key)

        total = 0
        batch: list[dict[str, Any]] = []
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
