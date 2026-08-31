PERMITS_FIELD_MAP = {
    "job_id": ["PermitNumber", "ObjectId"],
    "issuance_date": ["IssueDate"],
    "filing_date": ["ApplyDate"],
    "status": ["PermitStatus"],
    "job_type": ["PermitType", "WorkClass", "Category"],
    "cost": ["ValuationTotal"],
    "address_street": [
        "ParcelAddressNumber",
        "ParcelAddressPreDirection",
        "ParcelAddressStreet",
        "ParcelAddressStreetType",
    ],
    "bbl": ["ParcelNumber"],
    "zipcode": ["ParcelAddressZip"],
    "latitude": ["GISY"],
    "longitude": ["GISX"],
}

SLA_FIELD_MAP = {
    "license_id": ["License Number"],
    "dba": ["DBA", "Entity Name"],
    "premises_name": ["Entity Name"],
    "license_type": ["License Type", "License Sub-Type"],
    "effective_date": ["Original Issue Date"],
    "expiration_date": ["Expiration Date"],
    "address_street": ["Business Location"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT = "Henderson, NV"

DROPPED_PII_COLUMNS = (
    "OwnerName",
    "OwnerAddress",
    "ProfessionalName",
    "ProfessionalStateLicNbr",
    "ProfessionalAddress",
    "ProfessionalPhone",
    "Business Phone",
)

"""Henderson, NV spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Henderson
(southeast Las Vegas Valley, Clark County, NV).

Henderson is a TWO-FEED PARTIAL metro like Memphis: PERMITS
(``DSC_Permits`` on the city's AGOL org, Tier 1) and SLA (Active Business
Licenses CSV, Tier 2, address-only). COMPLAINTS_311 and DEEDS are Tier 3
(no Hub dataset; Clark County recording has no anonymous bulk API) and stay
unregistered.

Live-probe caveats that define this leaf (re-probed 2026-08-28, US-325;
original probe 2026-08-27):

* PERMITS is **daily**: newest ``IssueDate`` on the re-probe was
  2026-08-28 (single row; the 2026-08-20 batch landed 106 rows, then one
  probe-day row per day). Native ``GISX``/``GISY`` attributes are **WGS84
  geographic degrees** — verified live (values ≈ -115.09…-114.91 /
  35.93…36.09), NOT State Plane feet and NOT Web Mercator meters; no
  transform is applied. Null on ~11.8% of rows → composed parcel-address
  geocode supplement (ADR 0004) via ``compose_permit_address``. The layer's
  free-text ``LocationDescription`` is NOT an address and is never mapped.
  Companion full-history CSV (item ``53e66cc9…``) is the bulk backfill:
  ``IssueDate`` as ``MM-DD-YYYY HH:MM`` text with future-dated rows
  (≥ probe day) excluded as sentinels (Albuquerque discipline).
* SLA is a **snapshot CSV** (item ``2b3fac57…``, 12,851 rows, all
  ``Primary Jurisdiction = City of Henderson``): watermark ``Original Issue
  Date`` (``M/D/YYYY`` text; newest 2026-08-21 on the re-probe, 60d = 391 —
  the small-city 7d ≈ 2 is normal). Address-only (``Business Location`` +
  City/State/Zip) → ``needs_geocode=True``, ``geocode_context="Henderson,
  NV"``. The MJBL county-wide companion (item ``6c470a95…``) MUST be
  filtered to ``Jurisdiction='HENDERSON'`` before ingestion. The
  ``Business Licenses`` MapServer (``public/OpenDataGovernment``, mod 2022)
  is a frozen row-twin — do not register it.
"""

from typing import Any

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

HENDERSON_CITY_ID: str = "henderson"
HENDERSON_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Henderson (southeast Las Vegas Valley). Permissive enough to hold
# the Water Street District core (36.0395, -114.9797), the Green Valley /
# GVR belt, the Anthem/Seven Hills foothills, Lake Las Vegas, and the far
# southwest growth edge (live permit sample at 35.9328, -115.0866).
HENDERSON_METRO_BBOX: dict[str, float] = {
    "min_lat": 35.90,
    "max_lat": 36.10,
    "min_lng": -115.15,
    "max_lng": -114.82,
}

# 6 Henderson divisions. Hand-authored; borough resolution at ingest
# comes from coordinates via get_division_for_coordinate, so bboxes need only
# be sane and contain their own submarket centers.
HENDERSON_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_WATER_STREET": {
        "min_lat": 36.030,
        "max_lat": 36.055,
        "min_lng": -115.000,
        "max_lng": -114.965,
    },
    "GREEN_VALLEY_WEST": {
        "min_lat": 35.998,
        "max_lat": 36.035,
        "min_lng": -115.055,
        "max_lng": -115.002,
    },
    "GREEN_VALLEY_RANCH": {
        "min_lat": 36.005,
        "max_lat": 36.030,
        "min_lng": -115.000,
        "max_lng": -114.975,
    },
    "FOOTHILLS_SOUTH": {
        "min_lat": 35.960,
        "max_lat": 36.020,
        "min_lng": -115.010,
        "max_lng": -114.920,
    },
    "LAKE_LAS_VEGAS": {
        "min_lat": 36.015,
        "max_lat": 36.038,
        "min_lng": -114.940,
        "max_lng": -114.900,
    },
    "WEST_INNOVATION": {
        "min_lat": 35.975,
        "max_lat": 35.997,
        "min_lng": -115.060,
        "max_lng": -115.010,
    },
}


def is_in_henderson_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Henderson city bounds."""
    if lat is None or lng is None:
        return False
    return (
        HENDERSON_METRO_BBOX["min_lat"] <= lat <= HENDERSON_METRO_BBOX["max_lat"]
        and HENDERSON_METRO_BBOX["min_lng"] <= lng <= HENDERSON_METRO_BBOX["max_lng"]
    )


is_in_greater_henderson_metro = is_in_henderson_metro


def compose_permit_address(row: dict[str, Any]) -> str | None:
    """Join DSC_Permits parcel address parts into one geocode query.

    Probe form: ``{ParcelAddressNumber} {ParcelAddressPreDirection}
    {ParcelAddressStreet} {ParcelAddressStreetType}, Henderson, NV
    {ParcelAddressZip}``. Returns ``None`` when no street parts exist, so
    the geocode supplement is skipped rather than queried on noise.
    """

    def _first(*keys: str) -> str:
        for key in keys:
            val = row.get(key)
            if val is not None and str(val).strip():
                return str(val).strip()
        return ""

    street = " ".join(
        part
        for part in (
            _first("ParcelAddressNumber"),
            _first("ParcelAddressPreDirection"),
            _first("ParcelAddressStreet"),
            _first("ParcelAddressStreetType"),
        )
        if part
    )
    zipcode = _first("ParcelAddressZip")
    if street and zipcode:
        return f"{street}, Henderson, NV {zipcode}"
    if street:
        return f"{street}, Henderson, NV"
    return None


HENDERSON_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_WATER_STREET (1)
    # =======================================================================
    "Water Street District": SubmarketMeta(
        name="Water Street District",
        borough="DOWNTOWN_WATER_STREET",
        lat=36.0403,
        lng=-114.9815,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.84,
        capex=7600000.0,
        permit_vel=36.0,
        shift_ratio=1.48,
        sla=60.0,
        description="City core along Water Street with the civic center, facade-renewal infill, and the downtown redevelopment corridor's mixed-use permitting.",
        city_id="henderson",
    ),
    # =======================================================================
    # GREEN_VALLEY_WEST (1)
    # =======================================================================
    "Green Valley": SubmarketMeta(
        name="Green Valley",
        borough="GREEN_VALLEY_WEST",
        lat=36.0125,
        lng=-115.0340,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.87,
        capex=8800000.0,
        permit_vel=40.0,
        shift_ratio=1.52,
        sla=62.0,
        description="Master-planned 1970s-90s valley west of Green Valley Parkway with pool-home renovation, kitchen/bath alterations, and steady resale turnover.",
        city_id="henderson",
    ),
    # =======================================================================
    # GREEN_VALLEY_RANCH (1)
    # =======================================================================
    "Green Valley Ranch": SubmarketMeta(
        name="Green Valley Ranch",
        borough="GREEN_VALLEY_RANCH",
        lat=36.0185,
        lng=-114.9900,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.88,
        capex=9100000.0,
        permit_vel=42.0,
        shift_ratio=1.54,
        sla=63.0,
        description="GVR master plan around The District and the resort corridor with village retail, townhome infill, and the metro's highest lease pressure.",
        city_id="henderson",
    ),
    # =======================================================================
    # FOOTHILLS_SOUTH (3)
    # =======================================================================
    "Anthem": SubmarketMeta(
        name="Anthem",
        borough="FOOTHILLS_SOUTH",
        lat=36.0010,
        lng=-114.9330,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.90,
        capex=10200000.0,
        permit_vel=38.0,
        shift_ratio=1.56,
        sla=65.0,
        description="Gated foothills country-club belt below the Black Mountains with luxury custom-lot builds and the metro's top valuation band.",
        city_id="henderson",
    ),
    "Seven Hills": SubmarketMeta(
        name="Seven Hills",
        borough="FOOTHILLS_SOUTH",
        lat=36.0050,
        lng=-114.9740,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.89,
        capex=9600000.0,
        permit_vel=37.0,
        shift_ratio=1.55,
        sla=64.0,
        description="Hillside village plan south of the 215 with view-lot estate renovation and clubhouse-adjacent retail on Seven Hills Drive.",
        city_id="henderson",
    ),
    "MacDonald Ranch": SubmarketMeta(
        name="MacDonald Ranch",
        borough="FOOTHILLS_SOUTH",
        lat=36.0160,
        lng=-114.9410,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.89,
        capex=9400000.0,
        permit_vel=35.0,
        shift_ratio=1.53,
        sla=63.0,
        description="MacDonald Highlands and the Ranch corridor with guard-gated custom estates, hillside grading permits, and golf-course frontage stock.",
        city_id="henderson",
    ),
    # =======================================================================
    # LAKE_LAS_VEGAS (1)
    # =======================================================================
    "Lake Las Vegas": SubmarketMeta(
        name="Lake Las Vegas",
        borough="LAKE_LAS_VEGAS",
        lat=36.0235,
        lng=-114.9185,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.83,
        capex=8200000.0,
        permit_vel=30.0,
        shift_ratio=1.47,
        sla=58.0,
        description="Resort lake enclave around MonteLago Village with villa and condo product, hospitality-led permitting, and short-stay sensitive demand.",
        city_id="henderson",
    ),
    # =======================================================================
    # WEST_INNOVATION (1)
    # =======================================================================
    "Innovation District": SubmarketMeta(
        name="Innovation District",
        borough="WEST_INNOVATION",
        lat=35.9920,
        lng=-115.0200,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.80,
        capex=6900000.0,
        permit_vel=34.0,
        shift_ratio=1.44,
        sla=55.0,
        description="West Henderson's designated innovation corridor (Union Village / MedCity adjacency) with industrial-to-civic conversion and anchor-institution expansion.",
        city_id="henderson",
    ),
}


HENDERSON_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_WATER_STREET": BoroughMeta(
        name="DOWNTOWN_WATER_STREET",
        center_lat=36.0403,
        center_lng=-114.9815,
        zoom=14.0,
        bbox=HENDERSON_DIVISION_BBOXES["DOWNTOWN_WATER_STREET"],
        submarkets=[k for k, v in HENDERSON_SUBMARKETS.items() if v.borough == "DOWNTOWN_WATER_STREET"],
        city_id="henderson",
    ),
    "GREEN_VALLEY_WEST": BoroughMeta(
        name="GREEN_VALLEY_WEST",
        center_lat=36.0125,
        center_lng=-115.0340,
        zoom=13.5,
        bbox=HENDERSON_DIVISION_BBOXES["GREEN_VALLEY_WEST"],
        submarkets=[k for k, v in HENDERSON_SUBMARKETS.items() if v.borough == "GREEN_VALLEY_WEST"],
        city_id="henderson",
    ),
    "GREEN_VALLEY_RANCH": BoroughMeta(
        name="GREEN_VALLEY_RANCH",
        center_lat=36.0185,
        center_lng=-114.9900,
        zoom=13.5,
        bbox=HENDERSON_DIVISION_BBOXES["GREEN_VALLEY_RANCH"],
        submarkets=[k for k, v in HENDERSON_SUBMARKETS.items() if v.borough == "GREEN_VALLEY_RANCH"],
        city_id="henderson",
    ),
    "FOOTHILLS_SOUTH": BoroughMeta(
        name="FOOTHILLS_SOUTH",
        center_lat=36.0050,
        center_lng=-114.9480,
        zoom=12.5,
        bbox=HENDERSON_DIVISION_BBOXES["FOOTHILLS_SOUTH"],
        submarkets=[k for k, v in HENDERSON_SUBMARKETS.items() if v.borough == "FOOTHILLS_SOUTH"],
        city_id="henderson",
    ),
    "LAKE_LAS_VEGAS": BoroughMeta(
        name="LAKE_LAS_VEGAS",
        center_lat=36.0235,
        center_lng=-114.9185,
        zoom=13.0,
        bbox=HENDERSON_DIVISION_BBOXES["LAKE_LAS_VEGAS"],
        submarkets=[k for k, v in HENDERSON_SUBMARKETS.items() if v.borough == "LAKE_LAS_VEGAS"],
        city_id="henderson",
    ),
    "WEST_INNOVATION": BoroughMeta(
        name="WEST_INNOVATION",
        center_lat=35.9920,
        center_lng=-115.0200,
        zoom=13.0,
        bbox=HENDERSON_DIVISION_BBOXES["WEST_INNOVATION"],
        submarkets=[k for k, v in HENDERSON_SUBMARKETS.items() if v.borough == "WEST_INNOVATION"],
        city_id="henderson",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27, re-probed 2026-08-28. Do not register 311, deeds, the
# frozen Business Licenses MapServer, or sibling Hub views.
# ---------------------------------------------------------------------------
HENDERSON_PERMITS_ENDPOINT = (
    "https://services2.arcgis.com/naGsY5NZWVbd6bwD/arcgis/rest/services/"
    "DSC_Permits/FeatureServer/0"
)
HENDERSON_SLA_ENDPOINT = (
    "https://www.arcgis.com/sharing/rest/content/items/"
    "2b3fac57210542229afc4bfddd6cd6e8/data"
)
# MJBL county-wide companion — filter Jurisdiction='HENDERSON' at ingestion.
HENDERSON_SLA_MJBL_ENDPOINT = (
    "https://www.arcgis.com/sharing/rest/content/items/"
    "6c470a95e83e4051a4d1222afa056ed6/data"
)

HENDERSON_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": HENDERSON_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "IssueDate",
        "id_keys": ["PermitNumber", "ObjectId"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": HENDERSON_GEOCODE_CONTEXT,
            "oid_field": "ObjectId",
            "max_record_count": 1000,
            "order_by": "IssueDate DESC",
            "scope": (
                "DSC_Permits issued permits (native WGS84 GISX/GISY degrees "
                "with composed parcel-address geocode supplement; ~11.8% "
                "coordinate nulls; filter to issued statuses at analytics)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": HENDERSON_SLA_ENDPOINT,
        "platform": "csv",
        "watermark_col": "Original Issue Date",
        "id_keys": ["License Number"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 1,
            "watermark_type": "text",
            "watermark_format": "%m/%d/%Y",
            "ingestion_mode": "snapshot",
            "needs_geocode": True,
            "geocode_context": HENDERSON_GEOCODE_CONTEXT,
            "companion_endpoints": {
                "mjbl": {
                    "endpoint": HENDERSON_SLA_MJBL_ENDPOINT,
                    "filter": "Jurisdiction='HENDERSON'",
                    "watermark_col": "IssueDate",
                    "watermark_type": "text",
                    "watermark_format": "%m-%d-%Y %H:%M",
                    "id_keys": ["MJBLNumber", "IsPrimary"],
                }
            },
            "scope": (
                "Active Business Licenses snapshot (address-only -> ADR 0004 "
                "geocode on Business Location; MJBL county-wide companion "
                "filtered to Jurisdiction='HENDERSON'; frozen OpenDataGovernment "
                "MapServer twin is NOT registered)"
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_henderson_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Henderson feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in HENDERSON_FEED_SPECS:
        available = ", ".join(sorted(HENDERSON_FEED_SPECS))
        raise KeyError(
            f"'{HENDERSON_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = HENDERSON_FEED_SPECS[feed_name]
    extra_kwargs = {
        k: v for k, v in payload.get("extra", {}).items() if k != "scope"
    }
    return DatasetSpec(
        endpoint=payload["endpoint"],
        platform=payload["platform"],
        watermark_col=payload["watermark_col"],
        id_keys=payload["id_keys"],
        topic=getattr(settings, payload["topic_key"]),
        interval_seconds=payload["interval_seconds"],
        producer_key=payload["producer_key"],
        **extra_kwargs,
    )


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=HENDERSON_METRO_BBOX,
    division_bboxes=HENDERSON_DIVISION_BBOXES,
    submarkets=HENDERSON_SUBMARKETS,
    divisions=HENDERSON_DIVISIONS,
    contains=is_in_henderson_metro,
)

__all__ = [
    "HENDERSON_CITY_ID",
    "HENDERSON_DIVISIONS",
    "HENDERSON_DIVISION_BBOXES",
    "HENDERSON_FEED_SPECS",
    "HENDERSON_GEOCODE_CONTEXT",
    "HENDERSON_METRO_BBOX",
    "HENDERSON_PERMITS_ENDPOINT",
    "HENDERSON_SLA_ENDPOINT",
    "HENDERSON_SLA_MJBL_ENDPOINT",
    "HENDERSON_SUBMARKETS",
    "REGISTRATION",
    "compose_permit_address",
    "get_henderson_dataset",
    "is_in_greater_henderson_metro",
    "is_in_henderson_metro",
]
