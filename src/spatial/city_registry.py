"""City and Dataset Registry for Urban Signal.

Provides a unified, centralized registry for all supported metropolitan regions,
geographic boundaries, submarkets, division catalogs, and municipal dataset endpoints.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Protocol, Tuple, Union, runtime_checkable

from src.config import settings
from src.spatial.cities.chicago import (
    CHICAGO_DIVISION_BBOXES,
    CHICAGO_DIVISIONS,
    CHICAGO_METRO_BBOX,
    CHICAGO_SUBMARKETS,
)
from src.spatial.cities.los_angeles import (
    LA_DIVISION_BBOXES,
    LA_DIVISIONS,
    LA_METRO_BBOX,
    LA_SUBMARKETS,
)
from src.spatial.cities.san_francisco import (
    SAN_FRANCISCO_DIVISION_BBOXES,
    SAN_FRANCISCO_DIVISIONS,
    SAN_FRANCISCO_METRO_BBOX,
    SAN_FRANCISCO_SUBMARKETS,
    SF_DIVISION_BBOXES,
    SF_METRO_BBOX,
)
from src.spatial.cities.seattle import (
    SEATTLE_DIVISION_BBOXES,
    SEATTLE_DIVISIONS,
    SEATTLE_METRO_BBOX,
    SEATTLE_SUBMARKETS,
)
from src.spatial.submarkets import (
    NYC_BOROUGHS,
    NYC_BOROUGH_BBOXES,
    NYC_METRO_BBOX,
    NYC_SUBMARKETS,
    BoroughMeta,
    DivisionMeta,
    SubmarketMeta,
)


class CityId(str, Enum):
    """Canonical metropolitan city identifiers."""
    NYC = "nyc"
    CHICAGO = "chicago"
    SAN_FRANCISCO = "san_francisco"
    SEATTLE = "seattle"
    LOS_ANGELES = "los_angeles"


class FeedType(str, Enum):
    """Municipal data feed types."""
    PERMITS = "permits"
    COMPLAINTS_311 = "311"
    SLA = "sla"
    DEEDS = "deeds"


@runtime_checkable
class PaginatingClient(Protocol):
    """Protocol for paginated municipal data extraction across Socrata, CKAN, ArcGIS, etc."""

    def paginate(
        self,
        endpoint_url: str,
        where_clause: Optional[str] = None,
        order_by: str = ":id",
        batch_size: int = 1000,
        max_records: Optional[int] = None,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        ...


@dataclass
class DatasetSpec:
    """Specification for a municipal dataset endpoint and ingestion configuration."""
    endpoint: str
    platform: str = "socrata"  # "socrata", "arcgis", "ckan", etc.
    watermark_col: str = ""
    id_keys: List[str] = field(default_factory=list)
    topic: str = ""
    interval_seconds: float = 300.0
    producer_key: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CityRegistration:
    """Complete registration metadata for a supported metropolitan area."""
    city_id: CityId
    name: str
    state: str
    center: Dict[str, float]
    metro_bbox: Dict[str, float]
    division_bboxes: Dict[str, Dict[str, float]]
    submarkets: Dict[str, SubmarketMeta]
    divisions: Dict[str, BoroughMeta]
    datasets: Dict[FeedType, DatasetSpec]
    job_suffix: str = ""


# Canonical alias lookup mapping all known alias strings to CityId
ALIASES: Dict[str, CityId] = {
    # NYC
    "nyc": CityId.NYC,
    "new_york": CityId.NYC,
    "new-york": CityId.NYC,
    "new york": CityId.NYC,
    "new york city": CityId.NYC,
    "ny": CityId.NYC,

    # Chicago
    "chicago": CityId.CHICAGO,
    "chi": CityId.CHICAGO,
    "cook_county": CityId.CHICAGO,
    "cook-county": CityId.CHICAGO,
    "cook county": CityId.CHICAGO,

    # San Francisco & Bay Area
    "san_francisco": CityId.SAN_FRANCISCO,
    "san-francisco": CityId.SAN_FRANCISCO,
    "san francisco": CityId.SAN_FRANCISCO,
    "sf": CityId.SAN_FRANCISCO,
    "bay_area": CityId.SAN_FRANCISCO,
    "bay-area": CityId.SAN_FRANCISCO,
    "bay area": CityId.SAN_FRANCISCO,
    "sf_bay_area": CityId.SAN_FRANCISCO,
    "sf-bay-area": CityId.SAN_FRANCISCO,
    "sf bay area": CityId.SAN_FRANCISCO,

    # Seattle & King County
    "seattle": CityId.SEATTLE,
    "sea": CityId.SEATTLE,
    "king_county": CityId.SEATTLE,
    "king-county": CityId.SEATTLE,
    "king county": CityId.SEATTLE,
    "puget_sound": CityId.SEATTLE,
    "puget-sound": CityId.SEATTLE,
    "puget sound": CityId.SEATTLE,
    "bellevue": CityId.SEATTLE,

    # Los Angeles & LA County
    "los_angeles": CityId.LOS_ANGELES,
    "los-angeles": CityId.LOS_ANGELES,
    "los angeles": CityId.LOS_ANGELES,
    "la": CityId.LOS_ANGELES,
    "l.a.": CityId.LOS_ANGELES,
    "socal": CityId.LOS_ANGELES,
    "la_county": CityId.LOS_ANGELES,
    "la-county": CityId.LOS_ANGELES,
    "la county": CityId.LOS_ANGELES,
    "long_beach": CityId.LOS_ANGELES,
    "long beach": CityId.LOS_ANGELES,
    "pasadena": CityId.LOS_ANGELES,
    "glendale": CityId.LOS_ANGELES,
    "south_bay": CityId.LOS_ANGELES,
    "san_fernando_valley": CityId.LOS_ANGELES,
}


def normalize_city(city_id: Optional[str]) -> Optional[CityId]:
    """Normalize user-supplied city identifier to canonical CityId Enum or None if unknown."""
    if not city_id:
        return None
    c = str(city_id).strip().lower()
    return ALIASES.get(c, None)


REGISTRY: Dict[CityId, CityRegistration] = {
    CityId.NYC: CityRegistration(
        city_id=CityId.NYC,
        name="New York City",
        state="NY",
        center={"lat": 40.7128, "lng": -74.0060},
        metro_bbox=NYC_METRO_BBOX,
        division_bboxes=NYC_BOROUGH_BBOXES,
        submarkets=NYC_SUBMARKETS,
        divisions=NYC_BOROUGHS,
        job_suffix="",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_dob_endpoint,
                platform="socrata",
                watermark_col="issuance_date",
                id_keys=["job__", "job_number", "job_filing_number", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_311_endpoint,
                platform="socrata",
                watermark_col="created_date",
                id_keys=["unique_key", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_sla_endpoint,
                platform="socrata",
                watermark_col="effectivedate",
                id_keys=["licensepermitid", "legacyserialnumber", "serial_number", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.socrata_deeds_endpoint,
                platform="socrata",
                watermark_col="recorded_datetime",
                id_keys=["document_id", "doc_id", "id"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
            ),
        },
    ),
    CityId.CHICAGO: CityRegistration(
        city_id=CityId.CHICAGO,
        name="Chicago",
        state="IL",
        center={"lat": 41.8781, "lng": -87.6298},
        metro_bbox=CHICAGO_METRO_BBOX,
        division_bboxes=CHICAGO_DIVISION_BBOXES,
        submarkets=CHICAGO_SUBMARKETS,
        divisions=CHICAGO_DIVISIONS,
        job_suffix="chicago",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_chicago_dob_endpoint,
                platform="socrata",
                watermark_col="issue_date",
                id_keys=["id", "permit_", "permit_number"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_chicago_311_endpoint,
                platform="socrata",
                watermark_col="created_date",
                id_keys=["sr_number", "unique_key", "id", "service_request_number"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_chicago_licenses_endpoint,
                platform="socrata",
                watermark_col="date_issued",
                id_keys=["license_id", "account_number", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.socrata_chicago_deeds_endpoint,
                platform="socrata",
                watermark_col="sale_date",
                id_keys=["doc_no", "row_id", "pin"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
            ),
        },
    ),
    CityId.SAN_FRANCISCO: CityRegistration(
        city_id=CityId.SAN_FRANCISCO,
        name="San Francisco Bay Area",
        state="CA",
        center={"lat": 37.7749, "lng": -122.4194},
        metro_bbox=SAN_FRANCISCO_METRO_BBOX,
        division_bboxes=SAN_FRANCISCO_DIVISION_BBOXES,
        submarkets=SAN_FRANCISCO_SUBMARKETS,
        divisions=SAN_FRANCISCO_DIVISIONS,
        job_suffix="sf",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_sf_dob_endpoint,
                platform="socrata",
                watermark_col="issued_date",
                id_keys=["permit_number", "id", "application_number"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_sf_311_endpoint,
                platform="socrata",
                watermark_col="requested_datetime",
                id_keys=["service_request_id", "id", "unique_key"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_sf_licenses_endpoint,
                platform="socrata",
                watermark_col="location_start_date",
                id_keys=["location_id", "certificate_number", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.socrata_sf_deeds_endpoint,
                platform="socrata",
                watermark_col="closed_roll_year",
                id_keys=["parcel_number", "block_and_lot_number", "id", "doc_id"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
            ),
        },
    ),
    CityId.SEATTLE: CityRegistration(
        city_id=CityId.SEATTLE,
        name="Seattle Metro",
        state="WA",
        center={"lat": 47.6062, "lng": -122.3321},
        metro_bbox=SEATTLE_METRO_BBOX,
        division_bboxes=SEATTLE_DIVISION_BBOXES,
        submarkets=SEATTLE_SUBMARKETS,
        divisions=SEATTLE_DIVISIONS,
        job_suffix="seattle",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_seattle_permits_endpoint,
                platform="socrata",
                watermark_col="issueddate",
                id_keys=["permitnum", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_seattle_311_endpoint,
                platform="socrata",
                watermark_col="createddate",
                id_keys=["servicerequestnumber", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_seattle_licenses_endpoint,
                platform="socrata",
                watermark_col="applicationdate",
                id_keys=["license", "ubi", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
            ),
            # King County Assessor parcel sales stand in for recorded deeds. This
            # is an ArcGIS FeatureServer, not Socrata: it pages by OBJECTID via
            # resultOffset rather than by Socrata's $offset, so it needs an
            # ArcGIS-aware PaginatingClient.
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_kc_sales_url,
                platform="arcgis",
                watermark_col="SaleDate",
                id_keys=["ExciseTaxNum", "PIN", "OBJECTID"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                extra={"oid_field": "OBJECTID", "max_record_count": 1000},
            ),
        },
    ),
    CityId.LOS_ANGELES: CityRegistration(
        city_id=CityId.LOS_ANGELES,
        name="Los Angeles Metro",
        state="CA",
        center={"lat": 34.0522, "lng": -118.2437},
        metro_bbox=LA_METRO_BBOX,
        division_bboxes=LA_DIVISION_BBOXES,
        submarkets=LA_SUBMARKETS,
        divisions=LA_DIVISIONS,
        job_suffix="la",
        # DEEDS is the only feed deliberately absent. The city's 311 program
        # relaunched in 2025 as yearly MyLA311 "Cases" datasets (the current
        # -year set refreshes through the same day), and the former registry
        # note about an "archived 2013-2014 extract only" is obsolete. LA
        # County publishes no open transaction-level recorded-deeds or parcel
        # -sales endpoint — its Assessor roll table carries no sale price — so
        # FeedType.DEEDS stays unregistered rather than pointed at an annual
        # assessment snapshot. `get_dataset` raises a readable error for it;
        # the scheduler simply skips it.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_la_permits_endpoint,
                platform="socrata",
                watermark_col="issue_date",
                id_keys=["permit_nbr", "pin_nbr", "apn", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_la_311_endpoint,
                platform="socrata",
                watermark_col="createddate",
                id_keys=["casenumber", "srnumber", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_la_licenses_endpoint,
                platform="socrata",
                watermark_col="location_start_date",
                id_keys=["location_account", "business_name", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
            ),
        },
    ),
}


def get_dataset(city_id: CityId, feed: FeedType) -> DatasetSpec:
    """Look up one city's feed spec, failing with a readable message.

    Not every city publishes every feed: Los Angeles has no open recorded
    -deeds endpoint, for instance. Indexing ``REGISTRY[city].datasets[feed]``
    directly raises a bare KeyError that names neither the city nor the feed,
    so producers should route through here instead.
    """
    reg = REGISTRY.get(city_id)
    if reg is None:
        raise KeyError(f"City {city_id.value!r} is not registered in REGISTRY")
    spec = reg.datasets.get(feed)
    if spec is None:
        available = ", ".join(sorted(f.value for f in reg.datasets)) or "none"
        raise KeyError(
            f"City {city_id.value!r} has no {feed.value!r} feed registered "
            f"(available: {available})"
        )
    return spec


def get_job_name(feed: FeedType, city_id: CityId) -> str:
    """Generate canonical scheduler job name (e.g. 'permits', 'permits_chicago', 'permits_sf')."""
    reg = REGISTRY.get(city_id)
    if not reg or not reg.job_suffix:
        return feed.value
    return f"{feed.value}_{reg.job_suffix}"
