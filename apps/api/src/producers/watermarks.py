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
)


def parse_watermark(value: Any) -> datetime | None:
    """Parse supported API watermark values into UTC-aware datetimes.

    Municipal APIs expose watermarks as ISO/RFC3339 strings, NYC's historical
    ``MM/DD/YYYY`` text, compact ``YYYYMMDD`` text, dates, datetimes, or epoch
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
