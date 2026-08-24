"""Cincinnati, Ohio spatial registry and dashboard geometry."""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta


CINCINNATI_METRO_BBOX: Dict[str, float] = {
    "min_lat": 38.80,
    "max_lat": 39.45,
    "min_lng": -84.95,
    "max_lng": -84.15,
}

CINCINNATI_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "CINCINNATI_CORE": {
        "min_lat": 39.00,
        "max_lat": 39.20,
        "min_lng": -84.70,
        "max_lng": -84.35,
    },
}


def is_in_cincinnati_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Cincinnati extent."""
    if lat is None or lng is None:
        return False
    return (
        CINCINNATI_METRO_BBOX["min_lat"] <= lat <= CINCINNATI_METRO_BBOX["max_lat"]
        and CINCINNATI_METRO_BBOX["min_lng"] <= lng <= CINCINNATI_METRO_BBOX["max_lng"]
    )


CINCINNATI_SUBMARKETS: Dict[str, SubmarketMeta] = {
    "Downtown & Over-the-Rhine": SubmarketMeta(
        name="Downtown & Over-the-Rhine",
        borough="CINCINNATI_CORE",
        lat=39.1085,
        lng=-84.5145,
        zoom=13.8,
        pitch=48.0,
        base_lims=0.86,
        capex=8200000.0,
        permit_vel=42.0,
        shift_ratio=1.48,
        sla=62.0,
        description="Historic central-city blocks spanning the downtown business core and Over-the-Rhine mixed-use corridor.",
        city_id="cincinnati",
    ),
    "Uptown & Clifton": SubmarketMeta(
        name="Uptown & Clifton",
        borough="CINCINNATI_CORE",
        lat=39.1390,
        lng=-84.5150,
        zoom=13.6,
        pitch=44.0,
        base_lims=0.82,
        capex=6100000.0,
        permit_vel=35.0,
        shift_ratio=1.42,
        sla=58.0,
        description="University and medical-institution district north of downtown with dense rental and neighborhood retail demand.",
        city_id="cincinnati",
    ),
    "West End & Queensgate": SubmarketMeta(
        name="West End & Queensgate",
        borough="CINCINNATI_CORE",
        lat=39.1050,
        lng=-84.5380,
        zoom=13.6,
        pitch=44.0,
        base_lims=0.79,
        capex=5400000.0,
        permit_vel=31.0,
        shift_ratio=1.38,
        sla=55.0,
        description="West-side redevelopment edge between the central city, stadium district, and industrial riverfront.",
        city_id="cincinnati",
    ),
}

CINCINNATI_DIVISIONS: Dict[str, BoroughMeta] = {
    "CINCINNATI_CORE": BoroughMeta(
        name="Cincinnati Core",
        center_lat=39.1085,
        center_lng=-84.5145,
        zoom=12.8,
        bbox=CINCINNATI_DIVISION_BBOXES["CINCINNATI_CORE"],
        submarkets=list(CINCINNATI_SUBMARKETS),
        city_id="cincinnati",
    ),
}
