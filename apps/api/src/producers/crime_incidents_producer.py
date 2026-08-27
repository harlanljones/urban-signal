"""Crime Incident Feeds Ingestion Producer (CHI / SF / SEA / NYC).

Ingests NIBRS-classified municipal crime incident feeds (US-71) and streams
them to the ``raw.municipal.crime`` topic. Rows carry an ``offense_class``
(PART1 / PART2) so the model stage can drop Part-2 noise before any crime
signal ever reaches LIMS (ablation rule: nothing here feeds the LIMS score).
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
from src.schemas.models import CrimeEvent
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)

# UCR Part-I offenses (serious); everything else is Part-2 noise for signal
# purposes. "Simple Assault" / "Battery" are checked first because they contain
# the "ASSAULT" keyword but are Part-2.
PART1_KEYWORDS = (
    "MURDER",
    "HOMICIDE",
    "MANSLAUGHTER",
    "RAPE",
    "ROBBERY",
    "ARSON",
    "BURGLARY",
    "LARCENY",
    "MOTOR VEHICLE THEFT",
    "VEHICLE THEFT",
    "THEFT",
    "ASSAULT",
)


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


def classify_offense_class(offense_type: str, description: Any = None) -> str:
    """Best-effort UCR Part-1 vs Part-2 classification over offense text."""
    text = f"{offense_type or ''} {description or ''}".upper()
    if "SIMPLE ASSAULT" in text or "BATTERY" in text:
        return "PART2"
    if any(keyword in text for keyword in PART1_KEYWORDS):
        return "PART1"
    return "PART2"


class CrimeIncidentsProducer:
    """Ingests Chicago, SF, Seattle, and NYC crime incident feeds to Kafka."""

    def __init__(self, bootstrap_servers: str | None = None):
        schema_path = Path(__file__).parent.parent / "schemas" / "avro" / "crime_event.avsc"
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
        """Select the paginating client matching a DatasetSpec's platform."""
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

    def parse_socrata_row(self, row: dict[str, Any], city_id: str | None = None) -> CrimeEvent | None:
        """Convert a raw crime incident row to a strongly-typed CrimeEvent."""
        try:
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
                "incident_category" in row
                or "incident_subcategory" in row
                or "cad_number" in row
            ):
                resolved_city = "san_francisco"
            elif "cmplnt_num" in row or "ofns_desc" in row or "law_cat_cd" in row or "boro_nm" in row:
                resolved_city = "nyc"
            elif (
                "offense_id" in row
                or "nibrs_group_a_b" in row
                or "report_number" in row
                or "offense_category" in row
            ):
                resolved_city = "seattle"
            elif "primary_type" in row or "iucr" in row or "case_number" in row or "community_area" in row:
                resolved_city = "chicago"
            else:
                resolved_city = "nyc"

            from src.producers.field_maps import first_mapped, resolve_field_map

            field_map = resolve_field_map(resolved_city, FeedType.CRIME)

            incident_id = str(
                first_mapped(row, field_map, "incident_id")
                or row.get("offense_id")
                or row.get("incident_number")
                or row.get("id")
                or row.get("case_number")
                or row.get("cmplnt_num")
                or row.get("report_number")
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
            )
            if not lat_raw or not lng_raw:
                # Socrata point containers: GeoJSON point.coordinates = [lng, lat],
                # or {latitude, longitude} objects (Chicago location, NYC lat_lon).
                loc = row.get("location") or row.get("lat_lon") or row.get("point") or {}
                if isinstance(loc, dict):
                    if isinstance(loc.get("coordinates"), list):
                        lng_raw = loc["coordinates"][0]
                        lat_raw = loc["coordinates"][1]
                    else:
                        lat_raw = loc.get("latitude") or loc.get("lat")
                        lng_raw = loc.get("longitude") or loc.get("lng")
            if not lat_raw or not lng_raw:
                return None

            lat = float(lat_raw)
            lng = float(lng_raw)
            if lat == 0.0 and lng == 0.0:
                return None

            h3_res = self.spatial_indexer.get_multi_res_hierarchy(lat, lng)

            offense_type = (
                first_mapped(row, field_map, "offense_type")
                or row.get("primary_type")
                or row.get("nibrs_offense_code_description")
                or row.get("incident_category")
                or row.get("ofns_desc")
                or row.get("offense_category")
                or "Unknown"
            )
            description = (
                row.get("description")
                or row.get("incident_subcategory")
                or row.get("incident_description")
                or row.get("offense_sub_category")
                or row.get("pd_desc")
            )

            occurred_str = (
                first_mapped(row, field_map, "occurred_date")
                or row.get("date")
                or row.get("offense_date")
                or row.get("incident_datetime")
                or row.get("cmplnt_fr_dt")
            )
            reported_str = (
                first_mapped(row, field_map, "reported_date")
                or row.get("report_date_time")
                or row.get("report_datetime")
                or row.get("rpt_dt")
            )

            borough_val = (
                first_mapped(row, field_map, "borough")
                or row.get("community_area")
                or row.get("neighborhood")
                or row.get("analysis_neighborhood")
                or row.get("boro_nm")
                or row.get("police_district")
            )
            source_neighborhood = str(borough_val) if borough_val is not None else None
            from src.spatial.geo_utils import get_division_for_coordinate
            resolved_borough = get_division_for_coordinate(lat, lng, city_id=resolved_city) or source_neighborhood

            address = (
                row.get("block")
                or row.get("block_address")
                or row.get("intersection")
                or row.get("loc_of_occur_desc")
            )

            return CrimeEvent(
                city_id=resolved_city,
                incident_id=incident_id,
                offense_type=offense_type,
                offense_class=classify_offense_class(offense_type, description),
                description=description,
                borough=resolved_borough,
                source_neighborhood=source_neighborhood,
                address=address,
                latitude=lat,
                longitude=lng,
                occurred_date=_parse_datetime(occurred_str),
                reported_date=_parse_datetime(reported_str),
                resolution=(
                    row.get("resolution")
                    or row.get("crm_atpt_cptd_cd")
                    or row.get("status")
                ),
                h3_res7=h3_res["h3_res7"],
                h3_res8=h3_res["h3_res8"],
                h3_res9=h3_res["h3_res9"],
                ingested_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.warning("Error parsing crime row: %s", e)
            return None

    def run_stream(self, city_id: str = "nyc", limit: int = 5000, where_clause: str | None = None):
        """Fetch crime incident records and stream them into the crime topic."""
        from src.spatial.city_registry import (
            CityId,
            FeedType,
            get_dataset,
            normalize_city,
        )
        cid = normalize_city(city_id) or CityId.NYC
        spec = get_dataset(cid, FeedType.CRIME)
        endpoint = spec.endpoint
        client = self._client_for(spec.platform)
        from src.producers.acquisition import AcquisitionSpec, build_adapter_request

        client_kwargs = build_adapter_request(spec.platform, AcquisitionSpec.from_dataset_spec(spec))

        logger.info("Starting %s Crime Incident Stream (limit=%d)...", cid.value.upper(), limit)
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
                        topic=settings.topic_crime,
                        key=key,
                        payload=event,
                    )
                    records_streamed += 1

        self.producer.flush()
        logger.info("%s Crime Ingestion completed. Total streamed: %d records.", cid.value.upper(), records_streamed)
        return records_streamed


if __name__ == "__main__":
    from src.spatial.city_registry import ALIASES
    parser = argparse.ArgumentParser(description="Crime Incidents Kafka Producer")
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
    producer = CrimeIncidentsProducer()
    producer.run_stream(city_id=args.city, limit=args.limit)