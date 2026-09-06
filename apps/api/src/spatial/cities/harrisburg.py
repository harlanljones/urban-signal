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

"""Harrisburg Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Harrisburg,
PA (the state capital, on the Susquehanna River in Dauphin County — the
sibling Lancaster/York leaf boxes sit east/southeast and must stay clear of
this box).

Feed scope (US-311, registered 2026-09 without a live municipal probe;
endpoint is a documented best-effort ArcGIS FeatureServer URL per the
onboarding SOP — liveness is unverified). Harrisburg is a DEEDS-led partial
metro: the city's open-data property/sales layer is expected to carry
per-parcel ``SALE_DATE``/``SALE_PRICE``/``BOOK``/``PAGE``/``DEED_TYPE`` in the
ADR-0005 text-watermark shape. Re-probe once a live layer is confirmed.

* DEEDS — ``open_data/Property_Sales/FeatureServer/0``. Text ``SALE_DATE`` is
  the watermark (``%m/%d/%Y``); ``needs_geocode=False`` pending a confirmed
  native-parcel geometry probe. Producer key ``deeds`` resolves uniquely via
  ``job_suffix="harrisburg"``.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

HARRISBURG_CITY_ID: str = "harrisburg"

# City-parcel bbox around the Harrisburg metro (center 40.2732/-76.8867): SW
# approx 40.22/-76.94, NE approx 40.32/-76.83. The west edge is the
# Susquehanna River; the east edge the Blue Mountain foothills. Lancaster and
# York sit outside this box and must stay out.
HARRISBURG_METRO_BBOX: dict[str, float] = {
    "min_lat": 40.22,
    "max_lat": 40.32,
    "min_lng": -76.94,
    "max_lng": -76.83,
}

# Registration-contract center: downtown Harrisburg (State Capitol area).
HARRISBURG_CENTER: dict[str, float] = {"lat": 40.2732, "lng": -76.8867}

# 6 Harrisburg Division Bounding Boxes (strictly nested inside the metro bbox)
HARRISBURG_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_CAPITOL":  {"min_lat": 40.255, "max_lat": 40.290, "min_lng": -76.905, "max_lng": -76.875},
    "RIVERFRONT_EAST":   {"min_lat": 40.250, "max_lat": 40.285, "min_lng": -76.890, "max_lng": -76.855},
    "NORTH_SUSQUEHANNA": {"min_lat": 40.290, "max_lat": 40.320, "min_lng": -76.900, "max_lng": -76.860},
    "SOUTH_SIDE":        {"min_lat": 40.220, "max_lat": 40.255, "min_lng": -76.900, "max_lng": -76.860},
    "EAST_SHORE":        {"min_lat": 40.240, "max_lat": 40.280, "min_lng": -76.870, "max_lng": -76.835},
    "WEST_ENOLA":        {"min_lat": 40.240, "max_lat": 40.275, "min_lng": -76.938, "max_lng": -76.905},
}


def is_in_harrisburg_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Harrisburg metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        HARRISBURG_METRO_BBOX["min_lat"] <= lat <= HARRISBURG_METRO_BBOX["max_lat"]
        and HARRISBURG_METRO_BBOX["min_lng"] <= lng <= HARRISBURG_METRO_BBOX["max_lng"]
    )


def is_in_harrisburg(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_harrisburg_metro`."""
    return is_in_harrisburg_metro(lat, lng)


# ---------------------------------------------------------------------------
# Harrisburg Submarket Registry (7 Submarkets Across 6 Divisions)
# ---------------------------------------------------------------------------

HARRISBURG_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CAPITOL (1 Submarket)
    # =======================================================================
    "Capitol District": SubmarketMeta(
        name="Capitol District",
        borough="DOWNTOWN_CAPITOL",
        lat=40.2650,
        lng=-76.8850,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.85,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The State Capitol complex and downtown office core with adaptive-reuse conversions and the densest mixed-use pipeline in the metro.",
        city_id="harrisburg",
    ),
    # =======================================================================
    # RIVERFRONT_EAST (1 Submarket)
    # =======================================================================
    "Riverfront East": SubmarketMeta(
        name="Riverfront East",
        borough="RIVERFRONT_EAST",
        lat=40.2620,
        lng=-76.8750,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.82,
        capex=4400000.0,
        permit_vel=26.0,
        shift_ratio=1.36,
        sla=48.0,
        description="The Susquehanna riverfront east of downtown with marina-adjacent hospitality licensing and steady townhome reinvestment.",
        city_id="harrisburg",
    ),
    # =======================================================================
    # NORTH_SUSQUEHANNA (1 Submarket)
    # =======================================================================
    "Uptown Harrisburg": SubmarketMeta(
        name="Uptown Harrisburg",
        borough="NORTH_SUSQUEHANNA",
        lat=40.2980,
        lng=-76.8850,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.74,
        capex=3500000.0,
        permit_vel=22.0,
        shift_ratio=1.28,
        sla=42.0,
        description="The north-central grid above the Capitol with pre-war housing stock and investor renovation flow along the Susquehanna bluff.",
        city_id="harrisburg",
    ),
    # =======================================================================
    # SOUTH_SIDE (1 Submarket)
    # =======================================================================
    "South Harrisburg": SubmarketMeta(
        name="South Harrisburg",
        borough="SOUTH_SIDE",
        lat=40.2350,
        lng=-76.8800,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.70,
        capex=3100000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=40.0,
        description="The South Side ward south of the Capitol with craftsman-bungalow stock, a deep rental register, and block-by-block reinvestment.",
        city_id="harrisburg",
    ),
    # =======================================================================
    # EAST_SHORE (2 Submarkets)
    # =======================================================================
    "Allison Hill": SubmarketMeta(
        name="Allison Hill",
        borough="EAST_SHORE",
        lat=40.2580,
        lng=-76.8550,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.68,
        capex=2900000.0,
        permit_vel=18.0,
        shift_ratio=1.22,
        sla=38.0,
        description="The East Shore hill neighborhood with the metro's most active block-level acquisition and the heaviest vacancy-to-rehab conversion flow.",
        city_id="harrisburg",
    ),
    "Bellevue Park": SubmarketMeta(
        name="Bellevue Park",
        borough="EAST_SHORE",
        lat=40.2680,
        lng=-76.8480,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.72,
        capex=3300000.0,
        permit_vel=21.0,
        shift_ratio=1.26,
        sla=41.0,
        description="The eastern garden-suburb grid off Paxton Street with solid early-20th-century stock and steady owner-occupier demand.",
        city_id="harrisburg",
    ),
    # =======================================================================
    # WEST_ENOLA (1 Submarket)
    # =======================================================================
    "West Shore Enola": SubmarketMeta(
        name="West Shore Enola",
        borough="WEST_ENOLA",
        lat=40.2580,
        lng=-76.9250,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.66,
        capex=2700000.0,
        permit_vel=16.0,
        shift_ratio=1.18,
        sla=34.0,
        description="The Cumberland County shore across the river at Enola with commuter-served suburban turnover and rail-adjacent redevelopment.",
        city_id="harrisburg",
    ),
}


# ---------------------------------------------------------------------------
# Harrisburg Divisions Catalog
# ---------------------------------------------------------------------------

HARRISBURG_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_CAPITOL": BoroughMeta(
        name="DOWNTOWN_CAPITOL",
        center_lat=40.2650,
        center_lng=-76.8850,
        zoom=13.5,
        bbox=HARRISBURG_DIVISION_BBOXES["DOWNTOWN_CAPITOL"],
        submarkets=[k for k, v in HARRISBURG_SUBMARKETS.items() if v.borough == "DOWNTOWN_CAPITOL"],
        city_id="harrisburg",
    ),
    "RIVERFRONT_EAST": BoroughMeta(
        name="RIVERFRONT_EAST",
        center_lat=40.2620,
        center_lng=-76.8750,
        zoom=13.5,
        bbox=HARRISBURG_DIVISION_BBOXES["RIVERFRONT_EAST"],
        submarkets=[k for k, v in HARRISBURG_SUBMARKETS.items() if v.borough == "RIVERFRONT_EAST"],
        city_id="harrisburg",
    ),
    "NORTH_SUSQUEHANNA": BoroughMeta(
        name="NORTH_SUSQUEHANNA",
        center_lat=40.2980,
        center_lng=-76.8850,
        zoom=13.0,
        bbox=HARRISBURG_DIVISION_BBOXES["NORTH_SUSQUEHANNA"],
        submarkets=[k for k, v in HARRISBURG_SUBMARKETS.items() if v.borough == "NORTH_SUSQUEHANNA"],
        city_id="harrisburg",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=40.2350,
        center_lng=-76.8800,
        zoom=13.0,
        bbox=HARRISBURG_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in HARRISBURG_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="harrisburg",
    ),
    "EAST_SHORE": BoroughMeta(
        name="EAST_SHORE",
        center_lat=40.2630,
        center_lng=-76.8520,
        zoom=13.0,
        bbox=HARRISBURG_DIVISION_BBOXES["EAST_SHORE"],
        submarkets=[k for k, v in HARRISBURG_SUBMARKETS.items() if v.borough == "EAST_SHORE"],
        city_id="harrisburg",
    ),
    "WEST_ENOLA": BoroughMeta(
        name="WEST_ENOLA",
        center_lat=40.2580,
        center_lng=-76.9250,
        zoom=13.0,
        bbox=HARRISBURG_DIVISION_BBOXES["WEST_ENOLA"],
        submarkets=[k for k, v in HARRISBURG_SUBMARKETS.items() if v.borough == "WEST_ENOLA"],
        city_id="harrisburg",
    ),
}

HBG_DIVISION_BBOXES = HARRISBURG_DIVISION_BBOXES
HBG_SUBMARKETS = HARRISBURG_SUBMARKETS
HBG_DIVISIONS = HARRISBURG_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Best-effort endpoint (US-311): no live municipal open-data probe was
# performed; validate the FeatureServer layer before production ingest.
# ---------------------------------------------------------------------------
HARRISBURG_DEEDS_ENDPOINT = (
    "https://harrisburgpa.gov/server/rest/services/"
    "open_data/Property_Sales/FeatureServer/0"
)

HARRISBURG_FEED_SPECS: dict[str, dict[str, object]] = {
    "deeds": {
        "endpoint": HARRISBURG_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "SALE_DATE",
        "id_keys": ["PARCELID", "PRINTKEY", "SALE_DATE"],
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
                "Harrisburg DEEDS/sales via the city open-data Property_Sales "
                "layer (best-effort endpoint — live layer unverified at "
                "registration; re-probe before production ingest). TEXT "
                "MM/DD/YYYY watermark sorts lexically — typed comparison "
                "required (ADR-0005). $1 quitclaim transfers KEPT at ingest "
                "(no per-city where). No owner-name columns expected; party "
                "fields stay None. BOOK/PAGE ride id_keys as recorded-deed "
                "references; PARCELID/PRINTKEY are the parcel keys."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_harrisburg_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Harrisburg feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (permits/SLA/
    311 are absent at registration).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in HARRISBURG_FEED_SPECS:
        available = ", ".join(sorted(HARRISBURG_FEED_SPECS))
        raise KeyError(
            f"'{HARRISBURG_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = HARRISBURG_FEED_SPECS[feed_name]
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
    metro_bbox=HARRISBURG_METRO_BBOX,
    division_bboxes=HARRISBURG_DIVISION_BBOXES,
    submarkets=HARRISBURG_SUBMARKETS,
    divisions=HARRISBURG_DIVISIONS,
    contains=is_in_harrisburg_metro,
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "HARRISBURG_CENTER",
    "HARRISBURG_CITY_ID",
    "HARRISBURG_DEEDS_ENDPOINT",
    "HARRISBURG_DIVISIONS",
    "HARRISBURG_DIVISION_BBOXES",
    "HARRISBURG_FEED_SPECS",
    "HARRISBURG_METRO_BBOX",
    "HARRISBURG_SUBMARKETS",
    "HBG_DIVISIONS",
    "HBG_DIVISION_BBOXES",
    "HBG_SUBMARKETS",
    "REGISTRATION",
    "get_harrisburg_dataset",
    "is_in_harrisburg",
    "is_in_harrisburg_metro",
]
