"""Longview, TX — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
are initially limited to SNAP Retailers (TX slice) pending a verifiable public
city permits endpoint (per US-276). Do not fake endpoints.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

LONGVIEW_CITY_ID: str = "longview"

# Approximate Longview metro extents: generous box containing Longview core plus
# adjacent communities (White Oak/Gladewater edges to the west; Hallsville to the east).
# Downtown is around (32.5007, -94.7405).
LONGVIEW_METRO_BBOX: Dict[str, float] = {
    "min_lat": 32.40,
    "max_lat": 32.62,
    "min_lng": -94.90,
    "max_lng": -94.55,
}

# Registration-contract center: Longview City Hall vicinity.
LONGVIEW_CENTER: Dict[str, float] = {"lat": 32.5007, "lng": -94.7405}

# Division bounding boxes (strict subsets of LONGVIEW_METRO_BBOX)
LONGVIEW_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown / Core institutions
    "CENTRAL_CORE": {"min_lat": 32.480, "max_lat": 32.530, "min_lng": -94.760, "max_lng": -94.700},
    # West Loop 281, Longview Mall, White Oak edge
    "WEST_SIDE": {"min_lat": 32.490, "max_lat": 32.580, "min_lng": -94.900, "max_lng": -94.780},
    # Eastman/Industrial belts and Hallsville approach
    "EAST_BELT": {"min_lat": 32.470, "max_lat": 32.580, "min_lng": -94.680, "max_lng": -94.550},
    # South Longview / Estes Pkwy corridors
    "SOUTH_STRIPS": {"min_lat": 32.400, "max_lat": 32.490, "min_lng": -94.850, "max_lng": -94.680},
    # North Longview / Judson Rd and Loop 281 north arc
    "NORTH_LOOP": {"min_lat": 32.560, "max_lat": 32.620, "min_lng": -94.850, "max_lng": -94.650},
}


def is_in_longview_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Longview metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        LONGVIEW_METRO_BBOX["min_lat"] <= lat <= LONGVIEW_METRO_BBOX["max_lat"]
        and LONGVIEW_METRO_BBOX["min_lng"] <= lng <= LONGVIEW_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
LONGVIEW_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown Longview": SubmarketMeta(
        name="Downtown Longview",
        borough="CENTRAL_CORE",
        lat=32.5010,
        lng=-94.7400,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.74,
        capex=4300000.0,
        permit_vel=22.0,
        shift_ratio=1.26,
        sla=52.0,
        description="Civic and historic commercial core with adaptive reuse and hospitality infill.",
        city_id=LONGVIEW_CITY_ID,
    ),
    # WEST_SIDE
    "Longview Mall & West Loop 281": SubmarketMeta(
        name="Longview Mall & West Loop 281",
        borough="WEST_SIDE",
        lat=32.5360,
        lng=-94.7870,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.72,
        capex=4100000.0,
        permit_vel=21.0,
        shift_ratio=1.22,
        sla=50.0,
        description="Regional retail cluster and commercial corridors along W Loop 281.",
        city_id=LONGVIEW_CITY_ID,
    ),
    "White Oak & Gladewater Edge": SubmarketMeta(
        name="White Oak & Gladewater Edge",
        borough="WEST_SIDE",
        lat=32.5550,
        lng=-94.8600,
        zoom=13.2,
        pitch=40.0,
        base_lims=0.70,
        capex=3800000.0,
        permit_vel=19.0,
        shift_ratio=1.18,
        sla=46.0,
        description="Western edge trade area spanning White Oak and Gladewater approach.",
        city_id=LONGVIEW_CITY_ID,
    ),
    # EAST_BELT
    "Eastman Industrial Corridor": SubmarketMeta(
        name="Eastman Industrial Corridor",
        borough="EAST_BELT",
        lat=32.5530,
        lng=-94.6550,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.69,
        capex=3600000.0,
        permit_vel=18.0,
        shift_ratio=1.16,
        sla=44.0,
        description="Industrial belt and logistics support east of the core near Eastman facilities.",
        city_id=LONGVIEW_CITY_ID,
    ),
    "Hallsville Gateway": SubmarketMeta(
        name="Hallsville Gateway",
        borough="EAST_BELT",
        lat=32.5050,
        lng=-94.5750,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.68,
        capex=3500000.0,
        permit_vel=18.0,
        shift_ratio=1.15,
        sla=44.0,
        description="Eastern approach toward Hallsville with highway-oriented services and emerging nodes.",
        city_id=LONGVIEW_CITY_ID,
    ),
    # SOUTH_STRIPS
    "South Longview / Estes Pkwy": SubmarketMeta(
        name="South Longview / Estes Pkwy",
        borough="SOUTH_STRIPS",
        lat=32.4500,
        lng=-94.7160,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.71,
        capex=3700000.0,
        permit_vel=20.0,
        shift_ratio=1.20,
        sla=46.0,
        description="Southern growth belt and logistics along Estes Parkway and I-20 access.",
        city_id=LONGVIEW_CITY_ID,
    ),
    # NORTH_LOOP
    "Judson Road Corridor": SubmarketMeta(
        name="Judson Road Corridor",
        borough="NORTH_LOOP",
        lat=32.5630,
        lng=-94.7430,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.73,
        capex=4200000.0,
        permit_vel=21.0,
        shift_ratio=1.22,
        sla=48.0,
        description="North arc commercial spine and employment clusters along Judson Road and Loop 281.",
        city_id=LONGVIEW_CITY_ID,
    ),
}


LONGVIEW_DIVISIONS: Dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=32.5050,
        center_lng=-94.7350,
        zoom=13.8,
        bbox=LONGVIEW_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in LONGVIEW_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=LONGVIEW_CITY_ID,
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=32.5400,
        center_lng=-94.8100,
        zoom=13.2,
        bbox=LONGVIEW_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in LONGVIEW_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id=LONGVIEW_CITY_ID,
    ),
    "SOUTH_STRIPS": BoroughMeta(
        name="SOUTH_STRIPS",
        center_lat=32.4550,
        center_lng=-94.7300,
        zoom=13.0,
        bbox=LONGVIEW_DIVISION_BBOXES["SOUTH_STRIPS"],
        submarkets=[k for k, v in LONGVIEW_SUBMARKETS.items() if v.borough == "SOUTH_STRIPS"],
        city_id=LONGVIEW_CITY_ID,
    ),
    "EAST_BELT": BoroughMeta(
        name="EAST_BELT",
        center_lat=32.5400,
        center_lng=-94.6400,
        zoom=13.2,
        bbox=LONGVIEW_DIVISION_BBOXES["EAST_BELT"],
        submarkets=[k for k, v in LONGVIEW_SUBMARKETS.items() if v.borough == "EAST_BELT"],
        city_id=LONGVIEW_CITY_ID,
    ),
    "NORTH_LOOP": BoroughMeta(
        name="NORTH_LOOP",
        center_lat=32.5900,
        center_lng=-94.7400,
        zoom=12.8,
        bbox=LONGVIEW_DIVISION_BBOXES["NORTH_LOOP"],
        submarkets=[k for k, v in LONGVIEW_SUBMARKETS.items() if v.borough == "NORTH_LOOP"],
        city_id=LONGVIEW_CITY_ID,
    ),
}

LONGVIEW_DIVISION_BBOXES_EXPORT = LONGVIEW_DIVISION_BBOXES
LONGVIEW_SUBMARKETS_EXPORT = LONGVIEW_SUBMARKETS
LONGVIEW_DIVISIONS_EXPORT = LONGVIEW_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=LONGVIEW_METRO_BBOX,
    division_bboxes=LONGVIEW_DIVISION_BBOXES,
    submarkets=LONGVIEW_SUBMARKETS,
    divisions=LONGVIEW_DIVISIONS,
    contains=is_in_longview_metro,
)

__all__ = [
    "LONGVIEW_CENTER",
    "LONGVIEW_CITY_ID",
    "LONGVIEW_DIVISION_BBOXES",
    "LONGVIEW_DIVISION_BBOXES_EXPORT",
    "LONGVIEW_DIVISIONS",
    "LONGVIEW_DIVISIONS_EXPORT",
    "LONGVIEW_METRO_BBOX",
    "LONGVIEW_SUBMARKETS",
    "LONGVIEW_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_longview_metro",
]

