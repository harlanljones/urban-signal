"""Bay Area context-layer builder: one per-hex table the snapshot joins onto the map.

US-439..443 each shipped a Bay Area pipeline that ends in per-H3-res-9 values,
but nothing ran them, so none of it reached a grid tile. This module is the
missing orchestration step: it runs every layer, keeps the handful of metrics
the dashboard renders, and writes them as one table keyed by ``h3_index``.

    <out>/bay_area_context_res9.parquet   h3_index + one nullable Float64 column
                                          per CONTEXT_METRICS key
    <out>/bay_area_context_meta.json      generated_at, per-layer status/rows,
                                          metric catalog with attribution

Layers are independent. A layer that cannot run (no 511 key, an upstream host
down) is recorded as ``skipped``/``failed`` in the meta file and the rest still
publish; a hex a layer never touched carries a null for that layer's metrics,
never a zero, so the map shows "no data" rather than a fake low value.

``src.export.snapshot_builder --context-dir <out>`` consumes the output.

    PYTHONPATH=apps/api python -m src.export.bay_area_context --out build/context
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)

CONTEXT_TABLE = "bay_area_context_res9.parquet"
CONTEXT_META = "bay_area_context_meta.json"
CONTEXT_RESOLUTION = 9
DEFAULT_CACHE_DIR = Path("data") / "bay_area_context"
BAY_511_KEY_ENV = "BAY_511_API_KEY"

# Permit momentum needs the trailing 180 days; fetch a little more so a late
# issuance-date backfill at the window edge still lands.
PERMIT_LOOKBACK_DAYS = 200
PERMIT_MAX_RECORDS = 50_000
# A ZCTA whose latest market print is older than this (relative to the newest
# print in the file) is treated as having no current value.
MARKET_MAX_STALENESS_DAYS = 92

HexValues = dict[str, dict[str, float | None]]


@dataclass(frozen=True)
class ContextMetric:
    """One map-renderable context metric."""

    key: str
    label: str
    layer: str
    unit: str
    description: str


@dataclass(frozen=True)
class ContextLayer:
    """One source pipeline and the attribution its metrics must carry."""

    layer_id: str
    label: str
    attribution: str
    ticket: str


def _layer_catalog() -> dict[str, ContextLayer]:
    from src.producers.redfin_client import REDFIN_ATTRIBUTION
    from src.spatial.context_source import (
        LODES_ATTRIBUTION,
        OVERTURE_BUILDINGS_ATTRIBUTION,
        OVERTURE_PLACES_ATTRIBUTION,
    )
    from src.spatial.series_registry import ZILLOW_ATTRIBUTION

    return {
        "lodes": ContextLayer("lodes", "Employment (LEHD LODES)", LODES_ATTRIBUTION, "US-439"),
        "market": ContextLayer(
            "market",
            "Home prices and rents (Redfin, Zillow)",
            f"{REDFIN_ATTRIBUTION}. {ZILLOW_ATTRIBUTION}.",
            "US-440",
        ),
        "permits": ContextLayer(
            "permits",
            "Building permits (SF, San Jose)",
            "City and County of San Francisco and City of San Jose open data.",
            "US-441",
        ),
        "transit": ContextLayer(
            "transit",
            "Transit access (511 SF Bay GTFS)",
            "Transit data provided by 511.org (Metropolitan Transportation Commission).",
            "US-442",
        ),
        "overture": ContextLayer(
            "overture",
            "Buildings and places (Overture Maps)",
            f"{OVERTURE_BUILDINGS_ATTRIBUTION} {OVERTURE_PLACES_ATTRIBUTION}",
            "US-443",
        ),
    }


CONTEXT_METRICS: tuple[ContextMetric, ...] = (
    ContextMetric("jobs_total", "Jobs (LODES)", "lodes", "jobs",
                  "Workplace jobs (WAC C000) whose census block falls in the hex."),
    ContextMetric("jobs_to_residents", "Jobs per Resident Worker", "lodes", "ratio",
                  "Workplace jobs over resident workers; above 1 is a job center."),
    ContextMetric("transit_score", "Transit Access Score", "transit", "score",
                  "AM-peak frequency within 3 rings, distance-decayed, 0-100."),
    ContextMetric("permit_velocity_60_180", "Permit Velocity (60d vs 180d)", "permits", "ratio",
                  "Permits issued in the last 60 days over a third of the last 180."),
    ContextMetric("permit_capex_60d", "Permit CapEx Density (60d half-life)", "permits", "usd_per_km2",
                  "Permit valuation per km2, decayed with a 60-day half-life."),
    ContextMetric("residential_unit_delta", "Net New Housing Units", "permits", "units",
                  "Proposed minus existing dwelling units on permits in the last 180 days."),
    ContextMetric("median_sale_price", "Median Sale Price", "market", "usd",
                  "Redfin median sale price blended with Zillow ZHVI, area-weighted from ZIPs."),
    ContextMetric("rent_index", "Rent Index (ZORI)", "market", "usd_per_month",
                  "Zillow observed rent index, area-weighted from ZIPs."),
    ContextMetric("building_count", "Building Count", "overture", "buildings",
                  "Overture building footprints whose centroid falls in the hex."),
    ContextMetric("poi_density", "Places (POI) Count", "overture", "places",
                  "Overture places points in the hex."),
)
CONTEXT_METRIC_KEYS: tuple[str, ...] = tuple(m.key for m in CONTEXT_METRICS)


class LayerSkipped(RuntimeError):
    """A layer's prerequisite (usually a credential) is absent; not a failure."""


@dataclass
class BuildConfig:
    """Inputs shared by every layer builder."""

    cache_dir: Path = DEFAULT_CACHE_DIR
    as_of: datetime = field(default_factory=lambda: datetime.now(UTC))
    env: Mapping[str, str] = field(default_factory=lambda: dict(os.environ))


# --------------------------------------------------------------------------- #
# Layer builders — each returns {h3_index: {metric_key: value}}               #
# --------------------------------------------------------------------------- #
def build_lodes_layer(cfg: BuildConfig) -> HexValues:
    from src.spatial.lodes_bay_area_pipeline import (
        LodesBayAreaPipelineConfig,
        run_bay_area_lodes_pipeline,
    )

    result = run_bay_area_lodes_pipeline(
        LodesBayAreaPipelineConfig(cache_dir=cfg.cache_dir / "lodes")
    )
    if result.report.get("wac_status") != "ok" and result.report.get("rac_status") != "ok":
        raise RuntimeError(
            f"LODES WAC and RAC both unavailable: {result.report.get('wac_error')}"
        )
    return {
        record.h3_index: {
            "jobs_total": float(record.total_jobs),
            "jobs_to_residents": record.jobs_to_residents_ratio,
        }
        for record in result.records
    }


def build_transit_layer(cfg: BuildConfig) -> HexValues:
    from src.producers.bay_area_511_client import Bay511Client
    from src.spatial.transit_accessibility import score_feed

    api_key = (cfg.env.get(BAY_511_KEY_ENV) or "").strip()
    if not api_key:
        raise LayerSkipped(f"{BAY_511_KEY_ENV} is not set")
    feed = Bay511Client(api_key).fetch_all_operator_feeds()
    return {
        row["h3_index"]: {"transit_score": float(row["transit_connectivity_score"])}
        for row in score_feed(feed)
    }


def bay_area_permit_cities() -> list[Any]:
    """Registered cities with a PERMITS feed whose metro center is in the 9 counties."""
    from shapely.geometry import Point

    from src.spatial.bay_area_boundary import load_boundary_geometry
    from src.spatial.city_registry import REGISTRY, FeedType

    boundary = load_boundary_geometry()
    cities = []
    for city_id, registration in REGISTRY.items():
        if FeedType.PERMITS not in registration.datasets:
            continue
        bbox = registration.metro_bbox
        center = Point(
            (bbox["min_lng"] + bbox["max_lng"]) / 2, (bbox["min_lat"] + bbox["max_lat"]) / 2
        )
        if boundary.contains(center):
            cities.append(city_id)
    return sorted(cities, key=lambda c: c.value)


def fetch_recent_permits(city_id: Any, since: datetime) -> list[dict[str, Any]]:
    """Fetch one city's permits issued since ``since`` as PermitEvent dicts.

    Reuses the permits producer's row parser (field maps, taxonomy, geocoding)
    without opening a Kafka connection.
    """
    from src.producers.acquisition import AcquisitionSpec, build_adapter_request, build_where
    from src.spatial.city_registry import FeedType, get_dataset

    spec = get_dataset(city_id, FeedType.PERMITS)
    parser = _kafka_free_permit_parser()
    acquisition = AcquisitionSpec.from_dataset_spec(spec)
    # Text watermarks (San Jose's M/D/YYYY) compare in the source's own format.
    if acquisition.watermark_type == "text" and acquisition.watermark_format:
        since_value = since.strftime(acquisition.watermark_format)
    else:
        since_value = since.strftime("%Y-%m-%dT%H:%M:%S")
    where = build_where(
        base_where=acquisition.where,
        watermark_col=acquisition.watermark_col,
        high_watermark=since_value,
        endpoint=acquisition.endpoint,
        watermark_type=acquisition.watermark_type,
        watermark_format=acquisition.watermark_format,
        watermark_exclude=acquisition.watermark_exclude,
    )
    client = parser._client_for(spec.platform)
    events: list[dict[str, Any]] = []
    for batch in client.paginate(
        endpoint_url=spec.endpoint,
        **build_adapter_request(spec.platform, acquisition),
        where_clause=where,
        batch_size=1000,
        max_records=PERMIT_MAX_RECORDS,
    ):
        for row in batch:
            event = parser.parse_socrata_row(row, city_id=city_id.value)
            if event is not None and event.h3_res9:
                events.append(event.model_dump())
    return events


def _kafka_free_permit_parser() -> Any:
    """The permits producer's row parser and platform clients, minus Kafka."""
    from src.producers.dob_permits_producer import DOBPermitsProducer

    class _PermitRowParser(DOBPermitsProducer):
        def __init__(self) -> None:
            from src.producers.accela_client import AccelaClient
            from src.producers.arcgis_client import ArcGISClient
            from src.producers.carto_client import CartoClient
            from src.producers.ckan_client import CkanClient
            from src.producers.csv_client import CSVClient
            from src.producers.excel_client import ExcelClient
            from src.producers.socrata_client import SocrataClient
            from src.spatial.h3_indexer import H3SpatialIndexer

            self.socrata = SocrataClient()
            self.arcgis = ArcGISClient()
            self.accela = AccelaClient()
            self.carto = CartoClient()
            self.ckan = CkanClient()
            self.csv = CSVClient()
            self.excel = ExcelClient()
            self.spatial_indexer = H3SpatialIndexer()

    return _PermitRowParser()


def permit_hex_values(events: list[dict[str, Any]], as_of: datetime) -> HexValues:
    """Roll parsed permit events up to per-hex US-441 momentum metrics."""
    import pandas as pd

    from src.features.bay_area_permit_momentum import compute_bay_area_permit_hex_features

    if not events:
        return {}
    frame = pd.DataFrame(events)
    values: HexValues = {}
    for h3_index, rows in frame.groupby("h3_res9", sort=True):
        feats = compute_bay_area_permit_hex_features(rows, str(h3_index), as_of_date=as_of)
        if feats["permit_count_180d"] == 0:
            continue
        unit_delta = feats["residential_unit_delta"]
        values[str(h3_index)] = {
            "permit_velocity_60_180": float(feats["permit_velocity_60_180"]),
            "permit_capex_60d": float(feats["capex_density_decayed"]),
            "residential_unit_delta": float(unit_delta) if unit_delta is not None else None,
        }
    return values


def build_permits_layer(cfg: BuildConfig) -> HexValues:
    since = cfg.as_of - timedelta(days=PERMIT_LOOKBACK_DAYS)
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    cities = bay_area_permit_cities()
    for city_id in cities:
        try:
            city_events = fetch_recent_permits(city_id, since)
        except Exception as exc:  # noqa: BLE001 — one city's portal down must not drop the others
            errors.append(f"{city_id.value}: {exc}")
            logger.warning("Permit fetch failed for %s: %s", city_id.value, exc)
            continue
        logger.info("Permits: %s -> %d geocoded events", city_id.value, len(city_events))
        events.extend(city_events)
    if errors and len(errors) == len(cities):
        raise RuntimeError("; ".join(errors))
    return permit_hex_values(events, cfg.as_of)


def latest_per_zcta(
    table: Mapping[str, Mapping[date, float]], max_staleness_days: int = MARKET_MAX_STALENESS_DAYS
) -> tuple[dict[str, dict[date, float]], date | None]:
    """Collapse a per-ZCTA monthly table to one current value per ZCTA.

    Every ZCTA's newest print is relabelled to the table's newest period so the
    area-weighted join blends one as-of snapshot; prints older than
    ``max_staleness_days`` before that period are dropped instead of blended.
    """
    newest = max((period for periods in table.values() for period in periods), default=None)
    if newest is None:
        return {}, None
    cutoff = newest - timedelta(days=max_staleness_days)
    current: dict[str, dict[date, float]] = {}
    for zcta, periods in table.items():
        if not periods:
            continue
        latest = max(periods)
        if latest >= cutoff:
            current[zcta] = {newest: periods[latest]}
    return current, newest


def _observations_by_zcta(observations: list[Any], series_id: str) -> dict[str, dict[date, float]]:
    from src.spatial.bay_area_zips import is_bay_area_zip, normalize_zip

    table: dict[str, dict[date, float]] = {}
    for obs in observations:
        if obs.series_id != series_id:
            continue
        zcta = normalize_zip(obs.geography_id)
        if zcta and is_bay_area_zip(zcta):
            table.setdefault(zcta, {})[obs.period] = obs.value
    return table


def _fetch_zillow(series_key: str) -> dict[str, dict[date, float]]:
    from src.producers.series_client import SeriesClient
    from src.spatial.series_registry import SERIES_REGISTRY

    spec = SERIES_REGISTRY[series_key]
    return _observations_by_zcta(SeriesClient().fetch(spec), spec.series_id)


def market_hex_values(
    redfin_sale: Mapping[str, Mapping[date, float]],
    zillow_sale: Mapping[str, Mapping[date, float]],
    zillow_rent: Mapping[str, Mapping[date, float]],
    polygon_fn: Callable[[list[str]], Mapping[str, Any]],
) -> HexValues:
    """Reconcile Redfin/Zillow per ZCTA, then area-weight the current print onto hexes."""
    from src.features.market_reconciliation import build_hex_monthly_series, reconcile_series
    from src.spatial.zip_h3_join import build_weights

    sale, _ = latest_per_zcta(reconcile_series(redfin_sale, zillow_sale, "sale_price"))
    rent, _ = latest_per_zcta(reconcile_series({}, zillow_rent, "rent"))
    zctas = sorted(set(sale) | set(rent))
    if not zctas:
        return {}
    weights = build_weights(dict(polygon_fn(zctas)), resolution=CONTEXT_RESOLUTION)
    values: HexValues = {}
    for metric, table in (("median_sale_price", sale), ("rent_index", rent)):
        for h3_index, series in build_hex_monthly_series(weights, table, intensive=True).items():
            for value in series.values():
                values.setdefault(h3_index, {})[metric] = round(float(value), 2)
    return values


def build_market_layer(cfg: BuildConfig) -> HexValues:
    from src.producers.redfin_client import fetch_bay_area_zip_tracker
    from src.spatial.zcta_boundaries import ZctaBoundaryClient

    redfin_sale = _observations_by_zcta(
        fetch_bay_area_zip_tracker(), "redfin_median_sale_price_zip"
    )
    # Zillow is the fallback source for both families; a Zillow outage leaves
    # Redfin-only sale prices rather than failing the layer.
    zillow: dict[str, dict[str, dict[date, float]]] = {}
    for key in ("zhvi_zip", "zori_zip"):
        try:
            zillow[key] = _fetch_zillow(key)
        except Exception as exc:  # noqa: BLE001 — Zillow is a fallback source, not a requirement
            logger.warning("Zillow %s unavailable, continuing without it: %s", key, exc)
            zillow[key] = {}
    boundaries = ZctaBoundaryClient(cache_dir=cfg.cache_dir / "zcta")
    return market_hex_values(
        redfin_sale, zillow["zhvi_zip"], zillow["zori_zip"], boundaries.get_polygons
    )


def build_overture_layer(cfg: BuildConfig) -> HexValues:
    from src.spatial.overture_pipeline import run_overture_density_pipeline

    result = run_overture_density_pipeline()
    values: HexValues = {}
    for building in result.building_metrics:
        values.setdefault(building.h3_index, {})["building_count"] = float(building.building_count)
    for poi in result.poi_metrics:
        values.setdefault(poi.h3_index, {})["poi_density"] = float(poi.poi_density)
    return values


LAYER_BUILDERS: dict[str, Callable[[BuildConfig], HexValues]] = {
    "lodes": build_lodes_layer,
    "transit": build_transit_layer,
    "permits": build_permits_layer,
    "market": build_market_layer,
    "overture": build_overture_layer,
}


# --------------------------------------------------------------------------- #
# Merge + write                                                               #
# --------------------------------------------------------------------------- #
def merge_layers(layer_values: Mapping[str, HexValues]) -> pl.DataFrame:
    """One row per hex any layer touched; untouched metrics stay null."""
    merged: dict[str, dict[str, float | None]] = {}
    for values in layer_values.values():
        for h3_index, metrics in values.items():
            row = merged.setdefault(h3_index, {})
            for key, value in metrics.items():
                if key in CONTEXT_METRIC_KEYS:
                    row[key] = None if value is None else float(value)
    schema = {"h3_index": pl.Utf8, **{key: pl.Float64 for key in CONTEXT_METRIC_KEYS}}
    rows = [
        {"h3_index": h3_index, **{key: metrics.get(key) for key in CONTEXT_METRIC_KEYS}}
        for h3_index, metrics in sorted(merged.items())
    ]
    return pl.DataFrame(rows, schema=schema)


def build_context(
    out_dir: Path,
    cfg: BuildConfig | None = None,
    layers: list[str] | None = None,
    builders: Mapping[str, Callable[[BuildConfig], HexValues]] | None = None,
) -> dict[str, Any]:
    """Run the requested layers, write the table + meta, and return the meta.

    Raises ``RuntimeError`` (after writing nothing) only when no layer produced
    data, so a publish never swaps a good table for an empty one.
    """
    cfg = cfg or BuildConfig()
    builders = builders or LAYER_BUILDERS
    requested = layers or list(builders)
    catalog = _layer_catalog()

    layer_values: dict[str, HexValues] = {}
    layer_status: dict[str, dict[str, Any]] = {}
    for layer_id in requested:
        try:
            values = builders[layer_id](cfg)
        except LayerSkipped as exc:
            layer_status[layer_id] = {"status": "skipped", "reason": str(exc)}
            logger.info("Layer %s skipped: %s", layer_id, exc)
            continue
        except Exception as exc:
            layer_status[layer_id] = {"status": "failed", "reason": str(exc)[:500]}
            logger.exception("Layer %s failed", layer_id)
            continue
        if not values:
            layer_status[layer_id] = {"status": "failed", "reason": "no hexes produced"}
            continue
        layer_values[layer_id] = values
        layer_status[layer_id] = {"status": "ok", "hexes": len(values)}
        logger.info("Layer %s: %d hexes", layer_id, len(values))

    if not layer_values:
        raise RuntimeError(f"No Bay Area context layer produced data: {layer_status}")

    table = merge_layers(layer_values)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    table.write_parquet(out_dir / CONTEXT_TABLE)

    meta: dict[str, Any] = {
        "generated_at": cfg.as_of.isoformat(),
        "resolution": CONTEXT_RESOLUTION,
        "rows": table.height,
        "layers": {
            layer_id: {
                **layer_status[layer_id],
                "label": catalog[layer_id].label,
                "attribution": catalog[layer_id].attribution,
                "ticket": catalog[layer_id].ticket,
            }
            for layer_id in requested
        },
        "metrics": [
            {
                "key": metric.key,
                "label": metric.label,
                "layer": metric.layer,
                "unit": metric.unit,
                "description": metric.description,
            }
            for metric in CONTEXT_METRICS
            if metric.layer in layer_values
        ],
    }
    (out_dir / CONTEXT_META).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def load_context(context_dir: Path) -> tuple[dict[str, dict[str, float]], dict[str, Any]] | None:
    """Read a built context table as ``{h3_index: {metric: value}}`` + its meta.

    Null cells are omitted from the per-hex dict. Returns None when the
    directory carries no context table.
    """
    table_path = Path(context_dir) / CONTEXT_TABLE
    meta_path = Path(context_dir) / CONTEXT_META
    if not table_path.is_file() or not meta_path.is_file():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    frame = pl.read_parquet(table_path)
    metric_cols = [c for c in frame.columns if c in CONTEXT_METRIC_KEYS]
    values: dict[str, dict[str, float]] = {}
    for row in frame.iter_rows(named=True):
        metrics = {key: row[key] for key in metric_cols if row[key] is not None}
        if metrics:
            values[row["h3_index"]] = metrics
    return values, meta


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="Build the Bay Area per-hex context table")
    parser.add_argument("--out", default="build/context", help="Output directory")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR), help="Download cache root")
    parser.add_argument(
        "--layers", nargs="*", choices=list(LAYER_BUILDERS), default=list(LAYER_BUILDERS)
    )
    args = parser.parse_args()
    meta = build_context(
        Path(args.out), BuildConfig(cache_dir=Path(args.cache_dir)), layers=args.layers
    )
    print(json.dumps({k: v["status"] for k, v in meta["layers"].items()}))


if __name__ == "__main__":
    main()
