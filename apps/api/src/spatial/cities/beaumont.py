"""Beaumont, Texas spatial registry and dashboard geometry (South Central)."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Golden Triangle core around Beaumont; permissive bbox that keeps
# Beaumont proper plus near-ring communities without spanning the full MSA.
BEAUMONT_METRO_BBOX: dict[str, float] = {
    "min_lat": 29.90,
    "max_lat": 30.20,
    "min_lng": -94.30,
    "max_lng": -93.85,
}

# Single-division initial cut; additional divisions can be split later
# without breaking invariants so long as submarkets remain contained.
BEAUMONT_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "BEAUMONT_CORE": {
        "min_lat": 29.95,
        "max_lat": 30.18,
        "min_lng": -94.25,
        "max_lng": -93.90,
    },
}


def is_in_beaumont_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Beaumont extent."""
    if lat is None or lng is None:
        return False
    return (
        BEAUMONT_METRO_BBOX["min_lat"] <= lat <= BEAUMONT_METRO_BBOX["max_lat"]
        and BEAUMONT_METRO_BBOX["min_lng"] <= lng <= BEAUMONT_METRO_BBOX["max_lng"]
    )


BEAUMONT_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown Beaumont": SubmarketMeta(
        name="Downtown Beaumont",
        borough="BEAUMONT_CORE",
        lat=30.0840,
        lng=-94.1010,
        zoom=13.6,
        pitch=48.0,
        base_lims=0.84,
        capex=6800000.0,
        permit_vel=32.0,
        shift_ratio=1.42,
        sla=57.0,
        description="Civic and riverfront core around Crockett Street, Edison Museum, and Downtown arts venues.",
        city_id="beaumont",
    ),
    "West End": SubmarketMeta(
        name="West End",
        borough="BEAUMONT_CORE",
        lat=30.1000,
        lng=-94.1660,
        zoom=13.4,
        pitch=46.0,
        base_lims=0.83,
        capex=6400000.0,
        permit_vel=30.0,
        shift_ratio=1.40,
        sla=55.0,
        description="Retail and residential corridor around Dowlen Road and Phelan with steady renovation activity.",
        city_id="beaumont",
    ),
    "South Park": SubmarketMeta(
        name="South Park",
        borough="BEAUMONT_CORE",
        lat=30.0410,
        lng=-94.1220,
        zoom=13.4,
        pitch=46.0,
        base_lims=0.81,
        capex=5600000.0,
        permit_vel=27.0,
        shift_ratio=1.36,
        sla=53.0,
        description="Neighborhoods south of US-90 with university-adjacent housing stock and service demand.",
        city_id="beaumont",
    ),
    "North End": SubmarketMeta(
        name="North End",
        borough="BEAUMONT_CORE",
        lat=30.1100,
        lng=-94.1160,
        zoom=13.2,
        pitch=44.0,
        base_lims=0.82,
        capex=5900000.0,
        permit_vel=28.0,
        shift_ratio=1.38,
        sla=54.0,
        description="Historic residential grid north of downtown with rehabilitation pressure and code-enforcement load.",
        city_id="beaumont",
    ),
    "Calder Highlands": SubmarketMeta(
        name="Calder Highlands",
        borough="BEAUMONT_CORE",
        lat=30.0840,
        lng=-94.1480,
        zoom=13.2,
        pitch=44.0,
        base_lims=0.83,
        capex=6000000.0,
        permit_vel=29.0,
        shift_ratio=1.39,
        sla=54.0,
        description="Calder Avenue corridor and established neighborhoods with infill and alteration permits.",
        city_id="beaumont",
    ),
}

BEAUMONT_DIVISIONS: dict[str, BoroughMeta] = {
    "BEAUMONT_CORE": BoroughMeta(
        name="Beaumont Core",
        center_lat=30.0840,
        center_lng=-94.1300,
        zoom=11.8,
        bbox=BEAUMONT_DIVISION_BBOXES["BEAUMONT_CORE"],
        submarkets=list(BEAUMONT_SUBMARKETS),
        city_id="beaumont",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=BEAUMONT_METRO_BBOX,
    division_bboxes=BEAUMONT_DIVISION_BBOXES,
    submarkets=BEAUMONT_SUBMARKETS,
    divisions=BEAUMONT_DIVISIONS,
    contains=is_in_beaumont_metro,
)

__all__ = [
    "BEAUMONT_DIVISION_BBOXES",
    "BEAUMONT_DIVISIONS",
    "BEAUMONT_METRO_BBOX",
    "BEAUMONT_SUBMARKETS",
    "REGISTRATION",
    "is_in_beaumont_metro",
]

