"""Street-cut / utility permit feeds ingestion producer (US-81).

Ingests street-closure records from Chicago's CDOT feed (``jdis-5sry``, native
coordinates) and streams them to the ``raw.municipal.street_cut`` topic as a
**disruption context signal** — construction-adjacent disruption and utility
reinvestment show up here before building permits do.

Ablation rule (US-72): this feed is ingested for a separate "disruption index"
context feature. Nothing here feeds the LIMS score.

NYC's DOT street-construction permits (``tqtj-sjs8``) are parsed for their
shape but stay **unregistered**: current rows are address-only (the ``wkt``
State-Plane geometry exists only on 2016-2023 rows), so they cannot produce H3
events until a geocoding capability lands (same blocker as LA crime / Sacramento
permits).
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
from src.schemas.models import StreetCutEvent
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
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%Y%m%d",
        ):
            try:
                return datetime.strptime(val.strip(), fmt).replace(tzinfo=UTC)
            except ValueError:
                pass
    return None


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class StreetCutPermitsProducer:
    """Ingests street-cut / street-closure records to the street_cut topic."""

    def __init__(self, bootstrap_servers: str | None = None):
        schema_path = Path(__file__).parent.parent / "schemas" / "avro" / "street_cut_event.avsc"
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
                f"platform {platform!r} has no client on this producer "
                f"(available: {available}); wire it before registering the spec"
            )
        return client

    def _chicago_row(self, row: dict[str, Any]) -> StreetCutEvent | None:
        """Parse a Chicago CDOT street-closure row (``jdis-5sry``)."""
        lat_raw = row.get("latitude") or row.get("lat")
        lng_raw = row.get("longitude") or row.get("lng")
        if not lat_raw or not lng_raw:
            loc = row.get("location") or {}
            if isinstance(loc, dict) and isinstance(loc.get("coordinates"), list):
                lng_raw = loc["coordinates"][0]
                lat_raw = loc["coordinates"][1]
        lat = _as_float(lat_raw)
        lng = _as_float(lng_raw)
        if lat is None or lng is None or (lat == 0.0 and lng == 0.0):
            return None

        h3_res = self.spatial_indexer.get_multi_res_hierarchy(lat, lng)

        permit_id = str(
            row.get("applicationnumber")
            or row.get("uniquekey")
            or row.get("id")
            or ""
        ).strip()
        if not permit_id:
            return None

        street_name = (
            row.get("streetname")
            or row.get("street")
            or row.get("location_description")
        )
        address = None
        if street_name and (row.get("streetnumberfrom") or row.get("direction") or row.get("suffix")):
            address = (
                f"{row.get('streetnumberfrom', '')} "
                f"{row.get('direction', '')} {street_name} {row.get('suffix', '')}".strip()
            )

        return StreetCutEvent(
            city_id="chicago",
            permit_id=permit_id,
            permit_type=str(row.get("applicationtype") or "Unknown"),
            work_type=row.get("worktypedescription") or row.get("worktype"),
            status=row.get("applicationstatus") or row.get("currentmilestone"),
            street_name=street_name,
            address=address or street_name,
            latitude=lat,
            longitude=lng,
            issued_date=_parse_datetime(row.get("applicationissueddate")),
            start_date=_parse_datetime(row.get("applicationstartdate")),
            end_date=_parse_datetime(row.get("applicationenddate")),
            fees=_as_float(row.get("totalfees")),
            h3_res7=h3_res["h3_res7"],
            h3_res8=h3_res["h3_res8"],
            h3_res9=h3_res["h3_res9"],
            ingested_at=datetime.now(UTC),
        )

    def _nyc_row(self, row: dict[str, Any]) -> StreetCutEvent | None:
        """Parse an NYC DOT street-construction row (``tqtj-sjs8``).

        Current rows are address-only: the ``wkt``/``locationgeometry``
        State-Plane geometry exists only on 2016-2023 rows and there is no
        geocoder in the pipeline, so this returns None (dropped) unless a
        geographic point appears. Kept for the shape so geocoding can unlock
        it without producer surgery.
        """
        lat_raw = row.get("latitude") or row.get("lat")
        lng_raw = row.get("longitude") or row.get("lng")
        if not lat_raw or not lng_raw:
            return None
        lat = _as_float(lat_raw)
        lng = _as_float(lng_raw)
        if lat is None or lng is None or (lat == 0.0 and lng == 0.0):
            return None

        h3_res = self.spatial_indexer.get_multi_res_hierarchy(lat, lng)

        street_name = (
            row.get("onstreetname")
            or row.get("fromstreetname")
            or row.get("tostreetname")
        )
        address = (
            f"{row.get('permithousenumber', '')} {street_name}".strip()
            if row.get("permithousenumber") and street_name
            else street_name
        )

        return StreetCutEvent(
            city_id="nyc",
            permit_id=str(row.get("permitnumber") or row.get("applicationtrackingid") or "").strip(),
            permit_type=str(row.get("permittypedesc") or "Unknown"),
            work_type=row.get("permitpurposecomments"),
            status=row.get("permitstatusshortdesc") or row.get("permitstatusid"),
            street_name=street_name,
            address=address,
            latitude=lat,
            longitude=lng,
            issued_date=_parse_datetime(row.get("permitissuedate")),
            start_date=_parse_datetime(row.get("issuedworkstartdate")),
            end_date=_parse_datetime(row.get("issuedworkenddate")),
            h3_res7=h3_res["h3_res7"],
            h3_res8=h3_res["h3_res8"],
            h3_res9=h3_res["h3_res9"],
            ingested_at=datetime.now(UTC),
        )

    def parse_socrata_row(self, row: dict[str, Any], city_id: str | None = None) -> StreetCutEvent | None:
        """Convert a raw street-cut/closure row to a strongly-typed StreetCutEvent."""
        try:
            if city_id is not None and "nyc" in str(city_id).lower():
                return self._nyc_row(row)
            return self._chicago_row(row)
        except Exception as e:
            logger.warning("Error parsing street-cut row: %s", e)
            return None

    def run_stream(self, city_id: str = "chicago", limit: int = 5000, where_clause: str | None = None):
        """Fetch street-closure records and stream them into the street_cut topic."""
        from src.spatial.city_registry import (
            CityId,
            FeedType,
            get_dataset,
            normalize_city,
        )
        cid = normalize_city(city_id) or CityId.CHICAGO
        spec = get_dataset(cid, FeedType.STREET_CUT)
        endpoint = spec.endpoint
        client = self._client_for(spec.platform)
        from src.producers.acquisition import AcquisitionSpec, build_adapter_request

        client_kwargs = build_adapter_request(spec.platform, AcquisitionSpec.from_dataset_spec(spec))

        logger.info("Starting %s Street-Cut Stream (limit=%d)...", cid.value.upper(), limit)
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
                    key = f"{event.city_id}:{event.permit_id}"
                    self.producer.produce(
                        topic=settings.topic_street_cut,
                        key=key,
                        payload=event,
                    )
                    records_streamed += 1

        self.producer.flush()
        logger.info("%s Street-Cut Ingestion completed. Total streamed: %d records.", cid.value.upper(), records_streamed)
        return records_streamed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Street-Cut Permits Kafka Producer")
    parser.add_argument("--city", type=str, default="chicago", choices=["chicago", "nyc"])
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    producer = StreetCutPermitsProducer()
    producer.run_stream(city_id=args.city, limit=args.limit)