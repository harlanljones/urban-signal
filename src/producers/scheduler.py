"""Live Municipal Ingestion Scheduler & Poller.

Provides continuous, rate-limited polling from Socrata NYC Open Data endpoints
(DOB Permits, 311 Complaints, SLA Licenses, ACRIS Deeds) with:
- Configurable polling intervals / cron cadences
- Rate limiting and exponential backoff
- In-memory sliding-window deduplication
- Automatic dispatching to Kafka topics
- Isolated error catching & Dead-Letter Queue (DLQ) routing
"""

import argparse
import collections
import logging
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.config import settings
from src.producers.base_producer import BaseKafkaProducer
from src.producers.complaints_311_producer import Complaints311Producer
from src.producers.deeds_acris_producer import DeedsACRISProducer
from src.producers.dob_permits_producer import DOBPermitsProducer
from src.producers.sla_licenses_producer import SLALicensesProducer

logger = logging.getLogger(__name__)


class DeduplicationFilter:
    """Bounded sliding-window deduplication cache for municipal record identifiers."""

    def __init__(self, max_capacity: int = 100_000):
        self.max_capacity = max_capacity
        self._seen: set[str] = set()
        self._queue: collections.deque = collections.deque()
        self._lock = threading.Lock()

    def is_duplicate(self, record_key: str) -> bool:
        with self._lock:
            return record_key in self._seen

    def add(self, record_key: str):
        with self._lock:
            if record_key in self._seen:
                return
            if len(self._queue) >= self.max_capacity:
                oldest = self._queue.popleft()
                self._seen.discard(oldest)
            self._queue.append(record_key)
            self._seen.add(record_key)

    def check_and_add(self, record_key: str) -> bool:
        """Returns True if duplicate (already seen), False if newly added."""
        with self._lock:
            if record_key in self._seen:
                return True
            if len(self._queue) >= self.max_capacity:
                oldest = self._queue.popleft()
                self._seen.discard(oldest)
            self._queue.append(record_key)
            self._seen.add(record_key)
            return False

    def clear(self):
        with self._lock:
            self._seen.clear()
            self._queue.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._seen)


class ExponentialBackoffTracker:
    """Manages exponential backoff delays per ingestion job upon API or network failures."""

    def __init__(
        self,
        initial_backoff: float = 1.0,
        backoff_factor: float = 2.0,
        max_backoff: float = 300.0,
    ):
        self.initial_backoff = initial_backoff
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.consecutive_failures = 0
        self.current_backoff = 0.0

    def record_failure(self) -> float:
        self.consecutive_failures += 1
        delay = min(
            self.max_backoff,
            self.initial_backoff * (self.backoff_factor ** (self.consecutive_failures - 1)),
        )
        self.current_backoff = delay
        return delay

    def record_success(self):
        self.consecutive_failures = 0
        self.current_backoff = 0.0


@dataclass
class JobConfig:
    """Configuration for an individual municipal ingestion job."""

    name: str
    interval_seconds: float = 300.0
    batch_limit: int = 1000
    enabled: bool = True
    incremental: bool = True
    where_clause: str | None = None
    watermark_column: str | None = None


@dataclass
class JobMetrics:
    """Live metrics tracking for a specific ingestion endpoint."""

    total_runs: int = 0
    records_fetched: int = 0
    records_published: int = 0
    duplicates_skipped: int = 0
    errors_count: int = 0
    last_run_timestamp: datetime | None = None
    last_status: str = "IDLE"
    last_error: str | None = None
    high_watermark: str | None = None


class MunicipalIngestionScheduler:
    """Continuous, rate-limited polling orchestrator for NYC Socrata datasets."""

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        dlq_producer: BaseKafkaProducer | None = None,
        rate_limit_delay_seconds: float = 0.2,
        dedup_capacity: int = 100_000,
    ):
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.rate_limit_delay = rate_limit_delay_seconds
        self.dedup = DeduplicationFilter(max_capacity=dedup_capacity)
        self._stop_event = threading.Event()

        # Shared DLQ Producer
        self.dlq_producer = dlq_producer or BaseKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            dlq_topic=settings.topic_dlq,
        )

        # Producers
        self.producers: dict[str, Any] = {
            "permits": DOBPermitsProducer(bootstrap_servers=self.bootstrap_servers),
            "311": Complaints311Producer(bootstrap_servers=self.bootstrap_servers),
            "sla": SLALicensesProducer(bootstrap_servers=self.bootstrap_servers),
            "deeds": DeedsACRISProducer(bootstrap_servers=self.bootstrap_servers),
        }

        # Socrata Endpoints & Target Topics mapping derived from city registry
        from src.spatial.city_registry import REGISTRY, get_job_name

        self.job_metadata: dict[str, dict[str, Any]] = {}
        self.configs: dict[str, JobConfig] = {}

        for city_id, reg in REGISTRY.items():
            for feed_type, ds in reg.datasets.items():
                job_name = get_job_name(feed_type, city_id)
                self.job_metadata[job_name] = {
                    "endpoint": ds.endpoint,
                    "topic": ds.topic,
                    "watermark_col": ds.watermark_col,
                    "id_keys": ds.id_keys,
                    "city_id": city_id.value,
                    "producer_key": ds.producer_key or feed_type.value,
                    "platform": ds.platform,
                }
                self.configs[job_name] = JobConfig(
                    name=job_name,
                    interval_seconds=ds.interval_seconds,
                    watermark_column=ds.watermark_col,
                )

        self.metrics: dict[str, JobMetrics] = {k: JobMetrics() for k in self.configs}
        self.backoffs: dict[str, ExponentialBackoffTracker] = {k: ExponentialBackoffTracker() for k in self.configs}

    def _extract_record_id(self, job_name: str, row: dict[str, Any]) -> str:
        """Extract a unique record identifier from raw Socrata JSON row."""
        id_keys = self.job_metadata[job_name]["id_keys"]
        for k in id_keys:
            val = row.get(k)
            if val is not None and str(val).strip():
                return f"{job_name}:{str(val).strip()}"
        return f"{job_name}:hash_{hash(frozenset(row.items()))}"

    def configure_job(
        self,
        name: str,
        interval_seconds: float | None = None,
        batch_limit: int | None = None,
        enabled: bool | None = None,
        where_clause: str | None = None,
    ):
        """Update job configuration parameters."""
        if name not in self.configs:
            raise KeyError(f"Unknown job '{name}'. Valid jobs: {list(self.configs.keys())}")

        cfg = self.configs[name]
        if interval_seconds is not None:
            cfg.interval_seconds = interval_seconds
        if batch_limit is not None:
            cfg.batch_limit = batch_limit
        if enabled is not None:
            cfg.enabled = enabled
        if where_clause is not None:
            cfg.where_clause = where_clause

    def poll_job(
        self,
        job_name: str,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Executes a single poll cycle for a specific municipal dataset."""
        if job_name not in self.configs:
            raise KeyError(f"Invalid job name '{job_name}'")

        cfg = self.configs[job_name]
        met = self.metrics[job_name]
        meta = self.job_metadata[job_name]
        producer_key = meta.get("producer_key", job_name)
        producer_wrapper = self.producers[producer_key]
        city_id = meta.get("city_id", "nyc")
        backoff_tracker = self.backoffs[job_name]

        met.total_runs += 1
        met.last_run_timestamp = datetime.now(UTC)
        fetch_limit = limit or cfg.batch_limit

        # Build dynamic where clause for incremental watermark
        where_parts = []
        if cfg.where_clause:
            where_parts.append(f"({cfg.where_clause})")
        if cfg.incremental and met.high_watermark and meta["watermark_col"]:
            where_parts.append(f"{meta['watermark_col']} > '{met.high_watermark}'")

        active_where = " AND ".join(where_parts) if where_parts else None

        records_fetched = 0
        records_published = 0
        duplicates_skipped = 0
        new_high_watermark = met.high_watermark

        try:
            for batch in producer_wrapper.socrata.paginate(
                endpoint_url=meta["endpoint"],
                where_clause=active_where,
                batch_size=min(fetch_limit, 1000),
                max_records=fetch_limit,
            ):
                if self._stop_event.is_set():
                    break

                for row in batch:
                    records_fetched += 1
                    rec_id = self._extract_record_id(job_name, row)

                    # Deduplication check
                    if self.dedup.check_and_add(rec_id):
                        duplicates_skipped += 1
                        continue

                    # Rate limiting throttle
                    if self.rate_limit_delay > 0:
                        time.sleep(self.rate_limit_delay)

                    # Parse & Validate
                    try:
                        event = producer_wrapper.parse_socrata_row(row, city_id=city_id)
                        if event is None:
                            # Route malformed/missing coordinate row to DLQ
                            self.dlq_producer.route_to_dlq(
                                failed_topic=meta["topic"],
                                key=rec_id,
                                payload=row,
                                error_msg="parse_socrata_row returned None (missing ID or geometry)",
                            )
                            continue

                        # Extract partition key
                        key = (
                            getattr(event, "job_id", None)
                            or getattr(event, "incident_id", None)
                            or getattr(event, "license_id", None)
                            or getattr(event, "doc_id", None)
                            or rec_id
                        )
                        resolved_city = getattr(event, "city_id", city_id)
                        full_key = f"{resolved_city}:{key}"

                        # Produce to main topic
                        producer_wrapper.producer.produce(
                            topic=meta["topic"],
                            key=full_key,
                            payload=event,
                        )
                        records_published += 1

                        # Update high watermark
                        wm_val = (
                            getattr(event, "issuance_date", None)
                            or getattr(event, "created_date", None)
                            or getattr(event, "effective_date", None)
                            or getattr(event, "recorded_date", None)
                        )
                        if wm_val:
                            wm_str = wm_val.strftime("%Y-%m-%dT%H:%M:%S")
                            if new_high_watermark is None or wm_str > new_high_watermark:
                                new_high_watermark = wm_str

                    except Exception as parse_err:
                        logger.warning("Error processing row in %s: %s", job_name, parse_err)
                        self.dlq_producer.route_to_dlq(
                            failed_topic=meta["topic"],
                            key=rec_id,
                            payload=row,
                            error_msg=str(parse_err),
                        )

            # Flush producer buffers
            producer_wrapper.producer.flush()
            self.dlq_producer.flush()

            # Update metrics & watermark
            met.records_fetched += records_fetched
            met.records_published += records_published
            met.duplicates_skipped += duplicates_skipped
            met.high_watermark = new_high_watermark
            met.last_status = "SUCCESS"
            met.last_error = None
            backoff_tracker.record_success()

            logger.info(
                "Job '%s' completed: Fetched=%d | Published=%d | Duplicates=%d | Watermark=%s",
                job_name,
                records_fetched,
                records_published,
                duplicates_skipped,
                new_high_watermark,
            )

        except Exception as poll_err:
            met.errors_count += 1
            met.last_status = "ERROR"
            met.last_error = str(poll_err)
            delay = backoff_tracker.record_failure()
            logger.error("Job '%s' failed: %s (Backoff delay: %.1fs)", job_name, poll_err, delay)

            # Route error to DLQ
            self.dlq_producer.route_to_dlq(
                failed_topic=meta["topic"],
                key=f"poller_failure:{job_name}",
                payload={"error": str(poll_err), "job": job_name, "timestamp": datetime.now(UTC).isoformat()},
                error_msg=str(poll_err),
            )

        return {
            "job": job_name,
            "status": met.last_status,
            "records_fetched": records_fetched,
            "records_published": records_published,
            "duplicates_skipped": duplicates_skipped,
            "high_watermark": met.high_watermark,
            "error": met.last_error,
        }

    def poll_all(self, batch_limit: int | None = None) -> dict[str, dict[str, Any]]:
        """Executes a single poll cycle across all enabled municipal jobs."""
        logger.info("Starting batch municipal polling cycle across enabled endpoints...")
        results = {}
        for name, cfg in self.configs.items():
            if not cfg.enabled:
                continue
            if self._stop_event.is_set():
                break
            results[name] = self.poll_job(job_name=name, limit=batch_limit)
        return results

    def start(
        self,
        interval_seconds: float | None = None,
        max_cycles: int | None = None,
    ):
        """Runs the continuous polling scheduler loop."""
        self._stop_event.clear()
        cycle = 0
        logger.info("Municipal Ingestion Scheduler started.")

        try:
            while not self._stop_event.is_set():
                cycle += 1
                logger.info("Starting Polling Cycle #%d", cycle)
                self.poll_all()

                if max_cycles and cycle >= max_cycles:
                    logger.info("Reached max_cycles=%d. Stopping scheduler.", max_cycles)
                    break

                sleep_time = interval_seconds or 60.0
                # Interruptible sleep
                for _ in range(int(sleep_time * 10)):
                    if self._stop_event.is_set():
                        break
                    time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Scheduler interrupted by user.")
        finally:
            self.stop()

    def stop(self):
        """Halts the scheduler and flushes all Kafka producer buffers."""
        self._stop_event.set()
        for name, p in self.producers.items():
            try:
                p.producer.flush()
            except Exception as e:
                logger.warning("Error flushing %s producer on shutdown: %s", name, e)
        try:
            self.dlq_producer.flush()
        except Exception as e:
            logger.warning("Error flushing DLQ producer on shutdown: %s", e)
        logger.info("Municipal Ingestion Scheduler stopped and flushed.")

    def get_metrics(self) -> dict[str, Any]:
        """Returns snapshot of live telemetry metrics."""
        return {
            "dedup_cache_size": len(self.dedup),
            "jobs": {
                name: {
                    "total_runs": m.total_runs,
                    "records_fetched": m.records_fetched,
                    "records_published": m.records_published,
                    "duplicates_skipped": m.duplicates_skipped,
                    "errors_count": m.errors_count,
                    "last_status": m.last_status,
                    "last_error": m.last_error,
                    "high_watermark": m.high_watermark,
                    "last_run_timestamp": m.last_run_timestamp.isoformat() if m.last_run_timestamp else None,
                }
                for name, m in self.metrics.items()
            },
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Municipal Ingestion Scheduler & Poller")
    parser.add_argument(
        "--jobs",
        nargs="+",
        default=[
            "permits",
            "311",
            "sla",
            "deeds",
            "permits_chicago",
            "311_chicago",
            "sla_chicago",
            "deeds_chicago",
            "permits_sf",
            "311_sf",
            "sla_sf",
            "deeds_sf",
        ],
        help="Jobs to poll",
    )
    parser.add_argument("--limit", type=int, default=500, help="Per-job fetch limit")
    parser.add_argument("--interval", type=float, default=60.0, help="Cycle interval in seconds")
    parser.add_argument("--run-once", action="store_true", help="Execute single polling cycle and exit")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

    scheduler = MunicipalIngestionScheduler()

    # Enable only selected jobs
    for j_name, j_cfg in scheduler.configs.items():
        j_cfg.enabled = j_name in args.jobs

    if args.run_once:
        res = scheduler.poll_all(batch_limit=args.limit)
        print("Cycle Results:", res)
    else:
        scheduler.start(interval_seconds=args.interval)
