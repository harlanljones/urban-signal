from datetime import UTC, datetime

from src.producers.watermarks import compare_watermarks, newest_watermark, sort_watermarks


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
