DEEDS_FIELD_MAP = {
    "doc_id": ["pin"],
    "bbl": ["pin"],
    "doc_type": ["deed_type"],
    "document_amount": ["consideration"],
    "recorded_date": ["transfer_date"],
    "address_street": ["parcel_location"],
    "incident_address": ["parcel_location"],
}

FIELD_MAP = {
    "deeds": DEEDS_FIELD_MAP,
}

# Workbook columns a row keeps for its id but no event field reads: the deed
# book (``ID2026`` for an instrument recorded in 2026) and page.
NON_CANDIDATE_METADATA_COLUMNS = (
    "deed_book",
    "deed_page",
)

"""Richmond Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Richmond,
VA (fall-line capital on the James River — boxes chosen to stay clear of the
sibling Lynchburg/Charlottesville leaf extents).

Feed scope (US-348): Richmond is a DEEDS-led partial metro. The city's
portal carries no permit, 311 or dated licence feed (probe-richmond.md).

* DEEDS — the assessor's property transfers workbook, one .xlsx of every
  recorded transfer, re-released on or about the 15th of each month under a
  new name (``Assessor_Transfers_2026-09-23.xlsx``). The spec registers the
  media page that links the current file (``link_pattern``); the Excel client
  reads it a row at a time, keeps the last 365 days, and answers 304 until a
  new file appears. The workbook has no coordinates: each sale takes its
  parcel's centroid from the city's Parcels layer by ``PIN``. Buyer and
  seller names (``GRANTEE``, ``GRANTOR``) never leave the client: ``select``
  names only the columns the feed reads.

SLA (2026-09-30): the USDA SNAP retailer slice inside the metro box, which
stands in for the licence register the metro lacks. The corpus builds it
with the shared ``snap_sla_spec``; the feed mirror below does not carry it.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

RICHMOND_CITY_ID: str = "richmond"

# Metro bbox around the City of Richmond, VA (fall line on the James River).
# Center 37.5407 / -77.4360; the box spans the urban core from the West End
# through the East End, north to Ginter Park and south across the river to
# South Side / Manchester.
RICHMOND_METRO_BBOX: dict[str, float] = {
    "min_lat": 37.45,
    "max_lat": 37.70,
    "min_lng": -77.65,
    "max_lng": -77.30,
}

# Registration-contract center: downtown Richmond (Broad St CBD).
RICHMOND_CENTER: dict[str, float] = {"lat": 37.5407, "lng": -77.4360}

# 6 Richmond Division Bounding Boxes (strictly nested inside the metro bbox)
RICHMOND_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN":        {"min_lat": 37.52, "max_lat": 37.56, "min_lng": -77.45, "max_lng": -77.43},
    "THE_FAN":         {"min_lat": 37.55, "max_lat": 37.58, "min_lng": -77.47, "max_lng": -77.45},
    "NORTH_SIDE":      {"min_lat": 37.58, "max_lat": 37.66, "min_lng": -77.47, "max_lng": -77.43},
    "SOUTH_SIDE":      {"min_lat": 37.45, "max_lat": 37.56, "min_lng": -77.50, "max_lng": -77.43},
    "EAST_END":        {"min_lat": 37.50, "max_lat": 37.60, "min_lng": -77.43, "max_lng": -77.30},
    "WEST_END":        {"min_lat": 37.55, "max_lat": 37.68, "min_lng": -77.60, "max_lng": -77.48},
}


def is_in_richmond_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Richmond metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        RICHMOND_METRO_BBOX["min_lat"] <= lat <= RICHMOND_METRO_BBOX["max_lat"]
        and RICHMOND_METRO_BBOX["min_lng"] <= lng <= RICHMOND_METRO_BBOX["max_lng"]
    )


def is_in_richmond(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_richmond_metro`."""
    return is_in_richmond_metro(lat, lng)


# ---------------------------------------------------------------------------
# Richmond Submarket Registry (9 Submarkets Across 6 Divisions)
# ---------------------------------------------------------------------------

RICHMOND_SUBMARKETS: dict[str, SubmarketMeta] = {
    # DOWNTOWN (2 Submarkets)
    "Downtown Richmond": SubmarketMeta(
        name="Downtown Richmond",
        borough="DOWNTOWN",
        lat=37.5410,
        lng=-77.4370,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.86,
        capex=6500000.0,
        permit_vel=34.0,
        shift_ratio=1.48,
        sla=58.0,
        description="The Broad Street CBD and Riverfront with office-to-residential conversions, the downtown arena anchor projects, and the city's densest mixed-use pipeline.",
        city_id="richmond",
    ),
    "Jackson Ward": SubmarketMeta(
        name="Jackson Ward",
        borough="DOWNTOWN",
        lat=37.5470,
        lng=-77.4420,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.82,
        capex=4200000.0,
        permit_vel=24.0,
        shift_ratio=1.35,
        sla=46.0,
        description="The historic Black Wall Street district northwest of downtown with Italianate rowhouses, restoration trades, and a steady hospitality-licensing flow.",
        city_id="richmond",
    ),
    # THE_FAN (2 Submarkets)
    "The Fan": SubmarketMeta(
        name="The Fan",
        borough="THE_FAN",
        lat=37.5650,
        lng=-77.4600,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.84,
        capex=5100000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=54.0,
        description="The diagonal-grid Victorian neighborhood west of downtown with mansion-to-apartment conversions and a high-turnover condo stock.",
        city_id="richmond",
    ),
    "Museum District": SubmarketMeta(
        name="Museum District",
        borough="THE_FAN",
        lat=37.5550,
        lng=-77.4520,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.83,
        capex=4800000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=52.0,
        description="The Boulevard corridor around the VMFA / Science Museum where gallery-space retrofits and rowhouse renewals drive the permit mix.",
        city_id="richmond",
    ),
    # NORTH_SIDE (1 Submarket)
    "Scott's Addition": SubmarketMeta(
        name="Scott's Addition",
        borough="NORTH_SIDE",
        lat=37.5850,
        lng=-77.4600,
        zoom=14.5,
        pitch=38.0,
        base_lims=0.80,
        capex=4600000.0,
        permit_vel=32.0,
        shift_ratio=1.38,
        sla=50.0,
        description="The warehouses-to-breweries and apartment district north of the Fan with the city's highest permit velocity and entertainment licensing.",
        city_id="richmond",
    ),
    # SOUTH_SIDE (2 Submarkets)
    "Carytown": SubmarketMeta(
        name="Carytown",
        borough="SOUTH_SIDE",
        lat=37.5480,
        lng=-77.4860,
        zoom=15.0,
        pitch=35.0,
        base_lims=0.78,
        capex=3900000.0,
        permit_vel=26.0,
        shift_ratio=1.32,
        sla=48.0,
        description="The Cary Street boutique retail spine and surrounding early-20th-century blocks with investor renovation flow and stable rental demand.",
        city_id="richmond",
    ),
    "Manchester": SubmarketMeta(
        name="Manchester",
        borough="SOUTH_SIDE",
        lat=37.5100,
        lng=-77.4500,
        zoom=15.0,
        pitch=32.0,
        base_lims=0.70,
        capex=3100000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=40.0,
        description="The south-bank warehouse district across the river from downtown with loft conversions and brewery/industrial adaptive reuse.",
        city_id="richmond",
    ),
    # EAST_END (1 Submarket)
    "Church Hill": SubmarketMeta(
        name="Church Hill",
        borough="EAST_END",
        lat=37.5300,
        lng=-77.4100,
        zoom=14.5,
        pitch=32.0,
        base_lims=0.66,
        capex=2700000.0,
        permit_vel=16.0,
        shift_ratio=1.18,
        sla=34.0,
        description="The city's oldest neighborhood east of downtown where pre-war housing stock meets the heaviest vacancy-to-acquisition conversion flow.",
        city_id="richmond",
    ),
    # WEST_END (1 Submarket)
    "Westover Hills": SubmarketMeta(
        name="Westover Hills",
        borough="WEST_END",
        lat=37.6000,
        lng=-77.5500,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.68,
        capex=2900000.0,
        permit_vel=18.0,
        shift_ratio=1.20,
        sla=36.0,
        description="The southwest-river bluff single-family plateau with solid housing stock and steady block-by-block reinvestment.",
        city_id="richmond",
    ),
}


# ---------------------------------------------------------------------------
# Richmond Divisions Catalog
# ---------------------------------------------------------------------------

RICHMOND_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=37.5440,
        center_lng=-77.4395,
        zoom=13.5,
        bbox=RICHMOND_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in RICHMOND_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="richmond",
    ),
    "THE_FAN": BoroughMeta(
        name="THE_FAN",
        center_lat=37.5600,
        center_lng=-77.4560,
        zoom=13.5,
        bbox=RICHMOND_DIVISION_BBOXES["THE_FAN"],
        submarkets=[k for k, v in RICHMOND_SUBMARKETS.items() if v.borough == "THE_FAN"],
        city_id="richmond",
    ),
    "NORTH_SIDE": BoroughMeta(
        name="NORTH_SIDE",
        center_lat=37.6025,
        center_lng=-77.4450,
        zoom=13.0,
        bbox=RICHMOND_DIVISION_BBOXES["NORTH_SIDE"],
        submarkets=[k for k, v in RICHMOND_SUBMARKETS.items() if v.borough == "NORTH_SIDE"],
        city_id="richmond",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=37.4850,
        center_lng=-77.4650,
        zoom=13.0,
        bbox=RICHMOND_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in RICHMOND_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="richmond",
    ),
    "EAST_END": BoroughMeta(
        name="EAST_END",
        center_lat=37.5500,
        center_lng=-77.3650,
        zoom=13.0,
        bbox=RICHMOND_DIVISION_BBOXES["EAST_END"],
        submarkets=[k for k, v in RICHMOND_SUBMARKETS.items() if v.borough == "EAST_END"],
        city_id="richmond",
    ),
    "WEST_END": BoroughMeta(
        name="WEST_END",
        center_lat=37.6150,
        center_lng=-77.5400,
        zoom=13.0,
        bbox=RICHMOND_DIVISION_BBOXES["WEST_END"],
        submarkets=[k for k, v in RICHMOND_SUBMARKETS.items() if v.borough == "WEST_END"],
        city_id="richmond",
    ),
}

RIC_DIVISION_BBOXES = RICHMOND_DIVISION_BBOXES
RIC_SUBMARKETS = RICHMOND_SUBMARKETS
RIC_DIVISIONS = RICHMOND_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# US-348: DEEDS-led partial metro, read from the assessor's monthly transfers
# workbook; the Parcels layer supplies each sale's coordinates.
# ---------------------------------------------------------------------------
RICHMOND_DEEDS_ENDPOINT = "https://www.rva.gov/media/53946"
RICHMOND_PARCEL_LAYER = (
    "https://services1.arcgis.com/k3vhq11XkBNeeOfM/arcgis/rest/services/Parcels/FeatureServer/0"
)

RICHMOND_FEED_SPECS: dict[str, dict[str, object]] = {
    "deeds": {
        "endpoint": RICHMOND_DEEDS_ENDPOINT,
        "platform": "excel",
        "watermark_col": "transfer_date",
        "id_keys": ["pin", "transfer_date", "deed_book", "deed_page"],
        "topic_key": "topic_deeds",
        "interval_seconds": 86400.0,
        "producer_key": "deeds",
        "extra": {
            "link_pattern": r"Assessor_Transfers_[0-9-]+\.xlsx$",
            "composite_id": True,
            "ingestion_mode": "snapshot",
            "order_by": "transfer_date DESC",
            "select": "pin,transfer_date,consideration,deed_book,deed_page,deed_type,parcel_location",
            "where": "transfer_date >= CURRENT_DATE - INTERVAL '365' DAY",
            "batch_limit": 12000,
            "needs_geocode": False,
            "expected_cadence_days": 45,
            "non_spatial": False,
            "parcel_join": {
                "parcel_layer": RICHMOND_PARCEL_LAYER,
                "join_key": "PIN",
                "row_key": "pin",
                "geometry_source": "centroid",
            },
            "scope": (
                "Richmond VA DEEDS from the assessor's monthly property "
                "transfers workbook (439,398 transfers on 2026-09-23, newest "
                "first). A sale is its parcel, date, deed book and page; the "
                "last 365 days held about 6,650. $0 and non-market transfers "
                "are KEPT (the workbook's QUALIFIED column marks market sales; "
                "filtering is analysis-side)."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_richmond_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Richmond feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (permits and
    311 are not registered). SLA is the corpus's shared SNAP slice, which
    this mirror does not carry.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in RICHMOND_FEED_SPECS:
        available = ", ".join(sorted(RICHMOND_FEED_SPECS))
        raise KeyError(
            f"'{RICHMOND_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = RICHMOND_FEED_SPECS[feed_name]
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
    metro_bbox=RICHMOND_METRO_BBOX,
    division_bboxes=RICHMOND_DIVISION_BBOXES,
    submarkets=RICHMOND_SUBMARKETS,
    divisions=RICHMOND_DIVISIONS,
    contains=is_in_richmond_metro,
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "REGISTRATION",
    "RICHMOND_CENTER",
    "RICHMOND_CITY_ID",
    "RICHMOND_DEEDS_ENDPOINT",
    "RICHMOND_DIVISIONS",
    "RICHMOND_DIVISION_BBOXES",
    "RICHMOND_FEED_SPECS",
    "RICHMOND_METRO_BBOX",
    "RICHMOND_PARCEL_LAYER",
    "RICHMOND_SUBMARKETS",
    "RIC_DIVISIONS",
    "RIC_DIVISION_BBOXES",
    "RIC_SUBMARKETS",
    "get_richmond_dataset",
    "is_in_richmond",
    "is_in_richmond_metro",
]
