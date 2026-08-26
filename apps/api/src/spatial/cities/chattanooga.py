"""Chattanooga / Hamilton County, Tennessee spatial registry and geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

CHATTANOOGA_METRO_BBOX: dict[str, float] = {
    "min_lat": 34.98,
    "max_lat": 35.45,
    "min_lng": -85.50,
    "max_lng": -84.95,
}

CHATTANOOGA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "CHATTANOOGA_CORE": {
        "min_lat": 35.00,
        "max_lat": 35.35,
        "min_lng": -85.40,
        "max_lng": -85.05,
    },
}


def is_in_chattanooga_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the Hamilton County extent."""
    if lat is None or lng is None:
        return False
    return (
        CHATTANOOGA_METRO_BBOX["min_lat"] <= lat <= CHATTANOOGA_METRO_BBOX["max_lat"]
        and CHATTANOOGA_METRO_BBOX["min_lng"] <= lng <= CHATTANOOGA_METRO_BBOX["max_lng"]
    )


CHATTANOOGA_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Southside": SubmarketMeta(
        name="Downtown & Southside",
        borough="CHATTANOOGA_CORE",
        lat=35.0456,
        lng=-85.3097,
        zoom=13.5,
        pitch=48.0,
        base_lims=0.84,
        capex=7200000.0,
        permit_vel=38.0,
        shift_ratio=1.42,
        sla=58.0,
        description="Riverfront civic core and Southside warehouse district with adaptive reuse, hospitality, and multifamily infill.",
        city_id="chattanooga",
    ),
    "North Shore": SubmarketMeta(
        name="North Shore",
        borough="CHATTANOOGA_CORE",
        lat=35.0750,
        lng=-85.3150,
        zoom=13.1,
        pitch=44.0,
        base_lims=0.80,
        capex=5400000.0,
        permit_vel=31.0,
        shift_ratio=1.37,
        sla=55.0,
        description="Market Street and Frazier Avenue neighborhood retail corridor across the Tennessee River from downtown.",
        city_id="chattanooga",
    ),
    "East Chattanooga & Highland Park": SubmarketMeta(
        name="East Chattanooga & Highland Park",
        borough="CHATTANOOGA_CORE",
        lat=35.0520,
        lng=-85.2650,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.78,
        capex=4300000.0,
        permit_vel=28.0,
        shift_ratio=1.34,
        sla=53.0,
        description="Historic east-side neighborhoods with small-scale rehabilitation, neighborhood retail, and infill activity.",
        city_id="chattanooga",
    ),
    "East Brainerd": SubmarketMeta(
        name="East Brainerd",
        borough="CHATTANOOGA_CORE",
        lat=35.0120,
        lng=-85.1700,
        zoom=12.7,
        pitch=42.0,
        base_lims=0.79,
        capex=6100000.0,
        permit_vel=34.0,
        shift_ratio=1.39,
        sla=56.0,
        description="Southeast growth corridor where retail, medical, and residential development meet the Hamilton County edge.",
        city_id="chattanooga",
    ),
    "Hixson": SubmarketMeta(
        name="Hixson",
        borough="CHATTANOOGA_CORE",
        lat=35.1300,
        lng=-85.2350,
        zoom=12.8,
        pitch=42.0,
        base_lims=0.77,
        capex=5000000.0,
        permit_vel=29.0,
        shift_ratio=1.35,
        sla=54.0,
        description="North-of-river commercial corridor with suburban redevelopment, medical services, and mixed-use reinvestment.",
        city_id="chattanooga",
    ),
}


CHATTANOOGA_DIVISIONS: dict[str, BoroughMeta] = {
    "CHATTANOOGA_CORE": BoroughMeta(
        name="Chattanooga Core",
        center_lat=35.0456,
        center_lng=-85.3097,
        zoom=11.8,
        bbox=CHATTANOOGA_DIVISION_BBOXES["CHATTANOOGA_CORE"],
        submarkets=list(CHATTANOOGA_SUBMARKETS),
        city_id="chattanooga",
    ),
}
