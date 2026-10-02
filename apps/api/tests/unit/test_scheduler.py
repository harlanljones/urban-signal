"""Unit tests for Live Municipal Ingestion Scheduler & Poller."""

import json
from unittest.mock import MagicMock, create_autospec

import httpx
import pytest

from src.producers.scheduler import (
    _PAGINATE_KWARGS,
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


from unittest.mock import MagicMock, patch

def _refuse_live_request(self, request, *args, **kwargs):
    raise httpx.ConnectError(f"unit test refused a live request to {request.url.host}", request=request)


@pytest.fixture
def mock_scheduler(monkeypatch):
    # Some national producers (SBA loans, the FMCSA feeds, NCES schools, Head
    # Start) download through httpx directly rather than a `paginate` seam,
    # so `poll_all()` read their live sources; on 2026-10-02 one of those
    # downloads ran for more than 15 minutes. Their requests fail fast here.
    monkeypatch.setattr(httpx.Client, "send", _refuse_live_request)
    monkeypatch.setattr(httpx.AsyncClient, "send", _refuse_live_request)
    mock_dlq = MagicMock()
    with patch("src.producers.base_producer.BaseKafkaProducer"):
        scheduler = MunicipalIngestionScheduler(
            dlq_producer=mock_dlq,
            rate_limit_delay_seconds=0.0,
            dedup_capacity=1000,
        )
        for p in scheduler.producers.values():
            p.producer = MagicMock()
            # Stub every paginating client the producer holds rather than a
            # fixed list of names: stream producers (NFIP/OpenFEMA, GBFS, EV
            # charging, ...) reach the network through the same `paginate`
            # seam, and a name tuple silently rots the next time a producer
            # is registered. `poll_all()` drives stream jobs too, so an
            # unstubbed client turns a unit test into a live API probe.
            for attr in dir(p):
                if attr.startswith("_"):
                    continue
                try:
                    client = getattr(p, attr)
                except Exception:  # pragma: no cover - defensive: property side effects
                    continue
                if hasattr(client, "paginate"):
                    # Patch the method on the real client rather than swapping
                    # the object out: tests below read sibling attributes
                    # (snapshot support, endpoint resolution) off it.
                    try:
                        client.paginate = MagicMock(return_value=[])
                    except AttributeError:  # pragma: no cover - __slots__ clients
                        setattr(p, attr, MagicMock(**{"paginate.return_value": []}))
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


def test_spec_batch_limit_sets_the_per_poll_cap(mock_scheduler):
    """A feed whose source lands more rows at once than the default cap
    declares its own ``batch_limit``; every other feed keeps 1000."""
    from src.spatial.city_registry import REGISTRY, get_job_name

    for city_id, reg in REGISTRY.items():
        for feed_type, ds in reg.datasets.items():
            cfg = mock_scheduler.configs[get_job_name(feed_type, city_id)]
            assert cfg.batch_limit == (ds.batch_limit or 1000), cfg.name

    # Columbus 311's daily extract tops 1,000 rows on heavy weekdays.
    job = "311_cmoh"
    assert mock_scheduler.configs[job].batch_limit == 5000
    paginate = mock_scheduler.producers["311"].arcgis.paginate
    mock_scheduler.poll_job(job)
    _, kwargs = paginate.call_args
    assert kwargs["max_records"] == 5000
    assert kwargs["batch_size"] == 1000
    # An explicit per-call limit still wins over the declared cap.
    mock_scheduler.poll_job(job, limit=10)
    _, kwargs = paginate.call_args
    assert kwargs["max_records"] == 10


def test_snap_jobs_poll_their_own_metro(mock_scheduler):
    """A SNAP licence job asks the national layer for its state inside its
    metro bbox and reads enough rows to cover it (Houston's bbox holds 4,205
    retailers), rather than the state's first 1,000 by ObjectId."""
    from src.spatial.city_registry import CityId, FeedType, get_job_name

    paginate = mock_scheduler.producers["sla"].arcgis.paginate
    mock_scheduler.poll_job(get_job_name(FeedType.SLA, CityId.TALLAHASSEE))
    _, kwargs = paginate.call_args
    assert kwargs["where_clause"] == (
        "(State = 'FL' AND Latitude BETWEEN 30.29 AND 30.63"
        " AND Longitude BETWEEN -84.7 AND -84.05)"
    )
    assert kwargs["max_records"] == 1000

    mock_scheduler.poll_job(get_job_name(FeedType.SLA, CityId.HOUSTON))
    _, kwargs = paginate.call_args
    assert kwargs["where_clause"] == (
        "(State = 'TX' AND Latitude BETWEEN 29.2 AND 30.3"
        " AND Longitude BETWEEN -95.9 AND -94.8)"
    )
    assert kwargs["max_records"] == 7000


def test_snapshot_windows_poll_newest_first(mock_scheduler):
    """A newest-first snapshot sends its date order, with a unique tiebreaker
    for stable paging, and its window's cap, so each poll reads the latest
    sales instead of the first rows by object id. Cleveland also bounds the
    server's sort to 180 days."""
    from src.spatial.city_registry import CityId, FeedType, get_job_name

    paginate = mock_scheduler.producers["deeds"].arcgis.paginate
    mock_scheduler.poll_job(get_job_name(FeedType.DEEDS, CityId.CLEVELAND))
    _, kwargs = paginate.call_args
    assert kwargs["where_clause"] == "(last_transfer_date >= CURRENT_DATE - INTERVAL '180' DAY)"
    assert kwargs["order_by"] == "last_transfer_date DESC, OBJECTID DESC"
    assert kwargs["max_records"] == 6000

    paginate = mock_scheduler.producers["deeds"].socrata.paginate
    mock_scheduler.poll_job(get_job_name(FeedType.DEEDS, CityId.MONTGOMERY))
    _, kwargs = paginate.call_args
    assert kwargs["order_by"] == (
        "sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89 DESC, :id"
    )
    assert kwargs["max_records"] == 4000


def _stub_snap_parse(scheduler, monkeypatch):
    """Parse any SNAP-shaped row into a minimal licence event."""
    from types import SimpleNamespace

    def parse(row, city_id=None):
        return SimpleNamespace(license_id=str(row["Record_ID"]), city_id=city_id)

    monkeypatch.setattr(scheduler.producers["sla"], "parse_socrata_row", parse)


def test_snapshot_ids_survive_other_feeds_churn(mock_scheduler, monkeypatch):
    """A snapshot job keeps its own seen-set: the shared window (1000 ids in
    this fixture) filling with other feeds' ids must not make the snapshot's
    next poll re-emit its unchanged rows as new."""
    from src.spatial.city_registry import CityId, FeedType, get_job_name

    _stub_snap_parse(mock_scheduler, monkeypatch)
    job = get_job_name(FeedType.SLA, CityId.TALLAHASSEE)
    rows = [{"Record_ID": n, "ObjectId": n} for n in (101, 102, 103)]
    mock_scheduler.producers["sla"].arcgis.paginate.return_value = [rows]

    first = mock_scheduler.poll_job(job)
    assert first["records_published"] == 3
    assert mock_scheduler._dedup_for(job, 1000) is not mock_scheduler.dedup

    for n in range(1500):  # incremental feeds' new ids cycle the shared window
        mock_scheduler.dedup.check_and_add(f"311_nyc:{n}")

    second = mock_scheduler.poll_job(job)
    assert second["records_published"] == 0
    assert second["duplicates_skipped"] == 3
    assert mock_scheduler.get_metrics()["snapshot_dedup_size"] == 3


def test_incremental_jobs_share_the_dedup_window(mock_scheduler):
    assert mock_scheduler._dedup_for("311_cmoh", 5000) is mock_scheduler.dedup


def test_snapshot_seen_set_grows_with_an_explicit_limit(mock_scheduler):
    from src.spatial.city_registry import CityId, FeedType, get_job_name

    job = get_job_name(FeedType.SLA, CityId.HOUSTON)
    assert mock_scheduler._dedup_for(job, 7000).max_capacity == 14000
    assert mock_scheduler._dedup_for(job, 20000).max_capacity == 40000


def test_snapshot_that_fills_its_cap_warns(mock_scheduler, monkeypatch, caplog):
    """Rows past a table-order snapshot's cap are never read, so filling the
    cap is logged; a newest-first snapshot fills it by design."""
    import logging

    from src.spatial.city_registry import CityId, FeedType, get_job_name

    _stub_snap_parse(mock_scheduler, monkeypatch)
    rows = [{"Record_ID": n, "ObjectId": n} for n in (1, 2)]
    mock_scheduler.producers["sla"].arcgis.paginate.return_value = [rows]
    job = get_job_name(FeedType.SLA, CityId.TALLAHASSEE)

    with caplog.at_level(logging.WARNING, logger="src.producers.scheduler"):
        mock_scheduler.poll_job(job, limit=2)
    assert any("stopped at its 2-row cap" in r.getMessage() for r in caplog.records)

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="src.producers.scheduler"):
        mock_scheduler.poll_job(job, limit=5)
    assert not any("row cap" in r.getMessage() for r in caplog.records)

    for order_by in ("ObjectId DESC", "Record_ID desc, ObjectId DESC"):
        caplog.clear()
        mock_scheduler.job_metadata[job]["order_by"] = order_by
        with caplog.at_level(logging.WARNING, logger="src.producers.scheduler"):
            mock_scheduler.poll_job(job, limit=2)
        assert not any("row cap" in r.getMessage() for r in caplog.records), order_by

    # Only a leading DESC term makes a window: a column named *_desc, or a
    # DESC tiebreaker behind an ascending sort, still reads in table order.
    for order_by in ("Store_Desc ASC", "Store_Name ASC, ObjectId DESC"):
        caplog.clear()
        mock_scheduler.job_metadata[job]["order_by"] = order_by
        with caplog.at_level(logging.WARNING, logger="src.producers.scheduler"):
            mock_scheduler.poll_job(job, limit=2)
        assert any("stopped at its 2-row cap" in r.getMessage() for r in caplog.records), order_by


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
    # A date-only format keeps its boundary day (``>=``); the dedup drops
    # the rows already seen.
    assert kwargs["where_clause"] == (
        "issuance_date >= '20260810' AND issuance_date NOT IN ('ZZZZZZZZ')"
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

    def test_accela_and_excel_jobs_route_to_their_clients(self, mock_scheduler):
        """Madison (accela, since retracted) and Spokane (excel) permits raised
        "has no client registered" on every poll: the routing table stopped at
        csv."""
        producer = mock_scheduler.producers["permits"]
        assert mock_scheduler._paginating_client_for("permits_spokane") is producer.excel
        try:
            mock_scheduler.job_metadata["permits"]["platform"] = "accela"
            assert mock_scheduler._paginating_client_for("permits") is producer.accela
        finally:
            mock_scheduler.job_metadata["permits"]["platform"] = "socrata"

    def test_excel_poll_sorts_the_workbook_by_issue_date(self, mock_scheduler):
        """Spokane's workbook is not in date order (22,845 of 48,466 adjacent
        rows step back in time on 2026-09-30), so a capped incremental read in
        file order would jump the watermark past a quarter of the rows."""
        paginate = mock_scheduler.producers["permits"].excel.paginate
        mock_scheduler.poll_job("permits_spokane", limit=10)
        _, kwargs = paginate.call_args
        assert kwargs["order_by"] == "issued_date ASC"
        # The workbook client compares its watermark column as a date only
        # with a format (MyGov's text dates); Spokane's are date cells.
        assert set(kwargs) == {
            "endpoint_url", "where_clause", "batch_size", "max_records", "order_by", "watermark_col",
        }
        assert "watermark_format" not in kwargs


class TestYearSliceEndpoints:
    """D3: endpoint_by_year resolves at poll-time metadata build."""

    def _spec(self, by_year):
        from src.spatial.city_registry import DatasetSpec

        return DatasetSpec(endpoint="https://default.example", endpoint_by_year=by_year)

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
        from src.spatial.city_registry import INGESTION_MODES

        for meta in mock_scheduler.job_metadata.values():
            assert isinstance(meta["endpoint"], str) and meta["endpoint"]
            assert meta.get("ingestion_mode") in INGESTION_MODES, meta.get("ingestion_mode")


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

            # incremental control: same state emits a watermark clause (a
            # whole-hour watermark keeps its boundary: a date-only column)
            meta["ingestion_mode"] = "incremental"
            producer.socrata.paginate = MagicMock(return_value=iter([]))
            mock_scheduler.poll_job("sla", limit=10)
            _, kwargs = producer.socrata.paginate.call_args
            wc = kwargs.get("where_clause") or ""
            assert f"{meta['watermark_col']} >= '2020-01-01T00:00:00'" == wc
        finally:
            meta["platform"] = saved_platform
            if saved_mode is None:
                meta.pop("ingestion_mode", None)
            else:
                meta["ingestion_mode"] = saved_mode


class TestPollJobIngestionContract:
    """poll_job reaches every job's real client and producer intact.

    The fixture's MagicMock ``paginate`` accepts any kwargs and every producer
    attribute, which hid two crashes: the blanket kwargs splat raised
    TypeError on every watermarked socrata/arcgis/ckan/carto job, and the
    violations/inspections producers had no ``parse_socrata_row``.
    """

    @staticmethod
    def _enforce_real_paginate_signatures(scheduler):
        for producer in scheduler.producers.values():
            for attr in ("socrata", "arcgis", "accela", "carto", "ckan", "csv", "excel"):
                client = getattr(producer, attr, None)
                if client is None or isinstance(client, MagicMock):
                    continue
                real = type(client).paginate.__get__(client)
                client.paginate = create_autospec(real, return_value=[])

    def test_every_job_polls_through_the_real_paginate_signature(self, mock_scheduler):
        self._enforce_real_paginate_signatures(mock_scheduler)
        failures = {}
        for job_name, meta in mock_scheduler.job_metadata.items():
            if meta.get("national_feed") or meta.get("platform") not in _PAGINATE_KWARGS:
                continue
            result = mock_scheduler.poll_job(job_name, limit=5)
            if result["status"] != "SUCCESS":
                failures[job_name] = result["error"]
        assert not failures, failures

    def test_every_polled_producer_has_the_row_hook(self, mock_scheduler):
        # Known gap: energy_benchmark / bike_ped fan one row out to several
        # observation events inside ContextObservationsProducer.run_stream,
        # which poll_job's one-row-one-event loop cannot carry yet.
        known_gaps = {"energy_benchmark", "bike_ped"}
        polled = {
            meta["producer_key"]
            for meta in mock_scheduler.job_metadata.values()
            if meta.get("platform") != "gbfs" and not meta.get("national_feed")
        }
        missing = sorted(
            key
            for key in polled - known_gaps
            if not callable(getattr(mock_scheduler.producers[key], "parse_socrata_row", None))
        )
        assert not missing, missing

    def test_violations_job_publishes_with_run_stream_keys(self, mock_scheduler):
        producer = mock_scheduler.producers["violations"]
        rows = [
            {"case_id": "C-1", "opened_date": "2026-09-20T08:00:00.000", "latitude": "30.27", "longitude": "-97.74"},
            {"case_id": "C-2", "opened_date": "2026-09-22T09:30:00.000", "latitude": "30.28", "longitude": "-97.75"},
        ]
        producer.socrata.paginate = MagicMock(return_value=[rows])

        result = mock_scheduler.poll_job("violations_austin", limit=100)

        assert result["status"] == "SUCCESS"
        assert result["records_published"] == 2
        assert mock_scheduler.dlq_producer.route_to_dlq.call_count == 0
        keys = [c.kwargs["key"] for c in producer.producer.produce.call_args_list]
        assert keys == ["austin:C-1", "austin:C-2"]  # same shape as run_stream
        # ViolationEvent has no issuance/created/effective/recorded date, so
        # the watermark comes from the raw opened_date column.
        assert result["high_watermark"] == "2026-09-22T09:30:00"

        producer.socrata.paginate = MagicMock(return_value=[])
        mock_scheduler.poll_job("violations_austin", limit=100)
        _, kwargs = producer.socrata.paginate.call_args
        assert kwargs["where_clause"] == "opened_date > '2026-09-22T09:30:00'"

    def test_inspections_watermark_tracks_the_filter_column(self, mock_scheduler):
        producer = mock_scheduler.producers["inspections"]
        rows = [
            {
                "licenseno": "L-1",
                "_id": 1,
                "resultdttm": "2026-09-21 14:00:00+00",
                # issued years earlier: the watermark must follow resultdttm,
                # the column the incremental filter compares.
                "issdttm": "2019-01-01 00:00:00+00",
                "location": "(42.35, -71.06)",
            },
        ]
        producer.ckan.paginate = MagicMock(return_value=[rows])

        result = mock_scheduler.poll_job("inspections_boston", limit=100)

        assert result["records_published"] == 1
        assert mock_scheduler.dlq_producer.route_to_dlq.call_count == 0
        assert producer.producer.produce.call_args.kwargs["key"] == "boston:L-1"
        # The resource's timestamps are text: the stored watermark keeps the
        # column's own format so the next `resultdttm > '...'` compares alike.
        assert result["high_watermark"] == "2026-09-21 14:00:00+00"

    def test_raw_column_watermark_skips_future_rows(self, mock_scheduler):
        """Crime events carry occurred/reported dates, not one of the four
        watermark attributes; the raw-column fallback keeps the US-111 guard."""
        producer = mock_scheduler.producers["crime"]
        rows = [
            {"id": "1", "case_number": "JJ1", "date": "2028-02-26T00:00:00.000", "latitude": "41.88", "longitude": "-87.63"},
            {"id": "2", "case_number": "JJ2", "date": "2026-09-20T10:00:00.000", "latitude": "41.88", "longitude": "-87.63"},
        ]
        producer.socrata.paginate = MagicMock(return_value=[rows])

        result = mock_scheduler.poll_job("crime_chicago", limit=100)

        assert result["records_published"] == 2
        assert result["high_watermark"] == "2026-09-20T10:00:00"
