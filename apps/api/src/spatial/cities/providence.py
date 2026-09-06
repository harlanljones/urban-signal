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

"""Providence, RI Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Providence,
RI (the state capital, at the head of Narragansett Bay).

Feed scope (US-350): Providence is a DEEDS-led partial metro. The City of
Providence open-data portal publishes a parcels / sales layer carrying per-parcel
SALE_DATE / SALE_PRICE / DEED_TYPE. Until a live probe confirms the exact
resource, the registration points at a best-effort municipal FeatureServer URL
(see ``arcgis_providence_deeds_url`` in settings) and is documented as such in
PR_DESCRIPTION.md. The feed mirrors Rochester's ArcGIS shape:

* DEEDS — municipal parcels FeatureServer (``/FeatureServer/0``). Watermark
  ``SALE_DATE`` is TEXT ``MM/DD/YYYY``; the ADR-0005 text-watermark typed
  comparison is mandatory. Native parcel polygons (``outSR=4326``) supply each
  row's coordinates, so ``needs_geocode`` stays False — no ADR-0004 hook.
* PERMITS / SLA / COMPLAINTS_311 — absent from the scope of this ticket (US-350
  is DEEDS-only); do not register them until a dedicated ticket clears the feed
  family gate.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

PROVIDENCE_CITY_ID: str = "providence"

# Providence metro bbox (the city proper, head of Narragansett Bay). Center is
# downtown Providence (Kennedy Plaza).
PROVIDENCE_METRO_BBOX: dict[str, float] = {
    "min_lat": 41.79,
    "max_lat": 41.85,
    "min_lng": -71.45,
    "max_lng": -71.38,
}

# Registration-contract center: downtown Providence.
PROVIDENCE_CENTER: dict[str, float] = {"lat": 41.8240, "lng": -71.4128}

# 6 Providence Division Bounding Boxes (strictly nested inside the metro bbox)
PROVIDENCE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN":        {"min_lat": 41.815, "max_lat": 41.835, "min_lng": -71.425, "max_lng": -71.395},
    "EAST_SIDE":       {"min_lat": 41.820, "max_lat": 41.850, "min_lng": -71.400, "max_lng": -71.385},
    "FEDERAL_HILL":    {"min_lat": 41.810, "max_lat": 41.830, "min_lng": -71.440, "max_lng": -71.410},
    "SOUTH_SIDE":      {"min_lat": 41.790, "max_lat": 41.810, "min_lng": -71.440, "max_lng": -71.400},
    "NORTH_SIDE":      {"min_lat": 41.830, "max_lat": 41.850, "min_lng": -71.430, "max_lng": -71.400},
    "OLNEYVILLE":      {"min_lat": 41.810, "max_lat": 41.830, "min_lng": -71.450, "max_lng": -71.420},
}


def is_in_providence_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Providence metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        PROVIDENCE_METRO_BBOX["min_lat"] <= lat <= PROVIDENCE_METRO_BBOX["max_lat"]
        and PROVIDENCE_METRO_BBOX["min_lng"] <= lng <= PROVIDENCE_METRO_BBOX["max_lng"]
    )


def is_in_providence(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_providence_metro`."""
    return is_in_providence_metro(lat, lng)


# ---------------------------------------------------------------------------
# Providence Submarket Registry (9 Submarkets Across 6 Divisions)
# ---------------------------------------------------------------------------

PROVIDENCE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (2 Submarkets)
    # =======================================================================
    "Downtown Providence": SubmarketMeta(
        name="Downtown Providence",
        borough="DOWNTOWN",
        lat=41.8240,
        lng=-71.4128,
        zoom=15.0,
        pitch=55.0,
        base_lims=0.80,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.44,
        sla=55.0,
        description="The civic and office core around Kennedy Plaza and the riverwalk with conversion-condo activity and the city's densest commercial pipeline.",
        city_id="providence",
    ),
    "Capital Center": SubmarketMeta(
        name="Capital Center",
        borough="DOWNTOWN",
        lat=41.8300,
        lng=-71.4150,
        zoom=15.0,
        pitch=52.0,
        base_lims=0.83,
        capex=5800000.0,
        permit_vel=28.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The state-house district and I-195 redevelopment lands with loft conversions and the city's highest-energy storefront renewal.",
        city_id="providence",
    ),
    # =======================================================================
    # EAST_SIDE (2 Submarkets)
    # =======================================================================
    "College Hill": SubmarketMeta(
        name="College Hill",
        borough="EAST_SIDE",
        lat=41.8280,
        lng=-71.3970,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=6200000.0,
        permit_vel=26.0,
        shift_ratio=1.50,
        sla=57.0,
        description="The Brown/ RISD hilltop with historic single-family stock, Thayer Street commercial, and steady duplex-to-condo reinvestment.",
        city_id="providence",
    ),
    "Wayland": SubmarketMeta(
        name="Wayland",
        borough="EAST_SIDE",
        lat=41.8450,
        lng=-71.3900,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.79,
        capex=4700000.0,
        permit_vel=22.0,
        shift_ratio=1.40,
        sla=49.0,
        description="The East Side's east-of-the-river residential grid with stable owner-occupancy and the metro's most conservation-minded renovation flow.",
        city_id="providence",
    ),
    # =======================================================================
    # FEDERAL_HILL (2 Submarkets)
    # =======================================================================
    "Federal Hill": SubmarketMeta(
        name="Federal Hill",
        borough="FEDERAL_HILL",
        lat=41.8220,
        lng=-71.4250,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.74,
        capex=4200000.0,
        permit_vel=25.0,
        shift_ratio=1.43,
        sla=46.0,
        description="The Italianate restaurant-and-housing district on the west flank of downtown with triple-decker rental stock and block-by-block reinvestment.",
        city_id="providence",
    ),
    "West End": SubmarketMeta(
        name="West End",
        borough="FEDERAL_HILL",
        lat=41.8150,
        lng=-71.4300,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.72,
        capex=4000000.0,
        permit_vel=21.0,
        shift_ratio=1.38,
        sla=44.0,
        description="The Broad Street corridor and Dexter Training Ground with value-priced multi-family stock and early-stage commercial renewal.",
        city_id="providence",
    ),
    # =======================================================================
    # SOUTH_SIDE (2 Submarkets)
    # =======================================================================
    "Elmwood": SubmarketMeta(
        name="Elmwood",
        borough="SOUTH_SIDE",
        lat=41.8000,
        lng=-71.4200,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.70,
        capex=3800000.0,
        permit_vel=19.0,
        shift_ratio=1.34,
        sla=42.0,
        description="The Elmwood Avenue residential spine south of the hospital district with craftsman-bungalow stock and steady investor renovation flow.",
        city_id="providence",
    ),
    "South Providence": SubmarketMeta(
        name="South Providence",
        borough="SOUTH_SIDE",
        lat=41.7950,
        lng=-71.4150,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.68,
        capex=3600000.0,
        permit_vel=18.0,
        shift_ratio=1.33,
        sla=41.0,
        description="The Allens Avenue / Washington Park edge with the metro's lowest sale prices and the heaviest vacancy-to-acquisition conversion flow.",
        city_id="providence",
    ),
    # =======================================================================
    # NORTH_SIDE (1 Submarket)
    # =======================================================================
    "Smith Hill": SubmarketMeta(
        name="Smith Hill",
        borough="NORTH_SIDE",
        lat=41.8400,
        lng=-71.4150,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.73,
        capex=4300000.0,
        permit_vel=18.0,
        shift_ratio=1.33,
        sla=45.0,
        description="The Smith Hill / Wanskuck north side with State House-adjacent rowhouses, the Charles Street commercial strip, and value-priced family-housing reinvestment.",
        city_id="providence",
    ),
    # =======================================================================
    # OLNEYVILLE (1 Submarket)
    # =======================================================================
    "Olneyville": SubmarketMeta(
        name="Olneyville",
        borough="OLNEYVILLE",
        lat=41.8200,
        lng=-71.4350,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.71,
        capex=3900000.0,
        permit_vel=20.0,
        shift_ratio=1.36,
        sla=43.0,
        description="The Woonasquatucket mill district with mill-to-loft conversions, the Manton Avenue commercial row, and the city's most industrial-leaning reinvestment.",
        city_id="providence",
    ),
}


# ---------------------------------------------------------------------------
# Providence Divisions Catalog
# ---------------------------------------------------------------------------

PROVIDENCE_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=41.8270,
        center_lng=-71.4140,
        zoom=14.5,
        bbox=PROVIDENCE_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in PROVIDENCE_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="providence",
    ),
    "EAST_SIDE": BoroughMeta(
        name="EAST_SIDE",
        center_lat=41.8365,
        center_lng=-71.3935,
        zoom=14.0,
        bbox=PROVIDENCE_DIVISION_BBOXES["EAST_SIDE"],
        submarkets=[k for k, v in PROVIDENCE_SUBMARKETS.items() if v.borough == "EAST_SIDE"],
        city_id="providence",
    ),
    "FEDERAL_HILL": BoroughMeta(
        name="FEDERAL_HILL",
        center_lat=41.8185,
        center_lng=-71.4275,
        zoom=14.0,
        bbox=PROVIDENCE_DIVISION_BBOXES["FEDERAL_HILL"],
        submarkets=[k for k, v in PROVIDENCE_SUBMARKETS.items() if v.borough == "FEDERAL_HILL"],
        city_id="providence",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=41.7975,
        center_lng=-71.4175,
        zoom=14.0,
        bbox=PROVIDENCE_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in PROVIDENCE_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="providence",
    ),
    "NORTH_SIDE": BoroughMeta(
        name="NORTH_SIDE",
        center_lat=41.8400,
        center_lng=-71.4150,
        zoom=14.0,
        bbox=PROVIDENCE_DIVISION_BBOXES["NORTH_SIDE"],
        submarkets=[k for k, v in PROVIDENCE_SUBMARKETS.items() if v.borough == "NORTH_SIDE"],
        city_id="providence",
    ),
    "OLNEYVILLE": BoroughMeta(
        name="OLNEYVILLE",
        center_lat=41.8200,
        center_lng=-71.4350,
        zoom=14.0,
        bbox=PROVIDENCE_DIVISION_BBOXES["OLNEYVILLE"],
        submarkets=[k for k, v in PROVIDENCE_SUBMARKETS.items() if v.borough == "OLNEYVILLE"],
        city_id="providence",
    ),
}

PROV_DIVISION_BBOXES = PROVIDENCE_DIVISION_BBOXES
PROV_SUBMARKETS = PROVIDENCE_SUBMARKETS
PROV_DIVISIONS = PROVIDENCE_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Providence is DEEDS-only for US-350: the municipal parcels FeatureServer
# carries SALE_DATE / SALE_PRICE / DEED_TYPE. Native parcel polygons supply
# coordinates, so needs_geocode stays False.
# ---------------------------------------------------------------------------
PROVIDENCE_DEEDS_ENDPOINT = (
    "https://providenceri.gov/server/rest/services/OpenData/Parcels/FeatureServer/0"
)

PROVIDENCE_FEED_SPECS: dict[str, dict[str, object]] = {
    "deeds": {
        "endpoint": PROVIDENCE_DEEDS_ENDPOINT,
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
            "ingestion_mode": "incremental",
            "scope": (
                "Providence, RI DEEDS/sales via the municipal parcels "
                "FeatureServer (best-effort endpoint — not live-verified at "
                "registration; see PR_DESCRIPTION.md). TEXT MM/DD/YYYY "
                "watermark sorts lexically — typed comparison required "
                "(ADR-0005). Native parcel polygons (outSR=4326) supply each "
                "row's coordinates, so the ADR-0004 geocode hook is NOT "
                "declared. PERMITS/SLA/311 are out of scope for US-350."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_providence_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Providence feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (permits/SLA/311
    are absent from the US-350 scope).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in PROVIDENCE_FEED_SPECS:
        available = ", ".join(sorted(PROVIDENCE_FEED_SPECS))
        raise KeyError(
            f"'{PROVIDENCE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = PROVIDENCE_FEED_SPECS[feed_name]
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
    metro_bbox=PROVIDENCE_METRO_BBOX,
    division_bboxes=PROVIDENCE_DIVISION_BBOXES,
    submarkets=PROVIDENCE_SUBMARKETS,
    divisions=PROVIDENCE_DIVISIONS,
    contains=is_in_providence_metro,
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "PROVIDENCE_CENTER",
    "PROVIDENCE_CITY_ID",
    "PROVIDENCE_DEEDS_ENDPOINT",
    "PROVIDENCE_DIVISIONS",
    "PROVIDENCE_DIVISION_BBOXES",
    "PROVIDENCE_FEED_SPECS",
    "PROVIDENCE_METRO_BBOX",
    "PROVIDENCE_SUBMARKETS",
    "PROV_DIVISIONS",
    "PROV_DIVISION_BBOXES",
    "PROV_SUBMARKETS",
    "REGISTRATION",
    "get_providence_dataset",
    "is_in_providence",
    "is_in_providence_metro",
]
