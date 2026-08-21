"""Unit tests for Live Municipal Ingestion Scheduler & Poller."""

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


def test_poll_all_and_metrics(mock_scheduler):
    for p in mock_scheduler.producers.values():
        p.socrata.paginate = MagicMock(return_value=[])

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
    for p in mock_scheduler.producers.values():
        p.socrata.paginate = MagicMock(return_value=[])

    # Run exactly 1 cycle
    mock_scheduler.start(interval_seconds=0.01, max_cycles=1)

    metrics = mock_scheduler.get_metrics()
    assert metrics["jobs"]["permits"]["total_runs"] == 1
    assert mock_scheduler._stop_event.is_set()
