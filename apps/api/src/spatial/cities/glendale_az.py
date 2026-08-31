COMPLAINTS_311_FIELD_MAP = {
    "incident_id": ["Request_Number", "OBJECTID"],
    "complaint_type": ["Request_Type", "Request_Type_Group"],
    "created_date": ["Request_Date"],
    "closed_date": ["Close_Date"],
    "status": ["Status"],
    "borough": ["Council_District"],
    "incident_address": ["FULL_ADDRESS"],
}

SLA_FIELD_MAP = {
    "license_id": ["OBJECTID"],
    "license_type": ["BusinessType", "LicenseType"],
    "premises_name": ["BusinessName"],
    "dba": ["BusinessName"],
    "effective_date": ["IssuedOn"],
    "expiration_date": ["ExpiresOn"],
    "status": ["LicenseStatus"],
    "borough": ["District"],
    "address_street": ["AddressLine1"],
    "zipcode": ["ZipCode"],
}

FIELD_MAP = {
    "311": COMPLAINTS_311_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT = "Glendale, AZ"

DROPPED_NONADDRESS_COLUMNS = (
    "Latitude",
    "Longitude",
    "ANON_BLOCK",
    "Cross_Streets",
    "Responsible_Department_Name",
    "DateLoaded",
    "City",
    "State",
    "ParcelLegalDesc",
    "Shape",
    "GlobalID",
)

"""Glendale, AZ spatial registry and geometry (US-250).

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Glendale,
Arizona (northwest Maricopa County, ~250k).

Glendale is a TWO-FEED PARTIAL metro on the official City of Glendale ArcGIS
Server 11.4 (``gismaps.glendaleaz.com/gisserver``, owner ``GisAdmin_COG``):
COMPLAINTS_311 (``OpenData/GLENDALEONE_EXTERNAL_REQUESTS_PTS`` MapServer/0,
~107,646 rows) and SLA (``OpenData/Business_Licenses`` MapServer/1 table,
~9,856 rows). PERMITS are not anonymous (the ``SmartGov``/``Building_Safety``
folders return ArcGIS error 499 Token Required), and DEEDS are Maricopa
County-held (``docs/research/probe-maricopa-sales-affidavits.md`` — feasible
but needs CSVClient delimiter + scheduler zip_member forwarding on a spine
hold); ``get_glendale_az_dataset`` raises for both.

Live-probe evidence (2026-08-28, US-250):

* 311 — native **WGS84 (WKID 4326) point geometry**, the coordinate path
  (``ArcGISClient._flatten_feature`` lifts it to full-precision latitude/
  longitude). The ``Latitude``/``Longitude`` attributes are truncated
  3-decimal placeholders and are never candidates. 107,646 rows; watermark
  ``Request_Date`` newest ``1785888000000`` = 2026-08-05T00:00:00Z (co-newest
  batch). ``DateLoaded`` is uniform ``1785981615723`` = 2026-08-06T02:00:15Z
  — the layer is ETL bulk-replaced and was **22 days stale at probe**; the
  watermark registration is deliberate so the staleness probe alarms if the
  load does not resume. ``FULL_ADDRESS`` is anonymized to block level
  ("6700 BLOCK W DENTON LN"). ``needs_geocode=False`` (every row carries
  geometry). Council districts on the feed: BARREL / CACTUS / CHOLLA /
  OCOTILLO / SAHUARO / YUCCA (these name the six divisions).
* SLA — a **standalone table, no geometry**; ``IssuedOn``/``ExpiresOn`` are
  ``esriFieldTypeDateOnly`` arriving as ``YYYY-MM-DD`` strings (not
  ISO-normalized client-side). 9,856 rows; watermark ``IssuedOn`` newest
  **"2026-08-22"**; ``DateLoaded`` ``1787842811000`` = 2026-08-27T15:00:11Z
  (fresh load). Address-only → ``needs_geocode=True`` (ADR-0004) on the
  clean single-field ``AddressLine1`` with context "Glendale, AZ". Snapshot
  ingestion (full-replace registry, KC-SLA precedent).
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

GLENDALE_AZ_CITY_ID: str = "glendale_az"
GLENDALE_AZ_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Glendale (official CityBoundary polygon spans lat 33.5078..33.6979,
# lng -112.4616..-112.1516). Permissive enough to hold the full city incl.
# the Luke AFB / Westgate west edge and the Arrowhead/Cholla north while
# rejecting downtown Phoenix (33.4484, -112.0740) to the southeast.
GLENDALE_AZ_METRO_BBOX: dict[str, float] = {
    "min_lat": 33.50,
    "max_lat": 33.71,
    "min_lng": -112.47,
    "max_lng": -112.14,
}

# 6 Glendale divisions, named for the city's six council districts (the same
# values the feeds' Council_District/District columns carry). Hand-authored;
# borough resolution at ingest comes from coordinates via
# get_division_for_coordinate, so bboxes need only be sane, mutually
# non-overlapping, and contain their own submarket centers.
GLENDALE_AZ_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "OCOTILLO": {
        "min_lat": 33.50,
        "max_lat": 33.56,
        "min_lng": -112.205,
        "max_lng": -112.14,
    },
    "YUCCA": {
        "min_lat": 33.50,
        "max_lat": 33.56,
        "min_lng": -112.47,
        "max_lng": -112.205,
    },
    "CACTUS": {
        "min_lat": 33.56,
        "max_lat": 33.61,
        "min_lng": -112.205,
        "max_lng": -112.14,
    },
    "BARREL": {
        "min_lat": 33.56,
        "max_lat": 33.61,
        "min_lng": -112.47,
        "max_lng": -112.205,
    },
    "CHOLLA": {
        "min_lat": 33.61,
        "max_lat": 33.71,
        "min_lng": -112.205,
        "max_lng": -112.14,
    },
    "SAHUARO": {
        "min_lat": 33.61,
        "max_lat": 33.71,
        "min_lng": -112.47,
        "max_lng": -112.205,
    },
}


def is_in_glendale_az_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Glendale, AZ metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        GLENDALE_AZ_METRO_BBOX["min_lat"] <= lat <= GLENDALE_AZ_METRO_BBOX["max_lat"]
        and GLENDALE_AZ_METRO_BBOX["min_lng"] <= lng <= GLENDALE_AZ_METRO_BBOX["max_lng"]
    )


is_in_greater_glendale_az_metro = is_in_glendale_az_metro


GLENDALE_AZ_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # OCOTILLO (SE) (2)
    # =======================================================================
    "Downtown Glendale": SubmarketMeta(
        name="Downtown Glendale",
        borough="OCOTILLO",
        lat=33.5388,
        lng=-112.1859,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.86,
        capex=6800000.0,
        permit_vel=30.0,
        shift_ratio=1.46,
        sla=55.0,
        description=(
            "Historic downtown core on Glendale Avenue with the Antique Row "
            "shopping district, Murphy Park, and steady storefront "
            "commercial-renovation permitting around the Water Tower."
        ),
        city_id="glendale_az",
    ),
    "Ocotillo / 43rd Ave Corridor": SubmarketMeta(
        name="Ocotillo / 43rd Ave Corridor",
        borough="OCOTILLO",
        lat=33.5200,
        lng=-112.1800,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=4800000.0,
        permit_vel=26.0,
        shift_ratio=1.38,
        sla=49.0,
        description=(
            "Southeast council-district corridor of post-war tract housing "
            "and neighborhood retail along 43rd/51st avenues with "
            "renovation-led 311 and business-license churn."
        ),
        city_id="glendale_az",
    ),
    # =======================================================================
    # YUCCA (SW) (2)
    # =======================================================================
    "Westgate": SubmarketMeta(
        name="Westgate",
        borough="YUCCA",
        lat=33.5381,
        lng=-112.2599,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.88,
        capex=9800000.0,
        permit_vel=42.0,
        shift_ratio=1.54,
        sla=68.0,
        description=(
            "West Valley entertainment district anchored by State Farm "
            "Stadium, Desert Diamond Arena, and the Westgate dining/retail "
            "row with high hospitality license density."
        ),
        city_id="glendale_az",
    ),
    "Manistee Estates": SubmarketMeta(
        name="Manistee Estates",
        borough="YUCCA",
        lat=33.5276,
        lng=-112.2150,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.82,
        capex=5600000.0,
        permit_vel=24.0,
        shift_ratio=1.40,
        sla=51.0,
        description=(
            "Established residential district west of downtown with the "
            "historic Manistee Ranch, mature-canopy lots, and steady "
            "addition/renovation permitting."
        ),
        city_id="glendale_az",
    ),
    # =======================================================================
    # BARREL (W) (1)
    # =======================================================================
    "Grand Avenue / Barrel Corridor": SubmarketMeta(
        name="Grand Avenue / Barrel Corridor",
        borough="BARREL",
        lat=33.5750,
        lng=-112.2300,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.80,
        capex=5400000.0,
        permit_vel=28.0,
        shift_ratio=1.42,
        sla=52.0,
        description=(
            "West-central corridor along Grand Avenue with light-industrial, "
            "warehouse, and auto-services business licensing and water/sewer "
            "service-request volume."
        ),
        city_id="glendale_az",
    ),
    # =======================================================================
    # CACTUS (E) (1)
    # =======================================================================
    "51st Ave / Cactus District": SubmarketMeta(
        name="51st Ave / Cactus District",
        borough="CACTUS",
        lat=33.5650,
        lng=-112.1550,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.79,
        capex=5200000.0,
        permit_vel=27.0,
        shift_ratio=1.39,
        sla=50.0,
        description=(
            "East-central district hugging the Phoenix border with "
            "mid-century housing, strip-retail revitalization, and strong "
            "trash/street service-request cadence."
        ),
        city_id="glendale_az",
    ),
    # =======================================================================
    # CHOLLA (NE) (2)
    # =======================================================================
    "Arrowhead": SubmarketMeta(
        name="Arrowhead",
        borough="CHOLLA",
        lat=33.6289,
        lng=-112.1697,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.87,
        capex=9200000.0,
        permit_vel=40.0,
        shift_ratio=1.52,
        sla=64.0,
        description=(
            "Master-planned northeast Glendale around Arrowhead Towne Center "
            "with golf-course estates, big-box retail, and the city's "
            "highest-value new-construction permits."
        ),
        city_id="glendale_az",
    ),
    "Thunderbird": SubmarketMeta(
        name="Thunderbird",
        borough="CHOLLA",
        lat=33.6110,
        lng=-112.1430,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.84,
        capex=7200000.0,
        permit_vel=34.0,
        shift_ratio=1.46,
        sla=58.0,
        description=(
            "Northeast neighborhoods along Thunderbird Road near the "
            "Thunderbird School / ASU West campus with mixed multifamily "
            "and commercial infill."
        ),
        city_id="glendale_az",
    ),
    # =======================================================================
    # SAHUARO (NW) (1)
    # =======================================================================
    "Sahuaro Ranch": SubmarketMeta(
        name="Sahuaro Ranch",
        borough="SAHUARO",
        lat=33.6300,
        lng=-112.2139,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.83,
        capex=6800000.0,
        permit_vel=32.0,
        shift_ratio=1.44,
        sla=57.0,
        description=(
            "Northwest district around historic Sahuaro Ranch Park with "
            "tract-housing renovation, ranchette lots, and retail-anchored "
            "corridors at 59th/67th avenues."
        ),
        city_id="glendale_az",
    ),
}


GLENDALE_AZ_DIVISIONS: dict[str, BoroughMeta] = {
    "OCOTILLO": BoroughMeta(
        name="OCOTILLO",
        center_lat=33.53,
        center_lng=-112.19,
        zoom=13.5,
        bbox=GLENDALE_AZ_DIVISION_BBOXES["OCOTILLO"],
        submarkets=[k for k, v in GLENDALE_AZ_SUBMARKETS.items() if v.borough == "OCOTILLO"],
        city_id="glendale_az",
    ),
    "YUCCA": BoroughMeta(
        name="YUCCA",
        center_lat=33.53,
        center_lng=-112.26,
        zoom=13.0,
        bbox=GLENDALE_AZ_DIVISION_BBOXES["YUCCA"],
        submarkets=[k for k, v in GLENDALE_AZ_SUBMARKETS.items() if v.borough == "YUCCA"],
        city_id="glendale_az",
    ),
    "BARREL": BoroughMeta(
        name="BARREL",
        center_lat=33.585,
        center_lng=-112.30,
        zoom=12.5,
        bbox=GLENDALE_AZ_DIVISION_BBOXES["BARREL"],
        submarkets=[k for k, v in GLENDALE_AZ_SUBMARKETS.items() if v.borough == "BARREL"],
        city_id="glendale_az",
    ),
    "CACTUS": BoroughMeta(
        name="CACTUS",
        center_lat=33.585,
        center_lng=-112.16,
        zoom=12.5,
        bbox=GLENDALE_AZ_DIVISION_BBOXES["CACTUS"],
        submarkets=[k for k, v in GLENDALE_AZ_SUBMARKETS.items() if v.borough == "CACTUS"],
        city_id="glendale_az",
    ),
    "CHOLLA": BoroughMeta(
        name="CHOLLA",
        center_lat=33.66,
        center_lng=-112.17,
        zoom=12.5,
        bbox=GLENDALE_AZ_DIVISION_BBOXES["CHOLLA"],
        submarkets=[k for k, v in GLENDALE_AZ_SUBMARKETS.items() if v.borough == "CHOLLA"],
        city_id="glendale_az",
    ),
    "SAHUARO": BoroughMeta(
        name="SAHUARO",
        center_lat=33.66,
        center_lng=-112.30,
        zoom=12.5,
        bbox=GLENDALE_AZ_DIVISION_BBOXES["SAHUARO"],
        submarkets=[k for k, v in GLENDALE_AZ_SUBMARKETS.items() if v.borough == "SAHUARO"],
        city_id="glendale_az",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Do not register permits (SmartGov/Building_Safety are
# token-protected) or deeds (Maricopa County, CSVClient+scheduler spine gap).
# ---------------------------------------------------------------------------
GLENDALE_AZ_311_ENDPOINT = (
    "https://gismaps.glendaleaz.com/gisserver/rest/services/"
    "OpenData/GLENDALEONE_EXTERNAL_REQUESTS_PTS/MapServer/0"
)
GLENDALE_AZ_SLA_ENDPOINT = (
    "https://gismaps.glendaleaz.com/gisserver/rest/services/"
    "OpenData/Business_Licenses/MapServer/1"
)

GLENDALE_AZ_FEED_SPECS: dict[str, dict[str, object]] = {
    "311": {
        "endpoint": GLENDALE_AZ_311_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Request_Date",
        "id_keys": ["Request_Number", "OBJECTID"],
        "topic_key": "topic_311",
        "interval_seconds": 300.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "Request_Date DESC, Request_Number DESC",
            "scope": (
                "GlendaleOne citizen-service-request layer (MapServer/0 on "
                "the city gisserver). Native WGS84 point geometry is the "
                "coordinate path (Latitude/Longitude attributes are "
                "truncated placeholders, never candidates). FULL_ADDRESS is "
                "anonymized to block level. ETL bulk-replaces the layer; "
                "DateLoaded was 2026-08-06 (22 days stale) at the 2026-08-28 "
                "probe — register so the watermark staleness probe alarms if "
                "loads do not resume."
            ),
            "field_map": COMPLAINTS_311_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": GLENDALE_AZ_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "IssuedOn",
        "id_keys": ["OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": GLENDALE_AZ_GEOCODE_CONTEXT,
            "ingestion_mode": "snapshot",
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "IssuedOn DESC",
            "scope": (
                "Glendale Business Licenses table (MapServer/1 on the city "
                "gisserver). Standalone table with no geometry: rows geocode "
                "via the ADR-0004 supplement on the single-field "
                "AddressLine1 (context 'Glendale, AZ'). IssuedOn/ExpiresOn "
                "are esriFieldTypeDateOnly YYYY-MM-DD strings (not ISO-"
                "normalized by the ArcGIS client). Snapshot registry; "
                "license number is embedded in LicenseType but absent on "
                "some rows, so license_id maps to OBJECTID."
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_glendale_az_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a (pending-spine) Glendale, AZ feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is absent
    (permits, deeds).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in GLENDALE_AZ_FEED_SPECS:
        available = ", ".join(sorted(GLENDALE_AZ_FEED_SPECS))
        raise KeyError(
            f"'{GLENDALE_AZ_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = GLENDALE_AZ_FEED_SPECS[feed_name]
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
    metro_bbox=GLENDALE_AZ_METRO_BBOX,
    division_bboxes=GLENDALE_AZ_DIVISION_BBOXES,
    submarkets=GLENDALE_AZ_SUBMARKETS,
    divisions=GLENDALE_AZ_DIVISIONS,
    contains=is_in_glendale_az_metro,
)

__all__ = [
    "GLENDALE_AZ_311_ENDPOINT",
    "GLENDALE_AZ_CITY_ID",
    "GLENDALE_AZ_DIVISIONS",
    "GLENDALE_AZ_DIVISION_BBOXES",
    "GLENDALE_AZ_FEED_SPECS",
    "GLENDALE_AZ_GEOCODE_CONTEXT",
    "GLENDALE_AZ_METRO_BBOX",
    "GLENDALE_AZ_SLA_ENDPOINT",
    "GLENDALE_AZ_SUBMARKETS",
    "REGISTRATION",
    "get_glendale_az_dataset",
    "is_in_glendale_az_metro",
    "is_in_greater_glendale_az_metro",
]
