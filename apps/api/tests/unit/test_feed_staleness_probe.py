from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from scripts.feed_staleness_probe import page_stale, parse_timestamp, probe_feed, probe_registry

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
    assert len(results) == 4
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
