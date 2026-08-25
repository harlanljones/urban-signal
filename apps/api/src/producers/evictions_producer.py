"""NYC Marshal's Executed Evictions Producer (US-93).

Ingests NYC Marshals' executed evictions (`6z8x-wfk4`) as a NYC-only
context/validation signal. Per the survey's asymmetry rule this is NOT a LIMS
input — a single-metro feature must not drive cross-city decisions. The feed
carries lat/lon directly (verified 2026-08-24), so no geocoder dependency.
"""

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import settings
from src.producers.arcgis_client import ArcGISClient
from src.producers.base_producer import BaseKafkaProducer
from src.producers.carto_client import CartoClient
from src.producers.ckan_client import CkanClient
from src.producers.socrata_client import SocrataClient
from src.schemas.models import EvictionEvent
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)


def _parse_datetime(val: Any) -> datetime | None:
    """Parse ISO and common municipal date formats into a timezone-aware datetime."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=UTC)
    if isinstance(val, str):
        val_clean = val.replace("Z", "+00:00").strip()
        try:
            return datetime.fromisoformat(val_clean)
        except ValueError:
            pass
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y%m%d"):
            try:
                return datetime.strptime(val.strip(), fmt).replace(tzinfo=UTC)
            except ValueError:
                pass
    return None


class EvictionsProducer:
    """Ingests NYC Marshal's executed evictions and streams them to the evictions topic."""

    def __init__(self, bootstrap_servers: str | None = None):
        schema_path = Path(__file__).parent.parent / "schemas" / "avro" / "eviction_event.avsc"
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

    def parse_socrata_row(self, row: dict[str, Any], city_id: str | None = None) -> EvictionEvent | None:
        """Convert a raw executed-eviction row to a strongly-typed EvictionEvent."""
        try:
            from src.spatial.city_registry import (
                FeedType,
                normalize_city,
            )
            if city_id is not None:
                norm_c = normalize_city(city_id)
                resolved_city = norm_c.value if norm_c else city_id.lower()
            else:
                resolved_city = "nyc"

            from src.producers.field_maps import first_mapped, resolve_field_map

            field_map = resolve_field_map(resolved_city, FeedType.EVICTIONS)

            eviction_id = str(
                first_mapped(row, field_map, "eviction_id")
                or row.get("court_index_number")
                or row.get("docket_number")
                or ""
            ).strip()
            if not eviction_id:
                return None

            lat_raw = (
                first_mapped(row, field_map, "latitude")
                or row.get("latitude")
                or row.get("lat")
            )
            lng_raw = (
                first_mapped(row, field_map, "longitude")
                or row.get("longitude")
                or row.get("lng")
            )
            if not lat_raw or not lng_raw:
                return None

            lat = float(lat_raw)
            lng = float(lng_raw)
            if lat == 0.0 and lng == 0.0:
                return None

            h3_res = self.spatial_indexer.get_multi_res_hierarchy(lat, lng)

            address = (
                row.get("eviction_address")
                or row.get("address")
            )
            if row.get("eviction_apt_num"):
                address = f"{address} #{row['eviction_apt_num']}".strip()

            executed_str = (
                first_mapped(row, field_map, "executed_date")
                or row.get("executed_date")
            )

            borough_val = (
                first_mapped(row, field_map, "borough")
                or row.get("borough")
            )
            from src.spatial.geo_utils import get_division_for_coordinate
            resolved_borough = get_division_for_coordinate(lat, lng, city_id=resolved_city) or (
                str(borough_val) if borough_val is not None else None
            )

            return EvictionEvent(
                city_id=resolved_city,
                eviction_id=eviction_id,
                address=address,
                borough=resolved_borough,
                zipcode=(
                    first_mapped(row, field_map, "zipcode")
                    or row.get("eviction_zip")
                    or row.get("zipcode")
                ),
                residential_commercial=(
                    first_mapped(row, field_map, "residential_commercial")
                    or row.get("residential_commercial_ind")
                ),
                executed_date=_parse_datetime(executed_str),
                latitude=lat,
                longitude=lng,
                h3_res7=h3_res["h3_res7"],
                h3_res8=h3_res["h3_res8"],
                h3_res9=h3_res["h3_res9"],
                ingested_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.warning("Error parsing eviction row: %s", e)
            return None

    def run_stream(self, city_id: str = "nyc", limit: int = 5000, where_clause: str | None = None):
        """Fetch executed evictions and stream them into the evictions topic."""
        from src.spatial.city_registry import (
            CityId,
            FeedType,
            get_dataset,
            normalize_city,
        )
        cid = normalize_city(city_id) or CityId.NYC
        spec = get_dataset(cid, FeedType.EVICTIONS)
        endpoint = spec.endpoint
        client = self._client_for(spec.platform)
        client_kwargs = {
            k: v for k, v in spec.extra.items() if k in ("order_by", "id_col", "select") and v
        }

        logger.info("Starting %s Evictions Stream (limit=%d)...", cid.value.upper(), limit)
        records_streamed = 0

        for batch in client.paginate(
            endpoint_url=endpoint,
            **client_kwargs,
            where_clause=where_clause,
            batch_size=1000,
            max_records=limit,
        ):
            for row in batch:
                event = self.parse_socrata_row(row, city_id=cid.value)
                if event:
                    key = f"{event.city_id}:{event.eviction_id}"
                    self.producer.produce(
                        topic=settings.topic_evictions,
                        key=key,
                        payload=event,
                    )
                    records_streamed += 1

        self.producer.flush()
        logger.info("%s Evictions Ingestion completed. Total streamed: %d records.", cid.value.upper(), records_streamed)
        return records_streamed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NYC Executed Evictions Kafka Producer")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    producer = EvictionsProducer()
    producer.run_stream(city_id="nyc", limit=args.limit)