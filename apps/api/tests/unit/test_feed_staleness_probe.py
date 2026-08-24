from datetime import UTC, datetime, timedelta
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
    client.paginate.assert_called_once()


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
        extra={
            "watermark_type": "text",
            "watermark_format": "%Y%m%d",
            "watermark_exclude": ["ZZZZZZZZ"],
        },
    )
    now = datetime(2026, 8, 23, tzinfo=UTC)
    assert newest_watermark(client, spec, now=now) == datetime(2026, 8, 15, tzinfo=UTC)
    _, kwargs = client.paginate.call_args
    assert kwargs["where_clause"] == "transfer_date NOT IN ('ZZZZZZZZ')"


def test_newest_watermark_without_declarations_passes_no_guard():
    client = MagicMock()
    client.paginate.return_value = [[{"issued": "2026-08-01"}]]
    spec = DatasetSpec(endpoint="https://data.example/resource/test.json", watermark_col="issued")
    newest_watermark(client, spec, now=datetime(2026, 8, 23, tzinfo=UTC))
    _, kwargs = client.paginate.call_args
    assert kwargs["where_clause"] is None


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
    assert len(results) == 5  # permits, 311, sla, deeds, crime (US-71)
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
        extra={"expected_cadence_days": 30},
    )
    assert declared_staleness_threshold(spec) == timedelta(days=60)


def test_missing_or_invalid_declaration_falls_back():
    from scripts.feed_staleness_probe import STALE_AFTER, declared_staleness_threshold

    plain = DatasetSpec(endpoint="https://data.example/resource/test.json")
    assert declared_staleness_threshold(plain) is STALE_AFTER
    for bad in ({"expected_cadence_days": 0}, {"expected_cadence_days": "soon"}):
        spec = DatasetSpec(endpoint="u", extra=bad)
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
        extra={"endpoint_by_year": by_year, "expected_cadence_days": 7},
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
        extra={"expected_cadence_days": 30},
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
