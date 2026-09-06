"""Wilmington, DE spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Wilmington,
DE (New Castle County seat on the Christina River, at the head of the
Delaware Estuary — deliberately not overlapping the sibling Philadelphia
leaf box to the north).

Wilmington is a DEEDS-led partial metro: New Castle County publishes parcel
sales through its open-data ArcGIS FeatureServer. The feed carries per-parcel
``SALE_DATE``/``SALE_PRICE``/``PARCELID`` and native parcel polygons, so it
maps cleanly onto the ACRIS-shape DEEDS signal:

* DEEDS — ``Parcels/Real_Estate_Sales/FeatureServer/0``. Watermark
  ``SALE_DATE`` is the recorded-sale date; native parcel polygons
  (``outSR=4326`` rings -> centroid) supply every row's coordinates, so
  ``needs_geocode`` stays False — no ADR-0004 hook. ``SALE_DATE`` is treated
  as a TEXT date column (``%Y-%m-%d``) to keep ordering stable across the
  county's lexical sort.
* PERMITS — absent from the county open-data layer for city parcels; the
  municipal permit extract is not publicly served as an ArcGIS FeatureServer
  in the probed portal. Tier 3 — do not register.
* SLA / COMPLAINTS_311 — absent from the probed portal for Wilmington.
  Tier 3.

This leaf pins the DEEDS feed only. The endpoint is a best-effort URL of the
form ``https://gis.newcastlede.gov/server/rest/services/.../FeatureServer/0``
documented in PR_DESCRIPTION (US-310); the gate does not check endpoint
liveness. Re-probe the live layer within 72h of any spine change.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

WILMINGTON_DE_CITY_ID: str = "wilmington_de"

# Wilmington, DE city-parcel bbox. Anchored on the downtown core
# (39.7447 / -75.5466): south edge at the Christina River / Southbridge line
# (39.70), north edge at the Brandywine / city-limit line (39.79), west edge
# near the I-95 / Newport border (-75.62), east edge at the riverfront /
# Edgemoor line (-75.51). The metro box stays clear of Philadelphia's leaf
# box to the northeast.
WILMINGTON_DE_METRO_BBOX: dict[str, float] = {
    "min_lat": 39.70,
    "max_lat": 39.79,
    "min_lng": -75.62,
    "max_lng": -75.51,
}

# Registration-contract center: downtown Wilmington (Market St CBD).
WILMINGTON_DE_CENTER: dict[str, float] = {"lat": 39.7447, "lng": -75.5466}

# 6 Wilmington Division Bounding Boxes (strictly nested inside the metro bbox)
WILMINGTON_DE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_CORE":   {"min_lat": 39.740, "max_lat": 39.760, "min_lng": -75.560, "max_lng": -75.540},
    "RIVERFRONT":      {"min_lat": 39.730, "max_lat": 39.750, "min_lng": -75.540, "max_lng": -75.520},
    "WEST_SIDE":       {"min_lat": 39.750, "max_lat": 39.780, "min_lng": -75.600, "max_lng": -75.560},
    "NORTH_SIDE":      {"min_lat": 39.770, "max_lat": 39.790, "min_lng": -75.560, "max_lng": -75.520},
    "SOUTH_SIDE":      {"min_lat": 39.700, "max_lat": 39.730, "min_lng": -75.570, "max_lng": -75.530},
    "EAST_SIDE":       {"min_lat": 39.730, "max_lat": 39.760, "min_lng": -75.530, "max_lng": -75.510},
}


def is_in_wilmington_de_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Wilmington, DE metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        WILMINGTON_DE_METRO_BBOX["min_lat"] <= lat <= WILMINGTON_DE_METRO_BBOX["max_lat"]
        and WILMINGTON_DE_METRO_BBOX["min_lng"] <= lng <= WILMINGTON_DE_METRO_BBOX["max_lng"]
    )


def is_in_wilmington_de(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_wilmington_de_metro`."""
    return is_in_wilmington_de_metro(lat, lng)


# ---------------------------------------------------------------------------
# Wilmington, DE Submarket Registry (7 Submarkets Across 6 Divisions)
# Anchor coordinates sit inside their declared division bbox (verified against
# the metro extent above).
# ---------------------------------------------------------------------------

WILMINGTON_DE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CORE (2 Submarkets)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN_CORE",
        lat=39.7447,
        lng=-75.5466,
        zoom=15.0,
        pitch=55.0,
        base_lims=0.85,
        capex=6800000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The Market Street CBD and Rodney Square core with office-to-residential conversions, the Wilmington renaissance pipeline, and the city's densest mixed-use activity.",
        city_id="wilmington_de",
    ),
    "Little Italy": SubmarketMeta(
        name="Little Italy",
        borough="DOWNTOWN_CORE",
        lat=39.7470,
        lng=-75.5530,
        zoom=15.0,
        pitch=48.0,
        base_lims=0.81,
        capex=4900000.0,
        permit_vel=26.0,
        shift_ratio=1.40,
        sla=49.0,
        description="The Union Street corridor south of downtown with rowhouse restoration trades, trattoria-row licensing, and steady infill reinvestment.",
        city_id="wilmington_de",
    ),
    # =======================================================================
    # RIVERFRONT (1 Submarket)
    # =======================================================================
    "Riverfront": SubmarketMeta(
        name="Riverfront",
        borough="RIVERFRONT",
        lat=39.7420,
        lng=-75.5350,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.83,
        capex=6200000.0,
        permit_vel=28.0,
        shift_ratio=1.44,
        sla=54.0,
        description="The Christina Riverfront east of the CBD with the Blue Rocks ballpark, convention-hotel licensing, and the metro's highest-energy waterfront renewal.",
        city_id="wilmington_de",
    ),
    # =======================================================================
    # EAST_SIDE (1 Submarket)
    # =======================================================================
    "Trolley Square": SubmarketMeta(
        name="Trolley Square",
        borough="EAST_SIDE",
        lat=39.7580,
        lng=-75.5230,
        zoom=14.5,
        pitch=46.0,
        base_lims=0.87,
        capex=7000000.0,
        permit_vel=24.0,
        shift_ratio=1.48,
        sla=58.0,
        description="The 17th Street / Delaware Avenue edge of the East Side with 1920s apartment stock, stable owner-occupancy, and the metro's most conservation-minded renovation flow.",
        city_id="wilmington_de",
    ),
    # =======================================================================
    # WEST_SIDE (1 Submarket)
    # =======================================================================
    "Highlands": SubmarketMeta(
        name="Highlands",
        borough="WEST_SIDE",
        lat=39.7610,
        lng=-75.5780,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.78,
        capex=4600000.0,
        permit_vel=20.0,
        shift_ratio=1.38,
        sla=48.0,
        description="The West Side's Highlands grid around the Pennsylvania Avenue branch with pre-war single-family stock and block-by-block reinvestment near the city line.",
        city_id="wilmington_de",
    ),
    # =======================================================================
    # NORTH_SIDE (1 Submarket)
    # =======================================================================
    "Brandywine": SubmarketMeta(
        name="Brandywine",
        borough="NORTH_SIDE",
        lat=39.7800,
        lng=-75.5450,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.75,
        capex=4300000.0,
        permit_vel=18.0,
        shift_ratio=1.34,
        sla=46.0,
        description="The Brandywine / 10th Street north side with the hospital-edge commercial spine, Highlands spillover, and value-priced family-housing reinvestment.",
        city_id="wilmington_de",
    ),
    # =======================================================================
    # SOUTH_SIDE (1 Submarket)
    # =======================================================================
    "Southbridge": SubmarketMeta(
        name="Southbridge",
        borough="SOUTH_SIDE",
        lat=39.7150,
        lng=-75.5450,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.71,
        capex=3700000.0,
        permit_vel=17.0,
        shift_ratio=1.30,
        sla=42.0,
        description="The Christina River / Southbridge village with early-stage waterfront reinvestment, the port-adjacent industrial edge, and the metro's lowest sale prices.",
        city_id="wilmington_de",
    ),
}


# ---------------------------------------------------------------------------
# Wilmington, DE Divisions Catalog
# ---------------------------------------------------------------------------

WILMINGTON_DE_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=39.7455,
        center_lng=-75.5490,
        zoom=14.5,
        bbox=WILMINGTON_DE_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in WILMINGTON_DE_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="wilmington_de",
    ),
    "RIVERFRONT": BoroughMeta(
        name="RIVERFRONT",
        center_lat=39.7420,
        center_lng=-75.5350,
        zoom=14.0,
        bbox=WILMINGTON_DE_DIVISION_BBOXES["RIVERFRONT"],
        submarkets=[k for k, v in WILMINGTON_DE_SUBMARKETS.items() if v.borough == "RIVERFRONT"],
        city_id="wilmington_de",
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=39.7610,
        center_lng=-75.5780,
        zoom=14.0,
        bbox=WILMINGTON_DE_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in WILMINGTON_DE_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id="wilmington_de",
    ),
    "NORTH_SIDE": BoroughMeta(
        name="NORTH_SIDE",
        center_lat=39.7800,
        center_lng=-75.5450,
        zoom=14.0,
        bbox=WILMINGTON_DE_DIVISION_BBOXES["NORTH_SIDE"],
        submarkets=[k for k, v in WILMINGTON_DE_SUBMARKETS.items() if v.borough == "NORTH_SIDE"],
        city_id="wilmington_de",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=39.7150,
        center_lng=-75.5450,
        zoom=14.0,
        bbox=WILMINGTON_DE_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in WILMINGTON_DE_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="wilmington_de",
    ),
    "EAST_SIDE": BoroughMeta(
        name="EAST_SIDE",
        center_lat=39.7580,
        center_lng=-75.5230,
        zoom=14.0,
        bbox=WILMINGTON_DE_DIVISION_BBOXES["EAST_SIDE"],
        submarkets=[k for k, v in WILMINGTON_DE_SUBMARKETS.items() if v.borough == "EAST_SIDE"],
        city_id="wilmington_de",
    ),
}

WILM_DE_DIVISION_BBOXES = WILMINGTON_DE_DIVISION_BBOXES
WILM_DE_SUBMARKETS = WILMINGTON_DE_SUBMARKETS
WILM_DE_DIVISIONS = WILMINGTON_DE_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Wilmington DEEDS via New Castle County open-data ArcGIS FeatureServer.
# Native parcel polygons supply coordinates, so ADR-0004 geocode is NOT
# declared. Best-effort endpoint (US-310); re-probe the live layer within
# 72h of any spine change.
# ---------------------------------------------------------------------------
WILMINGTON_DE_DEEDS_ENDPOINT = (
    "https://gis.newcastlede.gov/server/rest/services/"
    "Parcels/Real_Estate_Sales/FeatureServer/0"
)

WILMINGTON_DE_DEEDS_FIELD_MAP = {
    "doc_id": ["PARCELID"],
    "bbl": ["PARCELID"],
    "doc_type": ["DEED_TYPE"],
    "document_amount": ["SALE_PRICE"],
    "recorded_date": ["SALE_DATE"],
    "address_street": ["SITE_ADDRESS"],
    "incident_address": ["SITE_ADDRESS"],
    "borough": ["CITY"],
    "zipcode": ["ZIP_CODE"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "deeds": WILMINGTON_DE_DEEDS_FIELD_MAP,
}

WILMINGTON_DE_FEED_SPECS: dict[str, dict[str, object]] = {
    "deeds": {
        "endpoint": WILMINGTON_DE_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "SALE_DATE",
        "id_keys": ["PARCELID", "OBJECTID"],
        "topic_key": "topic_deeds",
        "interval_seconds": 600.0,
        "producer_key": "deeds",
        "extra": {
            # Native parcel polygons (outSR=4326 rings -> centroid) supply
            # every row's coordinates; the ADR-0004 geocode hook is NOT
            # declared.
            "needs_geocode": False,
            "watermark_type": "text",
            "watermark_format": "%Y-%m-%d",
            "oid_field": "OBJECTID",
            "max_record_count": 100000,
            "ingestion_mode": "incremental",
            "expected_cadence_days": 30,
            "non_spatial": False,
            "scope": (
                "Wilmington, DE DEEDS/sales via New Castle County open-data "
                "parcel sales (native parcel polygons, NOT address-only). "
                "Best-effort endpoint (US-310); re-probe the live layer within "
                "72h of any spine change. SALE_DATE treated as TEXT "
                "%Y-%m-%d; native polygons supply coordinates so no geocode "
                "hook is declared. PARCELID/OBJECTID are the parcel keys; "
                "SALE_PRICE is the consideration and DEED_TYPE the instrument."
            ),
            "field_map": WILMINGTON_DE_DEEDS_FIELD_MAP,
        },
    },
}


def get_wilmington_de_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Wilmington, DE feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is absent
    (permits/SLA/311 are absent from the probed portal).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in WILMINGTON_DE_FEED_SPECS:
        available = ", ".join(sorted(WILMINGTON_DE_FEED_SPECS))
        raise KeyError(
            f"'{WILMINGTON_DE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = WILMINGTON_DE_FEED_SPECS[feed_name]
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
    metro_bbox=WILMINGTON_DE_METRO_BBOX,
    division_bboxes=WILMINGTON_DE_DIVISION_BBOXES,
    submarkets=WILMINGTON_DE_SUBMARKETS,
    divisions=WILMINGTON_DE_DIVISIONS,
    contains=is_in_wilmington_de_metro,
)

__all__ = [
    "FIELD_MAP",
    "REGISTRATION",
    "WILMINGTON_DE_CENTER",
    "WILMINGTON_DE_CITY_ID",
    "WILMINGTON_DE_DEEDS_ENDPOINT",
    "WILMINGTON_DE_DIVISIONS",
    "WILMINGTON_DE_DIVISION_BBOXES",
    "WILMINGTON_DE_FEED_SPECS",
    "WILMINGTON_DE_METRO_BBOX",
    "WILMINGTON_DE_SUBMARKETS",
    "WILM_DE_DIVISIONS",
    "WILM_DE_DIVISION_BBOXES",
    "WILM_DE_SUBMARKETS",
    "get_wilmington_de_dataset",
    "is_in_wilmington_de",
    "is_in_wilmington_de_metro",
]
