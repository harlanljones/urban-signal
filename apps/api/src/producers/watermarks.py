"""Typed comparison helpers for heterogeneous municipal watermark values."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime
from functools import cmp_to_key
from typing import Any

_TEXT_FORMATS = (
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M:%S",
    "%Y%m%d",
    "%Y-%m-%d",
    "%Y.%m.%d",
)


def parse_watermark(value: Any) -> datetime | None:
    """Parse supported API watermark values into UTC-aware datetimes.

    Municipal APIs expose watermarks as ISO/RFC3339 strings, NYC's historical
    ``MM/DD/YYYY`` text, compact ``YYYYMMDD`` text, MD SDAT's dotted
    ``YYYY.MM.DD`` text (US-128), dates, datetimes, or epoch
    seconds/milliseconds. Invalid and empty values are ignored explicitly so a
    malformed row cannot become the newest watermark by accident.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=UTC)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = float(value) / 1000 if abs(float(value)) > 10_000_000_000 else float(value)
        return datetime.fromtimestamp(seconds, tz=UTC)

    text = str(value).strip()
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    for fmt in _TEXT_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            pass
    return None


def compare_watermarks(left: Any, right: Any) -> int:
    """Return ``-1``, ``0``, or ``1`` after parsing both values.

    ``None`` sorts below a valid watermark. This gives callers a deterministic
    policy for mixed rows while keeping invalid values out of max calculations.
    """
    parsed_left = parse_watermark(left)
    parsed_right = parse_watermark(right)
    if parsed_left is None:
        return 0 if parsed_right is None else -1
    if parsed_right is None:
        return 1
    return (parsed_left > parsed_right) - (parsed_left < parsed_right)


def newest_watermark(values: Iterable[Any]) -> datetime | None:
    """Return the newest valid typed watermark from a row-value iterable."""
    parsed = [value for value in (parse_watermark(item) for item in values) if value is not None]
    return max(parsed) if parsed else None


def sort_watermarks(values: Iterable[Any]) -> list[Any]:
    """Sort raw values by their typed meaning, preserving the raw values."""
    return sorted(values, key=cmp_to_key(compare_watermarks))


def typed_watermark_entry(
    value: Any,
    *,
    fmt: str | None = None,
    exclude: Iterable[str] = (),
) -> tuple[str, datetime] | None:
    """Validate one raw column value as a declared-type watermark.

    Returns ``(raw_text, parsed_utc)`` or ``None`` when the value is empty,
    named on the sentinel exclusion list, or unparseable under ``fmt`` (a
    declared strptime format) or the default multi-format parser. Sentinels
    such as PG County's ``ZZZZZZZZ`` sort above every real date, so they
    must be dropped before any max/ORDER-BY comparison, not parsed.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw in set(exclude):
        return None
    if fmt:
        try:
            parsed = datetime.strptime(raw, fmt).replace(tzinfo=UTC)
        except ValueError:
            return None
    else:
        parsed = parse_watermark(raw)
    if parsed is None:
        return None
    return raw, parsed


def newest_typed_watermark(
    values: Iterable[Any],
    *,
    fmt: str | None = None,
    exclude: Iterable[str] = (),
) -> tuple[str, datetime] | None:
    """Return the (raw, parsed) watermark with the greatest calendar value.

    Typed comparison matters when a text column mixes formats (NYC's
    ``issuance_date`` carries ISO and ``MM/DD/YYYY`` in one column): lexical
    max would pick by string order, not by date.
    """
    entries = [
        entry
        for value in values
        if (entry := typed_watermark_entry(value, fmt=fmt, exclude=exclude)) is not None
    ]
    return max(entries, key=lambda entry: entry[1]) if entries else None


def watermark_exclude_clause(column: str, exclude: Iterable[str]) -> str | None:
    """Build a SQL ``NOT IN`` fragment excluding sentinel watermark values.

    Usable in Socrata ``$where``, ArcGIS ``where``, and Carto WHERE clauses.
    Returns ``None`` when nothing is excluded so callers can skip the param.
    """
    values = [str(value).replace("'", "''") for value in exclude if str(value).strip()]
    if not values:
        return None
    listed = ", ".join(f"'{value}'" for value in values)
    return f"{column} NOT IN ({listed})"


# ArcGIS servers that reject ISO-string date comparisons in ``where`` and only
# accept ANSI ``date 'YYYY-MM-DD'`` literals for date columns. US-109 (DC) /
# US-87 (Milwaukee) / US-88 (Charlotte): verified live — ``col >= '2026-08-
# 01T00:00:00'`` returns 400 "Unable to complete operation" while
# ``col >= date '2026-08-01'`` works.
ANSI_DATE_LITERAL_HOSTS = (
    "maps2.dcgis.dc.gov",
    "milwaukeemaps.milwaukee.gov",
    "gis.charlottenc.gov",
    "gis.tucsonaz.gov",
    "pub.sagis.org",
    "webgis.bgky.org",
    "intervector.leoncountyfl.gov",
    "maps.spartanburgcounty.org",
)


def watermark_comparison(
    watermark_col: str,
    op: str,
    value: str,
    endpoint: str,
    *,
    watermark_type: str | None = None,
    watermark_format: str | None = None,
) -> str:
    """Render a ``col OP <value>`` predicate with a server-appropriate literal.

    Most registered servers accept the ISO 8601 string the scheduler stores;
    the ANSI-literal hosts above reject it, so for those the value is
    truncated to its date component and wrapped in an ANSI ``date '...'``
    literal. Shared by the scheduler's incremental filter and the backfill
    loader's windowed filter so both stay query-shape compatible.
    """
    # San Jose's CKAN permits/311 exports store dates as M/D/YYYY text. A raw
    # string comparison would make `8/9` sort after `8/22`; cast both sides in
    # CKAN's SQL dialect while retaining the raw format in scheduler state.
    if (
        endpoint.startswith("ckan://")
        and watermark_type == "text"
        and watermark_format == "%m/%d/%Y %I:%M:%S %p"
    ):
        escaped = value.replace("'", "''")
        pg_format = "MM/DD/YYYY HH12:MI:SS AM"
        return (
            f'to_timestamp("{watermark_col}", \'{pg_format}\') {op} '
            f"to_timestamp('{escaped}', '{pg_format}')"
        )
    if any(host in endpoint for host in ANSI_DATE_LITERAL_HOSTS):
        return f"{watermark_col} {op} date '{value[:10]}'"
    return f"{watermark_col} {op} '{value}'"
