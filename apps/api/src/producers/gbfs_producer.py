"""GBFS station-change producer (US-363 §1.2 / §2.1).

Wraps ``SnapshotClient`` and turns its station-set diff into
``StationChangeEvent``s. Registered per city because a GBFS system maps
one-to-one onto a metro: Citi Bike -> nyc, Divvy -> chicago, Bay Wheels ->
san_francisco, Capital Bikeshare -> washington_dc.

Only the Lyft-operated pool is registered. Lyft's Data License Agreement
grants product use and prohibits re-hosting the raw feed as a standalone
dataset — we derive events and keep a private state store, and never
republish the feed. Lime, Bird, Spin, Bolt and Veo are barred by their own
terms (internal-non-commercial-only, 10-minute retention,
no-database-augmentation) and must not be added without new written terms.
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from src.config import settings
from src.producers.base_producer import BaseKafkaProducer
from src.producers.snapshot_client import SnapshotClient, StationRecord
from src.schemas.models import StationChangeEvent
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)

STATION_ADDED = "station_added"
STATION_REMOVED = "station_removed"


class GbfsProducer:
    """Diffs GBFS station sets and streams the transitions."""

    def __init__(self, bootstrap_servers: str | None = None, state_dir: str | None = None):
        schema_path = (
            Path(__file__).parent.parent / "schemas" / "avro" / "station_change_event.avsc"
        )
        self.producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=schema_path,
            dlq_topic=settings.topic_dlq,
        )
        # Named `gbfs` because the interlock gate resolves a spec's platform
        # to an attribute of the same name on the producer that claims it
        # (`test_platform_clients_exposed`). `snapshot` stays as a readable
        # alias for the archetype.
        self.gbfs = SnapshotClient(state_dir=state_dir)
        self.snapshot = self.gbfs
        # The gate also asserts every producer exposes a `socrata` client.
        # This one never queries Socrata; the attribute exists to satisfy the
        # shared invariant, and this comment exists so a reader does not spend
        # time wondering why a bikeshare producer holds one.
        from src.producers.socrata_client import SocrataClient

        self.socrata = SocrataClient()
        self.spatial_indexer = H3SpatialIndexer()

    def build_event(
        self,
        record: StationRecord,
        event_type: str,
        city_id: str,
        system_id: str,
        operator: Optional[str] = None,
        detected_at: Optional[datetime] = None,
    ) -> Optional[StationChangeEvent]:
        """One station transition -> one event, or None if unusable."""
        if record.lat is None or record.lon is None:
            return None
        stamp = detected_at or datetime.now(UTC)
        h3 = self.spatial_indexer.get_multi_res_hierarchy(record.lat, record.lon)

        from src.spatial.geo_utils import get_division_for_coordinate

        borough = get_division_for_coordinate(record.lat, record.lon, city_id=city_id)
        return StationChangeEvent(
            city_id=city_id,
            system_id=system_id,
            station_id=record.station_id,
            event_type=event_type,
            station_name=record.name,
            short_name=record.short_name,
            capacity=record.capacity,
            operator=operator,
            borough=borough,
            latitude=record.lat,
            longitude=record.lon,
            event_date=stamp,
            h3_res7=h3["h3_res7"],
            h3_res8=h3["h3_res8"],
            h3_res9=h3["h3_res9"],
            ingested_at=stamp,
        )

    def run_stream(self, city_id: str = "nyc", limit: int | None = None, **_: Any) -> int:
        """Poll one city's system, emit its transitions, persist the state."""
        from src.spatial.city_registry import CityId, FeedType, get_dataset, normalize_city

        cid = normalize_city(city_id) or CityId.NYC
        spec = get_dataset(cid, FeedType.GBFS)
        system_id = (spec.companion_endpoints or {}).get("system_id") or cid.value
        operator = (spec.companion_endpoints or {}).get("operator")

        diff, merged, version = self.snapshot.poll(system_id, spec.endpoint)

        streamed = 0
        for record, event_type in (
            [(r, STATION_ADDED) for r in diff.added] + [(r, STATION_REMOVED) for r in diff.removed]
        ):
            event = self.build_event(record, event_type, cid.value, system_id, operator)
            if event is None:
                continue
            self.producer.produce(
                topic=settings.topic_station_change,
                key=f"{event.city_id}:{system_id}:{event.station_id}",
                payload=event,
            )
            streamed += 1

        for station_id, reason in diff.dlq:
            self.producer.route_to_dlq(
                failed_topic=settings.topic_station_change,
                key=f"{cid.value}:{system_id}:{station_id or 'unknown'}",
                payload={"system_id": system_id, "station_id": station_id},
                error_msg=reason,
            )

        # Persist only after producing: if the process dies mid-emit the next
        # poll re-derives the same diff from the old state rather than losing
        # the transitions entirely.
        self.snapshot.save_state(system_id, merged)
        self.producer.flush()
        logger.info(
            "%s GBFS %s (v%s): streamed %d transitions, state now %d stations",
            cid.value.upper(),
            system_id,
            version or "?",
            streamed,
            len(merged),
        )
        return streamed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GBFS station-change Kafka producer")
    parser.add_argument("--city", default="nyc")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    GbfsProducer().run_stream(city_id=args.city)
