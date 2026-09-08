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

"""Albany Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Albany,
NY (Capital District seat on the Hudson — deliberately not overlapping the
sibling Rochester/Syracuse leaf boxes).

Feed scope (best-effort registration, 2026-09-02): Albany County's Real
Property parcels are published through the city/county ArcGIS catalog. The
DEEDS-led partial metro below carries the closest ACRIS-shape parcel/sales
feed. The endpoint is a BEST-EFFORT URL (see PR_DESCRIPTION); the interlock
gate does not probe endpoint liveness, so this registration lands the
geometry, submarkets, and producer-key wiring ahead of a verified live probe.

* DEEDS — ``Real_Property/Tax_Parcels/FeatureServer/0``. Watermark
  ``SALE_DATE`` is assumed TEXT ``MM/DD/YYYY``; if a live probe shows a
  different format, the declared ``watermark_format`` must follow. Native
  parcel polygons supply every row's coordinates, so ``needs_geocode`` stays
  False. ``producer_key='deeds'`` rides the shared ``deeds_acris_producer``.
* PERMITS / SLA / COMPLAINTS_311 — absent from the local catalog at probe
  time. Tier 3 — do not register until a live endpoint is confirmed.

Re-probe within 72 h of any spine change; replace the assumed endpoint with
the verified FeatureServer URL once the city's open-data portal resolves it.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

ALBANY_CITY_ID: str = "albany"

# City-parcel bbox around the Capital District core. SW corner ~42.62/-73.82,
# NE corner ~42.70/-73.71, the Hudson River forming the east/southeast edge.
ALBANY_METRO_BBOX: dict[str, float] = {
    "min_lat": 42.62,
    "max_lat": 42.70,
    "min_lng": -73.82,
    "max_lng": -73.71,
}

# Registration-contract center: downtown Albany (Empire State Plaza / Broadway).
ALBANY_CENTER: dict[str, float] = {"lat": 42.6526, "lng": -73.7562}

# 5 Albany Division Bounding Boxes (strictly nested inside the metro bbox)
ALBANY_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_HUDSON":  {"min_lat": 42.645, "max_lat": 42.665, "min_lng": -73.765, "max_lng": -73.750},
    "PINE_HILLS":      {"min_lat": 42.650, "max_lat": 42.672, "min_lng": -73.795, "max_lng": -73.770},
    "WESTERN_WARD":    {"min_lat": 42.625, "max_lat": 42.650, "min_lng": -73.800, "max_lng": -73.770},
    "EAST_ALBANY":     {"min_lat": 42.630, "max_lat": 42.670, "min_lng": -73.755, "max_lng": -73.720},
    "NORTH_ALBANY":    {"min_lat": 42.672, "max_lat": 42.698, "min_lng": -73.780, "max_lng": -73.740},
}


def is_in_albany_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Albany metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        ALBANY_METRO_BBOX["min_lat"] <= lat <= ALBANY_METRO_BBOX["max_lat"]
        and ALBANY_METRO_BBOX["min_lng"] <= lng <= ALBANY_METRO_BBOX["max_lng"]
    )


def is_in_albany(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_albany_metro`."""
    return is_in_albany_metro(lat, lng)


# ---------------------------------------------------------------------------
# Albany Submarket Registry (8 Submarkets Across 5 Divisions)
# ---------------------------------------------------------------------------

ALBANY_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_HUDSON (2 Submarkets)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN_HUDSON",
        lat=42.6526,
        lng=-73.7562,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.85,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.45,
        sla=56.0,
        description="The Empire State Plaza / Broadway CBD with state-office conversions, the downtown hospitality spine, and the city's densest mixed-use pipeline.",
        city_id="albany",
    ),
    "Hudson Park": SubmarketMeta(
        name="Hudson Park",
        borough="DOWNTOWN_HUDSON",
        lat=42.6560,
        lng=-73.7580,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.81,
        capex=4000000.0,
        permit_vel=23.0,
        shift_ratio=1.33,
        sla=45.0,
        description="The Hudson River bluff south of downtown with pre-war apartment houses, Washington Park-adjacent rowhousing, and steady restoration trades.",
        city_id="albany",
    ),
    # =======================================================================
    # PINE_HILLS (1 Submarket)
    # =======================================================================
    "Pine Hills": SubmarketMeta(
        name="Pine Hills",
        borough="PINE_HILLS",
        lat=42.6600,
        lng=-73.7850,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.83,
        capex=4900000.0,
        permit_vel=29.0,
        shift_ratio=1.41,
        sla=53.0,
        description="The student-dense grid west of the UAlbany downtown campus with dense rental stock, multifamily conversions, and high-turnover condo product.",
        city_id="albany",
    ),
    # =======================================================================
    # WESTERN_WARD (1 Submarket)
    # =======================================================================
    "Delaware": SubmarketMeta(
        name="Delaware",
        borough="WESTERN_WARD",
        lat=42.6400,
        lng=-73.7900,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.72,
        capex=3300000.0,
        permit_vel=21.0,
        shift_ratio=1.25,
        sla=41.0,
        description="The Delaware Avenue ward southwest of the plaza with craftsman-bungalow stock, a deep rental register, and block-by-block reinvestment.",
        city_id="albany",
    ),
    # =======================================================================
    # EAST_ALBANY (2 Submarkets)
    # =======================================================================
    "Beverwyck": SubmarketMeta(
        name="Beverwyck",
        borough="EAST_ALBANY",
        lat=42.6500,
        lng=-73.7400,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.70,
        capex=3100000.0,
        permit_vel=19.0,
        shift_ratio=1.22,
        sla=39.0,
        description="The suburban-style south-side grid toward the Bethlehem line with solid mid-century housing stock and investor renovation flow.",
        city_id="albany",
    ),
    "Buckingham": SubmarketMeta(
        name="Buckingham",
        borough="EAST_ALBANY",
        lat=42.6450,
        lng=-73.7350,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.68,
        capex=2900000.0,
        permit_vel=17.0,
        shift_ratio=1.20,
        sla=37.0,
        description="The east-side ward along New Scotland Avenue where the city's lowest sale prices meet the heaviest vacancy-to-acquisition conversion flow.",
        city_id="albany",
    ),
    # =======================================================================
    # NORTH_ALBANY (2 Submarkets)
    # =======================================================================
    "North Albany": SubmarketMeta(
        name="North Albany",
        borough="NORTH_ALBANY",
        lat=42.6850,
        lng=-73.7600,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.66,
        capex=2700000.0,
        permit_vel=16.0,
        shift_ratio=1.18,
        sla=34.0,
        description="The former industrial north ward along the Hudson and the rail yards with warehouse-to-loft conversion potential and rebuild work.",
        city_id="albany",
    ),
    "Arbor Hill": SubmarketMeta(
        name="Arbor Hill",
        borough="NORTH_ALBANY",
        lat=42.6800,
        lng=-73.7550,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.69,
        capex=3000000.0,
        permit_vel=18.0,
        shift_ratio=1.21,
        sla=38.0,
        description="The historic north-central neighborhood around Clinton Avenue with Victorian rowhouses, a deep rental register, and renewal-era reinvestment.",
        city_id="albany",
    ),
}


# ---------------------------------------------------------------------------
# Albany Divisions Catalog
# ---------------------------------------------------------------------------

ALBANY_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_HUDSON": BoroughMeta(
        name="DOWNTOWN_HUDSON",
        center_lat=42.6540,
        center_lng=-73.7570,
        zoom=13.5,
        bbox=ALBANY_DIVISION_BBOXES["DOWNTOWN_HUDSON"],
        submarkets=[k for k, v in ALBANY_SUBMARKETS.items() if v.borough == "DOWNTOWN_HUDSON"],
        city_id="albany",
    ),
    "PINE_HILLS": BoroughMeta(
        name="PINE_HILLS",
        center_lat=42.6600,
        center_lng=-73.7850,
        zoom=13.5,
        bbox=ALBANY_DIVISION_BBOXES["PINE_HILLS"],
        submarkets=[k for k, v in ALBANY_SUBMARKETS.items() if v.borough == "PINE_HILLS"],
        city_id="albany",
    ),
    "WESTERN_WARD": BoroughMeta(
        name="WESTERN_WARD",
        center_lat=42.6400,
        center_lng=-73.7900,
        zoom=13.0,
        bbox=ALBANY_DIVISION_BBOXES["WESTERN_WARD"],
        submarkets=[k for k, v in ALBANY_SUBMARKETS.items() if v.borough == "WESTERN_WARD"],
        city_id="albany",
    ),
    "EAST_ALBANY": BoroughMeta(
        name="EAST_ALBANY",
        center_lat=42.6470,
        center_lng=-73.7380,
        zoom=13.0,
        bbox=ALBANY_DIVISION_BBOXES["EAST_ALBANY"],
        submarkets=[k for k, v in ALBANY_SUBMARKETS.items() if v.borough == "EAST_ALBANY"],
        city_id="albany",
    ),
    "NORTH_ALBANY": BoroughMeta(
        name="NORTH_ALBANY",
        center_lat=42.6820,
        center_lng=-73.7580,
        zoom=13.0,
        bbox=ALBANY_DIVISION_BBOXES["NORTH_ALBANY"],
        submarkets=[k for k, v in ALBANY_SUBMARKETS.items() if v.borough == "NORTH_ALBANY"],
        city_id="albany",
    ),
}

ALB_DIVISION_BBOXES = ALBANY_DIVISION_BBOXES
ALB_SUBMARKETS = ALBANY_SUBMARKETS
ALB_DIVISIONS = ALBANY_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# ---------------------------------------------------------------------------
ALBANY_DEEDS_ENDPOINT = (
    "https://albanyny.gov/server/rest/services/Real_Property/"
    "Tax_Parcels/FeatureServer/0"
)

ALBANY_FEED_SPECS: dict[str, dict[str, object]] = {
    "deeds": {
        "endpoint": ALBANY_DEEDS_ENDPOINT,
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
                "Albany DEEDS/sales via the city/county Real Property parcels "
                "layer (best-effort endpoint; assumed TEXT MM/DD/YYYY SALE_DATE "
                "watermark, native parcel polygons, NO address-only). ENDPOINT "
                "IS A BEST-EFFORT ASSUMPTION (US-353): the city's open-data "
                "portal must be re-probed to confirm the live FeatureServer URL "
                "and watermark format before production ingest. $1 quitclaim "
                "transfers are KEPT at ingest (no per-city where; market-sale "
                "filtering is analysis-side). No owner-name columns assumed; "
                "party fields stay None. Re-probe within 72h of any spine or "
                "schedule change and replace the assumed endpoint."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_albany_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Albany feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (permits/SLA/
    311 are absent from the local catalog at probe time).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in ALBANY_FEED_SPECS:
        available = ", ".join(sorted(ALBANY_FEED_SPECS))
        raise KeyError(
            f"'{ALBANY_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = ALBANY_FEED_SPECS[feed_name]
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
    metro_bbox=ALBANY_METRO_BBOX,
    division_bboxes=ALBANY_DIVISION_BBOXES,
    submarkets=ALBANY_SUBMARKETS,
    divisions=ALBANY_DIVISIONS,
    contains=is_in_albany_metro,
)

__all__ = [
    "ALBANY_CENTER",
    "ALBANY_CITY_ID",
    "ALBANY_DEEDS_ENDPOINT",
    "ALBANY_DIVISIONS",
    "ALBANY_DIVISION_BBOXES",
    "ALBANY_FEED_SPECS",
    "ALBANY_METRO_BBOX",
    "ALBANY_SUBMARKETS",
    "ALB_DIVISIONS",
    "ALB_DIVISION_BBOXES",
    "ALB_SUBMARKETS",
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "REGISTRATION",
    "get_albany_dataset",
    "is_in_albany",
    "is_in_albany_metro",
]
