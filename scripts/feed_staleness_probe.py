"""Probe every registered feed for source and newest-record staleness.

The probe is deliberately a leaf: it reads the canonical registry, uses the
same paginating clients as ingestion, exports Prometheus metrics, and sends a
small JSON page to the configured webhook endpoints.  It does not write to
Kafka or the application database.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
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
from src.producers.arcgis_client import ArcGISClient
from src.producers.carto_client import CartoClient
from src.producers.ckan_client import CkanClient
from src.producers.socrata_client import SocrataClient
from src.producers.watermarks import (
    parse_watermark as parse_timestamp,
)
from src.producers.watermarks import (
    typed_watermark_entry,
    watermark_exclude_clause,
)
from src.spatial.city_registry import (
    REGISTRY,
    DatasetSpec,
    FeedType,
    get_job_name,
    resolve_endpoint,
)

logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(days=7)


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
    """
    raw = spec.extra.get("expected_cadence_days") if spec.extra else None
    try:
        days = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback
    if days <= 0:
        return fallback
    return timedelta(days=2 * days)

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


def _metadata_url(spec: DatasetSpec) -> str | None:
    """Return the native source metadata URL where the platform has one."""
    if spec.platform == "socrata":
        parts = urlsplit(spec.endpoint)
        if "/resource/" not in parts.path:
            return None
        dataset_id = parts.path.rsplit("/", 1)[-1].removesuffix(".json")
        return f"{parts.scheme}://{parts.netloc}/api/views/{dataset_id}.json"
    if spec.platform == "arcgis":
        return spec.endpoint.rstrip("/")
    return None


def fetch_source_updated_at(
    spec: DatasetSpec,
    request_json: Callable[..., Mapping[str, Any]],
) -> datetime | None:
    """Fetch ``rowsUpdatedAt`` or ArcGIS ``lastEditDate`` when available."""
    url = _metadata_url(spec)
    if not url:
        return None
    response = request_json(url, params={"f": "json"} if spec.platform == "arcgis" else {})
    payload = response.json() if hasattr(response, "json") else response
    value = payload.get("rowsUpdatedAt")
    if value is None:
        value = payload.get("data_updated_at")
    if value is None:
        value = payload.get("lastEditDate")
    if value is None:
        value = (payload.get("editingInfo") or {}).get("lastEditDate")
    return parse_timestamp(value)


def client_for(spec: DatasetSpec) -> Any:
    """Construct the platform client used by the ingestion path."""
    clients = {
        "socrata": SocrataClient,
        "arcgis": ArcGISClient,
        "carto": CartoClient,
        "ckan": CkanClient,
    }
    try:
        return clients[spec.platform]()
    except KeyError as exc:
        raise ValueError(f"Unsupported feed platform {spec.platform!r}") from exc

def newest_watermark(
    client: Any,
    spec: DatasetSpec,
    *,
    now: datetime | None = None,
) -> datetime | None:
    """Fetch a bounded newest-row sample and compare values after typed parsing.

    Comparing parsed values matters for NYC's mixed ISO and ``MM/DD/YYYY``
    permit watermark.  A bounded sample keeps the weekly probe cheap while
    retaining the source client's normal pagination and retry behavior.

    Feeds declaring a text watermark type (``spec.extra`` keys
    ``watermark_type`` / ``watermark_format`` / ``watermark_exclude`` — see
    ADR 0005) get their sentinels excluded server-side via a NOT-IN guard so
    garbage rows like PG County's ``ZZZZZZZZ`` cannot crowd out the real
    newest rows, and are compared under the declared strptime format.

    Values strictly after ``now`` are ignored: a future watermark is a source
    data artifact (license expirations and the like), not evidence of
    freshness, so a feed whose only watermarks are future-dated yields
    ``None`` here and ``probe_feed`` treats ``None`` as stale.
    """
    if not spec.watermark_col:
        return None
    now = now or datetime.now(UTC)
    extra = spec.extra or {}
    exclude = extra.get("watermark_exclude") or ()
    is_text = extra.get("watermark_type") == "text"
    fmt = extra.get("watermark_format") if is_text else None
    pages: Iterable[list[dict[str, Any]]] = client.paginate(
        endpoint_url=spec.endpoint,
        order_by=f"{spec.watermark_col} DESC",
        batch_size=1000,
        max_records=1000,
        where_clause=watermark_exclude_clause(spec.watermark_col, exclude),
    )
    entries = [
        entry
        for page in pages
        for row in page
        if (
            entry := typed_watermark_entry(
                row.get(spec.watermark_col),
                fmt=fmt,
                exclude=exclude,
            )
        )
        is not None
    ]
    valid = [entry for entry in entries if entry[1] <= now]
    best = max(valid, key=lambda entry: entry[1]) if valid else None
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
    )


def probe_registry(
    *,
    now: datetime | None = None,
    city_ids: set[str] | None = None,
    threshold: timedelta = STALE_AFTER,
    client_factory: Callable[[DatasetSpec], Any] = client_for,
    metadata_fetcher: Callable[[DatasetSpec], datetime | None] | None = None,
) -> list[ProbeResult]:
    """Probe all registered feeds without per-feed configuration."""
    now = now or datetime.now(UTC)
    metadata_fetcher = metadata_fetcher or (
        lambda spec: fetch_source_updated_at(spec, httpx.get)
    )
    results: list[ProbeResult] = []
    for city, registration in REGISTRY.items():
        if city_ids is not None and city.value not in city_ids:
            continue
        for feed, registered_spec in registration.datasets.items():
            spec = DatasetSpec(**asdict(registered_spec))
            spec.endpoint = resolve_endpoint(spec, today=now.date())
            source_error = None
            try:
                source_updated_at = metadata_fetcher(spec)
            except Exception as exc:  # noqa: BLE001  # one dead feed must not hide others
                source_updated_at = None
                source_error = str(exc)
                PROBE_ERRORS.labels(city.value, feed.value, "metadata").inc()
            try:
                result = probe_feed(
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
                result = ProbeResult(
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
                )
            FEED_AGE_DAYS.labels(city.value, feed.value, spec.platform).set(result.age_days or 0)
            FEED_STALE.labels(city.value, feed.value, spec.platform).set(int(result.stale))
            if result.error:
                PROBE_ERRORS.labels(city.value, feed.value, "probe").inc()
            results.append(result)
    PROBE_RUNS.labels("error" if any(result.error for result in results) else "success").inc()
    return results


def page_stale(results: list[ProbeResult], webhook_urls: list[str]) -> list[int]:
    """Send one generic JSON page for stale feeds to every configured webhook."""
    stale = [asdict(result) for result in results if result.stale]
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
    args = parser.parse_args()

    results = probe_registry(
        city_ids=set(args.cities) if args.cities else None,
        threshold=timedelta(days=args.threshold_days),
    )
    if not args.dry_run:
        page_stale(results, settings.webhook_alert_urls)
    print(json.dumps([asdict(result) for result in results], default=str))
    return 1 if any(result.stale for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
