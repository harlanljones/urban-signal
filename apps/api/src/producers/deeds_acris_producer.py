"""NYC ACRIS, Cook County/Chicago, San Francisco, Denver, Cincinnati, Columbus, Pittsburgh & MD SDAT (Baltimore/Montgomery/Prince George's) Deeds Ingestion Stream Producer."""

import argparse
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from src.config import settings
from src.producers.base_producer import BaseKafkaProducer
from src.producers.arcgis_client import ArcGISClient
from src.producers.carto_client import CartoClient
from src.producers.ckan_client import CkanClient
from src.producers.csv_client import CSVClient
from src.producers.socrata_client import SocrataClient
from src.schemas.models import DeedEvent
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)


def _parse_datetime(val: Any, spec: Any = None) -> Optional[datetime]:
    """Parse various ISO and common municipal date formats into a timezone-aware datetime.

    Numeric coercion (year or compact YYYYMMDD) is only attempted for rows
    whose feed carries a registered DatasetSpec. Unregistered candidate feeds
    (for example Denver's un-landed sales table) must not silently fabricate a
    date from a raw integer watermark value, so they fall through to the
    caller's now() fallback instead.
    """
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, (int, float)) and spec is not None:
        # Treat 4-digit numbers as years
        if 1900 <= int(val) <= 2100:
            return datetime(int(val), 1, 1, tzinfo=timezone.utc)
        # ArcGIS assessor tables commonly expose calendar dates as compact
        # numeric YYYYMMDD values (for example, SALEDATE=20260801).
        compact = str(int(val))
        if len(compact) == 8:
            try:
                return datetime.strptime(compact, "%Y%m%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
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
            "%Y.%m.%d",
            "%Y",
        ):
            try:
                return datetime.strptime(val.strip(), fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
    return None


def _to_int(val: Any) -> int | None:
    """Coerce a CSV cell into an int, tolerating float-like and blank values."""
    if val is None or str(val).strip() == "":
        return None
    try:
        return int(float(str(val)))
    except (ValueError, TypeError):
        return None


def _compose_hamilton_sale_date(row: dict[str, Any]) -> str | None:
    """Compose ``YYYY-MM-DD`` from Hamilton County's split sale-date columns.

    The Auditor CSV ships ``MonthSale``/``DaySale``/``YearSale`` as separate
    integer cells with no single sale-date column (US-126). Returns ``None``
    so the production chain falls through to its existing date handling when
    any of the three is missing or unparseable.
    """
    year = _to_int(row.get("yearsale"))
    month = _to_int(row.get("monthsale"))
    day = _to_int(row.get("daysale"))
    if not (year and month and day and 1900 <= year <= 2100):
        return None
    try:
        return date(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _parse_wkt_point(value: Any) -> tuple[float | None, float | None]:
    """Parse a WKT ``POINT (x y)`` string into ``(lng, lat)`` or ``(None, None)``.

    MD SDAT real-property rows (US-128) expose their ``point`` column over
    Socrata JSON as a WKT string ``"POINT (-76.62 39.31)"`` in WGS84 — the
    first coordinate is longitude, matching ``geo_utils.point_to_wkt``. Returns
    ``(None, None)`` for non-POINT/column values so the caller's existing null
    coordinate handling is unchanged.
    """
    if not isinstance(value, str):
        return None, None
    text = value.strip()
    upper = text.upper()
    if not upper.startswith("POINT") or "(" not in text or ")" not in text:
        return None, None
    inner = text[text.find("(") + 1 : text.rfind(")")].strip()
    parts = inner.split()
    if len(parts) < 2:
        return None, None
    try:
        lng = float(parts[0])
        lat = float(parts[1])
    except (ValueError, TypeError):
        return None, None
    return lng, lat


class DeedsACRISProducer:
    """Ingests NYC ACRIS, Cook County/Chicago, San Francisco, Denver,
    Cincinnati/Hamilton County, Columbus/Franklin County, Pittsburgh/WPRDC,
    and MD SDAT (Baltimore/Montgomery/Prince George's) property deeds
    and assessor records."""

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
        self.ckan = CkanClient()
        self.csv = CSVClient()
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
            elif "conveyancenumber" in row and "propertynumber" in row:
                # Hamilton County Auditor (Cincinnati) property-transfers CSV
                # (US-126): static file with ConveyanceNumber + PropertyNumber.
                resolved_city = "cincinnati"
            elif "PARCELID" in row and ("OWN1" in row or "OWNERNME1" in row):
                # Franklin County Auditor (Columbus) ArcGIS sales points
                # (US-127): all-uppercase schema; the effective id key is
                # PARCELID (+OBJECTID) because Instrument_Number is null
                # layer-wide.
                resolved_city = "columbus"
            elif "PARID" in row and "DEEDBOOK" in row:
                # WPRDC Allegheny County property-sale transactions (Pittsburgh
                # deeds, US-129): CKAN datastore, all-uppercase schema. No
                # lat/lng on the wire (address-only/PARID-only) — the deeds
                # producer tolerates null coordinates (Cook County precedent).
                resolved_city = "pittsburgh"
            elif "account_id_mdp_field_acctid" in row:
                # MD SDAT real-property assessment snapshot (US-128) shared by
                # Baltimore/Montgomery/Prince George's. All three counties carry
                # the identical schema; autodetect distinguishes them by the
                # county_name column (defaulting to baltimore when absent).
                county = str(row.get("county_name_mdp_field_cntyname", "")).lower()
                if "montgomery" in county:
                    resolved_city = "montgomery"
                elif "prince" in county or "george" in county:
                    resolved_city = "prince_georges"
                else:
                    resolved_city = "baltimore"
            else:
                resolved_city = "nyc"

            from src.producers.field_maps import first_mapped, resolve_field_map

            field_map = resolve_field_map(resolved_city, FeedType.DEEDS)

            # Resolve the registered DatasetSpec for this feed (if any). The
            # flattened spec carries the geocode/date-parsing flags directly;
            # unregistered candidate feeds (Denver's not-yet-landed sales table)
            # intentionally resolve to None so neither numeric date coercion nor
            # the geocode hook is invoked.
            spec = None
            try:
                cid = normalize_city(resolved_city)
                if cid is not None:
                    spec = get_dataset(cid, FeedType.DEEDS)
            except Exception:
                spec = None

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
                or row.get("Instrument_Number")
                or row.get("PARCELID")
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
                    or row.get("mappable_latitude_and_longitude")
                    or {}
                )
                if isinstance(loc, dict):
                    lat_raw = loc.get("latitude") or loc.get("lat") or (
                        loc.get("coordinates", [None, None])[1] if "coordinates" in loc else None
                    )
                    lng_raw = loc.get("longitude") or loc.get("lng") or (
                        loc.get("coordinates", [None, None])[0] if "coordinates" in loc else None
                    )
                elif isinstance(loc, str):
                    # MD SDAT (US-128) point column is a WKT string over Socrata
                    # JSON: "POINT (lng lat)" in WGS84 (see _parse_wkt_point).
                    lng_wkt, lat_wkt = _parse_wkt_point(loc)
                    lat_raw = lat_raw if lat_raw else lat_wkt
                    lng_raw = lng_raw if lng_raw else lng_wkt

            if not lat_raw or not lng_raw:
                # Address-only deed feeds can opt into ADR-0004 geocoding via a
                # direct ``needs_geocode`` declaration on their DatasetSpec. The
                # geocode hook is only reached when the feed actually declares
                # it, so feeds without a registered spec (or without the flag)
                # remain lossless and coordinate-less.
                if spec is not None and spec.needs_geocode:
                    from src.spatial.geocoder import geocode_row_if_declared

                    addr_candidate = (
                        first_mapped(row, field_map, "address_street")
                        or row.get("property_address")
                        or row.get("street_address")
                        or row.get("address")
                    )
                    resolved = geocode_row_if_declared(resolved_city, "deeds", addr_candidate)
                    if resolved is not None:
                        lat_raw, lng_raw = resolved

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

            recorded_str = first_mapped(row, field_map, "recorded_date")
            if not recorded_str and resolved_city == "cincinnati":
                # US-126: Hamilton County Auditor splits the sale date across
                # three int columns (YearSale/MonthSale/DaySale) with no single
                # sale-date column, so compose it before the generic chains.
                recorded_str = _compose_hamilton_sale_date(row)
            recorded_str = recorded_str or (
                row.get("recording_date")
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
            recorded_dt = _parse_datetime(recorded_str, spec) or datetime.now(timezone.utc)

            bbl_val = str(
                first_mapped(row, field_map, "bbl")
                or row.get("parcel_number")
                or row.get("block_and_lot_number")
                or row.get("bbl")
                or row.get("pin")
                or row.get("PIN")
                or row.get("property_index_number")
                or row.get("PARCELID")
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
                or row.get("OWNERNME1")
            )
            party2 = (
                first_mapped(row, field_map, "party2_grantee")
                or row.get("buyer")
                or row.get("buyername")
                or row.get("buyer_name")
                or row.get("party2_grantee")
                or row.get("party2_type")
                or row.get("grantee")
                or row.get("OWN1")
                or row.get("OWN2")
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
        from src.producers.acquisition import AcquisitionSpec, build_adapter_request

        client_kwargs = build_adapter_request(spec.platform, AcquisitionSpec.from_dataset_spec(spec))

        logger.info("Starting %s Deeds Ingestion Stream (limit=%d)...", cid.value.upper(), limit)
        records_streamed = 0
        parcel_join = spec.parcel_join
        parcel_centroids: Dict[str, tuple[float, float]] = {}

        for batch in client.paginate(
            endpoint_url=endpoint,
            **client_kwargs,
            where_clause=where_clause,
            batch_size=1000,
            max_records=limit,
        ):
            if parcel_join:
                join_key = parcel_join["join_key"]
                join_values = [row.get(join_key) for row in batch if row.get(join_key)]
                parcel_centroids.update(
                    client.fetch_centroid_index(
                        endpoint_url=parcel_join["parcel_layer"],
                        join_key=join_key,
                        join_values=join_values,
                    )
                )
            for row in batch:
                enriched_row = row
                if parcel_join:
                    join_value = ArcGISClient._normalize_join_value(row.get(parcel_join["join_key"]))
                    centroid = parcel_centroids.get(join_value)
                    if centroid:
                        enriched_row = dict(row)
                        enriched_row.setdefault("latitude", centroid[0])
                        enriched_row.setdefault("longitude", centroid[1])
                event = self.parse_socrata_row(enriched_row, city_id=cid.value)
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
