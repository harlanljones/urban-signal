DEEDS_FIELD_MAP = {
    "doc_id": ["PARCELID", "OBJECTID"],
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

"""Charleston, WV Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Charleston,
WV (Kanawha County seat on the Kanawha River — deliberately nested inside the
Kanawha Valley corridor, not overlapping the sibling Charleston SC leaf box).

Feed scope (best-effort, 2026-08-28; endpoint not live-probed): Charleston,
WV publishes an open-data parcel FeatureServer (``Charleston_Parcels`` on the
services8.arcgis.com AGOL org). The live attribute schema (sale-date /
sale-price / deed-type columns, native parcel polygon availability) is not yet
confirmed, so the DEEDS feed below mirrors the Rochester ACRIS-shape contract
as the working hypothesis:

* DEEDS — ``Charleston_Parcels/FeatureServer/0``. Assumed TEXT ``SALE_DATE``
  watermark and native parcel polygons (``needs_geocode=False``). The exact
  watermark format and id keys should be re-probed against the live layer once
  the producer is wired; the field map is a best-effort placeholder.

NOTE: this is a DEEDS-led partial metro (no permits/SLA/311 datasets confirmed
for the Charleston WV open-data portal at implementation time). Tier 3 feeds
are intentionally omitted per the partial-registration rule. Re-probe the live
layer before promoting any downstream consumer.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

CHARLESTON_WV_CITY_ID: str = "charleston_wv"

# City-parcel bbox around downtown Charleston, WV (Kanawha River bend near the
# Capitol Complex). Bounds chosen to contain every declared division box and
# the registration center (38.3498, -81.6326) without spilling into the
# sibling Charleston SC leaf box.
CHARLESTON_WV_METRO_BBOX: dict[str, float] = {
    "min_lat": 38.32,
    "max_lat": 38.38,
    "min_lng": -81.68,
    "max_lng": -81.58,
}

# Registration-contract center: downtown Charleston (Kanawha Blvd / Capitol St).
CHARLESTON_WV_CENTER: dict[str, float] = {"lat": 38.3498, "lng": -81.6326}

# 5 Charleston, WV Division Bounding Boxes (strictly nested inside the metro bbox)
CHARLESTON_WV_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_KANAWHA": {"min_lat": 38.345, "max_lat": 38.365, "min_lng": -81.650, "max_lng": -81.615},
    "EAST_END":         {"min_lat": 38.340, "max_lat": 38.360, "min_lng": -81.615, "max_lng": -81.585},
    "WEST_SIDE":        {"min_lat": 38.345, "max_lat": 38.365, "min_lng": -81.680, "max_lng": -81.650},
    "SOUTH_RIDGE":      {"min_lat": 38.320, "max_lat": 38.345, "min_lng": -81.650, "max_lng": -81.610},
    "NORTH_PARK":       {"min_lat": 38.360, "max_lat": 38.380, "min_lng": -81.660, "max_lng": -81.620},
}


def is_in_charleston_wv_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Charleston WV metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        CHARLESTON_WV_METRO_BBOX["min_lat"] <= lat <= CHARLESTON_WV_METRO_BBOX["max_lat"]
        and CHARLESTON_WV_METRO_BBOX["min_lng"] <= lng <= CHARLESTON_WV_METRO_BBOX["max_lng"]
    )


def is_in_charleston_wv(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_charleston_wv_metro`."""
    return is_in_charleston_wv_metro(lat, lng)


# ---------------------------------------------------------------------------
# Charleston, WV Submarket Registry (7 Submarkets Across 5 Divisions)
# Anchor coordinates are within their declared division boxes; lat/lng chosen
# around the Kanawha River corridor through Charleston, WV.
# ---------------------------------------------------------------------------

CHARLESTON_WV_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_KANAWHA (2 Submarkets)
    # =======================================================================
    "Downtown Charleston": SubmarketMeta(
        name="Downtown Charleston",
        borough="DOWNTOWN_KANAWHA",
        lat=38.3498,
        lng=-81.6326,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.84,
        capex=5200000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=52.0,
        description="The Capitol Complex / Kanawha Blvd CBD with state-office conversions, the core mixed-use pipeline, and the city's densest reinvestment corridor.",
        city_id="charleston_wv",
    ),
    "Capitol Market": SubmarketMeta(
        name="Capitol Market",
        borough="DOWNTOWN_KANAWHA",
        lat=38.3530,
        lng=-81.6180,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.80,
        capex=4000000.0,
        permit_vel=22.0,
        shift_ratio=1.32,
        sla=44.0,
        description="The market-district grid northeast of downtown with food-hall retail, loft conversions, and steady small-business licensing flow.",
        city_id="charleston_wv",
    ),
    # =======================================================================
    # EAST_END (2 Submarkets)
    # =======================================================================
    "East End": SubmarketMeta(
        name="East End",
        borough="EAST_END",
        lat=38.3500,
        lng=-81.6000,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.78,
        capex=3800000.0,
        permit_vel=20.0,
        shift_ratio=1.30,
        sla=42.0,
        description="The historic East End neighborhood east of downtown with restoration trades, the arts-corridor retrofit pipeline, and investor housing stock.",
        city_id="charleston_wv",
    ),
    "Kanawha City": SubmarketMeta(
        name="Kanawha City",
        borough="EAST_END",
        lat=38.3450,
        lng=-81.5950,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.72,
        capex=3300000.0,
        permit_vel=18.0,
        shift_ratio=1.25,
        sla=38.0,
        description="The southeast river-front neighborhood along MacCorkle Avenue with solid mid-century housing stock and block-by-block reinvestment.",
        city_id="charleston_wv",
    ),
    # =======================================================================
    # WEST_SIDE (1 Submarket)
    # =======================================================================
    "West Side": SubmarketMeta(
        name="West Side",
        borough="WEST_SIDE",
        lat=38.3550,
        lng=-81.6650,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.70,
        capex=3100000.0,
        permit_vel=18.0,
        shift_ratio=1.23,
        sla=37.0,
        description="The west-bank grid across the Kanawha River with pre-war housing, the city's lowest sale prices, and heaviest vacancy-to-acquisition flow.",
        city_id="charleston_wv",
    ),
    # =======================================================================
    # SOUTH_RIDGE (1 Submarket)
    # =======================================================================
    "South Hills": SubmarketMeta(
        name="South Hills",
        borough="SOUTH_RIDGE",
        lat=38.3350,
        lng=-81.6300,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.74,
        capex=3500000.0,
        permit_vel=20.0,
        shift_ratio=1.26,
        sla=40.0,
        description="The south-bank ridge neighborhoods along the Kanawha with commuter-adjacent housing and steady renovation trades.",
        city_id="charleston_wv",
    ),
    # =======================================================================
    # NORTH_PARK (1 Submarket)
    # =======================================================================
    "North Charleston": SubmarketMeta(
        name="North Charleston",
        borough="NORTH_PARK",
        lat=38.3700,
        lng=-81.6400,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.68,
        capex=2900000.0,
        permit_vel=16.0,
        shift_ratio=1.20,
        sla=36.0,
        description="The north-bank ward toward the I-64 corridor with lighter sale volume and investor acquisition interest at the metro edge.",
        city_id="charleston_wv",
    ),
}


# ---------------------------------------------------------------------------
# Charleston, WV Divisions Catalog
# ---------------------------------------------------------------------------

CHARLESTON_WV_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_KANAWHA": BoroughMeta(
        name="DOWNTOWN_KANAWHA",
        center_lat=38.3514,
        center_lng=-81.6253,
        zoom=13.5,
        bbox=CHARLESTON_WV_DIVISION_BBOXES["DOWNTOWN_KANAWHA"],
        submarkets=[k for k, v in CHARLESTON_WV_SUBMARKETS.items() if v.borough == "DOWNTOWN_KANAWHA"],
        city_id="charleston_wv",
    ),
    "EAST_END": BoroughMeta(
        name="EAST_END",
        center_lat=38.3475,
        center_lng=-81.5975,
        zoom=13.5,
        bbox=CHARLESTON_WV_DIVISION_BBOXES["EAST_END"],
        submarkets=[k for k, v in CHARLESTON_WV_SUBMARKETS.items() if v.borough == "EAST_END"],
        city_id="charleston_wv",
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=38.3550,
        center_lng=-81.6650,
        zoom=13.0,
        bbox=CHARLESTON_WV_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in CHARLESTON_WV_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id="charleston_wv",
    ),
    "SOUTH_RIDGE": BoroughMeta(
        name="SOUTH_RIDGE",
        center_lat=38.3325,
        center_lng=-81.6300,
        zoom=13.0,
        bbox=CHARLESTON_WV_DIVISION_BBOXES["SOUTH_RIDGE"],
        submarkets=[k for k, v in CHARLESTON_WV_SUBMARKETS.items() if v.borough == "SOUTH_RIDGE"],
        city_id="charleston_wv",
    ),
    "NORTH_PARK": BoroughMeta(
        name="NORTH_PARK",
        center_lat=38.3650,
        center_lng=-81.6400,
        zoom=13.0,
        bbox=CHARLESTON_WV_DIVISION_BBOXES["NORTH_PARK"],
        submarkets=[k for k, v in CHARLESTON_WV_SUBMARKETS.items() if v.borough == "NORTH_PARK"],
        city_id="charleston_wv",
    ),
}

CWV_DIVISION_BBOXES = CHARLESTON_WV_DIVISION_BBOXES
CWV_SUBMARKETS = CHARLESTON_WV_SUBMARKETS
CWV_DIVISIONS = CHARLESTON_WV_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Best-effort DEEDS contract mirroring the Rochester ACRIS-shape pattern; the
# live Charleston_Parcels attribute schema is not yet confirmed (see module
# docstring). Endpoint is a real AGOL FeatureServer published by the City of
# Charleston, WV. Re-probe before promoting downstream consumers.
# ---------------------------------------------------------------------------
CHARLESTON_WV_DEEDS_ENDPOINT = (
    "https://services8.arcgis.com/0zSnoqwLCR3i1Yfw/arcgis/rest/services/"
    "Charleston_Parcels/FeatureServer/0"
)

CHARLESTON_WV_FEED_SPECS: dict[str, dict[str, object]] = {
    "deeds": {
        "endpoint": CHARLESTON_WV_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "SALE_DATE",
        "id_keys": ["PARCELID", "OBJECTID", "SALE_DATE"],
        "topic_key": "topic_deeds",
        "interval_seconds": 600.0,
        "producer_key": "deeds",
        "extra": {
            # Native parcel polygons assumed to supply row coordinates; the
            # ADR-0004 geocode hook is NOT declared until the live layer is
            # confirmed to carry geometry. SALE_DATE assumed TEXT; the exact
            # watermark format must be re-probed against the live layer.
            "needs_geocode": False,
            "watermark_type": "text",
            "watermark_format": "%m/%d/%Y",
            "oid_field": "OBJECTID",
            "max_record_count": 100000,
            "expected_cadence_days": 30,
            "non_spatial": False,
            "scope": (
                "Charleston WV DEEDS/sales via the City of Charleston, WV open-data "
                "Charleston_Parcels FeatureServer (services8.arcgis.com AGOL org; "
                "endpoint real, attribute schema UNCONFIRMED at implementation). "
                "Mirrors the Rochester ACRIS-shape contract as a working hypothesis: "
                "TEXT SALE_DATE watermark, native parcel polygons (no ADR-0004 "
                "geocode hook declared yet), PARCELID/OBJECTID id keys. Re-probe the "
                "live layer to confirm watermark format and field names before "
                "promoting any downstream consumer. No permits/SLA/311 datasets are "
                "confirmed for the Charleston WV open-data portal (Tier 3 omitted)."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_charleston_wv_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Charleston WV feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (permits/SLA/
    311 are not yet registered for Charleston WV).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in CHARLESTON_WV_FEED_SPECS:
        available = ", ".join(sorted(CHARLESTON_WV_FEED_SPECS))
        raise KeyError(
            f"'{CHARLESTON_WV_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = CHARLESTON_WV_FEED_SPECS[feed_name]
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
    metro_bbox=CHARLESTON_WV_METRO_BBOX,
    division_bboxes=CHARLESTON_WV_DIVISION_BBOXES,
    submarkets=CHARLESTON_WV_SUBMARKETS,
    divisions=CHARLESTON_WV_DIVISIONS,
    contains=is_in_charleston_wv_metro,
)

__all__ = [
    "CHARLESTON_WV_CENTER",
    "CHARLESTON_WV_CITY_ID",
    "CHARLESTON_WV_DEEDS_ENDPOINT",
    "CHARLESTON_WV_DIVISIONS",
    "CHARLESTON_WV_DIVISION_BBOXES",
    "CHARLESTON_WV_FEED_SPECS",
    "CHARLESTON_WV_METRO_BBOX",
    "CHARLESTON_WV_SUBMARKETS",
    "CWV_DIVISIONS",
    "CWV_DIVISION_BBOXES",
    "CWV_SUBMARKETS",
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "REGISTRATION",
    "get_charleston_wv_dataset",
    "is_in_charleston_wv",
    "is_in_charleston_wv_metro",
]
