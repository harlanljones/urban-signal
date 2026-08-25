from datetime import UTC, datetime

from src.producers.watermarks import (
    compare_watermarks,
    newest_typed_watermark,
    newest_watermark,
    sort_watermarks,
    typed_watermark_entry,
    watermark_exclude_clause,
)

NYC_MIXED_WATERMARKS = [
    "2020-06-05",
    "08/21/2026",
    "08/20/2026",
    "20260819",
    "2026-08-18T12:30:00Z",
]


def test_mixed_nyc_formats_compare_by_calendar_value():
    assert compare_watermarks("08/21/2026", "2020-06-05") == 1
    assert compare_watermarks("2020-06-05", "08/21/2026") == -1
    assert newest_watermark(NYC_MIXED_WATERMARKS) == datetime(2026, 8, 21, tzinfo=UTC)


def test_sort_preserves_raw_values_but_uses_typed_order():
    assert sort_watermarks(NYC_MIXED_WATERMARKS) == [
        "2020-06-05",
        "2026-08-18T12:30:00Z",
        "20260819",
        "08/20/2026",
        "08/21/2026",
    ]


def test_invalid_and_empty_watermarks_sort_below_valid_values():
    assert compare_watermarks(None, "2026-08-21") == -1
    assert compare_watermarks("not-a-date", "") == 0
    assert newest_watermark([None, "", "not-a-date"]) is None


def test_typed_entry_drops_sentinels_and_unparseable_values():
    exclude = ("ZZZZZZZZ",)
    entry = typed_watermark_entry("20260815", fmt="%Y%m%d", exclude=exclude)
    assert entry == ("20260815", datetime(2026, 8, 15, tzinfo=UTC))
    assert typed_watermark_entry("ZZZZZZZZ", fmt="%Y%m%d", exclude=exclude) is None
    assert typed_watermark_entry("garbage", fmt="%Y%m%d") is None
    assert typed_watermark_entry("", exclude=exclude) is None
    assert typed_watermark_entry(None) is None


def test_newest_typed_watermark_uses_calendar_order_not_lexical():
    rows = ["ZZZZZZZZ", "20260801", "20260915"]
    best = newest_typed_watermark(rows, fmt="%Y%m%d", exclude=("ZZZZZZZZ",))
    assert best == ("20260915", datetime(2026, 9, 15, tzinfo=UTC))
    mixed = ["2020-06-05", "08/21/2026", "20260819"]
    best = newest_typed_watermark(mixed)
    assert best == ("08/21/2026", datetime(2026, 8, 21, tzinfo=UTC))
    assert newest_typed_watermark(["ZZZZZZZZ"], fmt="%Y%m%d", exclude=("ZZZZZZZZ",)) is None


def test_sdat_yyyy_mm_dd_text_watermark_parses_under_default_formats():
    """US-128 (MD SDAT deeds): the transfer-date watermark is dotted text
    ``YYYY.MM.DD``. It must parse through the default multi-format parser AND
    the caller must be able to declare it via fmt, while the no-sale sentinel
    ``0000.00.00`` stays None (month 0 is unparseable) rather than becoming a date."""
    from src.producers.watermarks import parse_watermark

    parsed = parse_watermark("2026.07.24")
    assert parsed == datetime(2026, 7, 24, tzinfo=UTC)
    with_sentinel = parse_watermark("0000.00.00")
    assert with_sentinel is None
    entry = typed_watermark_entry("2018.08.03", fmt="%Y.%m.%d")
    assert entry == ("2018.08.03", datetime(2018, 8, 3, tzinfo=UTC))
    assert newest_watermark(["0000.00.00", "2026.07.24", "2026.07.06"]) == datetime(2026, 7, 24, tzinfo=UTC)


def test_exclude_clause_quotes_and_skips_empty():
    assert (
        watermark_exclude_clause("transfer_date", ["ZZZZZZZZ"])
        == "transfer_date NOT IN ('ZZZZZZZZ')"
    )
    assert watermark_exclude_clause("col", ["O'BRIEN", ""]) == "col NOT IN ('O''BRIEN')"
    assert watermark_exclude_clause("col", []) is None
