FIELD_MAP = {
    "job_id": ["permit"],
    "issuance_date": ["issue"],
    "address_street": ["address"],
    "latitude": ["latitude", "location_1.latitude"],
    "longitude": ["longitude", "location_1.longitude"],
    "status": ["status"],
}

GAINESVILLE_PERMITS_FIELD_MAP = FIELD_MAP

"""Gainesville, FL Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, division catalog, and geographic
bounding boxes for the City of Gainesville, FL (Alachua County seat).

Feed coverage in this ticket: PERMITS via the verified public Socrata dataset
`p798-x3nx` on `data.cityofgainesville.org` (native latitude/longitude + point field).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

GAINESVILLE_CITY_ID: str = "gainesville"
GAINESVILLE_GEOCODE_CONTEXT: str = "Gainesville, FL"

# Broad bbox covering Gainesville proper and adjacent corridors (Newberry Rd / Archer Rd).
GAINESVILLE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 29.55,
    "max_lat": 29.75,
    "min_lng": -82.50,
    "max_lng": -82.20,
}

# Divide the metro into a compact set of camera regions that match recognizable areas.
GAINESVILLE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_UF": {
        "min_lat": 29.63,
        "max_lat": 29.67,
        "min_lng": -82.36,
        "max_lng": -82.30,
    },
    "NORTHWEST": {
        "min_lat": 29.65,
        "max_lat": 29.75,
        "min_lng": -82.44,
        "max_lng": -82.32,
    },
    "NORTHEAST": {
        "min_lat": 29.645,
        "max_lat": 29.75,
        "min_lng": -82.32,
        "max_lng": -82.22,
    },
    "SOUTHWEST_SOUTHEAST": {
        "min_lat": 29.55,
        "max_lat": 29.66,
        "min_lng": -82.50,
        "max_lng": -82.28,
    },
}


def is_in_gainesville_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Gainesville metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        GAINESVILLE_METRO_BBOX["min_lat"] <= lat <= GAINESVILLE_METRO_BBOX["max_lat"]
        and GAINESVILLE_METRO_BBOX["min_lng"] <= lng <= GAINESVILLE_METRO_BBOX["max_lng"]
    )


GAINESVILLE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # DOWNTOWN_UF
    "Downtown Gainesville": SubmarketMeta(
        name="Downtown Gainesville",
        borough="DOWNTOWN_UF",
        lat=29.6516,
        lng=-82.3248,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.86,
        capex=6800000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=58.0,
        description="Historic downtown core centered on University Ave and Main St with adaptive reuse.",
        city_id=GAINESVILLE_CITY_ID,
    ),
    "Midtown": SubmarketMeta(
        name="Midtown",
        borough="DOWNTOWN_UF",
        lat=29.6530,
        lng=-82.3380,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.84,
        capex=6200000.0,
        permit_vel=28.0,
        shift_ratio=1.38,
        sla=56.0,
        description="University-adjacent district at NW 13th St and University Ave with mixed-use infill.",
        city_id=GAINESVILLE_CITY_ID,
    ),
    "Innovation District": SubmarketMeta(
        name="Innovation District",
        borough="DOWNTOWN_UF",
        lat=29.6500,
        lng=-82.3300,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.83,
        capex=6100000.0,
        permit_vel=27.0,
        shift_ratio=1.36,
        sla=55.0,
        description="UF-adjacent startup cluster and research space between downtown and campus.",
        city_id=GAINESVILLE_CITY_ID,
    ),
    # NORTHWEST
    "Millhopper / Thornebrook": SubmarketMeta(
        name="Millhopper / Thornebrook",
        borough="NORTHWEST",
        lat=29.6880,
        lng=-82.3790,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=5200000.0,
        permit_vel=24.0,
        shift_ratio=1.32,
        sla=52.0,
        description="Northwest neighborhood retail and residential near Millhopper Road and 43rd St.",
        city_id=GAINESVILLE_CITY_ID,
    ),
    "Oaks Mall / Newberry Rd": SubmarketMeta(
        name="Oaks Mall / Newberry Rd",
        borough="NORTHWEST",
        lat=29.6530,
        lng=-82.4130,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.77,
        capex=5000000.0,
        permit_vel=23.0,
        shift_ratio=1.30,
        sla=50.0,
        description="Regional retail corridor around Oaks Mall and Newberry Road.",
        city_id=GAINESVILLE_CITY_ID,
    ),
    # NORTHEAST
    "East Gainesville": SubmarketMeta(
        name="East Gainesville",
        borough="NORTHEAST",
        lat=29.6510,
        lng=-82.2850,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.72,
        capex=4200000.0,
        permit_vel=21.0,
        shift_ratio=1.26,
        sla=46.0,
        description="Residential east side with corridor reinvestment along Hawthorne Rd.",
        city_id=GAINESVILLE_CITY_ID,
    ),
    "GNV Airport Area": SubmarketMeta(
        name="GNV Airport Area",
        borough="NORTHEAST",
        lat=29.6910,
        lng=-82.2750,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.70,
        capex=3900000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=44.0,
        description="Industrial and logistics near Gainesville Regional Airport.",
        city_id=GAINESVILLE_CITY_ID,
    ),
    # SOUTHWEST_SOUTHEAST
    "Butler Plaza / Archer Rd": SubmarketMeta(
        name="Butler Plaza / Archer Rd",
        borough="SOUTHWEST_SOUTHEAST",
        lat=29.6220,
        lng=-82.3840,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.79,
        capex=5600000.0,
        permit_vel=26.0,
        shift_ratio=1.34,
        sla=53.0,
        description="Southwest retail and multifamily corridor along Archer Road.",
        city_id=GAINESVILLE_CITY_ID,
    ),
    "Haile Plantation": SubmarketMeta(
        name="Haile Plantation",
        borough="SOUTHWEST_SOUTHEAST",
        lat=29.6110,
        lng=-82.4490,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.75,
        capex=4800000.0,
        permit_vel=22.0,
        shift_ratio=1.28,
        sla=48.0,
        description="Master-planned community southwest of I-75 with residential reinvestment.",
        city_id=GAINESVILLE_CITY_ID,
    ),
}

GAINESVILLE_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_UF": BoroughMeta(
        name="DOWNTOWN_UF",
        center_lat=29.650,
        center_lng=-82.335,
        zoom=13.5,
        bbox=GAINESVILLE_DIVISION_BBOXES["DOWNTOWN_UF"],
        submarkets=[k for k, v in GAINESVILLE_SUBMARKETS.items() if v.borough == "DOWNTOWN_UF"],
        city_id=GAINESVILLE_CITY_ID,
    ),
    "NORTHWEST": BoroughMeta(
        name="NORTHWEST",
        center_lat=29.690,
        center_lng=-82.380,
        zoom=13.0,
        bbox=GAINESVILLE_DIVISION_BBOXES["NORTHWEST"],
        submarkets=[k for k, v in GAINESVILLE_SUBMARKETS.items() if v.borough == "NORTHWEST"],
        city_id=GAINESVILLE_CITY_ID,
    ),
    "NORTHEAST": BoroughMeta(
        name="NORTHEAST",
        center_lat=29.690,
        center_lng=-82.285,
        zoom=13.0,
        bbox=GAINESVILLE_DIVISION_BBOXES["NORTHEAST"],
        submarkets=[k for k, v in GAINESVILLE_SUBMARKETS.items() if v.borough == "NORTHEAST"],
        city_id=GAINESVILLE_CITY_ID,
    ),
    "SOUTHWEST_SOUTHEAST": BoroughMeta(
        name="SOUTHWEST_SOUTHEAST",
        center_lat=29.615,
        center_lng=-82.405,
        zoom=12.8,
        bbox=GAINESVILLE_DIVISION_BBOXES["SOUTHWEST_SOUTHEAST"],
        submarkets=[k for k, v in GAINESVILLE_SUBMARKETS.items() if v.borough == "SOUTHWEST_SOUTHEAST"],
        city_id=GAINESVILLE_CITY_ID,
    ),
}

GREATER_GNV_METRO_BBOX = GAINESVILLE_METRO_BBOX
GNV_DIVISION_BBOXES = GAINESVILLE_DIVISION_BBOXES
GNV_SUBMARKETS = GAINESVILLE_SUBMARKETS
GNV_DIVISIONS = GAINESVILLE_DIVISIONS

# -----------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28 against data.cityofgainesville.org.
# -----------------------------------------------------------------------------
GAINESVILLE_PERMITS_ENDPOINT = "https://data.cityofgainesville.org/resource/p798-x3nx.json"

GAINESVILLE_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": GAINESVILLE_PERMITS_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "issue",
        "id_keys": ["permit"],
        "topic_key": "topic_permits",
        "interval_seconds": 600.0,
        "producer_key": "permits",
        "extra": {
            "order_by": "issue DESC",
            "field_map": GAINESVILLE_PERMITS_FIELD_MAP,
            # No geocode required for native point rows; fallback remains available in shared parser.
        },
    },
}


def get_gainesville_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset`` for test convenience."""
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in GAINESVILLE_FEED_SPECS:
        available = ", ".join(sorted(GAINESVILLE_FEED_SPECS))
        raise KeyError(f"'{GAINESVILLE_CITY_ID}' has no '{feed_name}' feed; available: {available}")
    payload = GAINESVILLE_FEED_SPECS[feed_name]
    extra_kwargs = {k: v for k, v in payload.get("extra", {}).items() if k != "scope"}
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
    metro_bbox=GAINESVILLE_METRO_BBOX,
    division_bboxes=GAINESVILLE_DIVISION_BBOXES,
    submarkets=GAINESVILLE_SUBMARKETS,
    divisions=GAINESVILLE_DIVISIONS,
    contains=is_in_gainesville_metro,
)

