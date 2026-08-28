"""City and Dataset Registry for Urban Signal.

Provides a unified, centralized registry for all supported metropolitan regions,
geographic boundaries, submarkets, division catalogs, and municipal dataset endpoints.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Protocol, Tuple, Union, runtime_checkable

from src.config import settings
from src.producers.field_maps_dallas import DALLAS_311_FIELD_MAP, DALLAS_FIELD_MAP
from src.producers.field_maps_louisville import LOUISVILLE_311_FIELD_MAP, LOUISVILLE_SLA_FIELD_MAP
from src.producers.field_maps_san_jose import FIELD_MAP as SAN_JOSE_FIELD_MAP
from src.producers.field_maps_tampa import FIELD_MAP as TAMPA_FIELD_MAP, SLA_FIELD_MAP as TAMPA_SLA_FIELD_MAP
from src.producers.field_maps_las_vegas import FIELD_MAP as LAS_VEGAS_FIELD_MAP
from src.producers.field_maps_boise import FIELD_MAP as BOISE_PERMITS_FIELD_MAP
from src.producers.field_maps_fort_worth import FIELD_MAP as FORT_WORTH_PERMITS_FIELD_MAP
from src.producers.field_maps_honolulu import FIELD_MAP as HONOLULU_FIELD_MAP
from src.producers.field_maps_orlando import SLA_FIELD_MAP as ORLANDO_SLA_FIELD_MAP
from src.producers.field_maps_miami_dade import FIELD_MAP as MIAMI_DADE_FIELD_MAP
from src.producers.field_maps_memphis import FIELD_MAP as MEMPHIS_FIELD_MAP
from src.producers.field_maps_gainesville import FIELD_MAP as GAINESVILLE_PERMITS_FIELD_MAP
from src.producers.field_maps_phoenix import FIELD_MAP as PHOENIX_FIELD_MAP
from src.producers.field_maps_albuquerque import FIELD_MAP as ALBUQUERQUE_FIELD_MAP
from src.producers.field_maps_st_louis import FIELD_MAP as ST_LOUIS_FIELD_MAP
from src.producers.field_maps_aurora import FIELD_MAP as AURORA_FIELD_MAP
from src.producers.field_maps_henderson import FIELD_MAP as HENDERSON_FIELD_MAP
from src.producers.field_maps_virginia_beach import FIELD_MAP as VIRGINIA_BEACH_FIELD_MAP
from src.producers.field_maps_omaha import FIELD_MAP as OMAHA_FIELD_MAP
from src.producers.field_maps_toledo import FIELD_MAP as TOLEDO_FIELD_MAP
from src.producers.field_maps_buffalo import SLA_FIELD_MAP as BUFFALO_SLA_FIELD_MAP
from src.producers.field_maps_rochester import DEEDS_FIELD_MAP as ROCHESTER_DEEDS_FIELD_MAP
from src.producers.field_maps_syracuse import SYRACUSE_SLA_FIELD_MAP
from src.producers.field_maps_lynchburg import FIELD_MAP as LYNCHBURG_FIELD_MAP
from src.producers.field_maps_greenville import FIELD_MAP as GREENVILLE_FIELD_MAP
from src.producers.field_maps_anchorage import DEEDS_FIELD_MAP as ANCHORAGE_DEEDS_FIELD_MAP
from src.producers.field_maps_tucson import SLA_FIELD_MAP as TUCSON_SLA_FIELD_MAP
from src.producers.field_maps_boston_licensing import FIELD_MAP as BOSTON_LICENSING_FIELD_MAP
from src.producers.field_maps_counters import (
    NYC_COUNTS_FIELD_MAP,
    SEATTLE_FREMONT_FIELD_MAP,
)
from src.producers.field_maps_energy_benchmark import (
    CHICAGO_ENERGY_FIELD_MAP,
    NYC_ENERGY_FIELD_MAP,
    SEATTLE_ENERGY_FIELD_MAP,
)
from src.spatial.cities.portland import (
    PORTLAND_DIVISION_BBOXES,
    PORTLAND_DIVISIONS,
    PORTLAND_METRO_BBOX,
    PORTLAND_PERMITS_FIELD_MAP,
    PORTLAND_SLA_FIELD_MAP,
    PORTLAND_SUBMARKETS,
)
from src.spatial.cities.columbus_ga import (
    COLUMBUS_GA_DIVISION_BBOXES,
    COLUMBUS_GA_DIVISIONS,
    COLUMBUS_GA_METRO_BBOX,
    COLUMBUS_GA_SUBMARKETS,
)
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
from src.spatial.cities.prince_georges import (
    PRINCE_GEORGES_DIVISION_BBOXES,
    PRINCE_GEORGES_DIVISIONS,
    PRINCE_GEORGES_METRO_BBOX,
    PRINCE_GEORGES_SUBMARKETS,
)
from src.spatial.cities.columbus import (
    COLUMBUS_DIVISION_BBOXES,
    COLUMBUS_DIVISIONS,
    COLUMBUS_METRO_BBOX,
    COLUMBUS_SUBMARKETS,
)
from src.spatial.cities.nashville import (
    NASHVILLE_DIVISION_BBOXES,
    NASHVILLE_DIVISIONS,
    NASHVILLE_METRO_BBOX,
    NASHVILLE_SUBMARKETS,
)
from src.spatial.cities.kansas_city import (
    KANSAS_CITY_DIVISION_BBOXES,
    KANSAS_CITY_DIVISIONS,
    KANSAS_CITY_METRO_BBOX,
    KANSAS_CITY_SUBMARKETS,
)
from src.spatial.cities.pierce import (
    PIERCE_DIVISION_BBOXES,
    PIERCE_DIVISIONS,
    PIERCE_METRO_BBOX,
    PIERCE_SUBMARKETS,
)
from src.spatial.cities.milwaukee import (
    MILWAUKEE_DIVISION_BBOXES,
    MILWAUKEE_DIVISIONS,
    MILWAUKEE_METRO_BBOX,
    MILWAUKEE_SUBMARKETS,
)
from src.spatial.cities.charlotte import (
    CHARLOTTE_DIVISION_BBOXES,
    CHARLOTTE_DIVISIONS,
    CHARLOTTE_METRO_BBOX,
    CHARLOTTE_SUBMARKETS,
)
from src.spatial.cities.pittsburgh import (
    PITTSBURGH_DIVISION_BBOXES,
    PITTSBURGH_DIVISIONS,
    PITTSBURGH_METRO_BBOX,
    PITTSBURGH_SUBMARKETS,
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
from src.spatial.cities.minneapolis import (
    MINNEAPOLIS_DIVISION_BBOXES,
    MINNEAPOLIS_DIVISIONS,
    MINNEAPOLIS_METRO_BBOX,
    MINNEAPOLIS_SUBMARKETS,
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
from src.spatial.cities.san_diego import (
    SAN_DIEGO_DIVISION_BBOXES,
    SAN_DIEGO_DIVISIONS,
    SAN_DIEGO_METRO_BBOX,
    SAN_DIEGO_SUBMARKETS,
)
from src.spatial.cities.houston import (
    HOUSTON_DIVISION_BBOXES,
    HOUSTON_DIVISIONS,
    HOUSTON_METRO_BBOX,
    HOUSTON_SUBMARKETS,
)
from src.spatial.cities.indianapolis import (
    INDIANAPOLIS_DIVISION_BBOXES,
    INDIANAPOLIS_DIVISIONS,
    INDIANAPOLIS_METRO_BBOX,
    INDIANAPOLIS_SUBMARKETS,
)
from src.spatial.cities.wichita import (
    WICHITA_DIVISION_BBOXES,
    WICHITA_DIVISIONS,
    WICHITA_METRO_BBOX,
    WICHITA_SUBMARKETS,
)
from src.spatial.cities.chattanooga import (
    CHATTANOOGA_DIVISION_BBOXES,
    CHATTANOOGA_DIVISIONS,
    CHATTANOOGA_METRO_BBOX,
    CHATTANOOGA_SUBMARKETS,
)
from src.spatial.cities.cleveland import (
    CLEVELAND_DIVISION_BBOXES,
    CLEVELAND_DIVISIONS,
    CLEVELAND_METRO_BBOX,
    CLEVELAND_SUBMARKETS,
)
from src.spatial.cities.hartford import (
    HARTFORD_DIVISION_BBOXES,
    HARTFORD_DIVISIONS,
    HARTFORD_METRO_BBOX,
    HARTFORD_SUBMARKETS,
)
from src.spatial.cities.raleigh import (
    RALEIGH_DIVISION_BBOXES,
    RALEIGH_DIVISIONS,
    RALEIGH_METRO_BBOX,
    RALEIGH_SUBMARKETS,
)
from src.spatial.cities.san_antonio import (
    SAN_ANTONIO_DIVISION_BBOXES,
    SAN_ANTONIO_DIVISIONS,
    SAN_ANTONIO_METRO_BBOX,
    SAN_ANTONIO_SUBMARKETS,
)
from src.spatial.cities.sacramento import (
    SACRAMENTO_DIVISION_BBOXES,
    SACRAMENTO_DIVISIONS,
    SACRAMENTO_METRO_BBOX,
    SACRAMENTO_SUBMARKETS,
)
from src.spatial.cities.reno import (
    RENO_DIVISION_BBOXES,
    RENO_DIVISIONS,
    RENO_METRO_BBOX,
    RENO_SUBMARKETS,
)
from src.spatial.cities.spokane import (
    SPOKANE_DIVISION_BBOXES,
    SPOKANE_DIVISIONS,
    SPOKANE_METRO_BBOX,
    SPOKANE_SUBMARKETS,
)
from src.spatial.cities.dayton import (
    DAYTON_DIVISION_BBOXES,
    DAYTON_DIVISIONS,
    DAYTON_METRO_BBOX,
    DAYTON_SUBMARKETS,
)
from src.spatial.cities.tulsa import (
    TULSA_DIVISION_BBOXES,
    TULSA_DIVISIONS,
    TULSA_METRO_BBOX,
    TULSA_SUBMARKETS,
)
from src.spatial.cities.el_paso import (
    EL_PASO_DIVISION_BBOXES,
    EL_PASO_DIVISIONS,
    EL_PASO_METRO_BBOX,
    EL_PASO_SUBMARKETS,
)
from src.spatial.cities.durham import (
    DURHAM_DIVISION_BBOXES,
    DURHAM_DIVISIONS,
    DURHAM_METRO_BBOX,
    DURHAM_SUBMARKETS,
)
from src.spatial.cities.dallas import (
    DALLAS_DIVISION_BBOXES,
    DALLAS_DIVISIONS,
    DALLAS_METRO_BBOX,
    DALLAS_SUBMARKETS,
)
from src.spatial.cities.louisville import (
    LOUISVILLE_DIVISION_BBOXES,
    LOUISVILLE_DIVISIONS,
    LOUISVILLE_METRO_BBOX,
    LOUISVILLE_SUBMARKETS,
)
from src.spatial.cities.san_jose import (
    SAN_JOSE_DIVISION_BBOXES,
    SAN_JOSE_DIVISIONS,
    SAN_JOSE_METRO_BBOX,
    SAN_JOSE_SUBMARKETS,
)
from src.spatial.cities.tampa import (
    TAMPA_DIVISION_BBOXES,
    TAMPA_DIVISIONS,
    TAMPA_METRO_BBOX,
    TAMPA_SUBMARKETS,
)
from src.spatial.cities.las_vegas import (
    LAS_VEGAS_DIVISION_BBOXES,
    LAS_VEGAS_DIVISIONS,
    LAS_VEGAS_METRO_BBOX,
    LAS_VEGAS_SUBMARKETS,
)
from src.spatial.cities.boise import (
    BOISE_DIVISION_BBOXES,
    BOISE_DIVISIONS,
    BOISE_METRO_BBOX,
    BOISE_SUBMARKETS,
)
from src.spatial.cities.fort_worth import (
    FORT_WORTH_DIVISION_BBOXES,
    FORT_WORTH_DIVISIONS,
    FORT_WORTH_METRO_BBOX,
    FORT_WORTH_SUBMARKETS,
)
from src.spatial.cities.honolulu import (
    HONOLULU_DIVISION_BBOXES,
    HONOLULU_DIVISIONS,
    HONOLULU_METRO_BBOX,
    HONOLULU_SUBMARKETS,
)
from src.spatial.cities.orlando import (
    ORLANDO_DIVISION_BBOXES,
    ORLANDO_DIVISIONS,
    ORLANDO_METRO_BBOX,
    ORLANDO_SUBMARKETS,
)
from src.spatial.cities.gainesville import (
    GAINESVILLE_DIVISION_BBOXES,
    GAINESVILLE_DIVISIONS,
    GAINESVILLE_METRO_BBOX,
    GAINESVILLE_SUBMARKETS,
)
from src.spatial.cities.miami_dade import (
    MIAMI_DADE_DIVISION_BBOXES,
    MIAMI_DADE_DIVISIONS,
    MIAMI_DADE_METRO_BBOX,
    MIAMI_DADE_SUBMARKETS,
)
from src.spatial.cities.ocala import (
    OCALA_DIVISION_BBOXES,
    OCALA_DIVISIONS,
    OCALA_METRO_BBOX,
    OCALA_SUBMARKETS,
)
from src.spatial.cities.memphis import (
    MEMPHIS_DIVISION_BBOXES,
    MEMPHIS_DIVISIONS,
    MEMPHIS_METRO_BBOX,
    MEMPHIS_SUBMARKETS,
)
from src.spatial.cities.phoenix import (
    PHOENIX_DIVISION_BBOXES,
    PHOENIX_DIVISIONS,
    PHOENIX_METRO_BBOX,
    PHOENIX_SUBMARKETS,
)
from src.spatial.cities.albuquerque import (
    ALBUQUERQUE_DIVISION_BBOXES,
    ALBUQUERQUE_DIVISIONS,
    ALBUQUERQUE_METRO_BBOX,
    ALBUQUERQUE_SUBMARKETS,
)
from src.spatial.cities.st_louis import (
    ST_LOUIS_DIVISION_BBOXES,
    ST_LOUIS_DIVISIONS,
    ST_LOUIS_METRO_BBOX,
    ST_LOUIS_SUBMARKETS,
)
from src.spatial.cities.aurora import (
    AURORA_DIVISION_BBOXES,
    AURORA_DIVISIONS,
    AURORA_METRO_BBOX,
    AURORA_SUBMARKETS,
)
from src.spatial.cities.henderson import (
    HENDERSON_DIVISION_BBOXES,
    HENDERSON_DIVISIONS,
    HENDERSON_METRO_BBOX,
    HENDERSON_SUBMARKETS,
)
from src.spatial.cities.virginia_beach import (
    VIRGINIA_BEACH_CENTER,
    VIRGINIA_BEACH_DIVISION_BBOXES,
    VIRGINIA_BEACH_DIVISIONS,
    VIRGINIA_BEACH_METRO_BBOX,
    VIRGINIA_BEACH_SUBMARKETS,
)
from src.spatial.cities.omaha import (
    OMAHA_DIVISION_BBOXES,
    OMAHA_DIVISIONS,
    OMAHA_METRO_BBOX,
    OMAHA_SUBMARKETS,
)
from src.spatial.cities.toledo import (
    TOLEDO_DIVISION_BBOXES,
    TOLEDO_DIVISIONS,
    TOLEDO_METRO_BBOX,
    TOLEDO_SUBMARKETS,
)
from src.spatial.cities.buffalo import (
    BUFFALO_DIVISION_BBOXES,
    BUFFALO_DIVISIONS,
    BUFFALO_METRO_BBOX,
    BUFFALO_SUBMARKETS,
)
from src.spatial.cities.rochester import (
    ROCHESTER_CENTER,
    ROCHESTER_DIVISION_BBOXES,
    ROCHESTER_DIVISIONS,
    ROCHESTER_METRO_BBOX,
    ROCHESTER_SUBMARKETS,
)
from src.spatial.cities.syracuse import (
    SYRACUSE_DIVISION_BBOXES,
    SYRACUSE_DIVISIONS,
    SYRACUSE_METRO_BBOX,
    SYRACUSE_SUBMARKETS,
)
from src.spatial.cities.lynchburg import (
    LYNCHBURG_CENTER,
    LYNCHBURG_DIVISION_BBOXES,
    LYNCHBURG_DIVISIONS,
    LYNCHBURG_METRO_BBOX,
    LYNCHBURG_SUBMARKETS,
)
from src.spatial.cities.greenville import (
    GREENVILLE_DIVISION_BBOXES,
    GREENVILLE_DIVISIONS,
    GREENVILLE_METRO_BBOX,
    GREENVILLE_SUBMARKETS,
)
from src.spatial.cities.anchorage import (
    ANCHORAGE_CENTER,
    ANCHORAGE_DIVISION_BBOXES,
    ANCHORAGE_DIVISIONS,
    ANCHORAGE_METRO_BBOX,
    ANCHORAGE_SUBMARKETS,
)
from src.spatial.cities.tucson import (
    TUCSON_DIVISION_BBOXES,
    TUCSON_DIVISIONS,
    TUCSON_METRO_BBOX,
    TUCSON_SUBMARKETS,
)
from src.spatial.cities.amarillo import (
    AMARILLO_CENTER,
    AMARILLO_DIVISION_BBOXES,
    AMARILLO_DIVISIONS,
    AMARILLO_METRO_BBOX,
    AMARILLO_SUBMARKETS,
)
from src.spatial.cities.beaumont import (
    BEAUMONT_DIVISION_BBOXES,
    BEAUMONT_DIVISIONS,
    BEAUMONT_METRO_BBOX,
    BEAUMONT_SUBMARKETS,
)
from src.spatial.cities.waco import (
    WACO_CENTER,
    WACO_DIVISION_BBOXES,
    WACO_DIVISIONS,
    WACO_METRO_BBOX,
    WACO_SUBMARKETS,
)
from src.spatial.cities.jackson_ms import (
    JACKSON_MS_CENTER,
    JACKSON_MS_DIVISION_BBOXES,
    JACKSON_MS_DIVISIONS,
    JACKSON_MS_METRO_BBOX,
    JACKSON_MS_SUBMARKETS,
)
from src.spatial.cities.macon_bibb import (
    MACON_BIBB_CENTER,
    MACON_BIBB_DIVISION_BBOXES,
    MACON_BIBB_DIVISIONS,
    MACON_BIBB_METRO_BBOX,
    MACON_BIBB_SUBMARKETS,
)
from src.spatial.cities.tyler import (
    TYLER_CENTER,
    TYLER_DIVISION_BBOXES,
    TYLER_DIVISIONS,
    TYLER_METRO_BBOX,
    TYLER_SUBMARKETS,
)
from src.spatial.cities.augusta import (
    AUGUSTA_CENTER,
    AUGUSTA_DIVISION_BBOXES,
    AUGUSTA_DIVISIONS,
    AUGUSTA_METRO_BBOX,
    AUGUSTA_SUBMARKETS,
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
    COLUMBUS_GA = "columbus_ga"
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
    PRINCE_GEORGES = "prince_georges"
    COLUMBUS = "columbus"
    NASHVILLE = "nashville"
    KANSAS_CITY = "kansas_city"
    MINNEAPOLIS = "minneapolis"
    PIERCE = "pierce"
    MILWAUKEE = "milwaukee"
    CHARLOTTE = "charlotte"
    PITTSBURGH = "pittsburgh"
    SAN_DIEGO = "san_diego"
    HOUSTON = "houston"
    INDIANAPOLIS = "indianapolis"
    WICHITA = "wichita"
    CHATTANOOGA = "chattanooga"
    CLEVELAND = "cleveland"
    HARTFORD = "hartford"
    RALEIGH = "raleigh"
    SAN_ANTONIO = "san_antonio"
    SACRAMENTO = "sacramento"
    RENO = "reno"
    SPOKANE = "spokane"
    DAYTON = "dayton"
    TULSA = "tulsa"
    EL_PASO = "el_paso"
    DURHAM = "durham"
    DALLAS = "dallas"
    LOUISVILLE = "louisville"
    PORTLAND = "portland"
    SAN_JOSE = "san_jose"
    TAMPA = "tampa"
    LAS_VEGAS = "las_vegas"
    BOISE = "boise"
    MELBOURNE = "melbourne"
    FORT_WORTH = "fort_worth"
    HONOLULU = "honolulu"
    ORLANDO = "orlando"
    GAINESVILLE = "gainesville"
    OCALA = "ocala"
    MIAMI_DADE = "miami_dade"
    MEMPHIS = "memphis"
    PHOENIX = "phoenix"
    ALBUQUERQUE = "albuquerque"
    ST_LOUIS = "st_louis"
    AURORA = "aurora"
    HENDERSON = "henderson"
    VIRGINIA_BEACH = "virginia_beach"
    OMAHA = "omaha"
    TOLEDO = "toledo"
    AMARILLO = "amarillo"
    BEAUMONT = "beaumont"
    WACO = "waco"
    JACKSON_MS = "jackson_ms"
    MACON_BIBB = "macon_bibb"
    TYLER = "tyler"
    AUGUSTA = "augusta"
    BUFFALO = "buffalo"
    ROCHESTER = "rochester"
    SYRACUSE = "syracuse"
    LYNCHBURG = "lynchburg"
    GREENVILLE = "greenville"
    ANCHORAGE = "anchorage"
    TUCSON = "tucson"


class FeedType(str, Enum):
    """Municipal data feed types."""
    PERMITS = "permits"
    COMPLAINTS_311 = "311"
    SLA = "sla"
    DEEDS = "deeds"
    # Signal-survey families (US-72). These make a feed *ingestible* — a
    # registration only lands via its own ticket once the feed clears its
    # family gate, and each signal carries its own ablation requirement
    # before it may enter LIMS.
    CRIME = "crime"
    STREET_CUT = "street_cut"
    EVICTIONS = "evictions"
    STR = "str"

    # US-363 context-measurement families. Neither is a signal in the
    # move-in/out sense: both are periodic per-asset measurements that ride
    # one shared ``ContextObservationEvent`` onto ``EnrichedH3Feature`` as
    # covariates, subject to the standing ablation rule before LIMS.
    ENERGY_BENCHMARK = "energy_benchmark"
    BIKE_PED = "bike_ped"

    # US-363 §1.2/§2.1. A GBFS system maps one-to-one onto a metro, so docked
    # bikeshare is city-shaped and registers here. The other three US-363
    # components (POI deltas, OpenFEMA, NREL AFDC) are national files that
    # cover every metro at once and live in `national_feeds.py` instead.
    GBFS = "gbfs"


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
    """Specification for a municipal dataset endpoint and ingestion configuration.

    Acquisition keys that used to live in a free-form ``extra`` dict are now
    first-class typed fields (US-186). Every field defaults to the old
    "key-absent" semantics, so existing callers behave identically. ``scope``
    was the only genuinely-dead key and has been dropped.
    """

    endpoint: str
    platform: str = "socrata"  # "socrata", "arcgis", "ckan", etc.
    watermark_col: str = ""
    id_keys: List[str] = field(default_factory=list)
    topic: str = ""
    interval_seconds: float = 300.0
    producer_key: str = ""
    # --- typed acquisition keys (formerly ``extra``) ---
    endpoint_by_year: Dict[str, str] = field(default_factory=dict)
    watermark_type: Optional[str] = None
    watermark_format: Optional[str] = None
    watermark_exclude: List[str] = field(default_factory=list)
    order_by: Optional[str] = None
    id_col: Optional[str] = None
    select: Optional[str] = None
    fallback_endpoints: List[str] = field(default_factory=list)
    where: Optional[str] = None
    needs_geocode: bool = False
    geocode_context: Optional[str] = None
    field_map: Dict[str, Any] = field(default_factory=dict)
    ingestion_mode: str = "incremental"
    oid_field: Optional[str] = None
    max_record_count: Optional[int] = None
    expected_cadence_days: Optional[int] = None
    alarm_exempt: bool = False
    alarm_exempt_reason: Optional[str] = None
    annual_rotation: bool = False
    companion_endpoints: Dict[str, Any] = field(default_factory=dict)
    proxy_for: Optional[str] = None
    retention_days: Optional[int] = None
    rolling_window_days: Optional[int] = None
    rollover: Optional[str] = None
    state_plane_crs: Optional[str] = None
    state_plane_units: Optional[str] = None
    state_plane_x_col: Optional[str] = None
    state_plane_y_col: Optional[str] = None
    parcel_join: Dict[str, Any] = field(default_factory=dict)
    non_spatial: Optional[bool] = None
    zip_member: Optional[str] = None


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
_HANDWRITTEN_ALIASES: Dict[str, CityId] = {
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

    # Prince George's County
    "prince_georges": CityId.PRINCE_GEORGES,
    "prince georges": CityId.PRINCE_GEORGES,
    "prince_georges_county": CityId.PRINCE_GEORGES,
    "prince george's county": CityId.PRINCE_GEORGES,
    "pgco": CityId.PRINCE_GEORGES,
    "pgcounty": CityId.PRINCE_GEORGES,

    # Columbus
    "columbus": CityId.COLUMBUS,
    "columbus_oh": CityId.COLUMBUS,
    # Columbus, GA — do not claim plain 'columbus'
    "columbus_ga": CityId.COLUMBUS_GA,
    "columbus-ga": CityId.COLUMBUS_GA,
    "columbus ga": CityId.COLUMBUS_GA,

    # Nashville
    "nashville": CityId.NASHVILLE,
    "nashville_tn": CityId.NASHVILLE,

    # Kansas City
    "kansas_city": CityId.KANSAS_CITY,
    "kc_mo": CityId.KANSAS_CITY,
    "kcmo": CityId.KANSAS_CITY,

    # Minneapolis
    "minneapolis": CityId.MINNEAPOLIS,
    "mpls": CityId.MINNEAPOLIS,
    "minneapolis_mn": CityId.MINNEAPOLIS,

    # Pierce County, WA
    "pierce": CityId.PIERCE,
    "pierce_county": CityId.PIERCE,
    "pierce-county": CityId.PIERCE,
    "pierce county": CityId.PIERCE,
    "tacoma": CityId.PIERCE,
    "tac": CityId.PIERCE,

    # Milwaukee, WI
    "milwaukee": CityId.MILWAUKEE,
    "mke": CityId.MILWAUKEE,
    "mke_wi": CityId.MILWAUKEE,

    # Charlotte / Mecklenburg, NC
    "charlotte": CityId.CHARLOTTE,
    "charlotte_nc": CityId.CHARLOTTE,
    "charlotte_mecklenburg": CityId.CHARLOTTE,
    "mecklenburg": CityId.CHARLOTTE,

    # Pittsburgh, PA
    "pittsburgh": CityId.PITTSBURGH,
    "pgh": CityId.PITTSBURGH,
    "pittsburgh_pa": CityId.PITTSBURGH,
    "burgh": CityId.PITTSBURGH,
    "san_diego": CityId.SAN_DIEGO,
    "sandiego": CityId.SAN_DIEGO,
    "san diego": CityId.SAN_DIEGO,
    "san-diego": CityId.SAN_DIEGO,
    "sd": CityId.SAN_DIEGO,

    # Houston, TX
    "houston": CityId.HOUSTON,
    "houston_tx": CityId.HOUSTON,
    "houston-tx": CityId.HOUSTON,
    "houston tx": CityId.HOUSTON,
    "htx": CityId.HOUSTON,
    "h-town": CityId.HOUSTON,

    # Indianapolis / Marion County, IN
    "indianapolis": CityId.INDIANAPOLIS,
    "indianapolis_in": CityId.INDIANAPOLIS,
    "indianapolis in": CityId.INDIANAPOLIS,
    "indy": CityId.INDIANAPOLIS,

    # Wichita, KS / Sedgwick County
    "wichita": CityId.WICHITA,
    "wichita_ks": CityId.WICHITA,
    "wichita ks": CityId.WICHITA,
    "ict": CityId.WICHITA,

    # Chattanooga & Hamilton County, Tennessee
    "chattanooga": CityId.CHATTANOOGA,
    "chattanooga_tn": CityId.CHATTANOOGA,
    "chattanooga tn": CityId.CHATTANOOGA,
    "hamilton_county_tn": CityId.CHATTANOOGA,
    "hamilton county tn": CityId.CHATTANOOGA,
    "scenic_city": CityId.CHATTANOOGA,

    # Cleveland & Cuyahoga County, Ohio
    "cleveland": CityId.CLEVELAND,
    "cleveland_oh": CityId.CLEVELAND,
    "cleveland oh": CityId.CLEVELAND,
    "cuyahoga_county": CityId.CLEVELAND,
    "cuyahoga county": CityId.CLEVELAND,
    "the_land": CityId.CLEVELAND,

    # Hartford, CT / Hartford County
    "hartford": CityId.HARTFORD,
    "hartford_ct": CityId.HARTFORD,
    "hartford ct": CityId.HARTFORD,
    "hartford_county": CityId.HARTFORD,
    "hartford county": CityId.HARTFORD,

    # Raleigh / Wake County, NC
    "raleigh": CityId.RALEIGH,
    "raleigh_nc": CityId.RALEIGH,
    "raleigh nc": CityId.RALEIGH,
    "wake_county": CityId.RALEIGH,
    "wake county": CityId.RALEIGH,

    # San Antonio / Bexar County, TX
    "san_antonio": CityId.SAN_ANTONIO,
    "san-antonio": CityId.SAN_ANTONIO,
    "san antonio": CityId.SAN_ANTONIO,
    "san_antonio_tx": CityId.SAN_ANTONIO,
    "san antonio tx": CityId.SAN_ANTONIO,
    "bexar_county": CityId.SAN_ANTONIO,
    "bexar county": CityId.SAN_ANTONIO,

    # Sacramento / Sacramento County, CA
    "sacramento": CityId.SACRAMENTO,
    "sacramento_ca": CityId.SACRAMENTO,
    "sacramento ca": CityId.SACRAMENTO,
    "sacramento_county": CityId.SACRAMENTO,
    "sacramento county": CityId.SACRAMENTO,

    # Reno / Washoe County, NV
    "reno": CityId.RENO,
    "reno_nv": CityId.RENO,
    "reno nv": CityId.RENO,
    "washoe_county": CityId.RENO,
    "washoe county": CityId.RENO,

    # Spokane / Spokane County, WA
    "spokane": CityId.SPOKANE,
    "spokane_wa": CityId.SPOKANE,
    "spokane wa": CityId.SPOKANE,
    "spokane_county": CityId.SPOKANE,
    "spokane county": CityId.SPOKANE,

    # Dayton / Montgomery County, OH
    "dayton": CityId.DAYTON,
    "dayton_oh": CityId.DAYTON,
    "dayton oh": CityId.DAYTON,
    "montgomery_county_oh": CityId.DAYTON,
    "montgomery county oh": CityId.DAYTON,

    # Tulsa / Tulsa County, OK
    "tulsa": CityId.TULSA,
    "tulsa_ok": CityId.TULSA,
    "tulsa ok": CityId.TULSA,
    "tulsa_county": CityId.TULSA,
    "tulsa county": CityId.TULSA,

    # El Paso / El Paso County, TX
    "el_paso": CityId.EL_PASO,
    "el paso": CityId.EL_PASO,
    "el_paso_tx": CityId.EL_PASO,
    "el paso tx": CityId.EL_PASO,
    "el_paso_county": CityId.EL_PASO,
    "el paso county": CityId.EL_PASO,

    # Durham / Durham County, NC
    "durham": CityId.DURHAM,
    "durham_nc": CityId.DURHAM,
    "durham nc": CityId.DURHAM,
    "durham_county": CityId.DURHAM,
    "durham county": CityId.DURHAM,

    # Dallas / Dallas County, TX
    "dallas": CityId.DALLAS,
    "dallas_tx": CityId.DALLAS,
    "dallas tx": CityId.DALLAS,
    "dallas_county": CityId.DALLAS,
    "dallas county": CityId.DALLAS,
    "big_d": CityId.DALLAS,

    # Louisville / Jefferson County, KY
    "louisville": CityId.LOUISVILLE,
    "louisville_ky": CityId.LOUISVILLE,
    "louisville ky": CityId.LOUISVILLE,
    "jefferson_county_ky": CityId.LOUISVILLE,
    "jefferson county ky": CityId.LOUISVILLE,

    # Portland / Multnomah County, OR
    "portland": CityId.PORTLAND,
    "portland_or": CityId.PORTLAND,
    "portland or": CityId.PORTLAND,
    "multnomah_county": CityId.PORTLAND,
    "multnomah county": CityId.PORTLAND,

    # San Jose / Santa Clara County
    "san_jose": CityId.SAN_JOSE,
    "san-jose": CityId.SAN_JOSE,
    "san jose": CityId.SAN_JOSE,
    "san_jose_ca": CityId.SAN_JOSE,
    "san jose ca": CityId.SAN_JOSE,
    "santa_clara_county": CityId.SAN_JOSE,
    "santa clara county": CityId.SAN_JOSE,

    # Tampa / Hillsborough County
    "tampa": CityId.TAMPA,
    "tampa_fl": CityId.TAMPA,
    "tampa fl": CityId.TAMPA,
    "hillsborough_county": CityId.TAMPA,
    "hillsborough county": CityId.TAMPA,

    # Las Vegas / Clark County
    "las_vegas": CityId.LAS_VEGAS,
    "las-vegas": CityId.LAS_VEGAS,
    "las vegas": CityId.LAS_VEGAS,
    "las_vegas_nv": CityId.LAS_VEGAS,
    "las vegas nv": CityId.LAS_VEGAS,
    "clark_county": CityId.LAS_VEGAS,
    "clark county": CityId.LAS_VEGAS,
    "vegas": CityId.LAS_VEGAS,

    # Boise / Ada County, ID
    "boise": CityId.BOISE,
    "boise_id": CityId.BOISE,
    "boise id": CityId.BOISE,
    "ada_county": CityId.BOISE,
    "ada county": CityId.BOISE,

    # Fort Worth / Tarrant County, TX
    "fort_worth": CityId.FORT_WORTH,
    "fort worth": CityId.FORT_WORTH,
    "fortworth": CityId.FORT_WORTH,
    "fort worth tx": CityId.FORT_WORTH,
    "tarrant_county": CityId.FORT_WORTH,
    "tarrant county": CityId.FORT_WORTH,

    # Honolulu / City and County of Honolulu (Oahu)
    "honolulu": CityId.HONOLULU,
    "honolulu_hi": CityId.HONOLULU,
    "honolulu hi": CityId.HONOLULU,
    "hnl": CityId.HONOLULU,
    "oahu": CityId.HONOLULU,
    "city_and_county_of_honolulu": CityId.HONOLULU,
    "city and county of honolulu": CityId.HONOLULU,

    # Orlando / Orange County, FL
    "orlando": CityId.ORLANDO,
    "orlando_fl": CityId.ORLANDO,
    "orlando fl": CityId.ORLANDO,
    "mco": CityId.ORLANDO,
    "orange_county_fl": CityId.ORLANDO,
    "orange county fl": CityId.ORLANDO,

    # Gainesville, FL
    "gainesville": CityId.GAINESVILLE,
    "gainesville_fl": CityId.GAINESVILLE,
    "gainesville fl": CityId.GAINESVILLE,

    # Ocala / Marion County, FL
    "ocala": CityId.OCALA,
    "ocala_fl": CityId.OCALA,
    "ocala fl": CityId.OCALA,

    # Miami-Dade County, FL (not City of Miami / Broward — ADR 0007)
    "miami_dade": CityId.MIAMI_DADE,
    "miami-dade": CityId.MIAMI_DADE,
    "miami dade": CityId.MIAMI_DADE,
    "miami_dade_county": CityId.MIAMI_DADE,
    "miami-dade county": CityId.MIAMI_DADE,
    "miami dade county": CityId.MIAMI_DADE,
    "mdc": CityId.MIAMI_DADE,

    # Memphis / Shelby County, TN
    "memphis": CityId.MEMPHIS,
    "memphis_tn": CityId.MEMPHIS,
    "memphis tn": CityId.MEMPHIS,
    "mem": CityId.MEMPHIS,
    "shelby_county": CityId.MEMPHIS,
    "shelby county": CityId.MEMPHIS,
    "shelby_county_tn": CityId.MEMPHIS,

    # Phoenix / Maricopa County, AZ
    "phoenix": CityId.PHOENIX,
    "phx": CityId.PHOENIX,
    "phoenix_az": CityId.PHOENIX,
    "phoenix az": CityId.PHOENIX,
    "maricopa_county": CityId.PHOENIX,
    "maricopa county": CityId.PHOENIX,

    # Albuquerque / Bernalillo County, NM
    "albuquerque": CityId.ALBUQUERQUE,
    "albuquerque_nm": CityId.ALBUQUERQUE,
    "albuquerque nm": CityId.ALBUQUERQUE,
    "abq": CityId.ALBUQUERQUE,
    "bernalillo": CityId.ALBUQUERQUE,
    "bernalillo_county": CityId.ALBUQUERQUE,
    "bernalillo county": CityId.ALBUQUERQUE,

    # City of St. Louis, MO (independent city — not St. Louis County)
    "st_louis": CityId.ST_LOUIS,
    "stl": CityId.ST_LOUIS,
    "saint_louis": CityId.ST_LOUIS,
    "st-louis": CityId.ST_LOUIS,
    "st louis": CityId.ST_LOUIS,

    # Aurora, CO
    "aurora": CityId.AURORA,
    "aurora_co": CityId.AURORA,
    "aurora-co": CityId.AURORA,
    "aurora co": CityId.AURORA,

    # Henderson, NV
    "henderson": CityId.HENDERSON,
    "henderson_nv": CityId.HENDERSON,
    "henderson-nv": CityId.HENDERSON,
    "henderson nv": CityId.HENDERSON,

    # Virginia Beach, VA
    "virginia_beach": CityId.VIRGINIA_BEACH,
    "virginia-beach": CityId.VIRGINIA_BEACH,
    "virginia beach": CityId.VIRGINIA_BEACH,
    "va_beach": CityId.VIRGINIA_BEACH,
    "va beach": CityId.VIRGINIA_BEACH,

    # Omaha, NE
    "omaha": CityId.OMAHA,
    "omaha_ne": CityId.OMAHA,
    "omaha-ne": CityId.OMAHA,
    "omaha ne": CityId.OMAHA,
    "oma": CityId.OMAHA,

    # Toledo, OH
    "toledo": CityId.TOLEDO,
    "toledo_oh": CityId.TOLEDO,
    "toledo-oh": CityId.TOLEDO,
    "toledo oh": CityId.TOLEDO,

    # Amarillo, TX
    "amarillo": CityId.AMARILLO,
    "amarillo_tx": CityId.AMARILLO,
    "amarillo tx": CityId.AMARILLO,
    # Beaumont, TX
    "beaumont": CityId.BEAUMONT,
    "beaumont_tx": CityId.BEAUMONT,
    "beaumont-tx": CityId.BEAUMONT,
    "beaumont tx": CityId.BEAUMONT,
    # Waco, TX
    "waco": CityId.WACO,
    "waco_tx": CityId.WACO,
    "waco tx": CityId.WACO,
    # Jackson, MS
    "jackson_ms": CityId.JACKSON_MS,
    "jackson-ms": CityId.JACKSON_MS,
    "jackson ms": CityId.JACKSON_MS,
    # Macon-Bibb, GA
    "macon_bibb": CityId.MACON_BIBB,
    "macon-bibb": CityId.MACON_BIBB,
    "macon bibb": CityId.MACON_BIBB,
    "macon": CityId.MACON_BIBB,
    "macon_ga": CityId.MACON_BIBB,
    # Tyler, TX
    "tyler": CityId.TYLER,
    "tyler_tx": CityId.TYLER,
    "tyler tx": CityId.TYLER,
    # Augusta, GA
    "augusta": CityId.AUGUSTA,
    "augusta_ga": CityId.AUGUSTA,
    "augusta ga": CityId.AUGUSTA,
    # Buffalo, NY
    "buffalo": CityId.BUFFALO,
    "buffalo_ny": CityId.BUFFALO,
    "buffalo-ny": CityId.BUFFALO,
    "buffalo ny": CityId.BUFFALO,

    # Rochester, NY
    "rochester": CityId.ROCHESTER,
    "rochester_ny": CityId.ROCHESTER,
    "rochester-ny": CityId.ROCHESTER,
    "rochester ny": CityId.ROCHESTER,

    # Syracuse, NY
    "syracuse": CityId.SYRACUSE,
    "syracuse_ny": CityId.SYRACUSE,
    "syracuse-ny": CityId.SYRACUSE,
    "syracuse ny": CityId.SYRACUSE,

    # Lynchburg, VA
    "lynchburg": CityId.LYNCHBURG,
    "lynchburg_va": CityId.LYNCHBURG,
    "lynchburg-va": CityId.LYNCHBURG,
    "lynchburg va": CityId.LYNCHBURG,

    # Greenville, SC
    "greenville": CityId.GREENVILLE,
    "greenville_sc": CityId.GREENVILLE,
    "greenville-sc": CityId.GREENVILLE,
    "greenville sc": CityId.GREENVILLE,

    # Anchorage, AK
    "anchorage": CityId.ANCHORAGE,
    "anchorage_ak": CityId.ANCHORAGE,
    "anchorage-ak": CityId.ANCHORAGE,
    "anchorage ak": CityId.ANCHORAGE,

    # Tucson, AZ
    "tucson": CityId.TUCSON,
    "tucson_az": CityId.TUCSON,
    "tucson-az": CityId.TUCSON,
    "tucson az": CityId.TUCSON,
    "tuscon": CityId.TUCSON,
}


def normalize_city(city_id: Optional[str]) -> Optional[CityId]:
    """Normalize user-supplied city identifier to canonical CityId Enum or None if unknown."""
    if not city_id:
        return None
    c = str(city_id).strip().lower()
    return ALIASES.get(c, None)


# US-364: USDA FNS SNAP Retailer Locator, registered as FeedType.SLA — the
# food-retail authorization slice (say so in feature names). One national
# FeatureServer covers every metro, so the registration is a single shared
# spec parameterized by a State where-clause (state-level coarseness is
# accepted for v1: rows outside the metro bbox still index global H3 cells —
# H3SpatialIndexer has no bbox gate — and metro scoping stays downstream).
#
# Verified live 2026-08-27: fields are Record_ID / Store_Name /
# Store_Street_Address / Additonal_Address (sic) / City / State / Zip_Code /
# Zip4 / County / Store_Type / Latitude / Longitude / Incentive_Program /
# Grantee_Name / ObjectId; Record_ID is unique across all 252,080 rows and is
# the retailer/record number. The live layer carries NO authorization-date
# fields (the auth start/end dates exist only in FNS's static 2005–2025
# historical zip), so events carry null issued/expiry and the feed ingests as
# a snapshot: a full registry pull per cycle whose cross-run id-dedup diff is
# the open/close signal (KC SLA precedent, US-134). FNS states the data is
# updated every 2 weeks, hence the 14-day cadence.
SNAP_SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["Record_ID"],
    "license_type": ["Store_Type"],
    "dba": ["Store_Name"],
    "latitude": ["Latitude"],
    "longitude": ["Longitude"],
    "address_street": ["Store_Street_Address"],
    "borough": ["City"],
    "zipcode": ["Zip_Code"],
}


def snap_sla_spec(state: str) -> DatasetSpec:
    """Build the SNAP SLA DatasetSpec for one metro's state slice."""
    return DatasetSpec(
        endpoint=settings.arcgis_snap_retailers_url,
        platform="arcgis",
        watermark_col="",
        id_keys=["Record_ID", "ObjectId"],
        topic=settings.topic_sla,
        interval_seconds=1800.0,
        producer_key="sla",
        expected_cadence_days=14,
        ingestion_mode="snapshot",
        oid_field="ObjectId",
        max_record_count=1000,
        where=f"State = '{state}'",
        field_map=SNAP_SLA_FIELD_MAP,
    )


_HANDWRITTEN_REGISTRY: Dict[CityId, CityRegistration] = {
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

                expected_cadence_days=7,
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_311_endpoint,
                platform="socrata",
                watermark_col="created_date",
                id_keys=["unique_key", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_sla_endpoint,
                platform="socrata",
                watermark_col="effectivedate",
                id_keys=["licensepermitid", "legacyserialnumber", "serial_number", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.socrata_deeds_endpoint,
                platform="socrata",
                watermark_col="recorded_datetime",
                id_keys=["document_id", "doc_id", "id"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                # NYC ACRIS record-to-date: source refreshes (rowsUpdatedAt
                # 2026-08-10, active) but newest recorded_datetime lags ~26d
                # (2026-07-31) — the DCP extract's recording lag. Alarm at
                # 2xN=42d (US-164).
                
                expected_cadence_days=21,
            ),
            # US-71: current-year YTD incident set (monthly publishing -> G11
            # cadence declaration; the staleness monitor alarms at 60d).
            FeedType.CRIME: DatasetSpec(
                endpoint=settings.socrata_nyc_crime_endpoint,
                platform="socrata",
                watermark_col="cmplnt_fr_dt",
                id_keys=["cmplnt_num"],
                topic=settings.topic_crime,
                interval_seconds=1800.0,
                producer_key="crime",
                
                expected_cadence_days=30,
            ),
            # US-93: Marshal's executed evictions — NYC-only context/validation,
            # never a LIMS input (single-metro asymmetry rule). Feed carries
            # lat/lon directly (verified 2026-08-24); ~8.4% newest-window geocode
            # gap == published gap, G5 passes.
            FeedType.EVICTIONS: DatasetSpec(
                endpoint=settings.socrata_nyc_evictions_endpoint,
                platform="socrata",
                watermark_col="executed_date",
                id_keys=["court_index_number", "docket_number"],
                topic=settings.topic_evictions,
                interval_seconds=900.0,
                producer_key="evictions",
                
                expected_cadence_days=7,
                field_map={'eviction_id': ['court_index_number', 'docket_number'], 'latitude': ['latitude'], 'longitude': ['longitude'], 'executed_date': ['executed_date'], 'borough': ['borough'], 'zipcode': ['eviction_zip'], 'residential_commercial': ['residential_commercial_ind']},
            ),
            # US-363 §2.7: LL84 benchmarking disclosure. Annual — the whole
            # cohort republishes at once, so `report_year` is the watermark and
            # it is a text one (Socrata types the column as a string).
            # Re-probed 2026-08-28: max report_year 2024, n=103,259 (2024
            # cohort 39,090; 1,354 null coordinates = 3.5%). Native lat/lng, so
            # needs_geocode stays false. alarm_exempt: a once-a-year feed is
            # stale by construction for ~11 months of every year.
            FeedType.ENERGY_BENCHMARK: DatasetSpec(
                endpoint=settings.socrata_nyc_energy_benchmark_endpoint,
                platform="socrata",
                watermark_col="report_year",
                id_keys=["property_id", "report_year"],
                topic=settings.topic_context_observations,
                interval_seconds=86400.0,
                producer_key="energy_benchmark",
                expected_cadence_days=365,
                watermark_type='text',
                watermark_format='%Y',
                alarm_exempt=True,
                alarm_exempt_reason='annual disclosure — one publication per year by design (US-363 §2.7)',
                field_map=NYC_ENERGY_FIELD_MAP,
            ),
            # US-363 §2.8: DOT automated counts. 21,016,786 15-minute rows,
            # max timestamp 2026-08-27T05:00 (same-day fresh, re-probed
            # 2026-08-28). The counts feed carries NO geometry: `sensor_id`
            # joins the counter registry `6up2-gnw8` (67 sensors), declared
            # here as a companion endpoint. The producer folds rows to one
            # observation per (sensor, mode, day) before producing — a
            # per-row event stream would be 21M messages for a per-hex mean.
            FeedType.BIKE_PED: DatasetSpec(
                endpoint=settings.socrata_nyc_bike_ped_counts_endpoint,
                platform="socrata",
                watermark_col="timestamp",
                id_keys=["flowid", "sensor_id", "timestamp"],
                topic=settings.topic_context_observations,
                interval_seconds=3600.0,
                producer_key="bike_ped",
                expected_cadence_days=1,
                # `status` is one of raw / modified / deleted (counted live
                # 2026-08-28: 18,579,562 / 2,435,656 / 1,568). A `deleted` row
                # is a retracted observation, so it is filtered server-side
                # rather than summed into a day's flow.
                where="status != 'deleted'",
                companion_endpoints={'sensor_registry': settings.socrata_nyc_bike_ped_sensors_endpoint},
                field_map=NYC_COUNTS_FIELD_MAP,
            ),

            # US-363 §2.1: docked bikeshare via snapshot diff. No watermark
            # column exists — GBFS changes state in place — so
            # `ingestion_mode: snapshot` and the station state store carry the
            # ingestion contract. Citi Bike (bkn), GBFS 2.3, 2,508 stations verified 2026-08-28.
            # LICENSE: Lyft's Data License Agreement permits product use and
            # bars re-hosting the raw feed; we derive events and never
            # republish. Lime/Bird/Spin/Bolt/Veo are barred outright.
            FeedType.GBFS: DatasetSpec(
                endpoint=settings.gbfs_nyc_discovery_endpoint,
                platform="gbfs",
                watermark_col="",
                id_keys=["station_id", "system_id"],
                topic=settings.topic_station_change,
                interval_seconds=3600.0,
                producer_key="gbfs",
                ingestion_mode="snapshot",
                expected_cadence_days=1,
                companion_endpoints={'system_id': 'bkn', 'operator': 'lyft'},
            ),
        },
    ),
    CityId.MELBOURNE: CityRegistration(
        city_id=CityId.MELBOURNE,
        name="Melbourne / Palm Bay / Titusville",
        state="FL",
        center={"lat": 28.0836, "lng": -80.6081},
        metro_bbox=MELBOURNE_METRO_BBOX,
        division_bboxes=MELBOURNE_DIVISION_BBOXES,
        submarkets=MELBOURNE_SUBMARKETS,
        divisions=MELBOURNE_DIVISIONS,
        job_suffix="melbourne",
        # Partial: PERMITS + SNAP SLA fallback (state-sliced 'FL').
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_brevard_permits_url,
                platform="arcgis",
                watermark_col="ISSUEDATE",
                id_keys=["FOLDERSEQUENCE", "OBJECTID0"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=1,
                oid_field="OBJECTID0",
                max_record_count=1000,
                order_by="ISSUEDATE DESC",
            ),
            # USDA FNS SNAP retailers as the SLA slice (Florida state filter).
            # Rows outside the metro bbox still carry global H3 tags; metro
            # scoping happens downstream in spatialization.
            FeedType.SLA: snap_sla_spec("FL"),
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
                
                expected_cadence_days=7,
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_chicago_311_endpoint,
                platform="socrata",
                watermark_col="created_date",
                id_keys=["sr_number", "unique_key", "id", "service_request_number"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_chicago_licenses_endpoint,
                platform="socrata",
                watermark_col="date_issued",
                id_keys=["license_id", "account_number", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.socrata_chicago_deeds_endpoint,
                platform="socrata",
                watermark_col="sale_date",
                id_keys=["doc_no", "row_id", "pin"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                # Cook County recorded-sales cadence: the dataset refreshes ~weekly
                # (rowsUpdatedAt 2026-08-19, active) but the newest sale_date lands
                # ~6 weeks back (2026-07-14) — the source's real close-to-record lag.
                # Alarm at 2xN=60d (US-164).
                
                expected_cadence_days=30,
            ),
            # US-71: CPD crime incidents (lat/lon verified 2026-08-24).
            FeedType.CRIME: DatasetSpec(
                endpoint=settings.socrata_chicago_crime_endpoint,
                platform="socrata",
                watermark_col="date",
                id_keys=["id", "case_number"],
                topic=settings.topic_crime,
                interval_seconds=1800.0,
                producer_key="crime",
                
                expected_cadence_days=7,
            ),
            # US-81: CDOT street closures (native coordinates, 99.9% coverage,
            # daily cadence). Disruption context only — never a LIMS term.
            # NYC's DOT street-construction permits (tqtj-sjs8) are NOT
            # registered: current rows are address-only (wkt State-Plane
            # geometry exists only on 2016-2023 rows), blocked on geocoding.
            FeedType.STREET_CUT: DatasetSpec(
                endpoint=settings.socrata_chicago_street_cut_endpoint,
                platform="socrata",
                watermark_col="applicationissueddate",
                id_keys=["applicationnumber", "uniquekey", "id"],
                topic=settings.topic_street_cut,
                interval_seconds=600.0,
                producer_key="street_cut",

                expected_cadence_days=7,
                needs_geocode=True,
                geocode_context="Chicago, IL",
                companion_endpoints={
                    "cdot_permits_master": settings.socrata_chicago_cdot_permits_endpoint,
                },
                field_map={
                    "permit_id": ["applicationnumber", "uniquekey"],
                    "permit_type": ["applicationtype", "applicationdescription"],
                    "work_type": ["worktypedescription", "worktype"],
                    "status": ["applicationstatus", "currentmilestone"],
                    "address": ["streetnumberfrom", "direction", "streetname", "suffix"],
                    "latitude": ["latitude"],
                    "longitude": ["longitude"],
                    "issued_date": ["applicationissueddate"],
                    "start_date": ["applicationstartdate"],
                    "end_date": ["applicationenddate"],
                    "fees": ["totalfees"],
                },
            ),
            # US-363 §2.7: Chicago energy benchmarking. Re-probed 2026-08-28:
            # max data_year 2023, n=28,329 — the feed genuinely lags NYC and
            # Seattle by a reporting year, which is a data property, not a
            # staleness incident. Native lat/lng plus a Socrata `location`
            # container (the field map reads both). `reporting_status` is the
            # compliance string here; there is no `compliancestatus` column.
            FeedType.ENERGY_BENCHMARK: DatasetSpec(
                endpoint=settings.socrata_chicago_energy_benchmark_endpoint,
                platform="socrata",
                watermark_col="data_year",
                id_keys=["row_id", "id", "data_year"],
                topic=settings.topic_context_observations,
                interval_seconds=86400.0,
                producer_key="energy_benchmark",
                expected_cadence_days=365,
                watermark_type='text',
                watermark_format='%Y',
                alarm_exempt=True,
                alarm_exempt_reason='annual disclosure, one reporting year behind by publication practice (US-363 §2.7)',
                field_map=CHICAGO_ENERGY_FIELD_MAP,
            ),

            # US-363 §2.1: docked bikeshare via snapshot diff. No watermark
            # column exists — GBFS changes state in place — so
            # `ingestion_mode: snapshot` and the station state store carry the
            # ingestion contract. Divvy (chi), GBFS 2.3, discovery verified 200 on 2026-08-28.
            # LICENSE: Lyft's Data License Agreement permits product use and
            # bars re-hosting the raw feed; we derive events and never
            # republish. Lime/Bird/Spin/Bolt/Veo are barred outright.
            FeedType.GBFS: DatasetSpec(
                endpoint=settings.gbfs_chicago_discovery_endpoint,
                platform="gbfs",
                watermark_col="",
                id_keys=["station_id", "system_id"],
                topic=settings.topic_station_change,
                interval_seconds=3600.0,
                producer_key="gbfs",
                ingestion_mode="snapshot",
                expected_cadence_days=1,
                companion_endpoints={'system_id': 'chi', 'operator': 'lyft'},
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
                
                expected_cadence_days=7,
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_sf_311_endpoint,
                platform="socrata",
                watermark_col="requested_datetime",
                id_keys=["service_request_id", "id", "unique_key"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_sf_licenses_endpoint,
                platform="socrata",
                watermark_col="location_start_date",
                id_keys=["location_id", "certificate_number", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.socrata_sf_deeds_endpoint,
                platform="socrata",
                watermark_col="data_loaded_at",
                id_keys=["parcel_number", "block_and_lot_number", "id", "doc_id"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                # SUSPECTED STALL: source_updated_at == newest data_loaded_at ==
                # 2026-06-26 (61d), and 0 rows have data_loaded_at >= 2026-07-01
                # (verified 2026-08-26). No live replacement identified (US-164);
                # keep registered + reported but exempt so it doesn't page forever.
                
                expected_cadence_days=7,
                alarm_exempt=True,
                alarm_exempt_reason='SUSPECTED STALL — frozen since 2026-06-26, no replacement (US-164)',
            ),
            # US-71: SFPD incident reports (point + intersection fields).
            FeedType.CRIME: DatasetSpec(
                endpoint=settings.socrata_sf_crime_endpoint,
                platform="socrata",
                watermark_col="incident_datetime",
                id_keys=["incident_number", "row_id"],
                topic=settings.topic_crime,
                interval_seconds=1800.0,
                producer_key="crime",
                
                expected_cadence_days=7,
            ),

            # US-363 §2.1: docked bikeshare via snapshot diff. No watermark
            # column exists — GBFS changes state in place — so
            # `ingestion_mode: snapshot` and the station state store carry the
            # ingestion contract. Bay Wheels (bay), GBFS 2.3, discovery verified 200 on 2026-08-28.
            # LICENSE: Lyft's Data License Agreement permits product use and
            # bars re-hosting the raw feed; we derive events and never
            # republish. Lime/Bird/Spin/Bolt/Veo are barred outright.
            FeedType.GBFS: DatasetSpec(
                endpoint=settings.gbfs_san_francisco_discovery_endpoint,
                platform="gbfs",
                watermark_col="",
                id_keys=["station_id", "system_id"],
                topic=settings.topic_station_change,
                interval_seconds=3600.0,
                producer_key="gbfs",
                ingestion_mode="snapshot",
                expected_cadence_days=1,
                companion_endpoints={'system_id': 'bay', 'operator': 'lyft'},
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
                
                expected_cadence_days=7,
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_seattle_311_endpoint,
                platform="socrata",
                watermark_col="createddate",
                id_keys=["servicerequestnumber", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                # US-110: Seattle spells the SR id `servicerequestnumber` (no
                # underscore) and the created date `createddate` — neither is
                # reachable by the generic chains, so every row dropped at
                # parse. Coordinates ride `latitude`/`longitude` (covered).
                
                expected_cadence_days=7,
                field_map={'incident_id': ['servicerequestnumber'], 'created_date': ['createddate'], 'complaint_type': ['webintakeservicerequests']},
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_seattle_licenses_endpoint,
                platform="socrata",
                watermark_col="applicationdate",
                id_keys=["license", "ubi", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
            ),
            # King County Assessor parcel sales stand in for recorded deeds. This
            # is an ArcGIS FeatureServer, not Socrata: it pages by OBJECTID via
            # resultOffset rather than by Socrata's $offset, so it needs an
            # ArcGIS-aware PaginatingClient.
            #
            # KNOWN-DEAD PUBLICATION (verified 2026-08-24, kept registered as
            # the honest staleness signal): both public copies — this service
            # and its on-prem twin gismaps.kingcounty.gov Property/
            # KingCo_PropertyInfo MapServer/3 — froze at SaleDate 2025-11-20
            # (lastEditDate 2025-11-28). The live replacement target is the
            # Assessor's weekly rpsale_extr table (AGO item 96ff1f46173541b9
            # a021a5fef1fdb8a9), which is access-restricted (403 GWM_0003,
            # absent from the org's anonymous directory) and carries
            # obtainer-only terms — see
            # docs/research/seattle-deeds-replacement.md for the full audit
            # and the two unblock paths (KC public sharing vs bulk-file
            # producer). Do not repoint this spec at either frozen copy.
            # alarm_exempt: source has no live anonymous replacement and the
            # gap is accepted (tracked US-163) — the probe still reports the
            # feed's true staleness but does not page the alarm for it.
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_kc_sales_url,
                platform="arcgis",
                watermark_col="SaleDate",
                id_keys=["ExciseTaxNum", "PIN", "OBJECTID"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=1000,
                alarm_exempt=True,
                alarm_exempt_reason='KNOWN-DEAD publication; no live anonymous replacement (US-163)',
            ),
            # US-71: SPD crime incidents (lat/lon verified 2026-08-24).
            FeedType.CRIME: DatasetSpec(
                endpoint=settings.socrata_seattle_crime_endpoint,
                platform="socrata",
                watermark_col="offense_date",
                id_keys=["offense_id", "report_number"],
                topic=settings.topic_crime,
                interval_seconds=1800.0,
                producer_key="crime",
                
                expected_cadence_days=7,
            ),
            # US-363 §2.7: Seattle benchmarking. Re-probed 2026-08-28: max
            # datayear 2024, n=34,699. Carries the richest compliance signal of
            # the three (`compliancestatus`) plus `ghgemissionsintensity`.
            FeedType.ENERGY_BENCHMARK: DatasetSpec(
                endpoint=settings.socrata_seattle_energy_benchmark_endpoint,
                platform="socrata",
                watermark_col="datayear",
                id_keys=["osebuildingid", "datayear"],
                topic=settings.topic_context_observations,
                interval_seconds=86400.0,
                producer_key="energy_benchmark",
                expected_cadence_days=365,
                watermark_type='text',
                watermark_format='%Y',
                alarm_exempt=True,
                alarm_exempt_reason='annual disclosure — one publication per year by design (US-363 §2.7)',
                field_map=SEATTLE_ENERGY_FIELD_MAP,
            ),
            # US-363 §2.8: Fremont Bridge hourly bike counts. 121,211 rows,
            # max date 2026-07-31T23:00 — the documented ~4-week lag, hence
            # the 35-day cadence declaration. WIDE layout: one row per hour
            # with nb/sb columns and no sensor id, because there is exactly
            # one sensor. `wide_layout` tells the producer to take the
            # directional columns (never the undirected total, which would
            # double-count the day) and to use the module's fixed coordinate
            # instead of a registry join.
            FeedType.BIKE_PED: DatasetSpec(
                endpoint=settings.socrata_seattle_bike_ped_counts_endpoint,
                platform="socrata",
                watermark_col="date",
                id_keys=["date"],
                topic=settings.topic_context_observations,
                interval_seconds=86400.0,
                producer_key="bike_ped",
                expected_cadence_days=35,
                companion_endpoints={'wide_layout': True},
                field_map=SEATTLE_FREMONT_FIELD_MAP,
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
                
                expected_cadence_days=7,
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
                
                expected_cadence_days=7,
                field_map={'incident_id': ['casenumber', 'srnumber'], 'latitude': ['geolocation__latitude__s'], 'longitude': ['geolocation__longitude__s'], 'complaint_type': ['requesttype'], 'created_date': ['createddate'], 'closed_date': ['closeddate'], 'zipcode': ['zipcode__c'], 'borough': ['locator_sr_neigborhood_council']},
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_la_licenses_endpoint,
                platform="socrata",
                watermark_col="location_start_date",
                id_keys=["location_account", "business_name", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
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
                
                expected_cadence_days=7,
                field_map={'job_id': ['numstring'], 'latitude': ['location_1.latitude'], 'longitude': ['location_1.longitude'], 'cost': ['constrval'], 'job_type': ['type'], 'issuance_date': ['issuedate'], 'filing_date': ['filingdate'], 'status': ['currentstatus'], 'borough': ['subdivision']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_nola_311_endpoint,
                platform="socrata",
                watermark_col="date_created",
                id_keys=["service_request", "rowid", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                field_map={'incident_id': ['service_request', 'rowid'], 'created_date': ['date_created'], 'closed_date': ['case_close_date'], 'descriptor': ['request_reason'], 'incident_address': ['final_address'], 'borough': ['address_councildis']},
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
                
                expected_cadence_days=7,
                field_map={'license_id': ['businesslicensenumber'], 'effective_date': ['businessstartdate'], 'license_type': ['businesstype'], 'dba': ['businessname'], 'premises_name': ['ownername']},
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
                
                expected_cadence_days=45,
                field_map={'doc_id': ['identifier'], 'bbl': ['geopin'], 'latitude': ['geocoded_column.latitude'], 'longitude': ['geocoded_column.longitude'], 'doc_type': ['disposition_channel'], 'borough': ['council_district']},
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
        # Partial registration: MyNorfolk 311 (`nbyu-xjez`) locates cases with
        # an address STRING (ADR 0004 geocoded at parse time), while the
        # business-license feed (`dpi6-sct5`) carries NATIVE lat/lng/geocoded_point
        # columns (the city geocodes `location_address` itself) — the Wave G2
        # "no geometry" verdict is obsolete. Registered with a where-filter that
        # drops the `'NO NORFOLK ADDRESS REQUIRED 99999'` placeholder rows
        # (special-event/no-fixed-premises licenses), leaving ~96% geocoded.
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
                
                expected_cadence_days=7,
                field_map={'cost': ['project_cost'], 'filing_date': ['application_date'], 'job_type': ['work_type', 'type']},
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
                
                expected_cadence_days=7,
                field_map={'doc_id': ['document_number'], 'bbl': ['gpin', 'parcel_id']},
            ),
            # MyNorfolk 311 locates cases with an address STRING only — the
            # original registration deferred these two feeds until an
            # address-geocoding capability existed (now ADR 0004). Rows carry
            # no coordinates on the wire from Socrata; producers geocode at
            # parse time because the declaration below flips the coordinate
            # requirement, keeping Avro doubles real.
            #
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_norfolk_licenses_endpoint,
                platform="socrata",
                watermark_col="business_opened_date",
                id_keys=["trading_as_name", "primary_owner", "business_opened_date"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                # The city geocodes `location_address` itself into
                # latitude/longitude (and geocoded_point), so the Wave G2
                # "no geometry" verdict is obsolete. ~25% of raw rows carry
                # the literal placeholder 'NO NORFOLK ADDRESS REQUIRED 99999'
                # (special-event/no-fixed-premises licenses); excluding them
                # server-side leaves >96% native-geocoded, well under the G8'
                # 5% null-H3 ceiling. Business names double as a license
                # identity (no numeric license id on the feed); the three
                # id_keys form the watermark/dedup tuple.
                
                expected_cadence_days=7,
                where="location_address != 'NO NORFOLK ADDRESS REQUIRED 99999'",
                field_map={'license_id': ['trading_as_name', 'primary_owner'], 'dba': ['trading_as_name'], 'premises_name': ['primary_owner'], 'license_type': ['naics'], 'effective_date': ['business_opened_date'], 'address_street': ['location_address'], 'latitude': ['latitude'], 'longitude': ['longitude']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_norfolk_311_endpoint,
                platform="socrata",
                watermark_col="creation_date",
                id_keys=["service_request_number", "id"],
                topic=settings.topic_311,
                interval_seconds=600.0,
                producer_key="311",
                
                expected_cadence_days=7,
                needs_geocode=True,
                geocode_context='Norfolk, VA',
                field_map={'incident_id': ['service_request_number'], 'complaint_type': ['service_request_type', 'service_request_category'], 'created_date': ['creation_date'], 'status': ['status'], 'incident_address': ['location']},
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
                
                expected_cadence_days=7,
                oid_field='ObjectId',
                max_record_count=1000,
                field_map={'job_id': ['record_id'], 'cost': ['amt_permit_cost']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_detroit_311_url,
                platform="arcgis",
                watermark_col="created_at",
                id_keys=["issue_id", "ObjectId", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='ObjectId',
                max_record_count=1000,
                field_map={'incident_id': ['issue_id'], 'closed_date': ['closed_at']},
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
                
                expected_cadence_days=7,
                oid_field='ObjectId',
                max_record_count=1000,
                field_map={'license_id': ['record_id'], 'license_type': ['license_type', 'license_category']},
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_detroit_sales_url,
                platform="arcgis",
                watermark_col="sale_date",
                id_keys=["sale_id", "liber_page", "ObjectId", "id"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                oid_field='ObjectId',
                max_record_count=1000,
                field_map={'doc_id': ['sale_id'], 'bbl': ['parcel_id'], 'document_amount': ['amt_sale_price']},
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
        # Partial registration like Los Angeles: Austin registers permits + 311
        # natively. US-136 adds the TABC statewide liquor-license SLA feed
        # (address-only; geocoded per ADR-0004). No property-sales feed exists
        # on data.austintexas.gov (Travis County Socrata is an unreachable
        # FedRAMP shell), so FeedType.DEEDS stays absent.
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
                
                expected_cadence_days=21,
                field_map={'cost': ['total_job_valuation'], 'filing_date': ['application_date'], 'job_type': ['work_type', 'permit_type'], 'proposed_units': ['number_of_units'], 'proposed_stories': ['number_of_floors'], 'borough': ['council_district']},
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
                
                expected_cadence_days=7,
                field_map={'latitude': ['sr_location_lat'], 'longitude': ['sr_location_long'], 'complaint_type': ['sr_type_desc'], 'created_date': ['sr_created_date'], 'closed_date': ['sr_closed_date'], 'status': ['sr_status_desc'], 'zipcode': ['sr_location_zip_code'], 'incident_address': ['sr_location'], 'borough': ['sr_location_council_district']},
        ),
            # US-136: TABC statewide liquor-license feed (data.texas.gov
            # `7hf9-qc9f` "TABC License Information"). Address-only — no lat/lng
            # columns — so needs_geocode flips the coordinate requirement and the
            # ADR 0004 geocoder resolves coordinates at parse time.
            # watermark = current_issued_date, the published issuance cursor
            # for this slowly-churning license file.
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_austin_tabc_endpoint,
                platform="socrata",
                watermark_col="current_issued_date",
                id_keys=["license_id", "master_file_id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                needs_geocode=True,
                geocode_context='TX',
                where="county = 'Travis'",
                field_map={'license_id': ['license_id'], 'license_type': ['license_type'], 'effective_date': ['current_issued_date'], 'expiration_date': ['expiration_date'], 'premises_name': ['owner'], 'dba': ['trade_name'], 'address_street': ['address'], 'status': ['license_status']},
            ),
            # US-265 note: Austin NIBRS crime (thrk-bqb6) is NOT registered — the
            # feed publishes no lat/lng and no street address (zip_code only),
            # which the ADR-0004 geocoder cannot resolve. Deferred pending a
            # coordinate- or address-bearing APD crime resource.
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
        # The verified Cincinnati catalog has permits, 311, business licenses,
        # and the Hamilton County Auditor property-transfers CSV (US-126). The
        # deeds feed is a static-CSV download (no REST API) that publishes the
        # current month's sales daily; SaleDate is synthesized from the three
        # int columns, so the spec runs as a snapshot window re-pulled each
        # poll and deduped on ConveyanceNumber+PropertyNumber.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_cincinnati_permits_endpoint,
                platform="socrata",
                watermark_col="issueddate",
                id_keys=["permit_number", "permitnumber", "pin", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                field_map={'job_id': ['permit_number', 'permitnumber', 'pin'], 'issuance_date': ['issueddate'], 'filing_date': ['applieddate'], 'address_street': ['originaladdress1'], 'zipcode': ['originalzip']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_cincinnati_311_endpoint,
                platform="socrata",
                watermark_col="date_time_received",
                id_keys=["service_request_id", "sr_number", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                field_map={'incident_id': ['sr_number'], 'created_date': ['date_time_received'], 'incident_address': ['address'], 'complaint_type': ['sr_type_desc', 'sr_type']},
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_cincinnati_licenses_endpoint,
                platform="socrata",
                watermark_col="entered_date",
                id_keys=["license_number", "license_id", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                field_map={'license_id': ['number_key', 'uniqueid'], 'effective_date': ['entered_date'], 'latitude': ['latitude'], 'longitude': ['longitude'], 'status': ['data_status', 'status_class']},
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.csv_cincinnati_deeds_endpoint,
                platform="csv",
                watermark_col="SaleDate",
                id_keys=["conveyancenumber", "propertynumber"],
                topic=settings.topic_deeds,
                interval_seconds=1800.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                ingestion_mode='snapshot',
                where="valid = 'Y'",
                needs_geocode=True,
                geocode_context='Hamilton County, OH',
                field_map={'doc_id': ['conveyancenumber'], 'bbl': ['propertynumber'], 'document_amount': ['saleamount'], 'party1_grantor': ['previousowner'], 'party2_grantee': ['ownername1', 'ownername2'], 'doc_type': ['deedtype'], 'incident_address': ['house#', 'streetname', 'streetsuffix'], 'zipcode': ['locationzipcode'], 'borough': ['appraisalarea']},
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
        # Boston has no open recorded-deeds feed; the Property Assessment FY snapshot
        # is wired as a DEEDS proxy so downstream models have a price-bearing input.
        # US-137 registers the Licensing Board feed (04dc653b) as SLA; coordinates
        # gpsx/gpsy are Massachusetts Mainland State Plane US survey feet (EPSG:2249);
        # Path A transforms them to WGS84.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.ckan_boston_permits_endpoint,
                platform="ckan",
                watermark_col="issued_date",
                id_keys=["permitnumber", "_id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                field_map={'job_id': ['permitnumber'], 'issuance_date': ['issued_date'], 'filing_date': ['issued_date'], 'address_street': ['address'], 'zipcode': ['zip'], 'borough': ['ward'], 'latitude': ['y_latitude', 'gpsy'], 'longitude': ['x_longitude', 'gpsx'], 'status': ['status'], 'cost': ['declared_valuation']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.ckan_boston_311_endpoint,
                platform="ckan",
                watermark_col="open_dt",
                id_keys=["case_enquiry_id", "_id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                field_map={'incident_id': ['case_enquiry_id'], 'latitude': ['latitude'], 'longitude': ['longitude'], 'complaint_type': ['type', 'case_title'], 'created_date': ['open_dt'], 'closed_date': ['closed_dt'], 'status': ['case_status'], 'incident_address': ['location_street_name', 'location'], 'zipcode': ['location_zipcode'], 'borough': ['ward']},
                endpoint_by_year={'2025': settings.ckan_boston_311_2025_endpoint, '2026': settings.ckan_boston_311_endpoint},
                rollover='manual-verify',
            ),
            # US-137: Boston Licensing Board register (CKAN 04dc653b-...).
            # Its only coordinate columns, gpsx/gpsy, are Massachusetts State
            # Plane US survey feet (EPSG:2249), so Path A transforms them.
            FeedType.SLA: DatasetSpec(
                endpoint=settings.ckan_boston_licenses_endpoint,
                platform="ckan",
                watermark_col="expires",
                id_keys=["license_num", "_id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                state_plane_crs='EPSG:2249',
                state_plane_units='US survey feet',
                state_plane_x_col='gpsx',
                state_plane_y_col='gpsy',
                field_map=BOSTON_LICENSING_FIELD_MAP,
            ),
            # US-209: Property Assessment FY2026 — proxy for recorded deeds.
            # Snapshot-mode so full table refreshes dedupe on pid. Many rows
            # lack coordinates; DeedEvent tolerates null lat/lng (Cook County precedent).
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.ckan_boston_property_assessment_endpoint,
                platform="ckan",
                watermark_col="",
                id_keys=["pid", "_id"],
                topic=settings.topic_deeds,
                interval_seconds=1800.0,
                producer_key="deeds",
                
                expected_cadence_days=365,
                ingestion_mode='snapshot',
                field_map={
                    "doc_id": ["pid", "parcel_id", "map_par_id"],
                    "bbl": ["pid", "parcel_id", "map_par_id"],
                    "document_amount": ["total_value", "total_assessed_value", "total_av", "av_total"],
                    "recorded_date": ["fy", "year"],
                    "latitude": ["latitude", "y_latitude", "gpsy"],
                    "longitude": ["longitude", "x_longitude", "gpsx"],
                    "borough": ["ward", "neighborhood"],
                    "address_street": ["location", "address"],
                },
            ),
            # US-: Boston Crime Incident Reports (CKAN 6220d948-... odata v4).
            # Source carries Lat/Long directly, so no geocode step required.
            FeedType.CRIME: DatasetSpec(
                endpoint=settings.ckan_boston_crime_endpoint,
                platform="ckan",
                watermark_col="OCCURRED_ON_DATE",
                id_keys=["INCIDENT_NUMBER"],
                topic="raw.municipal.crime",
                interval_seconds=300.0,
                producer_key="crime",
                field_map={
                    "incident_id": ["INCIDENT_NUMBER"],
                    "offense_type": ["OFFENSE_DESCRIPTION"],
                    "occurred_date": ["OCCURRED_ON_DATE"],
                    "latitude": ["Lat"],
                    "longitude": ["Long"],
                },
                needs_geocode=False,
                expected_cadence_days=7,
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
        # construction. Deeds/sales were not found in the county portal — the
        # registered DEEDS feed (US-128) comes from the state-level MD SDAT
        # real-property snapshot on opendata.maryland.gov instead.
        # Permits publishes a 4.97% geocode gap (9,244 of 186,140 rows lack
        # location coordinates; probed 2026-08-24); G5 is adjudicated against
        # that published gap (newest-500 drop 4.8%).
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_montgomery_permits_endpoint,
                platform="socrata",
                watermark_col="issueddate",
                id_keys=["permitno"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                field_map={'job_id': ['permitno'], 'issuance_date': ['issueddate'], 'filing_date': ['addeddate'], 'address_street': ['stno', 'stname', 'suffix', 'postdir'], 'zipcode': ['zip'], 'job_type': ['worktype', 'applicationtype', 'usecode'], 'status': ['status'], 'latitude': ['location.latitude'], 'longitude': ['location.longitude']},
                companion_endpoints={'commercial': 'https://data.montgomerycountymd.gov/resource/i26v-w6bd.json', 'demolition': 'https://data.montgomerycountymd.gov/resource/b6ht-fw3x.json', 'electrical': 'https://data.montgomerycountymd.gov/resource/qxie-8qnp.json'},
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_montgomery_licenses_endpoint,
                platform="socrata",
                watermark_col="",
                id_keys=["licensee_number", "licensee_name"],
                topic=settings.topic_sla,
                interval_seconds=900.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                ingestion_mode='snapshot',
                alarm_exempt=True,
                alarm_exempt_reason='SUSPECTED STALL — no date col, rowsUpdatedAt frozen 2026-04-01 (US-164)',
                field_map={'license_id': ['licensee_number'], 'license_type': ['channel_type'], 'premises_name': ['licensee_name', 'account_name'], 'address_street': ['street'], 'zipcode': ['zip'], 'latitude': ['location.latitude'], 'longitude': ['location.longitude']},
            ),
            # US-128: MD SDAT real-property deeds — per-parcel assessment
            # snapshot (one row per parcel; segment 1 = most recent sale, with
            # the prior two in _segment_2_/_3_). Point-geocoded natively via the
            # WKT mappable_latitude_and_longitude + the MDP WGS84 numeric
            # columns; monthly snapshot. No grantee (SDAT records grantor only);
            # the new-sale watermark is the dotted YYYY.MM.DD text, so the feed
            # runs snapshot (SF roll precedent) rather than incremental.
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.socrata_montgomery_deeds_endpoint,
                platform="socrata",
                watermark_col="sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89",
                id_keys=["account_id_mdp_field_acctid", "sales_segment_1_transfer_number_mdp_field_transno1_sdat_field_79"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                
                expected_cadence_days=30,
                ingestion_mode='snapshot',
                field_map={'doc_id': ['account_id_mdp_field_acctid'], 'bbl': ['account_id_mdp_field_acctid'], 'document_amount': ['sales_segment_1_consideration_mdp_field_considr1_sdat_field_90'], 'recorded_date': ['sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89'], 'party1_grantor': ['sales_segment_1_grantor_name_mdp_field_grntnam1_sdat_field_80'], 'latitude': ['mdp_latitude_mdp_field_digycord_converted_to_wgs84'], 'longitude': ['mdp_longitude_mdp_field_digxcord_converted_to_wgs84']},
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
                
                expected_cadence_days=7,
                field_map={'job_id': ['permitnumber', 'permitid'], 'issuance_date': ['issueddate'], 'filing_date': ['creationdate'], 'job_type': ['permittype'], 'cost': ['projectvalue'], 'address_street': ['streetaddress', 'address'], 'zipcode': ['zip'], 'borough': ['parishname']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_baton_rouge_311_endpoint,
                platform="socrata",
                watermark_col="createdate",
                id_keys=["id", "parentid"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                field_map={'incident_id': ['id'], 'latitude': ['latitude'], 'longitude': ['longitude'], 'complaint_type': ['typename', 'parenttype'], 'created_date': ['createdate'], 'status': ['statusdesc'], 'incident_address': ['streetaddress'], 'borough': ['division']},
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_baton_rouge_licenses_endpoint,
                platform="socrata",
                watermark_col="",
                id_keys=["taccount", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                ingestion_mode='snapshot',
                field_map={'license_id': ['taccount'], 'latitude': ['geolocation.latitude'], 'longitude': ['geolocation.longitude'], 'license_type': ['typename', 'naicname'], 'status': ['tstatus'], 'premises_name': ['tname', 'tlegalname']},
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
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                companion_endpoints={'commercial': 'https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/ODC_DEV_COMMERCIALCONSTPERMIT_P/FeatureServer/317'},
                field_map={'job_id': ['PERMIT_NUM'], 'issuance_date': ['DATE_ISSUED'], 'filing_date': ['DATE_RECEIVED'], 'job_type': ['CLASS'], 'cost': ['VALUATION'], 'address_street': ['ADDRESS'], 'proposed_units': ['UNITS'], 'borough': ['NEIGHBORHOOD']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_denver_311_url,
                platform="arcgis",
                watermark_col="Case_Created_Date",
                id_keys=["OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'latitude': ['Latitude'], 'longitude': ['Longitude'], 'incident_id': ['OBJECTID'], 'complaint_type': ['Type', 'Topic', 'Case_Summary'], 'created_date': ['Case_Created_dttm'], 'closed_date': ['Case_Closed_dttm'], 'status': ['Case_Status'], 'incident_address': ['Incident_Address_1'], 'zipcode': ['Incident_Zip_Code', 'Customer_Zip_Code'], 'borough': ['Neighborhood']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # The US-73 licenses descope stands for Denver's own business-
            # license source; this registration is the national FNS feed.
            FeedType.SLA: snap_sla_spec("CO"),
        },
    ),
    CityId.MINNEAPOLIS: CityRegistration(
        city_id=CityId.MINNEAPOLIS,
        name="Minneapolis",
        state="MN",
        center={"lat": 44.9778, "lng": -93.2650},
        metro_bbox=MINNEAPOLIS_METRO_BBOX,
        division_bboxes=MINNEAPOLIS_DIVISION_BBOXES,
        submarkets=MINNEAPOLIS_SUBMARKETS,
        divisions=MINNEAPOLIS_DIVISIONS,
        job_suffix="minneapolis",
        # Partial registration like Denver: permits + year-sliced 311 + the
        # narrow On/Off-Sale liquor license inventory (US-135). The licensee
        # type is notifications-grade (a license registry, not a hospitality
        # activity feed — Milwaukee SLA precedent), point-geocoded via native
        # `lat`/`long` attributes. The Off_Sale_Liquor companion layer rides
        # companion_endpoints. Property_Sales_2021_to_2025 stays unregistered
        # (stale max SALE_DATE 2025-09-30, county-coordinate X/Y not lat/lng).
        # 311 publishes one Public_311_<year> layer per year; the rollover
        # drill (US-70) requires the current year to be mapped, so a 2027
        # layer must be appended each New Year like DC/Boston/Baltimore.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_minneapolis_permits_url,
                platform="arcgis",
                watermark_col="issueDate",
                id_keys=["permitNumber"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=16000,
                field_map={'job_id': ['permitNumber'], 'issuance_date': ['issueDate'], 'cost': ['value'], 'job_type': ['permitType', 'workType'], 'status': ['status', 'milestone'], 'proposed_units': ['dwellingUnitsNew'], 'existing_units': ['dwellingUnitsEliminated'], 'borough': ['Neighborhoods_Desc', 'Wards']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_minneapolis_311_url,
                platform="arcgis",
                watermark_col="OPENEDDATETIME",
                id_keys=["CASEID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=16000,
                endpoint_by_year={'2015': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Public_311_2015/FeatureServer/0', '2016': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Public_311_2016/FeatureServer/0', '2017': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Public_311_2017/FeatureServer/0', '2018': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Public_311_2018/FeatureServer/0', '2019': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Public_311_2019/FeatureServer/0', '2020': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Public_311_2020/FeatureServer/0', '2021': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Public_311_2021/FeatureServer/0', '2022': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Public_311_2022/FeatureServer/0', '2023': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Public_311_2023/FeatureServer/0', '2024': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Public_311_2024/FeatureServer/0', '2025': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Public_311_2025/FeatureServer/0', '2026': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Public_311_2026/FeatureServer/0'},
                field_map={'incident_id': ['CASEID'], 'complaint_type': ['TYPENAME', 'REASONNAME', 'SUBJECTNAME'], 'created_date': ['OPENEDDATETIME'], 'closed_date': ['CLOSEDDATETIME'], 'incident_address': ['TITLE']},
            ),
            # US-135: On/Off-Sale liquor license inventory (AGOL item
            # 5042131de56d44749f6e43c0b5738b21). Point layer with native
            # `lat`/`long` attributes; `issueDate` is the watermark
            # (epoch-ms, esriFieldTypeDate -> ISO by ArcGISClient). The
            # Off_Sale_Liquor layer is registered as the companion endpoint
            # (Montgomery-partner precedent); the feed is a narrow liquor
            # registry, not a hospitality-activity feed (Milwaukee scope).
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_minneapolis_licenses_url,
                platform="arcgis",
                watermark_col="issueDate",
                id_keys=["licenseNumber", "OBJECTID"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=30,
                oid_field='OBJECTID',
                max_record_count=16000,
                companion_endpoints={'off_sale': 'https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Off_Sale_Liquor/FeatureServer/0'},
                field_map={'license_id': ['licenseNumber'], 'license_type': ['licenseType', 'liquorType'], 'effective_date': ['issueDate'], 'expiration_date': ['expirationDate'], 'dba': ['licenseName'], 'latitude': ['lat'], 'longitude': ['long'], 'incident_address': ['address'], 'borough': ['ward', 'neighborhood']},
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
        # activity feed. The DEEDS feed (US-128) comes from the state-level
        # MD SDAT real-property snapshot on opendata.maryland.gov — no
        # county/city transaction feed exists.
        # 311 publishes a 25.07% geocode gap (585,130 of 780,954 rows carry
        # coordinates; probed 2026-08-24). G5 is adjudicated against that
        # published gap: newest-500 drop 35%, mature-window drop 22.6% — the
        # live newest window skews to freshly created, still-ungeocoded
        # requests. Address-only rows remain dropped until the geocoding wave.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_baltimore_permits_url,
                platform="arcgis",
                watermark_col="IssuedDate",
                id_keys=["CaseNumber", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=1000,
                field_map={'job_id': ['CaseNumber'], 'issuance_date': ['IssuedDate'], 'expiration_date': ['ExpirationDate'], 'address_street': ['Address'], 'cost': ['Cost'], 'borough': ['Neighborhood', 'Council_District'], 'job_type': ['ProposedUse', 'ExistingUse']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_baltimore_311_url,
                platform="arcgis",
                watermark_col="CreatedDate",
                id_keys=["SRRecordID", "ServiceRequestNum", "RowID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='RowID',
                max_record_count=2000,
                field_map={'incident_id': ['SRRecordID', 'ServiceRequestNum', 'RowID'], 'latitude': ['Latitude'], 'longitude': ['Longitude'], 'complaint_type': ['SRType'], 'created_date': ['CreatedDate'], 'closed_date': ['CloseDate'], 'status': ['SRStatus'], 'incident_address': ['Address'], 'zipcode': ['ZipCode'], 'borough': ['Neighborhood', 'CouncilDistrict']},
                endpoint_by_year={'2025': settings.arcgis_baltimore_311_2025_url, '2026': settings.arcgis_baltimore_311_url},
                rollover='manual-verify',
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_baltimore_licenses_url,
                platform="arcgis",
                watermark_col="LicenseDate",
                id_keys=["LicenseNumber", "LLKey", "ESRI_OID"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                oid_field='ESRI_OID',
                max_record_count=2000,
                field_map={'license_id': ['LicenseNumber', 'LLKey'], 'license_type': ['LicenseClass', 'SubClass'], 'effective_date': ['LicenseDate'], 'expiration_date': ['LicenseEndDate'], 'status': ['LicenseStatus'], 'address_street': ['AddrStreet'], 'zipcode': ['AddrZip']},
            ),
            # US-128: MD SDAT real-property deeds — per-parcel assessment
            # snapshot (one row per parcel; segment 1 = most recent sale, with
            # the prior two in _segment_2_/_3_). Point-geocoded natively via the
            # WKT mappable_latitude_and_longitude + the MDP WGS84 numeric
            # columns; monthly snapshot. No grantee (SDAT records grantor only);
            # the new-sale watermark is the dotted YYYY.MM.DD text, so the feed
            # runs snapshot (SF roll precedent) rather than incremental.
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.socrata_baltimore_deeds_endpoint,
                platform="socrata",
                watermark_col="sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89",
                id_keys=["account_id_mdp_field_acctid", "sales_segment_1_transfer_number_mdp_field_transno1_sdat_field_79"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                
                expected_cadence_days=30,
                ingestion_mode='snapshot',
                field_map={'doc_id': ['account_id_mdp_field_acctid'], 'bbl': ['account_id_mdp_field_acctid'], 'document_amount': ['sales_segment_1_consideration_mdp_field_considr1_sdat_field_90'], 'recorded_date': ['sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89'], 'party1_grantor': ['sales_segment_1_grantor_name_mdp_field_grntnam1_sdat_field_80'], 'latitude': ['mdp_latitude_mdp_field_digycord_converted_to_wgs84'], 'longitude': ['mdp_longitude_mdp_field_digxcord_converted_to_wgs84']},
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
                
                expected_cadence_days=7,
                id_col='cartodb_id',
                order_by='permitissuedate',
                select='*, ST_Y(the_geom) AS latitude, ST_X(the_geom) AS longitude',
                field_map={'job_id': ['permitnumber'], 'issuance_date': ['permitissuedate'], 'borough': ['council_district'], 'zipcode': ['zip']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.carto_phl_311_endpoint,
                platform="carto",
                watermark_col="requested_datetime",
                id_keys=["service_request_id", "cartodb_id", "id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                id_col='cartodb_id',
                order_by='requested_datetime',
                field_map={'latitude': ['lat'], 'longitude': ['lon'], 'closed_date': ['closed_datetime']},
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.carto_phl_licenses_endpoint,
                platform="carto",
                watermark_col="mostrecentissuedate",
                id_keys=["licensenum", "cartodb_id", "id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                id_col='cartodb_id',
                order_by='mostrecentissuedate',
                select='*, ST_Y(the_geom) AS latitude, ST_X(the_geom) AS longitude',
                field_map={'license_id': ['licensenum'], 'license_type': ['licensetype'], 'effective_date': ['initialissuedate'], 'expiration_date': ['expirationdate'], 'status': ['licensestatus']},
            ),
            # Real Estate Transfer Tax summary is a price-bearing recorded-deeds
            # source (Office of Realty Transfer Tax) once scoped to actual
            # deeds: the where filter below keeps document_type='DEED', whose
            # rows are ~95% price-bearing (vs. the mortgages/satisfactions that
            # the table as a whole mixes in, mostly NULL consideration →
            # document_amount 0.0). recorded_date maps to recording_date because
            # document_date is frequently NULL/sentinel (years 9798, 2066
            # mortgage-assignment loan terms); watermark and keyset order sit
            # on recording_date for the same reason — see
            # docs/research/data-coverage-sweep-2026-08-25.md §7,
            # docs/research/deeds-watermark-audit.md and
            # docs/research/non-socrata-platforms.md §Philadelphia.
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.carto_phl_deeds_endpoint,
                platform="carto",
                watermark_col="recording_date",
                id_keys=["document_id", "cartodb_id", "id"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                where="document_type = 'DEED'",
                id_col='cartodb_id',
                order_by='recording_date',
                select='*, ST_Y(the_geom) AS latitude, ST_X(the_geom) AS longitude',
                alarm_exempt=True,
                alarm_exempt_reason='SUSPECTED DEED-slice lag/stall — newest DEED recording 2026-07-07 (US-164)',
                field_map={'recorded_date': ['recording_date'], 'document_amount': ['total_consideration'], 'bbl': ['opa_account_num'], 'party1_grantor': ['grantors'], 'party2_grantee': ['grantees']},
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
        # CAMA sales are enriched from Parcel Lots layer 33 by the deeds
        # producer's bounded SSL parcel join before they are parsed.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_dc_permits_url,
                platform="arcgis",
                watermark_col="ISSUE_DATE",
                id_keys=["PERMIT_ID", "DCRAINTERNALNUMBER", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                endpoint_by_year={'2023': 'https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/15', '2024': 'https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/16', '2025': 'https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/17', '2026': 'https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/18'},
                field_map={'job_id': ['PERMIT_ID'], 'latitude': ['LATITUDE'], 'longitude': ['LONGITUDE'], 'issuance_date': ['ISSUE_DATE'], 'job_type': ['PERMIT_TYPE_NAME', 'PERMIT_SUBTYPE_NAME'], 'cost': ['FEES_PAID'], 'borough': ['WARD'], 'zipcode': ['ZIPCODE']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_dc_311_url,
                platform="arcgis",
                watermark_col="ADDDATE",
                id_keys=["SERVICEREQUESTID", "GLOBALID", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=1000,
                endpoint_by_year={'2022': 'https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/14', '2023': 'https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/15', '2024': 'https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/16', '2025': 'https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/18', '2026': 'https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/21'},
                field_map={'incident_id': ['SERVICEREQUESTID'], 'latitude': ['LATITUDE'], 'longitude': ['LONGITUDE'], 'complaint_type': ['SERVICECODEDESCRIPTION'], 'created_date': ['ADDDATE'], 'closed_date': ['RESOLUTIONDATE'], 'status': ['SERVICEORDERSTATUS'], 'incident_address': ['STREETADDRESS'], 'borough': ['WARD'], 'zipcode': ['ZIPCODE']},
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_dc_licenses_url,
                platform="arcgis",
                watermark_col="INITIALISSUEDATE",
                id_keys=["CUSTOMERNUMBER", "GLOBALID", "OBJECTID"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                needs_geocode=True,
                geocode_context='Washington, DC',
                where="PREMISEINDC = 'Yes'",
                field_map={'license_id': ['CUSTOMERNUMBER'], 'license_type': ['LICENSETYPE'], 'effective_date': ['LICENSESTARTDATE'], 'expiration_date': ['LICENSEENDDATE'], 'borough': ['WARD'], 'address_street': ['PREMISEADDRESS']},
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_dc_sales_url,
                platform="arcgis",
                watermark_col="SALE_DATE",
                id_keys=["SSL", "ROW_NUMBER", "OBJECTID", "id"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                parcel_join={'parcel_layer': 'https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Property_and_Land_WebMercator/FeatureServer/33', 'join_key': 'SSL', 'geometry_source': 'centroid'},
                field_map={'doc_id': ['ROW_NUMBER'], 'bbl': ['SSL'], 'document_amount': ['SALE_PRICE'], 'recorded_date': ['SALE_DATE'], 'doc_type': ['QUALIFIED']},
            ),

            # US-363 §2.1: docked bikeshare via snapshot diff. No watermark
            # column exists — GBFS changes state in place — so
            # `ingestion_mode: snapshot` and the station state store carry the
            # ingestion contract. Capital Bikeshare, GBFS **1.1**, system
            # `dca-cabi`, 866 stations verified 2026-08-28. Reached through the
            # operator's discovery root, NOT gbfs.lyft.com/.../dca/, which is a
            # live-but-empty stub (see the config note).
            # LICENSE: Lyft's Data License Agreement permits product use and
            # bars re-hosting the raw feed; we derive events and never
            # republish. Lime/Bird/Spin/Bolt/Veo are barred outright.
            FeedType.GBFS: DatasetSpec(
                endpoint=settings.gbfs_washington_dc_discovery_endpoint,
                platform="gbfs",
                watermark_col="",
                id_keys=["station_id", "system_id"],
                topic=settings.topic_station_change,
                interval_seconds=3600.0,
                producer_key="gbfs",
                ingestion_mode="snapshot",
                expected_cadence_days=1,
                companion_endpoints={'system_id': 'dca-cabi', 'operator': 'lyft'},
            ),
        },
    ),
    CityId.PRINCE_GEORGES: CityRegistration(
        city_id=CityId.PRINCE_GEORGES,
        name="Prince George's County",
        state="MD",
        center={"lat": 38.72, "lng": -76.75},
        metro_bbox=PRINCE_GEORGES_METRO_BBOX,
        division_bboxes=PRINCE_GEORGES_DIVISION_BBOXES,
        submarkets=PRINCE_GEORGES_SUBMARKETS,
        divisions=PRINCE_GEORGES_DIVISIONS,
        job_suffix="pgmd",
        # National Capital Region cluster with DC and Montgomery. 311
        # publishes in monthly batches (newest row 38d old at the 2026-07-17
        # survey while the catalog read fresh), so it carries a G11 cadence
        # exception instead of paging forever.
        #
        # DEEDS (US-128) is the state-level MD SDAT real-property snapshot on
        # opendata.maryland.gov. It is Point-geocoded (WKT
        # mappable_latitude_and_longitude + MDP WGS84 numeric columns) and
        # parses cleanly, so it deliberately SIDESTEPS the held qzrv-2tnv
        # parcel table below — no geometry-hardening needed for this feed.
        #
        # The qzrv-2tnv parcel table ("Property", 353k rows) is deliberately
        # NOT registered yet: it is one row per tax account (a snapshot
        # candidate), but DeedsACRISProducer.parse_socrata_row extracts
        # coordinates only from POINT geometries and crashes with
        # "list index out of range" on the table's MultiPolygon parcel
        # shapes — every row would parse to None (verified live 2026-08-24).
        # Registering it now would page G5 forever; harden the geometry
        # extraction (centroid or ring-walk) first, then register in D4
        # snapshot mode with field_map doc_id=account,
        # document_amount=sales_price, recorded_date=transfer_date.
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_prince_georges_311_endpoint,
                platform="socrata",
                watermark_col="date_request_opened",
                id_keys=["service_request", "id"],
                topic=settings.topic_311,
                interval_seconds=600.0,
                producer_key="311",
                
                expected_cadence_days=30,
                field_map={'incident_id': ['service_request'], 'complaint_type': ['request_name'], 'created_date': ['date_request_opened'], 'status': ['request_status']},
            ),
            # US-128: MD SDAT real-property deeds — per-parcel assessment
            # snapshot (one row per parcel; segment 1 = most recent sale, with
            # the prior two in _segment_2_/_3_). Point-geocoded natively via the
            # WKT mappable_latitude_and_longitude + the MDP WGS84 numeric
            # columns; monthly snapshot. No grantee (SDAT records grantor only);
            # the new-sale watermark is the dotted YYYY.MM.DD text, so the feed
            # runs snapshot (SF roll precedent) rather than incremental.
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.socrata_pg_deeds_endpoint,
                platform="socrata",
                watermark_col="sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89",
                id_keys=["account_id_mdp_field_acctid", "sales_segment_1_transfer_number_mdp_field_transno1_sdat_field_79"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                
                expected_cadence_days=30,
                ingestion_mode='snapshot',
                field_map={'doc_id': ['account_id_mdp_field_acctid'], 'bbl': ['account_id_mdp_field_acctid'], 'document_amount': ['sales_segment_1_consideration_mdp_field_considr1_sdat_field_90'], 'recorded_date': ['sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89'], 'party1_grantor': ['sales_segment_1_grantor_name_mdp_field_grntnam1_sdat_field_80'], 'latitude': ['mdp_latitude_mdp_field_digycord_converted_to_wgs84'], 'longitude': ['mdp_longitude_mdp_field_digxcord_converted_to_wgs84']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("MD"),
        },
    ),
    CityId.COLUMBUS: CityRegistration(
        city_id=CityId.COLUMBUS,
        name="Columbus",
        state="OH",
        center={"lat": 39.9612, "lng": -83.0007},
        metro_bbox=COLUMBUS_METRO_BBOX,
        division_bboxes=COLUMBUS_DIVISION_BBOXES,
        submarkets=COLUMBUS_SUBMARKETS,
        divisions=COLUMBUS_DIVISIONS,
        job_suffix="cmoh",
        # Accela-derived uppercase schema. B1_ALT_ID identifies the permit;
        # OBJECTID stays out of the id chain because it is an edit counter,
        # not a business key. G3_VALUE_TTL = 0 is a legitimate zero-cost
        # permit, not a parse failure (~63% of newest rows).
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_columbus_permits_url,
                platform="arcgis",
                watermark_col="ISSUED_DT",
                id_keys=["B1_ALT_ID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'job_id': ['B1_ALT_ID'], 'issuance_date': ['ISSUED_DT'], 'cost': ['G3_VALUE_TTL'], 'address_street': ['SITE_ADDRESS'], 'zipcode': ['B1_SITUS_ZIP'], 'status': ['PERMIT_STATUS'], 'job_type': ['B1_PER_TYPE']},
            ),
            # US-127: Franklin County Auditor (FCAO) sales-dashboard points
            # layer — an annual-snapshot ArcGIS FeatureServer, point-geocoded
            # natively via outSR=4326. The layer ships a dual old/new column
            # set (SALEPRICE vs Sale_Price, OWNERNME1 vs OWN1/OWN2), so the
            # field map declares both with the fully-populated new side first.
            # Instrument_Number and MUNINAME/NHBDNAME are empty layer-wide
            # (probed 2026-08-25), so doc_id resolves to PARCELID and borough
            # falls back to coordinate->division (COLUMBUS_CORE). expected_
            # cadence=365 reflects the annual snapshot refresh.
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_columbus_deeds_url,
                platform="arcgis",
                watermark_col="SALEDATE",
                id_keys=["PARCELID", "Instrument_Number", "OBJECTID"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                
                expected_cadence_days=365,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'doc_id': ['Instrument_Number', 'PARCELID'], 'bbl': ['PARCELID'], 'document_amount': ['Sale_Price', 'SALEPRICE'], 'recorded_date': ['SALEDATE'], 'party1_grantor': ['OWNERNME1'], 'party2_grantee': ['OWN1', 'OWN2'], 'incident_address': ['SITEADDRESS'], 'zipcode': ['ZIPCD'], 'borough': ['MUNINAME', 'NHBDNAME']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("OH"),
        },
    ),
    CityId.COLUMBUS_GA: CityRegistration(
        city_id=CityId.COLUMBUS_GA,
        name="Columbus, GA",
        state="GA",
        center={"lat": 32.4610, "lng": -84.9877},
        metro_bbox=COLUMBUS_GA_METRO_BBOX,
        division_bboxes=COLUMBUS_GA_DIVISION_BBOXES,
        submarkets=COLUMBUS_GA_SUBMARKETS,
        divisions=COLUMBUS_GA_DIVISIONS,
        job_suffix="colga",
        # Verified ArcGIS permits (MapServer /0 Residential; client uses outSR=4326).
        # Scheduler does not poll companion_endpoints today; commercial/pool
        # layers can follow as future companions if/when that path grows.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_columbus_ga_permits_url,
                platform="arcgis",
                watermark_col="Issued",
                id_keys=["PermitNumber", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field="OBJECTID",
                max_record_count=2000,
                field_map={
                    "job_id": ["PermitNumber"],
                    "issuance_date": ["Issued"],
                    "cost": ["Valuation"],
                    "address_street": ["Address"],
                    "status": ["PermitStatus"],
                    "job_type": ["WorkClass", "InspectionDivision"],
                },
            ),
            # SLA fallback — SNAP retailers (state slice).
            FeedType.SLA: snap_sla_spec("GA"),
        },
    ),
    CityId.NASHVILLE: CityRegistration(
        city_id=CityId.NASHVILLE,
        name="Nashville / Davidson County",
        state="TN",
        center={"lat": 36.1627, "lng": -86.7818},
        metro_bbox=NASHVILLE_METRO_BBOX,
        division_bboxes=NASHVILLE_DIVISION_BBOXES,
        submarkets=NASHVILLE_SUBMARKETS,
        divisions=NASHVILLE_DIVISIONS,
        job_suffix="bna",
        # Mixed-case Lat/Lon attributes ride no fallback chain, so the field
        # map carries them; the two-date model keeps Date_Entered (application)
        # distinct from Date_Issued. Residential STR permits register as the
        # SLA-class signal (investor-buyout pressure), verified at 100% parse.
        # hubNashville 311 re-adjudicated positive from the HJ-119 exclusion
        # (US-131): the Current_Year view now carries 2026 rows and publishes a
        # 28.5% Latitude gap (52,997 of 185,902 rows), so the where-clause
        # `Latitude IS NOT NULL` filters to a 100%-geocoded stream.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_nashville_permits_url,
                platform="arcgis",
                watermark_col="Date_Issued",
                id_keys=["Permit__", "ObjectId"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='ObjectId',
                max_record_count=1000,
                field_map={'job_id': ['Permit__'], 'issuance_date': ['Date_Issued'], 'filing_date': ['Date_Entered'], 'cost': ['Const_Cost'], 'latitude': ['Lat'], 'longitude': ['Lon']},
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_nashville_str_url,
                platform="arcgis",
                watermark_col="Date_Issued",
                id_keys=["Permit__", "ObjectId"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=14,
                oid_field='ObjectId',
                max_record_count=1000,
                field_map={'license_id': ['Permit__'], 'effective_date': ['Date_Issued'], 'expiration_date': ['Expiration_Date'], 'license_type': ['Permit_Subtype_Description', 'Permit_Type'], 'status': ['Permit_Status'], 'latitude': ['Lat'], 'longitude': ['Lon']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_nashville_311_url,
                platform="arcgis",
                watermark_col="Date_Time_Opened",
                id_keys=["Request__", "GlobalID", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                where='Latitude IS NOT NULL',
                field_map={'incident_id': ['Request__'], 'latitude': ['Latitude'], 'longitude': ['Longitude'], 'created_date': ['Date_Time_Opened'], 'closed_date': ['Date_Time_Closed'], 'status': ['Status'], 'complaint_type': ['Request_Type', 'Subrequest_Type'], 'incident_address': ['Address'], 'zipcode': ['ZIP'], 'borough': ['Council_District']},
            ),
        },
    ),
    CityId.KANSAS_CITY: CityRegistration(
        city_id=CityId.KANSAS_CITY,
        name="Kansas City",
        state="MO",
        center={"lat": 39.10, "lng": -94.58},
        metro_bbox=KANSAS_CITY_METRO_BBOX,
        division_bboxes=KANSAS_CITY_DIVISION_BBOXES,
        submarkets=KANSAS_CITY_SUBMARKETS,
        divisions=KANSAS_CITY_DIVISIONS,
        job_suffix="kcmo",
        # Corrects the 2026-08-23 rejection: the feed was live under a name
        # that survey query missed. Publishes intraday (14/14 consecutive days
        # at the claim-time probe), so the standard G11 window applies. KC
        # permits survive only as dead annual archives and stay unregistered.
        # The SLA feed pnm4-68wg (US-134) is registered as a snapshot: native
        # GeoJSON point geometry (96.4%) plus a valid_license_for YYYYMMDD
        # expiration column, and a 90-day cadence given the ~7m publishing
        # lapse. Its location column is a GeoJSON Point (coordinates), so the
        # producer's generic location-container fallback resolves it rather
        # than the dotted field_map keys.
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_kansas_city_311_endpoint,
                platform="socrata",
                watermark_col="open_date_time",
                id_keys=["reported_issue"],
                topic=settings.topic_311,
                interval_seconds=600.0,
                producer_key="311",
                
                expected_cadence_days=7,
                field_map={'incident_id': ['reported_issue'], 'complaint_type': ['issue_type'], 'created_date': ['open_date_time'], 'status': ['current_status']},
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_kansas_city_licenses_endpoint,
                platform="socrata",
                watermark_col="",
                id_keys=["id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=90,
                ingestion_mode='snapshot',
                alarm_exempt=True,
                alarm_exempt_reason='7-month rowsUpdatedAt publishing lapse, source-side (US-163)',
                field_map={'license_id': ['id'], 'license_type': ['business_type'], 'expiration_date': ['valid_license_for'], 'dba': ['dba_name'], 'latitude': ['location.latitude'], 'longitude': ['location.longitude'], 'incident_address': ['address'], 'borough': ['city'], 'zipcode': ['zipcode']},
            ),
        },
    ),
    CityId.PIERCE: CityRegistration(
        city_id=CityId.PIERCE,
        name="Pierce County",
        state="WA",
        center={"lat": 47.2529, "lng": -122.4443},
        metro_bbox=PIERCE_METRO_BBOX,
        division_bboxes=PIERCE_DIVISION_BBOXES,
        submarkets=PIERCE_SUBMARKETS,
        divisions=PIERCE_DIVISIONS,
        job_suffix="pco",
        # Permits-only ArcGIS registration (US-80 / ADR 0007: separate
        # CityId, never a Seattle division). Point layer in WA State Plane;
        # outSR=4326 lifts WGS84 onto latitude/longitude before parsing.
        # Six departments share the layer; the where-clause filter keeps
        # Building/Land-Use so CapEx density reads clean (survey §1).
        # Watermark rides issuedDate so an accepted application that later
        # issues is re-ingested with its real issuance date; the two-date
        # field-map fallback keeps issuance_date populated on the ~13% of
        # rows still under review (issuedDate null).
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_pierce_permits_url,
                platform="arcgis",
                watermark_col="issuedDate",
                id_keys=["applicationNumber", "projectId", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                where="applicationDept LIKE '%BUILDING%' OR applicationDept LIKE '%LAND USE%'",
                field_map={'job_id': ['applicationNumber'], 'issuance_date': ['issuedDate', 'applicationDate'], 'filing_date': ['applicationDate'], 'cost': ['buildingValuation', 'projectValue'], 'address_street': ['siteAddress'], 'status': ['applicationStatus'], 'job_type': ['applicationType', 'workType', 'buildingType'], 'proposed_units': ['dwellingUnits'], 'proposed_stories': ['stories']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("WA"),
        },
    ),
    CityId.MILWAUKEE: CityRegistration(
        city_id=CityId.MILWAUKEE,
        name="Milwaukee",
        state="WI",
        center={"lat": 43.0389, "lng": -87.9065},
        metro_bbox=MILWAUKEE_METRO_BBOX,
        division_bboxes=MILWAUKEE_DIVISION_BBOXES,
        submarkets=MILWAUKEE_SUBMARKETS,
        divisions=MILWAUKEE_DIVISIONS,
        job_suffix="mke",
        # US-87 registered the liquor-license SLA (point geometry + dates).
        # US-138 adds building PERMITS and recorded DEEDS (CKAN CSV). Both arrive
        # address-only, so they geocode at parse time per ADR-0004; DEEDS uses
        # an ADR-0005 typed text watermark.
        datasets={
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_milwaukee_licenses_url,
                platform="arcgis",
                watermark_col="GIS_DATETIME",
                id_keys=["LICENSE_ID", "OBJECTID"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'license_id': ['LICENSE_ID'], 'effective_date': ['EFFECTIVE_DATE'], 'expiration_date': ['EXPIRATION_DATE'], 'license_type': ['LIC_TYPE_ABBR', 'PROFESSION_FULL_NAME']},
            ),
            # US-138: building permits CSV. Address-only coords — geocoded at
            # parse time per ADR-0004.
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.csv_milwaukee_permits_endpoint,
                platform="csv",
                watermark_col="date_issued",
                id_keys=["record_id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=90,
                order_by='date_issued ASC',
                id_col='record_id',
                needs_geocode=True,
                geocode_context='Milwaukee, WI',
                field_map={'job_id': ['record_id'], 'address_street': ['address'], 'issuance_date': ['date_issued'], 'filing_date': ['date_opened'], 'job_type': ['permit_type'], 'cost': ['construction_total_cost']},
            ),
            # US-138: recorded deeds / property sales CSV. Address-only
            # -> geocoded per ADR-0004; ADR-0005 typed text watermark.
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.csv_milwaukee_deeds_endpoint,
                platform="csv",
                watermark_col="sale_date",
                id_keys=["propertyid"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                
                expected_cadence_days=365,
                order_by='sale_date ASC',
                id_col='propertyid',
                endpoint_by_year={'2024': 'https://data.milwaukee.gov/dataset/7a8b81f6-d750-4f62-aee8-30ffce1c64ce/resource/01651dab-2be7-40c6-a9d6-31254fe02e29/download/armslengthsales_2024_valid_20250917.csv', '2025': settings.csv_milwaukee_deeds_endpoint},
                ingestion_mode='snapshot',
                needs_geocode=True,
                geocode_context='Milwaukee, WI',
                watermark_type='text',
                watermark_format='%m/%d/%Y',
                watermark_exclude=[],
                field_map={'doc_id': ['propertyid'], 'bbl': ['taxkey'], 'address_street': ['address'], 'document_amount': ['sale_price'], 'recorded_date': ['sale_date'], 'doc_type': ['proptype'], 'borough': ['district', 'nbhd']},
            ),
            # US-265: Milwaukee NIBRS crime (CKAN datastore, native lat/long).
            FeedType.CRIME: DatasetSpec(
                endpoint=settings.ckan_milwaukee_crime_endpoint,
                platform="ckan",
                watermark_col="Incident_Last_Edited",
                id_keys=["Case_Number"],
                topic=settings.topic_crime,
                interval_seconds=300.0,
                producer_key="crime",
                expected_cadence_days=7,
                watermark_type="timestamp",
                watermark_format="%Y-%m-%d %H:%M:%S",
                order_by="Incident_Last_Edited ASC",
                field_map={'incident_id': ['Case_Number'], 'latitude': ['Address_Latitude'], 'longitude': ['Address_Longitude'], 'offense_type': ['Offense_All'], 'occurred_date': ['Incident_Date'], 'borough': ['Police_District']},
            ),
            # US-265: Milwaukee Call Center 311 (CKAN, address-only -> geocoded).
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.ckan_milwaukee_311_endpoint,
                platform="ckan",
                watermark_col="CREATIONDATE",
                id_keys=["_id"],
                topic=settings.topic_311,
                interval_seconds=300.0,
                producer_key="311",
                expected_cadence_days=7,
                watermark_type="timestamp",
                watermark_format="%Y-%m-%d %H:%M:%S",
                order_by="CREATIONDATE ASC",
                oid_field="_id",
                needs_geocode=True,
                geocode_context="Milwaukee, WI",
                field_map={'incident_id': ['_id'], 'incident_address': ['OBJECTDESC'], 'complaint_type': ['TITLE'], 'created_date': ['CREATIONDATE'], 'closed_date': ['CLOSEDDATETIME']},
            ),
        },
    ),
    CityId.CHARLOTTE: CityRegistration(
        city_id=CityId.CHARLOTTE,
        name="Charlotte",
        state="NC",
        center={"lat": 35.2271, "lng": -80.8431},
        metro_bbox=CHARLOTTE_METRO_BBOX,
        division_bboxes=CHARLOTTE_DIVISION_BBOXES,
        submarkets=CHARLOTTE_SUBMARKETS,
        divisions=CHARLOTTE_DIVISIONS,
        job_suffix="clt",
        # 311-only registration (US-88): Charlotte's ODP ServiceRequests311
        # layer is the verified machine-readable feed (native LATITUDE/
        # LONGITUDE + point geometry, RECEIVED_DATE watermark). Mecklenburg
        # County permits/parcels sit on an ArcGIS Hub surface with no
        # quickly-verifiable bulk feed; city permits live in Accela ACA;
        # no verified licenses or sales feeds — all unregistered.
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_charlotte_311_url,
                platform="arcgis",
                watermark_col="RECEIVED_DATE",
                id_keys=["REQUEST_NO", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=7500,
                field_map={'incident_id': ['REQUEST_NO'], 'created_date': ['RECEIVED_DATE'], 'complaint_type': ['REQUEST_TYPE'], 'incident_address': ['FULL_ADDRESS'], 'borough': ['COUNCIL_DISTRICT']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("NC"),
        },
    ),
    CityId.PITTSBURGH: CityRegistration(
        city_id=CityId.PITTSBURGH,
        name="Pittsburgh",
        state="PA",
        center={"lat": 40.4417, "lng": -80.0000},
        metro_bbox=PITTSBURGH_METRO_BBOX,
        division_bboxes=PITTSBURGH_DIVISION_BBOXES,
        submarkets=PITTSBURGH_SUBMARKETS,
        divisions=PITTSBURGH_DIVISIONS,
        job_suffix="pgh",
        # WPRDC CKAN registration. Permits (US-89) is the native-lat/lng feed;
        # 311 (US-132) is the post-transition "Pittsburgh 311 Data" resource —
        # native lat/lng as TEXT (5-dec EXACT / 2-dec APPROXIMATE, cast to float
        # by the producer; ~99.8% geocoded in the newest window, legacy 2015-25
        # rows null). deeds (US-129) is the Allegheny County Property Sale
        # Transactions package — price-bearing but address-only / PARID-only, so
        # events are null-H3 like Cook County sales. The old 311 Data Archive is
        # a frozen separate package (the source of the obsolete "address-only
        # archive" verdict) and Licensed Businesses lacks usable addresses —
        # both stay unregistered.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.ckan_pittsburgh_permits_endpoint,
                platform="ckan",
                watermark_col="issue_date",
                id_keys=["permit_id", "parcel_num", "_id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                field_map={'job_id': ['permit_id'], 'issuance_date': ['issue_date'], 'cost': ['total_project_value'], 'address_street': ['address'], 'status': ['status'], 'job_type': ['permit_type', 'work_type'], 'zipcode': ['zip_code']},
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.ckan_pittsburgh_deeds_endpoint,
                platform="ckan",
                # SALEDATE is the freshness watermark: it is 0-null across the
                # 501k-row resource, whereas RECORDDATE has ~1.25k NULLs on the
                # newest-inserted rows — an incremental `RECORDDATE > hw` filter
                # would drop those rows, and a probe sample ordered by
                # `RECORDDATE DESC` is starved of dated rows (SQL sorts NULLs
                # first under DESC). `recorded_date` in field_map still uses
                # RECORDDATE for the event, unaffected by the watermark choice.
                watermark_col="SALEDATE",
                id_keys=["PARID", "RECORDDATE", "SALEDATE", "DEEDBOOK", "DEEDPAGE"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                field_map={'doc_id': ['PARID', 'DEEDBOOK', 'DEEDPAGE'], 'bbl': ['PARID'], 'document_amount': ['PRICE'], 'recorded_date': ['RECORDDATE'], 'doc_type': ['INSTRTYP'], 'borough': ['MUNIDESC', 'PROPERTYCITY'], 'incident_address': ['FULL_ADDRESS']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.ckan_pittsburgh_311_endpoint,
                platform="ckan",
                watermark_col="created_date_utc",
                id_keys=["unique_id", "case_number"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                field_map={'incident_id': ['unique_id', 'case_number'], 'latitude': ['latitude'], 'longitude': ['longitude'], 'created_date': ['created_date_utc'], 'closed_date': ['closed_date_utc'], 'complaint_type': ['subject'], 'incident_address': ['street'], 'borough': ['neighborhood', 'council_district', 'ward']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("PA"),
        },
    ),
    CityId.SAN_DIEGO: CityRegistration(
        city_id=CityId.SAN_DIEGO,
        name="San Diego",
        state="CA",
        center={"lat": 32.7157, "lng": -117.1611},
        metro_bbox=SAN_DIEGO_METRO_BBOX,
        division_bboxes=SAN_DIEGO_DIVISION_BBOXES,
        submarkets=SAN_DIEGO_SUBMARKETS,
        divisions=SAN_DIEGO_DIVISIONS,
        job_suffix="sd",
        # Partial registration (US-91 permits, US-124 311, US-125 SLA).
        # data.sandiego.gov is a static-CSV portal (seshat.datasd.org) with no
        # Socrata/ArcGIS API. Permits, Get It Done 311, and Business Tax
        # Certificates are CSV-only and geocoded (native lat/lng); the first
        # two are year-scoped (D3 endpoint_by_year), the SLA one a full
        # SNAPSHOT re-pulled each poll and deduped on account_key. No
        # property/deeds source exists in the 122-dataset inventory — DEEDS
        # stays unregistered.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.csv_san_diego_permits_endpoint,
                platform="csv",
                watermark_col="approval_issue_date",
                id_keys=["approval_id", "development_id", "project_id"],
                topic=settings.topic_permits,
                interval_seconds=1800.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                endpoint_by_year={'2026': 'https://seshat.datasd.org/development_permits/approvals_issued_2026_datasd.csv', '2027': 'https://seshat.datasd.org/development_permits/approvals_issued_2027_datasd.csv'},
                field_map={'job_id': ['approval_id'], 'issuance_date': ['approval_issue_date'], 'filing_date': ['approval_create_date'], 'cost': ['approval_valuation'], 'latitude': ['gis_latitude'], 'longitude': ['gis_longitude'], 'address_street': ['gis_address'], 'job_type': ['approval_type'], 'status': ['approval_status']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.csv_san_diego_311_endpoint,
                platform="csv",
                watermark_col="date_requested",
                id_keys=["service_request_id"],
                topic=settings.topic_311,
                interval_seconds=1800.0,
                producer_key="311",
                
                expected_cadence_days=7,
                endpoint_by_year={'2016': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2016_datasd.csv', '2017': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2017_datasd.csv', '2018': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2018_datasd.csv', '2019': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2019_datasd.csv', '2020': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2020_datasd.csv', '2021': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2021_datasd.csv', '2022': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2022_datasd.csv', '2023': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2023_datasd.csv', '2024': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2024_datasd.csv', '2025': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2025_datasd.csv', '2026': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2026_datasd.csv', '2027': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2027_datasd.csv'},
                companion_endpoints={'open': 'https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_open_datasd.csv'},
                field_map={'incident_id': ['service_request_id'], 'created_date': ['date_requested'], 'closed_date': ['date_closed'], 'complaint_type': ['service_name', 'service_name_detail'], 'latitude': ['lat'], 'longitude': ['lng'], 'incident_address': ['street_address'], 'zipcode': ['zipcode'], 'borough': ['council_district', 'comm_plan_name']},
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.csv_san_diego_licenses_endpoint,
                platform="csv",
                watermark_col="date_account_creation",
                id_keys=["account_key"],
                topic=settings.topic_sla,
                interval_seconds=1800.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                ingestion_mode='snapshot',
                field_map={'license_id': ['account_key'], 'effective_date': ['date_cert_effective'], 'expiration_date': ['date_cert_expiration'], 'license_type': ['naics_description', 'naics_sector'], 'dba': ['dba_name'], 'latitude': ['lat'], 'longitude': ['lng'], 'borough': ['council_district', 'bid'], 'address_street': ['address_road']},
            ),
        },
    ),
    CityId.INDIANAPOLIS: CityRegistration(
        city_id=CityId.INDIANAPOLIS,
        name="Indianapolis / Marion County",
        state="IN",
        center={"lat": 39.7684, "lng": -86.1581},
        metro_bbox=INDIANAPOLIS_METRO_BBOX,
        division_bboxes=INDIANAPOLIS_DIVISION_BBOXES,
        submarkets=INDIANAPOLIS_SUBMARKETS,
        divisions=INDIANAPOLIS_DIVISIONS,
        job_suffix="indianapolis",
        # 311-only registration (US-144): the RIMAC service-request layer is the
        # verified machine-readable feed (native point geometry + LAT/LONG_
        # attributes, REQUESTEDDATETIME epoch-ms watermark ~718.6k rows). City
        # permits sit in Accela Citizen Access (no public bulk API), INBiz SOS
        # bulk data is paid, and sales exist only as a nightly parcel snapshot —
        # so PERMITS/SLA/DEEDS stay deliberately unregistered; get_dataset
        # raises readable errors for them. Native LAT/LONG_ ride the field map
        # (uppercase), not a generic fallback.
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_indianapolis_311_url,
                platform="arcgis",
                watermark_col="REQUESTEDDATETIME",
                id_keys=["SERVICEREQUESTID", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'incident_id': ['SERVICEREQUESTID', 'EXTERNALSERVICEREQUEST'], 'created_date': ['REQUESTEDDATETIME'], 'closed_date': ['CLOSEDDATETIME'], 'status': ['STATUS'], 'complaint_type': ['ACTIVITY', 'SERVICENAME'], 'incident_address': ['ADDRESS'], 'borough': ['COUNCILDISTRICT'], 'zipcode': ['ZIPCODE'], 'latitude': ['LAT'], 'longitude': ['LONG_']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("IN"),
        },
    ),
    CityId.HOUSTON: CityRegistration(
        city_id=CityId.HOUSTON,
        name="Houston",
        state="TX",
        center={"lat": 29.7604, "lng": -95.3698},
        metro_bbox=HOUSTON_METRO_BBOX,
        division_bboxes=HOUSTON_DIVISION_BBOXES,
        submarkets=HOUSTON_SUBMARKETS,
        divisions=HOUSTON_DIVISIONS,
        job_suffix="houston",
        # 311-only registration (US-140): City of Houston mycity2
        # HOUSTON311_RECENT_SR_SNOW FeatureServer — native LATITUDE/LONGITUDE
        # doubles + point geometry, CREATED_ON epoch-ms watermark, newest row
        # 2026-08-24 (probed 2026-08-26). Rolling recent window with bounded
        # backfill to 2021-07; 99.98% geocoded (9 of 47,100 rows null lat/lng),
        # so no where-filter is needed. No permits/licenses/deeds feed exists on
        # any Houston portal (research: permits are Accela transactional not on a
        # portal; deeds are annual aggregate XLS) — all unregistered.
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_houston_311_url,
                platform="arcgis",
                watermark_col="CREATED_ON",
                id_keys=["CASE_NUMBER", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'incident_id': ['CASE_NUMBER'], 'latitude': ['LATITUDE'], 'longitude': ['LONGITUDE'], 'complaint_type': ['CASE_TYPE'], 'created_date': ['CREATED_ON'], 'closed_date': ['CLOSED_ON'], 'status': ['STATUS'], 'incident_address': ['ADDRESS', 'STREET'], 'zipcode': ['ZIP'], 'borough': ['SUPERNEIGHBORHOOD', 'COUNCIL_DISTRICT']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("TX"),
        },
    ),
    CityId.WICHITA: CityRegistration(
        city_id=CityId.WICHITA,
        name="Wichita",
        state="KS",
        center={"lat": 37.6872, "lng": -97.3301},
        metro_bbox=WICHITA_METRO_BBOX,
        division_bboxes=WICHITA_DIVISION_BBOXES,
        submarkets=WICHITA_SUBMARKETS,
        divisions=WICHITA_DIVISIONS,
        job_suffix="wichita",
        # Permits-only registration (US-157). The MISC/MABCD FeatureServer
        # publishes two point layers: layer 0 is Code Enforcement Violations (a
        # documented trap — the tickets that reference it are violations, not
        # permits) and layer 1 is the real MABCD permits SDE. ApplicationDate is
        # the epoch-ms watermark (newest 2026-08-25, day of probe). PermitNumber
        # identifies the permit (e.g. RFS2026-11032); OBJECTID stays out of the
        # job-id chain as an edit counter, mirroring the Columbus precedent.
        # No open 311/licenses/deeds feed exists, so get_dataset raises readable
        # errors for them. Point geometry (native lat/lng via outSR=4326) and
        # ApplicationDate epoch-ms are handled by the shared ArcGISClient.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_wichita_permits_url,
                platform="arcgis",
                watermark_col="ApplicationDate",
                id_keys=["PermitNumber", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'job_id': ['PermitNumber'], 'issuance_date': ['ApplicationDate'], 'cost': ['DeclaredValuation'], 'job_type': ['WorkType', 'OccupancyType'], 'status': ['PermitStatus'], 'address_street': ['InwardAddress'], 'zipcode': ['PostalCode'], 'borough': ['Jurisdiction', 'City']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("KS"),
        },
    ),
    CityId.CHATTANOOGA: CityRegistration(
        city_id=CityId.CHATTANOOGA,
        name="Chattanooga / Hamilton County",
        state="TN",
        center={"lat": 35.0456, "lng": -85.3097},
        metro_bbox=CHATTANOOGA_METRO_BBOX,
        division_bboxes=CHATTANOOGA_DIVISION_BBOXES,
        submarkets=CHATTANOOGA_SUBMARKETS,
        divisions=CHATTANOOGA_DIVISIONS,
        job_suffix="chattanooga",
        # US-155: the Hub CSV is the live permits source; the hosted
        # Permits_Permitted_to_Contractor FeatureServer twin is frozen and is
        # deliberately not used. The parcel layer is live but its sale-date
        # values are epoch-ms and reject the scheduler's ISO where literal, so
        # it runs as a snapshot feed while the parser still preserves dates.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.csv_chattanooga_permits_endpoint,
                platform="csv",
                watermark_col="issueddate",
                id_keys=["permitnum"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                order_by='issueddate DESC',
                fallback_endpoints=[settings.csv_chattanooga_permits_fallback_endpoint],
                field_map={'job_id': ['permitnum'], 'issuance_date': ['issueddate'], 'filing_date': ['applieddate'], 'job_type': ['permitclass'], 'cost': ['estprojectcostdec'], 'status': ['status'], 'address_street': ['address'], 'zipcode': ['zipcode', 'zip'], 'bbl': ['pin']},
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_chattanooga_deeds_url,
                platform="arcgis",
                watermark_col="SALE1DATE",
                id_keys=["PIN", "OBJECTID"],
                topic=settings.topic_deeds,
                interval_seconds=1800.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                ingestion_mode='snapshot',
                oid_field='OBJECTID',
                max_record_count=1000,
                field_map={'doc_id': ['PIN', 'PARCELID', 'OBJECTID'], 'recorded_date': ['SALE1DATE'], 'document_amount': ['SALE1CONSD'], 'bbl': ['PIN', 'PARCELID'], 'party2_grantee': ['OWNERNAME1'], 'doc_type': ['SALE1TYPE', 'DEEDTYPE', 'TYPE'], 'borough': ['MUNICIPALITY', 'CITY']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("TN"),
        },
    ),
    CityId.CLEVELAND: CityRegistration(
        city_id=CityId.CLEVELAND,
        name="Cleveland / Cuyahoga County",
        state="OH",
        center={"lat": 41.4993, "lng": -81.6944},
        metro_bbox=CLEVELAND_METRO_BBOX,
        division_bboxes=CLEVELAND_DIVISION_BBOXES,
        submarkets=CLEVELAND_SUBMARKETS,
        divisions=CLEVELAND_DIVISIONS,
        job_suffix="cleveland",
        # US-153: all three feeds are live ArcGIS layers from the Cleveland
        # Open Data organization. Issued permits have a documented ~10-day
        # publication lag; use ISSUE_DATE as the stable watermark. Parcel
        # analytics is polygonal, so ArcGISClient supplies centroid coords.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_cleveland_permits_url,
                platform="arcgis",
                watermark_col="ISSUE_DATE",
                id_keys=["PERMIT_NUMBER", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=14,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'job_id': ['PERMIT_NUMBER'], 'issuance_date': ['ISSUE_DATE'], 'filing_date': ['FILE_DATE'], 'job_type': ['PERMIT_TYPE', 'PERMIT_SUBTYPE'], 'cost': ['JOB_VALUE'], 'status': ['STATUS', 'PERMIT_STATUS'], 'address_street': ['ADDRESS'], 'zipcode': ['ZIP', 'ZIP_CODE'], 'bbl': ['PARCEL_NUMBER']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_cleveland_311_url,
                platform="arcgis",
                watermark_col="requested_datetime",
                id_keys=["SR_NUMBER", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'incident_id': ['SR_NUMBER', 'SERVICE_REQUEST_ID', 'REQUEST_ID'], 'created_date': ['requested_datetime'], 'closed_date': ['closed_datetime', 'closed_date'], 'status': ['status'], 'complaint_type': ['service_name'], 'incident_address': ['address'], 'borough': ['ward', 'neighborhood'], 'zipcode': ['zip', 'zipcode'], 'latitude': ['lat'], 'longitude': ['long']},
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_cleveland_deeds_url,
                platform="arcgis",
                watermark_col="last_transfer_date",
                id_keys=["PARCEL_ID", "OBJECTID"],
                topic=settings.topic_deeds,
                interval_seconds=1800.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                ingestion_mode='snapshot',
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'doc_id': ['PARCEL_ID', 'PARCEL_NUMBER', 'OBJECTID'], 'recorded_date': ['last_transfer_date'], 'document_amount': ['sale_price', 'transfer_amount'], 'bbl': ['parcel_number', 'PARCEL_NUMBER', 'PARCEL_ID'], 'party1_grantor': ['grantor'], 'party2_grantee': ['grantee'], 'doc_type': ['document_type', 'deed_type'], 'borough': ['ward', 'neighborhood']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("OH"),
        },
    ),
    CityId.HARTFORD: CityRegistration(
        city_id=CityId.HARTFORD,
        name="Hartford",
        state="CT",
        center={"lat": 41.7637, "lng": -72.6734},
        metro_bbox=HARTFORD_METRO_BBOX,
        division_bboxes=HARTFORD_DIVISION_BBOXES,
        submarkets=HARTFORD_SUBMARKETS,
        divisions=HARTFORD_DIVISIONS,
        job_suffix="hartford",
        # US-152: live ArcGIS 311 and permit tables plus Connecticut's daily
        # statewide eLicensing Socrata feed. The ArcGIS 311 X/Y values are CT
        # state-plane feet and the other records are address-only, so all three
        # feeds use the ADR-0004 geocoder hook.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_hartford_permits_url,
                platform="arcgis",
                watermark_col="DateIssued",
                id_keys=["RECORD_ID", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                needs_geocode=True,
                geocode_context='Hartford, CT',
                field_map={'job_id': ['RECORD_ID'], 'issuance_date': ['DateIssued'], 'job_type': ['PermitType', 'PERMIT_TYPE', 'WorkDescription'], 'cost': ['EstimatedCost', 'COST', 'ProjectCost'], 'status': ['Status', 'STATUS'], 'address_street': ['PROPERTY_ADDRESS', 'Location'], 'zipcode': ['ZIP', 'ZipCode', 'POSTAL_CODE'], 'bbl': ['PARCEL_ID', 'ParcelID']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_hartford_311_url,
                platform="arcgis",
                watermark_col="USER_Opened_Date",
                id_keys=["SR_Number", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                endpoint_by_year={'2026': settings.arcgis_hartford_311_url},
                needs_geocode=True,
                geocode_context='Hartford, CT',
                field_map={'incident_id': ['SR_Number', 'SRM_Number', 'OBJECTID'], 'created_date': ['USER_Opened_Date'], 'closed_date': ['USER_Closed_Date', 'Closed_Date'], 'status': ['Status', 'STATUS'], 'complaint_type': ['SR_Type', 'Request_Type', 'Service_Name'], 'incident_address': ['Match_addr', 'Location', 'Address'], 'borough': ['Neighborhood', 'Council_District'], 'zipcode': ['ZIP', 'ZipCode', 'PostalCode']},
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_hartford_sla_endpoint,
                platform="socrata",
                watermark_col="recordrefreshedon",
                id_keys=["license_number", "credential_number", "id"],
                topic=settings.topic_sla,
                interval_seconds=3600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                where="city = 'HARTFORD'",
                needs_geocode=True,
                geocode_context='Hartford, CT',
                field_map={'license_id': ['license_number', 'credential_number', 'id'], 'license_type': ['credential_type', 'credential_name', 'license_type'], 'effective_date': ['effective_date', 'issue_date'], 'expiration_date': ['expiration_date', 'expiry_date'], 'address_street': ['address', 'street_address', 'address_line_1'], 'zipcode': ['zip', 'zipcode', 'postal_code'], 'borough': ['city'], 'premises_name': ['business_name', 'name'], 'dba': ['business_name', 'name'], 'status': ['status', 'license_status']},
            ),
        },
    ),
    CityId.RALEIGH: CityRegistration(
        city_id=CityId.RALEIGH,
        name="Raleigh / Wake County",
        state="NC",
        center={"lat": 35.7796, "lng": -78.6382},
        metro_bbox=RALEIGH_METRO_BBOX,
        division_bboxes=RALEIGH_DIVISION_BBOXES,
        submarkets=RALEIGH_SUBMARKETS,
        divisions=RALEIGH_DIVISIONS,
        job_suffix="raleigh",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_raleigh_permits_url,
                platform="arcgis",
                watermark_col="issueddate",
                id_keys=["permitnum", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'job_id': ['permitnum', 'permitnumber'], 'issuance_date': ['issueddate'], 'filing_date': ['submitteddate', 'applicationdate'], 'job_type': ['permittypemapped', 'permittype', 'permitclass'], 'cost': ['estprojectcost', 'estimatedcost'], 'status': ['statuscurrent', 'status'], 'address_street': ['originaladdress1', 'address'], 'zipcode': ['originalzip', 'zip', 'zip_code'], 'bbl': ['pin', 'parcelid'], 'latitude': ['latitude_perm'], 'longitude': ['longitude_perm']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_raleigh_311_url,
                platform="arcgis",
                watermark_col="APPLIED_DATE",
                id_keys=["REQUEST_ID", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'incident_id': ['REQUEST_ID', 'SR_NUMBER', 'OBJECTID'], 'created_date': ['APPLIED_DATE'], 'closed_date': ['RESOLVED_DATE', 'CLOSED_DATE'], 'status': ['STATUS', 'Status'], 'complaint_type': ['CATEGORY', 'SERVICE', 'REQUEST_TYPE'], 'incident_address': ['ADDRESS', 'FULL_ADDRESS'], 'borough': ['DISTRICT', 'NEIGHBORHOOD'], 'zipcode': ['ZIP_CODE', 'ZIP']},
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_wake_deeds_url,
                platform="arcgis",
                watermark_col="SALE_DATE",
                id_keys=["OBJECTID", "PIN"],
                topic=settings.topic_deeds,
                interval_seconds=1800.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                ingestion_mode='snapshot',
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'doc_id': ['OBJECTID', 'PIN', 'PARCELID'], 'recorded_date': ['SALE_DATE'], 'document_amount': ['TOTSALPRICE', 'SALE_PRICE'], 'bbl': ['PIN', 'PARCELID'], 'party2_grantee': ['OWNER_NAME', 'OWNERNAME'], 'doc_type': ['DEED_TYPE', 'SALE_TYPE'], 'borough': ['MUNICIPALITY', 'CITY']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("NC"),
        },
    ),
    CityId.SAN_ANTONIO: CityRegistration(
        city_id=CityId.SAN_ANTONIO,
        name="San Antonio / Bexar County",
        state="TX",
        center={"lat": 29.4241, "lng": -98.4936},
        metro_bbox=SAN_ANTONIO_METRO_BBOX,
        division_bboxes=SAN_ANTONIO_DIVISION_BBOXES,
        submarkets=SAN_ANTONIO_SUBMARKETS,
        divisions=SAN_ANTONIO_DIVISIONS,
        job_suffix="san_antonio",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.ckan_san_antonio_permits_endpoint,
                platform="ckan",
                watermark_col="DATE ISSUED",
                id_keys=["PERMIT NUMBER", "PERMIT_NUMBER", "RECORD_ID", "_id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                needs_geocode=True,
                geocode_context='San Antonio, TX',
                field_map={'job_id': ['PERMIT NUMBER', 'PERMIT_NUMBER', 'RECORD_ID', '_id'], 'issuance_date': ['DATE ISSUED'], 'filing_date': ['DATE SUBMITTED'], 'job_type': ['PERMIT TYPE', 'PERMIT_TYPE', 'WORK TYPE'], 'cost': ['ESTIMATED COST', 'ESTIMATED_COST', 'TOTAL PROJECT VALUE'], 'status': ['STATUS', 'PERMIT STATUS'], 'address_street': ['ADDRESS'], 'zipcode': ['ZIP', 'ZIP CODE', 'ZIP_CODE'], 'latitude': ['Y_COORD'], 'longitude': ['X_COORD']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_san_antonio_311_url,
                platform="arcgis",
                watermark_col="OpenedDateTime",
                id_keys=["ServiceRequestNumber", "SRNumber", "REQUEST_ID", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'incident_id': ['ServiceRequestNumber', 'SRNumber', 'REQUEST_ID', 'OBJECTID'], 'created_date': ['OpenedDateTime'], 'closed_date': ['ClosedDateTime', 'ClosedDate'], 'status': ['Status', 'STATUS'], 'complaint_type': ['ServiceName', 'RequestType', 'Type'], 'incident_address': ['Address', 'StreetAddress'], 'borough': ['CouncilDistrict', 'Neighborhood'], 'zipcode': ['ZipCode', 'ZIP']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("TX"),
        },
    ),
    CityId.SACRAMENTO: CityRegistration(
        city_id=CityId.SACRAMENTO,
        name="Sacramento / Sacramento County",
        state="CA",
        center={"lat": 38.5816, "lng": -121.4944},
        metro_bbox=SACRAMENTO_METRO_BBOX,
        division_bboxes=SACRAMENTO_DIVISION_BBOXES,
        submarkets=SACRAMENTO_SUBMARKETS,
        divisions=SACRAMENTO_DIVISIONS,
        job_suffix="sacramento",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_sacramento_permits_url,
                platform="arcgis",
                watermark_col="ISSUED_DATE",
                id_keys=["Application", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",

                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                needs_geocode=False,
                companion_endpoints={
                    "city_bldg_permits_issued_current_year": settings.arcgis_sacramento_city_permits_url,
                },
                field_map={'job_id': ['Application', 'OBJECTID'], 'issuance_date': ['ISSUED_DATE'], 'filing_date': ['APPLIED_DATE', 'OpenDate'], 'job_type': ['Application_Type', 'Application_Subtype', 'PermitCategory'], 'cost': ['Valuation'], 'status': ['Application_Status'], 'address_street': ['Address'], 'zipcode': ['ZIP', 'ZipCode'], 'bbl': ['Parcel_Number']},
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_sacramento_311_url,
                platform="arcgis",
                watermark_col="DateCreated",
                id_keys=["ReferenceNumber", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'incident_id': ['ReferenceNumber', 'OBJECTID'], 'created_date': ['DateCreated'], 'closed_date': ['DateClosed'], 'status': ['PublicStatus'], 'complaint_type': ['CategoryLevel2', 'CategoryLevel1', 'CategoryName'], 'incident_address': ['Address'], 'borough': ['Neighborhood', 'CouncilDistrictNumber'], 'zipcode': ['ZIP']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("CA"),
        },
    ),
    CityId.RENO: CityRegistration(
        city_id=CityId.RENO,
        name="Reno / Washoe County",
        state="NV",
        center={"lat": 39.5296, "lng": -119.8138},
        metro_bbox=RENO_METRO_BBOX,
        division_bboxes=RENO_DIVISION_BBOXES,
        submarkets=RENO_SUBMARKETS,
        divisions=RENO_DIVISIONS,
        job_suffix="reno",
        # US-161: Washoe's public parcel share is a live county-wide polygon
        # layer. SALEDATE is MM/DD/YYYY text, so scheduler watermark state must
        # retain the declared string format rather than compare raw strings
        # across years. ArcGISClient requests outSR=4326 and derives polygon
        # centroids for the deed event coordinates.
        datasets={
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_reno_deeds_url,
                platform="arcgis",
                watermark_col="SALEDATE",
                id_keys=["PIN", "OBJECTID"],
                topic=settings.topic_deeds,
                interval_seconds=1800.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                ingestion_mode='snapshot',
                oid_field='OBJECTID',
                max_record_count=2000,
                watermark_type='text',
                watermark_format='%m/%d/%Y',
                field_map={'doc_id': ['PIN', 'OBJECTID'], 'bbl': ['PIN'], 'document_amount': ['SALEPRICE'], 'recorded_date': ['SALEDATE'], 'borough': ['CITY', 'SUBNAME']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("NV"),
        },
    ),
    CityId.SPOKANE: CityRegistration(
        city_id=CityId.SPOKANE,
        name="Spokane / Spokane County",
        state="WA",
        center={"lat": 47.6588, "lng": -117.4260},
        metro_bbox=SPOKANE_METRO_BBOX,
        division_bboxes=SPOKANE_DIVISION_BBOXES,
        submarkets=SPOKANE_SUBMARKETS,
        divisions=SPOKANE_DIVISIONS,
        job_suffix="spokane",
        datasets={
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_spokane_deeds_url,
                platform="arcgis",
                watermark_col="document_date",
                id_keys=["Parcel", "OBJECTID"],
                topic=settings.topic_deeds,
                interval_seconds=1800.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                endpoint_by_year={'2015': settings.arcgis_spokane_deeds_url.replace('/20', '/7'), '2016': settings.arcgis_spokane_deeds_url.replace('/20', '/6'), '2017': settings.arcgis_spokane_deeds_url.replace('/20', '/11'), '2018': settings.arcgis_spokane_deeds_url.replace('/20', '/10'), '2019': settings.arcgis_spokane_deeds_url.replace('/20', '/14'), '2020': settings.arcgis_spokane_deeds_url.replace('/20', '/15'), '2021': settings.arcgis_spokane_deeds_url.replace('/20', '/16'), '2022': settings.arcgis_spokane_deeds_url.replace('/20', '/5'), '2023': settings.arcgis_spokane_deeds_url.replace('/20', '/17'), '2024': settings.arcgis_spokane_deeds_url.replace('/20', '/18'), '2025': settings.arcgis_spokane_deeds_url.replace('/20', '/19'), '2026': settings.arcgis_spokane_deeds_url},
                field_map={'doc_id': ['Parcel', 'OBJECTID'], 'bbl': ['Parcel'], 'document_amount': ['gross_sale_price'], 'recorded_date': ['document_date'], 'doc_type': ['prop_use_code']},
            ),
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.excel_spokane_permits_url,
                platform="excel",
                watermark_col="issued_date",
                id_keys=["permit_number"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                needs_geocode=True,
                geocode_context='Spokane, WA',
                field_map={'job_id': ['permit_number'], 'issuance_date': ['issued_date'], 'filing_date': ['issued_date'], 'job_type': ['permit_type', 'project_description'], 'status': ['status', 'status_description'], 'address_street': ['site_address'], 'zipcode': ['site_zip'], 'bbl': ['parcel_number']},
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_wa_liquor_renewal_endpoint,
                platform="socrata",
                watermark_col="renewaldate",
                id_keys=["license", "ubi"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                where="city = 'SPOKANE'",
                field_map={'license_id': ['license'], 'license_type': ['l_a_type'], 'premises_name': ['designatedsignee'], 'dba': ['tradename'], 'address_street': ['streetaddress'], 'expiration_date': ['renewaldate'], 'borough': ['cityname', 'city']},
            ),
        },
    ),
    CityId.DAYTON: CityRegistration(
        city_id=CityId.DAYTON,
        name="Dayton / Montgomery County",
        state="OH",
        center={"lat": 39.7589, "lng": -84.1916},
        metro_bbox=DAYTON_METRO_BBOX,
        division_bboxes=DAYTON_DIVISION_BBOXES,
        submarkets=DAYTON_SUBMARKETS,
        divisions=DAYTON_DIVISIONS,
        job_suffix="dayton",
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_dayton_311_url,
                platform="arcgis",
                watermark_col="ADDDTTM",
                id_keys=["RowNumber", "REFNO"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='RowNumber',
                max_record_count=2000,
                rolling_window_days=90,
                retention_days=90,
                field_map={'incident_id': ['RowNumber', 'REFNO'], 'created_date': ['ADDDTTM'], 'closed_date': ['RESDTTM', 'ModDTTM'], 'status': ['RESFLAG', 'RESCODE'], 'complaint_type': ['PROBDESC', 'CatName', 'ProbDesc2'], 'incident_address': ['ADDRESS', 'LOC'], 'borough': ['NEIGH_COM', 'DISTRICT']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("OH"),
        },
    ),
    CityId.TULSA: CityRegistration(
        city_id=CityId.TULSA,
        name="Tulsa / Tulsa County",
        state="OK",
        center={"lat": 36.1540, "lng": -95.9928},
        metro_bbox=TULSA_METRO_BBOX,
        division_bboxes=TULSA_DIVISION_BBOXES,
        submarkets=TULSA_SUBMARKETS,
        divisions=TULSA_DIVISIONS,
        job_suffix="tulsa",
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_tulsa_311_url,
                platform="arcgis",
                watermark_col="case_opened",
                id_keys=["case_id", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                rolling_window_days=30,
                retention_days=30,
                field_map={'incident_id': ['case_id', 'OBJECTID'], 'created_date': ['case_opened'], 'closed_date': ['case_closed'], 'status': ['case_status'], 'complaint_type': ['case_type', 'case_reason', 'case_subject'], 'incident_address': ['case_external_ref']},
            ),
            # US-265: Tulsa crime (ArcGIS FeatureServer; coords from point geometry).
            FeedType.CRIME: DatasetSpec(
                endpoint=settings.arcgis_tulsa_crime_url,
                platform="arcgis",
                watermark_col="START_DATE",
                id_keys=["INCIDENT_NUM", "OBJECTID"],
                topic=settings.topic_crime,
                interval_seconds=300.0,
                producer_key="crime",
                expected_cadence_days=7,
                oid_field="OBJECTID",
                max_record_count=1000,
                field_map={'incident_id': ['INCIDENT_NUM', 'OBJECTID'], 'offense_type': ['CRIME_TYPE'], 'occurred_date': ['START_DATE']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("OK"),
        },
    ),
    CityId.EL_PASO: CityRegistration(
        city_id=CityId.EL_PASO,
        name="El Paso / El Paso County",
        state="TX",
        center={"lat": 31.7619, "lng": -106.4850},
        metro_bbox=EL_PASO_METRO_BBOX,
        division_bboxes=EL_PASO_DIVISION_BBOXES,
        submarkets=EL_PASO_SUBMARKETS,
        divisions=EL_PASO_DIVISIONS,
        job_suffix="el_paso",
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_el_paso_311_url,
                platform="arcgis",
                watermark_col="created_at",
                id_keys=["id", "request_id", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                rolling_window_days=30,
                retention_days=30,
                field_map={'incident_id': ['id', 'request_id', 'OBJECTID'], 'created_date': ['created_at'], 'status': ['status'], 'complaint_type': ['request_type', 'request_category'], 'incident_address': ['address'], 'borough': ['district']},
            ),
            # US-265: El Paso building permits (ArcGIS; frozen 2018-2021 snapshot).
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_el_paso_permits_url,
                platform="arcgis",
                watermark_col="Issued_Dat",
                id_keys=["B1_ALT_ID", "FID", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=7,
                oid_field="FID",
                max_record_count=1000,
                alarm_exempt=True,
                alarm_exempt_reason="frozen 2018-2021 historical building-permit snapshot",
                field_map={'job_id': ['B1_ALT_ID'], 'cost': ['JOBVALUE'], 'issued_date': ['Issued_Dat']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("TX"),
        },
    ),
    CityId.DURHAM: CityRegistration(
        city_id=CityId.DURHAM,
        name="Durham / Durham County",
        state="NC",
        center={"lat": 36.0014, "lng": -78.9018},
        metro_bbox=DURHAM_METRO_BBOX,
        division_bboxes=DURHAM_DIVISION_BBOXES,
        submarkets=DURHAM_SUBMARKETS,
        divisions=DURHAM_DIVISIONS,
        job_suffix="durham",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_durham_permits_url,
                platform="arcgis",
                watermark_col="ISSUE_DATE",
                id_keys=["PermitNum", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map={'job_id': ['PermitNum', 'OBJECTID'], 'issuance_date': ['ISSUE_DATE'], 'job_type': ['BLDB_ACTIVITY', 'BLDB_ACTIVITY_1', 'TYPE', 'BLD_Type'], 'cost': ['BLD_Cost'], 'address_street': ['LOCATION_ADDR'], 'bbl': ['PIN15', 'PIN', 'PID'], 'status': ['PmtStatus'], 'proposed_units': ['DWELLING_UNITS']},
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_durham_deeds_url,
                platform="arcgis",
                watermark_col="PKG_SALE_DATE",
                id_keys=["PIN", "OBJECTID_1", "OBJECTID"],
                topic=settings.topic_deeds,
                interval_seconds=1800.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                ingestion_mode='snapshot',
                oid_field='OBJECTID_1',
                max_record_count=2000,
                field_map={'doc_id': ['PIN', 'OBJECTID_1', 'OBJECTID'], 'bbl': ['PIN', 'PIN_EXT'], 'recorded_date': ['PKG_SALE_DATE', 'DEED_DATE'], 'document_amount': ['PKG_SALE_PRICE', 'LAND_SALE_PRICE'], 'party1_grantor': ['PROPERTY_OWNER'], 'borough': ['NEIGHBORHOOD', 'CITY']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("NC"),
        },
    ),
    CityId.DALLAS: CityRegistration(
        city_id=CityId.DALLAS,
        name="Dallas / Dallas County",
        state="TX",
        center={"lat": 32.7767, "lng": -96.7970},
        metro_bbox=DALLAS_METRO_BBOX,
        division_bboxes=DALLAS_DIVISION_BBOXES,
        submarkets=DALLAS_SUBMARKETS,
        divisions=DALLAS_DIVISIONS,
        job_suffix="dallas",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_dallas_row_permits_url,
                platform="arcgis",
                watermark_col="CREATEDDATE",
                id_keys=["EXTERNALFILENUM", "JOBID", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                order_by='CREATEDDATE DESC',
                proxy_for='row_permits',
                field_map=DALLAS_FIELD_MAP,
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_dallas_311_url,
                platform="arcgis",
                watermark_col="CreatedDate",
                id_keys=["Service_Request_Number_c", "CaseNumber", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=1,
                oid_field='OBJECTID',
                max_record_count=2000,
                rolling_window_days=30,
                retention_days=30,
                field_map=DALLAS_311_FIELD_MAP,
            ),
            # US-265 note: Dallas Crimes (pumt-d92b) is NOT registered — the feed
            # publishes no lat/lng and no street-address column, so it cannot be
            # geocoded by ADR-0004. Deferred pending a coordinate- or
            # address-bearing Dallas crime resource.
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("TX"),
        },
    ),
    CityId.LOUISVILLE: CityRegistration(
        city_id=CityId.LOUISVILLE,
        name="Louisville / Jefferson County",
        state="KY",
        center={"lat": 38.2527, "lng": -85.7585},
        metro_bbox=LOUISVILLE_METRO_BBOX,
        division_bboxes=LOUISVILLE_DIVISION_BBOXES,
        submarkets=LOUISVILLE_SUBMARKETS,
        divisions=LOUISVILLE_DIVISIONS,
        job_suffix="louisville",
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_louisville_311_url,
                platform="arcgis",
                watermark_col="requested_datetime",
                id_keys=["service_request_id", "ObjectId"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=30,
                oid_field='ObjectId',
                max_record_count=2000,
                annual_rotation=True,
                field_map=LOUISVILLE_311_FIELD_MAP,
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_louisville_abc_url,
                platform="arcgis",
                watermark_col="IssueDate",
                id_keys=["LicenseNumber", "ObjectId"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                oid_field='ObjectId',
                max_record_count=2000,
                where="County = 'Jefferson'",
                field_map=LOUISVILLE_SLA_FIELD_MAP,
            ),
            # US-265: Louisville crime (ArcGIS; no native coords -> geocoded).
            FeedType.CRIME: DatasetSpec(
                endpoint=settings.arcgis_louisville_crime_url,
                platform="arcgis",
                watermark_col="date_occurred",
                id_keys=["incident_number", "ObjectId"],
                topic=settings.topic_crime,
                interval_seconds=300.0,
                producer_key="crime",
                expected_cadence_days=7,
                oid_field="ObjectId",
                max_record_count=1000,
                needs_geocode=True,
                geocode_context="Louisville, KY",
                field_map={'incident_id': ['incident_number'], 'offense_type': ['offense_code_name', 'offense_classification'], 'occurred_date': ['date_occurred'], 'reported_date': ['date_reported'], 'address': ['block_address']},
            ),
            # US-265: Louisville active construction permits (ArcGIS, native lat/long).
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_louisville_permits_url,
                platform="arcgis",
                watermark_col="ISSUE_DATE",
                id_keys=["PERMIT_NUMBER", "ObjectId"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=7,
                oid_field="ObjectId",
                max_record_count=1000,
                field_map={'job_id': ['PERMIT_NUMBER'], 'cost': ['PROJECT_COSTS', 'PERMIT_FEE'], 'latitude': ['LATITUDE'], 'longitude': ['LONGITUDE'], 'issued_date': ['ISSUE_DATE']},
            ),
            # US-265: Louisville ROW construction permits (ArcGIS, native lat/long).
            FeedType.STREET_CUT: DatasetSpec(
                endpoint=settings.arcgis_louisville_street_cut_url,
                platform="arcgis",
                watermark_col="FROM_DATE",
                id_keys=["PERMIT_NO", "ObjectId"],
                topic=settings.topic_street_cut,
                interval_seconds=300.0,
                producer_key="street_cut",
                expected_cadence_days=7,
                oid_field="ObjectId",
                max_record_count=1000,
                field_map={'job_id': ['PERMIT_NO'], 'latitude': ['LATITUDE'], 'longitude': ['LONGITUDE'], 'issued_date': ['FROM_DATE']},
            ),
        },
    ),
    CityId.PORTLAND: CityRegistration(
        city_id=CityId.PORTLAND,
        name="Portland / Multnomah County",
        state="OR",
        center={"lat": 45.5152, "lng": -122.6784},
        metro_bbox=PORTLAND_METRO_BBOX,
        division_bboxes=PORTLAND_DIVISION_BBOXES,
        submarkets=PORTLAND_SUBMARKETS,
        divisions=PORTLAND_DIVISIONS,
        job_suffix="portland",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_portland_permits_url,
                platform="arcgis",
                watermark_col="ISSUEDATE",
                id_keys=["FOLDERNUMB", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                order_by='ISSUEDATE DESC',
                field_map=PORTLAND_PERMITS_FIELD_MAP,
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_portland_olcc_applications_endpoint,
                platform="socrata",
                watermark_col="date_received",
                id_keys=["trade_name", "address"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                needs_geocode=True,
                field_map=PORTLAND_SLA_FIELD_MAP,
            ),
        },
    ),
    CityId.SAN_JOSE: CityRegistration(
        city_id=CityId.SAN_JOSE,
        name="San Jose / Santa Clara County",
        state="CA",
        center={"lat": 37.3382, "lng": -121.8863},
        metro_bbox=SAN_JOSE_METRO_BBOX,
        division_bboxes=SAN_JOSE_DIVISION_BBOXES,
        submarkets=SAN_JOSE_SUBMARKETS,
        divisions=SAN_JOSE_DIVISIONS,
        job_suffix="san_jose",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.ckan_san_jose_permits_endpoint,
                platform="ckan",
                watermark_col="ISSUEDATE",
                id_keys=["FOLDERNUMBER", "FOLDERRSN", "_id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=1,
                rolling_window_days=30,
                needs_geocode=True,
                geocode_context='San Jose, CA',
                watermark_type='text',
                watermark_format='%m/%d/%Y %I:%M:%S %p',
                field_map=SAN_JOSE_FIELD_MAP['permits'],
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.ckan_san_jose_311_endpoint,
                platform="ckan",
                watermark_col="Date Created",
                id_keys=["Incident_ID", "_id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                
                expected_cadence_days=1,
                annual_rotation=True,
                watermark_type='text',
                watermark_format='%m/%d/%Y %I:%M:%S %p',
                field_map=SAN_JOSE_FIELD_MAP['311'],
                endpoint_by_year={'2026': settings.ckan_san_jose_311_endpoint},
            ),
            # US-265: San Jose Police Calls for Service (CKAN). Address-only
            # (no coordinate column in any package resource), so needs_geocode
            # resolves coordinates via ADR-0004 at parse time.
            FeedType.CRIME: DatasetSpec(
                endpoint=settings.ckan_san_jose_crime_endpoint,
                platform="ckan",
                producer_key="crime",
                watermark_col="OFFENSE_DATE",
                id_keys=["EID", "CALL_NUMBER", "_id"],
                topic=settings.topic_crime,
                interval_seconds=300.0,
                expected_cadence_days=7,
                needs_geocode=True,
                geocode_context="San Jose, CA",
                field_map={
                    'incident_id': ['EID', 'CALL_NUMBER'],
                    'offense_type': ['CALL_TYPE'],
                    'occurred_date': ['OFFENSE_DATE', 'REPORT_DATE'],
                    'address': ['ADDRESS'],
                },
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("CA"),
        },
    ),
    CityId.TAMPA: CityRegistration(
        city_id=CityId.TAMPA,
        name="Tampa / Hillsborough County",
        state="FL",
        center={"lat": 27.9506, "lng": -82.4572},
        metro_bbox=TAMPA_METRO_BBOX,
        division_bboxes=TAMPA_DIVISION_BBOXES,
        submarkets=TAMPA_SUBMARKETS,
        divisions=TAMPA_DIVISIONS,
        job_suffix="tampa",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_tampa_permits_url,
                platform="arcgis",
                watermark_col="LASTUPDATE",
                id_keys=["RECORD_ID", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=1,
                oid_field='OBJECTID',
                max_record_count=2000,
                order_by='LASTUPDATE DESC',
                field_map=TAMPA_FIELD_MAP,
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_tampa_sla_url,
                platform="arcgis",
                watermark_col="HISTORY_ACT_DT",
                id_keys=["ORD_PERMIT", "APP_NUM", "OBJECTID"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                field_map=TAMPA_SLA_FIELD_MAP,
            ),
            # US-265: Tampa Police Calls for Service (ArcGIS; coords from geometry).
            FeedType.CRIME: DatasetSpec(
                endpoint=settings.arcgis_tampa_crime_url,
                platform="arcgis",
                watermark_col="occ_date",
                id_keys=["ESRI_OID", "report_number"],
                topic=settings.topic_crime,
                interval_seconds=300.0,
                producer_key="crime",
                expected_cadence_days=7,
                oid_field="ESRI_OID",
                max_record_count=1000,
                field_map={'incident_id': ['report_number'], 'offense_type': ['case_description'], 'occurred_date': ['occ_date']},
            ),
            # US-265: Tampa ROW permits (ArcGIS, native lat/long).
            FeedType.STREET_CUT: DatasetSpec(
                endpoint=settings.arcgis_tampa_street_cut_url,
                platform="arcgis",
                watermark_col="ISSUEDDATE",
                id_keys=["OBJECTID", "RECORDID"],
                topic=settings.topic_street_cut,
                interval_seconds=600.0,
                producer_key="street_cut",
                expected_cadence_days=7,
                oid_field="OBJECTID",
                max_record_count=1000,
                field_map={'job_id': ['RECORDID'], 'latitude': ['LATITUDE'], 'longitude': ['LONGITUDE'], 'issued_date': ['ISSUEDDATE']},
            ),
        },
    ),
    CityId.LAS_VEGAS: CityRegistration(
        city_id=CityId.LAS_VEGAS,
        name="Las Vegas / Clark County",
        state="NV",
        center={"lat": 36.1147, "lng": -115.1728},
        metro_bbox=LAS_VEGAS_METRO_BBOX,
        division_bboxes=LAS_VEGAS_DIVISION_BBOXES,
        submarkets=LAS_VEGAS_SUBMARKETS,
        divisions=LAS_VEGAS_DIVISIONS,
        job_suffix="las_vegas",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_las_vegas_permits_url,
                platform="arcgis",
                watermark_col="ISSDTTM",
                id_keys=["APNO", "APBLDGKEY", "ObjectId"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='ObjectId',
                max_record_count=1000,
                order_by='ISSDTTM DESC',
                needs_geocode=True,
                geocode_context='Las Vegas, NV',
                field_map=LAS_VEGAS_FIELD_MAP['permits'],
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_las_vegas_deeds_url,
                platform="arcgis",
                watermark_col="SALEDATE",
                id_keys=["PARCEL", "DOCNO", "ObjectId"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                
                expected_cadence_days=7,
                oid_field='ObjectId',
                max_record_count=2000,
                order_by='SALEDATE DESC',
                needs_geocode=True,
                geocode_context='Las Vegas, NV',
                field_map=LAS_VEGAS_FIELD_MAP['deeds'],
            ),
            # US-265: Las Vegas LVMPD Calls For Service (ArcGIS, native lat/long).
            FeedType.CRIME: DatasetSpec(
                endpoint=settings.arcgis_las_vegas_calls_for_service_url,
                platform="arcgis",
                oid_field="OBJECTID",
                max_record_count=1000,
                watermark_col="incidentdate",
                id_keys=["OBJECTID", "incidentnumber"],
                topic=settings.topic_crime,
                interval_seconds=300.0,
                producer_key="crime",
                expected_cadence_days=7,
                field_map={'incident_id': ['incidentnumber', 'OBJECTID'], 'offense_type': ['incidenttypedescription'], 'occurred_date': ['incidentdate'], 'latitude': ['latitude'], 'longitude': ['longitude'], 'address': ['location']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("NV"),
        },
    ),
    CityId.BOISE: CityRegistration(
        city_id=CityId.BOISE,
        name="Boise / Ada County",
        state="ID",
        center={"lat": 43.6131, "lng": -116.2110},
        metro_bbox=BOISE_METRO_BBOX,
        division_bboxes=BOISE_DIVISION_BBOXES,
        submarkets=BOISE_SUBMARKETS,
        divisions=BOISE_DIVISIONS,
        job_suffix="boise",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_boise_permits_url,
                platform="arcgis",
                watermark_col="IssuedDate",
                id_keys=["RecordID", "OBJECTID", "id"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=2000,
                order_by='IssuedDate DESC',
                field_map={'job_id': ['RecordID'], 'cost': ['JobValue'], 'issued_date': ['IssuedDate'], 'latitude': ['Y'], 'longitude': ['X']},
            ),
            # US-265: Boise BPD crimes (ArcGIS; coords from point geometry).
            FeedType.CRIME: DatasetSpec(
                endpoint=settings.arcgis_boise_crime_url,
                platform="arcgis",
                watermark_col="OccurredDateTime",
                id_keys=["OBJECTID", "DRNumber"],
                topic=settings.topic_crime,
                interval_seconds=300.0,
                producer_key="crime",
                expected_cadence_days=7,
                oid_field="OBJECTID",
                max_record_count=1000,
                order_by="OccurredDateTime DESC",
                field_map={'incident_id': ['OBJECTID', 'DRNumber'], 'offense_type': ['IncidentType', 'CrimeCodeDescription', 'CrimeType'], 'occurred_date': ['OccurredDateTime', 'ReportedDate'], 'borough': ['District', 'PatrolArea']},
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("ID"),
        },
    ),
    CityId.FORT_WORTH: CityRegistration(
        city_id=CityId.FORT_WORTH,
        name="Fort Worth / Tarrant County",
        state="TX",
        center={"lat": 32.7550, "lng": -97.3300},
        metro_bbox=FORT_WORTH_METRO_BBOX,
        division_bboxes=FORT_WORTH_DIVISION_BBOXES,
        submarkets=FORT_WORTH_SUBMARKETS,
        divisions=FORT_WORTH_DIVISIONS,
        job_suffix="fort_worth",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_fort_worth_permits_url,
                platform="arcgis",
                watermark_col="File_Date",
                id_keys=["Unique_ID", "Permit_No", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                
                expected_cadence_days=7,
                oid_field='OBJECTID',
                max_record_count=1000,
                order_by='File_Date DESC',
                needs_geocode=True,
                geocode_context='Fort Worth, TX',
                field_map=FORT_WORTH_PERMITS_FIELD_MAP,
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("TX"),
        },
    ),
    CityId.HONOLULU: CityRegistration(
        city_id=CityId.HONOLULU,
        name="Honolulu / City and County of Honolulu",
        state="HI",
        center={"lat": 21.3069, "lng": -157.8583},
        metro_bbox=HONOLULU_METRO_BBOX,
        division_bboxes=HONOLULU_DIVISION_BBOXES,
        submarkets=HONOLULU_SUBMARKETS,
        divisions=HONOLULU_DIVISIONS,
        job_suffix="honolulu",
        # Partial registration like Austin/LA, but PERMITS is withheld:
        # 4vab-c87q is a closed snapshot through 2025-06-30 (US-193 live
        # probe 2026-08-27). 311 only until a live permits successor exists.
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_honolulu_311_endpoint,
                platform="socrata",
                watermark_col="date_created",
                id_keys=["id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                expected_cadence_days=1,
                rolling_window_days=30,
                watermark_type="text",
                watermark_format="%B %d, %Y at %I:%M %p",
                order_by="id",
                needs_geocode=True,
                geocode_context="Honolulu, HI",
                field_map=HONOLULU_FIELD_MAP["311"],
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("HI"),
        },
    ),
    CityId.ORLANDO: CityRegistration(
        city_id=CityId.ORLANDO,
        name="Orlando / Orange County",
        state="FL",
        center={"lat": 28.5383, "lng": -81.3792},
        metro_bbox=ORLANDO_METRO_BBOX,
        division_bboxes=ORLANDO_DIVISION_BBOXES,
        submarkets=ORLANDO_SUBMARKETS,
        divisions=ORLANDO_DIVISIONS,
        job_suffix="orlando",
        # Partial SLA-only: Business Tax Receipts primary. STR licenses are
        # an SLA companion (Nashville/Phoenix STR precedent) — do not use
        # FeedType.STR. Scheduler does not poll companion_endpoints today,
        # so ingest is BTR-only until companion polling is grown.
        datasets={
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_orlando_sla_endpoint,
                platform="socrata",
                watermark_col="received_date",
                id_keys=["case_number"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                expected_cadence_days=1,
                order_by="received_date DESC",
                needs_geocode=True,
                geocode_context="Orlando, FL",
                companion_endpoints={
                    "str_licenses": settings.socrata_orlando_str_endpoint,
                },
                field_map=ORLANDO_SLA_FIELD_MAP,
            ),
        },
    ),
    CityId.GAINESVILLE: CityRegistration(
        city_id=CityId.GAINESVILLE,
        name="Gainesville",
        state="FL",
        center={"lat": 29.6516, "lng": -82.3248},
        metro_bbox=GAINESVILLE_METRO_BBOX,
        division_bboxes=GAINESVILLE_DIVISION_BBOXES,
        submarkets=GAINESVILLE_SUBMARKETS,
        divisions=GAINESVILLE_DIVISIONS,
        job_suffix="gainesville",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_gainesville_permits_endpoint,
                platform="socrata",
                watermark_col="issue",
                id_keys=["permit"],
                topic=settings.topic_permits,
                interval_seconds=600.0,
                producer_key="permits",
                order_by="issue DESC",
                expected_cadence_days=1,
                field_map=GAINESVILLE_PERMITS_FIELD_MAP,
            ),
            # US-364: SNAP retailers as the food-retail SLA slice (FL).
            # Municipal 311 is stale post-2021 and is not registered.
            FeedType.SLA: snap_sla_spec("FL"),
        },
    ),
    CityId.MIAMI_DADE: CityRegistration(
        city_id=CityId.MIAMI_DADE,
        name="Miami-Dade County",
        state="FL",
        center={"lat": 25.7617, "lng": -80.1918},
        metro_bbox=MIAMI_DADE_METRO_BBOX,
        division_bboxes=MIAMI_DADE_DIVISION_BBOXES,
        submarkets=MIAMI_DADE_SUBMARKETS,
        divisions=MIAMI_DADE_DIVISIONS,
        job_suffix="miami_dade",
        # Partial: PERMITS + SLA + DEEDS. 311 year-slices freeze at 2023;
        # 2024 is token-gated. Do not alias miami / broward / fort_lauderdale.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_miami_dade_permits_url,
                platform="arcgis",
                watermark_col="PermitIssuedDate",
                id_keys=["PermitNumber", "ProcessNumber", "ObjectId"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                needs_geocode=True,
                geocode_context="Miami-Dade County, FL",
                oid_field="ObjectId",
                max_record_count=1000,
                expected_cadence_days=1,
                non_spatial=True,
                rolling_window_days=730,
                field_map=MIAMI_DADE_FIELD_MAP["permits"],
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_miami_dade_sla_url,
                platform="arcgis",
                watermark_col="BUSSDATE",
                id_keys=["ACCOUNTNO", "RECEIPTNO", "OBJECTID"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                ingestion_mode="snapshot",
                oid_field="OBJECTID",
                max_record_count=16000,
                expected_cadence_days=30,
                companion_endpoints={
                    "certificate_of_use": settings.arcgis_miami_dade_sla_certificate_of_use_url,
                    "enterprise_twin": settings.arcgis_miami_dade_sla_enterprise_twin_url,
                },
                field_map=MIAMI_DADE_FIELD_MAP["sla"],
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_miami_dade_deeds_url,
                platform="arcgis",
                watermark_col="DOS_1",
                id_keys=["FOLIO", "OR_BK_1", "OR_PG_1", "OBJECTID"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                watermark_type="text",
                watermark_format="%Y%m%d",
                where="PRICE_1 >= 10000",
                oid_field="OBJECTID",
                max_record_count=20000,
                expected_cadence_days=7,
                field_map=MIAMI_DADE_FIELD_MAP["deeds"],
            ),
        },
    ),
    CityId.MEMPHIS: CityRegistration(
        city_id=CityId.MEMPHIS,
        name="Memphis / Shelby County",
        state="TN",
        center={"lat": 35.1495, "lng": -90.0490},
        metro_bbox=MEMPHIS_METRO_BBOX,
        division_bboxes=MEMPHIS_DIVISION_BBOXES,
        submarkets=MEMPHIS_SUBMARKETS,
        divisions=MEMPHIS_DIVISIONS,
        job_suffix="memphis",
        # Partial like Austin/LA: PERMITS + 311. SLA/deeds are Tier 3
        # (Accela / Register-of-Deeds UIs). Permits are a monthly dump
        # (expected_cadence_days=31; 0 August 2026 rows on a 27 Aug probe
        # is month-end, not a dead archive). OID is ObjectId not OBJECTID.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_memphis_permits_url,
                platform="arcgis",
                watermark_col="Issued_Date",
                id_keys=["Record_ID", "ObjectId"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=31,
                needs_geocode=True,
                geocode_context="Memphis, TN",
                oid_field="ObjectId",
                max_record_count=1000,
                order_by="Issued_Date DESC",
                field_map=MEMPHIS_FIELD_MAP["permits"],
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_memphis_311_url,
                platform="arcgis",
                watermark_col="REPORTED_DATE",
                id_keys=["INCIDENT_NUMBER", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                expected_cadence_days=1,
                needs_geocode=True,
                geocode_context="Memphis, TN",
                oid_field="OBJECTID",
                max_record_count=3000,
                order_by="REPORTED_DATE DESC",
                field_map=MEMPHIS_FIELD_MAP["311"],
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("TN"),
        },
    ),
    CityId.PHOENIX: CityRegistration(
        city_id=CityId.PHOENIX,
        name="Phoenix / Maricopa County",
        state="AZ",
        center={"lat": 33.4484, "lng": -112.0740},
        metro_bbox=PHOENIX_METRO_BBOX,
        division_bboxes=PHOENIX_DIVISION_BBOXES,
        submarkets=PHOENIX_SUBMARKETS,
        divisions=PHOENIX_DIVISIONS,
        job_suffix="phoenix",
        # Partial: Planning_Permit + ShapePHX STR-as-SLA. No 311 / deeds.
        # Do not use FeedType.STR. Companion _DL is metadata until the
        # scheduler grows companion polling.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_phoenix_permits_url,
                platform="arcgis",
                watermark_col="PER_ISSUE_DATE",
                id_keys=["PER_NUM", "PID", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=1,
                oid_field="OBJECTID",
                max_record_count=2000,
                order_by="PER_ISSUE_DATE DESC",
                needs_geocode=False,
                companion_endpoints={
                    "shapephx_issued": settings.arcgis_phoenix_shapephx_permits_url,
                },
                field_map=PHOENIX_FIELD_MAP["permits"],
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_phoenix_sla_url,
                platform="arcgis",
                watermark_col="ISSUED_DATE",
                id_keys=["NAME", "ID", "OBJECTID"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                expected_cadence_days=7,
                oid_field="OBJECTID",
                max_record_count=2000,
                order_by="ISSUED_DATE DESC",
                needs_geocode=False,
                field_map=PHOENIX_FIELD_MAP["sla"],
            ),
        },
    ),
    CityId.ALBUQUERQUE: CityRegistration(
        city_id=CityId.ALBUQUERQUE,
        name="Albuquerque / Bernalillo County",
        state="NM",
        center={"lat": 35.0844, "lng": -106.6504},
        metro_bbox=ALBUQUERQUE_METRO_BBOX,
        division_bboxes=ALBUQUERQUE_DIVISION_BBOXES,
        submarkets=ALBUQUERQUE_SUBMARKETS,
        divisions=ALBUQUERQUE_DIVISIONS,
        job_suffix="albuquerque",
        # Partial: PERMITS CSV only. AGIS City_Building_Permits is frozen;
        # 311 CRM is not anonymously queryable. CSVClient has no IN predicate
        # — where is NOT IN Expired.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.csv_albuquerque_permits_endpoint,
                platform="csv",
                watermark_col="IssueDate",
                id_keys=["ApplicationPermitNumber"],
                topic=settings.topic_permits,
                interval_seconds=1800.0,
                producer_key="permits",
                expected_cadence_days=1,
                watermark_type="text",
                watermark_format="%Y%m%d",
                watermark_exclude=["20261224"],
                where="Status NOT IN ('Expired')",
                needs_geocode=True,
                geocode_context="Albuquerque, NM",
                field_map=ALBUQUERQUE_FIELD_MAP["permits"],
            ),
            # US-364: USDA FNS SNAP retailers as the food-retail SLA slice.
            # State-level filter (v1 coarseness): rows outside the metro bbox
            # still carry global H3 tags; metro scoping stays downstream.
            FeedType.SLA: snap_sla_spec("NM"),
        },
    ),
    CityId.ST_LOUIS: CityRegistration(
        city_id=CityId.ST_LOUIS,
        name="St. Louis",
        state="MO",
        center={"lat": 38.6270, "lng": -90.1994},
        metro_bbox=ST_LOUIS_METRO_BBOX,
        division_bboxes=ST_LOUIS_DIVISION_BBOXES,
        submarkets=ST_LOUIS_SUBMARKETS,
        divisions=ST_LOUIS_DIVISIONS,
        job_suffix="stl",
        # Partial: 311 zip CSV + 30-day permits CSV + liquor SLA snapshot.
        # Deeds SaleDate lags ~6 months. Independent city only.
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.csv_st_louis_311_endpoint,
                platform="csv",
                watermark_col="datetimeinit",
                id_keys=["requestid"],
                topic=settings.topic_311,
                interval_seconds=1800.0,
                producer_key="311",
                expected_cadence_days=1,
                zip_member="2026.csv",
                endpoint_by_year={"2026": "2026.csv", "2027": "2027.csv"},
                geocode_context="St. Louis, MO",
                field_map=ST_LOUIS_FIELD_MAP["311"],
            ),
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.csv_st_louis_permits_endpoint,
                platform="csv",
                watermark_col="issuedate",
                id_keys=["address", "issuedate", "applicationdescription"],
                topic=settings.topic_permits,
                interval_seconds=1800.0,
                producer_key="permits",
                expected_cadence_days=21,
                rolling_window_days=30,
                needs_geocode=True,
                watermark_format="%B, %d %Y %H:%M:%S",
                geocode_context="St. Louis, MO",
                field_map=ST_LOUIS_FIELD_MAP["permits"],
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.csv_st_louis_sla_endpoint,
                platform="csv",
                watermark_col="date_expiration",
                id_keys=["case_number", "id"],
                topic=settings.topic_sla,
                interval_seconds=1800.0,
                producer_key="sla",
                expected_cadence_days=1,
                ingestion_mode="snapshot",
                needs_geocode=True,
                where="status_code = 'ACTIVE'",
                watermark_exclude=["1969-12-31", "3027-07-02"],
                geocode_context="St. Louis, MO",
                field_map=ST_LOUIS_FIELD_MAP["sla"],
            ),
        },
    ),
    CityId.AURORA: CityRegistration(
        city_id=CityId.AURORA,
        name="Aurora",
        state="CO",
        center={"lat": 39.7294, "lng": -104.8319},
        metro_bbox=AURORA_METRO_BBOX,
        division_bboxes=AURORA_DIVISION_BBOXES,
        submarkets=AURORA_SUBMARKETS,
        divisions=AURORA_DIVISIONS,
        job_suffix="aurora",
        # US-326: issued building permits (MapServer 44) + business/SLA
        # (MapServer 77 snapshot). Native outSR=4326 geometry primary;
        # EPSG:2232 State-Plane X/Y fallback. L156/L157 rolling views and
        # L34/L36/L4 companions are NOT registered as separate feeds.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_aurora_permits_url,
                platform="arcgis",
                watermark_col="IssueDate",
                id_keys=["Permit_", "FolderRSN", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=1,
                needs_geocode=False,
                oid_field="OBJECTID",
                max_record_count=2000,
                order_by="IssueDate DESC",
                state_plane_crs="EPSG:2232",
                state_plane_units="ftUS",
                state_plane_x_col="PropX",
                state_plane_y_col="PropY",
                field_map=AURORA_FIELD_MAP["permits"],
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_aurora_sla_url,
                platform="arcgis",
                watermark_col="Issue_Date",
                id_keys=["License_Number", "entity_key", "OBJECTID"],
                topic=settings.topic_sla,
                interval_seconds=300.0,
                producer_key="sla",
                expected_cadence_days=1,
                needs_geocode=False,
                ingestion_mode="snapshot",
                oid_field="OBJECTID",
                max_record_count=2000,
                order_by="Issue_Date DESC",
                state_plane_crs="EPSG:2232",
                state_plane_units="ftUS",
                state_plane_x_col="X",
                state_plane_y_col="Y",
                companion_endpoints={
                    "liquor": settings.arcgis_aurora_sla_liquor_url,
                    "all_businesses": settings.arcgis_aurora_sla_all_businesses_url,
                    "marijuana": settings.arcgis_aurora_sla_marijuana_url,
                },
                field_map=AURORA_FIELD_MAP["sla"],
            ),
        },
    ),
    CityId.HENDERSON: CityRegistration(
        city_id=CityId.HENDERSON,
        name="Henderson",
        state="NV",
        center={"lat": 36.0395, "lng": -115.0341},
        metro_bbox=HENDERSON_METRO_BBOX,
        division_bboxes=HENDERSON_DIVISION_BBOXES,
        submarkets=HENDERSON_SUBMARKETS,
        divisions=HENDERSON_DIVISIONS,
        job_suffix="henderson",
        # US-325: DSC_Permits (GISX/GISY WGS84 with address supplement) +
        # Active Licenses CSV snapshot (address-only -> ADR 0004 geocode).
        # MJBL county-wide companion filtered to Jurisdiction='HENDERSON'.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_henderson_permits_url,
                platform="arcgis",
                watermark_col="IssueDate",
                id_keys=["PermitNumber", "ObjectId"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=1,
                needs_geocode=True,
                geocode_context="Henderson, NV",
                oid_field="ObjectId",
                max_record_count=1000,
                order_by="IssueDate DESC",
                field_map=HENDERSON_FIELD_MAP["permits"],
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_henderson_sla_url,
                platform="csv",
                watermark_col="Original Issue Date",
                id_keys=["License Number"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                expected_cadence_days=1,
                watermark_type="text",
                watermark_format="%m/%d/%Y",
                ingestion_mode="snapshot",
                needs_geocode=True,
                geocode_context="Henderson, NV",
                companion_endpoints={
                    "mjbl": {
                        "endpoint": settings.arcgis_henderson_sla_mjbl_url,
                        "filter": "Jurisdiction='HENDERSON'",
                        "watermark_col": "IssueDate",
                        "watermark_type": "text",
                        "watermark_format": "%m-%d-%Y %H:%M",
                        "id_keys": ["MJBLNumber", "IsPrimary"],
                    },
                },
                field_map=HENDERSON_FIELD_MAP["sla"],
            ),
        },
    ),
    CityId.VIRGINIA_BEACH: CityRegistration(
        city_id=CityId.VIRGINIA_BEACH,
        name="Virginia Beach",
        state="VA",
        center=VIRGINIA_BEACH_CENTER,
        metro_bbox=VIRGINIA_BEACH_METRO_BBOX,
        division_bboxes=VIRGINIA_BEACH_DIVISION_BBOXES,
        submarkets=VIRGINIA_BEACH_SUBMARKETS,
        divisions=VIRGINIA_BEACH_DIVISIONS,
        job_suffix="vb",
        # US-354: permits (cadence 1d), SLA (annual-license trickle, 365d),
        # deeds (batched ~2-3wk publication, 14d — probe mid-Sept for stall).
        # All three are address-only Tables (non_spatial, ADR-0005 geocode);
        # GPIN is the T1 parcel-join path.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_virginia_beach_permits_url,
                platform="arcgis",
                watermark_col="IssueDate",
                id_keys=["PermitNumber", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=1,
                watermark_type="text",
                watermark_format="%Y/%m/%d",
                needs_geocode=True,
                geocode_context="Virginia Beach, VA",
                oid_field="OBJECTID",
                max_record_count=2000,
                non_spatial=True,
                field_map=VIRGINIA_BEACH_FIELD_MAP["permits"],
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_virginia_beach_sla_url,
                platform="arcgis",
                watermark_col="Begin_Date",
                id_keys=["Trade_Name", "Owner_Name", "Business_Address"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                expected_cadence_days=365,
                watermark_type="text",
                watermark_format="%m/%d/%Y",
                needs_geocode=True,
                geocode_context="Virginia Beach, VA",
                oid_field="OBJECTID",
                max_record_count=2000,
                non_spatial=True,
                field_map=VIRGINIA_BEACH_FIELD_MAP["sla"],
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_virginia_beach_deeds_url,
                platform="arcgis",
                watermark_col="Sales_Date",
                id_keys=["Document_Number", "GPIN", "Sales_Date"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                expected_cadence_days=14,
                needs_geocode=True,
                geocode_context="Virginia Beach, VA",
                oid_field="OBJECTID",
                max_record_count=2000,
                non_spatial=True,
                field_map=VIRGINIA_BEACH_FIELD_MAP["deeds"],
            ),
        },
    ),
    CityId.OMAHA: CityRegistration(
        city_id=CityId.OMAHA,
        name="Omaha",
        state="NE",
        center={"lat": 41.2580, "lng": -95.9370},
        metro_bbox=OMAHA_METRO_BBOX,
        division_bboxes=OMAHA_DIVISION_BBOXES,
        submarkets=OMAHA_SUBMARKETS,
        divisions=OMAHA_DIVISIONS,
        job_suffix="omaha",
        # US-358: partial — Mayor's Hotline 311 only (Tier 1, same-day).
        # Native outSR=4326 geometry; PROBADDRESS geocode supplement.
        # DATETIMEINIT is an esriFieldTypeDateOnly watermark. SLA is the
        # SNAP state slice (USDA FNS retailers, US-364) — closes the gate
        # that no registered metro is SLA-less.
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_omaha_311_url,
                platform="arcgis",
                watermark_col="DATETIMEINIT",
                id_keys=["OBJECTID", "REQUESTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                expected_cadence_days=1,
                needs_geocode=True,
                geocode_context="Omaha, NE",
                oid_field="OBJECTID",
                max_record_count=2000,
                order_by="DATETIMEINIT DESC",
                field_map=OMAHA_FIELD_MAP["311"],
            ),
            FeedType.SLA: snap_sla_spec("NE"),
        },
    ),
    CityId.TOLEDO: CityRegistration(
        city_id=CityId.TOLEDO,
        name="Toledo",
        state="OH",
        center={"lat": 41.6528, "lng": -83.5379},
        metro_bbox=TOLEDO_METRO_BBOX,
        division_bboxes=TOLEDO_DIVISION_BBOXES,
        submarkets=TOLEDO_SUBMARKETS,
        divisions=TOLEDO_DIVISIONS,
        job_suffix="toledo",
        # US-359: partial — Engage Toledo Cityworks 311 only (Tier 1, same-day).
        # Native outSR=4326 geometry primary; LOCATION geocode supplement.
        # X_COORD/Y_COORD are mixed-CRS and are deliberately not mapped.
        # SLA is the SNAP state slice (OH, already established for
        # Columbus/Cleveland/Dayton via US-364).
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_toledo_311_url,
                platform="arcgis",
                watermark_col="INIT_DATE",
                id_keys=["REQUEST_ID"],
                topic=settings.topic_311,
                interval_seconds=300.0,
                producer_key="311",
                expected_cadence_days=1,
                needs_geocode=True,
                geocode_context="Toledo, OH",
                oid_field="REQUEST_ID",
                max_record_count=2000,
                order_by="INIT_DATE DESC",
                field_map=TOLEDO_FIELD_MAP["311"],
            ),
            FeedType.SLA: snap_sla_spec("OH"),
        },
    ),
    CityId.AMARILLO: CityRegistration(
        city_id=CityId.AMARILLO,
        name="Amarillo",
        state="TX",
        center=AMARILLO_CENTER,
        metro_bbox=AMARILLO_METRO_BBOX,
        division_bboxes=AMARILLO_DIVISION_BBOXES,
        submarkets=AMARILLO_SUBMARKETS,
        divisions=AMARILLO_DIVISIONS,
        job_suffix="amarillo",
        # US-270: initial registration with SNAP SLA (TX slice). City permits
        # via data.texas.gov not verifiable; do not register until public API exists.
        datasets={
            FeedType.SLA: snap_sla_spec("TX"),
        },
    ),
    CityId.BEAUMONT: CityRegistration(
        city_id=CityId.BEAUMONT,
        name="Beaumont",
        state="TX",
        center={"lat": 30.0840, "lng": -94.1010},
        metro_bbox=BEAUMONT_METRO_BBOX,
        division_bboxes=BEAUMONT_DIVISION_BBOXES,
        submarkets=BEAUMONT_SUBMARKETS,
        divisions=BEAUMONT_DIVISIONS,
        job_suffix="beaumont",
        # US-271: no verifiable public building-permits or 311 feed. Register
        # SNAP retailers as the SLA slice for Texas (US-364 precedent).
        datasets={
            FeedType.SLA: snap_sla_spec("TX"),
        },
    ),
    CityId.WACO: CityRegistration(
        city_id=CityId.WACO,
        name="Waco",
        state="TX",
        center=WACO_CENTER,
        metro_bbox=WACO_METRO_BBOX,
        division_bboxes=WACO_DIVISION_BBOXES,
        submarkets=WACO_SUBMARKETS,
        divisions=WACO_DIVISIONS,
        job_suffix="waco",
        # US-272: initial registration with SNAP SLA (TX slice). A verifiable
        # public city permits feed via data.texas.gov was not found; register
        # SNAP-only and expand when a municipal permits API is proven.
        datasets={
            FeedType.SLA: snap_sla_spec("TX"),
        },
    ),
    CityId.JACKSON_MS: CityRegistration(
        city_id=CityId.JACKSON_MS,
        name="Jackson",
        state="MS",
        center=JACKSON_MS_CENTER,
        metro_bbox=JACKSON_MS_METRO_BBOX,
        division_bboxes=JACKSON_MS_DIVISION_BBOXES,
        submarkets=JACKSON_MS_SUBMARKETS,
        divisions=JACKSON_MS_DIVISIONS,
        job_suffix="jackson_ms",
        # US-288: initial registration with SNAP-only SLA (MS slice). No
        # verifiable public permits/311 feed on open.jacksonms.gov as of claim.
        # Do not fake endpoints; expand when a municipal API is proven.
        datasets={
            FeedType.SLA: snap_sla_spec("MS"),
        },
    ),
    CityId.OCALA: CityRegistration(
        city_id=CityId.OCALA,
        name="Ocala / Marion County",
        state="FL",
        center={"lat": 29.1872, "lng": -82.1401},
        metro_bbox=OCALA_METRO_BBOX,
        division_bboxes=OCALA_DIVISION_BBOXES,
        submarkets=OCALA_SUBMARKETS,
        divisions=OCALA_DIVISIONS,
        job_suffix="ocala",
        # US-297: initial registration with SNAP-only SLA (FL slice). A verifiable
        # public Marion County/Ocala permits layer was not found on the ArcGIS Hub.
        # Do not fake endpoints; prefer SNAP until a municipal API is proven.
        datasets={
            FeedType.SLA: snap_sla_spec("FL"),
        },
    ),
    CityId.MACON_BIBB: CityRegistration(
        city_id=CityId.MACON_BIBB,
        name="Macon-Bibb County",
        state="GA",
        center=MACON_BIBB_CENTER,
        metro_bbox=MACON_BIBB_METRO_BBOX,
        division_bboxes=MACON_BIBB_DIVISION_BBOXES,
        submarkets=MACON_BIBB_SUBMARKETS,
        divisions=MACON_BIBB_DIVISIONS,
        job_suffix="macon_bibb",
        # US-295: verified public permits (ArcGIS FeatureServer) plus SNAP GA slice.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_macon_bibb_permits_url,
                platform="arcgis",
                watermark_col="ISSUEDATE",
                id_keys=["OBJECTID0", "FOLDERYEAR", "FOLDERSEQUENCE"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",

                expected_cadence_days=7,
                oid_field="OBJECTID0",
                max_record_count=1000,
                field_map={
                    "job_id": ["OBJECTID0"],
                    "issuance_date": ["ISSUEDATE"],
                    "filing_date": ["INDATE"],
                    "address_street": ["PROPSTREET"],
                    "zipcode": ["PROPPOSTAL"],
                },
            ),
            FeedType.SLA: snap_sla_spec("GA"),
        },
    ),
    CityId.TYLER: CityRegistration(
        city_id=CityId.TYLER,
        name="Tyler",
        state="TX",
        center=TYLER_CENTER,
        metro_bbox=TYLER_METRO_BBOX,
        division_bboxes=TYLER_DIVISION_BBOXES,
        submarkets=TYLER_SUBMARKETS,
        divisions=TYLER_DIVISIONS,
        job_suffix="tyler",
        # US-273: initial registration with SNAP SLA (TX slice). City permits
        # via data.texas.gov require verification; register when public API confirmed.
        datasets={
            FeedType.SLA: snap_sla_spec("TX"),
        },
    ),
    CityId.AUGUSTA: CityRegistration(
        city_id=CityId.AUGUSTA,
        name="Augusta",
        state="GA",
        center=AUGUSTA_CENTER,
        metro_bbox=AUGUSTA_METRO_BBOX,
        division_bboxes=AUGUSTA_DIVISION_BBOXES,
        submarkets=AUGUSTA_SUBMARKETS,
        divisions=AUGUSTA_DIVISIONS,
        job_suffix="augusta",
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_augusta_permits_url,
                platform="arcgis",
                watermark_col="DATE_ISSUE",
                id_keys=["PERMITNUMBER", "PERM_NUM"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=7,
                needs_geocode=True,
                geocode_context="Augusta, GA",
                oid_field="OBJECTID",
                max_record_count=15000,
                field_map={
                    "job_id": ["PERMITNUMBER", "PERM_NUM"],
                    "address_street": ["JOBADDRESS"],
                    "issuance_date": ["DATE_ISSUE", "DATE_ENTERED"],
                    "filing_date": ["DATE_ENTERED"],
                    "cost": ["WORKCOST"],
                    "status": ["PERMIT_STATUS"],
                },
            ),
            FeedType.SLA: snap_sla_spec("GA"),
        },
    ),
    CityId.BUFFALO: CityRegistration(
        city_id=CityId.BUFFALO,
        name="Buffalo",
        state="NY",
        center={"lat": 42.8864, "lng": -78.8784},
        metro_bbox=BUFFALO_METRO_BBOX,
        division_bboxes=BUFFALO_DIVISION_BBOXES,
        submarkets=BUFFALO_SUBMARKETS,
        divisions=BUFFALO_DIVISIONS,
        job_suffix="buffalo",
        # US-349: partial — restaurant-license SLA only (Tier 1). Native
        # WGS84 latitude/longitude; gpsx/gpsy are mixed-CRS and never
        # candidates. Socrata NULLs-first ordering demands the where guard.
        datasets={
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_buffalo_sla_endpoint,
                platform="socrata",
                watermark_col="issdttm",
                id_keys=["uniqkey", "licenseno", "aplickey"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                expected_cadence_days=7,
                needs_geocode=False,
                where="issdttm IS NOT NULL",
                order_by="issdttm DESC",
                field_map=BUFFALO_SLA_FIELD_MAP,
            ),
        },
    ),
    CityId.ROCHESTER: CityRegistration(
        city_id=CityId.ROCHESTER,
        name="Rochester",
        state="NY",
        center=ROCHESTER_CENTER,
        metro_bbox=ROCHESTER_METRO_BBOX,
        division_bboxes=ROCHESTER_DIVISION_BBOXES,
        submarkets=ROCHESTER_SUBMARKETS,
        divisions=ROCHESTER_DIVISIONS,
        job_suffix="rochester",
        # US-351: partial — deeds/sales via the Monroe County RPS tax-parcel
        # layer (native parcel polygons). Monthly roll with lag (Jul rows
        # stop 07/22; Aug=0 at the 2026-08-28 re-probe — re-probe before
        # declaring stalled). $1 quitclaims kept at ingest. SLA is the SNAP
        # state slice (US-364).
        datasets={
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_rochester_deeds_url,
                platform="arcgis",
                watermark_col="SALE_DATE",
                id_keys=["PRINTKEY", "PARCELID", "SALE_DATE"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                expected_cadence_days=30,
                needs_geocode=False,
                watermark_type="text",
                watermark_format="%m/%d/%Y",
                oid_field="OBJECTID",
                max_record_count=100000,
                non_spatial=False,
                field_map=ROCHESTER_DEEDS_FIELD_MAP,
            ),
            FeedType.SLA: snap_sla_spec("NY"),
        },
    ),
    CityId.SYRACUSE: CityRegistration(
        city_id=CityId.SYRACUSE,
        name="Syracuse",
        state="NY",
        center={"lat": 43.0481, "lng": -76.1474},
        metro_bbox=SYRACUSE_METRO_BBOX,
        division_bboxes=SYRACUSE_DIVISION_BBOXES,
        submarkets=SYRACUSE_SUBMARKETS,
        divisions=SYRACUSE_DIVISIONS,
        job_suffix="syracuse",
        # US-352: partial — rental-registry SLA only (Tier 1, event-driven).
        # Native WGS84 Latitude/Longitude; PII dropped at the field map;
        # frozen Permit_Requests and absent 311/deeds are NOT registered.
        datasets={
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_syracuse_sla_url,
                platform="arcgis",
                watermark_col="RR_app_received",
                id_keys=["SBL"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                expected_cadence_days=1,
                needs_geocode=False,
                oid_field="ObjectId",
                max_record_count=1000,
                order_by="RR_app_received DESC",
                field_map=SYRACUSE_SLA_FIELD_MAP,
            ),
        },
    ),
    CityId.LYNCHBURG: CityRegistration(
        city_id=CityId.LYNCHBURG,
        name="Lynchburg",
        state="VA",
        center=LYNCHBURG_CENTER,
        metro_bbox=LYNCHBURG_METRO_BBOX,
        division_bboxes=LYNCHBURG_DIVISION_BBOXES,
        submarkets=LYNCHBURG_SUBMARKETS,
        divisions=LYNCHBURG_DIVISIONS,
        job_suffix="lynchburg",
        # US-318: full three-family — permits (37), SLA (33), deeds (34) on
        # one ODPDynamic MapServer. Deeds are an address-less transfer table:
        # coordinates arrive via the LRSN -> layer-41 parcel-centroid join
        # (DC precedent) with ADR-0004 as the lossless fallback. Layer 34
        # publishes no objectIdField — ESRI_OID ordering is mandatory.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_lynchburg_permits_url,
                platform="arcgis",
                watermark_col="StartDate",
                id_keys=["RecordNo", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=1,
                needs_geocode=True,
                geocode_context="Lynchburg, VA",
                order_by="OBJECTID",
                oid_field="OBJECTID",
                max_record_count=50000,
                non_spatial=True,
                field_map=LYNCHBURG_FIELD_MAP["permits"],
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_lynchburg_sla_url,
                platform="arcgis",
                watermark_col="LicenseIssued",
                id_keys=["LicenseNumber", "OBJECTID"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                expected_cadence_days=365,
                needs_geocode=True,
                geocode_context="Lynchburg, VA",
                order_by="OBJECTID",
                oid_field="OBJECTID",
                max_record_count=50000,
                non_spatial=True,
                field_map=LYNCHBURG_FIELD_MAP["sla"],
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_lynchburg_deeds_url,
                platform="arcgis",
                watermark_col="SaleDate",
                id_keys=["LRSN", "DocumentNo"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                expected_cadence_days=1,
                needs_geocode=True,
                geocode_context="Lynchburg, VA",
                order_by="ESRI_OID",
                oid_field="ESRI_OID",
                max_record_count=50000,
                non_spatial=True,
                parcel_join={
                    "parcel_layer": settings.arcgis_lynchburg_parcel_layer_url,
                    "join_key": "LRSN",
                    "geometry_source": "centroid",
                },
                field_map=LYNCHBURG_FIELD_MAP["deeds"],
            ),
        },
    ),
    CityId.GREENVILLE: CityRegistration(
        city_id=CityId.GREENVILLE,
        name="Greenville",
        state="SC",
        center={"lat": 34.8497, "lng": -82.3992},
        metro_bbox=GREENVILLE_METRO_BBOX,
        division_bboxes=GREENVILLE_DIVISION_BBOXES,
        submarkets=GREENVILLE_SUBMARKETS,
        divisions=GREENVILLE_DIVISIONS,
        job_suffix="greenville",
        # US-340: partial — building permits only (Tier 1, rolling two-year
        # window; NewIssueDate is not where-queryable and time= is ignored).
        # SLA is the SNAP state slice (US-364).
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_greenville_permits_url,
                platform="arcgis",
                watermark_col="NewIssueDate",
                id_keys=["PERMIT_NUM"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=1,
                needs_geocode=True,
                geocode_context="Greenville, SC",
                oid_field="OBJECTID",
                max_record_count=7000,
                order_by="NewIssueDate DESC",
                field_map=GREENVILLE_FIELD_MAP["permits"],
            ),
            FeedType.SLA: snap_sla_spec("SC"),
        },
    ),
    CityId.ANCHORAGE: CityRegistration(
        city_id=CityId.ANCHORAGE,
        name="Anchorage",
        state="AK",
        center=ANCHORAGE_CENTER,
        metro_bbox=ANCHORAGE_METRO_BBOX,
        division_bboxes=ANCHORAGE_DIVISION_BBOXES,
        submarkets=ANCHORAGE_SUBMARKETS,
        divisions=ANCHORAGE_DIVISIONS,
        job_suffix="anchorage",
        # US-330: partial — assessor property-information deeds (daily batch
        # republication; recordings land business days, so Fri->Mon is a
        # normal 3-day watermark gap — alarm fires only when the daily batch
        # stalls past a full weekend + Monday). Future-dated Deed_Date
        # sentinels excluded at the source. SLA is the SNAP state slice
        # (US-364). Deed_Date/PUBDATE epochs are stamped noon UTC, not AKST.
        datasets={
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_anchorage_deeds_url,
                platform="arcgis",
                watermark_col="Deed_Date",
                id_keys=["Parcel_ID", "GIS_ParcelNum11", "OBJECTID"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                expected_cadence_days=3,
                needs_geocode=False,
                where="Deed_Date <= CURRENT_TIMESTAMP",
                order_by="Deed_Date DESC",
                oid_field="OBJECTID",
                max_record_count=2000,
                non_spatial=False,
                field_map=ANCHORAGE_DEEDS_FIELD_MAP,
            ),
            FeedType.SLA: snap_sla_spec("AK"),
        },
    ),
    CityId.TUCSON: CityRegistration(
        city_id=CityId.TUCSON,
        name="Tucson",
        state="AZ",
        center={"lat": 32.2226, "lng": -110.9723},
        metro_bbox=TUCSON_METRO_BBOX,
        division_bboxes=TUCSON_DIVISION_BBOXES,
        submarkets=TUCSON_SUBMARKETS,
        divisions=TUCSON_DIVISIONS,
        job_suffix="tucson",
        # US-328: partial — economic-development SLA snapshot. Future-dated
        # DT_START application sentinels are excluded at the source (static
        # watermark_exclude cannot pin rolling sentinels). ANSI-date host
        # (gis.tucsonaz.gov in ANSI_DATE_LITERAL_HOSTS). Store SR WKID 2868
        # AZ-East feet — coords only via outSR=4326 geometry lift.
        datasets={
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_tucson_sla_url,
                platform="arcgis",
                watermark_col="DT_START",
                id_keys=["ACC_NUM", "LIC_TYPE", "OBJECTID"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                expected_cadence_days=30,
                alarm_exempt=True,
                alarm_exempt_reason=(
                    "slow/annual effective cadence: newest non-future DT_START "
                    "rows land ~2 per 60d (layer IS maintained - future-dated "
                    "applications present); DT_START<=CURRENT_TIMESTAMP where "
                    "guard excludes future sentinels; alarm would false-positive "
                    "on the slow issuance pace"
                ),
                ingestion_mode="snapshot",
                needs_geocode=True,
                geocode_context="Tucson, AZ",
                where="DT_START <= CURRENT_TIMESTAMP",
                order_by="DT_START DESC",
                oid_field="OBJECTID",
                max_record_count=2000,
                field_map=TUCSON_SLA_FIELD_MAP,
            ),
        },
    ),
}


def resolve_endpoint(spec: DatasetSpec, today: Optional[Any] = None) -> str:
    """Resolve a spec's endpoint for "today", honoring year-sliced datasets.

    Some jurisdictions publish one layer/resource per calendar year
    (`endpoint_by_year={"2026": "...FeatureServer/18", ...}`).
    Returns the current year's entry when present, else the newest year not
    in the future, else the lexicographically latest entry. Annual rollover
    drill: see docs/expansion-roadmap.md §8.2.
    """
    by_year = spec.endpoint_by_year
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


def resolve_zip_member(spec: DatasetSpec, today: Optional[Any] = None) -> Optional[str]:
    """Resolve a zip-member filename for today without replacing the zip URL.

    St. Louis CSB publishes ``csb.zip`` with year files inside
    (``2026.csv``, …). ``endpoint_by_year`` maps year → member name; the
    HTTP endpoint stays the zip. ``resolve_endpoint`` must not be used on
    those specs — it would return ``2026.csv`` as a URL.
    """
    if not spec.zip_member:
        return None
    by_year = spec.endpoint_by_year
    if not by_year:
        return spec.zip_member
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


USE_DERIVED_REGISTRY = True

if USE_DERIVED_REGISTRY:
    from src.spatial import registry_derivation

    _RUNTIME_EXPORTS = registry_derivation.build_runtime_exports()
    if _RUNTIME_EXPORTS is None:
        REGISTRY = registry_derivation.build_registry_from_registrations()
        ALIASES = registry_derivation.build_aliases_from_registrations()
    else:
        REGISTRY, ALIASES = _RUNTIME_EXPORTS
