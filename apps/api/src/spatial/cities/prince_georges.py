"""Prince George's County, Maryland spatial registry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

PRINCE_GEORGES_METRO_BBOX: dict[str, float] = {
    "min_lat": 38.55,
    "max_lat": 39.22,
    "min_lng": -77.12,
    "max_lng": -76.62,
}

PRINCE_GEORGES_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "PRINCE_GEORGES_CORE": {
        "min_lat": 38.60,
        "max_lat": 39.05,
        "min_lng": -77.05,
        "max_lng": -76.70,
    },
}

def is_in_prince_georges_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered county extent."""
    if lat is None or lng is None:
        return False
    return (
        PRINCE_GEORGES_METRO_BBOX["min_lat"] <= lat <= PRINCE_GEORGES_METRO_BBOX["max_lat"]
        and PRINCE_GEORGES_METRO_BBOX["min_lng"] <= lng <= PRINCE_GEORGES_METRO_BBOX["max_lng"]
    )

PRINCE_GEORGES_SUBMARKETS: dict[str, SubmarketMeta] = {
    "National Harbor & Oxon Hill": SubmarketMeta(
        name="National Harbor & Oxon Hill",
        borough="PRINCE_GEORGES_CORE",
        lat=38.7830,
        lng=-76.9820,
        zoom=13.8,
        pitch=50.0,
        base_lims=0.82,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.41,
        sla=58.0,
        description="Potomac waterfront mixed-use district anchored by the convention center and casino, with hotel-adjacent retail and residential demand.",
        city_id="prince_georges",
    ),
    "Largo & Landover Core": SubmarketMeta(
        name="Largo & Landover Core",
        borough="PRINCE_GEORGES_CORE",
        lat=38.8700,
        lng=-76.8400,
        zoom=13.2,
        pitch=46.0,
        base_lims=0.79,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.38,
        sla=55.0,
        description="Blue Line office and medical corridor around Largo Town Center and the new regional hospital, with county-government anchoring.",
        city_id="prince_georges",
    ),
    "Bowie & South Laurel": SubmarketMeta(
        name="Bowie & South Laurel",
        borough="PRINCE_GEORGES_CORE",
        lat=38.9420,
        lng=-76.7300,
        zoom=12.8,
        pitch=44.0,
        base_lims=0.76,
        capex=4600000.0,
        permit_vel=27.0,
        shift_ratio=1.33,
        sla=52.0,
        description="Suburban family belt along the Route 197 and US-1 north corridors, dominated by single-family stock and town-center retail.",
        city_id="prince_georges",
    ),
    "College Park & Route 1": SubmarketMeta(
        name="College Park & Route 1",
        borough="PRINCE_GEORGES_CORE",
        lat=38.9900,
        lng=-76.9300,
        zoom=13.4,
        pitch=48.0,
        base_lims=0.84,
        capex=5000000.0,
        permit_vel=34.0,
        shift_ratio=1.45,
        sla=60.0,
        description="University of Maryland anchor market with student rental demand, research-park employment, and Purple Line construction activity.",
        city_id="prince_georges",
    ),
}

PRINCE_GEORGES_DIVISIONS: dict[str, BoroughMeta] = {
    "PRINCE_GEORGES_CORE": BoroughMeta(
        name="Prince Georges County",
        center_lat=38.72,
        center_lng=-76.75,
        zoom=10.6,
        bbox=PRINCE_GEORGES_DIVISION_BBOXES["PRINCE_GEORGES_CORE"],
        submarkets=list(PRINCE_GEORGES_SUBMARKETS),
        city_id="prince_georges",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=PRINCE_GEORGES_METRO_BBOX,
    division_bboxes=PRINCE_GEORGES_DIVISION_BBOXES,
    submarkets=PRINCE_GEORGES_SUBMARKETS,
    divisions=PRINCE_GEORGES_DIVISIONS,
    contains=is_in_prince_georges_metro,
)
