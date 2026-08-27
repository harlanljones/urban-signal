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
import json
import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from prometheus_client import Counter

from src.config import settings
from src.producers.base_producer import BaseKafkaProducer
from src.producers.complaints_311_producer import Complaints311Producer
from src.producers.crime_incidents_producer import CrimeIncidentsProducer
from src.producers.deeds_acris_producer import DeedsACRISProducer
from src.producers.dob_permits_producer import DOBPermitsProducer
from src.producers.evictions_producer import EvictionsProducer
from src.producers.sla_licenses_producer import SLALicensesProducer
from src.producers.street_cut_permits_producer import StreetCutPermitsProducer
from src.producers.watermarks import (
    typed_watermark_entry,
    watermark_comparison,
    watermark_exclude_clause,
)

logger = logging.getLogger(__name__)

# Year-slice feed rollover events (US-70): a job switched from one calendar
# year's layer/resource to the next. Scraped via the serving /metrics mount.
FEED_ROLLOVER = Counter(
    "urban_signal_feed_rollover_total",
    "Year-slice feed rollover events (endpoint switched to the next year's layer)",
    ["city_id", "feed"],
)


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
    # Monotonic deadline before which the job must not run again (US-107).
    # 0.0 means immediately due — every job runs on the first tick after boot.
    next_due: float = 0.0
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
    # Year-slice rollover telemetry (US-70): how many times the job switched
    # layers at New Year and when the most recent switch happened.
    rollovers: int = 0
    last_rollover: str | None = None


def _is_future_watermark(value: Any, now_dt: datetime) -> bool:
    """Whether a watermark datetime falls strictly after ``now_dt``.

    Mirrors the staleness probe's future-row treatment (US-111): a single
    future/sentinel row must not pin a feed's high watermark. Naive datetimes
    are treated as UTC so the comparison never raises.
    """
    if value is None:
        return False
    ts = value
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts > now_dt


def _parse_state_watermark(raw: str, fmt: str | None) -> datetime | None:
    """Parse a persisted high-watermark string for the future guard.

    Text-typed feeds (ADR 0005) store the raw declared-format string; all
    others store ISO. Returns ``None`` when unparseable so an unknown format
    is never mistaken for the future.
    """
    try:
        if fmt:
            return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


class MunicipalIngestionScheduler:
    """Continuous, rate-limited polling orchestrator for NYC Socrata datasets."""

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        dlq_producer: BaseKafkaProducer | None = None,
        rate_limit_delay_seconds: float = 0.2,
        dedup_capacity: int = 100_000,
        today_provider: Callable[[], date] | None = None,
    ):
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.rate_limit_delay = rate_limit_delay_seconds
        self.dedup = DeduplicationFilter(max_capacity=dedup_capacity)
        self._stop_event = threading.Event()
        # Injectable calendar clock (US-70): the rollover drill freezes this at
        # Jan 2 to prove the next-year layer is resolved at New Year.
        self._today_provider = today_provider or (lambda: datetime.now(UTC).date())

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
            "crime": CrimeIncidentsProducer(bootstrap_servers=self.bootstrap_servers),
            "street_cut": StreetCutPermitsProducer(bootstrap_servers=self.bootstrap_servers),
            "evictions": EvictionsProducer(bootstrap_servers=self.bootstrap_servers),
        }

        # Socrata Endpoints & Target Topics mapping derived from city registry
        from src.spatial.city_registry import REGISTRY, get_job_name, resolve_endpoint

        self.job_metadata: dict[str, dict[str, Any]] = {}
        self.configs: dict[str, JobConfig] = {}

        for city_id, reg in REGISTRY.items():
            for feed_type, ds in reg.datasets.items():
                job_name = get_job_name(feed_type, city_id)
                self.job_metadata[job_name] = {
                    "endpoint": resolve_endpoint(ds),
                    # Year-slice metadata (ADR 0002 / US-70): kept so the job
                    # can re-resolve its layer at poll time and detect the New
                    # Year switch instead of polling last year's layer forever.
                    "endpoint_by_year": dict(ds.endpoint_by_year or {}),
                    "endpoint_base": ds.endpoint,
                    "topic": ds.topic,
                    "watermark_col": ds.watermark_col,
                    "id_keys": ds.id_keys,
                    "city_id": city_id.value,
                    "producer_key": ds.producer_key or feed_type.value,
                    "platform": ds.platform,
                    "ingestion_mode": ds.ingestion_mode or "incremental",
                    # Platform-specific pagination knobs forwarded verbatim to
                    # clients that accept them (e.g. CartoClient select/
                    # order_by/id_col; socrata accepts order_by only). Clients
                    # that don't take a key simply never receive it.
                    "order_by": ds.order_by,
                    "id_col": ds.id_col,
                    "select": ds.select,
                    "fallback_endpoints": list(ds.fallback_endpoints or []),
                    # D7 text-watermark declarations (ADR 0005): sentinels
                    # become a server-side NOT-IN guard and the high
                    # watermark is tracked as the raw declared-format string
                    # instead of an ISO reformat of a parsed event attribute.
                    "watermark_type": ds.watermark_type,
                    "watermark_format": ds.watermark_format,
                    "watermark_exclude": ds.watermark_exclude or [],
                    "base_where": ds.where,
                }
                self.configs[job_name] = JobConfig(
                    name=job_name,
                    interval_seconds=ds.interval_seconds,
                    watermark_column=ds.watermark_col,
                )

        self.metrics: dict[str, JobMetrics] = {k: JobMetrics() for k in self.configs}
        self.backoffs: dict[str, ExponentialBackoffTracker] = {k: ExponentialBackoffTracker() for k in self.configs}

        # Durable watermark state (US-106): restore per-job high watermarks
        # across restarts; persistence is disabled until a state file is
        # configured via SCHEDULER_STATE_FILE.
        self.state_file: str | None = settings.scheduler_state_file or None
        if self.state_file:
            self._load_state()

    def _load_state(self) -> None:
        """Restore persisted high watermarks into job metrics (US-106)."""
        try:
            with open(self.state_file, encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            logger.info("No watermark state file at %s; starting fresh", self.state_file)
            return
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Ignoring unreadable watermark state %s: %s", self.state_file, exc)
            return
        restored = 0
        skipped_future = 0
        now_dt = datetime.now(UTC)
        for job_name, entry in data.items():
            met = self.metrics.get(job_name)
            wm = (entry or {}).get("high_watermark")
            if met is not None and wm and met.high_watermark is None:
                meta = self.job_metadata.get(job_name)
                fmt = meta.get("watermark_format") if meta else None
                parsed = _parse_state_watermark(str(wm), fmt)
                if parsed is not None and _is_future_watermark(parsed, now_dt):
                    # US-111: a poisoned state file (e.g. sla_sf seeded with a
                    # 2028 row) must not pin the feed's watermark on restore.
                    skipped_future += 1
                    logger.warning("Ignoring future watermark %r for job %s (US-111)", wm, job_name)
                    continue
                met.high_watermark = str(wm)
                restored += 1
        logger.info(
            "Restored %d job watermarks from %s%s",
            restored,
            self.state_file,
            f" (ignored {skipped_future} future)" if skipped_future else "",
        )

    def _save_state(self) -> None:
        """Atomically persist non-None high watermarks (US-106)."""
        if not self.state_file:
            return
        payload = {
            job: {"high_watermark": met.high_watermark, "updated_at": datetime.now(UTC).isoformat()}
            for job, met in self.metrics.items()
            if met.high_watermark
        }
        try:
            state_path = Path(self.state_file)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = state_path.with_suffix(state_path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            os.replace(tmp, state_path)
        except OSError as exc:
            # Best-effort persistence mirrors the tolerant read side: an
            # unwritable location (host runs with a container-only path,
            # read-only mount) must not kill polling.
            logger.warning("Ignoring unwritable watermark state %s: %s", self.state_file, exc)

    def _extract_record_id(self, job_name: str, row: dict[str, Any]) -> str:
        """Extract a unique record identifier from raw Socrata JSON row."""
        id_keys = self.job_metadata[job_name]["id_keys"]
        for k in id_keys:
            val = row.get(k)
            if val is not None and str(val).strip():
                return f"{job_name}:{str(val).strip()}"
        return f"{job_name}:hash_{hash(frozenset(row.items()))}"

    def _paginating_client_for(self, job_name: str):
        """Select the paginating client matching a job's registered platform.

        Routing is a dict dispatch so new platform clients (carto, ckan, ...)
        plug in by adding a producer attribute — no scheduler edit. The
        invariant suite asserts every producer exposes the client its
        registered specs need; an unregistered platform here is a readable
        error, never a silent fallthrough to Socrata.
        """
        meta = self.job_metadata[job_name]
        producer_wrapper = self.producers[meta.get("producer_key", job_name)]
        clients = {
            "socrata": getattr(producer_wrapper, "socrata", None),
            "arcgis": getattr(producer_wrapper, "arcgis", None),
            "carto": getattr(producer_wrapper, "carto", None),
            "ckan": getattr(producer_wrapper, "ckan", None),
            "csv": getattr(producer_wrapper, "csv", None),
        }
        platform = meta.get("platform", "socrata")
        client = clients.get(platform)
        if client is None:
            if platform not in clients:
                available = ", ".join(sorted(k for k, v in clients.items() if v is not None))
                raise ValueError(
                    f"Job '{job_name}': platform {platform!r} has no client "
                    f"registered (available: {available}); add a client module "
                    f"and expose it on the producer before registering this spec"
                )
            raise ValueError(
                f"Job '{job_name}': producer lacks the {platform!r} client its "
                f"spec requires — expose it as an attribute (see DeedsACRISProducer)"
            )
        return client

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

    def _rollover_check(self, job_name: str, today: date | None = None) -> bool:
        """Detect a year-slice layer switch and apply the New Year rollover reset.

        Year-sliced feeds (DC permits/311, Boston 311, Baltimore 311 — ADR
        0002) publish one layer/resource per calendar year. At New Year the
        resolved endpoint changes; the job must switch to the new layer, reset
        its watermark baseline (the new layer starts fresh), and emit a
        ``rollover`` metric event so the staleness monitor re-baselines
        instead of paging on the reset. Returns True when a rollover occurred.
        """
        from src.spatial.city_registry import DatasetSpec, resolve_endpoint

        meta = self.job_metadata[job_name]
        by_year = meta.get("endpoint_by_year")
        if not by_year:
            return False
        today = today or self._today_provider()
        resolved = resolve_endpoint(
            DatasetSpec(
                endpoint=meta["endpoint_base"],
                
                endpoint_by_year=by_year,
            ),
            today=today,
        )
        if resolved == meta["endpoint"]:
            return False
        met = self.metrics[job_name]
        old_watermark = met.high_watermark
        meta["endpoint"] = resolved
        met.high_watermark = None
        met.rollovers += 1
        met.last_rollover = today.isoformat()
        FEED_ROLLOVER.labels(meta.get("city_id", "unknown"), meta.get("producer_key", job_name)).inc()
        logger.warning(
            "Job '%s' rolled over to %s; watermark baseline reset (was %r)",
            job_name, resolved, old_watermark,
        )
        return True

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

        # US-70: New Year rollover for year-sliced feeds. Re-resolve the job's
        # endpoint against the calendar before building the watermark clause so
        # a layer switch repoints this poll to the new year's resource with a
        # reset baseline.
        self._rollover_check(job_name)

        # Build dynamic where clause for incremental watermark. Snapshot-mode
        # feeds (no watermark column — e.g. Baton Rouge's business registry)
        # pull the full table every cycle; the cross-run dedup cache makes the
        # re-poll a diff (only unseen ids are emitted), so mutations surface as
        # new ids and are tracked by the row-parity acceptance gate instead.
        where_parts = []
        if meta.get("base_where"):
            where_parts.append(f"({meta['base_where']})")
        if cfg.where_clause:
            where_parts.append(f"({cfg.where_clause})")
        is_snapshot = meta.get("ingestion_mode") == "snapshot"
        if (
            cfg.incremental
            and not is_snapshot
            and met.high_watermark
            and meta["watermark_col"]
        ):
            where_parts.append(
                watermark_comparison(
                    meta["watermark_col"],
                    ">",
                    met.high_watermark,
                    meta["endpoint"],
                    watermark_type=meta.get("watermark_type"),
                    watermark_format=meta.get("watermark_format"),
                )
            )
        exclude_guard = (
            watermark_exclude_clause(meta["watermark_col"], meta.get("watermark_exclude") or [])
            if meta["watermark_col"]
            else None
        )
        if exclude_guard:
            where_parts.append(exclude_guard)

        active_where = " AND ".join(where_parts) if where_parts else None

        records_fetched = 0
        records_published = 0
        duplicates_skipped = 0
        new_high_watermark = met.high_watermark
        # US-111 future-watermark guard: advance the high watermark only with
        # values at or before now (mirrors the staleness probe), so one
        # future/sentinel row cannot pin the feed's incremental filter.
        now_dt = datetime.now(UTC)
        future_watermarks = 0
        # Typed comparison state for text-typed watermarks (ADR 0005): the
        # stored high watermark stays the raw declared-format string so the
        # server-side `>` filter remains format-consistent across runs.
        new_hw_parsed: datetime | None = None
        if meta.get("watermark_type") == "text" and new_high_watermark:
            stored = typed_watermark_entry(new_high_watermark, fmt=meta.get("watermark_format"))
            new_hw_parsed = stored[1] if stored else None

        try:
            client_kwargs = {
                k: meta[k]
                for k in (
                    "order_by",
                    "id_col",
                    "select",
                    "fallback_endpoints",
                    "watermark_col",
                    "watermark_format",
                    "watermark_exclude",
                )
                if meta.get(k)
            }
            for batch in self._paginating_client_for(job_name).paginate(
                endpoint_url=meta["endpoint"],
                where_clause=active_where,
                batch_size=min(fetch_limit, 1000),
                max_records=fetch_limit,
                **client_kwargs,
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

                    # Text-typed watermarks track the RAW column value before
                    # row parsing (ADR 0005): a sentinel-free declared-format
                    # value advances ingestion recency even if event parsing
                    # later routes the row to the DLQ.
                    if meta.get("watermark_type") == "text":
                        entry = typed_watermark_entry(
                            row.get(meta["watermark_col"]),
                            fmt=meta.get("watermark_format"),
                            exclude=meta.get("watermark_exclude") or [],
                        )
                        if entry and _is_future_watermark(entry[1], now_dt):
                            future_watermarks += 1
                            logger.warning(
                                "Job '%s': ignoring future text watermark %r (US-111)",
                                job_name,
                                entry[0],
                            )
                        elif entry and (new_hw_parsed is None or entry[1] > new_hw_parsed):
                            new_high_watermark = entry[0]
                            new_hw_parsed = entry[1]

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

                        # Update high watermark. Text-typed feeds (ADR 0005)
                        # are tracked from the raw column before parsing, so
                        # skip the event-attr path here.
                        wm_val: Any = None
                        if meta.get("watermark_type") != "text":
                            wm_val = (
                                getattr(event, "issuance_date", None)
                                or getattr(event, "created_date", None)
                                or getattr(event, "effective_date", None)
                                or getattr(event, "recorded_date", None)
                            )
                        if wm_val:
                            if _is_future_watermark(wm_val, now_dt):
                                future_watermarks += 1
                                logger.warning(
                                    "Job '%s': ignoring future watermark %s (US-111)",
                                    job_name,
                                    wm_val,
                                )
                            else:
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

        # Persist watermark progress after every job attempt (US-106) so a
        # restart resumes from the latest watermark instead of the beginning.
        self._save_state()

        return {
            "job": job_name,
            "status": met.last_status,
            "records_fetched": records_fetched,
            "records_published": records_published,
            "duplicates_skipped": duplicates_skipped,
            "high_watermark": met.high_watermark,
            "error": met.last_error,
        }

    def poll_due(self, batch_limit: int | None = None) -> dict[str, dict[str, Any]]:
        """Run every enabled job whose per-feed interval has elapsed (US-107).

        Each job carries its own ``next_due`` monotonic deadline derived from
        the registry's ``interval_seconds``; due jobs run sequentially, so the
        politeness cap is one in-flight portal request per scheduler. Feed
        freshness is bounded by the feed's own cadence instead of the full
        rotation.
        """
        now = time.monotonic()
        due = [name for name, cfg in self.configs.items() if cfg.enabled and cfg.next_due <= now]
        results: dict[str, dict[str, Any]] = {}
        for name in due:
            if self._stop_event.is_set():
                break
            results[name] = self.poll_job(job_name=name, limit=batch_limit)
            self.configs[name].next_due = time.monotonic() + self.configs[name].interval_seconds
        if due:
            logger.info("Ran %d/%d due jobs this tick", len(due), len(self.configs))
        return results

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
        """Runs the continuous polling scheduler loop (staggered, US-107).

        ``interval_seconds`` is the tick granularity: every tick selects the
        jobs whose per-feed cadence (registry ``interval_seconds``) has
        elapsed and runs only those. A feed's freshness is therefore bounded
        by its own interval plus one tick, not by the size of the rotation.
        """
        self._stop_event.clear()
        tick = max(1.0, min(interval_seconds or 60.0, 60.0))
        tick_count = 0
        logger.info("Municipal Ingestion Scheduler started (per-feed intervals, %.0fs tick).", tick)

        try:
            while not self._stop_event.is_set():
                tick_count += 1
                self.poll_due()

                if max_cycles and tick_count >= max_cycles:
                    logger.info("Reached max_cycles=%d. Stopping scheduler.", max_cycles)
                    break

                # Interruptible sleep
                for _ in range(int(tick * 10)):
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
                    "rollovers": m.rollovers,
                    "last_rollover": m.last_rollover,
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
