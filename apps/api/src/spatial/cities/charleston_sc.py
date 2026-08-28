"""Charleston, SC — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
are initially limited to SNAP Retailers (SC slice) pending a verifiable public
city permits endpoint via the ArcGIS Hub (US-284).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

CHARLESTON_SC_CITY_ID: str = "charleston_sc"

# Approximate Charleston metro extents: generous box that contains the
# urbanized core (Charleston Peninsula, Mount Pleasant, West Ashley, North
# Charleston, Daniel Island, James Island). Downtown is around (32.781, -79.931).
CHARLESTON_SC_METRO_BBOX: Dict[str, float] = {
    "min_lat": 32.60,
    "max_lat": 33.02,
    "min_lng": -80.30,
    "max_lng": -79.60,
}

# Registration-contract center: Charleston City Hall vicinity.
CHARLESTON_SC_CENTER: Dict[str, float] = {"lat": 32.7810, "lng": -79.9310}

# Division bounding boxes (strict subsets of CHARLESTON_SC_METRO_BBOX)
CHARLESTON_SC_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Historic peninsula core
    "PENINSULA_CORE": {"min_lat": 32.740, "max_lat": 32.820, "min_lng": -79.975, "max_lng": -79.900},
    # Mount Pleasant (Old Village + US-17 corridors)
    "MOUNT_PLEASANT": {"min_lat": 32.770, "max_lat": 32.900, "min_lng": -79.900, "max_lng": -79.750},
    # West Ashley corridors
    "WEST_ASHLEY": {"min_lat": 32.720, "max_lat": 32.820, "min_lng": -80.060, "max_lng": -79.950},
    # North Charleston belt incl. Park Circle
    "NORTH_CHARLESTON": {"min_lat": 32.840, "max_lat": 32.980, "min_lng": -80.050, "max_lng": -79.900},
    # James Island spine (Folly Rd)
    "JAMES_ISLAND": {"min_lat": 32.700, "max_lat": 32.780, "min_lng": -79.990, "max_lng": -79.910},
    # Daniel Island / Cainhoy Peninsula
    "DANIEL_CAINHOY": {"min_lat": 32.840, "max_lat": 33.000, "min_lng": -79.930, "max_lng": -79.700},
}


def is_in_charleston_sc_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Charleston metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        CHARLESTON_SC_METRO_BBOX["min_lat"] <= lat <= CHARLESTON_SC_METRO_BBOX["max_lat"]
        and CHARLESTON_SC_METRO_BBOX["min_lng"] <= lng <= CHARLESTON_SC_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must lie inside
# their division boxes for interlock containment).
CHARLESTON_SC_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # PENINSULA_CORE
    "Historic Peninsula": SubmarketMeta(
        name="Historic Peninsula",
        borough="PENINSULA_CORE",
        lat=32.7810,
        lng=-79.9310,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=7800000.0,
        permit_vel=42.0,
        shift_ratio=1.38,
        sla=56.0,
        description="King St, City Market, and waterfront anchors with adaptive reuse and hospitality infill.",
        city_id=CHARLESTON_SC_CITY_ID,
    ),
    "Upper King & Cannonborough": SubmarketMeta(
        name="Upper King & Cannonborough",
        borough="PENINSULA_CORE",
        lat=32.7920,
        lng=-79.9420,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.84,
        capex=7200000.0,
        permit_vel=38.0,
        shift_ratio=1.32,
        sla=54.0,
        description="Mixed-use corridor and medical district spillover north of Calhoun.",
        city_id=CHARLESTON_SC_CITY_ID,
    ),
    # MOUNT_PLEASANT
    "Mount Pleasant Waterfront": SubmarketMeta(
        name="Mount Pleasant Waterfront",
        borough="MOUNT_PLEASANT",
        lat=32.8060,
        lng=-79.8750,
        zoom=13.8,
        pitch=42.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=30.0,
        shift_ratio=1.26,
        sla=50.0,
        description="Waterfront Park, Old Village, and US-17 commercial spine with steady reinvestment.",
        city_id=CHARLESTON_SC_CITY_ID,
    ),
    # WEST_ASHLEY
    "West Ashley Corridors": SubmarketMeta(
        name="West Ashley Corridors",
        borough="WEST_ASHLEY",
        lat=32.7820,
        lng=-80.0060,
        zoom=13.6,
        pitch=40.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=26.0,
        shift_ratio=1.22,
        sla=48.0,
        description="Savannah Hwy and Sam Rittenberg Blvd retail/service belts and medical clusters.",
        city_id=CHARLESTON_SC_CITY_ID,
    ),
    # NORTH_CHARLESTON
    "Park Circle": SubmarketMeta(
        name="Park Circle",
        borough="NORTH_CHARLESTON",
        lat=32.8850,
        lng=-79.9750,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.74,
        capex=5000000.0,
        permit_vel=24.0,
        shift_ratio=1.20,
        sla=46.0,
        description="Historic Park Circle district with small-scale infill and hospitality/logistics adjacency.",
        city_id=CHARLESTON_SC_CITY_ID,
    ),
    # JAMES_ISLAND
    "James Island Folly Rd": SubmarketMeta(
        name="James Island Folly Rd",
        borough="JAMES_ISLAND",
        lat=32.7420,
        lng=-79.9650,
        zoom=13.8,
        pitch=40.0,
        base_lims=0.74,
        capex=4700000.0,
        permit_vel=22.0,
        shift_ratio=1.18,
        sla=46.0,
        description="Folly Road commercial spine and neighborhood services.",
        city_id=CHARLESTON_SC_CITY_ID,
    ),
    # DANIEL_CAINHOY
    "Daniel Island": SubmarketMeta(
        name="Daniel Island",
        borough="DANIEL_CAINHOY",
        lat=32.8700,
        lng=-79.9100,
        zoom=13.8,
        pitch=38.0,
        base_lims=0.72,
        capex=4600000.0,
        permit_vel=21.0,
        shift_ratio=1.16,
        sla=44.0,
        description="Master-planned mixed-use with logistics adjacency across I-526.",
        city_id=CHARLESTON_SC_CITY_ID,
    ),
}


CHARLESTON_SC_DIVISIONS: Dict[str, BoroughMeta] = {
    "PENINSULA_CORE": BoroughMeta(
        name="PENINSULA_CORE",
        center_lat=32.7800,
        center_lng=-79.9350,
        zoom=13.8,
        bbox=CHARLESTON_SC_DIVISION_BBOXES["PENINSULA_CORE"],
        submarkets=[k for k, v in CHARLESTON_SC_SUBMARKETS.items() if v.borough == "PENINSULA_CORE"],
        city_id=CHARLESTON_SC_CITY_ID,
    ),
    "MOUNT_PLEASANT": BoroughMeta(
        name="MOUNT_PLEASANT",
        center_lat=32.8200,
        center_lng=-79.8550,
        zoom=13.2,
        bbox=CHARLESTON_SC_DIVISION_BBOXES["MOUNT_PLEASANT"],
        submarkets=[k for k, v in CHARLESTON_SC_SUBMARKETS.items() if v.borough == "MOUNT_PLEASANT"],
        city_id=CHARLESTON_SC_CITY_ID,
    ),
    "WEST_ASHLEY": BoroughMeta(
        name="WEST_ASHLEY",
        center_lat=32.7750,
        center_lng=-80.0000,
        zoom=13.2,
        bbox=CHARLESTON_SC_DIVISION_BBOXES["WEST_ASHLEY"],
        submarkets=[k for k, v in CHARLESTON_SC_SUBMARKETS.items() if v.borough == "WEST_ASHLEY"],
        city_id=CHARLESTON_SC_CITY_ID,
    ),
    "NORTH_CHARLESTON": BoroughMeta(
        name="NORTH_CHARLESTON",
        center_lat=32.9000,
        center_lng=-79.9750,
        zoom=12.8,
        bbox=CHARLESTON_SC_DIVISION_BBOXES["NORTH_CHARLESTON"],
        submarkets=[k for k, v in CHARLESTON_SC_SUBMARKETS.items() if v.borough == "NORTH_CHARLESTON"],
        city_id=CHARLESTON_SC_CITY_ID,
    ),
    "JAMES_ISLAND": BoroughMeta(
        name="JAMES_ISLAND",
        center_lat=32.7450,
        center_lng=-79.9650,
        zoom=13.2,
        bbox=CHARLESTON_SC_DIVISION_BBOXES["JAMES_ISLAND"],
        submarkets=[k for k, v in CHARLESTON_SC_SUBMARKETS.items() if v.borough == "JAMES_ISLAND"],
        city_id=CHARLESTON_SC_CITY_ID,
    ),
    "DANIEL_CAINHOY": BoroughMeta(
        name="DANIEL_CAINHOY",
        center_lat=32.9000,
        center_lng=-79.8400,
        zoom=12.8,
        bbox=CHARLESTON_SC_DIVISION_BBOXES["DANIEL_CAINHOY"],
        submarkets=[k for k, v in CHARLESTON_SC_SUBMARKETS.items() if v.borough == "DANIEL_CAINHOY"],
        city_id=CHARLESTON_SC_CITY_ID,
    ),
}

CHARLESTON_SC_DIVISION_BBOXES_EXPORT = CHARLESTON_SC_DIVISION_BBOXES
CHARLESTON_SC_SUBMARKETS_EXPORT = CHARLESTON_SC_SUBMARKETS
CHARLESTON_SC_DIVISIONS_EXPORT = CHARLESTON_SC_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=CHARLESTON_SC_METRO_BBOX,
    division_bboxes=CHARLESTON_SC_DIVISION_BBOXES,
    submarkets=CHARLESTON_SC_SUBMARKETS,
    divisions=CHARLESTON_SC_DIVISIONS,
    contains=is_in_charleston_sc_metro,
)

__all__ = [
    "CHARLESTON_SC_CENTER",
    "CHARLESTON_SC_CITY_ID",
    "CHARLESTON_SC_DIVISION_BBOXES",
    "CHARLESTON_SC_DIVISION_BBOXES_EXPORT",
    "CHARLESTON_SC_DIVISIONS",
    "CHARLESTON_SC_DIVISIONS_EXPORT",
    "CHARLESTON_SC_METRO_BBOX",
    "CHARLESTON_SC_SUBMARKETS",
    "CHARLESTON_SC_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_charleston_sc_metro",
]

