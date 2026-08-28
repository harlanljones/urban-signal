"""Waco, TX — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
are currently limited to SNAP Retailers (TX slice) pending a verifiable public
city permits endpoint (data.texas.gov probe TBD per US-272).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

WACO_CITY_ID: str = "waco"

# Approximate Waco metro extents: generous box that contains the urbanized
# area across McLennan County core communities (Waco, Bellmead, Lacy-Lakeview,
# Woodway, Hewitt). Downtown is around (31.549, -97.147).
WACO_METRO_BBOX: Dict[str, float] = {
    "min_lat": 31.40,
    "max_lat": 31.72,
    "min_lng": -97.35,
    "max_lng": -96.95,
}

# Registration-contract center: Waco City Hall vicinity.
WACO_CENTER: Dict[str, float] = {"lat": 31.5493, "lng": -97.1467}

# Division bounding boxes (strict subsets of WACO_METRO_BBOX)
WACO_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown, Baylor University, Magnolia
    "CENTRAL_CORE": {"min_lat": 31.520, "max_lat": 31.580, "min_lng": -97.180, "max_lng": -97.100},
    # Woodway / West Waco commercial corridors
    "WEST_SIDE": {"min_lat": 31.450, "max_lat": 31.580, "min_lng": -97.350, "max_lng": -97.200},
    # East Waco, Elm Ave, I-35 east frontage
    "EAST_GATE": {"min_lat": 31.500, "max_lat": 31.650, "min_lng": -97.120, "max_lng": -96.950},
    # South Waco / Hewitt belts along I-35
    "SOUTH_STRIPS": {"min_lat": 31.400, "max_lat": 31.500, "min_lng": -97.300, "max_lng": -97.120},
    # North Waco, Lacy-Lakeview, Bellmead, Waco Regional vicinity
    "NORTH_LOOP": {"min_lat": 31.580, "max_lat": 31.720, "min_lng": -97.250, "max_lng": -97.000},
}


def is_in_waco_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Waco metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        WACO_METRO_BBOX["min_lat"] <= lat <= WACO_METRO_BBOX["max_lat"]
        and WACO_METRO_BBOX["min_lng"] <= lng <= WACO_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
WACO_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown Waco": SubmarketMeta(
        name="Downtown Waco",
        borough="CENTRAL_CORE",
        lat=31.5530,
        lng=-97.1380,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.82,
        capex=6100000.0,
        permit_vel=32.0,
        shift_ratio=1.34,
        sla=56.0,
        description="Courthouse, Convention Center, and riverfront core with adaptive reuse and hospitality infill.",
        city_id=WACO_CITY_ID,
    ),
    "Baylor University District": SubmarketMeta(
        name="Baylor University District",
        borough="CENTRAL_CORE",
        lat=31.5470,
        lng=-97.1210,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.81,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.30,
        sla=54.0,
        description="Campus-adjacent mixed-use, student housing, and services along University Parks & I-35.",
        city_id=WACO_CITY_ID,
    ),
    "Magnolia Silos & Market": SubmarketMeta(
        name="Magnolia Silos & Market",
        borough="CENTRAL_CORE",
        lat=31.5493,
        lng=-97.1290,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.80,
        capex=5200000.0,
        permit_vel=29.0,
        shift_ratio=1.28,
        sla=52.0,
        description="Tourism anchor district around the Silos and Market grounds with hospitality momentum.",
        city_id=WACO_CITY_ID,
    ),
    # WEST_SIDE
    "West Waco / Woodway": SubmarketMeta(
        name="West Waco / Woodway",
        borough="WEST_SIDE",
        lat=31.5120,
        lng=-97.2230,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.76,
        capex=5000000.0,
        permit_vel=26.0,
        shift_ratio=1.24,
        sla=50.0,
        description="US-84 corridor retail, medical clusters, and residential-adjacent commercial grid.",
        city_id=WACO_CITY_ID,
    ),
    # SOUTH_STRIPS
    "Hewitt & South Bosque": SubmarketMeta(
        name="Hewitt & South Bosque",
        borough="SOUTH_STRIPS",
        lat=31.4650,
        lng=-97.2000,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.74,
        capex=4700000.0,
        permit_vel=24.0,
        shift_ratio=1.22,
        sla=48.0,
        description="Southern growth belt near Hewitt with highway-oriented retail and services.",
        city_id=WACO_CITY_ID,
    ),
    # EAST_GATE
    "East Waco & Elm Ave": SubmarketMeta(
        name="East Waco & Elm Ave",
        borough="EAST_GATE",
        lat=31.5600,
        lng=-97.1080,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.72,
        capex=4300000.0,
        permit_vel=23.0,
        shift_ratio=1.20,
        sla=46.0,
        description="Historic East Waco corridor and I-35 east frontage experiencing steady small-scale reinvestment.",
        city_id=WACO_CITY_ID,
    ),
    # NORTH_LOOP
    "Bellmead & Lacy-Lakeview": SubmarketMeta(
        name="Bellmead & Lacy-Lakeview",
        borough="NORTH_LOOP",
        lat=31.6250,
        lng=-97.0970,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.70,
        capex=3900000.0,
        permit_vel=22.0,
        shift_ratio=1.18,
        sla=44.0,
        description="North/east belt communities with logistics, light industrial, and highway services along I-35.",
        city_id=WACO_CITY_ID,
    ),
    "Airport Corridor": SubmarketMeta(
        name="Airport Corridor",
        borough="NORTH_LOOP",
        lat=31.6110,
        lng=-97.2280,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.69,
        capex=3700000.0,
        permit_vel=21.0,
        shift_ratio=1.16,
        sla=44.0,
        description="Waco Regional Airport vicinity and Industrial Blvd with logistics and hospitality ribbons.",
        city_id=WACO_CITY_ID,
    ),
}


WACO_DIVISIONS: Dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=31.5510,
        center_lng=-97.1380,
        zoom=13.8,
        bbox=WACO_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in WACO_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=WACO_CITY_ID,
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=31.5200,
        center_lng=-97.2500,
        zoom=13.2,
        bbox=WACO_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in WACO_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id=WACO_CITY_ID,
    ),
    "SOUTH_STRIPS": BoroughMeta(
        name="SOUTH_STRIPS",
        center_lat=31.4650,
        center_lng=-97.2100,
        zoom=13.0,
        bbox=WACO_DIVISION_BBOXES["SOUTH_STRIPS"],
        submarkets=[k for k, v in WACO_SUBMARKETS.items() if v.borough == "SOUTH_STRIPS"],
        city_id=WACO_CITY_ID,
    ),
    "EAST_GATE": BoroughMeta(
        name="EAST_GATE",
        center_lat=31.5700,
        center_lng=-97.0800,
        zoom=13.2,
        bbox=WACO_DIVISION_BBOXES["EAST_GATE"],
        submarkets=[k for k, v in WACO_SUBMARKETS.items() if v.borough == "EAST_GATE"],
        city_id=WACO_CITY_ID,
    ),
    "NORTH_LOOP": BoroughMeta(
        name="NORTH_LOOP",
        center_lat=31.6350,
        center_lng=-97.1400,
        zoom=12.8,
        bbox=WACO_DIVISION_BBOXES["NORTH_LOOP"],
        submarkets=[k for k, v in WACO_SUBMARKETS.items() if v.borough == "NORTH_LOOP"],
        city_id=WACO_CITY_ID,
    ),
}

WACO_DIVISION_BBOXES_EXPORT = WACO_DIVISION_BBOXES
WACO_SUBMARKETS_EXPORT = WACO_SUBMARKETS
WACO_DIVISIONS_EXPORT = WACO_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=WACO_METRO_BBOX,
    division_bboxes=WACO_DIVISION_BBOXES,
    submarkets=WACO_SUBMARKETS,
    divisions=WACO_DIVISIONS,
    contains=is_in_waco_metro,
)

__all__ = [
    "WACO_CENTER",
    "WACO_CITY_ID",
    "WACO_DIVISION_BBOXES",
    "WACO_DIVISION_BBOXES_EXPORT",
    "WACO_DIVISIONS",
    "WACO_DIVISIONS_EXPORT",
    "WACO_METRO_BBOX",
    "WACO_SUBMARKETS",
    "WACO_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_waco_metro",
]

