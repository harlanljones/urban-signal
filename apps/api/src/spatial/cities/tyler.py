"""Tyler, TX — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
are currently limited to SNAP Retailers (TX slice) pending a verifiable public
city permits endpoint via data.texas.gov.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

TYLER_CITY_ID: str = "tyler"

# Approximate Tyler city extents. Downtown is around (32.352, -95.301).
TYLER_METRO_BBOX: Dict[str, float] = {
    "min_lat": 32.25,
    "max_lat": 32.45,
    "min_lng": -95.45,
    "max_lng": -95.15,
}

# Registration-contract center: Downtown Tyler (City Hall vicinity).
TYLER_CENTER: Dict[str, float] = {"lat": 32.3519, "lng": -95.3006}

# Division bounding boxes (strict subsets of TYLER_METRO_BBOX)
TYLER_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "CENTRAL_CORE": {"min_lat": 32.335, "max_lat": 32.370, "min_lng": -95.330, "max_lng": -95.270},
    "WEST_SIDE": {"min_lat": 32.320, "max_lat": 32.420, "min_lng": -95.450, "max_lng": -95.340},
    "EAST_GATE": {"min_lat": 32.310, "max_lat": 32.420, "min_lng": -95.270, "max_lng": -95.150},
    "SOUTH_STRIPS": {"min_lat": 32.250, "max_lat": 32.330, "min_lng": -95.430, "max_lng": -95.250},
    "NORTH_LOOP": {"min_lat": 32.370, "max_lat": 32.450, "min_lng": -95.420, "max_lng": -95.220},
}


def is_in_tyler_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Tyler metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        TYLER_METRO_BBOX["min_lat"] <= lat <= TYLER_METRO_BBOX["max_lat"]
        and TYLER_METRO_BBOX["min_lng"] <= lng <= TYLER_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
TYLER_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown Tyler": SubmarketMeta(
        name="Downtown Tyler",
        borough="CENTRAL_CORE",
        lat=32.3519,
        lng=-95.3006,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.80,
        capex=5200000.0,
        permit_vel=26.0,
        shift_ratio=1.28,
        sla=52.0,
        description="Courthouse square, arts venues, and mixed commercial infill around downtown core.",
        city_id=TYLER_CITY_ID,
    ),
    "Medical District": SubmarketMeta(
        name="Medical District",
        borough="CENTRAL_CORE",
        lat=32.3450,
        lng=-95.3060,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.78,
        capex=5000000.0,
        permit_vel=24.0,
        shift_ratio=1.26,
        sla=50.0,
        description="Hospital and clinical cluster west of downtown with steady facilities investment.",
        city_id=TYLER_CITY_ID,
    ),
    # WEST_SIDE
    "West Loop 323": SubmarketMeta(
        name="West Loop 323",
        borough="WEST_SIDE",
        lat=32.3600,
        lng=-95.3800,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.74,
        capex=4400000.0,
        permit_vel=22.0,
        shift_ratio=1.22,
        sla=46.0,
        description="Auto-oriented commercial corridor along Loop 323 with retail pads and services.",
        city_id=TYLER_CITY_ID,
    ),
    # EAST_GATE
    "University Area": SubmarketMeta(
        name="University Area",
        borough="EAST_GATE",
        lat=32.3150,
        lng=-95.2450,
        zoom=13.8,
        pitch=40.0,
        base_lims=0.72,
        capex=4300000.0,
        permit_vel=21.0,
        shift_ratio=1.20,
        sla=44.0,
        description="UT Tyler campus and adjacent commercial/medical growth east of Broadway.",
        city_id=TYLER_CITY_ID,
    ),
    # SOUTH_STRIPS
    "Azalea District": SubmarketMeta(
        name="Azalea District",
        borough="SOUTH_STRIPS",
        lat=32.3200,
        lng=-95.3000,
        zoom=14.0,
        pitch=38.0,
        base_lims=0.76,
        capex=4600000.0,
        permit_vel=23.0,
        shift_ratio=1.24,
        sla=48.0,
        description="Historic residential and garden district with neighborhood-serving retail and renovations.",
        city_id=TYLER_CITY_ID,
    ),
    "South Broadway Corridor": SubmarketMeta(
        name="South Broadway Corridor",
        borough="SOUTH_STRIPS",
        lat=32.3000,
        lng=-95.3050,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.70,
        capex=4200000.0,
        permit_vel=20.0,
        shift_ratio=1.18,
        sla=44.0,
        description="Regional retail spine with highway-oriented pads and steady tenant rollover.",
        city_id=TYLER_CITY_ID,
    ),
    # NORTH_LOOP
    "North Loop & Industrial": SubmarketMeta(
        name="North Loop & Industrial",
        borough="NORTH_LOOP",
        lat=32.4050,
        lng=-95.3400,
        zoom=13.3,
        pitch=38.0,
        base_lims=0.68,
        capex=3800000.0,
        permit_vel=18.0,
        shift_ratio=1.16,
        sla=42.0,
        description="Industrial and logistics belt near Loop 323 with light manufacturing and services.",
        city_id=TYLER_CITY_ID,
    ),
}


TYLER_DIVISIONS: Dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=32.3520,
        center_lng=-95.3000,
        zoom=13.5,
        bbox=TYLER_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in TYLER_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=TYLER_CITY_ID,
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=32.3650,
        center_lng=-95.3950,
        zoom=13.0,
        bbox=TYLER_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in TYLER_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id=TYLER_CITY_ID,
    ),
    "EAST_GATE": BoroughMeta(
        name="EAST_GATE",
        center_lat=32.3600,
        center_lng=-95.2200,
        zoom=13.0,
        bbox=TYLER_DIVISION_BBOXES["EAST_GATE"],
        submarkets=[k for k, v in TYLER_SUBMARKETS.items() if v.borough == "EAST_GATE"],
        city_id=TYLER_CITY_ID,
    ),
    "SOUTH_STRIPS": BoroughMeta(
        name="SOUTH_STRIPS",
        center_lat=32.3000,
        center_lng=-95.3200,
        zoom=13.0,
        bbox=TYLER_DIVISION_BBOXES["SOUTH_STRIPS"],
        submarkets=[k for k, v in TYLER_SUBMARKETS.items() if v.borough == "SOUTH_STRIPS"],
        city_id=TYLER_CITY_ID,
    ),
    "NORTH_LOOP": BoroughMeta(
        name="NORTH_LOOP",
        center_lat=32.4100,
        center_lng=-95.3300,
        zoom=12.8,
        bbox=TYLER_DIVISION_BBOXES["NORTH_LOOP"],
        submarkets=[k for k, v in TYLER_SUBMARKETS.items() if v.borough == "NORTH_LOOP"],
        city_id=TYLER_CITY_ID,
    ),
}

TYLER_DIVISION_BBOXES_EXPORT = TYLER_DIVISION_BBOXES
TYLER_SUBMARKETS_EXPORT = TYLER_SUBMARKETS
TYLER_DIVISIONS_EXPORT = TYLER_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=TYLER_METRO_BBOX,
    division_bboxes=TYLER_DIVISION_BBOXES,
    submarkets=TYLER_SUBMARKETS,
    divisions=TYLER_DIVISIONS,
    contains=is_in_tyler_metro,
)

__all__ = [
    "TYLER_CENTER",
    "TYLER_CITY_ID",
    "TYLER_DIVISION_BBOXES",
    "TYLER_DIVISION_BBOXES_EXPORT",
    "TYLER_DIVISIONS",
    "TYLER_DIVISIONS_EXPORT",
    "TYLER_METRO_BBOX",
    "TYLER_SUBMARKETS",
    "TYLER_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_tyler_metro",
]

