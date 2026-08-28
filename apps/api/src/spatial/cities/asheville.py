"""Asheville, NC — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry first. Feed specs live in the spine (city_registry) and
start with SNAP Retailers (NC slice) unless and until a verifiable public
permits/311/deeds endpoint is proven on the City's ArcGIS Hub.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

ASHEVILLE_CITY_ID: str = "asheville"

# Approximate Asheville metro extents: generous box that contains the urbanized
# area across Asheville proper with headroom west/east and the south growth belt
# toward Arden. Downtown is around (35.5951, -82.5515).
ASHEVILLE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 35.43,
    "max_lat": 35.76,
    "min_lng": -82.72,
    "max_lng": -82.35,
}

# Registration-contract center: Asheville City Hall vicinity.
ASHEVILLE_CENTER: Dict[str, float] = {"lat": 35.5951, "lng": -82.5515}

# Division bounding boxes (strict subsets of ASHEVILLE_METRO_BBOX).
# Bboxes are authored to be sane and to contain their own submarket centers.
ASHEVILLE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown core: Pack Square to South Slope
    "DOWNTOWN_CORE": {
        "min_lat": 35.585,
        "max_lat": 35.610,
        "min_lng": -82.565,
        "max_lng": -82.530,
    },
    # River Arts District along the French Broad River
    "RIVER_ARTS": {
        "min_lat": 35.575,
        "max_lat": 35.600,
        "min_lng": -82.585,
        "max_lng": -82.545,
    },
    # West Asheville along Haywood Rd and I-240 west
    "WEST_ASHEVILLE": {
        "min_lat": 35.565,
        "max_lat": 35.620,
        "min_lng": -82.635,
        "max_lng": -82.565,
    },
    # North Asheville / Grove Park / Beaver Lake
    "NORTH_ASHEVILLE": {
        "min_lat": 35.620,
        "max_lat": 35.670,
        "min_lng": -82.590,
        "max_lng": -82.520,
    },
    # East Asheville / Tunnel Rd corridor
    "EAST_ASHEVILLE": {
        "min_lat": 35.575,
        "max_lat": 35.620,
        "min_lng": -82.520,
        "max_lng": -82.460,
    },
    # South Asheville / Biltmore Village / Arden
    "SOUTH_ASHEVILLE": {
        "min_lat": 35.470,
        "max_lat": 35.570,
        "min_lng": -82.560,
        "max_lng": -82.470,
    },
}


def is_in_asheville_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Asheville metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        ASHEVILLE_METRO_BBOX["min_lat"] <= lat <= ASHEVILLE_METRO_BBOX["max_lat"]
        and ASHEVILLE_METRO_BBOX["min_lng"] <= lng <= ASHEVILLE_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable catalog across divisions; coordinates must sit
# inside their division bboxes for the interlock containment tests).
ASHEVILLE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # DOWNTOWN_CORE
    "Downtown Asheville": SubmarketMeta(
        name="Downtown Asheville",
        borough="DOWNTOWN_CORE",
        lat=35.5955,
        lng=-82.5515,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.84,
        capex=6800000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=53.0,
        description="Pack Square to South Slope with adaptive reuse, hospitality, and mixed-use permitting momentum.",
        city_id=ASHEVILLE_CITY_ID,
    ),
    "Pack Square": SubmarketMeta(
        name="Pack Square",
        borough="DOWNTOWN_CORE",
        lat=35.5952,
        lng=-82.5503,
        zoom=15.0,
        pitch=46.0,
        base_lims=0.83,
        capex=6400000.0,
        permit_vel=28.0,
        shift_ratio=1.38,
        sla=52.0,
        description="Civic center with office-to-lodging reuse and storefront reinvestment along Biltmore Ave.",
        city_id=ASHEVILLE_CITY_ID,
    ),
    # RIVER_ARTS
    "River Arts District": SubmarketMeta(
        name="River Arts District",
        borough="RIVER_ARTS",
        lat=35.5825,
        lng=-82.5715,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.82,
        capex=6200000.0,
        permit_vel=26.0,
        shift_ratio=1.36,
        sla=51.0,
        description="Warehouse-to-studio conversions and infill along the French Broad River corridor.",
        city_id=ASHEVILLE_CITY_ID,
    ),
    # WEST_ASHEVILLE
    "West Asheville Haywood Rd": SubmarketMeta(
        name="West Asheville Haywood Rd",
        borough="WEST_ASHEVILLE",
        lat=35.5790,
        lng=-82.5930,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.80,
        capex=5600000.0,
        permit_vel=24.0,
        shift_ratio=1.32,
        sla=50.0,
        description="Haywood Road corridor with small-format commercial rehab and residential infill.",
        city_id=ASHEVILLE_CITY_ID,
    ),
    # NORTH_ASHEVILLE
    "North Asheville & Grove Park": SubmarketMeta(
        name="North Asheville & Grove Park",
        borough="NORTH_ASHEVILLE",
        lat=35.6260,
        lng=-82.5420,
        zoom=13.8,
        pitch=44.0,
        base_lims=0.79,
        capex=6000000.0,
        permit_vel=22.0,
        shift_ratio=1.30,
        sla=49.0,
        description="Historic Grove Park and Charlotte St corridor with steady alteration permits.",
        city_id=ASHEVILLE_CITY_ID,
    ),
    "Beaver Lake": SubmarketMeta(
        name="Beaver Lake",
        borough="NORTH_ASHEVILLE",
        lat=35.6410,
        lng=-82.5580,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.78,
        capex=5700000.0,
        permit_vel=21.0,
        shift_ratio=1.28,
        sla=48.0,
        description="North edge lake community with single-family additions and site improvements.",
        city_id=ASHEVILLE_CITY_ID,
    ),
    # EAST_ASHEVILLE
    "East Asheville": SubmarketMeta(
        name="East Asheville",
        borough="EAST_ASHEVILLE",
        lat=35.5960,
        lng=-82.4810,
        zoom=13.8,
        pitch=42.0,
        base_lims=0.78,
        capex=5400000.0,
        permit_vel=20.0,
        shift_ratio=1.26,
        sla=48.0,
        description="Tunnel Road corridor with neighborhood-serving retail nodes and residential turnover.",
        city_id=ASHEVILLE_CITY_ID,
    ),
    # SOUTH_ASHEVILLE
    "Biltmore Village": SubmarketMeta(
        name="Biltmore Village",
        borough="SOUTH_ASHEVILLE",
        lat=35.5650,
        lng=-82.5430,
        zoom=14.2,
        pitch=44.0,
        base_lims=0.80,
        capex=6100000.0,
        permit_vel=23.0,
        shift_ratio=1.30,
        sla=49.0,
        description="Historic village district at the estate gateway with hospitality and mixed-use rehab.",
        city_id=ASHEVILLE_CITY_ID,
    ),
    "South Asheville & Arden": SubmarketMeta(
        name="South Asheville & Arden",
        borough="SOUTH_ASHEVILLE",
        lat=35.4830,
        lng=-82.5130,
        zoom=13.2,
        pitch=40.0,
        base_lims=0.76,
        capex=5200000.0,
        permit_vel=19.0,
        shift_ratio=1.22,
        sla=46.0,
        description="Airport/Arden growth belt with retail pads and suburban multifamily infill.",
        city_id=ASHEVILLE_CITY_ID,
    ),
}


ASHEVILLE_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=35.5955,
        center_lng=-82.5515,
        zoom=14.0,
        bbox=ASHEVILLE_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in ASHEVILLE_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id=ASHEVILLE_CITY_ID,
    ),
    "RIVER_ARTS": BoroughMeta(
        name="RIVER_ARTS",
        center_lat=35.5865,
        center_lng=-82.5680,
        zoom=13.8,
        bbox=ASHEVILLE_DIVISION_BBOXES["RIVER_ARTS"],
        submarkets=[k for k, v in ASHEVILLE_SUBMARKETS.items() if v.borough == "RIVER_ARTS"],
        city_id=ASHEVILLE_CITY_ID,
    ),
    "WEST_ASHEVILLE": BoroughMeta(
        name="WEST_ASHEVILLE",
        center_lat=35.5900,
        center_lng=-82.6000,
        zoom=13.5,
        bbox=ASHEVILLE_DIVISION_BBOXES["WEST_ASHEVILLE"],
        submarkets=[k for k, v in ASHEVILLE_SUBMARKETS.items() if v.borough == "WEST_ASHEVILLE"],
        city_id=ASHEVILLE_CITY_ID,
    ),
    "NORTH_ASHEVILLE": BoroughMeta(
        name="NORTH_ASHEVILLE",
        center_lat=35.6350,
        center_lng=-82.5450,
        zoom=13.2,
        bbox=ASHEVILLE_DIVISION_BBOXES["NORTH_ASHEVILLE"],
        submarkets=[k for k, v in ASHEVILLE_SUBMARKETS.items() if v.borough == "NORTH_ASHEVILLE"],
        city_id=ASHEVILLE_CITY_ID,
    ),
    "EAST_ASHEVILLE": BoroughMeta(
        name="EAST_ASHEVILLE",
        center_lat=35.5980,
        center_lng=-82.4900,
        zoom=13.5,
        bbox=ASHEVILLE_DIVISION_BBOXES["EAST_ASHEVILLE"],
        submarkets=[k for k, v in ASHEVILLE_SUBMARKETS.items() if v.borough == "EAST_ASHEVILLE"],
        city_id=ASHEVILLE_CITY_ID,
    ),
    "SOUTH_ASHEVILLE": BoroughMeta(
        name="SOUTH_ASHEVILLE",
        center_lat=35.5250,
        center_lng=-82.5200,
        zoom=13.2,
        bbox=ASHEVILLE_DIVISION_BBOXES["SOUTH_ASHEVILLE"],
        submarkets=[k for k, v in ASHEVILLE_SUBMARKETS.items() if v.borough == "SOUTH_ASHEVILLE"],
        city_id=ASHEVILLE_CITY_ID,
    ),
}

# Export aliases to make static analyzers and pin-tests happy where used.
ASHEVILLE_DIVISION_BBOXES_EXPORT = ASHEVILLE_DIVISION_BBOXES
ASHEVILLE_SUBMARKETS_EXPORT = ASHEVILLE_SUBMARKETS
ASHEVILLE_DIVISIONS_EXPORT = ASHEVILLE_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=ASHEVILLE_METRO_BBOX,
    division_bboxes=ASHEVILLE_DIVISION_BBOXES,
    submarkets=ASHEVILLE_SUBMARKETS,
    divisions=ASHEVILLE_DIVISIONS,
    contains=is_in_asheville_metro,
)

__all__ = [
    "ASHEVILLE_CENTER",
    "ASHEVILLE_CITY_ID",
    "ASHEVILLE_DIVISION_BBOXES",
    "ASHEVILLE_DIVISION_BBOXES_EXPORT",
    "ASHEVILLE_DIVISIONS",
    "ASHEVILLE_DIVISIONS_EXPORT",
    "ASHEVILLE_METRO_BBOX",
    "ASHEVILLE_SUBMARKETS",
    "ASHEVILLE_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_asheville_metro",
]

