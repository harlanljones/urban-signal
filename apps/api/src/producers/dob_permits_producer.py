"""NYC & Chicago DOB / Building Permits and Alterations Ingestion Stream Producer."""

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import settings
from src.producers.arcgis_client import ArcGISClient
from src.producers.accela_client import AccelaClient
from src.producers.base_producer import BaseKafkaProducer
from src.producers.carto_client import CartoClient
from src.producers.ckan_client import CkanClient
from src.producers.csv_client import CSVClient
from src.producers.excel_client import ExcelClient
from src.producers.socrata_client import SocrataClient
from src.schemas.models import JobType, PermitEvent
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)

# US-91: San Diego's approvals table is broader than permits — it also carries
# process agreements, zone-history letters, use certificates, easement maps,
# Mills Act agreements, etc. Only construction/permit-class rows are the
# building-permit signal; everything else is dropped at parse time.
PERMIT_LIKE_KEYWORDS = (
    "PERMIT",
    "PMT",
    "BUILDING",
    "CONSTRUCTION",
    "DEMOLITION",
    "ELECTRICAL",
    "PLUMBING",
    "MECHANICAL",
    "PHOTOVOLTAIC",
    "GRADING",
    "FIRE",
)


def _is_permit_like_approval(approval_type: Any) -> bool:
    text = str(approval_type or "").upper()
    return any(keyword in text for keyword in PERMIT_LIKE_KEYWORDS)


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
            "%m/%d/%Y %I:%M:%S %p",
            "%Y-%m-%dT%H:%M:%S",
            "%B, %d %Y %H:%M:%S",
        ):
            try:
                return datetime.strptime(val.strip(), fmt).replace(tzinfo=UTC)
            except ValueError:
                pass
    return None


class DOBPermitsProducer:
    """Ingests NYC, Chicago, and San Francisco building permit filings and streams to Kafka."""

    def __init__(self, bootstrap_servers: str | None = None):
        schema_path = Path(__file__).parent.parent / "schemas" / "avro" / "permit_event.avsc"
        self.producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=schema_path,
            dlq_topic=settings.topic_dlq,
        )
        self.socrata = SocrataClient()
        self.arcgis = ArcGISClient()
        self.accela = AccelaClient()
        self.carto = CartoClient()
        self.ckan = CkanClient()
        self.csv = CSVClient()
        self.excel = ExcelClient()
        self.spatial_indexer = H3SpatialIndexer()

    def _client_for(self, platform: str):
        """Select the paginating client matching a DatasetSpec's platform.

        Both clients satisfy the same ``PaginatingClient`` protocol, so callers
        only need the right instance, not a different call shape.
        """
        clients = {
            "socrata": getattr(self, "socrata", None),
            "arcgis": getattr(self, "arcgis", None),
            "accela": getattr(self, "accela", None),
            "carto": getattr(self, "carto", None),
            "ckan": getattr(self, "ckan", None),
            "csv": getattr(self, "csv", None),
            "excel": getattr(self, "excel", None),
        }
        client = clients.get(platform)
        if client is None:
            available = ", ".join(sorted(k for k, v in clients.items() if v is not None))
            raise ValueError(
                f"platform {platform!r} has no client on this producer "
                f"(available: {available}); wire it before registering the spec"
            )
        return client

    def parse_socrata_row(self, row: dict[str, Any], city_id: str | None = None) -> PermitEvent | None:
        """Convert raw Socrata JSON permit dict into strongly-typed PermitEvent."""
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
                "permit_type_definition" in row
                or "revised_cost" in row
                or "analysis_neighborhood" in row
                or "neighborhoods_analysis_boundaries" in row
                or "supervisor_district" in row
            ):
                resolved_city = "san_francisco"
            elif "permit_nbr" in row or "cofo_date" in row or "permit_sub_type" in row:
                # LADBS building permits (data.lacity.org).
                resolved_city = "los_angeles"
            elif "permit_" in row or "reported_cost" in row or "community_area" in row:
                resolved_city = "chicago"
            elif (
                "approval_id" in row
                or "development_id" in row
                or "gis_apn" in row
            ):
                # San Diego Development Services approvals (US-91, flat CSV).
                resolved_city = "san_diego"
            else:
                resolved_city = "nyc"

            if resolved_city == "san_diego" and not _is_permit_like_approval(
                row.get("approval_type")
            ):
                # The approvals table is broader than permits (process
                # agreements, zone letters, use certificates, easement maps).
                return None

            from src.producers.field_maps import first_mapped, resolve_field_map

            field_map = resolve_field_map(resolved_city, FeedType.PERMITS)

            if resolved_city == "albuquerque":
                from src.spatial.cities.albuquerque import compose_permit_address

                composed = compose_permit_address(row)
                if composed:
                    row = {**row, "address_street": composed}

            job_id = str(
                first_mapped(row, field_map, "job_id")
                or row.get("permit_number")
                or row.get("permit_nbr")
                or row.get("permit_")
                or row.get("job__")
                or row.get("job_number")
                or row.get("job_filing_number")
                or row.get("id")
                or row.get("application_number")
                or ""
            ).strip()
            if not job_id:
                return None

            lat_raw = (
                first_mapped(row, field_map, "latitude")
                or row.get("latitude")
                or row.get("lat")
                or row.get("gis_latitude")
            )
            lng_raw = (
                first_mapped(row, field_map, "longitude")
                or row.get("longitude")
                or row.get("lng")
                or row.get("lon")
                or row.get("long")
                or row.get("gis_longitude")
            )
            if not lat_raw or not lng_raw:
                loc = row.get("location") or row.get("point") or row.get("the_geom") or row.get("shape") or {}
                if isinstance(loc, dict):
                    lat_raw = loc.get("latitude") or loc.get("lat") or (
                        loc.get("coordinates", [None, None])[1] if "coordinates" in loc else None
                    )
                    lng_raw = loc.get("longitude") or loc.get("lng") or loc.get("long") or (
                        loc.get("coordinates", [None, None])[0] if "coordinates" in loc else None
                    )

            # Some feeds expose projected/state-plane coordinates in fields
            # named X/Y. Never emit those values as geographic degrees.
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
                from src.spatial.geocoder import geocode_row_if_declared

                addr_candidate = (
                    first_mapped(row, field_map, "address_street")
                    or row.get("property_address")
                    or row.get("address")
                    or row.get("location")
                )
                if isinstance(addr_candidate, dict):
                    addr_candidate = None
                resolved = geocode_row_if_declared(resolved_city, "permits", addr_candidate)
                if resolved is None:
                    return None
                lat_raw, lng_raw = resolved

            lat = float(lat_raw)
            lng = float(lng_raw)

            # Spatial H3 hierarchy
            h3_res = self.spatial_indexer.get_multi_res_hierarchy(lat, lng)

            # Job Type
            raw_job_type = (
                first_mapped(row, field_map, "job_type")
                or row.get("permit_type_definition")
                or row.get("permit_type")
                or row.get("job_type")
                or row.get("filing_type")
                or row.get("description")
                or "A1"
            ).upper()
            if (
                "NEW CONSTRUCTION" in raw_job_type
                or "NEW BUILDING" in raw_job_type
                or raw_job_type in {"NEW", "NB"}
            ):
                job_type = JobType.NB
            elif "DEMOLITION" in raw_job_type or "DEMOLITIONS" in raw_job_type or "WRECKING" in raw_job_type or raw_job_type == "DM":
                job_type = JobType.DM
            elif "SIGN" in raw_job_type or raw_job_type == "SG":
                job_type = JobType.SG
            elif "SCAFFOLD" in raw_job_type or raw_job_type == "A3":
                job_type = JobType.A3
            elif "MAJOR" in raw_job_type or raw_job_type == "A1":
                job_type = JobType.A1
            elif (
                "RENOVATION" in raw_job_type
                or "ALTERATION" in raw_job_type
                or "ALTERATIONS" in raw_job_type
                or "ADDITION" in raw_job_type
                or "ADDITIONS" in raw_job_type
                or "REPAIR" in raw_job_type
                or "EASY PERMIT" in raw_job_type
                or "ELECTRIC" in raw_job_type
                or "PLUMBING" in raw_job_type
                or "OTC ALTERATIONS" in raw_job_type
                or raw_job_type == "A2"
            ):
                job_type = JobType.A2
            else:
                try:
                    job_type = JobType(raw_job_type)
                except ValueError:
                    job_type = JobType.OT

            # Cost
            cost_raw = (
                first_mapped(row, field_map, "cost")
                or row.get("revised_cost")
                or row.get("estimated_cost")
                or row.get("reported_cost")
                or row.get("total_fee")
                or row.get("initial_cost")
                or row.get("estimated_job_costs")
                or row.get("total_est_fee")
                or row.get("valuation")
                or 0.0
            )
            try:
                cost = float(str(cost_raw).replace("$", "").replace(",", "").strip())
            except (ValueError, TypeError):
                cost = 0.0

            # Filing / issuance dates
            issuance_str = (
                first_mapped(row, field_map, "issuance_date")
                or row.get("issued_date")
                or row.get("issue_date")
                or row.get("issuance_date")
                or row.get("first_construction_document_date")
                or row.get("fully_permitted")
                or row.get("filing_date")
                or row.get("dobrundate")
            )
            issuance_dt = _parse_datetime(issuance_str)

            filing_str = (
                first_mapped(row, field_map, "filing_date")
                or row.get("filed_date")
                or row.get("application_start_date")
                or row.get("filing_date")
                or row.get("submitted_date")
            )
            filing_dt = _parse_datetime(filing_str)

            # Borough / Neighborhood / District / Community Area
            borough_val = (
                first_mapped(row, field_map, "borough")
                or row.get("neighborhoods_analysis_boundaries")
                or row.get("analysis_neighborhood")
                or row.get("neighborhood")
                or row.get("supervisor_district")
                or row.get("borough")
            )
            if not borough_val and row.get("community_area") is not None:
                borough_val = str(row["community_area"])
            elif not borough_val and row.get("community_areas") is not None:
                borough_val = str(row["community_areas"])

            # Street address
            street_parts = [
                row.get("street_direction"),
                row.get("street_number_sfx"),
                row.get("street_name"),
                row.get("street_suffix"),
                row.get("street_type"),
            ]
            combined_street = " ".join(str(p).strip() for p in street_parts if p and str(p).strip())
            address_street = (
                combined_street
                or first_mapped(row, field_map, "address_street")
                or row.get("street_direction_name")
                or row.get("street_name")
                or row.get("address")
                or None
            )
            address_num = str(row.get("street_number") or row.get("house__") or row.get("house_number") or "") or None

            bbl = first_mapped(row, field_map, "bbl") or row.get("bbl")

            zipcode = str(
                first_mapped(row, field_map, "zipcode")
                or row.get("zip_code")
                or row.get("zipcode")
                or row.get("postcode")
                or row.get("zip")
                or ""
            )

            proposed_units = (
                first_mapped(row, field_map, "proposed_units")
                or row.get("proposed_units")
                or row.get("proposed_dwelling_units")
            )
            existing_units = (
                first_mapped(row, field_map, "existing_units")
                or row.get("existing_units")
                or row.get("existing_dwelling_units")
            )
            proposed_stories = (
                first_mapped(row, field_map, "proposed_stories")
                or row.get("proposed_stories")
                or row.get("proposed_no_of_stories")
                or row.get("number_of_stories")
            )

            source_neighborhood = str(borough_val) if borough_val is not None else None
            from src.spatial.geo_utils import get_division_for_coordinate
            resolved_borough = get_division_for_coordinate(lat, lng, city_id=resolved_city) or source_neighborhood

            return PermitEvent(
                city_id=resolved_city,
                job_id=job_id,
                job_type=job_type,
                borough=resolved_borough,
                source_neighborhood=source_neighborhood,
                block=str(row.get("block")) if row.get("block") else None,
                lot=str(row.get("lot")) if row.get("lot") else None,
                bbl=str(bbl) if bbl else None,
                address_street=address_street,
                address_num=address_num,
                zipcode=zipcode,
                latitude=lat,
                longitude=lng,
                estimated_cost=cost,
                proposed_dwelling_units=int(proposed_units) if proposed_units else None,
                existing_dwelling_units=int(existing_units) if existing_units else None,
                proposed_stories=int(proposed_stories) if proposed_stories else None,
                filing_date=filing_dt,
                issuance_date=issuance_dt,
                status=(
                    first_mapped(row, field_map, "status")
                    or row.get("current_status")
                    or row.get("job_status")
                    or row.get("status")
                    or "ISSUED"
                ),
                h3_res7=h3_res["h3_res7"],
                h3_res8=h3_res["h3_res8"],
                h3_res9=h3_res["h3_res9"],
                ingested_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.warning("Error parsing permit row: %s", e)
            return None

    def run_stream(self, city_id: str = "nyc", limit: int = 5000, where_clause: str | None = None):
        """Fetch permit records and stream them into Kafka topic."""
        from src.spatial.city_registry import (
            CityId,
            FeedType,
            get_dataset,
            normalize_city,
        )
        cid = normalize_city(city_id) or CityId.NYC
        spec = get_dataset(cid, FeedType.PERMITS)
        endpoint = spec.endpoint
        client = self._client_for(spec.platform)
        from src.producers.acquisition import AcquisitionSpec, build_adapter_request

        client_kwargs = build_adapter_request(spec.platform, AcquisitionSpec.from_dataset_spec(spec))

        logger.info("Starting %s DOB Permits Ingestion Stream (limit=%d)...", cid.value.upper(), limit)
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
                    key = f"{event.city_id}:{event.job_id}"
                    self.producer.produce(
                        topic=settings.topic_permits,
                        key=key,
                        payload=event,
                    )
                    records_streamed += 1

        self.producer.flush()
        logger.info("%s DOB Ingestion completed. Total streamed: %d records.", cid.value.upper(), records_streamed)
        return records_streamed


if __name__ == "__main__":
    from src.spatial.city_registry import ALIASES
    parser = argparse.ArgumentParser(description="DOB Permits Kafka Producer")
    parser.add_argument(
        "--city",
        type=str,
        default="nyc",
        choices=list(ALIASES.keys()),
        help="City identifier",
    )
    parser.add_argument("--limit", type=int, default=1000, help="Maximum records to ingest")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    producer = DOBPermitsProducer()
    producer.run_stream(city_id=args.city, limit=args.limit)
