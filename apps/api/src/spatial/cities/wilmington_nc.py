"""Wilmington, NC (New Hanover County) — Urban Signal spatial registration.

Leaf module: geometry only (metro bbox, divisions, submarkets, containment).
Feed specs live in the spine registry. Verified public permits feed exists on
the New Hanover County ArcGIS server and will be registered in REGISTRY.
"""

from typing import Dict, List

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

WILMINGTON_NC_CITY_ID: str = "wilmington_nc"

# Approximate Wilmington / New Hanover County extents. Bounds encompass
# Wilmington proper, Wrightsville Beach, Carolina Beach/Kure Beach, and the
# west-of-river employment belt to the Leland gateway while staying tight
# enough for clean division nesting.
WILMINGTON_NC_METRO_BBOX: Dict[str, float] = {
    "min_lat": 33.92,
    "max_lat": 34.39,
    "min_lng": -78.10,
    "max_lng": -77.70,
}

# Registration-contract center: Downtown Wilmington (Riverwalk vicinity).
WILMINGTON_NC_CENTER: Dict[str, float] = {"lat": 34.235, "lng": -77.948}

# Division bounding boxes (strict subsets of WILMINGTON_NC_METRO_BBOX).
WILMINGTON_NC_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown core and riverfront warehouse/port-adjacent districts
    "DOWNTOWN_RIVERFRONT": {"min_lat": 34.20, "max_lat": 34.26, "min_lng": -77.97, "max_lng": -77.90},
    # Northside growth belt: Murrayville, Northchase, Ogden/Porters Neck inland
    "NORTH_SIDE": {"min_lat": 34.26, "max_lat": 34.38, "min_lng": -77.98, "max_lng": -77.85},
    # West-of-river employment/industrial belt toward Leland/Navassa
    "WEST_SIDE": {"min_lat": 34.20, "max_lat": 34.32, "min_lng": -78.10, "max_lng": -77.98},
    # Beaches barrier island + east corridor (Wrightsville + Eastwood/Mayfaire)
    # West edge abuts DOWNTOWN_RIVERFRONT (-77.90) so UNCW & Eastwood, which sits
    # at -77.87, falls inside its own division rather than in the gap between them.
    "BEACHES": {"min_lat": 34.15, "max_lat": 34.25, "min_lng": -77.90, "max_lng": -77.70},
    # Southern Cape Fear / Shipyard Blvd, Carolina Beach, Kure Beach
    # East edge reaches -77.88 so Carolina Beach and Kure Beach, the barrier-island
    # towns this division is named for, sit inside it.
    "SOUTH_CAPE_FEAR": {"min_lat": 33.95, "max_lat": 34.20, "min_lng": -78.05, "max_lng": -77.88},
}


def is_in_wilmington_nc_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate lies within the Wilmington metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        WILMINGTON_NC_METRO_BBOX["min_lat"] <= lat <= WILMINGTON_NC_METRO_BBOX["max_lat"]
        and WILMINGTON_NC_METRO_BBOX["min_lng"] <= lng <= WILMINGTON_NC_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set per division; coordinates must lie within
# their division box for interlock containment).
WILMINGTON_NC_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # DOWNTOWN_RIVERFRONT
    "Downtown Wilmington": SubmarketMeta(
        name="Downtown Wilmington",
        borough="DOWNTOWN_RIVERFRONT",
        lat=34.236,
        lng=-77.949,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.82,
        capex=6200000.0,
        permit_vel=34.0,
        shift_ratio=1.34,
        sla=56.0,
        description="Historic core and Riverwalk district with adaptive reuse and hospitality infill.",
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    "Riverwalk & Castle Street": SubmarketMeta(
        name="Riverwalk & Castle Street",
        borough="DOWNTOWN_RIVERFRONT",
        lat=34.230,
        lng=-77.942,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.80,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.30,
        sla=54.0,
        description="Southern downtown corridor with small-scale mixed-use and streetscape reinvestment.",
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    # NORTH_SIDE
    "Northchase & Murrayville": SubmarketMeta(
        name="Northchase & Murrayville",
        borough="NORTH_SIDE",
        lat=34.294,
        lng=-77.900,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.74,
        capex=4800000.0,
        permit_vel=26.0,
        shift_ratio=1.22,
        sla=50.0,
        description="Northern growth belt with residential infill and logistics-adjacent services.",
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    "Ogden & Porters Neck": SubmarketMeta(
        name="Ogden & Porters Neck",
        borough="NORTH_SIDE",
        lat=34.285,
        lng=-77.870,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=27.0,
        shift_ratio=1.24,
        sla=51.0,
        description="Northeast residential/commercial corridors along Market St and Porters Neck Rd.",
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    # WEST_SIDE
    "Leland Gateway & West Bank": SubmarketMeta(
        name="Leland Gateway & West Bank",
        borough="WEST_SIDE",
        lat=34.225,
        lng=-78.030,
        zoom=13.2,
        pitch=40.0,
        base_lims=0.72,
        capex=4300000.0,
        permit_vel=23.0,
        shift_ratio=1.20,
        sla=46.0,
        description="Cape Fear west bank gateway: logistics, light industrial, and highway retail.",
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    "Navassa Industrial": SubmarketMeta(
        name="Navassa Industrial",
        borough="WEST_SIDE",
        lat=34.282,
        lng=-78.060,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.70,
        capex=3900000.0,
        permit_vel=22.0,
        shift_ratio=1.18,
        sla=44.0,
        description="Industrial belt northwest of the river with rail-adjacent parcels.",
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    # BEACHES
    "UNCW & Eastwood": SubmarketMeta(
        name="UNCW & Eastwood",
        borough="BEACHES",
        lat=34.225,
        lng=-77.870,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=31.0,
        shift_ratio=1.40,
        sla=53.0,
        description="Campus-adjacent district with student housing and services along Eastwood Rd.",
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    "Mayfaire & Military Cutoff": SubmarketMeta(
        name="Mayfaire & Military Cutoff",
        borough="BEACHES",
        lat=34.244,
        lng=-77.826,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.79,
        capex=6000000.0,
        permit_vel=33.0,
        shift_ratio=1.42,
        sla=55.0,
        description="Mixed-use retail and office cluster near Mayfaire and Military Cutoff.",
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    "Wrightsville Beach": SubmarketMeta(
        name="Wrightsville Beach",
        borough="BEACHES",
        lat=34.208,
        lng=-77.796,
        zoom=13.8,
        pitch=40.0,
        base_lims=0.76,
        capex=5200000.0,
        permit_vel=28.0,
        shift_ratio=1.28,
        sla=50.0,
        description="Barrier island hospitality and residential reinvestment.",
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    # SOUTH_CAPE_FEAR
    "Shipyard Blvd & Port": SubmarketMeta(
        name="Shipyard Blvd & Port",
        borough="SOUTH_CAPE_FEAR",
        lat=34.179,
        lng=-77.959,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.74,
        capex=5000000.0,
        permit_vel=27.0,
        shift_ratio=1.26,
        sla=49.0,
        description="Southern logistics and port-adjacent industrial/hospitality belt.",
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    "Carolina & Kure Beach": SubmarketMeta(
        name="Carolina & Kure Beach",
        borough="SOUTH_CAPE_FEAR",
        lat=34.036,
        lng=-77.898,
        zoom=13.2,
        pitch=38.0,
        base_lims=0.72,
        capex=4400000.0,
        permit_vel=24.0,
        shift_ratio=1.22,
        sla=46.0,
        description="Southern barrier-island towns with steady small-scale hospitality and residential activity.",
        city_id=WILMINGTON_NC_CITY_ID,
    ),
}


WILMINGTON_NC_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_RIVERFRONT": BoroughMeta(
        name="Downtown Riverfront",
        center_lat=34.235,
        center_lng=-77.944,
        zoom=13.8,
        bbox=WILMINGTON_NC_DIVISION_BBOXES["DOWNTOWN_RIVERFRONT"],
        submarkets=[k for k, v in WILMINGTON_NC_SUBMARKETS.items() if v.borough == "DOWNTOWN_RIVERFRONT"],
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    "NORTH_SIDE": BoroughMeta(
        name="North Side",
        center_lat=34.310,
        center_lng=-77.910,
        zoom=12.8,
        bbox=WILMINGTON_NC_DIVISION_BBOXES["NORTH_SIDE"],
        submarkets=[k for k, v in WILMINGTON_NC_SUBMARKETS.items() if v.borough == "NORTH_SIDE"],
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    "WEST_SIDE": BoroughMeta(
        name="West Side",
        center_lat=34.260,
        center_lng=-78.030,
        zoom=12.8,
        bbox=WILMINGTON_NC_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in WILMINGTON_NC_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    "BEACHES": BoroughMeta(
        name="Beaches",
        center_lat=34.220,
        center_lng=-77.820,
        zoom=13.0,
        bbox=WILMINGTON_NC_DIVISION_BBOXES["BEACHES"],
        submarkets=[k for k, v in WILMINGTON_NC_SUBMARKETS.items() if v.borough == "BEACHES"],
        city_id=WILMINGTON_NC_CITY_ID,
    ),
    "SOUTH_CAPE_FEAR": BoroughMeta(
        name="South Cape Fear",
        center_lat=34.100,
        center_lng=-77.940,
        zoom=12.8,
        bbox=WILMINGTON_NC_DIVISION_BBOXES["SOUTH_CAPE_FEAR"],
        submarkets=[k for k, v in WILMINGTON_NC_SUBMARKETS.items() if v.borough == "SOUTH_CAPE_FEAR"],
        city_id=WILMINGTON_NC_CITY_ID,
    ),
}

# Aliases kept for symmetry with other city modules' verbose spellings.
GREATER_WILMINGTON_NC_METRO_BBOX = WILMINGTON_NC_METRO_BBOX
WILMINGTON_NC_DIVISION_BBOXES_EXPORT = WILMINGTON_NC_DIVISION_BBOXES
WILMINGTON_NC_SUBMARKETS_EXPORT = WILMINGTON_NC_SUBMARKETS
WILMINGTON_NC_DIVISIONS_EXPORT = WILMINGTON_NC_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=WILMINGTON_NC_METRO_BBOX,
    division_bboxes=WILMINGTON_NC_DIVISION_BBOXES,
    submarkets=WILMINGTON_NC_SUBMARKETS,
    divisions=WILMINGTON_NC_DIVISIONS,
    contains=is_in_wilmington_nc_metro,
)

__all__ = [
    "WILMINGTON_NC_CITY_ID",
    "WILMINGTON_NC_CENTER",
    "WILMINGTON_NC_METRO_BBOX",
    "WILMINGTON_NC_DIVISION_BBOXES",
    "WILMINGTON_NC_SUBMARKETS",
    "WILMINGTON_NC_DIVISIONS",
    "WILMINGTON_NC_DIVISION_BBOXES_EXPORT",
    "WILMINGTON_NC_SUBMARKETS_EXPORT",
    "WILMINGTON_NC_DIVISIONS_EXPORT",
    "REGISTRATION",
    "is_in_wilmington_nc_metro",
]

