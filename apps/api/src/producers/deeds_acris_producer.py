"""NYC ACRIS & Cook County/Chicago Deeds and Commercial Mortgages Ingestion Stream Producer."""

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
from src.schemas.models import DeedEvent
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)


def _parse_datetime(val: Any) -> Optional[datetime]:
    """Parse various ISO and common municipal date formats into a timezone-aware datetime."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, (int, float)):
        # Treat 4-digit numbers as years
        if 1900 <= int(val) <= 2100:
            return datetime(int(val), 1, 1, tzinfo=timezone.utc)
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
            "%Y",
        ):
            try:
                return datetime.strptime(val.strip(), fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
    return None


class DeedsACRISProducer:
    """Ingests NYC ACRIS, Cook County/Chicago, and San Francisco property deeds and assessor records."""

    def __init__(self, bootstrap_servers: Optional[str] = None):
        schema_path = Path(__file__).parent.parent / "schemas" / "avro" / "deed_event.avsc"
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

    def parse_socrata_row(self, row: Dict[str, Any], city_id: Optional[str] = None) -> Optional[DeedEvent]:
        """Convert raw ACRIS / Cook County / SF Assessor deed record into strongly-typed DeedEvent."""
        try:
            # Determine city_id
            from src.spatial.city_registry import CityId, ALIASES, REGISTRY, FeedType, normalize_city, get_dataset
            if city_id is not None:
                norm_c = normalize_city(city_id)
                resolved_city = norm_c.value if norm_c else city_id.lower()
            elif row.get("city_id"):
                norm_c = normalize_city(row["city_id"])
                resolved_city = norm_c.value if norm_c else str(row["city_id"]).lower()
            elif (
                "parcel_number" in row
                or "block_and_lot_number" in row
                or "assessed_fixtures_value" in row
                or "assessed_improvement_value" in row
                or "assessed_land_value" in row
                or "closed_roll_year" in row
            ):
                resolved_city = "san_francisco"
            elif "ExciseTaxNum" in row or "SalePrice" in row or "Principal_Use" in row:
                # King County ArcGIS parcel sales (PascalCase attribute names).
                resolved_city = "seattle"
            elif "pin" in row or "township" in row or "sale_price" in row or "municipality" in row:
                resolved_city = "chicago"
            else:
                resolved_city = "nyc"

            from src.producers.field_maps import first_mapped, resolve_field_map

            field_map = resolve_field_map(resolved_city, FeedType.DEEDS)

            doc_id = str(
                first_mapped(row, field_map, "doc_id")
                or row.get("ExciseTaxNum")
                or row.get("parcel_number")
                or row.get("block_and_lot_number")
                or row.get("doc_id")
                or row.get("document_id")
                or row.get("doc_number")
                or row.get("document_number")
                or row.get("doc_no")
                or row.get("row_id")
                or row.get("control_number")
                or row.get("id")
                or ""
            ).strip()
            if not doc_id:
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
                or row.get("long")
                or row.get("gis_longitude")
            )
            if not lat_raw or not lng_raw:
                loc = (
                    row.get("the_geom")
                    or row.get("point")
                    or row.get("location")
                    or row.get("georeference")
                    or row.get("shape")
                    or {}
                )
                if isinstance(loc, dict):
                    lat_raw = loc.get("latitude") or loc.get("lat") or (
                        loc.get("coordinates", [None, None])[1] if "coordinates" in loc else None
                    )
                    lng_raw = loc.get("longitude") or loc.get("lng") or (
                        loc.get("coordinates", [None, None])[0] if "coordinates" in loc else None
                    )

            lat = float(lat_raw) if lat_raw is not None else None
            lng = float(lng_raw) if lng_raw is not None else None

            h3_res = {"h3_res7": None, "h3_res8": None, "h3_res9": None}
            if lat is not None and lng is not None:
                h3_res = self.spatial_indexer.get_multi_res_hierarchy(lat, lng)

            doc_type = (
                first_mapped(row, field_map, "doc_type")
                or row.get("property_class_code_definition")
                or row.get("doc_type")
                or row.get("document_type")
                or row.get("type_of_deed")
                or row.get("deed_type")
                or row.get("Property_Type")
                or "DEED"
            ).upper()

            def _parse_val(val: Any) -> float:
                if not val:
                    return 0.0
                if isinstance(val, (int, float)):
                    return float(val)
                try:
                    return float(str(val).replace("$", "").replace(",", "").strip())
                except (ValueError, TypeError):
                    return 0.0

            assessed_fixtures = _parse_val(row.get("assessed_fixtures_value"))
            assessed_improvement = _parse_val(row.get("assessed_improvement_value"))
            assessed_land = _parse_val(row.get("assessed_land_value"))
            assessed_personal = _parse_val(row.get("assessed_personal_property_value"))
            total_assessed_calc = assessed_fixtures + assessed_improvement + assessed_land + assessed_personal

            doc_amount = (
                _parse_val(row.get("total_assessed_value"))
                or _parse_val(row.get("assessed_value"))
                or (total_assessed_calc if total_assessed_calc > 0 else 0.0)
                or _parse_val(first_mapped(row, field_map, "document_amount"))
                or _parse_val(row.get("document_amt"))
                or _parse_val(row.get("doc_amount"))
                or _parse_val(row.get("recorded_amt"))
                or _parse_val(row.get("sale_price"))
                or _parse_val(row.get("SalePrice"))
                or _parse_val(row.get("amount"))
                or _parse_val(row.get("consideration"))
                or 0.0
            )

            recorded_str = (
                first_mapped(row, field_map, "recorded_date")
                or row.get("recording_date")
                or row.get("transfer_date")
                or row.get("sale_date")
                or row.get("assessment_date")
                or row.get("closed_roll_year")
                or row.get("roll_year")
                or row.get("recorded_datetime")
                or row.get("recorded_date")
                or row.get("record_date")
                or row.get("date_recorded")
                or row.get("exec_date")
                or row.get("good_through_date")
                or row.get("SaleDate")
            )
            recorded_dt = _parse_datetime(recorded_str) or datetime.now(timezone.utc)

            bbl_val = str(
                first_mapped(row, field_map, "bbl")
                or row.get("parcel_number")
                or row.get("block_and_lot_number")
                or row.get("bbl")
                or row.get("pin")
                or row.get("PIN")
                or row.get("property_index_number")
                or ""
            ) or None

            block_val = str(row.get("block")) if row.get("block") else None
            lot_val = str(row.get("lot")) if row.get("lot") else None
            if not block_val and row.get("block_and_lot_number"):
                bl_str = str(row["block_and_lot_number"]).strip()
                if len(bl_str) >= 4:
                    block_val = bl_str[:4]
                    lot_val = bl_str[4:]

            borough_val = (
                first_mapped(row, field_map, "borough")
                or row.get("analysis_neighborhood")
                or row.get("neighborhood")
                or row.get("supervisor_district")
                or row.get("borough")
                or row.get("township")
                or row.get("municipality")
                or row.get("city")
            )
            party1 = (
                first_mapped(row, field_map, "party1_grantor")
                or row.get("owner_name")
                or row.get("party1_grantor")
                or row.get("party1_type")
                or row.get("grantor")
                or row.get("seller")
                or row.get("seller_name")
                or row.get("Sellername")
            )
            party2 = (
                first_mapped(row, field_map, "party2_grantee")
                or row.get("buyer")
                or row.get("buyername")
                or row.get("buyer_name")
                or row.get("party2_grantee")
                or row.get("party2_type")
                or row.get("grantee")
            )

            source_neighborhood = str(borough_val) if borough_val is not None else None
            from src.spatial.geo_utils import get_division_for_coordinate
            resolved_borough = get_division_for_coordinate(lat, lng, city_id=resolved_city) or source_neighborhood

            return DeedEvent(
                city_id=resolved_city,
                doc_id=doc_id,
                doc_type=doc_type,
                bbl=bbl_val,
                borough=resolved_borough,
                source_neighborhood=source_neighborhood,
                block=block_val,
                lot=lot_val,
                document_amount=doc_amount,
                recorded_date=recorded_dt,
                party1_grantor=party1,
                party2_grantee=party2,
                latitude=lat,
                longitude=lng,
                h3_res7=h3_res["h3_res7"],
                h3_res8=h3_res["h3_res8"],
                h3_res9=h3_res["h3_res9"],
                ingested_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning("Error parsing deed row: %s", e)
            return None

    def run_stream(self, city_id: str = "nyc", limit: int = 5000, where_clause: Optional[str] = None):
        """Fetch deed records and stream to Kafka topic."""
        from src.spatial.city_registry import REGISTRY, CityId, FeedType, normalize_city, get_dataset
        cid = normalize_city(city_id) or CityId.NYC
        spec = get_dataset(cid, FeedType.DEEDS)
        endpoint = spec.endpoint
        client = self._client_for(spec.platform)
        client_kwargs = {
            k: v for k, v in spec.extra.items() if k in ("order_by", "id_col", "select") and v
        }

        logger.info("Starting %s Deeds Ingestion Stream (limit=%d)...", cid.value.upper(), limit)
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
                    key = f"{event.city_id}:{event.doc_id}"
                    self.producer.produce(
                        topic=settings.topic_deeds,
                        key=key,
                        payload=event,
                    )
                    records_streamed += 1

        self.producer.flush()
        logger.info("%s Deeds Ingestion completed. Total streamed: %d records.", cid.value.upper(), records_streamed)
        return records_streamed


if __name__ == "__main__":
    from src.spatial.city_registry import ALIASES
    parser = argparse.ArgumentParser(description="Deeds Kafka Producer")
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
    producer = DeedsACRISProducer()
    producer.run_stream(city_id=args.city, limit=args.limit)
