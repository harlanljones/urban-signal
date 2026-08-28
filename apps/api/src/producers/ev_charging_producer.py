"""NREL AFDC EV charging snapshot producer (US-363 §1.5)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import settings
from src.producers.base_producer import BaseKafkaProducer
from src.producers.nrel_afdc_client import NrelAfdcClient
from src.schemas.models import InfrastructureEvent
from src.spatial.geography_crosswalk import GeographyCrosswalk
from src.spatial.h3_indexer import H3SpatialIndexer


def _int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


class EvChargingProducer:
    def __init__(self, bootstrap_servers: str | None = None, client: Any = None, indexer: Any = None,
                 crosswalk: GeographyCrosswalk | None = None):
        self.client = client or NrelAfdcClient()
        self.ev_charging = self.client
        # Keep the scheduler's common producer surface uniform. AFDC is the
        # only client used by this producer; Socrata is intentionally unused.
        self.socrata = None
        self.indexer = indexer or H3SpatialIndexer()
        self.crosswalk = crosswalk or GeographyCrosswalk()
        self.producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=Path(__file__).parent.parent / "schemas" / "avro" / "infrastructure_event.avsc",
            dlq_topic=settings.topic_dlq,
        )

    def build_event(self, row: dict[str, Any], detected_at: datetime | None = None) -> InfrastructureEvent | None:
        try:
            lat, lng = float(row["latitude"]), float(row["longitude"])
        except (KeyError, TypeError, ValueError):
            return None
        city_id = self.crosswalk.city_for_point(lat, lng)
        if city_id is None:
            return None
        open_date = _date(row.get("open_date"))
        event_date = open_date or _date(row.get("last_updated")) or detected_at or datetime.now(UTC)
        level2 = _int(row.get("ev_level2_evse_num")) or 0
        fast = _int(row.get("ev_dc_fast_num")) or 0
        return InfrastructureEvent(
            city_id=city_id, asset_id=str(row.get("id")), category="ev_station",
            event_type="opened", name=row.get("station_name"), operator=row.get("owner_type_code"),
            status=row.get("status_code"), access_type=row.get("access_code"),
            unit_count=level2 + fast, fast_unit_count=fast, address=row.get("street_address"),
            zipcode=str(row["zip"]) if row.get("zip") else None, latitude=lat, longitude=lng,
            event_date=event_date, date_is_detection=open_date is None,
            **self.indexer.get_multi_res_hierarchy(lat, lng),
        )

    def run_stream(self, limit: int | None = None, **_: Any) -> int:
        emitted = 0
        for batch in self.client.paginate(settings.nrel_afdc_endpoint, max_records=limit):
            for row in batch:
                event = self.build_event(row)
                if event is None:
                    continue
                self.producer.produce(settings.topic_infrastructure, f"{event.city_id}:{event.asset_id}", event)
                emitted += 1
        self.producer.flush()
        return emitted
