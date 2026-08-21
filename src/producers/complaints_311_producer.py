"""NYC & Chicago 311 Service Requests Ingestion Stream Producer."""

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from src.config import settings
from src.features.shift_dynamics import ComplaintShiftDynamics
from src.producers.base_producer import BaseKafkaProducer
from src.producers.socrata_client import SocrataClient
from src.schemas.models import Complaint311Event
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)


def _parse_datetime(val: Any) -> Optional[datetime]:
    """Parse various ISO and common municipal date formats into a timezone-aware datetime."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str):
        val_clean = val.replace("Z", "+00:00").strip()
        try:
            return datetime.fromisoformat(val_clean)
        except ValueError:
            pass
        for fmt in (
            "%m/%d/%Y",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %I:%M:%S %p",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                return datetime.strptime(val.strip(), fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
    return None


class Complaints311Producer:
    """Ingests NYC, Chicago, and San Francisco 311 service complaints, classifies them, and streams to Kafka."""

    def __init__(self, bootstrap_servers: Optional[str] = None):
        schema_path = Path(__file__).parent.parent / "schemas" / "avro" / "complaint_311_event.avsc"
        self.producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=schema_path,
            dlq_topic=settings.topic_dlq,
        )
        self.socrata = SocrataClient()
        self.spatial_indexer = H3SpatialIndexer()
        self.shift_dynamics = ComplaintShiftDynamics()

    def parse_socrata_row(self, row: Dict[str, Any], city_id: Optional[str] = None) -> Optional[Complaint311Event]:
        """Parse raw 311 record into strongly-typed Complaint311Event with category classification."""
        try:
            # Determine city_id
            from src.spatial.city_registry import CityId, ALIASES, REGISTRY, FeedType, normalize_city
            if city_id is not None:
                norm_c = normalize_city(city_id)
                resolved_city = norm_c.value if norm_c else city_id.lower()
            elif row.get("city_id"):
                norm_c = normalize_city(row["city_id"])
                resolved_city = norm_c.value if norm_c else str(row["city_id"]).lower()
            elif (
                "service_request_id" in row
                or "service_name" in row
                or "service_details" in row
                or "neighborhoods_sffind_boundaries" in row
                or "supervisor_district" in row
            ):
                resolved_city = "san_francisco"
            elif "sr_number" in row or "sr_type" in row:
                resolved_city = "chicago"
            else:
                resolved_city = "nyc"

            incident_id = str(
                row.get("service_request_id")
                or row.get("sr_number")
                or row.get("unique_key")
                or row.get("service_request_number")
                or row.get("id")
                or ""
            ).strip()
            if not incident_id:
                return None

            lat_raw = row.get("latitude") or row.get("lat")
            lng_raw = row.get("longitude") or row.get("lng") or row.get("long")
            if not lat_raw or not lng_raw:
                loc = row.get("point") or row.get("location") or row.get("the_geom") or {}
                if isinstance(loc, dict):
                    lat_raw = loc.get("latitude") or loc.get("lat") or (
                        loc.get("coordinates", [None, None])[1] if "coordinates" in loc else None
                    )
                    lng_raw = loc.get("longitude") or loc.get("lng") or loc.get("long") or (
                        loc.get("coordinates", [None, None])[0] if "coordinates" in loc else None
                    )

            if not lat_raw or not lng_raw:
                return None

            lat = float(lat_raw)
            lng = float(lng_raw)

            h3_res = self.spatial_indexer.get_multi_res_hierarchy(lat, lng)

            complaint_type = (
                row.get("service_name")
                or row.get("service_details")
                or row.get("service_subtype")
                or row.get("sr_type")
                or row.get("complaint_type")
                or row.get("request_type")
                or row.get("type")
                or "Unknown"
            )
            descriptor = (
                row.get("service_details")
                or row.get("service_subtype")
                or row.get("descriptor")
                or row.get("sr_short_code")
                or row.get("sr_type")
            )
            category = self.shift_dynamics.classify_complaint_type(
                f"{complaint_type} {descriptor or ''}".strip()
            )

            created_str = (
                row.get("requested_datetime")
                or row.get("created_date")
                or row.get("create_date")
                or row.get("created_at")
            )
            created_dt = _parse_datetime(created_str) or datetime.now(timezone.utc)

            closed_str = (
                row.get("closed_date")
                or row.get("closed_datetime")
                or row.get("updated_datetime")
                or row.get("completion_date")
                or row.get("completed_date")
            )
            closed_dt = _parse_datetime(closed_str)

            borough_val = (
                row.get("neighborhoods_sffind_boundaries")
                or row.get("analysis_neighborhood")
                or row.get("neighborhood")
                or row.get("supervisor_district")
                or row.get("borough")
            )
            if not borough_val and row.get("community_area") is not None:
                borough_val = str(row["community_area"])
            elif not borough_val and row.get("community_areas") is not None:
                borough_val = str(row["community_areas"])

            incident_address = (
                row.get("address")
                or row.get("street_address")
                or row.get("incident_address")
            )

            zipcode = str(
                row.get("zipcode")
                or row.get("zip_code")
                or row.get("postal_code")
                or row.get("incident_zip")
                or row.get("postcode")
                or ""
            )

            source_neighborhood = str(borough_val) if borough_val is not None else None
            from src.spatial.geo_utils import get_division_for_coordinate
            resolved_borough = get_division_for_coordinate(lat, lng, city_id=resolved_city) or source_neighborhood

            return Complaint311Event(
                city_id=resolved_city,
                incident_id=incident_id,
                complaint_type=complaint_type,
                descriptor=descriptor,
                category=category,
                incident_address=incident_address,
                borough=resolved_borough,
                source_neighborhood=source_neighborhood,
                zipcode=zipcode,
                latitude=lat,
                longitude=lng,
                created_date=created_dt,
                closed_date=closed_dt,
                status=row.get("status") or "Open",
                h3_res7=h3_res["h3_res7"],
                h3_res8=h3_res["h3_res8"],
                h3_res9=h3_res["h3_res9"],
                ingested_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning("Error parsing 311 row: %s", e)
            return None

    def run_stream(self, city_id: str = "nyc", limit: int = 5000, where_clause: Optional[str] = None):
        """Fetch 311 records and stream them into Kafka topic."""
        from src.spatial.city_registry import REGISTRY, CityId, FeedType, normalize_city
        cid = normalize_city(city_id) or CityId.NYC
        endpoint = REGISTRY[cid].datasets[FeedType.COMPLAINTS_311].endpoint

        logger.info("Starting %s 311 Ingestion Stream (limit=%d)...", cid.value.upper(), limit)
        records_streamed = 0

        for batch in self.socrata.paginate(
            endpoint_url=endpoint,
            where_clause=where_clause,
            batch_size=1000,
            max_records=limit,
        ):
            for row in batch:
                event = self.parse_socrata_row(row, city_id=cid.value)
                if event:
                    key = f"{event.city_id}:{event.incident_id}"
                    self.producer.produce(
                        topic=settings.topic_311,
                        key=key,
                        payload=event,
                    )
                    records_streamed += 1

        self.producer.flush()
        logger.info("%s 311 Ingestion completed. Total streamed: %d records.", cid.value.upper(), records_streamed)
        return records_streamed


if __name__ == "__main__":
    from src.spatial.city_registry import ALIASES
    parser = argparse.ArgumentParser(description="311 Complaints Kafka Producer")
    parser.add_argument(
        "--city",
        type=str,
        default="nyc",
        choices=list(ALIASES.keys()),
        help="City identifier",
    )
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    producer = Complaints311Producer()
    producer.run_stream(city_id=args.city, limit=args.limit)
