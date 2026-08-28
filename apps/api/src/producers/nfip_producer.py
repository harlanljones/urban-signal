"""NFIP claims producer for OpenFEMA (US-363 §1.4)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from pathlib import Path

from src.config import settings
from src.producers.base_producer import BaseKafkaProducer
from src.producers.openfema_client import OpenFemaClient, odata_date_filter
from src.schemas.models import ContextObservationEvent, InsuranceLossEvent
from src.spatial.geography_crosswalk import GeographyCrosswalk
from src.spatial.h3_indexer import H3SpatialIndexer


def _float(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return default


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=UTC)
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


class NfipProducer:
    """Convert privacy-safe NFIP claims and county declarations into events."""

    def __init__(self, bootstrap_servers: str | None = None, client: Any = None,
                 crosswalk: GeographyCrosswalk | None = None, indexer: Any = None):
        self.client = client or OpenFemaClient()
        self.nfip = self.client
        # Scheduler wrappers expose the common client surface so the interlock
        # can inspect every producer uniformly. NFIP itself uses OpenFEMA, so
        # this is intentionally a non-operational compatibility attribute.
        self.socrata = None
        self.crosswalk = crosswalk or GeographyCrosswalk()
        self.indexer = indexer or H3SpatialIndexer()
        self.producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=Path(__file__).parent.parent / "schemas" / "avro" / "insurance_loss_event.avsc",
            dlq_topic=settings.topic_dlq,
        )
        self.context_producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            schema_file_path=Path(__file__).parent.parent / "schemas" / "avro" / "context_observation_event.avsc",
            dlq_topic=settings.topic_dlq,
        )

    def parse_claim(self, row: dict[str, Any]) -> tuple[InsuranceLossEvent | None, str | None]:
        event_date = _datetime(row.get("dateOfLoss"))
        if event_date is None:
            return None, "NFIP claim has no parseable dateOfLoss"
        point = self.crosswalk.tract_point(row.get("censusGeoid"))
        geometry_source = "tract_centroid"
        if point is None:
            point = self.crosswalk.zip_point(row.get("reportedZipCode") or row.get("zipCode"))
            geometry_source = "zip_centroid"
        if point is None:
            return None, "NFIP claim has no tract or ZIP geometry"
        city_id = self.crosswalk.city_for_point(point.latitude, point.longitude)
        if city_id is None:
            return None, "NFIP claim geometry is outside registered metros"
        h3 = self.indexer.get_multi_res_hierarchy(point.latitude, point.longitude)
        return InsuranceLossEvent(
            city_id=city_id,
            claim_id=str(row.get("id") or row.get("claimId") or ""),
            event_date=event_date,
            amount_paid_building=_float(row.get("amountPaidOnBuildingClaim"), 0.0) or 0.0,
            amount_paid_contents=_float(row.get("amountPaidOnContentsClaim"), 0.0) or 0.0,
            building_damage_amount=_float(row.get("buildingDamageAmount")),
            flood_event=row.get("floodEvent"),
            rated_flood_zone=row.get("ratedFloodZone"),
            census_geoid=str(row["censusGeoid"]) if row.get("censusGeoid") else None,
            county_code=str(row["countyCode"]) if row.get("countyCode") else None,
            zipcode=str(row["reportedZipCode"] or row["zipCode"]) if row.get("reportedZipCode") or row.get("zipCode") else None,
            state=row.get("state"), borough=None,
            occupancy_type=int(row["occupancyType"]) if row.get("occupancyType") not in (None, "") else None,
            water_depth=_float(row.get("waterDepth")), geometry_source=geometry_source,
            latitude=point.latitude, longitude=point.longitude, **h3,
        ), None

    def run_stream(self, since: Any = None, limit: int | None = None, **_: Any) -> int:
        endpoint = settings.openfema_nfip_claims_endpoint
        where = odata_date_filter("dateOfLoss", since) if since else None
        emitted = 0
        for batch in self.client.paginate(endpoint_url=endpoint, where_clause=where,
                                          order_by="dateOfLoss,id", max_records=limit):
            for row in batch:
                event, reason = self.parse_claim(row)
                if event is None:
                    self.producer.route_to_dlq(settings.topic_insurance_loss, str(row.get("id", "unknown")), row, reason or "invalid claim")
                    continue
                self.producer.produce(settings.topic_insurance_loss, f"{event.city_id}:{event.claim_id}", event)
                emitted += 1
        self.producer.flush()
        return emitted

    def parse_declaration(self, row: dict[str, Any]) -> tuple[ContextObservationEvent | None, str | None]:
        """Turn a county-level declaration into a context observation.

        Declarations have no point geometry and are not insurance-loss events;
        the county Gazetteer centroid supplies a coarse context location.
        """
        state_fips = row.get("fipsStateCode") or row.get("stateFips")
        county_fips = row.get("fipsCountyCode") or row.get("countyFips")
        if state_fips is not None and county_fips is not None:
            fips_text = str(state_fips).zfill(2) + str(county_fips).zfill(3)
        else:
            fips_text = str(row.get("placeCode") or "")
        point = self.crosswalk.county_point(fips_text)
        if point is None:
            return None, "FEMA declaration has no county centroid"
        city_id = self.crosswalk.city_for_point(point.latitude, point.longitude)
        if city_id is None:
            return None, "FEMA declaration county is outside registered metros"
        declaration_date = _datetime(row.get("declarationDate") or row.get("lastRefresh"))
        if declaration_date is None:
            return None, "FEMA declaration has no parseable declarationDate"
        h3 = self.indexer.get_multi_res_hierarchy(point.latitude, point.longitude)
        declaration_id = str(row.get("femaDeclarationString") or row.get("id") or fips_text)
        return ContextObservationEvent(
            city_id=city_id,
            observation_id=f"fema_declaration:{declaration_id}",
            source="fema_declaration",
            asset_id=declaration_id,
            asset_name=row.get("declarationTitle") or row.get("incidentType"),
            metric="declared_disaster",
            value=1.0,
            unit="declaration",
            period_start=declaration_date,
            period_type="day",
            category=row.get("incidentType"),
            latitude=point.latitude,
            longitude=point.longitude,
            **h3,
        ), None

    def run_declarations(self, since: Any = None, limit: int | None = None, **_: Any) -> int:
        """Emit county-level declarations to the context topic, never claims."""
        endpoint = settings.openfema_disaster_declarations_endpoint
        where = odata_date_filter("declarationDate", since) if since else None
        emitted = 0
        for batch in self.client.paginate(
            endpoint_url=endpoint,
            where_clause=where,
            order_by="declarationDate,femaDeclarationString",
            max_records=limit,
        ):
            for row in batch:
                event, reason = self.parse_declaration(row)
                declaration_id = str(row.get("femaDeclarationString") or row.get("id") or "unknown")
                if event is None:
                    self.context_producer.route_to_dlq(
                        settings.topic_context_observations,
                        declaration_id,
                        row,
                        reason or "invalid declaration",
                    )
                    continue
                self.context_producer.produce(
                    settings.topic_context_observations,
                    "event:" + event.city_id + ":" + event.observation_id,
                    event,
                )
                emitted += 1
        self.context_producer.flush()
        return emitted
