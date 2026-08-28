"""Macon-Bibb County, GA — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry).
Permits are registered from a verified ArcGIS FeatureServer layer; SLA registers
the Georgia slice of SNAP Retailers as a complementary signal.
"""

from typing import Dict

from src.spatial.registration import SpatialRegistration
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MACON_BIBB_CITY_ID: str = "macon_bibb"

# Approximate Macon-Bibb metro extents: generous box that contains the
# consolidated county (Downtown Macon through North Macon, West Bibb, East
# Macon/Ocmulgee Mounds, and the airport belt). Downtown is around (32.8366, -83.6266).
MACON_BIBB_METRO_BBOX: Dict[str, float] = {
    "min_lat": 32.670,
    "max_lat": 32.930,
    "min_lng": -83.850,
    "max_lng": -83.450,
}

# Registration-contract center: Downtown Macon (City Hall vicinity).
MACON_BIBB_CENTER: Dict[str, float] = {"lat": 32.8366, "lng": -83.6324}

# Division bounding boxes (strict subsets of MACON_BIBB_METRO_BBOX)
MACON_BIBB_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown, Riverfront/Amphitheater, Mercer University
    "DOWNTOWN_CORE": {"min_lat": 32.820, "max_lat": 32.860, "min_lng": -83.670, "max_lng": -83.600},
    # I‑475 belt, Eisenhower Pkwy corridor, West Bibb commercial ribbons
    "WEST_MACON": {"min_lat": 32.790, "max_lat": 32.870, "min_lng": -83.850, "max_lng": -83.680},
    # Bass Rd / Riverside Dr retail, North Macon neighborhoods
    "NORTH_MACON": {"min_lat": 32.870, "max_lat": 32.930, "min_lng": -83.780, "max_lng": -83.580},
    # Ocmulgee Mounds / East Macon / Emery Hwy corridor
    "EAST_MACON": {"min_lat": 32.800, "max_lat": 32.900, "min_lng": -83.620, "max_lng": -83.450},
    # South Bibb / Middle Georgia Regional Airport vicinity
    "SOUTH_BIBB": {"min_lat": 32.670, "max_lat": 32.800, "min_lng": -83.780, "max_lng": -83.550},
}


def is_in_macon_bibb_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Macon-Bibb metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        MACON_BIBB_METRO_BBOX["min_lat"] <= lat <= MACON_BIBB_METRO_BBOX["max_lat"]
        and MACON_BIBB_METRO_BBOX["min_lng"] <= lng <= MACON_BIBB_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
MACON_BIBB_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # DOWNTOWN_CORE
    "Downtown Macon": SubmarketMeta(
        name="Downtown Macon",
        borough="DOWNTOWN_CORE",
        lat=32.8366,
        lng=-83.6266,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.82,
        capex=5200000.0,
        permit_vel=28.0,
        shift_ratio=1.26,
        sla=55.0,
        description="Historic core along Cherry, Poplar, and 2nd Street with adaptive reuse and hospitality momentum.",
        city_id=MACON_BIBB_CITY_ID,
    ),
    "Riverfront & Amphitheater": SubmarketMeta(
        name="Riverfront & Amphitheater",
        borough="DOWNTOWN_CORE",
        lat=32.8340,
        lng=-83.6210,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.80,
        capex=4800000.0,
        permit_vel=26.0,
        shift_ratio=1.22,
        sla=52.0,
        description="Ocmulgee riverfront entertainment and open-space anchors at the downtown edge.",
        city_id=MACON_BIBB_CITY_ID,
    ),
    "Mercer University District": SubmarketMeta(
        name="Mercer University District",
        borough="DOWNTOWN_CORE",
        lat=32.8287,
        lng=-83.6513,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.78,
        capex=4500000.0,
        permit_vel=24.0,
        shift_ratio=1.20,
        sla=50.0,
        description="Campus-adjacent mixed-use and student housing southwest of downtown.",
        city_id=MACON_BIBB_CITY_ID,
    ),
    # WEST_MACON
    "Eisenhower Parkway Corridor": SubmarketMeta(
        name="Eisenhower Parkway Corridor",
        borough="WEST_MACON",
        lat=32.8060,
        lng=-83.6900,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.74,
        capex=4100000.0,
        permit_vel=22.0,
        shift_ratio=1.18,
        sla=48.0,
        description="Eisenhower retail and commercial corridor including redevelopment around the mall.",
        city_id=MACON_BIBB_CITY_ID,
    ),
    "I-475 West Industrial": SubmarketMeta(
        name="I-475 West Industrial",
        borough="WEST_MACON",
        lat=32.8230,
        lng=-83.7570,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.72,
        capex=3800000.0,
        permit_vel=20.0,
        shift_ratio=1.16,
        sla=46.0,
        description="Industrial and logistics ribbon near I‑475 with hospitality and highway services.",
        city_id=MACON_BIBB_CITY_ID,
    ),
    # NORTH_MACON
    "North Macon Retail (Bass Rd)": SubmarketMeta(
        name="North Macon Retail (Bass Rd)",
        borough="NORTH_MACON",
        lat=32.9120,
        lng=-83.7180,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.76,
        capex=4300000.0,
        permit_vel=23.0,
        shift_ratio=1.20,
        sla=49.0,
        description="Bass Road / Riverside Drive retail concentration and adjacent residential growth.",
        city_id=MACON_BIBB_CITY_ID,
    ),
    # EAST_MACON
    "Ocmulgee Mounds / East Macon": SubmarketMeta(
        name="Ocmulgee Mounds / East Macon",
        borough="EAST_MACON",
        lat=32.8348,
        lng=-83.6020,
        zoom=13.8,
        pitch=40.0,
        base_lims=0.70,
        capex=3500000.0,
        permit_vel=19.0,
        shift_ratio=1.14,
        sla=45.0,
        description="Emery Hwy corridor and Ocmulgee Mounds vicinity east of downtown.",
        city_id=MACON_BIBB_CITY_ID,
    ),
    # SOUTH_BIBB
    "Airport & Industrial South": SubmarketMeta(
        name="Airport & Industrial South",
        borough="SOUTH_BIBB",
        lat=32.6930,
        lng=-83.6490,
        zoom=13.2,
        pitch=38.0,
        base_lims=0.68,
        capex=3200000.0,
        permit_vel=18.0,
        shift_ratio=1.12,
        sla=44.0,
        description="Middle Georgia Regional Airport area and adjacent industrial parks.",
        city_id=MACON_BIBB_CITY_ID,
    ),
}


MACON_BIBB_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=32.8380,
        center_lng=-83.6280,
        zoom=13.8,
        bbox=MACON_BIBB_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in MACON_BIBB_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id=MACON_BIBB_CITY_ID,
    ),
    "WEST_MACON": BoroughMeta(
        name="WEST_MACON",
        center_lat=32.8300,
        center_lng=-83.7350,
        zoom=13.2,
        bbox=MACON_BIBB_DIVISION_BBOXES["WEST_MACON"],
        submarkets=[k for k, v in MACON_BIBB_SUBMARKETS.items() if v.borough == "WEST_MACON"],
        city_id=MACON_BIBB_CITY_ID,
    ),
    "NORTH_MACON": BoroughMeta(
        name="NORTH_MACON",
        center_lat=32.9000,
        center_lng=-83.6800,
        zoom=12.9,
        bbox=MACON_BIBB_DIVISION_BBOXES["NORTH_MACON"],
        submarkets=[k for k, v in MACON_BIBB_SUBMARKETS.items() if v.borough == "NORTH_MACON"],
        city_id=MACON_BIBB_CITY_ID,
    ),
    "EAST_MACON": BoroughMeta(
        name="EAST_MACON",
        center_lat=32.8500,
        center_lng=-83.5600,
        zoom=13.2,
        bbox=MACON_BIBB_DIVISION_BBOXES["EAST_MACON"],
        submarkets=[k for k, v in MACON_BIBB_SUBMARKETS.items() if v.borough == "EAST_MACON"],
        city_id=MACON_BIBB_CITY_ID,
    ),
    "SOUTH_BIBB": BoroughMeta(
        name="SOUTH_BIBB",
        center_lat=32.7350,
        center_lng=-83.6600,
        zoom=12.8,
        bbox=MACON_BIBB_DIVISION_BBOXES["SOUTH_BIBB"],
        submarkets=[k for k, v in MACON_BIBB_SUBMARKETS.items() if v.borough == "SOUTH_BIBB"],
        city_id=MACON_BIBB_CITY_ID,
    ),
}

MACON_BIBB_DIVISION_BBOXES_EXPORT = MACON_BIBB_DIVISION_BBOXES
MACON_BIBB_SUBMARKETS_EXPORT = MACON_BIBB_SUBMARKETS
MACON_BIBB_DIVISIONS_EXPORT = MACON_BIBB_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=MACON_BIBB_METRO_BBOX,
    division_bboxes=MACON_BIBB_DIVISION_BBOXES,
    submarkets=MACON_BIBB_SUBMARKETS,
    divisions=MACON_BIBB_DIVISIONS,
    contains=is_in_macon_bibb_metro,
)

__all__ = [
    "MACON_BIBB_CENTER",
    "MACON_BIBB_CITY_ID",
    "MACON_BIBB_DIVISION_BBOXES",
    "MACON_BIBB_DIVISION_BBOXES_EXPORT",
    "MACON_BIBB_DIVISIONS",
    "MACON_BIBB_DIVISIONS_EXPORT",
    "MACON_BIBB_METRO_BBOX",
    "MACON_BIBB_SUBMARKETS",
    "MACON_BIBB_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_macon_bibb_metro",
]

