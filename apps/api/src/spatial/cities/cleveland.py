"""Cleveland / Cuyahoga County, Ohio spatial registry and geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

CLEVELAND_METRO_BBOX: dict[str, float] = {
    "min_lat": 41.30,
    "max_lat": 41.65,
    "min_lng": -81.95,
    "max_lng": -81.50,
}

CLEVELAND_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "CLEVELAND_CORE": {
        "min_lat": 41.35,
        "max_lat": 41.60,
        "min_lng": -81.90,
        "max_lng": -81.55,
    },
}


def is_in_cleveland_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Cleveland extent."""
    if lat is None or lng is None:
        return False
    return (
        CLEVELAND_METRO_BBOX["min_lat"] <= lat <= CLEVELAND_METRO_BBOX["max_lat"]
        and CLEVELAND_METRO_BBOX["min_lng"] <= lng <= CLEVELAND_METRO_BBOX["max_lng"]
    )


CLEVELAND_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Flats": SubmarketMeta(
        name="Downtown & Flats",
        borough="CLEVELAND_CORE",
        lat=41.4993,
        lng=-81.6944,
        zoom=13.2,
        pitch=48.0,
        base_lims=0.85,
        capex=7800000.0,
        permit_vel=37.0,
        shift_ratio=1.43,
        sla=57.0,
        description="Lakefront civic core and riverfront Flats with adaptive reuse, hospitality, and mixed-use redevelopment.",
        city_id="cleveland",
    ),
    "Ohio City & Tremont": SubmarketMeta(
        name="Ohio City & Tremont",
        borough="CLEVELAND_CORE",
        lat=41.4839,
        lng=-81.7049,
        zoom=13.4,
        pitch=46.0,
        base_lims=0.86,
        capex=6900000.0,
        permit_vel=39.0,
        shift_ratio=1.46,
        sla=56.0,
        description="West-side historic neighborhoods with restaurant, residential, and small-scale commercial infill.",
        city_id="cleveland",
    ),
    "University Circle & Fairfax": SubmarketMeta(
        name="University Circle & Fairfax",
        borough="CLEVELAND_CORE",
        lat=41.5088,
        lng=-81.6045,
        zoom=13.1,
        pitch=44.0,
        base_lims=0.82,
        capex=6200000.0,
        permit_vel=33.0,
        shift_ratio=1.39,
        sla=55.0,
        description="Institutional and arts anchor with medical expansion, neighborhood reinvestment, and multifamily demand.",
        city_id="cleveland",
    ),
    "Detroit-Shoreway & Edgewater": SubmarketMeta(
        name="Detroit-Shoreway & Edgewater",
        borough="CLEVELAND_CORE",
        lat=41.4642,
        lng=-81.7350,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.79,
        capex=5400000.0,
        permit_vel=31.0,
        shift_ratio=1.37,
        sla=54.0,
        description="Near-west lakefront corridor combining arts districts, neighborhood retail, and housing rehabilitation.",
        city_id="cleveland",
    ),
    "Slavic Village & Broadway": SubmarketMeta(
        name="Slavic Village & Broadway",
        borough="CLEVELAND_CORE",
        lat=41.4650,
        lng=-81.6750,
        zoom=12.9,
        pitch=42.0,
        base_lims=0.76,
        capex=4300000.0,
        permit_vel=27.0,
        shift_ratio=1.34,
        sla=52.0,
        description="South-side reinvestment corridor with historic housing stock, neighborhood commercial, and infill opportunity.",
        city_id="cleveland",
    ),
}


CLEVELAND_DIVISIONS: dict[str, BoroughMeta] = {
    "CLEVELAND_CORE": BoroughMeta(
        name="Cleveland Core",
        center_lat=41.4993,
        center_lng=-81.6944,
        zoom=11.8,
        bbox=CLEVELAND_DIVISION_BBOXES["CLEVELAND_CORE"],
        submarkets=list(CLEVELAND_SUBMARKETS),
        city_id="cleveland",
    ),
}
