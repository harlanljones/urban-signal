"""City and Dataset Registry for Urban Signal.

Provides a unified, centralized registry for all supported metropolitan regions,
geographic boundaries, submarkets, division catalogs, and municipal dataset endpoints.
"""

from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from src.config import settings
from src.spatial.submarkets import (
    BoroughMeta,
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
    MADISON = "madison"
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
    PEORIA = "peoria"
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
    SAVANNAH = "savannah"
    BOWLING_GREEN = "bowling_green"
    TALLAHASSEE = "tallahassee"
    SPARTANBURG = "spartanburg"
    ABILENE = "abilene"
    ALEXANDRIA = "alexandria"
    ASHEVILLE = "asheville"
    CAPE_CORAL = "cape_coral"
    CHARLESTON_SC = "charleston_sc"
    FORT_SMITH = "fort_smith"
    JONESBORO = "jonesboro"
    LAKE_CHARLES = "lake_charles"
    LAKELAND = "lakeland"
    LAREDO = "laredo"
    LEXINGTON = "lexington"
    LONGVIEW = "longview"
    MIDLAND = "midland"
    MONROE = "monroe"
    ODESSA = "odessa"
    PORT_ST_LUCIE = "port_st_lucie"
    TEXARKANA = "texarkana"
    WILMINGTON_NC = "wilmington_nc"
    GRAND_RAPIDS = "grand_rapids"
    INLAND_EMPIRE = "inland_empire"
    STOCKTON = "stockton"
    BOULDER = "boulder"
    CHANDLER = "chandler"
    MODESTO = "modesto"
    BEND = "bend"
    VANCOUVER_WA = "vancouver_wa"
    ANAHEIM = "anaheim"
    SANTA_ROSA = "santa_rosa"
    OAKLAND = "oakland"
    NAMPA = "nampa"
    YAKIMA = "yakima"
    OXNARD_VENTURA = "oxnard_ventura"
    MEDFORD = "medford"
    TEMPE = "tempe"
    BOZEMAN = "bozeman"
    MISSOULA = "missoula"
    SANTA_FE = "santa_fe"
    EUGENE = "eugene"
    GLENDALE_AZ = "glendale_az"
    SCOTTSDALE = "scottsdale"
    LONG_BEACH = "long_beach"
    LAS_CRUCES = "las_cruces"
    BILLINGS = "billings"
    SALEM_OR = "salem_or"
    TACOMA = "tacoma"
    SIOUX_FALLS = "sioux_falls"
    LINCOLN = "lincoln"
    TOPEKA = "topeka"
    WORCESTER = "worcester"
    NEW_HAVEN = "new_haven"
    BRIDGEPORT = "bridgeport"
    CANTON = "canton"
    EVANSVILLE = "evansville"
    HUNTSVILLE = "huntsville"
    MONTGOMERY_AL = "montgomery_al"


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
    VIOLATIONS = "violations"
    INSPECTIONS = "inspections"
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
        where_clause: str | None = None,
        order_by: str = ":id",
        batch_size: int = 1000,
        max_records: int | None = None,
    ) -> Generator[list[dict[str, Any]], None, None]:
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
    id_keys: list[str] = field(default_factory=list)
    topic: str = ""
    interval_seconds: float = 300.0
    producer_key: str = ""
    # --- typed acquisition keys (formerly ``extra``) ---
    endpoint_by_year: dict[str, str] = field(default_factory=dict)
    watermark_type: str | None = None
    watermark_format: str | None = None
    watermark_exclude: list[str] = field(default_factory=list)
    order_by: str | None = None
    id_col: str | None = None
    select: str | None = None
    fallback_endpoints: list[str] = field(default_factory=list)
    where: str | None = None
    needs_geocode: bool = False
    geocode_context: str | None = None
    field_map: dict[str, Any] = field(default_factory=dict)
    ingestion_mode: str = "incremental"
    oid_field: str | None = None
    max_record_count: int | None = None
    expected_cadence_days: int | None = None
    alarm_exempt: bool = False
    alarm_exempt_reason: str | None = None
    annual_rotation: bool = False
    companion_endpoints: dict[str, Any] = field(default_factory=dict)
    proxy_for: str | None = None
    retention_days: int | None = None
    rolling_window_days: int | None = None
    rollover: str | None = None
    state_plane_crs: str | None = None
    state_plane_units: str | None = None
    state_plane_x_col: str | None = None
    state_plane_y_col: str | None = None
    parcel_join: dict[str, Any] = field(default_factory=dict)
    non_spatial: bool | None = None
    zip_member: str | None = None
    # CSV feeds are not always comma-delimited (Maricopa sales affidavits are
    # pipe-delimited). Forwarded verbatim to CSVClient.paginate (US-392).
    delimiter: str | None = None


@dataclass
class CityRegistration:
    """Complete registration metadata for a supported metropolitan area."""
    city_id: CityId
    name: str
    state: str
    center: dict[str, float]
    metro_bbox: dict[str, float]
    division_bboxes: dict[str, dict[str, float]]
    submarkets: dict[str, SubmarketMeta]
    divisions: dict[str, BoroughMeta]
    datasets: dict[FeedType, DatasetSpec]
    job_suffix: str = ""


# Canonical alias lookup mapping all known alias strings to CityId
def normalize_city(city_id: str | None) -> CityId | None:
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


def resolve_endpoint(spec: DatasetSpec, today: Any | None = None) -> str:
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
        today = datetime.now(UTC).date()
    year = getattr(today, "year", None)
    if year is None:
        year = int(str(today)[:4])
    for candidate in range(year, -1, -1):
        key = str(candidate)
        if key in by_year:
            return by_year[key]
    return by_year[max(by_year)]


def resolve_zip_member(spec: DatasetSpec, today: Any | None = None) -> str | None:
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
        today = datetime.now(UTC).date()
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


from src.spatial import registry_derivation as _registry_derivation

REGISTRY, ALIASES = _registry_derivation.build_runtime_exports()
__all__ = [
    "ALIASES",
    "REGISTRY",
    "CityId",
    "CityRegistration",
    "DatasetSpec",
    "FeedType",
    "get_dataset",
    "get_job_name",
    "normalize_city",
    "resolve_endpoint",
    "resolve_zip_member",
]
