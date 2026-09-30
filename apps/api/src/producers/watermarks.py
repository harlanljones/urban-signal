"""Typed comparison helpers for heterogeneous municipal watermark values."""

from __future__ import annotations

import calendar
import logging
import re
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from functools import cmp_to_key
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

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
# accept ANSI ``date``/``timestamp`` literals for date columns. US-109 (DC) /
# US-87 (Milwaukee) / US-88 (Charlotte): verified live — ``col >= '2026-08-
# 01T00:00:00'`` returns 400 "Unable to complete operation" while
# ``col >= date '2026-08-01'`` works. Every incremental feed on these hosts
# also answers ``col > timestamp '2026-09-24 12:00:00'`` (verified 2026-09-30).
ANSI_DATE_LITERAL_HOSTS = (
    "maps2.dcgis.dc.gov",
    "milwaukeemaps.milwaukee.gov",
    "gis.charlottenc.gov",
    "gis.tucsonaz.gov",
    "pub.sagis.org",
    "webgis.bgky.org",
    "intervector.leoncountyfl.gov",
    "maps.spartanburgcounty.org",
    "gisportal.stocktonca.gov",
    "gis.countyofriverside.us",
    "gis.chandleraz.gov",
    "maps.medfordmaps.org",
    # Des Moines, IA (ArcGIS Server 10.91): verified live 2026-09-29 —
    # ``IssuedDate > '2026-09-25T05:00:00'`` returns 400 "Unable to complete
    # operation" while ``IssuedDate >= date '2026-09-25'`` works.
    "maps.dsm.city",
    # Columbus, OH (ArcGIS Server 11.5): verified live 2026-09-30 —
    # ``REPORTED_DATE > '2026-09-22T00:00:00'`` returns 400 "Unable to complete
    # operation" while ``REPORTED_DATE > date '2026-09-22'`` works. The layer
    # declares Eastern time and reads literals in it.
    "maps2.columbus.gov",
    # Augusta, GA (10.91), Dayton, OH (11.4) and Peoria County, IL (11.4):
    # verified live 2026-09-30 with count queries — ``> '2026-09-22T05:31:07'``
    # returns 400 "Unable to complete operation" on each, while ``> date
    # '2026-09-22'`` works. Every first poll passed (no watermark yet); the
    # second poll failed.
    "gismap.augustaga.gov",
    "maps.daytonohio.gov",
    "gis.peoriacounty.gov",
    # Tulsa, OK (ArcGIS Server 11.5): verified live 2026-09-30 —
    # ``case_opened > '2026-08-24T02:53:23'`` returns 400 "Unable to complete
    # operation" while ``case_opened > date '2026-08-24'`` works.
    "maps.cityoftulsa.org",
    # Kanawha County Assessor, WV (SQL Server backed): verified live 2026-09-30 —
    # ``Last_Sales_Date >= '2026-09-01'`` returns 400 "Unable to complete
    # operation" while ``Last_Sales_Date >= date '2026-09-01'`` works. Charleston
    # WV deeds poll as a snapshot today, so this only matters if they go incremental.
    "kanawhacountyassessorgis.com",
    # Roanoke, VA (ArcGIS Server): verified live 2026-09-30 —
    # ``pxfer_date > '2026-09-01T00:00:00'`` and ``pxfer_date >= '2026-09-01'``
    # return 400 "Unable to complete operation" while ``pxfer_date >= date
    # '2026-09-01'`` works.
    "maps.roanokeva.gov",
    # Verified live 2026-09-30 with a count query on every incremental ArcGIS
    # feed: ``col > '2026-09-24T12:00:00'`` returns 400 on each of these while
    # ``col > timestamp '2026-09-24 12:00:00'`` answers. Each feed's first poll
    # passed (no watermark yet) and every later poll failed. A shared ArcGIS
    # proxy is matched by its server id, since its other servers take ISO.
    "ags.auroragov.org",
    "billingsgis.com",
    "gis.bouldercolorado.gov",
    "gisweb.bozeman.net",
    "scgisa.starkcountyohio.gov",
    "capeims.capecoral.gov",
    "ccggisprod.columbusga.org",
    "webgis2.durhamnc.gov",
    "maps.evansvillegis.com",
    "mapit.fortworthtexas.gov",
    "gismaps.glendaleaz.com",
    "utility.arcgis.com/usrsvcs/servers/d595ae995fb049d3ac54919ebf24b1ac",
    "mycity2.houstontx.gov",
    "maps.huntsvilleal.gov",
    "gis.indy.gov",
    "maps.las-cruces.org",
    "gis.palmbayflorida.org",
    "311.memphistn.gov",
    "gis.montgomeryal.gov",
    "utility.arcgis.com/usrsvcs/servers/7751a4c516434f1d947c67cd78a4d968",
    "dcgis.org/server",
    "maps.phoenix.gov",
    "mapportal.phoenix.gov",
    "www.portlandmaps.com",
    "arcgis.tampagov.net",
    "gis.toledo.oh.gov",
    "gismaps.wichita.gov",
    "gis.nhcgov.com",
    # Maricopa County Assessor (ArcGIS Server 11.5): verified live 2026-09-30 —
    # ``DEED_DATE > '2026-09-01T00:00:00'`` returns 400 "Unable to complete
    # operation" while ``DEED_DATE > timestamp '2026-09-01 00:00:00'`` works.
    # Its five deeds feeds poll as snapshots; a backfill with a start date
    # sends the literal.
    "gis.mcassessor.maricopa.gov",
    # Jackson County, OR (ArcGIS Server 10.91): verified live 2026-09-30 —
    # ``SalesDate >= '2026-09-01T00:00:00'`` and ``SalesDate >= '2026-09-01
    # 00:00:00'`` return 400 "Unable to complete operation" while ``SalesDate
    # >= timestamp '2026-09-01 00:00:00'`` works. Medford's deeds poll as a
    # snapshot; a backfill with a start date sends the literal.
    "spatial.jacksoncountyor.gov",
    # Mecklenburg County, NC: verified live 2026-09-30 — ``issue_date >=
    # '2026-09-29T00:00:00'`` returns 400 "Unable to complete operation" while
    # ``issue_date >= timestamp '2026-09-29 00:00:00'`` works. The layer
    # declares Eastern time and reads literals in it.
    "meckgis.mecklenburgcountync.gov",
    # Asheville, NC: verified live 2026-09-30 — ``date_opened >=
    # '2026-09-28T00:00:00'`` returns 400 "Unable to complete operation" while
    # ``date_opened >= timestamp '2026-09-28 00:00:00'`` works. The layer
    # declares Eastern time and reads literals in it: ``>= timestamp
    # '2026-09-29 02:00:00'`` leaves out that day's rows, stored at 04:00Z.
    "gis.ashevillenc.gov",
)


def casts_text_watermark(
    endpoint: str, watermark_type: str | None, watermark_format: str | None
) -> bool:
    """Whether a filter casts a text watermark to a timestamp on both sides.

    San Jose's CKAN permits/311 exports store dates as M/D/YYYY text. A raw
    string comparison would make `8/9` sort after `8/22`; the filter casts
    both sides in CKAN's SQL dialect while scheduler state keeps the raw format.
    """
    return (
        endpoint.startswith("ckan://")
        and watermark_type == "text"
        and watermark_format == "%m/%d/%Y %I:%M:%S %p"
    )


# A date format whose text sorts as its dates do: year first, then month, day
# and time, each zero-padded.
_YEAR_FIRST = re.compile(
    r"^%Y(?:[^%]*%m(?:[^%]*%d(?:[^%]*%H(?:[^%]*%M(?:[^%]*%S(?:[^%]*%f)?)?)?)?)?)?[^%]*$"
)


def text_sorts_as_dates(watermark_format: str | None) -> bool:
    """Whether text written in ``watermark_format`` sorts in date order.

    Only a year-first format does (``%Y%m%d``, ``%Y-%m-%d %H:%M:%S``). As
    text, ``12/31/2018`` sorts above ``07/02/2026``.
    """
    return bool(watermark_format and _YEAR_FIRST.match(watermark_format))


# Date parts a text window names; a time of day or a zone matches anything.
_DATE_DIRECTIVES = frozenset("YymBbdAa")
_TIME_DIRECTIVES = frozenset("HIMSfpzZ")


def _format_tokens(fmt: str) -> list[tuple[bool, str]] | None:
    """Split a strptime format into ``(is_directive, text)`` tokens.

    None when the format cannot be named day by day: it lacks a year, a month
    or a day, uses another directive, or has a literal ``%`` or ``_`` (LIKE
    wildcards).
    """
    tokens: list[tuple[bool, str]] = []
    pos = 0
    for match in re.finditer(r"%(.)", fmt):
        if match.start() > pos:
            tokens.append((False, fmt[pos : match.start()]))
        tokens.append((True, match.group(1)))
        pos = match.end()
    if pos < len(fmt):
        tokens.append((False, fmt[pos:]))
    directives = {text for is_directive, text in tokens if is_directive}
    literals = "".join(text for is_directive, text in tokens if not is_directive)
    if (
        not directives <= _DATE_DIRECTIVES | _TIME_DIRECTIVES
        or not directives & {"Y", "y"}
        or not directives & {"m", "B", "b"}
        or "d" not in directives
        or "%" in literals
        or "_" in literals
    ):
        return None
    return tokens


def _date_cover(start: date, end: date) -> list[tuple[str, date]]:
    """Whole years, whole months and single days that cover ``start..end``."""
    units: list[tuple[str, date]] = []
    day = start
    while day <= end:
        month_end = day.replace(day=calendar.monthrange(day.year, day.month)[1])
        if (day.month, day.day) == (1, 1) and date(day.year, 12, 31) <= end:
            units.append(("year", day))
            day = date(day.year + 1, 1, 1)
        elif day.day == 1 and month_end <= end:
            units.append(("month", day))
            day = month_end + timedelta(days=1)
        else:
            units.append(("day", day))
            day += timedelta(days=1)
    return units


def _render_unit(tokens: list[tuple[bool, str]], unit: str, day: date, padded: bool) -> str:
    """One unit of a cover as the column writes it, ``%`` where any text goes."""
    parts = []
    for is_directive, text in tokens:
        if not is_directive:
            parts.append(text.replace("'", "''"))
        elif text == "Y":
            parts.append(f"{day.year:04d}")
        elif text == "y":
            parts.append(f"{day.year % 100:02d}")
        elif text == "m" and unit != "year":
            parts.append(f"{day.month:02d}" if padded else str(day.month))
        elif text in "Bb" and unit != "year":
            parts.append(day.strftime(f"%{text}"))
        elif text == "d" and unit == "day":
            parts.append(f"{day.day:02d}" if padded else str(day.day))
        elif text in "Aa" and unit == "day":
            parts.append(day.strftime(f"%{text}"))
        else:
            parts.append("%")
    # Wildcards joined only by punctuation are one wildcard: ``%:% %`` is ``%``.
    return re.sub(r"%(?:[^0-9A-Za-z%]*%)+", "%", "".join(parts))


def text_date_window(
    watermark_col: str,
    op: str,
    value: str,
    watermark_format: str,
    *,
    today: date | None = None,
) -> str | None:
    """Name the dates from a text watermark's day to today, as the column writes them.

    A format that is not year first does not compare as text: from
    ``09/28/2026``, ``SALEDATE > '09/28/2026'`` read September 29 to December
    31 of every past year, and Worcester's unpadded ``9/9/2026`` sorted above
    ``9/30/2026``. The window lists each day instead, from the watermark's
    (the next day for ``>`` on a date-only column) to today in UTC, with
    whole months and years as ``LIKE`` patterns:
    ``SALEDATE IN ('09/28/2026', '9/28/2026', ...) OR SALEDATE LIKE
    '10/%/2026'``. Each day is written padded and unpadded, since strptime
    reads both. A time of day matches any text (Honolulu's ``September 29,
    2026 at %``), so rows earlier on the watermark's day are read again and
    the dedup drops them. None when the format or value cannot be read.
    """
    tokens = _format_tokens(watermark_format)
    if tokens is None or op not in (">", ">="):
        return None
    entry = typed_watermark_entry(value, fmt=watermark_format) or typed_watermark_entry(value)
    if entry is None:
        return None
    start = entry[1].date()
    if op == ">" and not any(is_directive and text in _TIME_DIRECTIVES for is_directive, text in tokens):
        start += timedelta(days=1)
    end = max(today or datetime.now(UTC).date(), start)
    exact: list[str] = []
    patterns: list[str] = []
    for unit, day in _date_cover(start, end):
        for padded in (True, False):
            text = _render_unit(tokens, unit, day, padded)
            bucket = patterns if "%" in text else exact
            if text not in bucket:
                bucket.append(text)
    terms = []
    if exact:
        listed = ", ".join(f"'{text}'" for text in exact)
        terms.append(f"{watermark_col} IN ({listed})")
    terms.extend(f"{watermark_col} LIKE '{pattern}'" for pattern in patterns)
    return terms[0] if len(terms) == 1 else f"({' OR '.join(terms)})"


# An ArcGIS layer or a Socrata resource: servers that evaluate ``where``.
_SERVER_FILTERED = re.compile(r"/rest/services/.+/(?:FeatureServer|MapServer)/\d+/?$|/resource/[^/]+\.json$")


def _server_reads_where(endpoint: str) -> bool:
    """Whether the server evaluates ``where`` (an ArcGIS layer, a Socrata resource).

    The CSV and workbook clients evaluate it themselves, comparing a text
    column as dates in its declared format.
    """
    return bool(_SERVER_FILTERED.search(endpoint))


def watermark_comparison(
    watermark_col: str,
    op: str,
    value: str,
    endpoint: str,
    *,
    watermark_type: str | None = None,
    watermark_format: str | None = None,
    time_zone: str | None = None,
    today: date | None = None,
) -> str:
    """Render a ``col OP <value>`` predicate with a server-appropriate literal.

    Most registered servers accept the ISO 8601 string the scheduler stores;
    the ANSI-literal hosts above reject it, so for those the value becomes an
    ANSI ``timestamp '...'`` literal, exact to the second. (A ``date``
    literal compared whole days: it re-read the watermark's day on every
    poll, and a day holding more rows than the batch cap never let the
    watermark leave it.) Shared by the scheduler's incremental filter and the
    backfill loader's windowed filter so both stay query-shape compatible.

    The stored value is UTC, but an ArcGIS layer whose
    ``dateFieldsTimeReference`` names a zone reads every literal, ISO or
    ANSI, as local time there. ``time_zone`` renders the value in that zone;
    without it DC's 311 filter started four hours late (Eastern) and skipped
    the requests filed in between.

    A text column whose format is not year first cannot be compared as text,
    so an ArcGIS or Socrata server gets the dates themselves
    (``text_date_window``).
    """
    if casts_text_watermark(endpoint, watermark_type, watermark_format):
        escaped = value.replace("'", "''")
        pg_format = "MM/DD/YYYY HH12:MI:SS AM"
        return (
            f'to_timestamp("{watermark_col}", \'{pg_format}\') {op} '
            f"to_timestamp('{escaped}', '{pg_format}')"
        )
    if (
        watermark_type == "text"
        and watermark_format
        and not text_sorts_as_dates(watermark_format)
        and _server_reads_where(endpoint)
    ):
        window = text_date_window(watermark_col, op, value, watermark_format, today=today)
        if window is not None:
            return window
    parsed = parse_watermark(value) if watermark_type != "text" else None
    if parsed is not None and time_zone:
        try:
            parsed = parsed.astimezone(ZoneInfo(time_zone))
        except (ZoneInfoNotFoundError, ValueError):
            logger.warning("Unknown time zone %r; comparing %s in UTC", time_zone, watermark_col)
    if any(host in endpoint for host in ANSI_DATE_LITERAL_HOSTS):
        if parsed is None:
            return f"{watermark_col} {op} date '{value[:10]}'"
        return f"{watermark_col} {op} timestamp '{parsed:%Y-%m-%d %H:%M:%S}'"
    if parsed is not None and time_zone:
        return f"{watermark_col} {op} '{parsed:%Y-%m-%dT%H:%M:%S}'"
    return f"{watermark_col} {op} '{value}'"
