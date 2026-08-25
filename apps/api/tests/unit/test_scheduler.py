"""Unit tests for Live Municipal Ingestion Scheduler & Poller."""

import json
from unittest.mock import MagicMock

import pytest

from src.producers.scheduler import (
    DeduplicationFilter,
    ExponentialBackoffTracker,
    MunicipalIngestionScheduler,
)


def test_deduplication_filter():
    dedup = DeduplicationFilter(max_capacity=3)

    assert len(dedup) == 0
    assert not dedup.is_duplicate("key1")

    # Add key1 -> returns False (new)
    assert not dedup.check_and_add("key1")
    assert dedup.is_duplicate("key1")
    assert len(dedup) == 1

    # Check key1 again -> returns True (duplicate)
    assert dedup.check_and_add("key1")
    assert len(dedup) == 1

    # Add key2, key3
    assert not dedup.check_and_add("key2")
    assert not dedup.check_and_add("key3")
    assert len(dedup) == 3

    # Add key4 -> should evict key1 (FIFO queue)
    assert not dedup.check_and_add("key4")
    assert len(dedup) == 3
    assert not dedup.is_duplicate("key1")
    assert dedup.is_duplicate("key4")

    # Clear
    dedup.clear()
    assert len(dedup) == 0
    assert not dedup.is_duplicate("key4")


def test_exponential_backoff_tracker():
    tracker = ExponentialBackoffTracker(initial_backoff=2.0, backoff_factor=2.0, max_backoff=20.0)

    delay1 = tracker.record_failure()
    assert delay1 == 2.0
    assert tracker.consecutive_failures == 1

    delay2 = tracker.record_failure()
    assert delay2 == 4.0

    delay3 = tracker.record_failure()
    assert delay3 == 8.0

    delay4 = tracker.record_failure()
    assert delay4 == 16.0

    delay5 = tracker.record_failure()
    assert delay5 == 20.0  # Capped at max_backoff

    tracker.record_success()
    assert tracker.consecutive_failures == 0
    assert tracker.current_backoff == 0.0


@pytest.fixture
def mock_scheduler():
    mock_dlq = MagicMock()
    scheduler = MunicipalIngestionScheduler(
        dlq_producer=mock_dlq,
        rate_limit_delay_seconds=0.0,
        dedup_capacity=1000,
    )
    # Mock individual producers' Kafka producers to prevent socket calls
    for p in scheduler.producers.values():
        p.producer = MagicMock()
        # The registry now contains ArcGIS, CARTO, CKAN, and CSV feeds in
        # addition to the original Socrata jobs.  Keep this unit fixture
        # network-free for every supported platform selected by
        # _paginating_client_for().
        for client_name in ("socrata", "arcgis", "carto", "ckan", "csv"):
            client = getattr(p, client_name, None)
            if client is not None:
                client.paginate = MagicMock(return_value=[])
    return scheduler


def test_job_configuration(mock_scheduler):
    mock_scheduler.configure_job("permits", interval_seconds=120.0, batch_limit=500, enabled=False, where_clause="status = 'ISSUED'")
    cfg = mock_scheduler.configs["permits"]
    assert cfg.interval_seconds == 120.0
    assert cfg.batch_limit == 500
    assert not cfg.enabled
    assert cfg.where_clause == "status = 'ISSUED'"

    with pytest.raises(KeyError):
        mock_scheduler.configure_job("invalid_job", interval_seconds=10.0)


def test_extract_record_id(mock_scheduler):
    permits_id = mock_scheduler._extract_record_id("permits", {"job__": "M123456"})
    assert permits_id == "permits:M123456"

    c311_id = mock_scheduler._extract_record_id("311", {"unique_key": "SR999"})
    assert c311_id == "311:SR999"

    sla_id = mock_scheduler._extract_record_id("sla", {"licensepermitid": "LIC-888"})
    assert sla_id == "sla:LIC-888"

    deeds_id = mock_scheduler._extract_record_id("deeds", {"document_id": "CRFN-111"})
    assert deeds_id == "deeds:CRFN-111"


def test_poll_job_successful_and_deduplicated(mock_scheduler):
    job_name = "permits"
    mock_producer = mock_scheduler.producers[job_name]

    # Mock Socrata pagination with 2 valid records (1 duplicate) and 1 malformed record
    mock_rows_page1 = [
        {
            "job__": "M001",
            "latitude": "40.725",
            "longitude": "-73.997",
            "job_type": "A1",
            "initial_cost": "500000",
            "issuance_date": "2026-08-01T10:00:00.000",
        },
        {
            "job__": "M001",  # Duplicate key
            "latitude": "40.725",
            "longitude": "-73.997",
            "job_type": "A1",
            "initial_cost": "500000",
            "issuance_date": "2026-08-01T10:00:00.000",
        },
        {
            "job__": "M002",
            # Missing latitude/longitude -> parse returns None
            "job_type": "NB",
            "initial_cost": "1500000",
        },
    ]

    mock_producer.socrata.paginate = MagicMock(return_value=[mock_rows_page1])

    result = mock_scheduler.poll_job("permits", limit=100)

    assert result["job"] == "permits"
    assert result["status"] == "SUCCESS"
    assert result["records_fetched"] == 3
    assert result["records_published"] == 1
    assert result["duplicates_skipped"] == 1

    # Main producer called once for valid M001
    assert mock_producer.producer.produce.call_count == 1
    assert mock_producer.producer.flush.call_count == 1

    # DLQ producer called once for missing coords on M002
    assert mock_scheduler.dlq_producer.route_to_dlq.call_count == 1


def test_poll_job_socrata_error_dlq(mock_scheduler):
    job_name = "311"
    mock_producer = mock_scheduler.producers[job_name]
    mock_producer.socrata.paginate = MagicMock(side_effect=RuntimeError("SODA HTTP 500 Connection Timeout"))

    result = mock_scheduler.poll_job("311", limit=50)

    assert result["status"] == "ERROR"
    assert "Connection Timeout" in result["error"]
    assert mock_scheduler.metrics["311"].errors_count == 1
    assert mock_scheduler.dlq_producer.route_to_dlq.call_count == 1


def test_text_watermark_guard_and_raw_high_watermark(mock_scheduler):
    """D7 (ADR 0005): declared sentinels are excluded server-side and text
    high watermarks stay raw declared-format strings, calendar-compared."""
    job_name = "permits"
    mock_producer = mock_scheduler.producers[job_name]
    mock_scheduler.job_metadata[job_name].update(
        watermark_type="text",
        watermark_format="%Y%m%d",
        watermark_exclude=["ZZZZZZZZ"],
    )
    mock_scheduler.metrics[job_name].high_watermark = "20260810"

    mock_rows = [
        {"job__": "M010", "latitude": "40.7", "longitude": "-73.9", "issuance_date": "ZZZZZZZZ"},
        {"job__": "M011", "latitude": "40.7", "longitude": "-73.9", "issuance_date": "20260815"},
        {"job__": "M012", "latitude": "40.7", "longitude": "-73.9", "issuance_date": "20260801"},
    ]
    mock_producer.socrata.paginate = MagicMock(return_value=[mock_rows])

    result = mock_scheduler.poll_job(job_name, limit=100)

    _, kwargs = mock_producer.socrata.paginate.call_args
    assert kwargs["where_clause"] == (
        "issuance_date > '20260810' AND issuance_date NOT IN ('ZZZZZZZZ')"
    )
    # Raw declared-format string stored; sentinel dropped; calendar max wins
    # even though 20260801 sorts above it lexically.
    assert result["high_watermark"] == "20260815"
    assert mock_scheduler.metrics[job_name].high_watermark == "20260815"


def test_future_dated_row_does_not_advance_high_watermark(mock_scheduler):
    """US-111: a future/sentinel-dated row must not pin the high watermark —
    sla_sf was poisoned by a 2028 row, filtering `> '2028-...'` until 2028."""
    job_name = "permits"
    mock_producer = mock_scheduler.producers[job_name]
    mock_rows = [
        {
            "job__": "M001",
            "latitude": "40.725",
            "longitude": "-73.997",
            "job_type": "A1",
            "initial_cost": "100000",
            "issuance_date": "2028-02-26T00:00:00.000",  # future row
        },
        {
            "job__": "M002",
            "latitude": "40.725",
            "longitude": "-73.997",
            "job_type": "A1",
            "initial_cost": "100000",
            "issuance_date": "2026-08-01T10:00:00.000",  # current row
        },
    ]
    mock_producer.socrata.paginate = MagicMock(return_value=[mock_rows])

    result = mock_scheduler.poll_job(job_name, limit=100)

    # Both rows published; the watermark advances only to the non-future row.
    assert result["records_published"] == 2
    assert result["high_watermark"] == "2026-08-01T10:00:00"


def test_future_text_watermark_not_advanced(mock_scheduler):
    """US-111: the ADR-0005 text-watermark path ignores future declared-format
    values the same way the event-attr path does."""
    job_name = "permits"
    mock_producer = mock_scheduler.producers[job_name]
    mock_scheduler.job_metadata[job_name].update(
        watermark_type="text",
        watermark_format="%Y%m%d",
        watermark_exclude=[],
    )
    mock_scheduler.metrics[job_name].high_watermark = "20260810"
    mock_rows = [
        {"job__": "M010", "latitude": "40.7", "longitude": "-73.9", "issuance_date": "20280226"},
        {"job__": "M011", "latitude": "40.7", "longitude": "-73.9", "issuance_date": "20260820"},
    ]
    mock_producer.socrata.paginate = MagicMock(return_value=[mock_rows])

    result = mock_scheduler.poll_job(job_name, limit=100)

    assert result["high_watermark"] == "20260820"


def test_load_state_skips_future_watermark(mock_scheduler, tmp_path):
    """US-111: a poisoned state file self-heals — a future watermark is not
    restored, so the feed resumes incremental ingestion."""
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps(
            {
                "permits": {"high_watermark": "2028-02-26T00:00:00"},
                "sla": {"high_watermark": "2026-08-01T00:00:00"},
            }
        ),
        encoding="utf-8",
    )
    mock_scheduler.state_file = str(state)
    mock_scheduler._load_state()

    assert mock_scheduler.metrics["permits"].high_watermark is None  # future ignored
    assert mock_scheduler.metrics["sla"].high_watermark == "2026-08-01T00:00:00"


def test_poll_all_and_metrics(mock_scheduler):
    # Disable deeds
    mock_scheduler.configs["deeds"].enabled = False

    res = mock_scheduler.poll_all()
    assert "permits" in res
    assert "311" in res
    assert "sla" in res
    assert "deeds" not in res  # Disabled

    metrics = mock_scheduler.get_metrics()
    assert "dedup_cache_size" in metrics
    assert "jobs" in metrics
    assert "permits" in metrics["jobs"]
    assert metrics["jobs"]["permits"]["total_runs"] == 1
    assert metrics["jobs"]["permits"]["last_status"] == "SUCCESS"


def test_scheduler_start_stop(mock_scheduler):
    # Run exactly 1 cycle
    mock_scheduler.start(interval_seconds=0.01, max_cycles=1)

    metrics = mock_scheduler.get_metrics()
    assert metrics["jobs"]["permits"]["total_runs"] == 1
    assert mock_scheduler._stop_event.is_set()


class TestPlatformRouting:
    """D1: client routing is a dict dispatch with readable failures."""

    def test_unknown_platform_raises_readable_error(self, mock_scheduler):
        mock_scheduler.job_metadata["permits"]["platform"] = "ftp"
        try:
            with pytest.raises(ValueError, match="platform 'ftp' has no client"):
                mock_scheduler._paginating_client_for("permits")
        finally:
            mock_scheduler.job_metadata["permits"]["platform"] = "socrata"

    def test_missing_client_attribute_raises_readable_error(self, mock_scheduler):
        # permits producer has no .arcgis attribute-level client registered? It
        # does since Wave C2 — remove it to simulate an unwired producer.
        try:
            saved = mock_scheduler.producers["permits"].arcgis
            del mock_scheduler.producers["permits"].arcgis
            mock_scheduler.job_metadata["permits"]["platform"] = "arcgis"
            with pytest.raises(ValueError, match="lacks the 'arcgis' client"):
                mock_scheduler._paginating_client_for("permits")
        finally:
            mock_scheduler.producers["permits"].arcgis = saved
            mock_scheduler.job_metadata["permits"]["platform"] = "socrata"


class TestYearSliceEndpoints:
    """D3: endpoint_by_year resolves at poll-time metadata build."""

    def _spec(self, by_year):
        from src.spatial.city_registry import DatasetSpec

        return DatasetSpec(endpoint="https://default.example", extra={"endpoint_by_year": by_year})

    def test_current_year_wins(self):
        import datetime as dt

        from src.spatial.city_registry import resolve_endpoint

        spec = self._spec({"2024": "u/24", "2025": "u/25", "2026": "u/26"})
        assert resolve_endpoint(spec, dt.date(2026, 6, 1)) == "u/26"

    def test_newest_past_year_when_current_missing(self):
        import datetime as dt

        from src.spatial.city_registry import resolve_endpoint

        spec = self._spec({"2025": "u/25", "2027": "u/27"})
        assert resolve_endpoint(spec, dt.date(2026, 6, 1)) == "u/25"

    def test_future_only_falls_back_to_latest(self):
        import datetime as dt

        from src.spatial.city_registry import resolve_endpoint

        spec = self._spec({"2030": "u/30"})
        assert resolve_endpoint(spec, dt.date(2026, 6, 1)) == "u/30"

    def test_plain_spec_passthrough(self):
        from src.spatial.city_registry import DatasetSpec, resolve_endpoint

        assert resolve_endpoint(DatasetSpec(endpoint="u/plain")) == "u/plain"

    def test_scheduler_metadata_uses_resolver(self, mock_scheduler):
        """Every job's endpoint came through resolve_endpoint (year-sliced
        specs would show their resolved layer)."""
        for meta in mock_scheduler.job_metadata.values():
            assert isinstance(meta["endpoint"], str) and meta["endpoint"]
            assert meta.get("ingestion_mode") in ("incremental", "snapshot")


class TestSnapshotMode:
    """D4: snapshot feeds skip the watermark clause; dedup cache diffs pulls."""

    def test_snapshot_job_skips_watermark_after_first_run(self, mock_scheduler):
        meta = mock_scheduler.job_metadata["sla"]
        cfg = mock_scheduler.configs["sla"]
        met = mock_scheduler.metrics["sla"]
        producer = mock_scheduler.producers[meta["producer_key"]]

        saved_platform = meta["platform"]
        saved_mode = meta.get("ingestion_mode")
        try:
            meta["platform"] = "socrata"
            meta["ingestion_mode"] = "snapshot"
            producer.socrata.paginate = MagicMock(return_value=iter([]))

            met.high_watermark = "2020-01-01T00:00:00"
            cfg.incremental = True
            mock_scheduler.poll_job("sla", limit=10)
            _, kwargs = producer.socrata.paginate.call_args
            assert not kwargs.get("where_clause")

            # incremental control: same state emits a watermark clause
            meta["ingestion_mode"] = "incremental"
            producer.socrata.paginate = MagicMock(return_value=iter([]))
            mock_scheduler.poll_job("sla", limit=10)
            _, kwargs = producer.socrata.paginate.call_args
            wc = kwargs.get("where_clause") or ""
            assert f"{meta['watermark_col']} > '2020-01-01T00:00:00'" == wc
        finally:
            meta["platform"] = saved_platform
            if saved_mode is None:
                meta.pop("ingestion_mode", None)
            else:
                meta["ingestion_mode"] = saved_mode
