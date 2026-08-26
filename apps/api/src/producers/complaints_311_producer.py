"""NYC & Chicago 311 Service Requests Ingestion Stream Producer."""

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import settings
from src.features.shift_dynamics import ComplaintShiftDynamics
from src.producers.arcgis_client import ArcGISClient
from src.producers.base_producer import BaseKafkaProducer
from src.producers.carto_client import CartoClient
from src.producers.ckan_client import CkanClient
from src.producers.csv_client import CSVClient
from src.producers.socrata_client import SocrataClient
from src.schemas.models import Complaint311Event
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)


def _parse_datetime(val: Any) -> datetime | None:
    """Parse various ISO and common municipal date formats into a timezone-aware datetime."""
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
        for fmt in (
            "%m/%d/%Y",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d",
            "%m/%d/%Y %I:%M:%S %p",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                return datetime.strptime(val.strip(), fmt).replace(tzinfo=UTC)
            except ValueError:
                pass
    return None


class Complaints311Producer:
    """Ingests NYC, Chicago, and San Francisco 311 service complaints, classifies them, and streams to Kafka."""

    def __init__(self, bootstrap_servers: str | None = None):
        schema_path = Path(__file__).parent.parent / "schemas" / "avro" / "complaint_311_event.avsc"
        self.producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=schema_path,
            dlq_topic=settings.topic_dlq,
        )
        self.socrata = SocrataClient()
        self.arcgis = ArcGISClient()
        self.carto = CartoClient()
        self.ckan = CkanClient()
        self.csv = CSVClient()
        self.spatial_indexer = H3SpatialIndexer()
        self.shift_dynamics = ComplaintShiftDynamics()

    def _client_for(self, platform: str):
        """Select the paginating client matching a DatasetSpec's platform.

        Both clients satisfy the same ``PaginatingClient`` protocol, so callers
        only need the right instance, not a different call shape.
        """
        clients = {
            "socrata": getattr(self, "socrata", None),
            "arcgis": getattr(self, "arcgis", None),
            "carto": getattr(self, "carto", None),
            "ckan": getattr(self, "ckan", None),
            "csv": getattr(self, "csv", None),
        }
        client = clients.get(platform)
        if client is None:
            available = ", ".join(sorted(k for k, v in clients.items() if v is not None))
            raise ValueError(
                f"platform {platform!r} has no client on this producer "
                f"(available: {available}); wire it before registering the spec"
            )
        return client

    def parse_socrata_row(self, row: dict[str, Any], city_id: str | None = None) -> Complaint311Event | None:
        """Parse raw 311 record into strongly-typed Complaint311Event with category classification."""
        try:
            # Determine city_id
            from src.spatial.city_registry import (
                FeedType,
                normalize_city,
            )
            if city_id is not None:
                norm_c = normalize_city(city_id)
                resolved_city = norm_c.value if norm_c else city_id.lower()
            elif row.get("city_id"):
                norm_c = normalize_city(row["city_id"])
                resolved_city = norm_c.value if norm_c else str(row["city_id"]).lower()
            elif (
                "service_request_id" in row
                and (
                    "date_requested" in row
                    or "sap_notification_number" in row
                    or "comm_plan_name" in row
                )
            ):
                # San Diego Get It Done (US-124, flat CSV). SF 311 also uses
                # `service_request_id`, so an SD-only corroborating marker
                # (its date_requested / sap_notification_number / comm_plan
                # family) is required before claiming the row.
                resolved_city = "san_diego"
            elif (
                "service_request_id" in row
                or "service_name" in row
                or "service_details" in row
                or "neighborhoods_sffind_boundaries" in row
                or "supervisor_district" in row
            ):
                resolved_city = "san_francisco"
            elif (
                "sr_number" in row
                and (
                    "sr_type" in row
                    or "sr_short_code" in row
                    or "ward" in row
                    or "police_sector" in row
                    or "community_area" in row
                )
            ):
                # Chicago 311. `sr_number` alone is not distinctive enough:
                # Austin's feed carries it too, so a corroborating Chicago-only
                # marker (its schema's sr_type/ward/community_area family) is
                # required before claiming the row.
                resolved_city = "chicago"
            elif (
                "casenumber" in row
                or "srnumber" in row
                or "department_name__c" in row
            ):
                # LA MyLA311. No column collides with the SF or Chicago keys;
                # the 2026 "Cases" schema uses `casenumber`, the 2015-2024
                # yearly backfills use `srnumber`.
                resolved_city = "los_angeles"
            else:
                resolved_city = "nyc"

            from src.producers.field_maps import first_mapped, resolve_field_map
            from src.spatial.geocoder import geocode_row_if_declared

            field_map = resolve_field_map(resolved_city, FeedType.COMPLAINTS_311)

            incident_id = str(
                first_mapped(row, field_map, "incident_id")
                or row.get("service_request_id")
                or row.get("sr_number")
                or row.get("unique_key")
                or row.get("service_request_number")
                or row.get("id")
                or ""
            ).strip()
            if not incident_id:
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
                or row.get("long")
            )
            if not lat_raw or not lng_raw:
                loc = row.get("point") or row.get("location") or row.get("the_geom") or {}
                if isinstance(loc, dict):
                    lat_raw = loc.get("latitude") or loc.get("lat") or (
                        loc.get("coordinates", [None, None])[1] if "coordinates" in loc else None
                    )
                    lng_raw = loc.get("longitude") or loc.get("lng") or loc.get("long") or (
                        loc.get("coordinates", [None, None])[0] if "coordinates" in loc else None
                    )

            # Some ArcGIS services expose projected coordinates as point
            # geometry. Hartford's 311 layer uses CT state-plane feet, which
            # ArcGISClient would otherwise flatten into misleading lat/lng
            # fields. Force declared address-geocoded feeds through the
            # geocoder when the values cannot be geographic degrees.
            try:
                if (
                    lat_raw is not None
                    and lng_raw is not None
                    and (abs(float(lat_raw)) > 90 or abs(float(lng_raw)) > 180)
                ):
                    lat_raw = None
                    lng_raw = None
            except (TypeError, ValueError):
                lat_raw = None
                lng_raw = None

            if not lat_raw or not lng_raw:
                # Address-string feeds declaring extra["needs_geocode"]
                # (ADR 0004) resolve coordinates at parse time so the wire
                # event carries real doubles; everything else keeps the
                # legacy hard drop.
                addr_candidate = (
                    first_mapped(row, field_map, "incident_address")
                    or row.get("address")
                    or row.get("street_address")
                    or row.get("location")
                )
                if isinstance(addr_candidate, dict):
                    addr_candidate = None
                resolved = geocode_row_if_declared(resolved_city, "311", addr_candidate)
                if resolved is None:
                    return None
                lat_raw, lng_raw = resolved

            lat = float(lat_raw)
            lng = float(lng_raw)

            # Some feeds (LA business registrations ~7%, MyLA311's ungeocoded
            # remainder) carry a 0.0/0.0 placeholder rather than a real
            # geocode. Treating that as a valid coordinate would file those
            # rows under an H3 cell in the Gulf of Guinea.
            if lat == 0.0 and lng == 0.0:
                return None

            h3_res = self.spatial_indexer.get_multi_res_hierarchy(lat, lng)

            complaint_type = (
                first_mapped(row, field_map, "complaint_type")
                or row.get("service_name")
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
                first_mapped(row, field_map, "created_date")
                or row.get("requested_datetime")
                or row.get("created_date")
                or row.get("create_date")
                or row.get("created_at")
            )
            created_dt = _parse_datetime(created_str) or datetime.now(UTC)

            closed_str = (
                first_mapped(row, field_map, "closed_date")
                or row.get("closed_date")
                or row.get("closed_datetime")
                or row.get("updated_datetime")
                or row.get("completion_date")
                or row.get("completed_date")
            )
            closed_dt = _parse_datetime(closed_str)

            borough_val = (
                first_mapped(row, field_map, "borough")
                or row.get("neighborhoods_sffind_boundaries")
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
                first_mapped(row, field_map, "incident_address")
                or row.get("address")
                or row.get("street_address")
                or row.get("incident_address")
            )

            zipcode = str(
                first_mapped(row, field_map, "zipcode")
                or row.get("zipcode")
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
                status=(
                    first_mapped(row, field_map, "status")
                    or row.get("status")
                    or "Open"
                ),
                h3_res7=h3_res["h3_res7"],
                h3_res8=h3_res["h3_res8"],
                h3_res9=h3_res["h3_res9"],
                ingested_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.warning("Error parsing 311 row: %s", e)
            return None

    def run_stream(self, city_id: str = "nyc", limit: int = 5000, where_clause: str | None = None):
        """Fetch 311 records and stream them into Kafka topic."""
        from src.spatial.city_registry import (
            CityId,
            FeedType,
            get_dataset,
            normalize_city,
        )
        cid = normalize_city(city_id) or CityId.NYC
        spec = get_dataset(cid, FeedType.COMPLAINTS_311)
        endpoint = spec.endpoint
        client = self._client_for(spec.platform)
        client_kwargs = {
            k: v for k, v in spec.extra.items() if k in ("order_by", "id_col", "select") and v
        }

        logger.info("Starting %s 311 Ingestion Stream (limit=%d)...", cid.value.upper(), limit)
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
