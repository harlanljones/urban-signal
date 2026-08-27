"""Sacramento / Sacramento County spatial registry and geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

SACRAMENTO_METRO_BBOX: dict[str, float] = {
    "min_lat": 38.00,
    "max_lat": 38.80,
    "min_lng": -121.90,
    "max_lng": -121.00,
}

SACRAMENTO_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "SACRAMENTO_CORE": {
        "min_lat": 38.0184,
        "max_lat": 38.7365,
        "min_lng": -121.8627,
        "max_lng": -121.0262,
    },
}


def is_in_sacramento_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Sacramento extent."""
    if lat is None or lng is None:
        return False
    return (
        SACRAMENTO_METRO_BBOX["min_lat"] <= lat <= SACRAMENTO_METRO_BBOX["max_lat"]
        and SACRAMENTO_METRO_BBOX["min_lng"] <= lng <= SACRAMENTO_METRO_BBOX["max_lng"]
    )


SACRAMENTO_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Midtown": SubmarketMeta(
        name="Downtown & Midtown", borough="SACRAMENTO_CORE", lat=38.5816, lng=-121.4944,
        zoom=13.1, pitch=46.0, base_lims=0.83, capex=7200000.0, permit_vel=38.0,
        shift_ratio=1.40, sla=57.0,
        description="Civic and historic urban core with state employment, adaptive reuse, and mixed-use infill pressure.",
        city_id="sacramento",
    ),
    "East Sacramento & River Park": SubmarketMeta(
        name="East Sacramento & River Park", borough="SACRAMENTO_CORE", lat=38.5740, lng=-121.4380,
        zoom=12.9, pitch=44.0, base_lims=0.81, capex=6100000.0, permit_vel=32.0,
        shift_ratio=1.36, sla=55.0,
        description="Established neighborhoods balancing housing rehabilitation, river access, and small-scale redevelopment.",
        city_id="sacramento",
    ),
    "Land Park & South Sacramento": SubmarketMeta(
        name="Land Park & South Sacramento", borough="SACRAMENTO_CORE", lat=38.5240, lng=-121.4930,
        zoom=12.8, pitch=43.0, base_lims=0.78, capex=5200000.0, permit_vel=29.0,
        shift_ratio=1.33, sla=53.0,
        description="South-side residential and commercial corridors with repair, infill, and public-service demand.",
        city_id="sacramento",
    ),
    "Natomas": SubmarketMeta(
        name="Natomas", borough="SACRAMENTO_CORE", lat=38.6500, lng=-121.5100,
        zoom=12.6, pitch=41.0, base_lims=0.76, capex=6800000.0, permit_vel=35.0,
        shift_ratio=1.39, sla=54.0,
        description="Fast-growing northwestern area where residential expansion, infrastructure, and floodplain constraints intersect.",
        city_id="sacramento",
    ),
    "Arden-Arcade & North County": SubmarketMeta(
        name="Arden-Arcade & North County", borough="SACRAMENTO_CORE", lat=38.6100, lng=-121.3800,
        zoom=12.5, pitch=40.0, base_lims=0.75, capex=5700000.0, permit_vel=31.0,
        shift_ratio=1.34, sla=52.0,
        description="Unincorporated commercial and residential corridor with county permitting, retrofit, and neighborhood-service activity.",
        city_id="sacramento",
    ),
}


SACRAMENTO_DIVISIONS: dict[str, BoroughMeta] = {
    "SACRAMENTO_CORE": BoroughMeta(
        name="Sacramento / Sacramento County", center_lat=38.5816, center_lng=-121.4944, zoom=10.8,
        bbox=SACRAMENTO_DIVISION_BBOXES["SACRAMENTO_CORE"], submarkets=list(SACRAMENTO_SUBMARKETS),
        city_id="sacramento",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=SACRAMENTO_METRO_BBOX,
    division_bboxes=SACRAMENTO_DIVISION_BBOXES,
    submarkets=SACRAMENTO_SUBMARKETS,
    divisions=SACRAMENTO_DIVISIONS,
    contains=is_in_sacramento_metro,
)
