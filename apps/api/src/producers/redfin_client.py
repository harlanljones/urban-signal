"""Redfin ZIP-code market tracker ingestion (US-440).

Redfin publishes a full-history, whole-file weekly refresh of its ZIP-level
market tracker on a public S3 bucket — no key, no pagination, no watermark
column: ``https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_
tracker/zip_code_market_tracker.tsv000.gz``. Verified live 2026-09-13:
58 columns, gzip-compressed, tab-delimited, one row per
``(REGION, PROPERTY_TYPE, PERIOD_BEGIN)`` with a rolling 90-day
``PERIOD_DURATION`` window (``PERIOD_BEGIN``/``PERIOD_END`` advance monthly,
the window itself does not shrink to a calendar month). ``REGION`` carries a
``"Zip Code: 94104"`` label rather than a bare ZIP.

This does not reuse :mod:`src.producers.series_client` — that module's
``SeriesSpec`` is one value column per feed spec, matched to Zillow/FHFA's
single-metric-per-file shape. Redfin publishes eight metrics per row in one
file, so refetching and re-parsing the multi-GB file eight times (once per
metric) would be wasteful; ``fetch_bay_area_zip_tracker`` parses it once and
emits :class:`~src.producers.series_client.SeriesObservation` rows for every
registered metric so :class:`~src.features.macro_series_store.MacroSeriesStore`
can ingest them exactly like a Zillow release.

**Aggregate row only.** Redfin breaks every metric out by
``PROPERTY_TYPE`` (single-family, condo, ...); ``PROPERTY_TYPE_ID == -1``
("All Residential") is the cross-type aggregate and is the only row this
ingests — the point of a ZIP-level market signal for LIMS is one number per
ZIP per month, not a property-type-sliced table.

**Revision handling matches Zillow.** Redfin republishes the whole file on
every release, including revisions to prior months, so ingestion is a full
whole-file diff (``ingestion_mode="full"``) exactly like the Zillow/FHFA
series — never an append-only watermark.

**Bay Area scope.** ``fetch_bay_area_zip_tracker`` filters to
:data:`~src.spatial.bay_area_zips.BAY_AREA_ZIP_PREFIXES` before parsing rows
further; this ticket's scope is the nine-county Bay Area, not a national
ingest.
"""

from __future__ import annotations

import csv
import gzip
import io
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime

from src.producers.series_client import SeriesObservation, parse_period, to_float
from src.spatial.bay_area_zips import is_bay_area_zip, normalize_zip

logger = logging.getLogger(__name__)

REDFIN_ZIP_TRACKER_URL = (
    "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/"
    "zip_code_market_tracker.tsv000.gz"
)

# Redfin's aggregate-across-property-types row. Every other PROPERTY_TYPE_ID
# (2 = Condo/Co-op, 3 = Single Family Residential, ...) is a slice of this one.
ALL_RESIDENTIAL_PROPERTY_TYPE_ID = "-1"

REDFIN_ATTRIBUTION = (
    "Data licensed for public use by Redfin (redfin.com/news/data-center)"
)

# series_id suffix (registered under "redfin_<metric>_zip") -> Redfin TSV
# column, and the unit each metric is reported in. Verified live 2026-09-13
# against the 58-column header of zip_code_market_tracker.tsv000.gz.
REDFIN_METRICS: dict[str, tuple[str, str]] = {
    "median_sale_price": ("MEDIAN_SALE_PRICE", "usd"),
    "median_list_price": ("MEDIAN_LIST_PRICE", "usd"),
    "median_ppsf": ("MEDIAN_PPSF", "usd_per_sqft"),
    "homes_sold": ("HOMES_SOLD", "count"),
    "inventory": ("INVENTORY", "count"),
    "pending_sales": ("PENDING_SALES", "count"),
    "median_dom": ("MEDIAN_DOM", "days"),
    "price_drops": ("PRICE_DROPS", "pct"),
}

# Metrics that describe a level (a price, a duration) and must be
# area-*weighted* when spread across hexes, versus metrics that describe a
# count and must be area-*allocated* (US-440 acceptance criteria). Consumed by
# src.spatial.zip_h3_join.
INTENSIVE_REDFIN_METRICS: tuple[str, ...] = (
    "median_sale_price",
    "median_list_price",
    "median_ppsf",
    "median_dom",
    "price_drops",
)
EXTENSIVE_REDFIN_METRICS: tuple[str, ...] = (
    "homes_sold",
    "inventory",
    "pending_sales",
)


class RedfinFetchError(RuntimeError):
    """Raised when the Redfin ZIP tracker is unreachable or unparseable."""


@dataclass(frozen=True)
class RedfinRow:
    """One parsed (zip, period) row with every registered metric."""

    zcta: str
    period: date
    metrics: dict[str, float]


def _get_bytes(url: str, timeout_seconds: float) -> bytes:
    import httpx

    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception as exc:  # httpx.HTTPError and friends
        raise RedfinFetchError(f"{url}: {exc}") from exc


def parse_redfin_tsv(text: str) -> Iterator[RedfinRow]:
    """Parse the decompressed Redfin ZIP tracker TSV into Bay Area rows.

    Filters to Bay Area ZIPs and the "All Residential" aggregate row before
    yielding, so a caller never sees a property-type slice or an
    out-of-scope ZIP. A metric absent or non-numeric for a (zip, period) is
    simply missing from ``metrics`` rather than raising — Redfin reports
    ``NA`` for a metric with too few transactions to publish (rural/PO-box
    and very low-volume ZIPs), and the ZIP-to-H3 join must degrade
    gracefully around that (US-440 acceptance criteria: "handles ZIPs with
    no data gracefully").
    """
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    for row in reader:
        if str(row.get("PROPERTY_TYPE_ID", "")).strip() != ALL_RESIDENTIAL_PROPERTY_TYPE_ID:
            continue
        zcta = normalize_zip(row.get("REGION"))
        if not zcta or not is_bay_area_zip(zcta):
            continue
        period = parse_period(row.get("PERIOD_END"), "month")
        if period is None:
            continue
        metrics: dict[str, float] = {}
        for metric, (column, _unit) in REDFIN_METRICS.items():
            value = to_float(row.get(column))
            if value is not None:
                metrics[metric] = value
        if not metrics:
            # Every metric was NA for this (zip, period) — nothing to yield,
            # but this is not an error; it's how a ZIP with too few
            # transactions that month reports.
            continue
        yield RedfinRow(zcta=zcta, period=period, metrics=metrics)


def redfin_rows_to_observations(
    rows: Iterator[RedfinRow], vintage: str | None = None
) -> list[SeriesObservation]:
    """Flatten parsed Redfin rows into one SeriesObservation per metric.

    Mirrors the shape :class:`~src.features.macro_series_store.MacroSeriesStore`
    already accepts from :class:`~src.producers.series_client.SeriesClient`,
    so a Redfin release upserts through the same store as Zillow/FHFA.
    """
    stamp = vintage or datetime.now(UTC).date().isoformat()
    observations: list[SeriesObservation] = []
    for row in rows:
        for metric, value in row.metrics.items():
            _column, unit = REDFIN_METRICS[metric]
            observations.append(
                SeriesObservation(
                    series_id=f"redfin_{metric}_zip",
                    geography_level="zip",
                    geography_id=row.zcta,
                    period=row.period,
                    value=value,
                    source_vintage=stamp,
                    city_id="san_francisco",
                    unit=unit,
                )
            )
    return observations


def fetch_bay_area_zip_tracker(
    url: str = REDFIN_ZIP_TRACKER_URL,
    timeout_seconds: float = 300.0,
    vintage: str | None = None,
) -> list[SeriesObservation]:
    """Fetch, decompress and parse the full Redfin ZIP tracker for Bay Area ZIPs.

    One whole-file GET (the file is ~1.5 GB compressed as of 2026-09-13;
    ``timeout_seconds`` defaults generously) per Redfin's own publication
    model — there is no incremental/paged variant of this feed.
    """
    raw = _get_bytes(url, timeout_seconds)
    try:
        text = gzip.decompress(raw).decode("utf-8", errors="replace")
    except OSError as exc:
        raise RedfinFetchError(f"{url}: not a valid gzip payload: {exc}") from exc
    rows = parse_redfin_tsv(text)
    return redfin_rows_to_observations(rows, vintage=vintage)
