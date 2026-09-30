"""Bulk backfill loader: load registered feeds through the streaming path.

Sibling of ``backfill_probe.py``. Where the probe is read-only, this loader
publishes: every row flows through the same parse+publish machinery as the
scheduler (producer ``parse_socrata_row`` → raw Kafka topic via the producer's
avro client), so PostGIS parity measured after a load is real streaming parity.

Design notes:

* Reuses ``MunicipalIngestionScheduler`` for job metadata, platform clients,
  client arguments, parcel joins, producers, dedup filter, and DLQ routing —
  one source of truth for the ingestion contract, no duplicated field maps.
* Platform-aware default page sizes; every portal accepts smaller.
* Windowed parity is the default (``--since-days 90``) per the adjudicated G6
  reading; ``--full`` loads complete history.
* Snapshot feeds (no watermark column) load their table head, in the spec's
  own order, under ``--max-rows-per-feed``.
* A text-typed watermark whose format the server cannot order (``MM/DD/YYYY``
  on ArcGIS) is read without a window and filtered client-side; the report's
  ``outside_window`` counts the rows read and left out. A cap then counts rows
  read in the spec's own order.
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
import re
import sys
import time
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from src.producers.acquisition import (
    AcquisitionEngine,
    AcquisitionSpec,
    advance_event_watermark,
    build_where,
)
from src.producers.scheduler import _PAGINATE_KWARGS, MunicipalIngestionScheduler
from src.producers.watermarks import (
    ANSI_DATE_LITERAL_HOSTS,
    casts_text_watermark,
    parse_watermark,
)
from src.spatial.city_registry import DatasetSpec

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

# A date format whose text sorts as its dates do: year first, then month, day
# and time, each zero-padded.
_YEAR_FIRST = re.compile(
    r"^%Y(?:[^%]*%m(?:[^%]*%d(?:[^%]*%H(?:[^%]*%M(?:[^%]*%S(?:[^%]*%f)?)?)?)?)?)?[^%]*$"
)


def _spec_from_meta(meta: dict[str, Any]) -> AcquisitionSpec:
    """Build a typed ``AcquisitionSpec`` for a scheduler job-metadata dict.

    The meaningful watermark keys live at the top level of ``job_metadata``
    (mirroring the typed ``DatasetSpec`` acquisition fields); lift them into an
    ``AcquisitionSpec`` so the engine's WHERE and watermark helpers can be used
    verbatim.
    """
    watermark_exclude = meta.get("watermark_exclude")
    return AcquisitionSpec.from_dataset_spec(
        DatasetSpec(
            endpoint=meta.get("endpoint", ""),
            platform=meta.get("platform", "socrata"),
            watermark_col=meta.get("watermark_col", ""),
            id_keys=list(meta.get("id_keys") or []),
            topic=meta.get("topic", ""),
            producer_key=meta.get("producer_key", ""),
            watermark_type=meta.get("watermark_type"),
            watermark_format=meta.get("watermark_format"),
            watermark_exclude=list(watermark_exclude) if watermark_exclude is not None else None,
            where=meta.get("base_where"),
        )
    )


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

    Every pass keeps the registry's own ``where`` (``base_where``), as
    ``poll_job`` does: on a shared layer it is what scopes the rows to the
    metro (a SNAP state and bbox, a county code, a CA ABC county), so a
    backfill without it would load other places' rows under this city.
    The client gets the arguments ``poll_job`` hands it (``_PAGINATE_KWARGS``):
    a ``select`` that keeps owner and party names out of the rows, a
    workbook's ``link_pattern``, a zipped CSV's member and delimiter, a CSV's
    typed watermark column, a Carto keyset column.
    Snapshot feeds carry no watermark column: no window, and the spec's own
    order — the load is a table-head sweep bounded by ``max_records``.
    Watermarked feeds add the window (plus the declared sentinel guard, ADR
    0005) and page newest-first so a capped run keeps the freshest slice.

    The clause comes from the ``AcquisitionEngine`` WHERE builder (US-182).
    A text-typed column (ADR 0005) compares as the text its format writes, so
    its window starts in that format, as ``poll_job``'s stored watermark does:
    an ISO literal read every ``YYYYMMDD`` date from the first of January. A
    format the server cannot order is windowed client-side instead
    (``client_side_window``).
    """
    base_where = meta.get("base_where")
    wm = meta.get("watermark_col")
    client_kwargs: dict[str, Any] = {
        key: meta[key]
        for key in _PAGINATE_KWARGS.get(meta.get("platform", "socrata"), ())
        if meta.get(key)
    }
    if not wm:
        where = build_where(
            base_where=base_where,
            watermark_col="",
            high_watermark=None,
            endpoint=str(meta.get("endpoint", "")),
            snapshot=True,
        )
        return where, client_kwargs

    spec = _spec_from_meta(meta)
    text_format = meta.get("watermark_format") if meta.get("watermark_type") == "text" else None
    client_window = client_side_window(meta)
    high_watermark = (
        since_dt.strftime(text_format or "%Y-%m-%dT%H:%M:%S")
        if since_dt is not None and not client_window
        else None
    )
    where = build_where(
        base_where=base_where,
        watermark_col=wm,
        high_watermark=high_watermark,
        endpoint=str(meta.get("endpoint", "")),
        watermark_op=">=",
        watermark_exclude=spec.watermark_exclude,
        watermark_type="text" if text_format else None,
        watermark_format=text_format,
    )

    if _is_ansi_date_literal_server(meta):
        client_kwargs.pop("order_by", None)
    elif _sorts_as_dates(meta):
        client_kwargs["order_by"] = f"{wm} DESC"
    # Otherwise the column has no newest-first order; the spec's own stands.
    return where, client_kwargs


def _sorts_as_dates(meta: dict[str, Any]) -> bool:
    """Whether the watermark column, ordered where it is read, is in date order.

    A text-typed column (ADR 0005) sorts as text, which is date order only
    when its format is year first. A CSV sorts in the declared format
    client-side.
    """
    fmt = meta.get("watermark_format")
    if meta.get("watermark_type") != "text" or not fmt or meta.get("platform") == "csv":
        return True
    return bool(_YEAR_FIRST.match(fmt))


def client_side_window(meta: dict[str, Any]) -> str | None:
    """The declared format, when a text column's window cannot be sent.

    A column that does not sort as dates does not compare as them either:
    from ``07/02/2026``, Reno's sales read every December 31 from 2018 to
    2025. San Jose's CKAN filter casts both sides to timestamps
    (``casts_text_watermark``); for the rest (``MM/DD/YYYY`` on ArcGIS,
    Honolulu's ``September 7, 2026 at 1:27 PM``) the backfill reads the feed
    without the window and keeps the rows inside it.
    """
    if not meta.get("watermark_col") or _sorts_as_dates(meta):
        return None
    if casts_text_watermark(
        str(meta.get("endpoint", "")), meta.get("watermark_type"), meta.get("watermark_format")
    ):
        return None
    return meta.get("watermark_format")


def _in_window(value: Any, fmt: str, since_dt: datetime) -> bool:
    """Whether a text watermark falls on or after the window's start.

    The column holds a local time with no zone, so the start's clock time is
    compared as it is. A value that does not parse is outside.
    """
    try:
        parsed = datetime.strptime(str(value).strip(), fmt)  # noqa: DTZ007
    except (TypeError, ValueError):
        return False
    return parsed >= since_dt.replace(tzinfo=None)


def _is_ansi_date_literal_server(meta: dict[str, Any]) -> bool:
    """Whether the feed's server rejects ISO-string date comparisons.

    The DC (``maps2.dcgis.dc.gov``) and Milwaukee (``milwaukeemaps.
    milwaukee.gov``) ArcGIS servers reject ISO-string date comparisons in
    ``where`` AND the ``where + orderByFields`` combination (US-109 / US-87).
    Their working shape is ``where <col> >= date 'YYYY-MM-DD'`` with no
    orderByFields (OID paging) — the shape ``watermark_comparison`` emits.
    """
    return any(host in str(meta.get("endpoint", "")) for host in ANSI_DATE_LITERAL_HOSTS)


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

    fetched = published = duplicates = drops = outside_window = 0
    max_watermark_seen: str | None = None
    error: str | None = None
    # US-111 future-watermark guard (mirrors the scheduler): a future/sentinel
    # row must not become the seeded tail watermark — sla_dc carries 2028 rows
    # that would pin `INITIALISSUEDATE > '2028-...'` until then. The guard now
    # lives in the AcquisitionEngine's watermark helpers (US-182).
    now_dt = datetime.now(timezone.utc)
    spec = _spec_from_meta(meta)
    engine = AcquisitionEngine(spec)

    try:
        # Resolve the platform client inside the guarded section: a missing
        # client is a per-job error report, never a whole-run crash.
        client = scheduler._paginating_client_for(job_name)
        producer_wrapper = scheduler.producers[meta["producer_key"]]
        where_clause, client_kwargs = build_query_shape(meta, since_dt)
        window_format = client_side_window(meta) if since_dt is not None else None
        effective_page = page_size or PLATFORM_PAGE_SIZE.get(platform, 1000)
        for batch in client.paginate(
            endpoint_url=meta["endpoint"],
            where_clause=where_clause,
            batch_size=effective_page,
            max_records=max_rows,
            **client_kwargs,
        ):
            if window_format:
                kept = [
                    row for row in batch
                    if _in_window(row.get(meta["watermark_col"]), window_format, since_dt)
                ]
                outside_window += len(batch) - len(kept)
                batch = kept
            # A sales table without geometry takes each parcel's centroid, as
            # poll_job places it.
            if meta.get("parcel_join") and batch:
                batch = scheduler._join_parcel_centroids(job_name, batch)

            # Text-typed feeds (ADR 0005) track the raw declared-format string
            # from the column before parsing; the engine skips future rows.
            if spec.watermark_type == "text":
                max_watermark_seen = engine.advance_text_watermark(
                    batch,
                    high_watermark=max_watermark_seen,
                    now_dt=now_dt,
                )

            for row in batch:
                fetched += 1
                rec_id = scheduler._extract_record_id(job_name, row)

                if scheduler.dedup.check_and_add(rec_id):
                    duplicates += 1
                    continue

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
                        or getattr(event, "violation_id", None)
                        or getattr(event, "inspection_id", None)
                        or rec_id
                    )
                    resolved_city = getattr(event, "city_id", city_id)
                    producer_wrapper.producer.produce(
                        topic=meta["topic"],
                        key=f"{resolved_city}:{key}",
                        payload=event,
                    )
                    published += 1

                    if spec.watermark_type != "text":
                        # Mirrors poll_job: events without a WM_ATTRS date
                        # fall back to the raw watermark column.
                        wm_candidates = [getattr(event, attr, None) for attr in WM_ATTRS]
                        if not any(wm_candidates) and spec.watermark_col:
                            wm_candidates = [parse_watermark(row.get(spec.watermark_col))]
                        for wm_val in wm_candidates:
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
                                max_watermark_seen = advance_event_watermark(
                                    max_watermark_seen,
                                    wm_val,
                                    now_dt,
                                )
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
        "outside_window": outside_window,
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
