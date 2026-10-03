from datetime import UTC, date, datetime, timedelta
from functools import partial
from unittest.mock import MagicMock

from scripts.feed_staleness_probe import (
    newest_watermark,
    page_stale,
    parse_timestamp,
    probe_feed,
    probe_registry,
)

from src.spatial.city_registry import DatasetSpec, FeedType


def test_parse_timestamp_handles_mixed_text_watermarks():
    assert parse_timestamp("08/21/2026") > parse_timestamp("2020-06-05")
    assert parse_timestamp("20260821") == datetime(2026, 8, 21, tzinfo=UTC)


def test_probe_feed_catches_deliberately_stale_fixture():
    client = MagicMock()
    client.paginate.return_value = [[
        {"issued": "2026-08-01"},
        {"issued": "2026-08-10"},
    ]]
    now = datetime(2026, 8, 23, tzinfo=UTC)
    result = probe_feed(
        "nyc",
        FeedType.PERMITS,
        DatasetSpec(endpoint="https://data.example/resource/test.json", watermark_col="issued"),
        now=now,
        client=client,
        source_updated_at=datetime(2026, 8, 10, tzinfo=UTC),
    )
    assert result.newest_watermark == datetime(2026, 8, 10, tzinfo=UTC)
    assert result.age_days == 13
    assert result.stale
    # By value, then by row id (the column's type is left open).
    assert client.paginate.call_count == 2


def test_probe_feed_pages_when_both_sources_are_stale():
    client = MagicMock()
    client.paginate.return_value = [[{"issued": "2026-08-01"}]]
    result = probe_feed(
        "nyc",
        FeedType.PERMITS,
        DatasetSpec(endpoint="https://data.example/resource/test.json", watermark_col="issued"),
        now=datetime(2026, 8, 23, tzinfo=UTC),
        client=client,
        source_updated_at=datetime(2026, 8, 1, tzinfo=UTC),
        threshold=timedelta(days=7),
    )
    assert result.stale
    assert result.age_days == 22


def test_newest_watermark_excludes_declared_sentinels_server_side():
    client = MagicMock()
    client.paginate.return_value = [[
        {"transfer_date": "ZZZZZZZZ"},
        {"transfer_date": "20260815"},
    ]]
    spec = DatasetSpec(
        endpoint="https://data.example/resource/test.json",
        watermark_col="transfer_date",
        watermark_type="text",
        watermark_format="%Y%m%d",
        watermark_exclude=["ZZZZZZZZ"],
    )
    now = datetime(2026, 8, 23, tzinfo=UTC)
    assert newest_watermark(client, spec, now=now) == datetime(2026, 8, 15, tzinfo=UTC)
    _, kwargs = client.paginate.call_args
    assert kwargs["where_clause"] == (
        "(transfer_date IS NOT NULL) AND transfer_date NOT IN ('ZZZZZZZZ')"
    )


def test_newest_watermark_without_declarations_asks_only_for_set_values():
    client = MagicMock()
    client.paginate.return_value = [[{"issued": "2026-08-01"}]]
    spec = DatasetSpec(endpoint="https://data.example/resource/test.json", watermark_col="issued")
    newest_watermark(client, spec, now=datetime(2026, 8, 23, tzinfo=UTC))
    _, kwargs = client.paginate.call_args
    assert kwargs["where_clause"] == "(issued IS NOT NULL)"


def test_newest_watermark_ignores_future_rows():
    client = MagicMock()
    client.paginate.return_value = [[
        {"issued": "2026-08-21"},
        {"issued": "2027-05-01"},
    ]]
    spec = DatasetSpec(endpoint="https://data.example/resource/test.json", watermark_col="issued")
    newest = newest_watermark(client, spec, now=datetime(2026, 8, 23, tzinfo=UTC))
    assert newest == datetime(2026, 8, 21, tzinfo=UTC)


def test_probe_feed_ignores_future_rows_and_reports_fresh():
    client = MagicMock()
    client.paginate.return_value = [[
        {"issued": "2026-08-21"},
        {"issued": "2027-05-01"},
    ]]
    result = probe_feed(
        "nyc",
        FeedType.PERMITS,
        DatasetSpec(endpoint="https://data.example/resource/test.json", watermark_col="issued"),
        now=datetime(2026, 8, 23, tzinfo=UTC),
        client=client,
        source_updated_at=datetime(2026, 8, 21, tzinfo=UTC),
    )
    assert result.newest_watermark == datetime(2026, 8, 21, tzinfo=UTC)
    assert result.age_days == 2
    assert not result.stale


def test_probe_feed_treats_all_future_watermarks_as_stale():
    client = MagicMock()
    client.paginate.return_value = [[{"issued": "2027-05-01"}]]
    result = probe_feed(
        "nyc",
        FeedType.PERMITS,
        DatasetSpec(endpoint="https://data.example/resource/test.json", watermark_col="issued"),
        now=datetime(2026, 8, 23, tzinfo=UTC),
        client=client,
    )
    assert result.newest_watermark is None
    assert result.stale


def test_probe_feed_reports_client_failure_as_stale():
    client = MagicMock()
    client.paginate.side_effect = RuntimeError("fixture intentionally stale")
    result = probe_feed(
        "nyc",
        FeedType.PERMITS,
        DatasetSpec(endpoint="https://data.example/resource/test.json", watermark_col="issued"),
        now=datetime(2026, 8, 23, tzinfo=UTC),
        client=client,
    )
    assert result.stale
    assert "fixture intentionally stale" in result.error


def test_probe_registry_uses_registered_city_feeds_without_manual_config():
    client = MagicMock()
    client.paginate.return_value = [[{"issued": "2026-08-22"}]]
    results = probe_registry(
        city_ids={"nyc"},
        now=datetime(2026, 8, 23, tzinfo=UTC),
        client_factory=lambda spec: client,
        metadata_fetcher=lambda spec: datetime(2026, 8, 22, tzinfo=UTC),
    )
    assert {result.city_id for result in results} == {"nyc"}
    # Pinned as a set rather than a count so adding or dropping a feed names
    # itself in the diff: permits, 311, sla, deeds, crime (US-71), evictions
    # (US-93), energy_benchmark + bike_ped (US-363 §2.7/§2.8), GBFS
    # (US-363 §1.2), inspections (NYC food-service), childcare (US-377).
    assert {result.feed for result in results} == {
        "permits",
        "311",
        "sla",
        "deeds",
        "crime",
        "evictions",
        "energy_benchmark",
        "bike_ped",
        "gbfs",
        "inspections",
        "childcare",
    }
    assert all(not result.stale for result in results)


def test_page_stale_serializes_timestamps_and_posts_to_every_webhook(monkeypatch):
    captured = []

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, *, json):
            captured.append((url, json))
            return type("Response", (), {"status_code": 202})()

    monkeypatch.setattr("scripts.feed_staleness_probe.httpx.Client", lambda timeout: FakeClient())
    result = probe_feed(
        "nyc",
        FeedType.PERMITS,
        DatasetSpec(endpoint="https://data.example/resource/test.json", watermark_col="issued"),
        now=datetime(2026, 8, 23, tzinfo=UTC),
        client=MagicMock(),
        source_updated_at=datetime(2026, 8, 1, tzinfo=UTC),
    )

    webhook_urls = [
        "https://staging.example/hooks/feed-staleness",
        "https://staging.example/hooks/backup-staleness",
    ]
    assert page_stale([result], webhook_urls) == [202, 202]
    assert [url for url, _ in captured] == webhook_urls
    assert captured[0][1]["event"] == "feed_staleness"
    assert captured[0][1]["stale_feeds"][0]["source_updated_at"] == "2026-08-01T00:00:00+00:00"
    assert captured[0][1] == captured[1][1]


def test_declared_cadence_sets_alarm_window():
    from scripts.feed_staleness_probe import declared_staleness_threshold

    spec = DatasetSpec(
        endpoint="https://data.example/resource/test.json",
        watermark_col="issued",
        expected_cadence_days=30,
    )
    assert declared_staleness_threshold(spec) == timedelta(days=60)


def test_missing_or_invalid_declaration_falls_back():
    from scripts.feed_staleness_probe import STALE_AFTER, declared_staleness_threshold

    plain = DatasetSpec(endpoint="https://data.example/resource/test.json")
    assert declared_staleness_threshold(plain) is STALE_AFTER
    for bad in ({"expected_cadence_days": 0}, {"expected_cadence_days": "soon"}):
        spec = DatasetSpec(endpoint="u", **bad)
        assert declared_staleness_threshold(spec, fallback=timedelta(days=3)) == timedelta(days=3)


def test_rollover_rebaseline_does_not_page_staleness_monitor():
    """US-70: at New Year the probe re-baselines against the NEXT year's layer
    (resolve_endpoint is date-aware); a fresh new-year source must not page."""
    from dataclasses import asdict

    from scripts.feed_staleness_probe import declared_staleness_threshold

    from src.spatial.city_registry import resolve_endpoint

    by_year = {
        "2026": "https://fake.example/FeatureServer/18",
        "2027": "https://fake.example/FeatureServer/19",
    }
    spec = DatasetSpec(
        endpoint="https://fake.example/base",
        watermark_col="ADDDATE",
        endpoint_by_year=by_year,
        expected_cadence_days=7,
    )
    now = datetime(2027, 1, 2, 12, 0, tzinfo=UTC)
    rolled = DatasetSpec(**{**asdict(spec), "endpoint": resolve_endpoint(spec, today=now.date())})

    client = MagicMock()
    client.paginate.return_value = [[{"ADDDATE": "2027-01-02T08:00:00"}]]
    result = probe_feed(
        "washington_dc",
        FeedType.COMPLAINTS_311,
        rolled,
        now=now,
        client=client,
        source_updated_at=datetime(2027, 1, 2, 9, 0, tzinfo=UTC),
        threshold=declared_staleness_threshold(rolled),
    )
    assert result.endpoint == "https://fake.example/FeatureServer/19"
    assert result.newest_watermark == datetime(2027, 1, 2, 8, 0, tzinfo=UTC)
    assert result.age_days is not None and result.age_days < 0.5
    assert result.stale is False


def test_probe_alarms_at_twice_declared_cadence_not_global_seven():
    from scripts.feed_staleness_probe import declared_staleness_threshold

    client = MagicMock()
    client.paginate.return_value = [[{"issued": "2026-07-01"}]]
    monthly = DatasetSpec(
        endpoint="https://data.example/resource/test.json",
        watermark_col="issued",
        expected_cadence_days=30,
    )
    now = datetime(2026, 8, 23, tzinfo=UTC)
    # 53 days old: beyond the old global 7-day window, inside 2 x 30
    result = probe_feed(
        "nyc",
        FeedType.PERMITS,
        monthly,
        now=now,
        client=client,
        threshold=declared_staleness_threshold(monthly),
    )
    assert result.stale is False

    stale = probe_feed(
        "nyc",
        FeedType.PERMITS,
        monthly,
        now=now,
        client=client,
        threshold=declared_staleness_threshold(monthly),
        source_updated_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    assert stale.stale is True


def test_probe_registry_applies_per_feed_declared_thresholds():
    """Wiring proof: an 8-day-old NYC feed is healthy under the backfilled
    N=7 declaration (alarm at 14d) though the legacy global 7 flagged it."""
    from scripts.feed_staleness_probe import probe_registry

    client = MagicMock()
    client.paginate.return_value = [[{"issuance_date": "2026-08-15"}]]
    results = probe_registry(
        now=datetime(2026, 8, 23, tzinfo=UTC),
        city_ids={"nyc"},
        client_factory=lambda spec: client,
        metadata_fetcher=lambda spec: None,
    )
    # Only permits matches the mocked watermark column; others read stale
    # because their columns are absent from the fixture rows.
    permits = next(result for result in results if result.feed == "permits")
    assert permits.stale is False and abs(permits.age_days - 8.0) < 1e-9


def test_a_yearly_csv_endpoint_is_dated_by_this_years_file(monkeypatch):
    """Pima County's sales endpoint is written with ``{year}``: the probe asks
    for this year's file, never the template."""
    import scripts.feed_staleness_probe as probe

    from src.producers.csv_client import yearly_files

    monkeypatch.setattr(probe, "yearly_files", partial(yearly_files, today=date(2026, 10, 2)))
    request = MagicMock(return_value=MagicMock(headers={"last-modified": "Fri, 02 Oct 2026 07:20:45 GMT"}))
    spec = DatasetSpec(endpoint="https://example.test/sales/{year}//SALE{year}.ZIP", platform="csv")

    assert probe.fetch_source_updated_at(spec, request) == datetime(2026, 10, 2, 7, 20, 45, tzinfo=UTC)
    request.assert_called_once_with("https://example.test/sales/2026//SALE2026.ZIP")


# ---------------------------------------------------------------------------
# A run that finishes: short newest-first reads, the poll's own filter, hosts
# side by side, a deadline (2026-10-02: every scheduled run since at least
# 2026-08-31 was cancelled at the job's 20-minute limit with no output).
# ---------------------------------------------------------------------------


LAYER = {"date_fields": {"IssueDate"}, "oid_field": "OBJECTID"}


def _reads(spec, rows=None, layer=LAYER):
    """Each read the probe makes of ``spec``: its paginate kwargs."""
    client = MagicMock()
    client.paginate.return_value = [rows or []]
    client.get_layer_metadata.return_value = layer
    newest_watermark(client, spec, now=datetime(2026, 10, 2, tzinfo=UTC))
    return [call.kwargs for call in client.paginate.call_args_list]


def test_a_date_column_is_read_newest_first_alone_and_through_the_feeds_filter():
    from scripts.feed_staleness_probe import NEWEST_ROWS

    spec = DatasetSpec(
        endpoint="https://example.test/arcgis/rest/services/Permits/FeatureServer/0",
        platform="arcgis",
        watermark_col="IssueDate",
        where="Permit_Type IN ('Building Permit')",
        select="OBJECTID,Permit,IssueDate",
    )
    [read] = _reads(spec)
    assert read["where_clause"] == "((Permit_Type IN ('Building Permit')) AND IssueDate IS NOT NULL)"
    assert read["order_by"] == "IssueDate DESC"
    assert read["select"] == "IssueDate"
    assert read["max_records"] == NEWEST_ROWS


def test_an_open_typed_text_column_on_a_layer_is_read_by_value_and_by_object_id():
    """Worcester's work orders write their day as text ("2026-09-30"), and the
    table's object ids do not follow it: its newest 1,000 by object id were
    logged in January 2021."""
    from scripts.feed_staleness_probe import FULL_PAGE_ROWS, NEWEST_ROWS

    spec = DatasetSpec(
        endpoint="https://example.test/arcgis/rest/services/Requests/FeatureServer/0",
        platform="arcgis",
        watermark_col="Date_Logged",
    )
    client = MagicMock()
    client.get_layer_metadata.return_value = {"date_fields": set(), "oid_field": "ObjectId"}
    client.paginate.side_effect = [
        [[{"Date_Logged": "2026-09-30"}, {"Date_Logged": "2026-09-29"}]],
        [[{"Date_Logged": "2021-01-12"}]],
    ]
    newest = newest_watermark(client, spec, now=datetime(2026, 10, 2, tzinfo=UTC))
    assert newest == datetime(2026, 9, 30, tzinfo=UTC)
    reads = [(call.kwargs["order_by"], call.kwargs["max_records"]) for call in client.paginate.call_args_list]
    assert reads == [("Date_Logged DESC", NEWEST_ROWS), ("ObjectId DESC", FULL_PAGE_ROWS)]


def test_an_open_typed_columns_row_id_read_is_a_full_page():
    """Lincoln's permits keep their issue date as month-first text the spec
    leaves untyped, and their ids drift from their dates. Read by value,
    December sorts last ("12/30/2025"); the newest 100 by object id end on
    2025-12-23, and the newest 1,000 reach 2026-01-22."""
    from scripts.feed_staleness_probe import FULL_PAGE_ROWS, NEWEST_ROWS

    spec = DatasetSpec(
        endpoint="https://example.test/arcgis/rest/services/Permits/MapServer/4",
        platform="arcgis",
        watermark_col="Issued",
    )
    client = MagicMock()
    client.get_layer_metadata.return_value = {"date_fields": {"SD_APP_DD"}, "oid_field": "OBJECTID_1"}
    by_object_id = [{"Issued": "12/23/2025"}] * 795 + [{"Issued": "01/22/2026"}] + [{"Issued": "11/04/2025"}] * 204
    client.paginate.side_effect = [[[{"Issued": "12/30/2025"}] * 100], [by_object_id]]
    newest = newest_watermark(client, spec, now=datetime(2026, 10, 2, tzinfo=UTC))
    assert newest == datetime(2026, 1, 22, tzinfo=UTC)
    reads = [(call.kwargs["order_by"], call.kwargs["max_records"]) for call in client.paginate.call_args_list]
    assert reads == [("Issued DESC", NEWEST_ROWS), ("OBJECTID_1 DESC", FULL_PAGE_ROWS)]


def test_an_open_typed_column_is_read_by_value_and_by_row_id():
    """NYC's permits keep their issue date as text, "2020-06-05" on old rows
    and "09/30/2026" on new ones: a descending read by value stops in 2020."""
    from scripts.feed_staleness_probe import FULL_PAGE_ROWS, NEWEST_ROWS

    spec = DatasetSpec(
        endpoint="https://data.cityofnewyork.us/resource/ipu4-2q9a.json",
        watermark_col="issuance_date",
    )
    client = MagicMock()
    client.paginate.side_effect = [
        [[{"issuance_date": "2020-06-05"}, {"issuance_date": "2020-06-04"}]],
        [[{"issuance_date": "09/30/2026"}, {"issuance_date": "09/29/2026"}]],
    ]
    newest = newest_watermark(client, spec, now=datetime(2026, 10, 2, tzinfo=UTC))
    assert newest == datetime(2026, 9, 30, tzinfo=UTC)
    reads = [(call.kwargs["order_by"], call.kwargs["max_records"]) for call in client.paginate.call_args_list]
    assert reads == [("issuance_date DESC", NEWEST_ROWS), (":id DESC", FULL_PAGE_ROWS)]


def test_ckan_is_read_without_the_guard_that_would_send_it_to_sql():
    from scripts.feed_staleness_probe import FULL_PAGE_ROWS, NEWEST_ROWS

    spec = DatasetSpec(
        endpoint="https://data.example/api/3/action/datastore_search?resource_id=abc",
        platform="ckan",
        watermark_col="SALEDATE",
    )
    reads = _reads(spec)
    assert [read["where_clause"] for read in reads] == [None, None]
    assert [(read["order_by"], read["max_records"]) for read in reads] == [
        ("SALEDATE DESC", NEWEST_ROWS),
        ("_id DESC", FULL_PAGE_ROWS),
    ]


def test_ckan_reads_by_row_id_whatever_the_columns_type():
    """With no existence check, a descending read on CKAN puts rows without a
    date first: the newest 100 of Boston's inspection results by date had no
    result date at all."""
    from scripts.feed_staleness_probe import FULL_PAGE_ROWS, NEWEST_ROWS

    spec = DatasetSpec(
        endpoint="ckan://data.example/abc",
        platform="ckan",
        watermark_col="resultdttm",
        watermark_type="text",
        watermark_format="%Y-%m-%d %H:%M:%S+00",
    )
    client = MagicMock()
    client.paginate.side_effect = [[[{"resultdttm": None}] * 100], [[{"resultdttm": "2026-09-30 14:05:00+00"}]]]
    newest = newest_watermark(client, spec, now=datetime(2026, 10, 2, tzinfo=UTC))
    assert newest == datetime(2026, 9, 30, 14, 5, tzinfo=UTC)
    reads = [(call.kwargs["order_by"], call.kwargs["max_records"]) for call in client.paginate.call_args_list]
    assert reads == [("resultdttm DESC", NEWEST_ROWS), ("_id DESC", FULL_PAGE_ROWS)]


WORCESTER_PERMITS = DatasetSpec(
    endpoint="https://example.test/arcgis/rest/services/Building_Permits/FeatureServer/0",
    platform="arcgis",
    watermark_col="Issued",
    watermark_type="text",
    watermark_format="%m/%d/%Y",
    where="Status <> 'Void'",
)
WORCESTER_LAYER = {"date_fields": set(), "oid_field": "ObjectId"}


def test_month_first_text_dates_are_read_by_naming_the_last_weeks_dates():
    """"9/4/2026" sorts after "10/1/2026" as text, and Worcester's newest
    permits hold its lowest object ids: its newest 1,000 by object id were
    issued in 2015. The poll names the dates it wants, and so does the probe."""
    from scripts.feed_staleness_probe import FULL_PAGE_ROWS

    client = MagicMock()
    client.get_layer_metadata.return_value = WORCESTER_LAYER
    client.paginate.return_value = [[{"Issued": "9/26/2026"}, {"Issued": "9/30/2026"}]]
    newest = newest_watermark(client, WORCESTER_PERMITS, now=datetime(2026, 10, 2, 12, tzinfo=UTC))
    assert newest == datetime(2026, 9, 30, tzinfo=UTC)
    [read] = [call.kwargs for call in client.paginate.call_args_list]
    assert (read["order_by"], read["max_records"]) == ("ObjectId DESC", FULL_PAGE_ROWS)
    assert read["where_clause"].startswith(
        "((Status <> 'Void') AND Issued IN ('09/25/2026', '9/25/2026', '09/26/2026', "
    )
    assert read["where_clause"].endswith("'10/02/2026', '10/2/2026'))")


def test_a_quiet_week_widens_the_window_until_one_holds_rows():
    client = MagicMock()
    client.get_layer_metadata.return_value = WORCESTER_LAYER
    client.paginate.side_effect = [[[]], [[]], [[{"Issued": "9/4/2026"}]]]
    newest = newest_watermark(client, WORCESTER_PERMITS, now=datetime(2026, 10, 2, 12, tzinfo=UTC))
    assert newest == datetime(2026, 9, 4, tzinfo=UTC)
    windows = [call.kwargs["where_clause"] for call in client.paginate.call_args_list]
    # A week, two weeks, then four weeks back.
    assert [window.split(" IN ('")[1][:10] for window in windows] == ["09/25/2026", "09/18/2026", "09/04/2026"]


def test_a_feed_with_no_dated_row_in_ten_years_has_no_newest_date():
    client = MagicMock()
    client.get_layer_metadata.return_value = WORCESTER_LAYER
    client.paginate.return_value = [[]]
    assert newest_watermark(client, WORCESTER_PERMITS, now=datetime(2026, 10, 2, 12, tzinfo=UTC)) is None
    windows = [call.kwargs["where_clause"] for call in client.paginate.call_args_list]
    assert len(windows) == 11
    assert "LIKE '%/2017'" in windows[-1] and "'10/04/2016'" in windows[-1]


def test_how_each_kind_of_text_date_is_read():
    from scripts.feed_staleness_probe import FULL_PAGE_ROWS, NEWEST_ROWS

    def reads(platform, fmt, value):
        spec = DatasetSpec(
            endpoint="https://example.test/layer/0",
            platform=platform,
            watermark_col="SaleDate",
            watermark_type="text",
            watermark_format=fmt,
        )
        return [
            (read["order_by"], read["max_records"], " LIKE " in (read["where_clause"] or "") or " IN (" in (read["where_clause"] or ""))
            for read in _reads(spec, rows=[{"SaleDate": value}])
        ]

    # Month first: the last week's dates, named, on a server that filters.
    assert reads("arcgis", "%m/%d/%Y", "10/1/2026") == [("OBJECTID DESC", FULL_PAGE_ROWS, True)]
    assert reads("socrata", "%B %d, %Y at %I:%M %p", "October 1, 2026 at 09:15 AM") == [
        (":id DESC", FULL_PAGE_ROWS, True)
    ]
    # San Jose's CKAN tables: the newest rows by row id, a full page.
    assert reads("ckan", "%m/%d/%Y %I:%M:%S %p", "10/1/2026 09:15:00 AM") == [("_id DESC", FULL_PAGE_ROWS, False)]
    # Year first, text sorts as the date does.
    assert reads("arcgis", "%Y%m%d", "20261001") == [("SaleDate DESC", NEWEST_ROWS, False)]
    assert reads("socrata", "%Y-%m-%d", "2026-10-01") == [("SaleDate DESC", NEWEST_ROWS, False)]


def test_month_first_text_dates_are_dated_by_their_newest_value_not_the_last_read():
    spec = DatasetSpec(
        endpoint="https://example.test/layer/0",
        platform="arcgis",
        watermark_col="SaleDate",
        watermark_type="text",
        watermark_format="%m/%d/%Y",
    )
    client = MagicMock()
    client.get_layer_metadata.return_value = LAYER
    client.paginate.return_value = [[{"SaleDate": "9/4/2026"}, {"SaleDate": "10/1/2026"}]]
    newest = newest_watermark(client, spec, now=datetime(2026, 10, 2, tzinfo=UTC))
    assert newest == datetime(2026, 10, 1, tzinfo=UTC)


def test_a_file_is_read_whole_with_the_options_its_poll_uses():
    spec = DatasetSpec(
        endpoint="https://example.test/datamart/sale.zip",
        platform="csv",
        watermark_col="sale_date",
        watermark_format="%m/%d/%Y",
        zip_member="sale.txt",
        delimiter="|",
        columns=["parcel", "sale_date", "price"],
        select="parcel,sale_date,price",
        where="price > '0'",
    )
    [kwargs] = _reads(spec)
    assert kwargs["max_records"] is None
    assert kwargs["where_clause"] == "(price > '0')"
    assert kwargs["zip_member"] == "sale.txt"
    assert kwargs["delimiter"] == "|"
    assert kwargs["columns"] == ["parcel", "sale_date", "price"]
    assert kwargs["select"] == "parcel,sale_date,price"
    assert kwargs["watermark_format"] == "%m/%d/%Y"


def test_a_files_dates_are_read_in_its_declared_format_whatever_their_type():
    """Boulder's sales write "9/15/2026 12:00:00 AM", which only the declared
    format reads; its CSV client compares them in that format too."""
    spec = DatasetSpec(
        endpoint="https://example.test/sales.csv",
        platform="csv",
        watermark_col="tdate",
        watermark_format="%m/%d/%Y %I:%M:%S %p",
    )
    client = MagicMock()
    client.paginate.return_value = [[{"tdate": "9/15/2026 12:00:00 AM"}, {"tdate": "9/30/2026 12:00:00 AM"}]]
    newest = newest_watermark(client, spec, now=datetime(2026, 10, 2, tzinfo=UTC))
    assert newest == datetime(2026, 9, 30, tzinfo=UTC)


def test_a_file_is_dated_by_its_headers_without_downloading_it():
    import scripts.feed_staleness_probe as probe

    request_json = MagicMock(side_effect=AssertionError("downloaded the file"))
    request_headers = MagicMock(
        return_value=MagicMock(headers={"last-modified": "Thu, 01 Oct 2026 06:00:00 GMT"})
    )
    spec = DatasetSpec(endpoint="https://example.test/sales.zip", platform="csv")
    assert probe.fetch_source_updated_at(spec, request_json, request_headers) == datetime(
        2026, 10, 1, 6, tzinfo=UTC
    )
    request_headers.assert_called_once_with("https://example.test/sales.zip")


def test_a_bike_share_feed_is_dated_by_its_last_updated_stamp():
    import scripts.feed_staleness_probe as probe

    spec = DatasetSpec(endpoint="https://gbfs.example/gbfs.json", platform="gbfs")
    seconds = MagicMock(return_value={"last_updated": 1790980800, "ttl": 60})
    assert probe.fetch_source_updated_at(spec, seconds) == datetime(2026, 10, 2, 22, 40, tzinfo=UTC)
    rfc3339 = MagicMock(return_value={"last_updated": "2026-10-02T22:40:00+00:00"})
    assert probe.fetch_source_updated_at(spec, rfc3339) == datetime(2026, 10, 2, 22, 40, tzinfo=UTC)
    # No rows to read, so no client.
    assert probe.client_for(spec) is None


def test_a_daily_feed_alarms_no_sooner_than_the_fallback_window():
    """A Monday run sees Friday's permits at best, and date-only values count
    from midnight: 2 x 1 days paged every weekday-only feed every week."""
    from scripts.feed_staleness_probe import STALE_AFTER, declared_staleness_threshold

    daily = DatasetSpec(endpoint="https://data.example/resource/test.json", expected_cadence_days=1)
    assert declared_staleness_threshold(daily) == STALE_AFTER
    assert declared_staleness_threshold(daily, fallback=timedelta(days=3)) == timedelta(days=3)
    weekly = DatasetSpec(endpoint="https://data.example/resource/test.json", expected_cadence_days=7)
    assert declared_staleness_threshold(weekly) == timedelta(days=14)


def test_the_arcgis_probe_reads_no_geometry_and_retries_once():
    import scripts.feed_staleness_probe as probe

    client = probe.client_for(DatasetSpec(endpoint="https://example.test/layer/0", platform="arcgis"))
    assert client.return_geometry is False
    # ``max_retries`` counts attempts: the first, and one retry.
    assert client.max_retries == probe.CLIENT_ATTEMPTS == 2


def _nyc_hosts():
    from collections import Counter

    from scripts.feed_staleness_probe import host_of

    from src.spatial.city_registry import REGISTRY, CityId

    return Counter(host_of(spec.endpoint) for spec in REGISTRY[CityId.NYC].datasets.values())


def test_feeds_on_one_host_are_probed_one_at_a_time_the_gap_apart():
    client = MagicMock()
    client.paginate.return_value = [[{"issued": "2026-10-01"}]]
    sleeps = []
    results = probe_registry(
        city_ids={"nyc"},
        now=datetime(2026, 10, 2, tzinfo=UTC),
        client_factory=lambda spec: client,
        metadata_fetcher=lambda spec: datetime(2026, 10, 1, tzinfo=UTC),
        workers=4,
        min_host_gap=2.2,
        clock=lambda: 100.0,
        sleep=sleeps.append,
    )
    assert len(results) == sum(_nyc_hosts().values())
    # The clock stands still, so every feed after a host's first waits the gap.
    assert sleeps == [2.2] * sum(count - 1 for count in _nyc_hosts().values())
    assert all(result.error is None for result in results)


def test_results_keep_the_registry_order():
    from src.spatial.city_registry import REGISTRY, CityId

    results = probe_registry(
        city_ids={"nyc"},
        now=datetime(2026, 10, 2, tzinfo=UTC),
        client_factory=lambda spec: MagicMock(paginate=MagicMock(return_value=[[]])),
        metadata_fetcher=lambda spec: datetime(2026, 10, 1, tzinfo=UTC),
        workers=8,
    )
    assert [result.feed for result in results] == [feed.value for feed in REGISTRY[CityId.NYC].datasets]


def test_feeds_on_an_excluded_host_are_not_probed():
    host, _ = _nyc_hosts().most_common(1)[0]
    parent = host.split(".", 1)[1]
    asked = []

    def factory(spec):
        asked.append(spec.endpoint)
        return MagicMock(paginate=MagicMock(return_value=[[{"issued": "2026-10-01"}]]))

    results = probe_registry(
        city_ids={"nyc"},
        now=datetime(2026, 10, 2, tzinfo=UTC),
        client_factory=factory,
        metadata_fetcher=lambda spec: datetime(2026, 10, 1, tzinfo=UTC),
        skip_hosts=[parent],
    )
    skipped = [result for result in results if result.endpoint.split("/")[2] == host]
    assert skipped and all(result.error.startswith("not probed") for result in skipped)
    assert not any(result.stale for result in skipped)
    assert not any(host in endpoint for endpoint in asked)


def test_feeds_not_started_by_the_deadline_are_not_probed():
    from itertools import chain, repeat

    ticks = chain([0.0], repeat(61.0))
    results = probe_registry(
        city_ids={"nyc"},
        now=datetime(2026, 10, 2, tzinfo=UTC),
        client_factory=lambda spec: MagicMock(),
        metadata_fetcher=lambda spec: datetime(2026, 10, 1, tzinfo=UTC),
        deadline=timedelta(minutes=1),
        clock=lambda: next(ticks),
    )
    assert results
    assert all(result.error == "not probed: the run's deadline passed" for result in results)
    assert not any(result.stale for result in results)


def test_progress_lines_name_the_feed_and_its_dates():
    from scripts.feed_staleness_probe import ProbeResult, progress_line

    result = ProbeResult(
        city_id="gainesville",
        feed="permits",
        platform="arcgis",
        endpoint="https://example.test/layer/0",
        job="gainesville_permits",
        source_updated_at=datetime(2026, 10, 1, 6, tzinfo=UTC),
        newest_watermark=datetime(2023, 2, 28, tzinfo=UTC),
        age_days=1311.0,
        stale=True,
    )
    assert progress_line(result) == (
        "STALE           gainesville/permits [arcgis] newest=2023-02-28 source=2026-10-01 age=1311.0d"
    )


def test_a_feed_with_no_date_to_read_says_why_it_reads_stale():
    undated = probe_feed(
        "boston",
        FeedType.DEEDS,
        DatasetSpec(endpoint="https://data.example/api/3/action/datastore_search?resource_id=x", platform="ckan"),
        now=datetime(2026, 10, 2, tzinfo=UTC),
        client=MagicMock(),
    )
    assert undated.stale
    assert undated.error == "no watermark column, and the source gives no update time"

    client = MagicMock()
    client.paginate.return_value = [[]]
    empty = probe_feed(
        "nyc",
        FeedType.PERMITS,
        DatasetSpec(endpoint="https://data.example/resource/test.json", watermark_col="issued"),
        now=datetime(2026, 10, 2, tzinfo=UTC),
        client=client,
    )
    assert empty.stale
    assert empty.error == "no rows with a valid watermark"
