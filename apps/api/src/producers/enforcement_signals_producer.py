"""Boston signal-supplement producers (US-209): Building/Property Violations + Food Inspections.

Both are CKAN feeds on data.boston.gov with direct coordinate columns (lat/long
for violations; a "(lat, lng)" location tuple for inspections). Each producer
streams to its own topic and is subject to the US-72 ablation rule before any
LIMS use.
"""

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
from src.schemas.models import ViolationEvent, InspectionEvent
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)


def _parse_location_tuple(raw: Any) -> tuple[float, float] | None:
    """Parse a ``(lat, lng)`` string tuple returned by the CKAN DataStore."""
    if not raw:
        return None
    cleaned = str(raw).strip().strip("()").replace(" ", "")
    parts = cleaned.split(",")
    if len(parts) != 2:
        return None
    try:
        lat = float(parts[0])
        lng = float(parts[1])
        if lat == 0.0 and lng == 0.0:
            return None
        return lat, lng
    except (ValueError, TypeError):
        return None


class ViolationsProducer:
    """Ingests Boston Building & Property Violations (CKAN) to Kafka.

    Direct lat/long, status_dttm watermark, case_no id. Follows the
    CrimeIncidentsProducer pattern for interlock-gate compatibility."""

    def __init__(self, bootstrap_servers: str | None = None):
        schema_path = Path(__file__).parent.parent / "schemas" / "avro" / "violation_event.avsc"
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
                f"platform {platform!r} has no client on ViolationsProducer "
                f"(available: {available})"
            )
        return client

    def parse_row(self, row: dict[str, Any], city_id: str | None = None) -> ViolationEvent | None:
        try:
            from src.producers.field_maps import first_mapped, resolve_field_map
            from src.spatial.city_registry import FeedType, normalize_city

            if city_id is not None:
                norm_c = normalize_city(city_id)
                resolved_city = norm_c.value if norm_c else city_id.lower()
            else:
                resolved_city = "boston"

            field_map = resolve_field_map(resolved_city, FeedType.VIOLATIONS)

            violation_id = str(
                first_mapped(row, field_map, "violation_id")
                or row.get("case_no")
                or ""
            ).strip()
            if not violation_id:
                return None

            lat_raw = first_mapped(row, field_map, "latitude") or row.get("latitude")
            lng_raw = first_mapped(row, field_map, "longitude") or row.get("longitude")
            if not lat_raw or not lng_raw:
                return None
            lat = float(lat_raw)
            lng = float(lng_raw)
            if lat == 0.0 and lng == 0.0:
                return None

            h3_res = self.spatial_indexer.get_multi_res_hierarchy(lat, lng)
            status_date = (
                first_mapped(row, field_map, "status_date")
                or row.get("status_dttm")
                or row.get("opened_date")
            )

            return ViolationEvent(
                city_id=resolved_city,
                violation_id=violation_id,
                code=str(
                    first_mapped(row, field_map, "code")
                    or row.get("code")
                    or row.get("case_type")
                    or ""
                ),
                status=str(first_mapped(row, field_map, "status") or row.get("status") or "") or None,
                description=str(
                    first_mapped(row, field_map, "description")
                    or row.get("description")
                    or row.get("case_type")
                    or ""
                ) or None,
                borough=str(first_mapped(row, field_map, "borough") or row.get("ward") or row.get("city") or "") or None,
                address=str(
                    first_mapped(row, field_map, "address")
                    or row.get("violation_street")
                    or row.get("address")
                    or (
                        f"{row.get('house_number', '')} {row.get('street_name', '')}".strip()
                        if row.get("house_number") or row.get("street_name")
                        else None
                    )
                ) or None,
                zipcode=str(
                    first_mapped(row, field_map, "zipcode")
                    or row.get("zip")
                    or row.get("zip_code")
                    or row.get("violation_zip")
                    or ""
                ) or None,
                latitude=lat,
                longitude=lng,
                status_date=_parse_datetime(status_date),
                h3_res7=h3_res["h3_res7"],
                h3_res8=h3_res["h3_res8"],
                h3_res9=h3_res["h3_res9"],
                ingested_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.warning("Error parsing violation row: %s", e)
            return None

    def run_stream(self, city_id: str = "boston", limit: int = 5000, where_clause: str | None = None):
        from src.spatial.city_registry import CityId, FeedType, get_dataset, normalize_city
        from src.producers.acquisition import AcquisitionSpec, build_adapter_request

        cid = normalize_city(city_id) or CityId.BOSTON
        spec = get_dataset(cid, FeedType.VIOLATIONS)
        endpoint = spec.endpoint
        client = self._client_for(spec.platform)
        client_kwargs = build_adapter_request(spec.platform, AcquisitionSpec.from_dataset_spec(spec))

        logger.info("Starting %s Violations Stream (limit=%d)...", cid.value.upper(), limit)
        count = 0
        for batch in client.paginate(endpoint_url=endpoint, **client_kwargs, where_clause=where_clause, batch_size=1000, max_records=limit):
            for row in batch:
                event = self.parse_row(row, city_id=cid.value)
                if event:
                    key = f"{event.city_id}:{event.violation_id}"
                    self.producer.produce(topic=settings.topic_violations, key=key, payload=event)
                    count += 1
        self.producer.flush()
        logger.info("%s Violations complete: %d records.", cid.value.upper(), count)
        return count


class InspectionsProducer:
    """Ingests Boston Food Establishment Inspections (CKAN) to Kafka.

    `location` is a ``(lat, lng)`` string tuple; licenseno id; status_date
    watermark. Follows the CrimeIncidentsProducer pattern."""

    def __init__(self, bootstrap_servers: str | None = None):
        schema_path = Path(__file__).parent.parent / "schemas" / "avro" / "inspection_event.avsc"
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
                f"platform {platform!r} has no client on InspectionsProducer "
                f"(available: {available})"
            )
        return client

    def parse_row(self, row: dict[str, Any], city_id: str | None = None) -> InspectionEvent | None:
        try:
            from src.producers.field_maps import first_mapped, resolve_field_map
            from src.spatial.city_registry import FeedType, normalize_city

            if city_id is not None:
                norm_c = normalize_city(city_id)
                resolved_city = norm_c.value if norm_c else city_id.lower()
            else:
                resolved_city = "boston"

            field_map = resolve_field_map(resolved_city, FeedType.INSPECTIONS)

            inspection_id = str(
                first_mapped(row, field_map, "inspection_id")
                or row.get("licenseno")
                or row.get("property_id")
                or ""
            ).strip()
            if not inspection_id:
                return None

            lat, lng = None, None
            lat_raw = first_mapped(row, field_map, "latitude") or row.get("latitude")
            lng_raw = first_mapped(row, field_map, "longitude") or row.get("longitude")
            if lat_raw is not None and lng_raw is not None:
                try:
                    lat, lng = float(lat_raw), float(lng_raw)
                except (ValueError, TypeError):
                    lat, lng = None, None
            if lat is None or lng is None:
                raw_loc = row.get("location")
                if raw_loc:
                    parsed = _parse_location_tuple(raw_loc)
                    if parsed:
                        lat, lng = parsed
            if lat is None or lng is None:
                return None
            if lat == 0.0 and lng == 0.0:
                return None

            h3_res = self.spatial_indexer.get_multi_res_hierarchy(lat, lng)
            issued_date = first_mapped(row, field_map, "issued_date") or row.get("issdttm")
            result_date = first_mapped(row, field_map, "result_date") or row.get("resultdttm") or row.get("status_date")

            return InspectionEvent(
                city_id=resolved_city,
                inspection_id=inspection_id,
                business_name=str(
                    first_mapped(row, field_map, "business_name") or row.get("businessname") or row.get("dba") or ""
                ) or None,
                license_category=str(
                    first_mapped(row, field_map, "license_category") or row.get("licensecat") or ""
                ) or None,
                license_status=str(
                    first_mapped(row, field_map, "license_status") or row.get("licstatus") or row.get("action") or ""
                ) or None,
                result=str(first_mapped(row, field_map, "result") or row.get("result") or row.get("grade") or "") or None,
                violation_level=str(
                    first_mapped(row, field_map, "violation_level") or row.get("viol_level") or row.get("critical_flag") or ""
                ) or None,
                violation_desc=str(
                    first_mapped(row, field_map, "violation_desc") or row.get("violdesc") or row.get("violation_description") or ""
                ) or None,
                borough=str(first_mapped(row, field_map, "borough") or row.get("city") or row.get("boro") or "") or None,
                address=str(
                    first_mapped(row, field_map, "address")
                    or row.get("address")
                    or (
                        f"{row.get('building', '')} {row.get('street', '')}".strip()
                        if row.get("building") or row.get("street")
                        else None
                    )
                ) or None,
                zipcode=str(first_mapped(row, field_map, "zipcode") or row.get("zip") or row.get("zipcode") or "") or None,
                latitude=lat,
                longitude=lng,
                issued_date=_parse_datetime(issued_date),
                result_date=_parse_datetime(result_date),
                h3_res7=h3_res["h3_res7"],
                h3_res8=h3_res["h3_res8"],
                h3_res9=h3_res["h3_res9"],
                ingested_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.warning("Error parsing inspection row: %s", e)
            return None

    def run_stream(self, city_id: str = "boston", limit: int = 5000, where_clause: str | None = None):
        from src.spatial.city_registry import CityId, FeedType, get_dataset, normalize_city
        from src.producers.acquisition import AcquisitionSpec, build_adapter_request

        cid = normalize_city(city_id) or CityId.BOSTON
        spec = get_dataset(cid, FeedType.INSPECTIONS)
        endpoint = spec.endpoint
        client = self._client_for(spec.platform)
        client_kwargs = build_adapter_request(spec.platform, AcquisitionSpec.from_dataset_spec(spec))

        logger.info("Starting %s Inspections Stream (limit=%d)...", cid.value.upper(), limit)
        count = 0
        for batch in client.paginate(endpoint_url=endpoint, **client_kwargs, where_clause=where_clause, batch_size=1000, max_records=limit):
            for row in batch:
                event = self.parse_row(row, city_id=cid.value)
                if event:
                    key = f"{event.city_id}:{event.inspection_id}"
                    self.producer.produce(topic=settings.topic_inspections, key=key, payload=event)
                    count += 1
        self.producer.flush()
        logger.info("%s Inspections complete: %d records.", cid.value.upper(), count)
        return count


def _parse_datetime(val: Any) -> datetime | None:
    """Parse various ISO and municipal date formats into a timezone-aware datetime."""
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
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(val_clean, fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
    return None


if __name__ == "__main__":
    import argparse
    from src.spatial.city_registry import ALIASES
    parser = argparse.ArgumentParser(description="Boston Signal Supplement Producer (US-209)")
    parser.add_argument("--city", type=str, default="boston", choices=list(ALIASES.keys()))
    parser.add_argument("--signal", type=str, default="violations", choices=["violations", "inspections"])
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    producer_cls = ViolationsProducer if args.signal == "violations" else InspectionsProducer
    producer = producer_cls()
    producer.run_stream(city_id=args.city, limit=args.limit)