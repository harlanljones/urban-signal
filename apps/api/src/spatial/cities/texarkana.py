"""Texarkana, TX-AR — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
are currently limited to SNAP Retailers (TX slice) pending verifiable public
municipal permits endpoints for both sides of the bi-state metro (US-282).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

TEXARKANA_CITY_ID: str = "texarkana"

# Approximate Texarkana metro extents: generous box covering both the Texas and
# Arkansas sides centered on State Line Ave. Downtown is around (33.425, -94.048).
TEXARKANA_METRO_BBOX: Dict[str, float] = {
    "min_lat": 33.35,
    "max_lat": 33.60,
    "min_lng": -94.30,
    "max_lng": -93.90,
}

# Registration-contract center: Bi-State Justice Building vicinity near State Line Ave.
TEXARKANA_CENTER: Dict[str, float] = {"lat": 33.4251, "lng": -94.0477}

# Division bounding boxes (strict subsets of TEXARKANA_METRO_BBOX)
TEXARKANA_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown core straddling State Line Ave
    "CENTRAL_CORE": {"min_lat": 33.410, "max_lat": 33.450, "min_lng": -94.080, "max_lng": -94.020},
    # Texas-side commercial corridors west of the core (includes Wake Village/Nash)
    "TEXAS_WEST": {"min_lat": 33.400, "max_lat": 33.490, "min_lng": -94.250, "max_lng": -94.120},
    # Arkansas-side neighborhoods and Broad/Arkansas Blvd corridors
    "ARKANSAS_EAST": {"min_lat": 33.410, "max_lat": 33.500, "min_lng": -94.060, "max_lng": -93.950},
    # I-30 corridor nodes (Richmond Rd, Summerhill)
    "I30_CORRIDOR": {"min_lat": 33.450, "max_lat": 33.520, "min_lng": -94.200, "max_lng": -94.050},
    # South belt retail along State Line/US-71/US-82
    "SOUTH_STRIP": {"min_lat": 33.350, "max_lat": 33.420, "min_lng": -94.100, "max_lng": -94.000},
}


def is_in_texarkana_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Texarkana metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        TEXARKANA_METRO_BBOX["min_lat"] <= lat <= TEXARKANA_METRO_BBOX["max_lat"]
        and TEXARKANA_METRO_BBOX["min_lng"] <= lng <= TEXARKANA_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
TEXARKANA_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown State Line": SubmarketMeta(
        name="Downtown State Line",
        borough="CENTRAL_CORE",
        lat=33.4300,
        lng=-94.0460,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.80,
        capex=5200000.0,
        permit_vel=22.0,
        shift_ratio=1.20,
        sla=46.0,
        description="Historic downtown straddling State Line Ave with civic anchors and hospitality infill.",
        city_id=TEXARKANA_CITY_ID,
    ),
    "Texas Blvd & 7th St": SubmarketMeta(
        name="Texas Blvd & 7th St",
        borough="CENTRAL_CORE",
        lat=33.4240,
        lng=-94.0520,
        zoom=14.8,
        pitch=45.0,
        base_lims=0.79,
        capex=5000000.0,
        permit_vel=21.0,
        shift_ratio=1.18,
        sla=44.0,
        description="West-of-core crossroads with small-format retail and services.",
        city_id=TEXARKANA_CITY_ID,
    ),
    # I30_CORRIDOR
    "I-30 at Richmond Rd": SubmarketMeta(
        name="I-30 at Richmond Rd",
        borough="I30_CORRIDOR",
        lat=33.4760,
        lng=-94.1690,
        zoom=14.2,
        pitch=42.0,
        base_lims=0.76,
        capex=4800000.0,
        permit_vel=20.0,
        shift_ratio=1.16,
        sla=44.0,
        description="Regional retail node and hospitality cluster at Richmond Rd & I-30.",
        city_id=TEXARKANA_CITY_ID,
    ),
    "I-30 at Summerhill": SubmarketMeta(
        name="I-30 at Summerhill",
        borough="I30_CORRIDOR",
        lat=33.4620,
        lng=-94.0740,
        zoom=14.2,
        pitch=42.0,
        base_lims=0.75,
        capex=4700000.0,
        permit_vel=19.0,
        shift_ratio=1.15,
        sla=44.0,
        description="Interchange commercial cluster with auto-oriented retail and services.",
        city_id=TEXARKANA_CITY_ID,
    ),
    # TEXAS_WEST
    "Wake Village & Nash": SubmarketMeta(
        name="Wake Village & Nash",
        borough="TEXAS_WEST",
        lat=33.4300,
        lng=-94.1700,
        zoom=13.6,
        pitch=40.0,
        base_lims=0.73,
        capex=4300000.0,
        permit_vel=18.0,
        shift_ratio=1.14,
        sla=42.0,
        description="West-side suburban municipalities with industrial and highway services.",
        city_id=TEXARKANA_CITY_ID,
    ),
    # ARKANSAS_EAST
    "Broad St & Arkansas Blvd": SubmarketMeta(
        name="Broad St & Arkansas Blvd",
        borough="ARKANSAS_EAST",
        lat=33.4410,
        lng=-94.0330,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.72,
        capex=4200000.0,
        permit_vel=18.0,
        shift_ratio=1.12,
        sla=42.0,
        description="Arkansas-side commercial corridor and civic services east of State Line Ave.",
        city_id=TEXARKANA_CITY_ID,
    ),
    "East Arkansas Industrial": SubmarketMeta(
        name="East Arkansas Industrial",
        borough="ARKANSAS_EAST",
        lat=33.4670,
        lng=-93.9950,
        zoom=13.6,
        pitch=38.0,
        base_lims=0.70,
        capex=4000000.0,
        permit_vel=17.0,
        shift_ratio=1.10,
        sla=42.0,
        description="Industrial/logistics clusters along Oats/Arkansas Blvd towards the airport approach.",
        city_id=TEXARKANA_CITY_ID,
    ),
    # SOUTH_STRIP
    "South State Line Retail": SubmarketMeta(
        name="South State Line Retail",
        borough="SOUTH_STRIP",
        lat=33.3990,
        lng=-94.0420,
        zoom=13.8,
        pitch=38.0,
        base_lims=0.71,
        capex=4100000.0,
        permit_vel=17.0,
        shift_ratio=1.10,
        sla=42.0,
        description="Auto-oriented retail and services belt along State Line/US-71/US-82.",
        city_id=TEXARKANA_CITY_ID,
    ),
}


TEXARKANA_DIVISIONS: Dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=33.4280,
        center_lng=-94.0460,
        zoom=13.8,
        bbox=TEXARKANA_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in TEXARKANA_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=TEXARKANA_CITY_ID,
    ),
    "TEXAS_WEST": BoroughMeta(
        name="TEXAS_WEST",
        center_lat=33.4350,
        center_lng=-94.1850,
        zoom=13.2,
        bbox=TEXARKANA_DIVISION_BBOXES["TEXAS_WEST"],
        submarkets=[k for k, v in TEXARKANA_SUBMARKETS.items() if v.borough == "TEXAS_WEST"],
        city_id=TEXARKANA_CITY_ID,
    ),
    "ARKANSAS_EAST": BoroughMeta(
        name="ARKANSAS_EAST",
        center_lat=33.4550,
        center_lng=-94.0150,
        zoom=13.2,
        bbox=TEXARKANA_DIVISION_BBOXES["ARKANSAS_EAST"],
        submarkets=[k for k, v in TEXARKANA_SUBMARKETS.items() if v.borough == "ARKANSAS_EAST"],
        city_id=TEXARKANA_CITY_ID,
    ),
    "I30_CORRIDOR": BoroughMeta(
        name="I30_CORRIDOR",
        center_lat=33.4700,
        center_lng=-94.1400,
        zoom=13.2,
        bbox=TEXARKANA_DIVISION_BBOXES["I30_CORRIDOR"],
        submarkets=[k for k, v in TEXARKANA_SUBMARKETS.items() if v.borough == "I30_CORRIDOR"],
        city_id=TEXARKANA_CITY_ID,
    ),
    "SOUTH_STRIP": BoroughMeta(
        name="SOUTH_STRIP",
        center_lat=33.3950,
        center_lng=-94.0550,
        zoom=13.2,
        bbox=TEXARKANA_DIVISION_BBOXES["SOUTH_STRIP"],
        submarkets=[k for k, v in TEXARKANA_SUBMARKETS.items() if v.borough == "SOUTH_STRIP"],
        city_id=TEXARKANA_CITY_ID,
    ),
}

TEXARKANA_DIVISION_BBOXES_EXPORT = TEXARKANA_DIVISION_BBOXES
TEXARKANA_SUBMARKETS_EXPORT = TEXARKANA_SUBMARKETS
TEXARKANA_DIVISIONS_EXPORT = TEXARKANA_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=TEXARKANA_METRO_BBOX,
    division_bboxes=TEXARKANA_DIVISION_BBOXES,
    submarkets=TEXARKANA_SUBMARKETS,
    divisions=TEXARKANA_DIVISIONS,
    contains=is_in_texarkana_metro,
)

__all__ = [
    "TEXARKANA_CENTER",
    "TEXARKANA_CITY_ID",
    "TEXARKANA_DIVISION_BBOXES",
    "TEXARKANA_DIVISION_BBOXES_EXPORT",
    "TEXARKANA_DIVISIONS",
    "TEXARKANA_DIVISIONS_EXPORT",
    "TEXARKANA_METRO_BBOX",
    "TEXARKANA_SUBMARKETS",
    "TEXARKANA_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_texarkana_metro",
]

