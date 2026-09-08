DEEDS_FIELD_MAP = {
    "doc_id": ["PARCELID", "PRINTKEY"],
    "bbl": ["PARCELID"],
    "doc_type": ["DEED_TYPE"],
    "document_amount": ["SALE_PRICE"],
    "recorded_date": ["SALE_DATE"],
    "address_street": ["SITEADDRESS"],
    "incident_address": ["SITEADDRESS"],
    "borough": ["CITY"],
    "zipcode": ["ZIP5"],
}

FIELD_MAP = {
    "deeds": DEEDS_FIELD_MAP,
}

NON_CANDIDATE_METADATA_COLUMNS = (
    "VALID",
    "MultiSale",
    "PARCEL_SOURCE",
    "BOOK",
    "PAGE",
)

"""Roanoke Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Roanoke,
VA (the Star City of the Roanoke Valley, in the Blue Ridge foothills —
deliberately nested inside the Roanoke metro box and not overlapping the
sibling Lynchburg/Spartanburg leaf boxes).

Feed scope (mid-Atlantic/Northeast onboarding, US-314; not yet live-probed):
Roanoke publishes an open-data parcel layer on its municipal ArcGIS server
(``gis.roanokeva.gov``). The best-effort endpoint below is the city parcel
FeatureServer; the live watermark column and cadence are TBD at first probe
(see PR_DESCRIPTION). The feed is modeled as a DEEDS-led partial metro:

* DEEDS — ``OpenData/Parcels/FeatureServer/0``. Native parcel polygons
  (``outSR=4326`` rings -> centroid) are expected to supply every row's
  coordinates, so ``needs_geocode`` is False pending confirmation. Watermark
  ``SALE_DATE`` assumed TEXT ``MM/DD/YYYY`` (typed comparison required,
  ADR-0005) until a live probe confirms the format.
* PERMITS / SLA / COMPLAINTS_311 — not registered on this ticket; add via
  their own tickets once the open-data portal's feeds are enumerated.

Implementation note: the endpoint is a documented best-effort URL; confirm
the live layer name and ``SALE_DATE`` watermark at the first probe and
update both the Settings default and this leaf together.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

ROANOKE_CITY_ID: str = "roanoke"

# Roanoke metro bbox (Roanoke Valley, VA). The north edge reaches toward
# Hollins, the west edge the Salem/Giles line, the east edge Vinton, and the
# south edge Mill Mountain — all strictly inside this box.
ROANOKE_METRO_BBOX: dict[str, float] = {
    "min_lat": 37.20,
    "max_lat": 37.34,
    "min_lng": -80.02,
    "max_lng": -79.88,
}

# Registration-contract center: downtown Roanoke (Campbell Avenue CBD).
ROANOKE_CENTER: dict[str, float] = {"lat": 37.2710, "lng": -79.9414}

# 5 Roanoke Division Bounding Boxes (strictly nested inside the metro bbox)
ROANOKE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_ROANOKE":    {"min_lat": 37.250, "max_lat": 37.290, "min_lng": -79.955, "max_lng": -79.920},
    "NORTHWEST_HOLLINS":   {"min_lat": 37.300, "max_lat": 37.330, "min_lng": -79.990, "max_lng": -79.950},
    "SOUTHWEST_MILL_MOUNTAIN": {"min_lat": 37.200, "max_lat": 37.250, "min_lng": -79.980, "max_lng": -79.940},
    "NORTHEAST_VINTON":    {"min_lat": 37.260, "max_lat": 37.300, "min_lng": -79.910, "max_lng": -79.880},
    "WEST_GILES":          {"min_lat": 37.220, "max_lat": 37.280, "min_lng": -80.010, "max_lng": -79.970},
}


def is_in_roanoke_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Roanoke metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        ROANOKE_METRO_BBOX["min_lat"] <= lat <= ROANOKE_METRO_BBOX["max_lat"]
        and ROANOKE_METRO_BBOX["min_lng"] <= lng <= ROANOKE_METRO_BBOX["max_lng"]
    )


def is_in_roanoke(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_roanoke_metro`."""
    return is_in_roanoke_metro(lat, lng)


# ---------------------------------------------------------------------------
# Roanoke Submarket Registry (7 Submarkets Across 5 Divisions)
# ---------------------------------------------------------------------------

ROANOKE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_ROANOKE (2 Submarkets)
    # =======================================================================
    "Center City": SubmarketMeta(
        name="Center City",
        borough="DOWNTOWN_ROANOKE",
        lat=37.2710,
        lng=-79.9390,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.84,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=52.0,
        description="The Campbell Avenue / Market Square CBD with office-to-residential conversions, the Roanoke STAR-adjacent civic projects, and the city's densest mixed-use pipeline.",
        city_id="roanoke",
    ),
    "Old Southwest": SubmarketMeta(
        name="Old Southwest",
        borough="DOWNTOWN_ROANOKE",
        lat=37.2660,
        lng=-79.9460,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.80,
        capex=4100000.0,
        permit_vel=24.0,
        shift_ratio=1.34,
        sla=46.0,
        description="The turn-of-the-century streetcar suburb of brick rowhouses on the bluff southwest of downtown with steady restoration trades.",
        city_id="roanoke",
    ),
    # =======================================================================
    # NORTHWEST_HOLLINS (1 Submarket)
    # =======================================================================
    "Hollins": SubmarketMeta(
        name="Hollins",
        borough="NORTHWEST_HOLLINS",
        lat=37.3150,
        lng=-79.9700,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.66,
        capex=2800000.0,
        permit_vel=17.0,
        shift_ratio=1.20,
        sla=36.0,
        description="The northwest Roanoke community around Hollins University with seasonal student-housing turnover and steady single-family reinvestment.",
        city_id="roanoke",
    ),
    # =======================================================================
    # SOUTHWEST_MILL_MOUNTAIN (2 Submarkets)
    # =======================================================================
    "Mill Mountain": SubmarketMeta(
        name="Mill Mountain",
        borough="SOUTHWEST_MILL_MOUNTAIN",
        lat=37.2350,
        lng=-79.9600,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.70,
        capex=3200000.0,
        permit_vel=20.0,
        shift_ratio=1.25,
        sla=40.0,
        description="The south-side district at the base of Mill Mountain with cottage and bungalow stock, park-adjacent hospitality licensing, and hillside rebuild work.",
        city_id="roanoke",
    ),
    "Wasena": SubmarketMeta(
        name="Wasena",
        borough="SOUTHWEST_MILL_MOUNTAIN",
        lat=37.2450,
        lng=-79.9450,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.72,
        capex=3400000.0,
        permit_vel=21.0,
        shift_ratio=1.27,
        sla=41.0,
        description="The Wasena neighborhood along the Roanoke River greenway with solid pre-war housing stock and investor renovation flow.",
        city_id="roanoke",
    ),
    # =======================================================================
    # NORTHEAST_VINTON (1 Submarket)
    # =======================================================================
    "Vinton": SubmarketMeta(
        name="Vinton",
        borough="NORTHEAST_VINTON",
        lat=37.2800,
        lng=-79.9000,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.64,
        capex=2600000.0,
        permit_vel=16.0,
        shift_ratio=1.18,
        sla=34.0,
        description="The town of Vinton east of the Roanoke River with the lowest sale prices in the metro and steady vacancy-to-acquisition conversion flow.",
        city_id="roanoke",
    ),
    # =======================================================================
    # WEST_GILES (2 Submarkets)
    # =======================================================================
    "Salem": SubmarketMeta(
        name="Salem",
        borough="WEST_GILES",
        lat=37.2550,
        lng=-79.9900,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.68,
        capex=3000000.0,
        permit_vel=18.0,
        shift_ratio=1.22,
        sla=38.0,
        description="The city of Salem west of Roanoke with the collegiate and medical-corridor rental register and block-by-block reinvestment.",
        city_id="roanoke",
    ),
    "Clearbrook": SubmarketMeta(
        name="Clearbrook",
        borough="WEST_GILES",
        lat=37.2250,
        lng=-80.0000,
        zoom=13.0,
        pitch=30.0,
        base_lims=0.60,
        capex=2400000.0,
        permit_vel=15.0,
        shift_ratio=1.16,
        sla=33.0,
        description="The rural-residential fringe southwest of Roanoke with acreage parcels, well-and-septic stock, and the slowest sale cadence in the metro.",
        city_id="roanoke",
    ),
}


# ---------------------------------------------------------------------------
# Roanoke Divisions Catalog
# ---------------------------------------------------------------------------

ROANOKE_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_ROANOKE": BoroughMeta(
        name="DOWNTOWN_ROANOKE",
        center_lat=37.2680,
        center_lng=-79.9420,
        zoom=13.5,
        bbox=ROANOKE_DIVISION_BBOXES["DOWNTOWN_ROANOKE"],
        submarkets=[k for k, v in ROANOKE_SUBMARKETS.items() if v.borough == "DOWNTOWN_ROANOKE"],
        city_id="roanoke",
    ),
    "NORTHWEST_HOLLINS": BoroughMeta(
        name="NORTHWEST_HOLLINS",
        center_lat=37.3150,
        center_lng=-79.9700,
        zoom=13.0,
        bbox=ROANOKE_DIVISION_BBOXES["NORTHWEST_HOLLINS"],
        submarkets=[k for k, v in ROANOKE_SUBMARKETS.items() if v.borough == "NORTHWEST_HOLLINS"],
        city_id="roanoke",
    ),
    "SOUTHWEST_MILL_MOUNTAIN": BoroughMeta(
        name="SOUTHWEST_MILL_MOUNTAIN",
        center_lat=37.2400,
        center_lng=-79.9520,
        zoom=13.0,
        bbox=ROANOKE_DIVISION_BBOXES["SOUTHWEST_MILL_MOUNTAIN"],
        submarkets=[k for k, v in ROANOKE_SUBMARKETS.items() if v.borough == "SOUTHWEST_MILL_MOUNTAIN"],
        city_id="roanoke",
    ),
    "NORTHEAST_VINTON": BoroughMeta(
        name="NORTHEAST_VINTON",
        center_lat=37.2800,
        center_lng=-79.9000,
        zoom=13.0,
        bbox=ROANOKE_DIVISION_BBOXES["NORTHEAST_VINTON"],
        submarkets=[k for k, v in ROANOKE_SUBMARKETS.items() if v.borough == "NORTHEAST_VINTON"],
        city_id="roanoke",
    ),
    "WEST_GILES": BoroughMeta(
        name="WEST_GILES",
        center_lat=37.2400,
        center_lng=-79.9950,
        zoom=13.0,
        bbox=ROANOKE_DIVISION_BBOXES["WEST_GILES"],
        submarkets=[k for k, v in ROANOKE_SUBMARKETS.items() if v.borough == "WEST_GILES"],
        city_id="roanoke",
    ),
}

RNK_DIVISION_BBOXES = ROANOKE_DIVISION_BBOXES
RNK_SUBMARKETS = ROANOKE_SUBMARKETS
RNK_DIVISIONS = ROANOKE_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Best-effort Roanoke open-data parcel layer; confirm the live endpoint and
# SALE_DATE watermark at the first probe (see module docstring).
# ---------------------------------------------------------------------------
ROANOKE_DEEDS_ENDPOINT = (
    "https://gis.roanokeva.gov/server/rest/services/OpenData/Parcels/FeatureServer/0"
)

ROANOKE_FEED_SPECS: dict[str, dict[str, object]] = {
    "deeds": {
        "endpoint": ROANOKE_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "SALE_DATE",
        "id_keys": ["PARCELID", "OBJECTID"],
        "topic_key": "topic_deeds",
        "interval_seconds": 600.0,
        "producer_key": "deeds",
        "extra": {
            "needs_geocode": False,
            "watermark_type": "text",
            "watermark_format": "%m/%d/%Y",
            "oid_field": "OBJECTID",
            "max_record_count": 100000,
            "expected_cadence_days": 30,
            "non_spatial": False,
            "scope": (
                "Roanoke DEEDS/sales via the city open-data parcel layer "
                "(best-effort endpoint; native parcel polygons expected to "
                "supply coordinates, so the ADR-0004 geocode hook is NOT "
                "declared pending confirmation). TEXT MM/DD/YYYY watermark "
                "assumed (typed comparison required, ADR-0005). PERMITS/SLA/"
                "311 are NOT enumerated on this ticket — add via their own "
                "tickets once the open-data portal feeds are surveyed. "
                "PARCELID/OBJECTID are the parcel keys; SALE_DATE is the "
                "assumed watermark column. Confirm the live layer name and "
                "watermark at the first probe and update Settings + this leaf "
                "together."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_roanoke_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Roanoke feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (permits/SLA/
    311 are not registered on this ticket).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in ROANOKE_FEED_SPECS:
        available = ", ".join(sorted(ROANOKE_FEED_SPECS))
        raise KeyError(
            f"'{ROANOKE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = ROANOKE_FEED_SPECS[feed_name]
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
    metro_bbox=ROANOKE_METRO_BBOX,
    division_bboxes=ROANOKE_DIVISION_BBOXES,
    submarkets=ROANOKE_SUBMARKETS,
    divisions=ROANOKE_DIVISIONS,
    contains=is_in_roanoke_metro,
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "REGISTRATION",
    "RNK_DIVISIONS",
    "RNK_DIVISION_BBOXES",
    "RNK_SUBMARKETS",
    "ROANOKE_CENTER",
    "ROANOKE_CITY_ID",
    "ROANOKE_DEEDS_ENDPOINT",
    "ROANOKE_DIVISIONS",
    "ROANOKE_DIVISION_BBOXES",
    "ROANOKE_FEED_SPECS",
    "ROANOKE_METRO_BBOX",
    "ROANOKE_SUBMARKETS",
    "get_roanoke_dataset",
    "is_in_roanoke",
    "is_in_roanoke_metro",
]
