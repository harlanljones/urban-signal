"""Probe every registered feed for source and newest-record staleness.

The probe is deliberately a leaf: it reads the canonical registry, uses the
same paginating clients as ingestion, exports Prometheus metrics, and sends a
small JSON page to the configured webhook endpoints.  It does not write to
Kafka or the application database.

A run reads each feed's newest rows the way its poll filters them, and probes
the registry's hosts side by side, one request at a time per host, so the
weekly run finishes inside its job's time limit. Each result is logged as it
lands, and a feed not reached by the deadline is reported as not probed.
"""

from __future__ import annotations

import argparse
import email.utils
import json
import logging
import queue
import sys
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

API_ROOT = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import httpx
from prometheus_client import Counter, Gauge
from src.config import settings
from src.producers import tolerant_http
from src.producers.acquisition import (
    AcquisitionSpec,
    build_where,
    newest_valid_watermark,
)
from src.producers.arcgis_client import ArcGISClient
from src.producers.carto_client import CartoClient
from src.producers.ckan_client import CkanClient
from src.producers.csv_client import CSVClient, yearly_files
from src.producers.excel_client import ExcelClient
from src.producers.socrata_client import SocrataClient
from src.producers.watermarks import parse_watermark as parse_timestamp
from src.producers.watermarks import (
    text_date_window,
    text_sorts_as_dates,
    typed_watermark_entry,
)
from src.spatial.city_registry import (
    REGISTRY,
    DatasetSpec,
    FeedType,
    get_job_name,
    resolve_endpoint,
    resolve_zip_member,
)

logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(days=7)

# Rows read newest first. A date column sorts by date, so the first rows hold
# the newest, and a few spare rows ride over future-dated junk at the top. A
# file is downloaded whole and every row counts.
NEWEST_ROWS = 100
FULL_PAGE_ROWS = 1000
# A month-first text date sorts as text ("9/4/2026" after "10/1/2026"), and a
# table's ids need not follow its dates (Worcester's newest permits hold its
# lowest object ids). Such a column is read as its poll reads it, by naming
# the dates (``text_date_window``): the last week, then a window twice as
# long, and so on to ten years, until one holds rows.
FIRST_WINDOW_DAYS = 7
LAST_WINDOW_DAYS = 3650

# Hosts probed side by side; each host's feeds are probed one at a time.
DEFAULT_WORKERS = 16
# The weekly job stops at 20 minutes. No feed starts after the deadline, and
# the run stops waiting for feeds in flight a grace period later; both are
# reported as not probed rather than lost with the job.
DEFAULT_DEADLINE = timedelta(minutes=15)
GRACE_SECONDS = 120.0
# A probe tries a request twice (a client's ``max_retries`` counts every
# attempt), and gives up on a silent host sooner than a poll does.
CLIENT_TIMEOUT_SECONDS = 20.0
CLIENT_ATTEMPTS = 2

# Platforms whose rows the server filters, sorts and trims to named columns.
_SERVER_SIDE = frozenset({"socrata", "arcgis", "ckan", "carto"})


def declared_staleness_threshold(
    spec: DatasetSpec,
    fallback: timedelta = STALE_AFTER,
) -> timedelta:
    """Resolve one feed's staleness alarm window from its declared cadence.

    G11 (wave-2 §2.3): every feed declares ``extra={"expected_cadence_days":
    N}`` and alarms at ``2 × N`` days instead of a global 7 — PG County 311
    publishes ~monthly and would page forever under the old assumption.
    Missing, non-numeric, or non-positive declarations fall back to
    ``fallback``; the registry invariant test keeps that path empty for
    registered feeds.

    The window is never shorter than ``fallback``: a daily feed's newest
    permit on a Monday morning run is Friday's, and its dates have no time,
    so ``2 × 1`` days paged every weekday-only feed every week.
    """
    raw = spec.expected_cadence_days
    try:
        days = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback
    if days <= 0:
        return fallback
    return max(timedelta(days=2 * days), fallback)

FEED_AGE_DAYS = Gauge(
    "urban_signal_feed_age_days",
    "Age in days of the older of source metadata and newest feed watermark",
    ["city_id", "feed", "platform"],
)
FEED_STALE = Gauge(
    "urban_signal_feed_stale",
    "Whether a registered feed is older than the staleness threshold",
    ["city_id", "feed", "platform"],
)
PROBE_RUNS = Counter(
    "urban_signal_feed_staleness_probe_runs_total",
    "Completed feed staleness probe runs",
    ["status"],
)
PROBE_ERRORS = Counter(
    "urban_signal_feed_staleness_probe_errors_total",
    "Feed staleness probe errors",
    ["city_id", "feed", "kind"],
)


@dataclass(frozen=True)
class ProbeResult:
    """The durable, JSON-serializable result for one registered feed."""

    city_id: str
    feed: str
    platform: str
    endpoint: str
    job: str
    source_updated_at: datetime | None
    newest_watermark: datetime | None
    age_days: float | None
    stale: bool
    error: str | None = None
    alarm_exempt: bool = False


NOT_PROBED = "not probed"


def _metadata_url(spec: DatasetSpec) -> str | None:
    """Return the native source metadata URL where the platform has one."""
    if spec.platform == "socrata":
        parts = urlsplit(spec.endpoint)
        if "/resource/" not in parts.path:
            return None
        dataset_id = parts.path.rsplit("/", 1)[-1].removesuffix(".json")
        return f"{parts.scheme}://{parts.netloc}/api/views/{dataset_id}.json"
    if spec.platform in ("arcgis", "gbfs"):
        return spec.endpoint.rstrip("/")
    return None


def response_headers(url: str) -> httpx.Response:
    """The response to a GET of ``url`` with its headers read and its body not.

    A file feed is dated by its ``Last-Modified`` header, and several are
    zips of tens of megabytes, which a plain GET would download only to read
    one header.
    """
    with (
        httpx.Client(timeout=CLIENT_TIMEOUT_SECONDS, follow_redirects=True) as client,
        client.stream("GET", url) as response,
    ):
        return response


def fetch_source_updated_at(
    spec: DatasetSpec,
    request_json: Callable[..., Mapping[str, Any]],
    request_headers: Callable[[str], Any] | None = None,
) -> datetime | None:
    """Fetch ``rowsUpdatedAt``/``lastEditDate``, a GBFS ``last_updated``, or a file's ``Last-Modified``."""
    if spec.platform in ("csv", "excel"):
        # An endpoint written with ``{year}`` names a file a year (Pima
        # County's sales); this year's is the one being rebuilt.
        url = yearly_files(spec.endpoint)[0][0]
        try:
            response = (request_headers or request_json)(url)
        except Exception:  # noqa: BLE001  # a csv HEAD failure must not hide others
            return None
        header = response.headers.get("last-modified") if hasattr(response, "headers") else None
        if not header:
            return None
        try:
            parsed = email.utils.parsedate_to_datetime(header)
        except (TypeError, ValueError):
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    url = _metadata_url(spec)
    if not url:
        return None
    response = request_json(url, params={"f": "json"} if spec.platform == "arcgis" else {})
    payload = response.json() if hasattr(response, "json") else response
    if spec.platform == "gbfs":
        # GBFS 2.x stamps each file with POSIX seconds, 3.0 with RFC 3339.
        value = payload.get("last_updated")
        if isinstance(value, int | float) and not isinstance(value, bool):
            return datetime.fromtimestamp(value, UTC)
        return parse_timestamp(value)
    value = payload.get("rowsUpdatedAt")
    if value is None:
        value = payload.get("data_updated_at")
    if value is None:
        value = payload.get("lastEditDate")
    if value is None:
        value = (payload.get("editingInfo") or {}).get("lastEditDate")
    return parse_timestamp(value)


def client_for(spec: DatasetSpec) -> Any:
    """Construct the platform client used by the ingestion path.

    A GBFS feed has no rows to date (its files carry ``last_updated``), so it
    gets no client.
    """
    if spec.platform == "gbfs":
        return None
    api_clients = {
        "socrata": SocrataClient,
        "arcgis": ArcGISClient,
        "carto": CartoClient,
        "ckan": CkanClient,
    }
    if spec.platform == "arcgis":
        # The probe reads a date column, never a geometry.
        return ArcGISClient(
            timeout_seconds=CLIENT_TIMEOUT_SECONDS,
            max_retries=CLIENT_ATTEMPTS,
            return_geometry=False,
        )
    if spec.platform in api_clients:
        return api_clients[spec.platform](
            timeout_seconds=CLIENT_TIMEOUT_SECONDS, max_retries=CLIENT_ATTEMPTS
        )
    file_clients = {"csv": CSVClient, "excel": ExcelClient}
    try:
        return file_clients[spec.platform]()
    except KeyError as exc:
        raise ValueError(f"Unsupported feed platform {spec.platform!r}") from exc


def _row_value(row: Mapping[str, Any], key: str) -> Any:
    """Case-insensitive cell lookup.

    Some clients (CSVClient lowercases headers; CkanClient's non-SQL
    ``datastore_search`` path returns lowercase keys) transform the column
    casing a feed declared in the registry, so a literal ``row.get(key)`` for
    an uppercase watermark column (e.g. Pittsburgh deeds ``RECORDDATE``)
    misses. Prefer the exact key, then a lowercased fallback.
    """
    if key in row:
        return row[key]
    return row.get(key.lower())


def file_options(spec: DatasetSpec) -> dict[str, Any]:
    """The options a file feed's poll hands its client (the zip member,
    delimiter, header row, point column, linked file, column list and the
    watermark's declared format), so the probe parses the file as the poll
    does. Each client ignores the options that are not its own."""
    options: dict[str, Any] = {
        "zip_member": resolve_zip_member(spec) if spec.zip_member else None,
        "delimiter": spec.delimiter,
        "columns": list(spec.columns or []) or None,
        "point_col": spec.point_col,
        "point_lon_first": spec.point_lon_first,
        "link_pattern": spec.link_pattern,
        "fallback_endpoints": list(spec.fallback_endpoints or []) or None,
        "select": spec.select,
        "watermark_col": spec.watermark_col,
        "watermark_format": spec.watermark_format,
        "watermark_exclude": list(spec.watermark_exclude or []) or None,
    }
    return {key: value for key, value in options.items() if value}


def _row_id(spec: DatasetSpec, client: Any) -> str | None:
    """The column a server numbers its rows by, where it has one."""
    if spec.platform == "arcgis":
        return client.get_layer_metadata(spec.endpoint)["oid_field"]
    return {"socrata": ":id", "ckan": "_id"}.get(spec.platform)


def text_windows(spec: DatasetSpec, acq: AcquisitionSpec, now: datetime) -> list[str]:
    """Filters naming each date from a week, two weeks, four and so on up to
    ten years before ``now`` to its day, as a month-first text column writes
    them, for a server that filters rows (an ArcGIS layer or a Socrata
    resource). Empty for any other column, or a format the window cannot
    name day by day."""
    fmt = acq.watermark_format
    if (
        spec.platform not in ("arcgis", "socrata")
        or acq.watermark_type != "text"
        or not fmt
        or text_sorts_as_dates(fmt)
    ):
        return []
    windows: list[str] = []
    days = FIRST_WINDOW_DAYS
    while True:
        start = datetime.combine((now - timedelta(days=days)).date(), datetime.min.time())
        window = text_date_window(spec.watermark_col, ">=", start.strftime(fmt), fmt, today=now.date())
        if window is None:
            return []
        windows.append(window)
        if days >= LAST_WINDOW_DAYS:
            return windows
        days = min(2 * days, LAST_WINDOW_DAYS)


def probe_reads(spec: DatasetSpec, acq: AcquisitionSpec, client: Any) -> list[tuple[str, int | None]]:
    """The reads a probe makes of a feed (``text_windows`` aside): each an
    order and a row count.

    A date or number column, or a text one written year first
    (``%Y-%m-%d``), sorts by date, so its first rows are the newest. A text
    column whose type the spec leaves open may hold dates that sort as text
    (NYC's permits mix "2020-06-05" and "09/30/2026"), so a full page of the
    newest rows by row id backs up the read by value: ids drift from dates
    (Lincoln's newest 100 permits by object id end in December 2025, its
    newest 1,000 reach January 2026). So it does on CKAN, which takes no
    existence check (see ``newest_watermark``) and sorts rows without a date
    first in a descending read. A month-first text date the window cannot
    name is read by row id alone. A file is read whole.
    """
    newest_first = f"{spec.watermark_col} DESC"
    if spec.platform not in _SERVER_SIDE:
        return [(newest_first, None)]
    if spec.platform == "arcgis":
        # The layer types its fields, and the poll's first request reads
        # them anyway.
        meta = client.get_layer_metadata(spec.endpoint)
        typed = meta["date_fields"] | set(meta.get("numeric_fields", ()))
        if spec.watermark_col in typed:
            return [(newest_first, NEWEST_ROWS)]
    row_id = _row_id(spec, client)
    if row_id is None:
        return [(newest_first, NEWEST_ROWS)]
    by_row_id = (f"{row_id} DESC", FULL_PAGE_ROWS)
    if acq.watermark_type == "text" and not text_sorts_as_dates(acq.watermark_format):
        return [by_row_id]
    if acq.watermark_type and spec.platform != "ckan":
        return [(newest_first, NEWEST_ROWS)]
    return [(newest_first, NEWEST_ROWS), by_row_id]


def newest_watermark(
    client: Any,
    spec: DatasetSpec,
    *,
    now: datetime | None = None,
) -> datetime | None:
    """The newest valid watermark among the rows the feed's poll would read.

    The feed's own filter applies, so a statewide table is dated by the rows
    its city reads. A server-side read asks for the watermark column alone:
    a month-first text date by the windows ``text_windows`` names, the
    first that holds rows, and any other column in the orders
    ``probe_reads`` names, rows where it is set. A file is read whole, as its
    poll reads it.
    """
    if not spec.watermark_col:
        return None
    now = now or datetime.now(UTC)
    # The sentinel guard (ADR 0005) and the US-111 future-guard now come from
    # the AcquisitionEngine; only the probe-specific newest-first ordering and
    # per-column case-insensitive lookup stay here.
    acq = AcquisitionSpec.from_dataset_spec(spec)
    exclude = acq.watermark_exclude
    server_side = spec.platform in _SERVER_SIDE
    # A file's client compares and sorts by the declared format whatever the
    # type (Boulder's sales write "9/15/2026 12:00:00 AM"); a server's column
    # is text only where the spec says so.
    fmt = acq.watermark_format if acq.watermark_type == "text" or not server_side else None
    kwargs: dict[str, Any] = {"select": spec.watermark_col} if server_side else file_options(spec)

    def read(order_by: str, rows: int | None, where: str | None) -> list[tuple[str, datetime]]:
        pages: Iterable[list[dict[str, Any]]] = client.paginate(
            endpoint_url=spec.endpoint,
            order_by=order_by,
            batch_size=rows or FULL_PAGE_ROWS,
            max_records=rows,
            where_clause=build_where(
                base_where=where,
                watermark_col=spec.watermark_col,
                high_watermark=None,
                endpoint=spec.endpoint,
                watermark_exclude=exclude,
            ),
            **kwargs,
        )
        return [
            entry
            for page in pages
            for row in page
            if (
                entry := typed_watermark_entry(
                    _row_value(row, spec.watermark_col),
                    fmt=fmt,
                    exclude=exclude,
                )
            )
            is not None
        ]

    entries: list[tuple[str, datetime]] = []
    windows = text_windows(spec, acq, now) if server_side else []
    if windows:
        newest_ids = f"{_row_id(spec, client)} DESC"
        for window in windows:
            entries = read(newest_ids, FULL_PAGE_ROWS, f"({spec.where}) AND {window}" if spec.where else window)
            if entries:
                break
    else:
        base_where = spec.where
        if server_side and spec.platform != "ckan":
            # Rows without a date sort first in a descending read on some
            # servers. CKAN is left alone: the guard would send every read to
            # its SQL action, which WPRDC refuses, and its row-id read covers
            # NULLs.
            present = f"{spec.watermark_col} IS NOT NULL"
            base_where = f"({base_where}) AND {present}" if base_where else present
        for order_by, rows in probe_reads(spec, acq, client):
            entries.extend(read(order_by, rows, base_where))
    best = newest_valid_watermark(entries, now)
    return best[1] if best else None


def probe_feed(
    city_id: str,
    feed: FeedType,
    spec: DatasetSpec,
    *,
    now: datetime,
    client: Any,
    source_updated_at: datetime | None = None,
    source_error: str | None = None,
    threshold: timedelta = STALE_AFTER,
) -> ProbeResult:
    """Probe one feed; source metadata errors do not hide row freshness."""
    row_error = None
    try:
        newest = newest_watermark(client, spec, now=now)
    except Exception as exc:  # noqa: BLE001  # client errors vary by platform
        newest = None
        row_error = str(exc)

    timestamps = [value for value in (source_updated_at, newest) if value is not None]
    oldest = min(timestamps) if timestamps else None
    age_days = (now - oldest).total_seconds() / 86400 if oldest else None
    stale = oldest is None or now - oldest > threshold
    errors = "; ".join(error for error in (source_error, row_error) if error) or None
    if oldest is None and errors is None:
        errors = (
            "no rows with a valid watermark"
            if spec.watermark_col
            else "no watermark column, and the source gives no update time"
        )
    # Documented-dead / intentionally-unmaintained feeds (extra["alarm_exempt"])
    # are still reported with their true staleness but do not page the alarm:
    # their source has no live replacement and the human has accepted the gap.
    alarm_exempt = bool(spec.alarm_exempt)
    return ProbeResult(
        city_id=city_id,
        feed=feed.value,
        platform=spec.platform,
        endpoint=spec.endpoint,
        job=get_job_name(
            feed,
            next(cid for cid, reg in REGISTRY.items() if reg.city_id.value == city_id),
        ),
        source_updated_at=source_updated_at,
        newest_watermark=newest,
        age_days=age_days,
        stale=stale,
        error=errors,
        alarm_exempt=alarm_exempt,
    )


def host_of(endpoint: str) -> str:
    """The host a feed's requests go to (``carto://phl.carto.com/...`` too)."""
    return (urlsplit(endpoint).hostname or "").lower()


def host_matches(host: str, patterns: Iterable[str]) -> bool:
    """Whether ``host`` is one of ``patterns`` or under one of them."""
    host = host.lower()
    return any(host == p or host.endswith("." + p) for p in (p.lower().strip(".") for p in patterns))


def probe_registry(
    *,
    now: datetime | None = None,
    city_ids: set[str] | None = None,
    threshold: timedelta = STALE_AFTER,
    client_factory: Callable[[DatasetSpec], Any] = client_for,
    metadata_fetcher: Callable[[DatasetSpec], datetime | None] | None = None,
    workers: int = DEFAULT_WORKERS,
    deadline: timedelta | None = DEFAULT_DEADLINE,
    skip_hosts: Iterable[str] = (),
    min_host_gap: float = 0.0,
    on_result: Callable[[ProbeResult], None] | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> list[ProbeResult]:
    """Probe all registered feeds without per-feed configuration.

    Hosts are probed side by side (``workers`` at a time), and each host's
    feeds one after another, ``min_host_gap`` seconds apart. A feed on a
    host in ``skip_hosts``, or not started by ``deadline``, comes back not
    probed (and not stale). Results keep the registry's order.
    """
    now = now or datetime.now(UTC)
    metadata_fetcher = metadata_fetcher or (
        lambda spec: fetch_source_updated_at(spec, tolerant_http.get, response_headers)
    )
    skip = tuple(skip_hosts)
    started = clock()
    jobs: list[tuple[int, Any, FeedType, DatasetSpec]] = []
    for city, registration in REGISTRY.items():
        if city_ids is not None and city.value not in city_ids:
            continue
        for feed, registered_spec in registration.datasets.items():
            spec = DatasetSpec(**asdict(registered_spec))
            # A zip whose members are a file a year (St. Louis's ``csb.zip``)
            # keeps its URL; ``file_options`` names this year's member.
            if not spec.zip_member:
                spec.endpoint = resolve_endpoint(spec, today=now.date())
            jobs.append((len(jobs), city, feed, spec))

    by_host: dict[str, list[tuple[int, Any, FeedType, DatasetSpec]]] = defaultdict(list)
    for job in jobs:
        by_host[host_of(job[3].endpoint)].append(job)

    results: list[ProbeResult | None] = [None] * len(jobs)
    lock = threading.Lock()

    def not_probed(city: Any, feed: FeedType, spec: DatasetSpec, why: str) -> ProbeResult:
        return ProbeResult(
            city_id=city.value,
            feed=feed.value,
            platform=spec.platform,
            endpoint=spec.endpoint,
            job=get_job_name(feed, city),
            source_updated_at=None,
            newest_watermark=None,
            age_days=None,
            stale=False,
            error=f"{NOT_PROBED}: {why}",
            alarm_exempt=bool(spec.alarm_exempt),
        )

    def probe_one(city: Any, feed: FeedType, spec: DatasetSpec) -> ProbeResult:
        source_error = None
        try:
            source_updated_at = metadata_fetcher(spec)
        except Exception as exc:  # noqa: BLE001  # one dead feed must not hide others
            source_updated_at = None
            source_error = str(exc)
            PROBE_ERRORS.labels(city.value, feed.value, "metadata").inc()
        try:
            return probe_feed(
                city.value,
                feed,
                spec,
                now=now,
                client=client_factory(spec),
                source_updated_at=source_updated_at,
                source_error=source_error,
                threshold=declared_staleness_threshold(spec, fallback=threshold),
            )
        except Exception as exc:  # noqa: BLE001  # defensive boundary
            return ProbeResult(
                city_id=city.value,
                feed=feed.value,
                platform=spec.platform,
                endpoint=spec.endpoint,
                job=get_job_name(feed, city),
                source_updated_at=source_updated_at,
                newest_watermark=None,
                age_days=None,
                stale=True,
                error=str(exc),
                alarm_exempt=bool(spec.alarm_exempt),
            )

    def record(index: int, result: ProbeResult) -> None:
        if not (result.error or "").startswith(NOT_PROBED):
            FEED_AGE_DAYS.labels(result.city_id, result.feed, result.platform).set(result.age_days or 0)
            FEED_STALE.labels(result.city_id, result.feed, result.platform).set(int(result.stale))
            if result.error:
                PROBE_ERRORS.labels(result.city_id, result.feed, "probe").inc()
        with lock:
            results[index] = result
            if on_result is not None:
                on_result(result)

    def probe_host(host: str, host_jobs: list[tuple[int, Any, FeedType, DatasetSpec]]) -> None:
        skipped = host_matches(host, skip) if skip else False
        last_end: float | None = None
        for index, city, feed, spec in host_jobs:
            if skipped:
                record(index, not_probed(city, feed, spec, f"{host} is excluded"))
                continue
            if deadline is not None and clock() - started > deadline.total_seconds():
                record(index, not_probed(city, feed, spec, "the run's deadline passed"))
                continue
            if last_end is not None and min_host_gap > 0:
                wait = min_host_gap - (clock() - last_end)
                if wait > 0:
                    sleep(wait)
            record(index, probe_one(city, feed, spec))
            last_end = clock()

    # Busiest hosts first, so the longest queue starts at once.
    pending: queue.SimpleQueue[tuple[str, list[tuple[int, Any, FeedType, DatasetSpec]]]] = queue.SimpleQueue()
    for item in sorted(by_host.items(), key=lambda item: -len(item[1])):
        pending.put(item)

    def work() -> None:
        while True:
            try:
                host, host_jobs = pending.get_nowait()
            except queue.Empty:
                return
            probe_host(host, host_jobs)

    # Daemon threads: a feed still in flight at the hard stop is reported and
    # left behind, so a hung download cannot hold the run past its job limit.
    threads = [threading.Thread(target=work, daemon=True) for _ in range(max(1, min(workers, len(by_host))))]
    for thread in threads:
        thread.start()
    hard_stop = None if deadline is None else started + deadline.total_seconds() + GRACE_SECONDS
    for thread in threads:
        thread.join(None if hard_stop is None else max(0.0, hard_stop - clock()))

    with lock:
        snapshot = list(results)
    final = [
        result
        if result is not None
        else not_probed(city, feed, spec, "the run stopped before this feed finished")
        for result, (_, city, feed, spec) in zip(snapshot, jobs, strict=True)
    ]
    probed = [result for result in final if not (result.error or "").startswith(NOT_PROBED)]
    PROBE_RUNS.labels("error" if any(result.error for result in probed) else "success").inc()
    return final


def page_stale(results: list[ProbeResult], webhook_urls: list[str]) -> list[int]:
    """Send one generic JSON page for stale feeds to every configured webhook."""
    stale = [asdict(result) for result in results if result.stale and not result.alarm_exempt]
    if not stale or not webhook_urls:
        return []
    stale = json.loads(json.dumps(stale, default=_json_default))
    payload = {"event": "feed_staleness", "stale_feeds": stale, "count": len(stale)}
    statuses: list[int] = []
    with httpx.Client(timeout=10.0) as client:
        for url in webhook_urls:
            response = client.post(url, json=payload)
            statuses.append(response.status_code)
    return statuses


def _json_default(value: Any) -> str:
    """Serialize probe values without losing timestamp precision in pages."""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def progress_line(result: ProbeResult) -> str:
    """One feed's result as a log line, so a cut-off run still leaves its census."""
    newest = result.newest_watermark.date().isoformat() if result.newest_watermark else "-"
    source = result.source_updated_at.date().isoformat() if result.source_updated_at else "-"
    age = f"{result.age_days:.1f}d" if result.age_days is not None else "-"
    state = "STALE" if result.stale else "ok"
    if result.stale and result.alarm_exempt:
        state = "stale (exempt)"
    if (result.error or "").startswith(NOT_PROBED):
        state = "skipped"
    line = f"{state:<15} {result.city_id}/{result.feed} [{result.platform}] newest={newest} source={source} age={age}"
    if result.error:
        line += f" error={result.error[:160]}"
    return line


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", action="append", dest="cities", help="Limit to a city id")
    parser.add_argument(
        "--threshold-days",
        type=float,
        default=7.0,
        help=(
            "Fallback staleness threshold in days for feeds without a "
            "declared expected_cadence_days (feeds with a declaration "
            "alarm at 2 x N days instead)"
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not send webhook pages")
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS, help="Hosts probed side by side"
    )
    parser.add_argument(
        "--deadline-minutes",
        type=float,
        default=DEFAULT_DEADLINE.total_seconds() / 60,
        help="Report feeds not started by then as not probed (0 for no deadline)",
    )
    parser.add_argument(
        "--skip-host",
        action="append",
        default=[],
        help="Do not request this host or its subdomains (repeatable)",
    )
    parser.add_argument(
        "--min-host-gap",
        type=float,
        default=0.0,
        help="Seconds from the end of one feed's probe to the start of the next on a host",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    began = time.monotonic()
    results = probe_registry(
        city_ids=set(args.cities) if args.cities else None,
        threshold=timedelta(days=args.threshold_days),
        workers=args.workers,
        deadline=timedelta(minutes=args.deadline_minutes) if args.deadline_minutes > 0 else None,
        skip_hosts=args.skip_host,
        min_host_gap=args.min_host_gap,
        on_result=lambda result: print(progress_line(result), file=sys.stderr, flush=True),
    )
    if not args.dry_run:
        page_stale(results, settings.webhook_alert_urls)
    skipped = sum(1 for result in results if (result.error or "").startswith(NOT_PROBED))
    stale = sum(1 for result in results if result.stale and not result.alarm_exempt)
    print(
        f"{len(results)} feeds in {time.monotonic() - began:.0f} s: {stale} stale, "
        f"{sum(1 for r in results if r.stale and r.alarm_exempt)} stale but exempt, "
        f"{skipped} not probed",
        file=sys.stderr,
        flush=True,
    )
    print(json.dumps([asdict(result) for result in results], default=str))
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
