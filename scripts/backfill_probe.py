"""G5/G6 backfill probe: live parse-rate and source-count parity per feed.

The probe is deliberately a leaf in the same spirit as
``scripts/feed_staleness_probe.py``: it reads the canonical registry, uses the
same paginating clients and row parsers as ingestion, and reports a durable
JSON result.  It never writes to Kafka or the application database.

What it measures
----------------
* **G5 parse rate** — of the newest ``--max-records`` rows (default 500) per
  registered feed, the share that the real ingestion parser turns into a typed
  event.  Rows the parser drops are bucketed by the two known gating causes
  (no id, no geometry) so the "drop rate <= published geocode gap" part of the
  gate has signal even before a staging database exists.
* **G6 source-count** — the source's own record count, so a later DB-backed
  backfill-parity run can compare against it.  Returns ``null`` when a platform
  has no cheap count probe.

Use ``--city`` to scope to one or more cities and ``--count`` to also fetch the
source counts.  Existing year-slice endpoints are resolved for today just like
the scheduler does at poll time.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import httpx
from src.features.shift_dynamics import ComplaintShiftDynamics
from src.producers.arcgis_client import ArcGISClient
from src.producers.carto_client import CartoClient
from src.producers.ckan_client import CkanClient
from src.producers.complaints_311_producer import Complaints311Producer
from src.producers.deeds_acris_producer import DeedsACRISProducer
from src.producers.dob_permits_producer import DOBPermitsProducer
from src.producers.field_maps import first_mapped
from src.producers.sla_licenses_producer import SLALicensesProducer
from src.producers.socrata_client import SocrataClient
from src.spatial.city_registry import REGISTRY, DatasetSpec, FeedType, resolve_endpoint
from src.spatial.h3_indexer import H3SpatialIndexer

PRODUCERS: dict[str, type[Any]] = {
    "permits": DOBPermitsProducer,
    "311": Complaints311Producer,
    "sla": SLALicensesProducer,
    "deeds": DeedsACRISProducer,
}

CLIENTS: dict[str, type[Any]] = {
    "socrata": SocrataClient,
    "arcgis": ArcGISClient,
    "carto": CartoClient,
    "ckan": CkanClient,
}


@dataclass
class FeedProbeResult:
    """One feed's G5/G6 probe result (JSON-serializable)."""

    city_id: str
    feed: str
    platform: str
    endpoint: str
    producer_key: str
    order_by: str
    sampled: int
    parsed: int
    dropped: int
    parse_rate: float | None
    drop_reasons: dict[str, int] = field(default_factory=dict)
    source_count: int | None = None
    watermark_seen: Any = None
    error: str | None = None


def client_for(spec: DatasetSpec) -> Any:
    """Construct the platform client used by the ingestion path."""
    try:
        return CLIENTS[spec.platform]()
    except KeyError as exc:
        raise ValueError(f"Unsupported feed platform {spec.platform!r}") from exc


def producer_for(producer_key: str) -> Any:
    """Build the ingestion producer for a feed type without opening Kafka.

    ``parse_socrata_row`` only touches ``self.spatial_indexer`` (and the 311
    producer's ``self.shift_dynamics``), so we skip ``__init__`` and inject just
    those dependencies.  The probe stays a read-only leaf and never opens a
    broker connection (a real ``__init__`` would spawn librdkafka threads and
    log "Connection refused" noise).
    """
    cls = PRODUCERS.get(producer_key)
    if cls is None:
        raise ValueError(f"No producer registered for key {producer_key!r}")
    producer = cls.__new__(cls)
    producer.spatial_indexer = H3SpatialIndexer()
    if producer_key == "311":
        producer.shift_dynamics = ComplaintShiftDynamics()
    return producer


def _drop_reason(row: dict[str, Any], field_map: dict[str, list[str]]) -> str:
    """Best-effort classification for a row the parser dropped.

    Mirrors the producers' generic fallback chains: a bare ``id`` counts as a
    job key and a bare ``latitude``/``longitude`` counts as geometry, so the
    diagnostic labels match the gates the ingestion path actually enforces.
    """
    id_candidates = ("job_id", "license_id", "incident_id", "doc_id")
    has_id = bool(row.get("id")) or any(
        first_mapped(row, field_map, name) is not None for name in id_candidates
    )
    lat = first_mapped(row, field_map, "latitude") or row.get("latitude") or row.get("lat")
    lng = first_mapped(row, field_map, "longitude") or row.get("longitude") or row.get("lng")
    if not has_id:
        return "missing_id"
    if not lat or not lng:
        return "missing_geometry"
    return "other"


def source_count(spec: DatasetSpec) -> int | None:
    """Best-effort source record count (G6 numerator).  None when unavailable."""
    try:
        if spec.platform == "arcgis":
            client = client_for(spec)
            payload = client._request_json(
                f"{spec.endpoint.rstrip('/')}/query",
                {"where": "1=1", "returnCountOnly": "true", "f": "json"},
            )
            value = payload.get("count")
            return int(value) if value is not None else None
        if spec.platform == "socrata":
            parts = spec.endpoint.rstrip("/").split("/resource/")
            base = parts[0]
            dataset_id = parts[1].split("?")[0].removesuffix(".json")
            url = f"{base}/resource/{dataset_id}.json"
            payload = httpx.get(url, params={"$select": "COUNT(*)"}, timeout=20.0).json()
            value = payload[0].get("COUNT") or payload[0].get("count")
            return int(value) if value is not None else None
        if spec.platform == "carto":
            payload = httpx.post(
                "https://phl.carto.com/api/v2/sql",
                data={"q": f"SELECT COUNT(*) AS n FROM ({spec.endpoint.split('/tables/')[-1]})"},
                timeout=20.0,
            ).json()
            return int(payload["rows"][0]["n"])
    except Exception:  # noqa: BLE001  # a missing/expensive count probe must not fail the feed
        return None
    return None


def probe_feed(
    city_id: str,
    feed: FeedType,
    spec: DatasetSpec,
    *,
    max_records: int,
    want_count: bool,
) -> FeedProbeResult:
    """Probe one registered feed: parse the newest rows and (optionally) count."""
    endpoint = spec.endpoint
    order_col = spec.watermark_col
    order_by = f"{order_col} DESC" if order_col else ""
    field_map = spec.field_map if isinstance(spec.field_map, dict) else {}

    client = client_for(spec)
    producer = producer_for(spec.producer_key or feed.value)

    sampled = parsed = 0
    drop_reasons: Counter[str] = Counter()
    watermark_seen = None
    rows: list[dict[str, Any]] = []

    try:
        fetch_kwargs: dict[str, Any] = {"batch_size": max_records, "max_records": max_records}
        if order_col:
            fetch_kwargs["order_by"] = order_by
        # Snapshot feeds carry no watermark column; sample the table head
        # under each client's default stable ordering instead.
        for page in client.paginate(endpoint_url=endpoint, **fetch_kwargs):
            rows.extend(page)
    except Exception as exc:  # noqa: BLE001
        return FeedProbeResult(
            city_id=city_id,
            feed=feed.value,
            platform=spec.platform,
            endpoint=endpoint,
            producer_key=spec.producer_key or feed.value,
            order_by=order_by,
            sampled=0,
            parsed=0,
            dropped=0,
            parse_rate=None,
            source_count=source_count(spec) if want_count else None,
            error=f"fetch: {exc}",
        )

    for row in rows:
        sampled += 1
        try:
            event = producer.parse_socrata_row(row, city_id=city_id)
        except Exception:  # noqa: BLE001  # one bad row must not kill the sample
            event = None
        if event is not None:
            parsed += 1
        else:
            drop_reasons[_drop_reason(row, field_map)] += 1
        if order_col and not watermark_seen and row.get(order_col):
            watermark_seen = row.get(order_col)

    parse_rate = (parsed / sampled) if sampled else None
    return FeedProbeResult(
        city_id=city_id,
        feed=feed.value,
        platform=spec.platform,
        endpoint=endpoint,
        producer_key=spec.producer_key or feed.value,
        order_by=order_by,
        sampled=sampled,
        parsed=parsed,
        dropped=sampled - parsed,
        parse_rate=round(parse_rate, 4) if parse_rate is not None else None,
        drop_reasons=dict(drop_reasons),
        source_count=source_count(spec) if want_count else None,
        watermark_seen=watermark_seen,
    )


def probe_registry(
    *,
    city_ids: set[str] | None = None,
    max_records: int = 500,
    want_count: bool = False,
    today: datetime | None = None,
) -> list[FeedProbeResult]:
    """Probe every registered feed (optionally scoped to cities) for G5/G6."""
    now = today or datetime.now(UTC)
    results: list[FeedProbeResult] = []
    for city, registration in REGISTRY.items():
        if city_ids is not None and city.value not in city_ids:
            continue
        for feed, registered_spec in registration.datasets.items():
            spec = DatasetSpec(**asdict(registered_spec))
            spec.endpoint = resolve_endpoint(spec, today=now.date())
            try:
                result = probe_feed(
                    city.value,
                    feed,
                    spec,
                    max_records=max_records,
                    want_count=want_count,
                )
            except Exception as exc:  # noqa: BLE001  # defensive boundary
                result = FeedProbeResult(
                    city_id=city.value,
                    feed=feed.value,
                    platform=spec.platform,
                    endpoint=spec.endpoint,
                    producer_key=spec.producer_key or feed.value,
                    order_by="",
                    sampled=0,
                    parsed=0,
                    dropped=0,
                    parse_rate=None,
                    error=str(exc),
                )
            results.append(result)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", action="append", dest="cities", help="Limit to a city id (repeatable)")
    parser.add_argument("--max-records", type=int, default=500, help="Newest rows to sample per feed")
    parser.add_argument("--count", action="store_true", help="Also fetch the source record count (G6)")
    args = parser.parse_args()

    results = probe_registry(
        city_ids=set(args.cities) if args.cities else None,
        max_records=args.max_records,
        want_count=args.count,
    )
    print(json.dumps([asdict(result) for result in results], default=str, indent=2))
    failed = [r for r in results if r.error or (r.sampled and r.parse_rate is not None and r.parse_rate < 0.95)]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
