"""Canton / Stark County, Ohio spatial registry and geometry.

Canton is the seat of Stark County in northeast Ohio's Rust Belt. US-425
registers the county Auditor's live Property Sales layer (a daily CAMA sync
of deed/sale transactions) plus USDA SNAP SLA coverage. The metro bbox covers
Canton, Massillon, and North Canton — the Stark County urbanized core the
sales layer spans.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

CANTON_METRO_BBOX: dict[str, float] = {
    "min_lat": 40.65,
    "max_lat": 40.95,
    "min_lng": -81.65,
    "max_lng": -81.20,
}

CANTON_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "CANTON_CORE": {
        "min_lat": 40.70,
        "max_lat": 40.90,
        "min_lng": -81.55,
        "max_lng": -81.28,
    },
}


def is_in_canton_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Canton/Stark extent."""
    if lat is None or lng is None:
        return False
    return (
        CANTON_METRO_BBOX["min_lat"] <= lat <= CANTON_METRO_BBOX["max_lat"]
        and CANTON_METRO_BBOX["min_lng"] <= lng <= CANTON_METRO_BBOX["max_lng"]
    )


CANTON_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown Canton": SubmarketMeta(
        name="Downtown Canton",
        borough="CANTON_CORE",
        lat=40.7989,
        lng=-81.3784,
        zoom=13.4,
        pitch=46.0,
        base_lims=0.80,
        capex=5200000.0,
        permit_vel=28.0,
        shift_ratio=1.34,
        sla=52.0,
        description="Historic civic core anchored by the Pro Football Hall of Fame district and downtown loft reuse.",
        city_id="canton",
    ),
    "North Canton": SubmarketMeta(
        name="North Canton",
        borough="CANTON_CORE",
        lat=40.8759,
        lng=-81.4023,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.79,
        capex=4700000.0,
        permit_vel=26.0,
        shift_ratio=1.32,
        sla=51.0,
        description="Affluent suburban node with steady single-family permit flow and neighborhood retail corridors.",
        city_id="canton",
    ),
    "Massillon": SubmarketMeta(
        name="Massillon",
        borough="CANTON_CORE",
        lat=40.7967,
        lng=-81.5215,
        zoom=12.8,
        pitch=41.0,
        base_lims=0.73,
        capex=3600000.0,
        permit_vel=22.0,
        shift_ratio=1.27,
        sla=46.0,
        description="Ohio & Erie Canal town with housing rehabilitation, downtown reinvestment, and industrial reuse.",
        city_id="canton",
    ),
    "Plain & Jackson Townships": SubmarketMeta(
        name="Plain & Jackson Townships",
        borough="CANTON_CORE",
        lat=40.8300,
        lng=-81.3500,
        zoom=12.6,
        pitch=40.0,
        base_lims=0.74,
        capex=3900000.0,
        permit_vel=24.0,
        shift_ratio=1.29,
        sla=48.0,
        description="Suburban bedroom townships around the Belden Village retail belt with residential infill.",
        city_id="canton",
    ),
}

CANTON_DIVISIONS: dict[str, BoroughMeta] = {
    "CANTON_CORE": BoroughMeta(
        name="Canton Core",
        center_lat=40.7989,
        center_lng=-81.3784,
        zoom=11.4,
        bbox=CANTON_DIVISION_BBOXES["CANTON_CORE"],
        submarkets=list(CANTON_SUBMARKETS),
        city_id="canton",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=CANTON_METRO_BBOX,
    division_bboxes=CANTON_DIVISION_BBOXES,
    submarkets=CANTON_SUBMARKETS,
    divisions=CANTON_DIVISIONS,
    contains=is_in_canton_metro,
)
