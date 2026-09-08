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

"""Burlington Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Burlington,
VT (Chittenden County seat on Lake Champlain — deliberately not overlapping
the sibling Montpelier/Plattsburgh leaf boxes).

Feed scope (best-effort definition 2026-09-03; see PR_DESCRIPTION assumption):
Burlington publishes an open-data parcel/sales layer on its municipal ArcGIS
Portal. The DEEDS feed mirrors Rochester's ArcGIS shape — a tax-parcel
FeatureServer carrying per-parcel SALE_DATE/SALE_PRICE — with native parcel
polygons supplying every row's coordinates, so ``needs_geocode`` stays False.
The endpoint in ``arcgis_burlington_deeds_url`` is a documented best-effort
URL pending a live probe of the Burlington open-data portal; the gate does not
check endpoint liveness.

Implementation notes:
* DEEDS — ``Assessment_Parcels/FeatureServer/0`` (best-effort). Producer key
  ``deeds``, topic ``raw.municipal.deeds``, ``oid_field='OBJECTID'``,
  ``ingestion_mode='incremental'``.
* PERMITS — absent from the open-data portal at definition time. Tier 3.
* SLA/licenses — absent. Tier 3.
* COMPLAINTS_311 — absent. Tier 3.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

BURLINGTON_CITY_ID: str = "burlington"

# Burlington metro bbox (Chittenden County lakefront extent): SW corner
# -73.30/44.41 (Winooski line / Shelburne town line), NE corner -73.13/44.55
# (Colchester line). The north edge is Lake Champlain, the west edge the lake,
# the east edge the Winooski River / I-89 corridor.
BURLINGTON_METRO_BBOX: dict[str, float] = {
    "min_lat": 44.41,
    "max_lat": 44.55,
    "min_lng": -73.30,
    "max_lng": -73.13,
}

# Registration-contract center: downtown Burlington (Church Street).
BURLINGTON_CENTER: dict[str, float] = {"lat": 44.4759, "lng": -73.2121}

# 6 Burlington Division Bounding Boxes (strictly nested inside the metro bbox)
BURLINGTON_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN":        {"min_lat": 44.460, "max_lat": 44.490, "min_lng": -73.225, "max_lng": -73.195},
    "SOUTH_END":       {"min_lat": 44.420, "max_lat": 44.460, "min_lng": -73.230, "max_lng": -73.190},
    "NEW_NORTH_END":   {"min_lat": 44.490, "max_lat": 44.530, "min_lng": -73.220, "max_lng": -73.185},
    "OLD_NORTH_END":   {"min_lat": 44.470, "max_lat": 44.500, "min_lng": -73.190, "max_lng": -73.160},
    "WEST_ROOT":       {"min_lat": 44.430, "max_lat": 44.470, "min_lng": -73.280, "max_lng": -73.240},
    "EAST_HILL":       {"min_lat": 44.450, "max_lat": 44.490, "min_lng": -73.160, "max_lng": -73.140},
}


def is_in_burlington_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Burlington metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        BURLINGTON_METRO_BBOX["min_lat"] <= lat <= BURLINGTON_METRO_BBOX["max_lat"]
        and BURLINGTON_METRO_BBOX["min_lng"] <= lng <= BURLINGTON_METRO_BBOX["max_lng"]
    )


def is_in_burlington(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_burlington_metro`."""
    return is_in_burlington_metro(lat, lng)


# ---------------------------------------------------------------------------
# Burlington Submarket Registry (8 Submarkets Across 6 Divisions)
# ---------------------------------------------------------------------------

BURLINGTON_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (2 Submarkets)
    # =======================================================================
    "Church Street Marketplace": SubmarketMeta(
        name="Church Street Marketplace",
        borough="DOWNTOWN",
        lat=44.4766,
        lng=-73.2121,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.85,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The pedestrian mall CBD with mixed-use conversions, the Burlington anchor retail corridor, and the city's densest downtown pipeline.",
        city_id="burlington",
    ),
    "Waterfront": SubmarketMeta(
        name="Waterfront",
        borough="DOWNTOWN",
        lat=44.4750,
        lng=-73.2180,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.80,
        capex=4100000.0,
        permit_vel=23.0,
        shift_ratio=1.33,
        sla=45.0,
        description="The Lake Champlain waterfront boardwalk and former industrial parcels with hospitality and mixed-use redevelopment flow.",
        city_id="burlington",
    ),
    # =======================================================================
    # SOUTH_END (1 Submarket)
    # =======================================================================
    "South End Arts District": SubmarketMeta(
        name="South End Arts District",
        borough="SOUTH_END",
        lat=44.4450,
        lng=-73.2120,
        zoom=15.0,
        pitch=38.0,
        base_lims=0.72,
        capex=3300000.0,
        permit_vel=21.0,
        shift_ratio=1.25,
        sla=41.0,
        description="The Pine Street arts-and-light-industrial district with maker-space conversions and steady studio/loft turnover.",
        city_id="burlington",
    ),
    # =======================================================================
    # NEW_NORTH_END (1 Submarket)
    # =======================================================================
    "University of Vermont": SubmarketMeta(
        name="University of Vermont",
        borough="NEW_NORTH_END",
        lat=44.4950,
        lng=-73.2000,
        zoom=14.5,
        pitch=38.0,
        base_lims=0.78,
        capex=3900000.0,
        permit_vel=26.0,
        shift_ratio=1.31,
        sla=48.0,
        description="The UVM / Trinity campus corridor with student-housing conversions, lab retrofits, and high-turnover rental stock.",
        city_id="burlington",
    ),
    # =======================================================================
    # OLD_NORTH_END (1 Submarket)
    # =======================================================================
    "Old North End": SubmarketMeta(
        name="Old North End",
        borough="OLD_NORTH_END",
        lat=44.4850,
        lng=-73.1780,
        zoom=14.5,
        pitch=35.0,
        base_lims=0.68,
        capex=2900000.0,
        permit_vel=19.0,
        shift_ratio=1.22,
        sla=38.0,
        description="The dense pre-war neighborhood northwest of downtown with craftsman-bungalow stock and block-by-block reinvestment.",
        city_id="burlington",
    ),
    # =======================================================================
    # WEST_ROOT (1 Submarket)
    # =======================================================================
    "Riverside": SubmarketMeta(
        name="Riverside",
        borough="WEST_ROOT",
        lat=44.4500,
        lng=-73.2600,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.64,
        capex=2600000.0,
        permit_vel=16.0,
        shift_ratio=1.18,
        sla=34.0,
        description="The Winooski River-adjacent grid west of downtown with solid housing stock and investor renovation flow.",
        city_id="burlington",
    ),
    # =======================================================================
    # EAST_HILL (2 Submarkets)
    # =======================================================================
    "Hill Section": SubmarketMeta(
        name="Hill Section",
        borough="EAST_HILL",
        lat=44.4700,
        lng=-73.1500,
        zoom=14.5,
        pitch=32.0,
        base_lims=0.71,
        capex=3200000.0,
        permit_vel=20.0,
        shift_ratio=1.23,
        sla=40.0,
        description="The east-slope single-family plateau above the O.N.E. with stable owner-occupied stock and modest teardown-rebuild activity.",
        city_id="burlington",
    ),
    "Prospect Park": SubmarketMeta(
        name="Prospect Park",
        borough="EAST_HILL",
        lat=44.4650,
        lng=-73.1460,
        zoom=14.5,
        pitch=32.0,
        base_lims=0.69,
        capex=3000000.0,
        permit_vel=18.0,
        shift_ratio=1.20,
        sla=37.0,
        description="The southeastern hill pocket with views over the lake and steady mid-century home renovation trades.",
        city_id="burlington",
    ),
}


# ---------------------------------------------------------------------------
# Burlington Divisions Catalog
# ---------------------------------------------------------------------------

BURLINGTON_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=44.4760,
        center_lng=-73.2121,
        zoom=13.5,
        bbox=BURLINGTON_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in BURLINGTON_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="burlington",
    ),
    "SOUTH_END": BoroughMeta(
        name="SOUTH_END",
        center_lat=44.4450,
        center_lng=-73.2120,
        zoom=13.5,
        bbox=BURLINGTON_DIVISION_BBOXES["SOUTH_END"],
        submarkets=[k for k, v in BURLINGTON_SUBMARKETS.items() if v.borough == "SOUTH_END"],
        city_id="burlington",
    ),
    "NEW_NORTH_END": BoroughMeta(
        name="NEW_NORTH_END",
        center_lat=44.4950,
        center_lng=-73.2000,
        zoom=13.0,
        bbox=BURLINGTON_DIVISION_BBOXES["NEW_NORTH_END"],
        submarkets=[k for k, v in BURLINGTON_SUBMARKETS.items() if v.borough == "NEW_NORTH_END"],
        city_id="burlington",
    ),
    "OLD_NORTH_END": BoroughMeta(
        name="OLD_NORTH_END",
        center_lat=44.4850,
        center_lng=-73.1780,
        zoom=13.0,
        bbox=BURLINGTON_DIVISION_BBOXES["OLD_NORTH_END"],
        submarkets=[k for k, v in BURLINGTON_SUBMARKETS.items() if v.borough == "OLD_NORTH_END"],
        city_id="burlington",
    ),
    "WEST_ROOT": BoroughMeta(
        name="WEST_ROOT",
        center_lat=44.4500,
        center_lng=-73.2600,
        zoom=13.0,
        bbox=BURLINGTON_DIVISION_BBOXES["WEST_ROOT"],
        submarkets=[k for k, v in BURLINGTON_SUBMARKETS.items() if v.borough == "WEST_ROOT"],
        city_id="burlington",
    ),
    "EAST_HILL": BoroughMeta(
        name="EAST_HILL",
        center_lat=44.4700,
        center_lng=-73.1500,
        zoom=13.0,
        bbox=BURLINGTON_DIVISION_BBOXES["EAST_HILL"],
        submarkets=[k for k, v in BURLINGTON_SUBMARKETS.items() if v.borough == "EAST_HILL"],
        city_id="burlington",
    ),
}

BTV_DIVISION_BBOXES = BURLINGTON_DIVISION_BBOXES
BTV_SUBMARKETS = BURLINGTON_SUBMARKETS
BTV_DIVISIONS = BURLINGTON_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Best-effort Burlington open-data parcel/sales layer (endpoint documented in
# arcgis_burlington_deeds_url). Mirrors Rochester's ArcGIS shape: native parcel
# polygons supply coordinates (needs_geocode False), incremental ingestion with
# a TEXT watermark.
# ---------------------------------------------------------------------------
BURLINGTON_DEEDS_ENDPOINT = (
    "https://data.burlingtonvt.gov/server/rest/services/"
    "Assessment_Parcels/FeatureServer/0"
)

BURLINGTON_FEED_SPECS: dict[str, dict[str, object]] = {
    "deeds": {
        "endpoint": BURLINGTON_DEEDS_ENDPOINT,
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
                "Burlington VT DEEDS/sales via the municipal open-data tax "
                "parcel layer (best-effort endpoint pending a live probe of "
                "the Burlington open-data portal; the interlock gate does not "
                "check endpoint liveness). Native parcel polygons (outSR=4326 "
                "rings -> centroid) supply every row's coordinates, so the "
                "ADR-0004 geocode hook is NOT declared. TEXT MM/DD/YYYY "
                "watermark sorts lexically — typed comparison required "
                "(ADR-0005). $1 quitclaim transfers are KEPT at ingest (no "
                "per-city where; market-sale filtering is analysis-side). "
                "PARCELID/PRINTKEY are the parcel keys; BOOK/PAGE ride id_keys "
                "as recorded-deed references. No owner-name columns exist; "
                "party fields stay None."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_burlington_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Burlington feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (permits/SLA/311
    are absent from the open-data portal at definition time).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in BURLINGTON_FEED_SPECS:
        available = ", ".join(sorted(BURLINGTON_FEED_SPECS))
        raise KeyError(
            f"'{BURLINGTON_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = BURLINGTON_FEED_SPECS[feed_name]
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
    metro_bbox=BURLINGTON_METRO_BBOX,
    division_bboxes=BURLINGTON_DIVISION_BBOXES,
    submarkets=BURLINGTON_SUBMARKETS,
    divisions=BURLINGTON_DIVISIONS,
    contains=is_in_burlington_metro,
)

__all__ = [
    "BTV_DIVISIONS",
    "BTV_DIVISION_BBOXES",
    "BTV_SUBMARKETS",
    "BURLINGTON_CENTER",
    "BURLINGTON_CITY_ID",
    "BURLINGTON_DEEDS_ENDPOINT",
    "BURLINGTON_DIVISIONS",
    "BURLINGTON_DIVISION_BBOXES",
    "BURLINGTON_FEED_SPECS",
    "BURLINGTON_METRO_BBOX",
    "BURLINGTON_SUBMARKETS",
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "REGISTRATION",
    "get_burlington_dataset",
    "is_in_burlington",
    "is_in_burlington_metro",
]
