"""NY State Liquor Authority & Chicago Business Licenses Producer."""

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from src.config import settings
from src.producers.base_producer import BaseKafkaProducer
from src.producers.arcgis_client import ArcGISClient
from src.producers.carto_client import CartoClient
from src.producers.socrata_client import SocrataClient
from src.schemas.models import SLALicenseEvent
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


class SLALicensesProducer:
    """Ingests NY SLA, Chicago, and San Francisco business/hospitality license filings and streams to Kafka."""

    def __init__(self, bootstrap_servers: Optional[str] = None):
        schema_path = Path(__file__).parent.parent / "schemas" / "avro" / "sla_license_event.avsc"
        self.producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=schema_path,
            dlq_topic=settings.topic_dlq,
        )
        self.socrata = SocrataClient()
        self.arcgis = ArcGISClient()
        self.carto = CartoClient()
        self.spatial_indexer = H3SpatialIndexer()

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
        }
        client = clients.get(platform)
        if client is None:
            available = ", ".join(sorted(k for k, v in clients.items() if v is not None))
            raise ValueError(
                f"platform {platform!r} has no client on this producer "
                f"(available: {available}); wire it before registering the spec"
            )
        return client

    def parse_socrata_row(self, row: Dict[str, Any], city_id: Optional[str] = None) -> Optional[SLALicenseEvent]:
        """Convert raw SLA / business license record to strongly-typed SLALicenseEvent."""
        try:
            # Determine city_id
            from src.spatial.city_registry import CityId, ALIASES, REGISTRY, FeedType, normalize_city, get_dataset
            if city_id is not None:
                norm_c = normalize_city(city_id)
                resolved_city = norm_c.value if norm_c else city_id.lower()
            elif row.get("city_id"):
                norm_c = normalize_city(row["city_id"])
                resolved_city = norm_c.value if norm_c else str(row["city_id"]).lower()
            elif "location_account" in row or "primary_naics_description" in row:
                # LA Office of Finance active-business registrations. Checked
                # before San Francisco: LA shares dba_name and location_start_date
                # with the SF registry, so only these two columns discriminate.
                resolved_city = "los_angeles"
            elif (
                "location_id" in row
                or "dba_name" in row
                or "ownership_name" in row
                or "naics_code_description" in row
                or "lic_code_description" in row
                or "business_start_date" in row
                or "location_start_date" in row
            ):
                resolved_city = "san_francisco"
            elif (
                "doing_business_as_name" in row
                or "license_description" in row
                or ("license_id" in row and "licensepermitid" not in row and "legacyserialnumber" not in row)
            ):
                resolved_city = "chicago"
            else:
                resolved_city = "nyc"

            from src.producers.field_maps import first_mapped, resolve_field_map
            from src.spatial.geocoder import geocode_row_if_declared

            field_map = resolve_field_map(resolved_city, FeedType.SLA)

            license_id = str(
                first_mapped(row, field_map, "license_id")
                or row.get("location_id")
                or row.get("location_account")
                or row.get("certificate_number")
                or row.get("business_account_number")
                or row.get("license_id")
                or row.get("licensepermitid")
                or row.get("legacyserialnumber")
                or row.get("serial_number")
                or row.get("license_serial_number")
                or row.get("account_number")
                or row.get("id")
                or ""
            ).strip()
            if not license_id:
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
                loc = (
                    row.get("business_location")
                    or row.get("location_1")
                    or row.get("georeference")
                    or row.get("location")
                    or row.get("point")
                    or row.get("the_geom")
                    or {}
                )
                if isinstance(loc, dict):
                    lat_raw = loc.get("latitude") or loc.get("lat") or (
                        loc.get("coordinates", [None, None])[1] if "coordinates" in loc else None
                    )
                    lng_raw = loc.get("longitude") or loc.get("lng") or (
                        loc.get("coordinates", [None, None])[0] if "coordinates" in loc else None
                    )

            if not lat_raw or not lng_raw:
                # Address-string feeds declaring extra["needs_geocode"]
                # (ADR 0004) resolve coordinates at parse time so the wire
                # event carries real doubles; coordinate-less registries
                # without the declaration keep emitting null-coord events.
                addr_candidate = (
                    first_mapped(row, field_map, "address_street")
                    or row.get("location_address")
                    or row.get("address")
                    or row.get("street_address")
                )
                resolved = geocode_row_if_declared(resolved_city, "sla", addr_candidate)
                if resolved is not None:
                    lat_raw, lng_raw = resolved

            lat = float(lat_raw) if lat_raw is not None else None
            lng = float(lng_raw) if lng_raw is not None else None

            # Roughly 7% of LA's business-registration rows carry a 0.0/0.0
            # placeholder rather than a real geocode. Treating that as a valid
            # coordinate would file them under an H3 cell in the Gulf of Guinea.
            if lat is not None and lng is not None and lat == 0.0 and lng == 0.0:
                return None

            # Non-spatial license registries (DC Basic Business Licenses) have
            # no coordinates at all: emit null-lat/lng/null-H3 events keyed on
            # the license id, mirroring the deeds producer's tolerance for
            # coordinate-less sources — rather than dropping every row.
            h3_res = (
                self.spatial_indexer.get_multi_res_hierarchy(lat, lng)
                if lat is not None and lng is not None
                else {"h3_res7": None, "h3_res8": None, "h3_res9": None}
            )

            effective_str = (
                first_mapped(row, field_map, "effective_date")
                or row.get("business_start_date")
                or row.get("location_start_date")
                or row.get("date_issued")
                or row.get("license_start_date")
                or row.get("effectivedate")
                or row.get("license_effective_date")
                or row.get("effective_date")
                or row.get("originalissuedate")
                or row.get("lastissuedate")
            )
            effective_dt = _parse_datetime(effective_str)

            expiration_str = (
                first_mapped(row, field_map, "expiration_date")
                or row.get("location_end_date")
                or row.get("business_end_date")
                or row.get("license_term_expiration_date")
                or row.get("expiration_date")
                or row.get("license_expiration_date")
            )
            expiration_dt = _parse_datetime(expiration_str)

            license_type = (
                first_mapped(row, field_map, "license_type")
                or row.get("naics_code_description")
                or row.get("lic_code_description")
                or row.get("business_description")
                or row.get("class_code_description")
                or row.get("license_description")
                or row.get("description")
                or row.get("license_type_name")
                or row.get("business_activity")
                or row.get("class")
                or row.get("license_class")
                or "On-Premises Liquor"
            )

            premises_name = (
                row.get("ownership_name")
                or row.get("legal_name")
                or row.get("legalname")
                or row.get("premises_name")
                or row.get("dba_name")
            )

            dba = (
                row.get("dba_name")
                or row.get("doing_business_as_name")
                or row.get("dba")
                or row.get("doing_business_as")
                or row.get("business_name")
            )

            address = (
                row.get("street_address")
                or row.get("business_address")
                or row.get("full_business_address")
                or row.get("address")
                or row.get("actualaddressofpremises")
                or row.get("actual_address_line1")
            )

            if row.get("location_end_date") or row.get("business_end_date"):
                default_status = "INACTIVE"
            else:
                default_status = "ACTIVE"
            status = (
                first_mapped(row, field_map, "status")
                or row.get("license_status")
                or row.get("licensestatus")
                or row.get("status")
                or default_status
            )

            borough_val = (
                first_mapped(row, field_map, "borough")
                or row.get("neighborhoods_analysis_boundaries")
                or row.get("analysis_neighborhood")
                or row.get("neighborhood")
                or row.get("supervisor_district")
                or row.get("borough")
            )
            source_neighborhood = str(borough_val) if borough_val is not None else None
            from src.spatial.geo_utils import get_division_for_coordinate
            resolved_borough = get_division_for_coordinate(lat, lng, city_id=resolved_city) or source_neighborhood

            return SLALicenseEvent(
                city_id=resolved_city,
                license_id=license_id,
                license_type=license_type,
                premises_name=premises_name,
                dba=dba,
                address=address,
                borough=resolved_borough,
                source_neighborhood=source_neighborhood,
                latitude=lat,
                longitude=lng,
                effective_date=effective_dt,
                expiration_date=expiration_dt,
                license_status=status,
                h3_res7=h3_res["h3_res7"],
                h3_res8=h3_res["h3_res8"],
                h3_res9=h3_res["h3_res9"],
                ingested_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning("Error parsing SLA row: %s", e)
            return None

    def run_stream(self, city_id: str = "nyc", limit: int = 5000, where_clause: Optional[str] = None):
        """Fetch SLA / license records and stream them into Kafka topic."""
        from src.spatial.city_registry import REGISTRY, CityId, FeedType, normalize_city, get_dataset
        cid = normalize_city(city_id) or CityId.NYC
        spec = get_dataset(cid, FeedType.SLA)
        endpoint = spec.endpoint
        client = self._client_for(spec.platform)
        client_kwargs = {
            k: v for k, v in spec.extra.items() if k in ("order_by", "id_col", "select") and v
        }

        logger.info("Starting %s SLA / License Ingestion Stream (limit=%d)...", cid.value.upper(), limit)
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
                    key = f"{event.city_id}:{event.license_id}"
                    self.producer.produce(
                        topic=settings.topic_sla,
                        key=key,
                        payload=event,
                    )
                    records_streamed += 1

        self.producer.flush()
        logger.info("%s SLA / License Ingestion completed. Total streamed: %d records.", cid.value.upper(), records_streamed)
        return records_streamed


if __name__ == "__main__":
    from src.spatial.city_registry import ALIASES
    parser = argparse.ArgumentParser(description="Hospitality Licenses Kafka Producer")
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
    producer = SLALicensesProducer()
    producer.run_stream(city_id=args.city, limit=args.limit)
