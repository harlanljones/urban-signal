"""Bulk backfill loader: load registered feeds through the streaming path.

Sibling of ``backfill_probe.py``. Where the probe is read-only, this loader
publishes: every row flows through the same parse+publish machinery as the
scheduler (producer ``parse_socrata_row`` → raw Kafka topic via the producer's
avro client), so PostGIS parity measured after a load is real streaming parity.

Design notes:

* Reuses ``MunicipalIngestionScheduler`` for job metadata, platform clients,
  producers, dedup filter, and DLQ routing — one source of truth for the
  ingestion contract, no duplicated field maps.
* Platform-aware default page sizes; every portal accepts smaller.
* Windowed parity is the default (``--since-days 90``) per the adjudicated G6
  reading; ``--full`` loads complete history.
* Snapshot feeds (no watermark column) load their table head under
  ``--max-rows-per-feed``.
* The per-feed report's ``max_watermark_seen`` is the seed value for the
  durable watermark store (US-106).

Run on the host against the staging compose stack:

    KAFKA_BOOTSTRAP_SERVERS=localhost:9092 python scripts/backfill_loader.py \
        --city baltimore --since-days 90
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from src.producers.scheduler import MunicipalIngestionScheduler
from src.producers.watermarks import (
    typed_watermark_entry,
    watermark_exclude_clause,
)

logger = logging.getLogger(__name__)

# Conservative per-platform page sizes. Clients further clamp to their own
# transport limits (e.g. ArcGIS maxRecordCount).
PLATFORM_PAGE_SIZE = {
    "socrata": 5000,
    "ckan": 10000,
    "arcgis": 2000,
    "carto": 5000,
}

WM_ATTRS = ("issuance_date", "created_date", "effective_date", "recorded_date")


def select_jobs(
    scheduler: MunicipalIngestionScheduler,
    cities: Iterable[str] | None,
    feeds: Iterable[str] | None,
) -> list[str]:
    """Filter job names by registered city ids and producer keys."""
    city_set = {c.strip().lower() for c in cities or [] if c.strip()}
    feed_set = {f.strip().lower() for f in feeds or [] if f.strip()}
    selected: list[str] = []
    for job_name, meta in sorted(scheduler.job_metadata.items()):
        if city_set and str(meta.get("city_id", "")).lower() not in city_set:
            continue
        if feed_set and str(meta.get("producer_key", "")).lower() not in feed_set:
            continue
        selected.append(job_name)
    return selected


def build_query_shape(
    meta: dict[str, Any], since_dt: datetime | None
) -> tuple[str | None, dict[str, Any]]:
    """Return ``(where_clause, client_kwargs)`` for a backfill pass.

    Snapshot feeds carry no watermark column: no where, no order — the load is
    a table-head sweep bounded by ``max_records``. Watermarked feeds filter to
    the window (plus the declared sentinel guard, ADR 0005) and page
    newest-first so a capped run keeps the freshest slice.
    """
    wm = meta.get("watermark_col")
    if not wm:
        return None, {}

    parts: list[str] = []
    if since_dt is not None:
        parts.append(f"{wm} >= {_watermark_literal(meta, since_dt)}")
    guard = watermark_exclude_clause(wm, meta.get("watermark_exclude") or [])
    if guard:
        parts.append(guard)

    client_kwargs: dict[str, Any] = {}
    if not _is_dc_arcgis(meta):
        client_kwargs["order_by"] = f"{wm} DESC"
    return " AND ".join(parts) or None, client_kwargs


_DC_ARCGIS_HOSTS = ("maps2.dcgis.dc.gov",)


def _is_dc_arcgis(meta: dict[str, Any]) -> bool:
    """Whether the feed's server is the Washington DC ArcGIS server.

    ``maps2.dcgis.dc.gov`` is unlike every other registered server: it rejects
    ISO-string date comparisons in ``where`` (400 "Unable to complete
    operation") and the ``where + orderByFields`` combination. Its working
    query shape is ``where <date_col> >= date 'YYYY-MM-DD'`` with no
    orderByFields (OID paging) — the shape the scheduler uses (US-109).
    """
    return any(host in str(meta.get("endpoint", "")) for host in _DC_ARCGIS_HOSTS)


def _watermark_literal(meta: dict[str, Any], since_dt: datetime) -> str:
    """Render a watermark lower-bound literal the server accepts.

    The DC ArcGIS server only accepts ANSI ``date 'YYYY-MM-DD'`` literals for
    date columns; every other registered platform accepts the ISO 8601 string.
    """
    if _is_dc_arcgis(meta):
        return f"date '{since_dt.strftime('%Y-%m-%d')}'"
    return f"'{since_dt.strftime('%Y-%m-%dT%H:%M:%S')}'"


def backfill_job(
    scheduler: MunicipalIngestionScheduler,
    job_name: str,
    *,
    since_dt: datetime | None,
    max_rows: int | None,
    page_size: int | None,
    batch_delay_seconds: float,
) -> dict[str, Any]:
    """Bulk-load one job; returns its report entry."""
    meta = scheduler.job_metadata[job_name]
    platform = meta.get("platform", "socrata")
    city_id = meta["city_id"]

    fetched = published = duplicates = drops = 0
    max_watermark_seen: str | None = None
    error: str | None = None
    # US-111 future-watermark guard (mirrors the scheduler): a future/sentinel
    # row must not become the seeded tail watermark — sla_dc carries 2028 rows
    # that would pin `INITIALISSUEDATE > '2028-...'` until then.
    now_dt = datetime.now(timezone.utc)

    try:
        # Resolve the platform client inside the guarded section: a missing
        # client is a per-job error report, never a whole-run crash.
        client = scheduler._paginating_client_for(job_name)
        producer_wrapper = scheduler.producers[meta["producer_key"]]
        where_clause, client_kwargs = build_query_shape(meta, since_dt)
        effective_page = page_size or PLATFORM_PAGE_SIZE.get(platform, 1000)
        for batch in client.paginate(
            endpoint_url=meta["endpoint"],
            where_clause=where_clause,
            batch_size=effective_page,
            max_records=max_rows,
            **client_kwargs,
        ):
            for row in batch:
                fetched += 1
                rec_id = scheduler._extract_record_id(job_name, row)

                if scheduler.dedup.check_and_add(rec_id):
                    duplicates += 1
                    continue

                # Track text-typed watermarks from the raw column before
                # parsing (ADR 0005), exactly like the scheduler.
                if meta.get("watermark_type") == "text":
                    entry = typed_watermark_entry(
                        row.get(meta["watermark_col"]),
                        fmt=meta.get("watermark_format"),
                        exclude=meta.get("watermark_exclude") or [],
                    )
                    if entry:
                        parsed = entry[1]
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=timezone.utc)
                        if parsed <= now_dt and (
                            max_watermark_seen is None or entry[0] > max_watermark_seen
                        ):
                            max_watermark_seen = entry[0]

                try:
                    event = producer_wrapper.parse_socrata_row(row, city_id=city_id)
                    if event is None:
                        drops += 1
                        scheduler.dlq_producer.route_to_dlq(
                            failed_topic=meta["topic"],
                            key=rec_id,
                            payload=row,
                            error_msg="backfill: parse_socrata_row returned None",
                        )
                        continue

                    key = (
                        getattr(event, "job_id", None)
                        or getattr(event, "incident_id", None)
                        or getattr(event, "license_id", None)
                        or getattr(event, "doc_id", None)
                        or rec_id
                    )
                    resolved_city = getattr(event, "city_id", city_id)
                    producer_wrapper.producer.produce(
                        topic=meta["topic"],
                        key=f"{resolved_city}:{key}",
                        payload=event,
                    )
                    published += 1

                    if meta.get("watermark_type") != "text":
                        for attr in WM_ATTRS:
                            wm_val = getattr(event, attr, None)
                            if wm_val:
                                if wm_val.tzinfo is None:
                                    wm_val = wm_val.replace(tzinfo=timezone.utc)
                                if wm_val > now_dt:
                                    logger.warning(
                                        "backfill %s: ignoring future watermark %s (US-111)",
                                        job_name,
                                        wm_val,
                                    )
                                    break
                                wm_str = wm_val.strftime("%Y-%m-%dT%H:%M:%S")
                                if max_watermark_seen is None or wm_str > max_watermark_seen:
                                    max_watermark_seen = wm_str
                                break
                except Exception as parse_err:  # noqa: BLE001
                    drops += 1
                    logger.warning("backfill %s: row error: %s", job_name, parse_err)
                    scheduler.dlq_producer.route_to_dlq(
                        failed_topic=meta["topic"],
                        key=rec_id,
                        payload=row,
                        error_msg=str(parse_err),
                    )

            if batch_delay_seconds > 0:
                time.sleep(batch_delay_seconds)

        producer_wrapper.producer.flush()
    except Exception as exc:  # noqa: BLE001
        error = f"fetch/publish aborted: {exc}"
        logger.error("backfill %s: %s", job_name, exc)

    return {
        "job": job_name,
        "city_id": city_id,
        "feed": meta["producer_key"],
        "platform": platform,
        "mode": "snapshot" if not meta.get("watermark_col") else "windowed" if since_dt else "full",
        "where_clause": where_clause,
        "fetched": fetched,
        "published": published,
        "duplicates": duplicates,
        "parse_drops": drops,
        "max_watermark_seen": max_watermark_seen,
        "error": error,
    }


def _seed_state_file(path: str, reports: list[dict[str, Any]]) -> int:
    """Merge backfill tail watermarks into a scheduler state file (US-106).

    Keeps the max per job under the scheduler's string-compare semantics and
    never lowers an existing watermark; errored feeds are skipped.
    """
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        existing = {}
    seeded = 0
    for report in reports:
        job = report.get("job")
        wm = report.get("max_watermark_seen")
        if not job or not wm or report.get("error"):
            continue
        current = (existing.get(job) or {}).get("high_watermark")
        if current and str(current) >= str(wm):
            continue
        existing[job] = {
            "high_watermark": wm,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "seeded_by": "backfill_loader",
        }
        seeded += 1
    tmp = state_path.with_suffix(state_path.suffix + ".tmp")
    tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    os.replace(tmp, state_path)
    logger.info("Seeded %d job watermarks into %s", seeded, state_path)
    return seeded


def main(argv: list[str] | None = None, scheduler: Any = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--city", action="append", help="Limit to a city id (repeatable)")
    parser.add_argument("--feed", action="append", help="Limit to a producer key: permits/311/sla/deeds (repeatable)")
    parser.add_argument(
        "--since-days",
        type=int,
        default=90,
        help="Windowed parity: load rows with watermark >= now-N days (default 90)",
    )
    parser.add_argument("--full", action="store_true", help="Load complete history instead of the window")
    parser.add_argument("--max-rows-per-feed", type=int, default=None, help="Hard cap per feed")
    parser.add_argument("--page-size", type=int, default=None, help="Override platform default page size")
    parser.add_argument("--batch-delay-seconds", type=float, default=0.5, help="Politeness sleep between pages")
    parser.add_argument(
        "--seed-state",
        default=None,
        help="Write each feed's tail watermark into this scheduler state file (US-106)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

    scheduler = scheduler or MunicipalIngestionScheduler()
    jobs = select_jobs(scheduler, args.city, args.feed)
    if not jobs:
        parser.error("no registered jobs match the given --city/--feed filters")

    since_dt = None
    if not args.full:
        since_dt = datetime.now(timezone.utc) - timedelta(days=args.since_days)

    reports = [
        backfill_job(
            scheduler,
            job_name,
            since_dt=since_dt,
            max_rows=args.max_rows_per_feed,
            page_size=args.page_size,
            batch_delay_seconds=args.batch_delay_seconds,
        )
        for job_name in jobs
    ]

    print(json.dumps(reports, indent=2))
    if args.seed_state:
        _seed_state_file(args.seed_state, reports)
    return 1 if any(r["error"] for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
