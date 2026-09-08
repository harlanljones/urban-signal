DEEDS_FIELD_MAP = {
    "doc_id": ["PARCELID"],
    "bbl": ["PARCELID"],
    "doc_type": ["SALE_TYPE"],
    "document_amount": ["SALE_PRICE"],
    "recorded_date": ["SALE_DATE"],
    "address_street": ["SITEADDRESS"],
    "incident_address": ["SITEADDRESS"],
    "borough": ["CITY"],
    "zipcode": ["ZIPCODE"],
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

"""Frederick Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Frederick,
MD (county seat of Frederick County, at the foot of the Catoctin Mountains
— deliberately not overlapping the sibling Baltimore/Washington leaf boxes).

Feed scope (probed 2026-09-03; best-effort endpoint documented in
PR_DESCRIPTION): Frederick County publishes its parcel roll as the
``Frederick_Parcels`` FeatureServer (AGOL org X3lKekbdaBmNjCHu), a native
polygon layer carrying per-parcel sale attributes. The deeds registration
reuses the parcel layer's sale columns as the arms-length transfer signal —
the closest ACRIS-shape feed Frederick has. The endpoint is a documented
best-effort URL; liveness is not enforced by the interlock gate.

* DEEDS — ``Frederick_Parcels`` FeatureServer layer 3. Native parcel
  polygons (``outSR=4326`` rings → centroid) supply every row's
  coordinates, so ``needs_geocode`` stays False — no ADR-0004 hook.
* PERMITS / SLA / 311 — absent from the public Frederick open-data surface;
  Tier 3, not registered.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

FREDERICK_CITY_ID: str = "frederick"

# Frederick metro bbox around the provided center (39.4143 / -77.4105). The
# north edge approaches the Catoctin foothills, the south edge the Monocacy
# River, the west edge the Middletown Valley, the east edge the Liberty
# Reservoir watershed — all kept clear of the Baltimore/Washington boxes.
FREDERICK_METRO_BBOX: dict[str, float] = {
    "min_lat": 39.35,
    "max_lat": 39.48,
    "min_lng": -77.47,
    "max_lng": -77.37,
}

# Registration-contract center: downtown Frederick (Carroll Creek / Market St).
FREDERICK_CENTER: dict[str, float] = {"lat": 39.4143, "lng": -77.4105}

# 5 Frederick Division Bounding Boxes (strictly nested inside the metro bbox)
FREDERICK_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_HISTORIC": {"min_lat": 39.40, "max_lat": 39.425, "min_lng": -77.425, "max_lng": -77.405},
    "NORTH_MARKET":     {"min_lat": 39.425, "max_lat": 39.46, "min_lng": -77.430, "max_lng": -77.400},
    "SOUTH_CREEK":      {"min_lat": 39.36, "max_lat": 39.40, "min_lng": -77.430, "max_lng": -77.400},
    "WEST_RIDGE":       {"min_lat": 39.39, "max_lat": 39.45, "min_lng": -77.470, "max_lng": -77.430},
    "EAST_GATE":        {"min_lat": 39.39, "max_lat": 39.45, "min_lng": -77.400, "max_lng": -77.370},
}


def is_in_frederick_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Frederick metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        FREDERICK_METRO_BBOX["min_lat"] <= lat <= FREDERICK_METRO_BBOX["max_lat"]
        and FREDERICK_METRO_BBOX["min_lng"] <= lng <= FREDERICK_METRO_BBOX["max_lng"]
    )


def is_in_frederick(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_frederick_metro`."""
    return is_in_frederick_metro(lat, lng)


# ---------------------------------------------------------------------------
# Frederick Submarket Registry (7 Submarkets Across 5 Divisions)
# ---------------------------------------------------------------------------

FREDERICK_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_HISTORIC (2 Submarkets)
    # =======================================================================
    "Downtown Frederick": SubmarketMeta(
        name="Downtown Frederick",
        borough="DOWNTOWN_HISTORIC",
        lat=39.4130,
        lng=-77.4110,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.86,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The Carroll Creek / Market Street CBD with office-to-residential conversions, the Frederick anchor projects, and the city's densest mixed-use pipeline.",
        city_id="frederick",
    ),
    "Carroll Creek": SubmarketMeta(
        name="Carroll Creek",
        borough="DOWNTOWN_HISTORIC",
        lat=39.4100,
        lng=-77.4070,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.82,
        capex=4100000.0,
        permit_vel=24.0,
        shift_ratio=1.34,
        sla=46.0,
        description="The linear park district southwest of downtown with restored historic rowhouses and steady restoration trades.",
        city_id="frederick",
    ),
    # =======================================================================
    # NORTH_MARKET (2 Submarkets)
    # =======================================================================
    "North Market Street": SubmarketMeta(
        name="North Market Street",
        borough="NORTH_MARKET",
        lat=39.4320,
        lng=-77.4120,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.84,
        capex=4900000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=54.0,
        description="The north-end corridor of boutique retail, mansions cut into apartments, and high-turnover condo stock.",
        city_id="frederick",
    ),
    "Golden Mile": SubmarketMeta(
        name="Golden Mile",
        borough="NORTH_MARKET",
        lat=39.4450,
        lng=-77.4100,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.78,
        capex=3600000.0,
        permit_vel=22.0,
        shift_ratio=1.28,
        sla=42.0,
        description="The U.S. 40 commercial strip with auto-row reinvestment and investor renovation flow.",
        city_id="frederick",
    ),
    # =======================================================================
    # SOUTH_CREEK (1 Submarket)
    # =======================================================================
    "South End": SubmarketMeta(
        name="South End",
        borough="SOUTH_CREEK",
        lat=39.3850,
        lng=-77.4150,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.70,
        capex=3000000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=40.0,
        description="The Monocacy-side wards south of downtown with craftsman-bungalow stock and block-by-block reinvestment.",
        city_id="frederick",
    ),
    # =======================================================================
    # WEST_RIDGE (1 Submarket)
    # =======================================================================
    "West Side": SubmarketMeta(
        name="West Side",
        borough="WEST_RIDGE",
        lat=39.4150,
        lng=-77.4500,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.74,
        capex=3300000.0,
        permit_vel=21.0,
        shift_ratio=1.26,
        sla=42.0,
        description="The west-side grid toward the Middletown Valley with solid pre-war housing stock and steady acquisition flow.",
        city_id="frederick",
    ),
    # =======================================================================
    # EAST_GATE (1 Submarket)
    # =======================================================================
    "East Gate": SubmarketMeta(
        name="East Gate",
        borough="EAST_GATE",
        lat=39.4150,
        lng=-77.3850,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.68,
        capex=2800000.0,
        permit_vel=17.0,
        shift_ratio=1.20,
        sla=36.0,
        description="The east-side gateway toward the Liberty watershed with the city's lowest sale prices and heaviest vacancy-to-acquisition conversion.",
        city_id="frederick",
    ),
}


# ---------------------------------------------------------------------------
# Frederick Divisions Catalog
# ---------------------------------------------------------------------------

FREDERICK_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_HISTORIC": BoroughMeta(
        name="DOWNTOWN_HISTORIC",
        center_lat=39.4100,
        center_lng=-77.4110,
        zoom=13.5,
        bbox=FREDERICK_DIVISION_BBOXES["DOWNTOWN_HISTORIC"],
        submarkets=[k for k, v in FREDERICK_SUBMARKETS.items() if v.borough == "DOWNTOWN_HISTORIC"],
        city_id="frederick",
    ),
    "NORTH_MARKET": BoroughMeta(
        name="NORTH_MARKET",
        center_lat=39.4400,
        center_lng=-77.4120,
        zoom=13.5,
        bbox=FREDERICK_DIVISION_BBOXES["NORTH_MARKET"],
        submarkets=[k for k, v in FREDERICK_SUBMARKETS.items() if v.borough == "NORTH_MARKET"],
        city_id="frederick",
    ),
    "SOUTH_CREEK": BoroughMeta(
        name="SOUTH_CREEK",
        center_lat=39.3850,
        center_lng=-77.4150,
        zoom=13.0,
        bbox=FREDERICK_DIVISION_BBOXES["SOUTH_CREEK"],
        submarkets=[k for k, v in FREDERICK_SUBMARKETS.items() if v.borough == "SOUTH_CREEK"],
        city_id="frederick",
    ),
    "WEST_RIDGE": BoroughMeta(
        name="WEST_RIDGE",
        center_lat=39.4200,
        center_lng=-77.4500,
        zoom=13.0,
        bbox=FREDERICK_DIVISION_BBOXES["WEST_RIDGE"],
        submarkets=[k for k, v in FREDERICK_SUBMARKETS.items() if v.borough == "WEST_RIDGE"],
        city_id="frederick",
    ),
    "EAST_GATE": BoroughMeta(
        name="EAST_GATE",
        center_lat=39.4200,
        center_lng=-77.3850,
        zoom=13.0,
        bbox=FREDERICK_DIVISION_BBOXES["EAST_GATE"],
        submarkets=[k for k, v in FREDERICK_SUBMARKETS.items() if v.borough == "EAST_GATE"],
        city_id="frederick",
    ),
}

FRK_DIVISION_BBOXES = FREDERICK_DIVISION_BBOXES
FRK_SUBMARKETS = FREDERICK_SUBMARKETS
FRK_DIVISIONS = FREDERICK_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Frederick deeds/sales via the Frederick County parcel FeatureServer (AGOL
# org X3lKekbdaBmNjCHu, "Frederick_Parcels" layer 3). Native parcel polygons
# supply coordinates; no ADR-0004 geocode hook. Best-effort endpoint pending
# live probe (see PR_DESCRIPTION).
# ---------------------------------------------------------------------------
FREDERICK_DEEDS_ENDPOINT = (
    "https://services1.arcgis.com/X3lKekbdaBmNjCHu/ArcGIS/rest/services/"
    "Frederick_Parcels/FeatureServer/3"
)

FREDERICK_FEED_SPECS: dict[str, dict[str, object]] = {
    "deeds": {
        "endpoint": FREDERICK_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "SALE_DATE",
        "id_keys": ["PARCELID", "OBJECTID", "SALE_DATE"],
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
                "Frederick MD deeds/sales via the Frederick County parcel "
                "FeatureServer (AGOL org X3lKekbdaBmNjCHu, 'Frederick_Parcels' "
                "layer 3). Native parcel polygons supply coordinates; no "
                "ADR-0004 geocode hook. SALE_DATE is TEXT MM/DD/YYYY (typed "
                "comparison required, ADR-0005). Best-effort endpoint pending a "
                "live probe — the interlock gate does not verify endpoint "
                "liveness. $1 quitclaim transfers are KEPT at ingest; "
                "market-sale filtering is analysis-side. PARTY fields stay None; "
                "PARCELID/OBJECTID are the parcel keys."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_frederick_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Frederick feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (deeds only).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in FREDERICK_FEED_SPECS:
        available = ", ".join(sorted(FREDERICK_FEED_SPECS))
        raise KeyError(
            f"'{FREDERICK_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = FREDERICK_FEED_SPECS[feed_name]
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
    metro_bbox=FREDERICK_METRO_BBOX,
    division_bboxes=FREDERICK_DIVISION_BBOXES,
    submarkets=FREDERICK_SUBMARKETS,
    divisions=FREDERICK_DIVISIONS,
    contains=is_in_frederick_metro,
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "FREDERICK_CENTER",
    "FREDERICK_CITY_ID",
    "FREDERICK_DEEDS_ENDPOINT",
    "FREDERICK_DIVISIONS",
    "FREDERICK_DIVISION_BBOXES",
    "FREDERICK_FEED_SPECS",
    "FREDERICK_METRO_BBOX",
    "FREDERICK_SUBMARKETS",
    "FRK_DIVISIONS",
    "FRK_DIVISION_BBOXES",
    "FRK_SUBMARKETS",
    "REGISTRATION",
    "get_frederick_dataset",
    "is_in_frederick",
    "is_in_frederick_metro",
]
