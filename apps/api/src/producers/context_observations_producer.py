"""Context-observation producer: energy benchmarking + bike/ped counters.

US-363 §2.7 and §2.8. Both families are "zero new machinery" in the sweep's
sense — they ride the existing ``SocrataClient`` and a ``DatasetSpec`` — but
neither maps onto an existing event, so they share one typed shape,
``ContextObservationEvent`` (see the decision note in
``.streams/us363-new-sources-wave.md``).

Two parse paths, one transport:

**Energy benchmarking** (``FeedType.ENERGY_BENCHMARK``, annual). One source
row is one building-year. The producer walks the city's metric catalog and
emits one observation per metric that resolves to a real number. Absence is
prose in these feeds (``"Not Available"``, ``"NA"``), so a missing metric is
dropped, never coerced to 0.0 — a mean over coerced zeros would drag every
hex toward the floor. Compliance is emitted as a 0/1 ``compliance`` metric so
the "% non-compliant" feature is a plain mean.

**Counters** (``FeedType.BIKE_PED``, daily). NYC publishes 21M 15-minute
directional rows and Seattle 121k hourly wide rows; a feature described as
"flow intensity per hex" must not become 21M Kafka events. Rows are folded
into one observation per (sensor, travel mode, day) *before* production.
NYC rows carry no geometry — the sensor registry ``6up2-gnw8`` (declared as
``companion_endpoints["sensor_registry"]``) supplies lat/lon, and a row whose
sensor is absent from the registry goes to the DLQ rather than to a guessed
coordinate. Seattle's feed is a single fixed structure whose coordinate is a
module constant.
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from src.config import settings
from src.producers.arcgis_client import ArcGISClient
from src.producers.base_producer import BaseKafkaProducer
from src.producers.carto_client import CartoClient
from src.producers.ckan_client import CkanClient
from src.producers.field_maps import first_mapped
from src.producers.field_maps_counters import (
    NYC_COUNTER_REGISTRY_FIELD_MAP,
    SEATTLE_FREMONT_DIRECTION_COLUMNS,
    SEATTLE_FREMONT_SENSOR,
    counter_metric_name,
    normalize_travel_mode,
)
from src.producers.field_maps_energy_benchmark import (
    is_non_compliant,
    metrics_for,
    to_float,
)
from src.producers.socrata_client import SocrataClient
from src.schemas.models import ContextObservationEvent
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)

SOURCE_ENERGY = "energy_benchmark"
SOURCE_COUNTERS = "bike_ped"

# ENERGY STAR scores below this are the "underperforming stock" share the
# sweep asks for (§2.7: "% score<50"). 50 is the national median by
# construction, so the share is "worse than a median building".
LOW_ENERGY_STAR_SCORE = 50.0


def _parse_datetime(val: Any) -> datetime | None:
    """Parse ISO and common municipal date formats into an aware datetime."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=UTC)
    text = str(val).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        # Socrata floating timestamps are naive local wall clock. Stamping
        # them UTC (the repo's convention for every other municipal feed)
        # keeps day bucketing deterministic; letting them stay naive would
        # make `astimezone` reinterpret them in the host's timezone and
        # silently move counts across the day boundary.
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _year_bounds(year_value: Any) -> tuple[datetime, datetime] | None:
    """Turn a report-year cell into (Jan 1, Dec 31 23:59:59) UTC bounds."""
    try:
        year = int(str(year_value).strip()[:4])
    except (TypeError, ValueError):
        return None
    if not (1900 <= year <= 2100):
        return None
    return (
        datetime(year, 1, 1, tzinfo=UTC),
        datetime(year, 12, 31, 23, 59, 59, tzinfo=UTC),
    )


def _day_bounds(ts: datetime) -> tuple[datetime, datetime]:
    start = ts.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start.replace(hour=23, minute=59, second=59)


class ContextObservationsProducer:
    """Streams building-energy and counter observations to the context topic."""

    def __init__(self, bootstrap_servers: str | None = None):
        schema_path = (
            Path(__file__).parent.parent / "schemas" / "avro" / "context_observation_event.avsc"
        )
        self.producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=schema_path,
            dlq_topic=settings.topic_dlq,
        )
        self.socrata = SocrataClient()
        self.arcgis = ArcGISClient()
        self.carto = CartoClient()
        self.ckan = CkanClient()
        self.spatial_indexer = H3SpatialIndexer()
        # sensor_registry cache keyed by (city_id, sensor_id)
        self._sensor_cache: dict[str, dict[str, dict[str, Any]]] = {}

    # ----------------------------------------------------------------- #
    # client plumbing                                                     #
    # ----------------------------------------------------------------- #
    def _client_for(self, platform: str):
        clients = {
            "socrata": getattr(self, "socrata", None),
            "arcgis": getattr(self, "arcgis", None),
            "carto": getattr(self, "carto", None),
            "ckan": getattr(self, "ckan", None),
        }
        client = clients.get(platform)
        if client is None:
            available = ", ".join(sorted(k for k, v in clients.items() if v is not None))
            raise ValueError(
                f"platform {platform!r} has no client on this producer "
                f"(available: {available}); wire it before registering the spec"
            )
        return client

    def _h3(self, lat: float | None, lng: float | None) -> dict[str, str | None]:
        if lat is None or lng is None:
            return {"h3_res7": None, "h3_res8": None, "h3_res9": None}
        return self.spatial_indexer.get_multi_res_hierarchy(lat, lng)

    # ----------------------------------------------------------------- #
    # §2.7 energy benchmarking                                            #
    # ----------------------------------------------------------------- #
    def parse_energy_row(
        self,
        row: dict[str, Any],
        city_id: str,
        field_map: dict[str, list[str]] | None = None,
    ) -> list[ContextObservationEvent]:
        """Fan one building-year row out into its per-metric observations."""
        from src.spatial.city_registry import FeedType, normalize_city
        from src.producers.field_maps import resolve_field_map

        norm = normalize_city(city_id)
        resolved_city = norm.value if norm else str(city_id).lower()
        fmap = field_map if field_map is not None else resolve_field_map(
            resolved_city, FeedType.ENERGY_BENCHMARK
        )

        asset_id = str(first_mapped(row, fmap, "asset_id") or "").strip()
        if not asset_id:
            return []

        bounds = _year_bounds(first_mapped(row, fmap, "period"))
        if bounds is None:
            return []
        period_start, period_end = bounds

        lat = to_float(first_mapped(row, fmap, "latitude"))
        lng = to_float(first_mapped(row, fmap, "longitude"))
        if lat is not None and lng is not None and lat == 0.0 and lng == 0.0:
            lat = lng = None
        h3 = self._h3(lat, lng)

        borough_raw = first_mapped(row, fmap, "borough")
        borough = str(borough_raw) if borough_raw is not None else None
        if lat is not None and lng is not None:
            from src.spatial.geo_utils import get_division_for_coordinate

            borough = get_division_for_coordinate(lat, lng, city_id=resolved_city) or borough

        category_raw = first_mapped(row, fmap, "category")
        neighborhood_raw = first_mapped(row, fmap, "source_neighborhood")
        address_raw = first_mapped(row, fmap, "address")
        zip_raw = first_mapped(row, fmap, "zipcode")

        common = {
            "city_id": resolved_city,
            "source": SOURCE_ENERGY,
            "asset_id": asset_id,
            "asset_name": (
                str(first_mapped(row, fmap, "asset_name"))
                if first_mapped(row, fmap, "asset_name") is not None
                else None
            ),
            "period_start": period_start,
            "period_end": period_end,
            "period_type": "year",
            "category": str(category_raw) if category_raw is not None else None,
            "address": str(address_raw) if address_raw is not None else None,
            "borough": borough,
            "source_neighborhood": str(neighborhood_raw) if neighborhood_raw is not None else None,
            "zipcode": str(zip_raw) if zip_raw is not None else None,
            "latitude": lat,
            "longitude": lng,
            **h3,
        }

        period_label = str(period_start.year)
        events: list[ContextObservationEvent] = []
        for metric, spec in metrics_for(resolved_city).items():
            value = None
            for column in spec.get("columns", []):
                value = to_float(row.get(column))
                if value is not None:
                    break
            if value is None:
                continue
            events.append(
                ContextObservationEvent(
                    observation_id=f"{SOURCE_ENERGY}:{asset_id}:{period_label}:{metric}",
                    metric=metric,
                    value=value,
                    unit=spec.get("unit"),
                    **common,
                )
            )

        # Compliance as a 0/1 metric so "% non-compliant" is a plain mean.
        non_compliant = is_non_compliant(first_mapped(row, fmap, "compliance"))
        if non_compliant is not None:
            events.append(
                ContextObservationEvent(
                    observation_id=f"{SOURCE_ENERGY}:{asset_id}:{period_label}:non_compliant",
                    metric="non_compliant",
                    value=1.0 if non_compliant else 0.0,
                    unit="indicator",
                    **common,
                )
            )
        return events

    # ----------------------------------------------------------------- #
    # §2.8 counters                                                       #
    # ----------------------------------------------------------------- #
    def load_sensor_registry(self, city_id: str, spec: Any) -> dict[str, dict[str, Any]]:
        """Fetch and cache the counter registry that supplies NYC geometry.

        A counts row whose ``sensor_id`` is absent here has no defensible
        coordinate; the caller sends it to the DLQ rather than inventing one.
        """
        cached = self._sensor_cache.get(city_id)
        if cached is not None:
            return cached

        registry_url = (spec.companion_endpoints or {}).get("sensor_registry")
        sensors: dict[str, dict[str, Any]] = {}
        if not registry_url:
            self._sensor_cache[city_id] = sensors
            return sensors

        client = self._client_for(spec.platform)
        for batch in client.paginate(endpoint_url=registry_url, batch_size=1000):
            for srow in batch:
                sid = str(first_mapped(srow, NYC_COUNTER_REGISTRY_FIELD_MAP, "asset_id") or "").strip()
                if not sid:
                    continue
                lat = to_float(first_mapped(srow, NYC_COUNTER_REGISTRY_FIELD_MAP, "latitude"))
                lng = to_float(first_mapped(srow, NYC_COUNTER_REGISTRY_FIELD_MAP, "longitude"))
                name = first_mapped(srow, NYC_COUNTER_REGISTRY_FIELD_MAP, "asset_name")
                sensors[sid] = {
                    "latitude": lat,
                    "longitude": lng,
                    "asset_name": str(name) if name is not None else None,
                }
        self._sensor_cache[city_id] = sensors
        logger.info("Loaded %d counter sensors for %s", len(sensors), city_id)
        return sensors

    def aggregate_count_rows(
        self,
        rows: Iterable[dict[str, Any]],
        city_id: str,
    ) -> dict[tuple[str, str, datetime], float]:
        """Fold narrow NYC count rows into (sensor, mode, day) daily totals.

        Both directions are summed: the sweep's feature is flow intensity
        through the hex, not net directional imbalance.
        """
        totals: dict[tuple[str, str, datetime], float] = defaultdict(float)
        for row in rows:
            sensor_id = str(row.get("sensor_id") or "").strip()
            if not sensor_id:
                continue
            ts = _parse_datetime(row.get("timestamp"))
            if ts is None:
                continue
            count = to_float(row.get("counts"))
            if count is None:
                continue
            mode = normalize_travel_mode(row.get("travelmode"))
            day, _ = _day_bounds(ts)
            totals[(sensor_id, mode, day)] += count
        return dict(totals)

    def aggregate_fremont_rows(
        self,
        rows: Iterable[dict[str, Any]],
    ) -> dict[tuple[str, str, datetime], float]:
        """Fold Seattle's wide hourly rows into (sensor, mode, day) totals.

        Only the directional columns are summed; ``fremont_bridge`` is the
        undirected total and adding it would double-count the day.
        """
        totals: dict[tuple[str, str, datetime], float] = defaultdict(float)
        sensor_id = SEATTLE_FREMONT_SENSOR["asset_id"]
        mode = SEATTLE_FREMONT_SENSOR["travel_mode"]
        for row in rows:
            ts = _parse_datetime(row.get("date"))
            if ts is None:
                continue
            day, _ = _day_bounds(ts)
            for column in SEATTLE_FREMONT_DIRECTION_COLUMNS:
                value = to_float(row.get(column))
                if value is None:
                    continue
                totals[(sensor_id, mode, day)] += value
        return dict(totals)

    def build_counter_events(
        self,
        totals: dict[tuple[str, str, datetime], float],
        city_id: str,
        sensors: dict[str, dict[str, Any]],
    ) -> tuple[list[ContextObservationEvent], list[tuple[str, str]]]:
        """Turn daily totals into events; return (events, unlocatable keys)."""
        from src.spatial.city_registry import normalize_city

        norm = normalize_city(city_id)
        resolved_city = norm.value if norm else str(city_id).lower()

        events: list[ContextObservationEvent] = []
        unlocatable: list[tuple[str, str]] = []
        for (sensor_id, mode, day), value in sorted(totals.items(), key=lambda kv: (kv[0][2], kv[0][0], kv[0][1])):
            sensor = sensors.get(sensor_id)
            if not sensor or sensor.get("latitude") is None or sensor.get("longitude") is None:
                unlocatable.append((sensor_id, day.date().isoformat()))
                continue
            lat = float(sensor["latitude"])
            lng = float(sensor["longitude"])
            borough = None
            from src.spatial.geo_utils import get_division_for_coordinate

            borough = get_division_for_coordinate(lat, lng, city_id=resolved_city)
            _, day_end = _day_bounds(day)
            events.append(
                ContextObservationEvent(
                    city_id=resolved_city,
                    observation_id=(
                        f"{SOURCE_COUNTERS}:{sensor_id}:{day.date().isoformat()}:"
                        f"{counter_metric_name(mode)}"
                    ),
                    source=SOURCE_COUNTERS,
                    asset_id=sensor_id,
                    asset_name=sensor.get("asset_name"),
                    metric=counter_metric_name(mode),
                    value=float(value),
                    unit="counts_per_day",
                    period_start=day,
                    period_end=day_end,
                    period_type="day",
                    category=normalize_travel_mode(mode),
                    borough=borough,
                    latitude=lat,
                    longitude=lng,
                    **self._h3(lat, lng),
                )
            )
        return events, unlocatable

    # ----------------------------------------------------------------- #
    # streaming entrypoints                                               #
    # ----------------------------------------------------------------- #
    def _emit(self, events: list[ContextObservationEvent]) -> int:
        for event in events:
            self.producer.produce(
                topic=settings.topic_context_observations,
                key=f"{event.city_id}:{event.observation_id}",
                payload=event,
            )
        return len(events)

    def run_stream(
        self,
        city_id: str = "nyc",
        limit: int = 5000,
        where_clause: str | None = None,
        feed: Any = None,
    ) -> int:
        """Dispatch to the energy or counter path for one city."""
        from src.spatial.city_registry import CityId, FeedType, get_dataset, normalize_city

        cid = normalize_city(city_id) or CityId.NYC
        feed_type = feed or FeedType.ENERGY_BENCHMARK
        spec = get_dataset(cid, feed_type)

        if feed_type == FeedType.BIKE_PED:
            return self._run_counters(cid, spec, limit=limit, where_clause=where_clause)
        return self._run_energy(cid, spec, limit=limit, where_clause=where_clause)

    def _run_energy(self, cid: Any, spec: Any, limit: int, where_clause: str | None) -> int:
        from src.producers.acquisition import AcquisitionSpec, build_adapter_request

        client = self._client_for(spec.platform)
        client_kwargs = build_adapter_request(spec.platform, AcquisitionSpec.from_dataset_spec(spec))
        logger.info("Starting %s energy-benchmark stream (limit=%d)", cid.value.upper(), limit)

        streamed = 0
        for batch in client.paginate(
            endpoint_url=spec.endpoint,
            **client_kwargs,
            where_clause=where_clause,
            batch_size=1000,
            max_records=limit,
        ):
            for row in batch:
                streamed += self._emit(
                    self.parse_energy_row(row, city_id=cid.value, field_map=spec.field_map)
                )
        self.producer.flush()
        logger.info("%s energy-benchmark stream complete: %d observations", cid.value.upper(), streamed)
        return streamed

    def _run_counters(self, cid: Any, spec: Any, limit: int, where_clause: str | None) -> int:
        from src.producers.acquisition import AcquisitionSpec, build_adapter_request

        client = self._client_for(spec.platform)
        client_kwargs = build_adapter_request(spec.platform, AcquisitionSpec.from_dataset_spec(spec))

        wide = bool((spec.companion_endpoints or {}).get("wide_layout"))
        if wide:
            sensors = {SEATTLE_FREMONT_SENSOR["asset_id"]: dict(SEATTLE_FREMONT_SENSOR)}
        else:
            sensors = self.load_sensor_registry(cid.value, spec)

        logger.info("Starting %s counter stream (limit=%d, wide=%s)", cid.value.upper(), limit, wide)
        rows: list[dict[str, Any]] = []
        for batch in client.paginate(
            endpoint_url=spec.endpoint,
            **client_kwargs,
            where_clause=where_clause,
            batch_size=1000,
            max_records=limit,
        ):
            rows.extend(batch)

        totals = self.aggregate_fremont_rows(rows) if wide else self.aggregate_count_rows(rows, cid.value)
        events, unlocatable = self.build_counter_events(totals, cid.value, sensors)
        streamed = self._emit(events)

        for sensor_id, day in unlocatable:
            self.producer.route_to_dlq(
                failed_topic=settings.topic_context_observations,
                key=f"{cid.value}:{SOURCE_COUNTERS}:{sensor_id}:{day}",
                payload={"sensor_id": sensor_id, "day": day},
                error_msg="counter sensor absent from the sensor registry — no defensible coordinate",
            )
        self.producer.flush()
        logger.info(
            "%s counter stream complete: %d daily observations from %d rows (%d unlocatable)",
            cid.value.upper(),
            streamed,
            len(rows),
            len(unlocatable),
        )
        return streamed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Context observation Kafka producer")
    parser.add_argument("--city", default="nyc")
    parser.add_argument("--feed", default="energy_benchmark", choices=["energy_benchmark", "bike_ped"])
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    from src.spatial.city_registry import FeedType

    ContextObservationsProducer().run_stream(
        city_id=args.city,
        limit=args.limit,
        feed=FeedType.ENERGY_BENCHMARK if args.feed == "energy_benchmark" else FeedType.BIKE_PED,
    )
