"""City and Dataset Registry for Urban Signal.

Provides a unified, centralized registry for all supported metropolitan regions,
geographic boundaries, submarkets, division catalogs, and municipal dataset endpoints.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Protocol, Tuple, Union, runtime_checkable

from src.config import settings
from src.spatial.cities.chicago import (
    CHICAGO_DIVISION_BBOXES,
    CHICAGO_DIVISIONS,
    CHICAGO_METRO_BBOX,
    CHICAGO_SUBMARKETS,
)
from src.spatial.cities.philadelphia import (
    PHILADELPHIA_METRO_BBOX,
    PHL_DIVISION_BBOXES,
    PHL_DIVISIONS,
    PHL_SUBMARKETS,
)
from src.spatial.cities.washington_dc import (
    DC_DIVISION_BBOXES,
    DC_DIVISIONS,
    DC_METRO_BBOX,
    DC_SUBMARKETS,
)
from src.spatial.cities.austin import (
    AUSTIN_DIVISION_BBOXES,
    AUSTIN_DIVISIONS,
    AUSTIN_METRO_BBOX,
    AUSTIN_SUBMARKETS,
)
from src.spatial.cities.cincinnati import (
    CINCINNATI_DIVISION_BBOXES,
    CINCINNATI_DIVISIONS,
    CINCINNATI_METRO_BBOX,
    CINCINNATI_SUBMARKETS,
)
from src.spatial.cities.boston import (
    BOSTON_DIVISION_BBOXES,
    BOSTON_DIVISIONS,
    BOSTON_METRO_BBOX,
    BOSTON_SUBMARKETS,
)
from src.spatial.cities.baltimore import (
    BALTIMORE_DIVISION_BBOXES,
    BALTIMORE_DIVISIONS,
    BALTIMORE_METRO_BBOX,
    BALTIMORE_SUBMARKETS,
)
from src.spatial.cities.montgomery import (
    MONTGOMERY_DIVISION_BBOXES,
    MONTGOMERY_DIVISIONS,
    MONTGOMERY_METRO_BBOX,
    MONTGOMERY_SUBMARKETS,
)
from src.spatial.cities.baton_rouge import (
    BATON_ROUGE_DIVISION_BBOXES,
    BATON_ROUGE_DIVISIONS,
    BATON_ROUGE_METRO_BBOX,
    BATON_ROUGE_SUBMARKETS,
)
from src.spatial.cities.denver import (
    DENVER_DIVISION_BBOXES,
    DENVER_DIVISIONS,
    DENVER_METRO_BBOX,
    DENVER_SUBMARKETS,
)
from src.spatial.cities.detroit import (
    DETROIT_DIVISION_BBOXES,
    DETROIT_DIVISIONS,
    DETROIT_METRO_BBOX,
    DETROIT_SUBMARKETS,
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
from src.spatial.cities.new_orleans import (
    NEW_ORLEANS_METRO_BBOX,
    NOLA_DIVISION_BBOXES,
    NOLA_DIVISIONS,
    NOLA_SUBMARKETS,
)
from src.spatial.cities.norfolk import (
    NORFOLK_DIVISION_BBOXES,
    NORFOLK_DIVISIONS,
    NORFOLK_METRO_BBOX,
    NORFOLK_SUBMARKETS,
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
    NEW_ORLEANS = "new_orleans"
    NORFOLK = "norfolk"
    DETROIT = "detroit"
    AUSTIN = "austin"
    CINCINNATI = "cincinnati"
    BOSTON = "boston"
    BALTIMORE = "baltimore"
    MONTGOMERY = "montgomery"
    BATON_ROUGE = "baton_rouge"
    DENVER = "denver"
    PHILADELPHIA = "philadelphia"
    WASHINGTON_DC = "washington_dc"


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

    # New Orleans & Orleans Parish
    "new_orleans": CityId.NEW_ORLEANS,
    "new-orleans": CityId.NEW_ORLEANS,
    "new orleans": CityId.NEW_ORLEANS,
    "nola": CityId.NEW_ORLEANS,
    "orleans_parish": CityId.NEW_ORLEANS,
    "orleans-parish": CityId.NEW_ORLEANS,
    "orleans parish": CityId.NEW_ORLEANS,

    # Norfolk & Hampton Roads
    "norfolk": CityId.NORFOLK,
    "norfolk_va": CityId.NORFOLK,
    "norfolk-va": CityId.NORFOLK,
    "norfolk va": CityId.NORFOLK,

    # Detroit & Metro Detroit
    "detroit": CityId.DETROIT,
    "detroit_mi": CityId.DETROIT,
    "detroit-mi": CityId.DETROIT,
    "detroit mi": CityId.DETROIT,

    # Austin & Travis County
    "austin": CityId.AUSTIN,
    "travis_county": CityId.AUSTIN,
    "travis-county": CityId.AUSTIN,
    "travis county": CityId.AUSTIN,

    # Cincinnati & Hamilton County
    "cincinnati": CityId.CINCINNATI,
    "cincy": CityId.CINCINNATI,
    "cinci": CityId.CINCINNATI,
    "cincinnati-oh": CityId.CINCINNATI,
    "cincinnati oh": CityId.CINCINNATI,
    "hamilton_county": CityId.CINCINNATI,
    "hamilton county": CityId.CINCINNATI,

    "boston": CityId.BOSTON,
    "bos": CityId.BOSTON,
    "greater_boston": CityId.BOSTON,
    "greater boston": CityId.BOSTON,
    "cambridge": CityId.BOSTON,
    "somerville": CityId.BOSTON,

    # Baltimore
    "baltimore": CityId.BALTIMORE,
    "baltimore_city": CityId.BALTIMORE,
    "baltimore city": CityId.BALTIMORE,
    "bmore": CityId.BALTIMORE,
    "montgomery": CityId.MONTGOMERY,
    "montgomery_county": CityId.MONTGOMERY,
    "montgomery county": CityId.MONTGOMERY,
    "montgomery_md": CityId.MONTGOMERY,
    "moco": CityId.MONTGOMERY,

    # Baton Rouge / East Baton Rouge Parish
    "baton_rouge": CityId.BATON_ROUGE,
    "baton-rouge": CityId.BATON_ROUGE,
    "baton rouge": CityId.BATON_ROUGE,
    "brla": CityId.BATON_ROUGE,
    "east_baton_rouge": CityId.BATON_ROUGE,
    "east baton rouge": CityId.BATON_ROUGE,

    # Denver
    "denver": CityId.DENVER,
    "denver_co": CityId.DENVER,
    "denver-co": CityId.DENVER,

    # Philadelphia
    "philadelphia": CityId.PHILADELPHIA,
    "philly": CityId.PHILADELPHIA,
    "phl": CityId.PHILADELPHIA,

    # Washington DC
    "washington_dc": CityId.WASHINGTON_DC,
    "washington-dc": CityId.WASHINGTON_DC,
    "washington dc": CityId.WASHINGTON_DC,
    "dc": CityId.WASHINGTON_DC,
    "district_of_columbia": CityId.WASHINGTON_DC,
    "district of columbia": CityId.WASHINGTON_DC,
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
                # MyLA311 spells every core column differently from the shared
                # parser chains. The 2026+ "Cases" schema is Salesforce-derived
                # (`casenumber`, `geolocation__latitude__s`); the 2015-2024
                # yearly backfills use `srnumber`/`requesttype`. Declared here
                # rather than grown into the shared chains — see
                # src/producers/field_maps.py.
                extra={
                    "field_map": {
                        "incident_id": ["casenumber", "srnumber"],
                        "latitude": ["geolocation__latitude__s"],
                        "longitude": ["geolocation__longitude__s"],
                        "complaint_type": ["requesttype"],
                        "created_date": ["createddate"],
                        "closed_date": ["closeddate"],
                        "zipcode": ["zipcode__c"],
                        "borough": ["locator_sr_neigborhood_council"],
                    }
                },
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
    CityId.NEW_ORLEANS: CityRegistration(
        city_id=CityId.NEW_ORLEANS,
        name="New Orleans Metro",
        state="LA",
        center={"lat": 29.9511, "lng": -90.0715},
        metro_bbox=NEW_ORLEANS_METRO_BBOX,
        division_bboxes=NOLA_DIVISION_BBOXES,
        submarkets=NOLA_SUBMARKETS,
        divisions=NOLA_DIVISIONS,
        job_suffix="nola",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_nola_permits_endpoint,
                platform="socrata",
                watermark_col="issuedate",
                id_keys=["numstring", "prmtid", "objectid", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                # NOLA permits spell everything their own way; `pin` exists on
                # the feed but is a parcel number — deliberately kept out of
                # the job-id chain. See src/producers/field_maps.py.
                extra={
                    "field_map": {
                        "job_id": ["numstring"],
                        "latitude": ["location_1.latitude"],
                        "longitude": ["location_1.longitude"],
                        "cost": ["constrval"],
                        "job_type": ["type"],
                        "issuance_date": ["issuedate"],
                        "filing_date": ["filingdate"],
                        "status": ["currentstatus"],
                        "borough": ["subdivision"],
                    }
                },
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_nola_311_endpoint,
                platform="socrata",
                watermark_col="date_created",
                id_keys=["service_request", "rowid", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                extra={
                    "field_map": {
                        "incident_id": ["service_request", "rowid"],
                        "created_date": ["date_created"],
                        "closed_date": ["case_close_date"],
                        "descriptor": ["request_reason"],
                        "incident_address": ["final_address"],
                        "borough": ["address_councildis"],
                    }
                },
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_nola_licenses_endpoint,
                platform="socrata",
                watermark_col="businessstartdate",
                id_keys=["businesslicensenumber", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                # ~18% of rows sit outside the parish (metro-bbox filtering
                # drops them) and some businessstartdate values are future-
                # dated (max seen 2027-02-27) — tolerated, not treated as now.
                extra={
                    "field_map": {
                        "license_id": ["businesslicensenumber"],
                        "effective_date": ["businessstartdate"],
                        "license_type": ["businesstype"],
                        "dba": ["businessname"],
                        "premises_name": ["ownername"],
                    }
                },
            ),
            # NORA Sold Properties is the Redevelopment Authority's own
            # disposals, NOT a general recorded-deeds feed — it under-counts
            # ordinary market transactions and carries no price column
            # (document_amount parses to 0.0 by design). Registered with that
            # caveat, like King County parcel sales for Seattle.
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.socrata_nola_deeds_endpoint,
                platform="socrata",
                watermark_col="sale_date",
                id_keys=["identifier", "geopin", "id"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                extra={
                    "field_map": {
                        "doc_id": ["identifier"],
                        "bbl": ["geopin"],
                        "latitude": ["geocoded_column.latitude"],
                        "longitude": ["geocoded_column.longitude"],
                        "doc_type": ["disposition_channel"],
                        "borough": ["council_district"],
                    }
                },
            ),
        },
    ),
    CityId.NORFOLK: CityRegistration(
        city_id=CityId.NORFOLK,
        name="Norfolk",
        state="VA",
        center={"lat": 36.8508, "lng": -76.2859},
        metro_bbox=NORFOLK_METRO_BBOX,
        division_bboxes=NORFOLK_DIVISION_BBOXES,
        submarkets=NORFOLK_SUBMARKETS,
        divisions=NORFOLK_DIVISIONS,
        job_suffix="norfolk",
        # Partial registration like Los Angeles: MyNorfolk 311 (`nbyu-xjez`)
        # locates cases with an address STRING and the business-license feed
        # (`dpi6-sct5`) has no geometry at all — both need an address-geocoding
        # capability before they can produce H3-keyed events. Deferred rather
        # than registered shapeless.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_norfolk_permits_endpoint,
                platform="socrata",
                watermark_col="issue_date",
                id_keys=["permit_number", "gpin", "tax_account", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                # Scheduled (future-dated) filings appear on this feed (max
                # seen 2027-01-27) — tolerated as watermark skew.
                extra={
                    "field_map": {
                        "cost": ["project_cost"],
                        "filing_date": ["application_date"],
                        # work_type before type: bare "Building" classifies to
                        # OT; the NB/A2 signal lives in work_type.
                        "job_type": ["work_type", "type"],
                    }
                },
            ),
            # Property Assessment and Sales publishes one dataset per fiscal
            # year (FY23...FY27). Rotate the endpoint each July — the new FY
            # file is a different resource ID. Rows carry no coordinates:
            # events are null-lat/lng/null-H3 like Cook County sales, keyed on
            # document_number + GPIN.
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.socrata_norfolk_deeds_endpoint,
                platform="socrata",
                watermark_col="transfer_date",
                id_keys=["document_number", "lrsn", "gpin", "id"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                extra={
                    "field_map": {
                        "doc_id": ["document_number"],
                        "bbl": ["gpin", "parcel_id"],
                    }
                },
            ),
        },
    ),
    CityId.DETROIT: CityRegistration(
        city_id=CityId.DETROIT,
        name="Detroit",
        state="MI",
        center={"lat": 42.3314, "lng": -83.0458},
        metro_bbox=DETROIT_METRO_BBOX,
        division_bboxes=DETROIT_DIVISION_BBOXES,
        submarkets=DETROIT_SUBMARKETS,
        divisions=DETROIT_DIVISIONS,
        job_suffix="detroit",
        # All four feeds are ArcGIS FeatureServers (services2 host) paged by
        # the existing ArcGISClient. Every Detroit layer's objectIdField is
        # `ObjectId` (camelCase — NOT King County's `OBJECTID`), so each spec
        # carries oid_field explicitly. Permits/licenses/sales dates arrive as
        # esriFieldTypeDateOnly strings ("YYYY-MM-DD"); the 311 feed uses true
        # epoch-ms dates the client converts. Sales rows include a typo-year
        # sentinel ('2925-12-24') — tolerated watermark skew.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_detroit_permits_url,
                platform="arcgis",
                watermark_col="issued_date",
                id_keys=["record_id", "ObjectId", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                extra={
                    "oid_field": "ObjectId",
                    "max_record_count": 1000,
                    "field_map": {
                        "job_id": ["record_id"],
                        "cost": ["amt_permit_cost"],
                    },
                },
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_detroit_311_url,
                platform="arcgis",
                watermark_col="created_at",
                id_keys=["issue_id", "ObjectId", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                extra={
                    "oid_field": "ObjectId",
                    "max_record_count": 1000,
                    "field_map": {
                        "incident_id": ["issue_id"],
                        "closed_date": ["closed_at"],
                    },
                },
            ),
            # Renewal-driven feed: `expiration_date` is the only date column,
            # so effective_date stays None and the watermark moves slowly by
            # design. Geocoded point layer (research's "non-spatial table"
            # verdict was wrong).
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_detroit_licenses_url,
                platform="arcgis",
                watermark_col="expiration_date",
                id_keys=["record_id", "ObjectId", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                extra={
                    "oid_field": "ObjectId",
                    "max_record_count": 1000,
                    # The shared license_type chain has no bare 'license_type'
                    # term — without the map every row falls to the
                    # 'On-Premises Liquor' default.
                    "field_map": {
                        "license_id": ["record_id"],
                        "license_type": ["license_type", "license_category"],
                    },
                },
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_detroit_sales_url,
                platform="arcgis",
                watermark_col="sale_date",
                id_keys=["sale_id", "liber_page", "ObjectId", "id"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                extra={
                    "oid_field": "ObjectId",
                    "max_record_count": 1000,
                    "field_map": {
                        "doc_id": ["sale_id"],
                        "bbl": ["parcel_id"],
                        "document_amount": ["amt_sale_price"],
                    },
                },
            ),
        },
    ),
    CityId.AUSTIN: CityRegistration(
        city_id=CityId.AUSTIN,
        name="Austin",
        state="TX",
        center={"lat": 30.2672, "lng": -97.7431},
        metro_bbox=AUSTIN_METRO_BBOX,
        division_bboxes=AUSTIN_DIVISION_BBOXES,
        submarkets=AUSTIN_SUBMARKETS,
        divisions=AUSTIN_DIVISIONS,
        job_suffix="austin",
        # Partial registration like Los Angeles: Austin registers two feeds
        # only. No business-license or property-sales feed exists on
        # data.austintexas.gov — the domain exited the Socrata discovery mesh
        # after the Texas ODP migration (its catalog now serves three internal
        # analytics views), TABC's statewide alcohol licenses carry zero
        # geocodes, and Travis County's Socrata presence is an unreachable
        # FedRAMP shell. FeedType.SLA and FeedType.DEEDS stay deliberately
        # absent; `get_dataset` raises readable errors for them.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_austin_permits_endpoint,
                platform="socrata",
                watermark_col="issue_date",
                id_keys=["permit_number", "objectid", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                # total_job_valuation is NULL on remodel rows (accepted);
                # work_type before permit_type so NB/Addition signal survives
                # generic "Building Permit" values (mirror of Norfolk).
                extra={
                    "field_map": {
                        "cost": ["total_job_valuation"],
                        "filing_date": ["application_date"],
                        "job_type": ["work_type", "permit_type"],
                        "proposed_units": ["number_of_units"],
                        "proposed_stories": ["number_of_floors"],
                        "borough": ["council_district"],
                    }
                },
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_austin_311_endpoint,
                platform="socrata",
                watermark_col="sr_created_date",
                id_keys=["sr_number", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                # sr_number is also a Chicago chain term: production always
                # passes city_id explicitly, and the tightened chicago sniff
                # requires corroborating markers (see complaints_311_producer).
                extra={
                    "field_map": {
                        "latitude": ["sr_location_lat"],
                        "longitude": ["sr_location_long"],
                        "complaint_type": ["sr_type_desc"],
                        "created_date": ["sr_created_date"],
                        "closed_date": ["sr_closed_date"],
                        "status": ["sr_status_desc"],
                        "zipcode": ["sr_location_zip_code"],
                        "incident_address": ["sr_location"],
                        "borough": ["sr_location_council_district"],
                    }
                },
            ),
        },
    ),
    CityId.CINCINNATI: CityRegistration(
        city_id=CityId.CINCINNATI,
        name="Cincinnati",
        state="OH",
        center={"lat": 39.1031, "lng": -84.5120},
        metro_bbox=CINCINNATI_METRO_BBOX,
        division_bboxes=CINCINNATI_DIVISION_BBOXES,
        submarkets=CINCINNATI_SUBMARKETS,
        divisions=CINCINNATI_DIVISIONS,
        job_suffix="cinci",
        # The verified Cincinnati catalog has permits, 311, and business
        # licenses. No transaction-level sales/deeds feed was identified;
        # leave DEEDS absent instead of inventing a source.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_cincinnati_permits_endpoint,
                platform="socrata",
                watermark_col="issueddate",
                id_keys=["permit_number", "permitnumber", "pin", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                extra={
                    "field_map": {
                        "job_id": ["permit_number", "permitnumber", "pin"],
                        "issuance_date": ["issueddate"],
                        "filing_date": ["applieddate"],
                        "address_street": ["originaladdress1"],
                        "zipcode": ["originalzip"],
                    }
                },
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_cincinnati_311_endpoint,
                platform="socrata",
                watermark_col="date_time_received",
                id_keys=["service_request_id", "sr_number", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                extra={
                    "field_map": {
                        "incident_id": ["sr_number"],
                        "created_date": ["date_time_received"],
                        "incident_address": ["address"],
                        "complaint_type": ["sr_type_desc", "sr_type"],
                    }
                },
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_cincinnati_licenses_endpoint,
                platform="socrata",
                watermark_col="entered_date",
                id_keys=["license_number", "license_id", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                extra={
                    "field_map": {
                        "license_id": ["number_key", "uniqueid"],
                        "effective_date": ["entered_date"],
                        "latitude": ["latitude"],
                        "longitude": ["longitude"],
                        "status": ["data_status", "status_class"],
                    }
                },
            ),
        },
    ),
    CityId.BOSTON: CityRegistration(
        city_id=CityId.BOSTON,
        name="Boston",
        state="MA",
        center={"lat": 42.355, "lng": -71.065},
        metro_bbox=BOSTON_METRO_BBOX,
        division_bboxes=BOSTON_DIVISION_BBOXES,
        submarkets=BOSTON_SUBMARKETS,
        divisions=BOSTON_DIVISIONS,
        job_suffix="boston",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.ckan_boston_permits_endpoint,
                platform="ckan",
                watermark_col="issued_date",
                id_keys=["permitnumber", "_id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                extra={
                    "field_map": {
                        "job_id": ["permitnumber"],
                        "issuance_date": ["issued_date"],
                        "filing_date": ["issued_date"],
                        "address_street": ["address"],
                        "zipcode": ["zip"],
                        "borough": ["ward"],
                        "latitude": ["y_latitude", "gpsy"],
                        "longitude": ["x_longitude", "gpsx"],
                        "status": ["status"],
                        "cost": ["declared_valuation"],
                    }
                },
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.ckan_boston_311_endpoint,
                platform="ckan",
                watermark_col="open_dt",
                id_keys=["case_enquiry_id", "_id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                extra={
                    "field_map": {
                        "incident_id": ["case_enquiry_id"],
                        "latitude": ["latitude"],
                        "longitude": ["longitude"],
                        "complaint_type": ["type", "case_title"],
                        "created_date": ["open_dt"],
                        "closed_date": ["closed_dt"],
                        "status": ["case_status"],
                        "incident_address": ["location_street_name", "location"],
                        "zipcode": ["location_zipcode"],
                        "borough": ["ward"],
                    },
                    "endpoint_by_year": {
                        "2025": settings.ckan_boston_311_2025_endpoint,
                        "2026": settings.ckan_boston_311_endpoint,
                    },
                    "rollover": "manual-verify",
                },
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.ckan_boston_licenses_endpoint,
                platform="ckan",
                watermark_col="issued",
                id_keys=["license_num", "_id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                extra={
                    "field_map": {
                        "license_id": ["license_num"],
                        "latitude": ["gpsy"],
                        "longitude": ["gpsx"],
                        "effective_date": ["issued"],
                        "expiration_date": ["expires"],
                        "license_type": ["license_type"],
                        "status": ["status"],
                        "address_street": ["address"],
                        "zipcode": ["zip"],
                    }
                },
            ),
        },
    ),
    CityId.MONTGOMERY: CityRegistration(
        city_id=CityId.MONTGOMERY,
        name="Montgomery County",
        state="MD",
        center={"lat": 39.140, "lng": -77.190},
        metro_bbox=MONTGOMERY_METRO_BBOX,
        division_bboxes=MONTGOMERY_DIVISION_BBOXES,
        submarkets=MONTGOMERY_SUBMARKETS,
        divisions=MONTGOMERY_DIVISIONS,
        job_suffix="montgomery",
        # MC311 (xtyh-brr2) is deliberately excluded: it has only zip/city/
        # district fields and no street or coordinates, so it fails G5 by
        # construction. Deeds/sales were not found in the county portal.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_montgomery_permits_endpoint,
                platform="socrata",
                watermark_col="issueddate",
                id_keys=["permitno"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                extra={
                    "field_map": {
                        "job_id": ["permitno"],
                        "issuance_date": ["issueddate"],
                        "filing_date": ["addeddate"],
                        "address_street": ["stno", "stname", "suffix", "postdir"],
                        "zipcode": ["zip"],
                        "job_type": ["worktype", "applicationtype", "usecode"],
                        "status": ["status"],
                        "latitude": ["location.latitude"],
                        "longitude": ["location.longitude"],
                    },
                    "companion_endpoints": {
                        "commercial": "https://data.montgomerycountymd.gov/resource/i26v-w6bd.json",
                        "demolition": "https://data.montgomerycountymd.gov/resource/b6ht-fw3x.json",
                        "electrical": "https://data.montgomerycountymd.gov/resource/qxie-8qnp.json",
                    },
                },
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_montgomery_licenses_endpoint,
                platform="socrata",
                watermark_col="",
                id_keys=["licensee_number", "licensee_name"],
                topic=settings.topic_sla,
                interval_seconds=900.0,
                producer_key="sla",
                extra={
                    "ingestion_mode": "snapshot",
                    "scope": "ABS liquor licensees only",
                    "field_map": {
                        "license_id": ["licensee_number"],
                        "license_type": ["channel_type"],
                        "premises_name": ["licensee_name", "account_name"],
                        "address_street": ["street"],
                        "zipcode": ["zip"],
                        "latitude": ["location.latitude"],
                        "longitude": ["location.longitude"],
                    },
                },
            ),
        },
    ),
    CityId.BATON_ROUGE: CityRegistration(
        city_id=CityId.BATON_ROUGE,
        name="Baton Rouge / East Baton Rouge Parish",
        state="LA",
        center={"lat": 30.4505, "lng": -91.1870},
        metro_bbox=BATON_ROUGE_METRO_BBOX,
        division_bboxes=BATON_ROUGE_DIVISION_BBOXES,
        submarkets=BATON_ROUGE_SUBMARKETS,
        divisions=BATON_ROUGE_DIVISIONS,
        job_suffix="brla",
        # The verified portal has daily permits, geocoded 311, and a
        # parish-wide business registry. The registry has no usable open-date
        # watermark, so D4 snapshot mode diffs ids across full refreshes.
        # Adjudicated/foreclosure parcels are not market sales and remain out.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_baton_rouge_permits_endpoint,
                platform="socrata",
                watermark_col="issueddate",
                id_keys=["permitid", "permitnumber", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                extra={
                    "field_map": {
                        "job_id": ["permitnumber", "permitid"],
                        "issuance_date": ["issueddate"],
                        "filing_date": ["creationdate"],
                        "job_type": ["permittype"],
                        "cost": ["projectvalue"],
                        "address_street": ["streetaddress", "address"],
                        "zipcode": ["zip"],
                        "borough": ["parishname"],
                    }
                },
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_baton_rouge_311_endpoint,
                platform="socrata",
                watermark_col="createdate",
                id_keys=["id", "parentid"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                extra={
                    "field_map": {
                        "incident_id": ["id"],
                        "latitude": ["latitude"],
                        "longitude": ["longitude"],
                        "complaint_type": ["typename", "parenttype"],
                        "created_date": ["createdate"],
                        "status": ["statusdesc"],
                        "incident_address": ["streetaddress"],
                        "borough": ["division"],
                    }
                },
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_baton_rouge_licenses_endpoint,
                platform="socrata",
                watermark_col="",
                id_keys=["taccount", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                extra={
                    "ingestion_mode": "snapshot",
                    "field_map": {
                        "license_id": ["taccount"],
                        "latitude": ["geolocation.latitude"],
                        "longitude": ["geolocation.longitude"],
                        "license_type": ["typename", "naicname"],
                        "status": ["tstatus"],
                        "premises_name": ["tname", "tlegalname"],
                    },
                },
            ),
        },
    ),
    CityId.DENVER: CityRegistration(
        city_id=CityId.DENVER,
        name="Denver",
        state="CO",
        center={"lat": 39.7392, "lng": -104.9903},
        metro_bbox=DENVER_METRO_BBOX,
        division_bboxes=DENVER_DIVISION_BBOXES,
        submarkets=DENVER_SUBMARKETS,
        divisions=DENVER_DIVISIONS,
        job_suffix="denver",
        # Licenses have no issue-date field and sales are non-spatial. The
        # numeric RECEPTION_DATE/$0 transfer quirks belong to the deliberately
        # excluded sales feed and are retained in research documentation.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_denver_permits_url,
                platform="arcgis",
                watermark_col="DATE_ISSUED",
                id_keys=["PERMIT_NUM", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                extra={
                    "oid_field": "OBJECTID",
                    "max_record_count": 2000,
                    "companion_endpoints": {
                        "commercial": (
                            "https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/"
                            "ODC_DEV_COMMERCIALCONSTPERMIT_P/FeatureServer/317"
                        )
                    },
                    "field_map": {
                        "job_id": ["PERMIT_NUM"],
                        "issuance_date": ["DATE_ISSUED"],
                        "filing_date": ["DATE_RECEIVED"],
                        "job_type": ["CLASS"],
                        "cost": ["VALUATION"],
                        "address_street": ["ADDRESS"],
                        "proposed_units": ["UNITS"],
                        "borough": ["NEIGHBORHOOD"],
                    },
                },
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_denver_311_url,
                platform="arcgis",
                watermark_col="Case_Created_Date",
                id_keys=["OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                extra={
                    "oid_field": "OBJECTID",
                    "max_record_count": 2000,
                    "field_map": {
                        "latitude": ["Latitude"],
                        "longitude": ["Longitude"],
                        "incident_id": ["OBJECTID"],
                        "complaint_type": ["Type", "Topic", "Case_Summary"],
                        "created_date": ["Case_Created_dttm"],
                        "closed_date": ["Case_Closed_dttm"],
                        "status": ["Case_Status"],
                        "incident_address": ["Incident_Address_1"],
                        "zipcode": ["Incident_Zip_Code", "Customer_Zip_Code"],
                        "borough": ["Neighborhood"],
                    },
                },
            ),
        },
    ),
    CityId.BALTIMORE: CityRegistration(
        city_id=CityId.BALTIMORE,
        name="Baltimore",
        state="MD",
        center={"lat": 39.290, "lng": -76.612},
        metro_bbox=BALTIMORE_METRO_BBOX,
        division_bboxes=BALTIMORE_DIVISION_BBOXES,
        submarkets=BALTIMORE_SUBMARKETS,
        divisions=BALTIMORE_DIVISIONS,
        job_suffix="baltimore",
        # Baltimore's liquor table is intentionally notifications-grade:
        # it is a narrow license inventory rather than a complete hospitality
        # activity feed. No transaction/deeds feed is registered.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_baltimore_permits_url,
                platform="arcgis",
                watermark_col="IssuedDate",
                id_keys=["CaseNumber", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                extra={
                    "oid_field": "OBJECTID",
                    "max_record_count": 1000,
                    "field_map": {
                        "job_id": ["CaseNumber"],
                        "issuance_date": ["IssuedDate"],
                        "expiration_date": ["ExpirationDate"],
                        "address_street": ["Address"],
                        "cost": ["Cost"],
                        "borough": ["Neighborhood", "Council_District"],
                        "job_type": ["ProposedUse", "ExistingUse"],
                    },
                },
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_baltimore_311_url,
                platform="arcgis",
                watermark_col="CreatedDate",
                id_keys=["SRRecordID", "ServiceRequestNum", "RowID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                extra={
                    "oid_field": "RowID",
                    "max_record_count": 2000,
                    "field_map": {
                        "incident_id": ["SRRecordID", "ServiceRequestNum", "RowID"],
                        "latitude": ["Latitude"],
                        "longitude": ["Longitude"],
                        "complaint_type": ["SRType"],
                        "created_date": ["CreatedDate"],
                        "closed_date": ["CloseDate"],
                        "status": ["SRStatus"],
                        "incident_address": ["Address"],
                        "zipcode": ["ZipCode"],
                        "borough": ["Neighborhood", "CouncilDistrict"],
                    },
                    "endpoint_by_year": {
                        "2025": settings.arcgis_baltimore_311_2025_url,
                        "2026": settings.arcgis_baltimore_311_url,
                    },
                    "rollover": "manual-verify",
                },
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_baltimore_licenses_url,
                platform="arcgis",
                watermark_col="LicenseDate",
                id_keys=["LicenseNumber", "LLKey", "ESRI_OID"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                extra={
                    "oid_field": "ESRI_OID",
                    "max_record_count": 2000,
                    "field_map": {
                        "license_id": ["LicenseNumber", "LLKey"],
                        "license_type": ["LicenseClass", "SubClass"],
                        "effective_date": ["LicenseDate"],
                        "expiration_date": ["LicenseEndDate"],
                        "status": ["LicenseStatus"],
                        "address_street": ["AddrStreet"],
                        "zipcode": ["AddrZip"],
                    },
                    "scope": "notifications-grade",
                },
            ),
        },
    ),
    CityId.PHILADELPHIA: CityRegistration(
        city_id=CityId.PHILADELPHIA,
        name="Philadelphia",
        state="PA",
        center={"lat": 39.9526, "lng": -75.1652},
        metro_bbox=PHILADELPHIA_METRO_BBOX,
        division_bboxes=PHL_DIVISION_BBOXES,
        submarkets=PHL_SUBMARKETS,
        divisions=PHL_DIVISIONS,
        job_suffix="philadelphia",
        # All four feeds are CARTO tables (phl.carto.com) paged by the
        # CartoClient's keyset on (date, cartodb_id); sentinel dates
        # (year-3200 seen live on mostrecentissuedate, year-9798 on
        # rtt_summary.document_date) are excluded CLIENT-side. permits/
        # business_licenses/rtt_summary carry geometry only as the_geom hex
        # WKB — their select extras project ST_X/ST_Y to plain
        # latitude/longitude keys so shared parser chains match.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.carto_phl_permits_endpoint,
                platform="carto",
                watermark_col="permitissuedate",
                id_keys=["cartodb_id", "permitnumber", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                extra={
                    "id_col": "cartodb_id",
                    "order_by": "permitissuedate",
                    "select": "*, ST_Y(the_geom) AS latitude, ST_X(the_geom) AS longitude",
                    "field_map": {
                        "job_id": ["permitnumber"],
                        "issuance_date": ["permitissuedate"],
                        "borough": ["council_district"],
                        "zipcode": ["zip"],
                    },
                },
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.carto_phl_311_endpoint,
                platform="carto",
                watermark_col="requested_datetime",
                id_keys=["service_request_id", "cartodb_id", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                extra={
                    "id_col": "cartodb_id",
                    "order_by": "requested_datetime",
                    "field_map": {
                        "latitude": ["lat"],
                        "longitude": ["lon"],
                        "closed_date": ["closed_datetime"],
                    },
                },
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.carto_phl_licenses_endpoint,
                platform="carto",
                watermark_col="mostrecentissuedate",
                id_keys=["licensenum", "cartodb_id", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                extra={
                    "id_col": "cartodb_id",
                    "order_by": "mostrecentissuedate",
                    "select": "*, ST_Y(the_geom) AS latitude, ST_X(the_geom) AS longitude",
                    "field_map": {
                        "license_id": ["licensenum"],
                        "license_type": ["licensetype"],
                        "effective_date": ["initialissuedate"],
                        "expiration_date": ["expirationdate"],
                        "status": ["licensestatus"],
                    },
                },
            ),
            # Real Estate Transfer Tax summary includes mortgages and
            # satisfactions: NULL consideration parses to amount 0.0 by
            # design, and recorded_date maps to recording_date because
            # document_date is frequently NULL/sentinel. See
            # docs/research/non-socrata-platforms.md §Philadelphia.
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.carto_phl_deeds_endpoint,
                platform="carto",
                watermark_col="document_date",
                id_keys=["document_id", "cartodb_id", "id"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                extra={
                    "id_col": "cartodb_id",
                    "order_by": "document_date",
                    "select": "*, ST_Y(the_geom) AS latitude, ST_X(the_geom) AS longitude",
                    "field_map": {
                        "recorded_date": ["recording_date"],
                        "document_amount": ["total_consideration"],
                        "bbl": ["opa_account_num"],
                        "party1_grantor": ["grantors"],
                        "party2_grantee": ["grantees"],
                    },
                },
            ),
        },
    ),
    CityId.WASHINGTON_DC: CityRegistration(
        city_id=CityId.WASHINGTON_DC,
        name="Washington DC",
        state="DC",
        center={"lat": 38.9072, "lng": -77.0369},
        metro_bbox=DC_METRO_BBOX,
        division_bboxes=DC_DIVISION_BBOXES,
        submarkets=DC_SUBMARKETS,
        divisions=DC_DIVISIONS,
        job_suffix="dc",
        # All four feeds are ArcGIS FeatureServers; permits and 311 publish
        # one layer PER CALENDAR YEAR — endpoint_by_year maps below resolve
        # via resolve_endpoint at scheduler build; run the December rollover
        # drill before each New Year (roadmap §8.2) and append the new year's
        # layer id here. Basic Business Licenses and Property Sales CAMA are
        # NON-SPATIAL: events carry null lat/lng/null H3 keyed by SSL /
        # customer number (deeds-precedent tolerance); joining CAMA sales to
        # Parcel Lots (layer 33) for geometry is future work.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_dc_permits_url,
                platform="arcgis",
                watermark_col="ISSUE_DATE",
                id_keys=["PERMIT_ID", "DCRAINTERNALNUMBER", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                extra={
                    "oid_field": "OBJECTID",
                    "max_record_count": 2000,
                    "endpoint_by_year": {
                        "2023": "https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/15",
                        "2024": "https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/16",
                        "2025": "https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/17",
                        "2026": "https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/18",
                    },
                    "field_map": {
                        "job_id": ["PERMIT_ID"],
                        "latitude": ["LATITUDE"],
                        "longitude": ["LONGITUDE"],
                        "issuance_date": ["ISSUE_DATE"],
                        "job_type": ["PERMIT_TYPE_NAME", "PERMIT_SUBTYPE_NAME"],
                        "cost": ["FEES_PAID"],
                        "borough": ["WARD"],
                        "zipcode": ["ZIPCODE"],
                    },
                },
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_dc_311_url,
                platform="arcgis",
                watermark_col="ADDDATE",
                id_keys=["SERVICEREQUESTID", "GLOBALID", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                extra={
                    "oid_field": "OBJECTID",
                    "max_record_count": 1000,
                    "endpoint_by_year": {
                        "2022": "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/14",
                        "2023": "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/15",
                        "2024": "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/16",
                        "2025": "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/18",
                        "2026": "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/21",
                    },
                    "field_map": {
                        "incident_id": ["SERVICEREQUESTID"],
                        "latitude": ["LATITUDE"],
                        "longitude": ["LONGITUDE"],
                        "complaint_type": ["SERVICECODEDESCRIPTION"],
                        "created_date": ["ADDDATE"],
                        "closed_date": ["RESOLUTIONDATE"],
                        "status": ["SERVICEORDERSTATUS"],
                        "incident_address": ["STREETADDRESS"],
                        "borough": ["WARD"],
                        "zipcode": ["ZIPCODE"],
                    },
                },
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_dc_licenses_url,
                platform="arcgis",
                watermark_col="INITIALISSUEDATE",
                id_keys=["CUSTOMERNUMBER", "GLOBALID", "OBJECTID"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                extra={
                    "oid_field": "OBJECTID",
                    "max_record_count": 2000,
                    "non_spatial": True,
                    "field_map": {
                        "license_id": ["CUSTOMERNUMBER"],
                        "license_type": ["LICENSETYPE"],
                        "effective_date": ["LICENSESTARTDATE"],
                        "expiration_date": ["LICENSEENDDATE"],
                        "borough": ["WARD"],
                    },
                },
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_dc_sales_url,
                platform="arcgis",
                watermark_col="SALE_DATE",
                id_keys=["SSL", "ROW_NUMBER", "OBJECTID", "id"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                extra={
                    "oid_field": "OBJECTID",
                    "max_record_count": 2000,
                    "non_spatial": True,
                    "field_map": {
                        "doc_id": ["ROW_NUMBER"],
                        "bbl": ["SSL"],
                        "document_amount": ["SALE_PRICE"],
                        "recorded_date": ["SALE_DATE"],
                        "doc_type": ["QUALIFIED"],
                    },
                },
            ),
        },
    ),
}


def resolve_endpoint(spec: DatasetSpec, today: Optional[Any] = None) -> str:
    """Resolve a spec's endpoint for "today", honoring year-sliced datasets.

    Some jurisdictions publish one layer/resource per calendar year
    (`extra={"endpoint_by_year": {"2026": "...FeatureServer/18", ...}}`).
    Returns the current year's entry when present, else the newest year not
    in the future, else the lexicographically latest entry. Annual rollover
    drill: see docs/expansion-roadmap.md §8.2.
    """
    by_year = spec.extra.get("endpoint_by_year")
    if not by_year:
        return spec.endpoint
    if today is None:
        today = datetime.now(timezone.utc).date()
    year = getattr(today, "year", None)
    if year is None:
        year = int(str(today)[:4])
    for candidate in range(year, -1, -1):
        key = str(candidate)
        if key in by_year:
            return by_year[key]
    return by_year[max(by_year)]


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
