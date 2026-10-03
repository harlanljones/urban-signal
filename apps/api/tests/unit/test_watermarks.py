from datetime import UTC, date, datetime

import pytest

from src.producers.watermarks import (
    compare_watermarks,
    newest_typed_watermark,
    newest_watermark,
    sort_watermarks,
    text_date_window,
    text_sorts_as_dates,
    typed_watermark_entry,
    watermark_comparison,
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


def test_nyc_permits_poll_names_its_month_first_dates():
    """NYC's ``issuance_date`` is text, ISO through 2020-06-05 and MM/DD/YYYY
    since, so ``issuance_date >= '2023-03-13T00:00:00'`` compared it as text
    and read nothing after a feed's first poll. Declared month-first, the poll
    names the dates, from a raw watermark or the ISO one the old spec stored.
    (``dobrundate`` cannot drive it: a reload stamps nearly every row.)"""
    from src.spatial.city_registry import CityId, FeedType, get_dataset

    spec = get_dataset(CityId.NYC, FeedType.PERMITS)
    assert (spec.watermark_col, spec.watermark_type, spec.watermark_format) == (
        "issuance_date",
        "text",
        "%m/%d/%Y",
    )
    kw = {
        "watermark_type": spec.watermark_type,
        "watermark_format": spec.watermark_format,
        "today": date(2026, 10, 2),
    }
    window = "issuance_date IN ('10/01/2026', '10/1/2026', '10/02/2026', '10/2/2026')"
    assert watermark_comparison("issuance_date", ">=", "10/01/2026", spec.endpoint, **kw) == window
    assert watermark_comparison("issuance_date", ">", "2026-09-30T00:00:00", spec.endpoint, **kw) == window


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


_CHARLOTTE = "https://gis.charlottenc.gov/arcgis/rest/services/ODP/ServiceRequests311/MapServer/0"
_DC_311 = "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/21"
_GREENVILLE = "https://citygis.greenvillesc.gov/arcgis/rest/services/Permits/MapServer/0"


def test_a_literal_only_host_takes_an_exact_timestamp():
    """A ``date`` literal compared whole days: every poll re-read the day, and
    a day with more rows than the cap never let the watermark leave it."""
    assert watermark_comparison("RECEIVED_DATE", ">", "2026-09-29T18:23:07", _CHARLOTTE) == (
        "RECEIVED_DATE > timestamp '2026-09-29 18:23:07'"
    )


def test_a_layer_zone_renders_the_watermark_as_local_time():
    """DC's 311 layer reads literals as Eastern time: 01:30 UTC is 21:30 the
    evening before, where the UTC day's ``date`` literal started at 04:00 UTC
    and skipped the requests filed in between."""
    assert watermark_comparison(
        "ADDDATE", ">", "2026-09-30T01:30:00", _DC_311, time_zone="America/New_York"
    ) == "ADDDATE > timestamp '2026-09-29 21:30:00'"
    # Standard time: five hours behind.
    assert watermark_comparison(
        "ADDDATE", ">", "2026-01-15T01:30:00", _DC_311, time_zone="America/New_York"
    ) == "ADDDATE > timestamp '2026-01-14 20:30:00'"


def test_an_iso_host_with_a_zone_takes_a_local_iso_string():
    """Greenville takes ISO strings but reads them as Eastern time, so a
    date-only row stored at local midnight (04:00 UTC) matches only 00:00."""
    assert watermark_comparison(
        "NewIssueDate", ">=", "2026-09-25T04:00:00", _GREENVILLE, time_zone="America/New_York"
    ) == "NewIssueDate >= '2026-09-25T00:00:00'"
    # Without a zone the stored string passes through untouched.
    assert watermark_comparison("NewIssueDate", ">=", "2026-09-25T04:00:00", _GREENVILLE) == (
        "NewIssueDate >= '2026-09-25T04:00:00'"
    )


def test_text_watermarks_and_unknown_zones_keep_the_stored_value(caplog):
    assert watermark_comparison(
        "DOCDATE", ">=", "20260916", _GREENVILLE,
        watermark_type="text", watermark_format="%Y%m%d", time_zone="America/Los_Angeles",
    ) == "DOCDATE >= '20260916'"
    with caplog.at_level("WARNING"):
        got = watermark_comparison("col", ">", "2026-09-29T18:23:07", _GREENVILLE, time_zone="Mars/Olympus")
    assert got == "col > '2026-09-29T18:23:07'"
    assert "Mars/Olympus" in caplog.text



_RENO = "https://gisweb.washoecounty.gov/arcgis/rest/services/OpenData/WashoeDataShare/MapServer/0"
_HONOLULU = "https://data.honolulu.gov/resource/jdy7-ftwe.json"


@pytest.mark.parametrize(
    ("fmt", "sorts"),
    [
        ("%Y%m%d", True),
        ("%Y-%m-%d %H:%M:%S.%f", True),
        ("%Y/%m/%d", True),
        ("%Y", True),
        ("%m/%d/%Y", False),
        ("%B %d, %Y at %I:%M %p", False),
        (None, False),
    ],
)
def test_only_a_year_first_format_sorts_as_dates(fmt, sorts):
    assert text_sorts_as_dates(fmt) is sorts


def test_a_text_window_names_each_day_to_today():
    """As text, ``SALEDATE > '09/21/2026'`` read September 22 to December 31
    of every past year. The window names the days, padded and unpadded."""
    assert text_date_window("SALEDATE", ">=", "09/28/2026", "%m/%d/%Y", today=date(2026, 9, 30)) == (
        "SALEDATE IN ('09/28/2026', '9/28/2026', '09/29/2026', '9/29/2026', '09/30/2026', '9/30/2026')"
    )
    # A strict boundary on a date-only column starts the next day.
    assert text_date_window("SALEDATE", ">", "09/28/2026", "%m/%d/%Y", today=date(2026, 9, 30)) == (
        "SALEDATE IN ('09/29/2026', '9/29/2026', '09/30/2026', '9/30/2026')"
    )
    # Worcester writes 9/9/2026, which sorted above 9/30/2026.
    assert text_date_window("D", ">=", "9/9/2026", "%m/%d/%Y", today=date(2026, 9, 10)) == (
        "D IN ('09/09/2026', '9/9/2026', '09/10/2026', '9/10/2026')"
    )
    # Into a new month, both months' days are named; October's are written
    # the same padded and unpadded from the 10th.
    got = text_date_window("D", ">=", "9/29/2026", "%m/%d/%Y", today=date(2026, 10, 10))
    assert got.startswith("D IN ('09/29/2026', '9/29/2026', '09/30/2026', '9/30/2026', '10/01/2026', '10/1/2026'")
    assert got.endswith("'10/09/2026', '10/9/2026', '10/10/2026')")


def test_a_long_text_window_takes_whole_months_and_years():
    got = text_date_window("SALEDATE", ">=", "12/30/2023", "%m/%d/%Y", today=date(2026, 2, 1))
    assert got == (
        "(SALEDATE IN ('12/30/2023', '12/31/2023', '02/01/2026', '2/1/2026')"
        " OR SALEDATE LIKE '%/2024' OR SALEDATE LIKE '%/2025'"
        " OR SALEDATE LIKE '01/%/2026' OR SALEDATE LIKE '1/%/2026')"
    )


def test_a_time_of_day_matches_any_text():
    """Honolulu writes ``September 29, 2026 at 10:17 PM``: the watermark's
    own day is read whole, and the dedup drops the rows already seen."""
    got = text_date_window(
        "date_created", ">", "September 29, 2026 at 10:17 PM", "%B %d, %Y at %I:%M %p",
        today=date(2026, 10, 1),
    )
    assert got == (
        "(date_created LIKE 'September 29, 2026 at %' OR date_created LIKE 'September 30, 2026 at %'"
        " OR date_created LIKE 'October 01, 2026 at %' OR date_created LIKE 'October 1, 2026 at %')"
    )


@pytest.mark.parametrize(
    ("value", "fmt"),
    [
        ("not a date", "%m/%d/%Y"),
        ("09/2026", "%m/%Y"),
        ("2026_09_28", "%Y_%m_%d"),
        ("09/28/2026 +0000", "%m/%d/%Y %z%j"),
    ],
)
def test_a_value_or_format_it_cannot_name_gives_no_window(value, fmt):
    assert text_date_window("D", ">=", value, fmt, today=date(2026, 9, 30)) is None


def test_the_server_gets_the_dates_where_text_would_not_sort():
    kw = {"watermark_type": "text", "watermark_format": "%m/%d/%Y", "today": date(2026, 9, 29)}
    assert watermark_comparison("SALEDATE", ">=", "09/28/2026", _RENO, **kw) == (
        "SALEDATE IN ('09/28/2026', '9/28/2026', '09/29/2026', '9/29/2026')"
    )
    assert watermark_comparison(
        "date_created", ">=", "September 29, 2026 at 12:00 AM", _HONOLULU,
        watermark_type="text", watermark_format="%B %d, %Y at %I:%M %p", today=date(2026, 9, 29),
    ) == "date_created LIKE 'September 29, 2026 at %'"
    # A CSV client compares the column as dates itself; San Jose's CKAN
    # filter casts both sides; a year-first format sorts as text.
    assert watermark_comparison("sale_date", ">=", "09/28/2026", "https://data.example/sales.csv", **kw) == (
        "sale_date >= '09/28/2026'"
    )
    assert watermark_comparison(
        "ISSUEDATE", ">", "9/28/2026 1:00:00 PM", "ckan://data.sanjoseca.gov/x",
        watermark_type="text", watermark_format="%m/%d/%Y %I:%M:%S %p",
    ).startswith('to_timestamp("ISSUEDATE"')
    assert watermark_comparison(
        "DOCDATE", ">", "20260928", _RENO, watermark_type="text", watermark_format="%Y%m%d"
    ) == "DOCDATE > '20260928'"
