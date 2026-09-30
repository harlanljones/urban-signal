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
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from prometheus_client import Counter

from src.config import settings
from src.producers.base_producer import BaseKafkaProducer
from src.producers.complaints_311_producer import Complaints311Producer
from src.producers.context_observations_producer import ContextObservationsProducer
from src.producers.crime_incidents_producer import CrimeIncidentsProducer
from src.producers.enforcement_signals_producer import InspectionsProducer, ViolationsProducer
from src.producers.deeds_acris_producer import DeedsACRISProducer
from src.producers.dob_permits_producer import DOBPermitsProducer
from src.producers.ev_charging_producer import EvChargingProducer
from src.producers.carrier_license_producer import CarrierLicenseProducer
from src.producers.head_start_producer import HeadStartProducer
from src.producers.nces_anchor_producer import NcesAnchorProducer
from src.producers.nppes_diff_producer import NppesDiffProducer
from src.producers.evictions_producer import EvictionsProducer
from src.producers.gbfs_producer import GbfsProducer
from src.producers.nfip_producer import NfipProducer
from src.producers.nrel_afdc_client import NrelAfdcClient
from src.producers.poi_diff_producer import PoiDiffProducer
from src.producers.childcare_producer import ChildcareLicensingProducer
from src.producers.sla_licenses_producer import SLALicensesProducer
from src.producers.sba_loan_producer import SbaLoanProducer
from src.producers.fdic_bankbranch_producer import FdicBankBranchProducer
from src.producers.street_cut_permits_producer import StreetCutPermitsProducer
from src.producers.acquisition import _ADAPTER_REQUEST_KEYS
from src.producers.arcgis_client import ArcGISClient
from src.producers.watermarks import (
    parse_watermark,
    typed_watermark_entry,
    watermark_comparison,
    watermark_exclude_clause,
)
from src.spatial.national_feeds import NATIONAL_FEEDS, NationalFeed, schedulable_feeds

logger = logging.getLogger(__name__)

# Pagination kwargs each platform client's ``paginate`` accepts beyond the
# shared endpoint/where/batch/max arguments: the US-185 adapter contract
# (``acquisition.build_adapter_request``) plus the CSV client's zip,
# delimiter and header-row options, which only the scheduler forwards. The
# socrata/arcgis/ckan/carto signatures reject the watermark_* keys, so
# forwarding them raises TypeError before the first request.
_PAGINATE_KWARGS: dict[str, tuple[str, ...]] = {
    **_ADAPTER_REQUEST_KEYS,
    "csv": (*_ADAPTER_REQUEST_KEYS["csv"], "zip_member", "delimiter", "columns"),
    # Accela's public surface is an ArcGIS facade (AccelaClient); a workbook
    # is sorted and column-picked client-side like a CSV.
    "accela": _ADAPTER_REQUEST_KEYS["arcgis"],
    "excel": ("order_by", "select", "link_pattern"),
}

# A snapshot whose order starts ``<col> DESC`` reads its newest rows first,
# so its cap is a window on recent rows rather than a cut through the table.
_NEWEST_FIRST = re.compile(r"\s*[^\s,]+\s+DESC\b", re.IGNORECASE)

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
    # Set when a poll filled its cap without moving the watermark: the next
    # filter would read the same rows, so it steps past the boundary until the
    # watermark moves (see ``_watermark_predicate``).
    boundary_stalled: bool = False


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
        # A snapshot job re-reads its table every poll and emits only ids it
        # has not seen, so its seen-set is the feed's state, not an overlap
        # window. Each snapshot job keeps its own, sized to its cap: in the
        # shared window above, other feeds' new ids evict a snapshot's ids and
        # its next poll re-emits unchanged rows as new.
        self.snapshot_dedup: dict[str, DeduplicationFilter] = {}
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
            # US-377: childcare registries are their own feed with their own
            # field maps, sharing the SLA producer's event shape and topic.
            "childcare": ChildcareLicensingProducer(bootstrap_servers=self.bootstrap_servers),
"deeds": DeedsACRISProducer(bootstrap_servers=self.bootstrap_servers),
            "crime": CrimeIncidentsProducer(bootstrap_servers=self.bootstrap_servers),
            "violations": ViolationsProducer(bootstrap_servers=self.bootstrap_servers),
            "inspections": InspectionsProducer(bootstrap_servers=self.bootstrap_servers),
            "street_cut": StreetCutPermitsProducer(bootstrap_servers=self.bootstrap_servers),
            "evictions": EvictionsProducer(bootstrap_servers=self.bootstrap_servers),
            # US-363 §2.7/§2.8: one producer serves both context-measurement
            # feeds, dispatching on FeedType inside run_stream. Two keys, one
            # instance — the gate checks producer_key -> platform clients, not
            # producer_key -> distinct object.
            "energy_benchmark": ContextObservationsProducer(bootstrap_servers=self.bootstrap_servers),
            "bike_ped": ContextObservationsProducer(bootstrap_servers=self.bootstrap_servers),
            "gbfs": GbfsProducer(bootstrap_servers=self.bootstrap_servers),
            "nfip_claims": NfipProducer(bootstrap_servers=self.bootstrap_servers),
            # POI release deltas are credential-gated; the national scheduler
            # keeps the job visible but only enables it when HF_TOKEN exists.
            "poi_change": PoiDiffProducer(
                bootstrap_servers=self.bootstrap_servers,
                strict_licensing=True,
            ),
            # US-371: the API key stays environment-backed; settings.nrel_api_key
            # (default "") exists so `NrelAfdcClient()` constructs standalone.
            # The sentinel keeps the disabled producer constructible without a
            # credential while the host remains egress-unverified.
            "ev_charging": EvChargingProducer(
                bootstrap_servers=self.bootstrap_servers,
                client=NrelAfdcClient(
                    api_key=settings.nrel_api_key or os.environ.get("NREL_API_KEY") or "UNCONFIGURED"
                ),
            ),
            # US-373: the FMCSA national carrier family — one producer serves
            # the three DatasetSpec-shaped national resources, dispatching on
            # the job's carrier_spec key inside run_stream.
            "carrier": CarrierLicenseProducer(bootstrap_servers=self.bootstrap_servers),
            # US-375/US-376: the anchor-institution family — NCES school churn
            # (annual) and the Head Start daily snapshot share one event and
            # one topic.
            "nces_anchor": NcesAnchorProducer(bootstrap_servers=self.bootstrap_servers),
            "head_start": HeadStartProducer(bootstrap_servers=self.bootstrap_servers),
            # US-378: SBA 7(a)/504 loan approvals — cumulative FOIA snapshot per program.
            "sba_loan": SbaLoanProducer(bootstrap_servers=self.bootstrap_servers),
            "bank_branch": FdicBankBranchProducer(bootstrap_servers=self.bootstrap_servers),
            # US-374: NPPES weekly incremental diffs for medical office churn.
            "nppes": NppesDiffProducer(bootstrap_servers=self.bootstrap_servers),
        }

        # Socrata Endpoints & Target Topics mapping derived from city registry
        from src.spatial.city_registry import (
            REGISTRY,
            get_job_name,
            resolve_endpoint,
            resolve_zip_member,
        )

        self.job_metadata: dict[str, dict[str, Any]] = {}
        self.configs: dict[str, JobConfig] = {}

        for city_id, reg in REGISTRY.items():
            for feed_type, ds in reg.datasets.items():
                job_name = get_job_name(feed_type, city_id)
                zip_member = resolve_zip_member(ds) if ds.zip_member else None
                endpoint = ds.endpoint if ds.zip_member else resolve_endpoint(ds)
                self.job_metadata[job_name] = {
                    "endpoint": endpoint,
                    # Year-slice metadata (ADR 0002 / US-70): kept so the job
                    # can re-resolve its layer at poll time and detect the New
                    # Year switch instead of polling last year's layer forever.
                    "endpoint_by_year": dict(ds.endpoint_by_year or {}),
                    "endpoint_base": ds.endpoint,
                    "topic": ds.topic,
                    "watermark_col": ds.watermark_col,
                    "id_keys": ds.id_keys,
                    "composite_id": ds.composite_id,
                    "city_id": city_id.value,
                    "producer_key": ds.producer_key or feed_type.value,
                    # Which registered feed this job ingests. Several feed
                    # types share one producer (childcare and business
                    # licensing both run through `sla_licenses_producer`), so
                    # the producer cannot infer this from `producer_key` — it
                    # selects the field map by feed.
                    "feed_type": feed_type.value,
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
                    "zip_member": zip_member,
                    "delimiter": ds.delimiter,
                    "columns": list(ds.columns or []),
                    "link_pattern": ds.link_pattern,
                    # A table with no geometry (DC, Lynchburg and Roanoke
                    # sales) takes each row's coordinates from its parcel's
                    # centroid.
                    "parcel_join": dict(ds.parcel_join or {}),
                    # A county-wide source keeps only the rows placed inside
                    # the city's metro box (Bend's Deschutes County sales).
                    "metro_clip": ds.metro_clip,
                }
                self.configs[job_name] = JobConfig(
                    name=job_name,
                    interval_seconds=ds.interval_seconds,
                    batch_limit=ds.batch_limit or JobConfig.batch_limit,
                    # GBFS is wired as an explicit stream job below, but keep
                    # it opt-in until its per-city endpoint has been verified
                    # by the scheduler runtime. This also preserves the
                    # municipal poll loop's existing network surface.
                    enabled=ds.platform != "gbfs",
                    watermark_column=ds.watermark_col,
                )

        # National feeds are one job per source, not one job per city. Keep
        # every implemented source visible in the scheduler, but leave an
        # unverified or credentialed source disabled until its registry spec
        # makes it safe to poll (US-363). Claims and declarations share the
        # OpenFEMA producer but dispatch to different event contracts.
        runnable_national = {spec.feed for spec in schedulable_feeds()}
        national_specs = {
            spec.feed: spec
            for spec in schedulable_feeds()
            if spec.feed in (
                NationalFeed.NFIP_CLAIMS,
                NationalFeed.DISASTER_DECLARATIONS,
                NationalFeed.POI_CHANGE,
                NationalFeed.EV_CHARGING,
                NationalFeed.SBA_LOAN,
                NationalFeed.BANK_BRANCH,
                NationalFeed.NPPES_MEDICAL,
            )
        }
        for feed in (
            NationalFeed.NFIP_CLAIMS,
            NationalFeed.DISASTER_DECLARATIONS,
            NationalFeed.POI_CHANGE,
            NationalFeed.EV_CHARGING,
            NationalFeed.SBA_LOAN,
            NationalFeed.BANK_BRANCH,
            NationalFeed.NPPES_MEDICAL,
        ):
            spec = NATIONAL_FEEDS[feed]
            job_name = spec.feed.value
            self.job_metadata[job_name] = {
                "endpoint": spec.endpoint,
                "endpoint_base": spec.endpoint,
                "topic": spec.topic,
                "watermark_col": spec.watermark_col,
                "id_keys": spec.id_keys,
                "producer_key": spec.producer_key,
                "platform": spec.platform,
                "ingestion_mode": spec.ingestion_mode,
                "national_feed": spec.feed,
                "auth_env": spec.auth_env,
                "state_dir": spec.state_dir,
            }
            self.configs[job_name] = JobConfig(
                name=job_name,
                interval_seconds=spec.interval_seconds,
                enabled=feed in runnable_national and feed in national_specs,
                watermark_column=spec.watermark_col or None,
            )

        # US-373: FMCSA national carrier family, beside NATIONAL_FEEDS in
        # DatasetSpec shape (see fmcsa_specs.py — deliberately unregistered
        # in the city REGISTRY). Zero config additions; the census carries a
        # monthly full-snapshot rollover because A→I flips happen in-place
        # without moving add_date.
        from src.producers.fmcsa_specs import (
            FMCSA_AUTHHIST_SPEC,
            FMCSA_CENSUS_SPEC,
            FMCSA_OOS_SPEC,
        )
        carrier_specs = (
            ("fmcsa_census", FMCSA_CENSUS_SPEC),
            ("fmcsa_authhist", FMCSA_AUTHHIST_SPEC),
            ("fmcsa_oos", FMCSA_OOS_SPEC),
        )
        for job_name, spec in carrier_specs:
            self.job_metadata[job_name] = {
                "endpoint": spec["endpoint"],
                "endpoint_base": spec["endpoint"],
                "topic": spec["topic"],
                "watermark_col": spec["watermark_col"],
                "watermark_format": spec.get("watermark_format"),
                "id_keys": spec["id_keys"],
                "producer_key": spec["producer_key"],
                "platform": spec["platform"],
                "ingestion_mode": spec["ingestion_mode"],
                "national_feed": "carrier_family",
                "carrier_spec": job_name,
            }
            self.configs[job_name] = JobConfig(
                name=job_name,
                interval_seconds=spec["interval_seconds"],
                enabled=True,
                watermark_column=spec["watermark_col"] or None,
            )

        # US-375/US-376: national anchor-institution jobs. Both produce to
        # topic_anchor_institutions; the gate's registry invariants do not
        # apply (no per-city endpoints).
        self.job_metadata["nces_anchor"] = {
            "endpoint": "https://nces.ed.gov/ccd/data/zip/",
            "endpoint_base": "https://nces.ed.gov/ccd/data/zip/",
            "topic": settings.topic_anchor_institutions,
            "watermark_col": "",
            "id_keys": ["ncessch"],
            "producer_key": "nces_anchor",
            "platform": "csv",
            "ingestion_mode": "full",
            "national_feed": "anchor_family",
        }
        self.configs["nces_anchor"] = JobConfig(
            name="nces_anchor",
            interval_seconds=7 * 86400.0,
            enabled=True,
            watermark_column=None,
        )
        self.job_metadata["head_start"] = {
            "endpoint": settings.head_start_locations_url,
            "endpoint_base": settings.head_start_locations_url,
            "topic": settings.topic_anchor_institutions,
            "watermark_col": "",
            "id_keys": ["grant_number", "service_location_name"],
            "producer_key": "head_start",
            "platform": "csv",
            "ingestion_mode": "snapshot",
            "national_feed": "anchor_family",
        }
        self.configs["head_start"] = JobConfig(
            name="head_start",
            interval_seconds=86400.0,
            enabled=True,
            watermark_column=None,
        )

        self.metrics: dict[str, JobMetrics] = {k: JobMetrics() for k in self.configs}
        self.backoffs: dict[str, ExponentialBackoffTracker] = {k: ExponentialBackoffTracker() for k in self.configs}

        # Durable watermark state (US-106): restore per-job high watermarks
        # across restarts; persistence is disabled until a state file is
        # configured via SCHEDULER_STATE_FILE.
        self.state_file: str | None = settings.scheduler_state_file or None
        if self.state_file:
            self._load_state()

    def _poll_stream_job(self, job_name: str, limit: int | None = None) -> dict[str, Any]:
        """Run a non-Socrata producer through the scheduler metrics seam."""
        met = self.metrics[job_name]
        meta = self.job_metadata[job_name]
        producer = self.producers[meta["producer_key"]]
        met.total_runs += 1
        met.last_run_timestamp = datetime.now(UTC)
        try:
            if meta.get("platform") == "gbfs":
                count = producer.run_stream(city_id=meta["city_id"], limit=limit)
            elif meta.get("national_feed") == "carrier_family":
                count = producer.run_stream(spec=meta.get("carrier_spec"), limit=limit)
            elif meta.get("national_feed") == NationalFeed.NFIP_CLAIMS:
                count = producer.run_stream(since=met.high_watermark, limit=limit)
            elif meta.get("national_feed") == NationalFeed.DISASTER_DECLARATIONS:
                count = producer.run_declarations(since=met.high_watermark, limit=limit)
            else:
                count = producer.run_stream(limit=limit)
            count = int(count or 0)
            met.records_fetched += count
            met.records_published += count
            met.last_status = "SUCCESS"
            met.last_error = None
            met.high_watermark = datetime.now(UTC).isoformat() if count and meta.get("national_feed") else met.high_watermark
            self.backoffs[job_name].record_success()
        except Exception as poll_err:  # noqa: BLE001 - producer failures are isolated per job
            met.errors_count += 1
            met.last_status = "ERROR"
            met.last_error = str(poll_err)
            self.backoffs[job_name].record_failure()
            logger.error("Job '%s' failed: %s", job_name, poll_err)
        self._save_state()
        return {
            "job": job_name,
            "status": met.last_status,
            "records_fetched": count if met.last_status == "SUCCESS" else 0,
            "records_published": count if met.last_status == "SUCCESS" else 0,
            "duplicates_skipped": 0,
            "high_watermark": met.high_watermark,
            "error": met.last_error,
        }

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
        meta = self.job_metadata[job_name]
        if meta.get("city_id") == "st_louis" and meta.get("producer_key") == "permits":
            from src.spatial.cities.st_louis import permit_composite_id

            return f"{job_name}:{permit_composite_id(row)}"
        id_keys = meta["id_keys"]
        if meta.get("composite_id"):
            # Rows unique only as a combination (a sale keyed by parcel and
            # instrument) join every key; a missing part stays empty.
            parts = ["" if row.get(k) is None else str(row.get(k)).strip() for k in id_keys]
            if any(parts):
                return f"{job_name}:{'|'.join(parts)}"
        else:
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
            "accela": getattr(producer_wrapper, "accela", None),
            "carto": getattr(producer_wrapper, "carto", None),
            "ckan": getattr(producer_wrapper, "ckan", None),
            "csv": getattr(producer_wrapper, "csv", None),
            "excel": getattr(producer_wrapper, "excel", None),
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
        from src.spatial.city_registry import DatasetSpec, resolve_endpoint, resolve_zip_member

        meta = self.job_metadata[job_name]
        by_year = meta.get("endpoint_by_year")
        if not by_year:
            return False
        today = today or self._today_provider()
        if meta.get("zip_member"):
            resolved_member = resolve_zip_member(
                DatasetSpec(
                    endpoint=meta["endpoint_base"],
                    zip_member=meta["zip_member"],
                    endpoint_by_year=by_year,
                ),
                today=today,
            )
            if not resolved_member or resolved_member == meta["zip_member"]:
                return False
            met = self.metrics[job_name]
            old_member = meta["zip_member"]
            old_watermark = met.high_watermark
            meta["zip_member"] = resolved_member
            met.high_watermark = None
            met.rollovers += 1
            met.last_rollover = today.isoformat()
            FEED_ROLLOVER.labels(meta.get("city_id", "unknown"), meta.get("producer_key", job_name)).inc()
            logger.info(
                "feed_rollover job=%s old_member=%s new_member=%s old_watermark=%s",
                job_name,
                old_member,
                resolved_member,
                old_watermark,
            )
            return True
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

    def _dedup_for(self, job_name: str, fetch_limit: int) -> DeduplicationFilter:
        """The seen-set a poll checks: the job's own for snapshots, else shared."""
        if self.job_metadata[job_name].get("ingestion_mode") != "snapshot":
            return self.dedup
        capacity = 2 * max(fetch_limit, self.configs[job_name].batch_limit)
        seen = self.snapshot_dedup.get(job_name)
        if seen is None:
            seen = self.snapshot_dedup[job_name] = DeduplicationFilter(max_capacity=capacity)
        elif seen.max_capacity < capacity:
            seen.max_capacity = capacity
        return seen

    def _watermark_predicate(self, job_name: str) -> str:
        """The incremental filter on a job's watermark column.

        A strict ``>`` suits a timestamp column. A date-only column stores one
        time for every row of a day (UTC midnight, noon, or local midnight at
        04:00 to 10:00 UTC across US zones), so rows published later that day
        carry the watermark's own value and ``>`` never reads them. A watermark
        on a whole hour therefore keeps its boundary with ``>=``, and the dedup
        drops the rows already seen.

        A poll that filled its cap without moving the watermark would read the
        same rows again (``JobMetrics.boundary_stalled``). Until the watermark
        moves, the filter steps past its boundary: a strict ``>`` on a whole
        hour, and ``>=`` the next second on a timestamp, since a server can
        hold a finer time than its JSON returns (Milwaukee's licence refresh
        reads back as 01:23:59 but sorts after 01:23:59.999).
        """
        meta = self.job_metadata[job_name]
        met = self.metrics[job_name]
        value = met.high_watermark
        text = meta.get("watermark_type") == "text"
        if text:
            entry = typed_watermark_entry(value, fmt=meta.get("watermark_format"))
            parsed = entry[1] if entry else None
        else:
            parsed = parse_watermark(value)
        whole_hour = parsed is not None and parsed.minute == parsed.second == parsed.microsecond == 0
        op = ">=" if whole_hour and not met.boundary_stalled else ">"
        if met.boundary_stalled and parsed is not None and not whole_hour and not text:
            op, value = ">=", (parsed + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S")
        return watermark_comparison(
            meta["watermark_col"],
            op,
            value,
            meta["endpoint"],
            watermark_type=meta.get("watermark_type"),
            watermark_format=meta.get("watermark_format"),
            time_zone=self._layer_time_zone(job_name),
        )

    def _layer_time_zone(self, job_name: str) -> str | None:
        """The zone an ArcGIS layer reads ``where`` literals in (None for UTC).

        Read from the layer's metadata, which the client fetches once and
        caches for its paging anyway.
        """
        meta = self.job_metadata[job_name]
        if meta.get("platform") != "arcgis":
            return None
        client = self._paginating_client_for(job_name)
        get_metadata = getattr(client, "get_layer_metadata", None)
        if get_metadata is None:
            return None
        zone = get_metadata(meta["endpoint"]).get("time_zone")
        return zone if isinstance(zone, str) else None

    def _join_parcel_centroids(self, job_name: str, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Give rows without coordinates their parcel's centroid (``parcel_join``).

        Sales tables with no geometry (Lynchburg, Roanoke, DC's CAMA sales)
        name each row's parcel. Only this batch's parcels are read from the
        spec's parcel layer, as the deeds producer's ``run_stream`` does.
        The join's ``where`` limits the parcels that can place a row: Pierce
        County's parcels place Tacoma's sales only in the city's tax code
        areas, and a sale elsewhere in the county stays unplaced.
        """
        meta = self.job_metadata[job_name]
        join = meta["parcel_join"]
        key = join["join_key"]
        # The row's own name for the key, where it differs from the parcel
        # layer's (a workbook's headers arrive lower-cased).
        row_key = join.get("row_key") or key

        def unplaced(row: dict[str, Any]) -> bool:
            return row.get("latitude") is None or row.get("longitude") is None

        wanted = [row[row_key] for row in batch if unplaced(row) and row.get(row_key) not in (None, "")]
        if not wanted:
            return batch
        client = getattr(self.producers[meta["producer_key"]], "arcgis", None) or ArcGISClient()
        centroids = client.fetch_centroid_index(
            endpoint_url=join["parcel_layer"],
            join_key=key,
            join_values=wanted,
            via=join.get("via"),
            where=join.get("where"),
        )
        joined = []
        for row in batch:
            centroid = centroids.get(ArcGISClient._normalize_join_value(row.get(row_key))) if unplaced(row) else None
            joined.append({**row, "latitude": centroid[0], "longitude": centroid[1]} if centroid else row)
        return joined

    def _metro_clip(self, job_name: str) -> Callable[[dict[str, Any]], bool] | None:
        """The test a ``metro_clip`` feed's rows pass: placed inside the metro box.

        A row is placed by the columns its field map names for latitude and
        longitude, else by ``latitude``/``longitude`` (a parcel join's
        centroid, or the ArcGIS client's). Feeds without the flag get None.
        """
        meta = self.job_metadata[job_name]
        if not meta.get("metro_clip"):
            return None
        from src.producers.field_maps import first_mapped, resolve_field_map
        from src.spatial.city_registry import REGISTRY, CityId, FeedType

        box = REGISTRY[CityId(meta["city_id"])].metro_bbox
        try:
            field_map = resolve_field_map(meta["city_id"], FeedType(meta["feed_type"]))
        except ValueError:
            field_map = {}

        def inside(row: dict[str, Any]) -> bool:
            lat = first_mapped(row, field_map, "latitude") or row.get("latitude")
            lng = first_mapped(row, field_map, "longitude") or row.get("longitude")
            try:
                lat, lng = float(lat), float(lng)
            except (TypeError, ValueError):
                return False
            return box["min_lat"] <= lat <= box["max_lat"] and box["min_lng"] <= lng <= box["max_lng"]

        return inside

    def poll_job(
        self,
        job_name: str,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Executes a single poll cycle for a specific municipal dataset."""
        if job_name not in self.configs:
            raise KeyError(f"Invalid job name '{job_name}'")

        if self.job_metadata[job_name].get("platform") == "gbfs" or self.job_metadata[job_name].get("national_feed"):
            return self._poll_stream_job(job_name, limit=limit)

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

        is_snapshot = meta.get("ingestion_mode") == "snapshot"
        watermark_filtered = bool(
            cfg.incremental
            and not is_snapshot
            and met.high_watermark
            and meta["watermark_col"]
        )

        records_fetched = 0
        records_published = 0
        duplicates_skipped = 0
        outside_metro = 0
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

        dedup = self._dedup_for(job_name, fetch_limit)
        try:
            # Build dynamic where clause for incremental watermark. Snapshot-mode
            # feeds (no watermark column — e.g. Baton Rouge's business registry)
            # pull the full table every cycle; the cross-run dedup cache makes the
            # re-poll a diff (only unseen ids are emitted), so mutations surface as
            # new ids and are tracked by the row-parity acceptance gate instead.
            # Built inside the try: an ArcGIS layer's zone comes from its metadata.
            where_parts = []
            if meta.get("base_where"):
                where_parts.append(f"({meta['base_where']})")
            if cfg.where_clause:
                where_parts.append(f"({cfg.where_clause})")
            if watermark_filtered:
                where_parts.append(self._watermark_predicate(job_name))
            exclude_guard = (
                watermark_exclude_clause(meta["watermark_col"], meta.get("watermark_exclude") or [])
                if meta["watermark_col"]
                else None
            )
            if exclude_guard:
                where_parts.append(exclude_guard)

            active_where = " AND ".join(where_parts) if where_parts else None

            client_kwargs = {
                k: meta[k]
                for k in _PAGINATE_KWARGS.get(meta.get("platform", "socrata"), ())
                if meta.get(k)
            }
            clip = self._metro_clip(job_name)
            for batch in self._paginating_client_for(job_name).paginate(
                endpoint_url=meta["endpoint"],
                where_clause=active_where,
                batch_size=min(fetch_limit, 1000),
                max_records=fetch_limit,
                **client_kwargs,
            ):
                if self._stop_event.is_set():
                    break
                if meta.get("parcel_join"):
                    batch = self._join_parcel_centroids(job_name, batch)

                for row in batch:
                    records_fetched += 1
                    if clip is not None and not clip(row):
                        outside_metro += 1
                        continue
                    rec_id = self._extract_record_id(job_name, row)

                    # Deduplication check
                    if dedup.check_and_add(rec_id):
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
                            or getattr(event, "violation_id", None)
                            or getattr(event, "inspection_id", None)
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
                        # skip this path. The rest advance from the watermark
                        # column too, since the incremental filter compares
                        # that column: an event's own date can come from
                        # another column (Connecticut licences filter on the
                        # refresh date but date the event by its effective
                        # date). The event date stands in only when the
                        # column is empty or unparseable.
                        wm_val: Any = None
                        if meta.get("watermark_type") != "text":
                            if meta["watermark_col"]:
                                wm_val = parse_watermark(row.get(meta["watermark_col"]))
                            if wm_val is None:
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

            # A snapshot read in table order that fills its cap has rows it
            # never reads: its source outgrew batch_limit (or its where clause
            # lost its scope). A newest-first snapshot (order_by ... DESC) is a
            # window on recent rows by design, so a full page is expected.
            newest_first = bool(_NEWEST_FIRST.match(str(meta.get("order_by") or "")))
            if is_snapshot and not newest_first and records_fetched >= fetch_limit:
                logger.warning(
                    "Job '%s': snapshot poll stopped at its %d-row cap; rows past "
                    "it are never read (raise the feed's batch_limit or narrow "
                    "its where clause)",
                    job_name,
                    fetch_limit,
                )

            # A filtered poll that filled its cap without moving the watermark
            # read only rows at its boundary, and the same filter would read
            # them again: step past the boundary until the watermark moves. A
            # newest-first read would have met any newer row first, so a full
            # page there holds no newer rows and stepping past skips nothing.
            if new_high_watermark != met.high_watermark:
                met.boundary_stalled = False
            elif (
                watermark_filtered
                and not newest_first
                and records_fetched >= fetch_limit
                and not met.boundary_stalled
            ):
                met.boundary_stalled = True
                logger.warning(
                    "Job '%s': a full %d-row poll left the watermark at %s; the next "
                    "poll steps past it and skips the rest of that boundary (raise the "
                    "feed's batch_limit, or order it by its watermark column)",
                    job_name,
                    fetch_limit,
                    new_high_watermark,
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
            if outside_metro:
                logger.info("Job '%s': skipped %d rows outside the metro box", job_name, outside_metro)

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
            "outside_metro": outside_metro,
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
            "snapshot_dedup_size": sum(len(seen) for seen in self.snapshot_dedup.values()),
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
