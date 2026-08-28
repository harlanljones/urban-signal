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

    def parse_row(self, row: dict[str, Any]) -> ViolationEvent | None:
        try:
            from src.producers.field_maps import first_mapped, resolve_field_map
            from src.spatial.city_registry import FeedType

            violation_id = str(first_mapped(row, {"violation_id": ["case_no"]}, "violation_id") or "").strip()
            if not violation_id:
                return None

            lat_raw = first_mapped(row, {"latitude": ["latitude"]}, "latitude") or row.get("latitude")
            lng_raw = first_mapped(row, {"longitude": ["longitude"]}, "longitude") or row.get("longitude")
            if not lat_raw or not lng_raw:
                return None
            lat = float(lat_raw)
            lng = float(lng_raw)
            if lat == 0.0 and lng == 0.0:
                return None

            h3_res = self.spatial_indexer.get_multi_res_hierarchy(lat, lng)
            status_date = first_mapped(row, {"status_date": ["status_dttm"]}, "status_date") or row.get("status_dttm")

            return ViolationEvent(
                city_id="boston",
                violation_id=violation_id,
                code=str(first_mapped(row, {"code": ["code"]}, "code") or row.get("code", "")),
                status=str(row.get("status", "")) or None,
                description=first_mapped(row, {"description": ["description", "value"]}, "description") or row.get("description"),
                borough=str(row.get("ward", "")) or None,
                address=first_mapped(row, {"address": ["violation_stno", "violation_street"]}, "address") or row.get("violation_street"),
                zipcode=str(row.get("violation_zip", "")) or None,
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
                event = self.parse_row(row)
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

    def parse_row(self, row: dict[str, Any]) -> InspectionEvent | None:
        try:
            inspection_id = str(row.get("licenseno") or row.get("property_id", "")).strip()
            if not inspection_id:
                return None

            lat, lng = None, None
            raw_loc = row.get("location")
            if raw_loc:
                parsed = _parse_location_tuple(raw_loc)
                if parsed:
                    lat, lng = parsed
            if lat is None or lng is None:
                return None

            h3_res = self.spatial_indexer.get_multi_res_hierarchy(lat, lng)
            issued_date = row.get("issdttm")
            result_date = row.get("resultdttm") or row.get("status_date")

            return InspectionEvent(
                city_id="boston",
                inspection_id=inspection_id,
                business_name=str(row.get("businessname", "")) or None,
                license_category=str(row.get("licensecat", "")) or None,
                license_status=str(row.get("licstatus", "")) or None,
                result=str(row.get("result", "")) or None,
                violation_level=str(row.get("viol_level", "")) or None,
                violation_desc=str(row.get("violdesc", "")) or None,
                borough=str(row.get("city", "")) or None,
                address=str(row.get("address", "")) or None,
                zipcode=str(row.get("zip", "")) or None,
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
                event = self.parse_row(row)
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