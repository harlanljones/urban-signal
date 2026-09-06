DEEDS_FIELD_MAP = {
    "doc_id": ["PARCELID"],
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

"""Huntington, WV Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Huntington,
WV (Cabell County seat on the Ohio River — deliberately not overlapping the
sibling Charleston/Huntington-corridor leaf boxes).

Feed scope: Huntington is a DEEDS-led partial metro. The city's municipal
open-data parcel/sales layer (Cabell County Assessor extract surfaced through
the City of Huntington ArcGIS server) carries per-parcel SALE_DATE / SALE_PRICE
/ DEED_TYPE — the closest ACRIS-shape feed in this corridor. The feed is an
ArcGIS polygon service served by the existing ``ArcGISClient``:

* DEEDS — ``Parcels/Deeds/FeatureServer/0``. Watermark ``SALE_DATE`` is TEXT
  ``MM/DD/YYYY``; ADR-0005 text-watermark with the declared ``%m/%d/%Y`` format
  is mandatory. Native parcel polygons (``outSR=4326`` rings -> centroid) supply
  every row's coordinates, so ``needs_geocode`` stays False — no ADR-0004 hook.
* PERMITS — absent on the City Hub at probe time. Tier 3.
* SLA/licenses — absent on the City Hub at probe time. Tier 3.
* COMPLAINTS_311 — absent on the City Hub at probe time. Tier 3.

NOTE ON ENDPOINT (US-320): the ``arcgis_huntington_wv_deeds_url`` default is a
best-effort placeholder (``https://huntingtonwv.gov/server/rest/services/...``).
The endpoint was not confirmed live during onboarding; it must be verified
against the City's open-data portal before the feed is scheduled. The gate does
not check endpoint liveness.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

HUNTINGTON_WV_CITY_ID: str = "huntington_wv"

# Huntington metro bbox around the downtown core (lat 38.4192, lng -82.4454).
HUNTINGTON_WV_METRO_BBOX: dict[str, float] = {
    "min_lat": 38.35,
    "max_lat": 38.49,
    "min_lng": -82.55,
    "max_lng": -82.36,
}

# Registration-contract center: downtown Huntington (8th St / 4th Ave core).
HUNTINGTON_WV_CENTER: dict[str, float] = {"lat": 38.4192, "lng": -82.4454}

# 5 Huntington Division Bounding Boxes (strictly nested inside the metro bbox)
HUNTINGTON_WV_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_RIVERFRONT": {"min_lat": 38.40, "max_lat": 38.44, "min_lng": -82.46, "max_lng": -82.43},
    "HIGHLAND_PARK":       {"min_lat": 38.44, "max_lat": 38.48, "min_lng": -82.46, "max_lng": -82.42},
    "SOUTH_SIDE":          {"min_lat": 38.35, "max_lat": 38.40, "min_lng": -82.50, "max_lng": -82.44},
    "EAST_HUNTINGTON":     {"min_lat": 38.40, "max_lat": 38.46, "min_lng": -82.43, "max_lng": -82.40},
    "WEST_END":            {"min_lat": 38.37, "max_lat": 38.43, "min_lng": -82.55, "max_lng": -82.48},
}


def is_in_huntington_wv_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Huntington metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        HUNTINGTON_WV_METRO_BBOX["min_lat"] <= lat <= HUNTINGTON_WV_METRO_BBOX["max_lat"]
        and HUNTINGTON_WV_METRO_BBOX["min_lng"] <= lng <= HUNTINGTON_WV_METRO_BBOX["max_lng"]
    )


def is_in_huntington_wv(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_huntington_wv_metro`."""
    return is_in_huntington_wv_metro(lat, lng)


# ---------------------------------------------------------------------------
# Huntington Submarket Registry (7 Submarkets Across 5 Divisions)
# ---------------------------------------------------------------------------

HUNTINGTON_WV_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_RIVERFRONT (2 Submarkets)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN_RIVERFRONT",
        lat=38.4200,
        lng=-82.4450,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.85,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The 9th Street civic core and Ohio River riverfront with mixed-use conversions, the Marshall University edge, and the city's densest downtown pipeline.",
        city_id="huntington_wv",
    ),
    "Riverfront": SubmarketMeta(
        name="Riverfront",
        borough="DOWNTOWN_RIVERFRONT",
        lat=38.4130,
        lng=-82.4480,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.81,
        capex=4100000.0,
        permit_vel=23.0,
        shift_ratio=1.34,
        sla=45.0,
        description="The Harris Riverfront Park and Pullman Square district with hospitality licensing, festival-trade retail, and riverfront redevelopment.",
        city_id="huntington_wv",
    ),
    # =======================================================================
    # HIGHLAND_PARK (2 Submarkets)
    # =======================================================================
    "Highland Park": SubmarketMeta(
        name="Highland Park",
        borough="HIGHLAND_PARK",
        lat=38.4580,
        lng=-82.4450,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.79,
        capex=3800000.0,
        permit_vel=27.0,
        shift_ratio=1.38,
        sla=50.0,
        description="The Hal Greer corridor and historic residential grid around the namesake park with steady renovation trades and student-adjacent rental stock.",
        city_id="huntington_wv",
    ),
    "Ritter Park": SubmarketMeta(
        name="Ritter Park",
        borough="HIGHLAND_PARK",
        lat=38.4450,
        lng=-82.4350,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.82,
        capex=4400000.0,
        permit_vel=29.0,
        shift_ratio=1.40,
        sla=52.0,
        description="The Ritter Park / 5th Avenue estate district with high-value pre-war housing stock and investor restoration flow.",
        city_id="huntington_wv",
    ),
    # =======================================================================
    # SOUTH_SIDE (1 Submarket)
    # =======================================================================
    "Southside": SubmarketMeta(
        name="Southside",
        borough="SOUTH_SIDE",
        lat=38.3750,
        lng=-82.4700,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.70,
        capex=3100000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=40.0,
        description="The South Side / 29th Street ward across the 4th Avenue viaduct with craftsman-bungalow stock, a deep rental register, and block-by-block reinvestment.",
        city_id="huntington_wv",
    ),
    # =======================================================================
    # EAST_HUNTINGTON (1 Submarket)
    # =======================================================================
    "East End": SubmarketMeta(
        name="East End",
        borough="EAST_HUNTINGTON",
        lat=38.4250,
        lng=-82.4150,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.73,
        capex=3500000.0,
        permit_vel=22.0,
        shift_ratio=1.28,
        sla=43.0,
        description="The east-bank neighborhoods along the 31st Street bridge approach with solid mid-century housing and vacancy-to-acquisition conversion flow.",
        city_id="huntington_wv",
    ),
    # =======================================================================
    # WEST_END (1 Submarket)
    # =======================================================================
    "West End": SubmarketMeta(
        name="West End",
        borough="WEST_END",
        lat=38.4000,
        lng=-82.5150,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.66,
        capex=2700000.0,
        permit_vel=16.0,
        shift_ratio=1.18,
        sla=34.0,
        description="The West End / Guyandotte fringe along US-60 with the city's lowest sale prices and the heaviest acquisition-conversion flow.",
        city_id="huntington_wv",
    ),
}


# ---------------------------------------------------------------------------
# Huntington Divisions Catalog
# ---------------------------------------------------------------------------

HUNTINGTON_WV_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_RIVERFRONT": BoroughMeta(
        name="DOWNTOWN_RIVERFRONT",
        center_lat=38.4165,
        center_lng=-82.4450,
        zoom=13.5,
        bbox=HUNTINGTON_WV_DIVISION_BBOXES["DOWNTOWN_RIVERFRONT"],
        submarkets=[k for k, v in HUNTINGTON_WV_SUBMARKETS.items() if v.borough == "DOWNTOWN_RIVERFRONT"],
        city_id="huntington_wv",
    ),
    "HIGHLAND_PARK": BoroughMeta(
        name="HIGHLAND_PARK",
        center_lat=38.4515,
        center_lng=-82.4425,
        zoom=13.0,
        bbox=HUNTINGTON_WV_DIVISION_BBOXES["HIGHLAND_PARK"],
        submarkets=[k for k, v in HUNTINGTON_WV_SUBMARKETS.items() if v.borough == "HIGHLAND_PARK"],
        city_id="huntington_wv",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=38.3750,
        center_lng=-82.4700,
        zoom=13.0,
        bbox=HUNTINGTON_WV_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in HUNTINGTON_WV_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="huntington_wv",
    ),
    "EAST_HUNTINGTON": BoroughMeta(
        name="EAST_HUNTINGTON",
        center_lat=38.4300,
        center_lng=-82.4150,
        zoom=13.0,
        bbox=HUNTINGTON_WV_DIVISION_BBOXES["EAST_HUNTINGTON"],
        submarkets=[k for k, v in HUNTINGTON_WV_SUBMARKETS.items() if v.borough == "EAST_HUNTINGTON"],
        city_id="huntington_wv",
    ),
    "WEST_END": BoroughMeta(
        name="WEST_END",
        center_lat=38.4000,
        center_lng=-82.5150,
        zoom=13.0,
        bbox=HUNTINGTON_WV_DIVISION_BBOXES["WEST_END"],
        submarkets=[k for k, v in HUNTINGTON_WV_SUBMARKETS.items() if v.borough == "WEST_END"],
        city_id="huntington_wv",
    ),
}

HNT_DIVISION_BBOXES = HUNTINGTON_WV_DIVISION_BBOXES
HNT_SUBMARKETS = HUNTINGTON_WV_SUBMARKETS
HNT_DIVISIONS = HUNTINGTON_WV_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# ---------------------------------------------------------------------------
HUNTINGTON_WV_DEEDS_ENDPOINT = (
    "https://huntingtonwv.gov/server/rest/services/"
    "Parcels/Deeds/FeatureServer/0"
)

HUNTINGTON_WV_FEED_SPECS: dict[str, dict[str, object]] = {
    "deeds": {
        "endpoint": HUNTINGTON_WV_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "SALE_DATE",
        "id_keys": ["PARCELID", "SALE_DATE"],
        "topic_key": "topic_deeds",
        "interval_seconds": 600.0,
        "producer_key": "deeds",
        "extra": {
            # Native parcel polygons (outSR=4326 rings -> centroid) supply
            # every row's coordinates; the ADR-0004 geocode hook is NOT
            # declared. SITEADDRESS/ZIP5 expected complete on sampled sale rows.
            "needs_geocode": False,
            "watermark_type": "text",
            "watermark_format": "%m/%d/%Y",
            "oid_field": "OBJECTID",
            "max_record_count": 100000,
            "expected_cadence_days": 30,
            "non_spatial": False,
            "scope": (
                "Huntington WV DEEDS/sales via the City municipal open-data "
                "parcel/sales ArcGIS layer (Cabell County Assessor extract). "
                "TEXT MM/DD/YYYY watermark sorts lexically — typed comparison "
                "required (ADR-0005). ENDPOINT UNVERIFIED (US-320): the "
                "arcgis_huntington_wv_deeds_url default is a best-effort "
                "placeholder and must be confirmed against the City open-data "
                "portal before scheduling. $1 quitclaim transfers are KEPT at "
                "ingest (no per-city where). No owner-name columns exist; party "
                "fields stay None. PARCELID is the parcel key; SALE_DATE is the "
                "watermark."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_huntington_wv_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Huntington feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (permits/SLA/
    311 are absent from the City Hub at probe time).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in HUNTINGTON_WV_FEED_SPECS:
        available = ", ".join(sorted(HUNTINGTON_WV_FEED_SPECS))
        raise KeyError(
            f"'{HUNTINGTON_WV_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = HUNTINGTON_WV_FEED_SPECS[feed_name]
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
    metro_bbox=HUNTINGTON_WV_METRO_BBOX,
    division_bboxes=HUNTINGTON_WV_DIVISION_BBOXES,
    submarkets=HUNTINGTON_WV_SUBMARKETS,
    divisions=HUNTINGTON_WV_DIVISIONS,
    contains=is_in_huntington_wv_metro,
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "HNT_DIVISIONS",
    "HNT_DIVISION_BBOXES",
    "HNT_SUBMARKETS",
    "HUNTINGTON_WV_CENTER",
    "HUNTINGTON_WV_CITY_ID",
    "HUNTINGTON_WV_DEEDS_ENDPOINT",
    "HUNTINGTON_WV_DIVISIONS",
    "HUNTINGTON_WV_DIVISION_BBOXES",
    "HUNTINGTON_WV_FEED_SPECS",
    "HUNTINGTON_WV_METRO_BBOX",
    "HUNTINGTON_WV_SUBMARKETS",
    "REGISTRATION",
    "get_huntington_wv_dataset",
    "is_in_huntington_wv",
    "is_in_huntington_wv_metro",
]
