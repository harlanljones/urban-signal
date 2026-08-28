"""Abilene, TX — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
are currently limited to SNAP Retailers (TX slice) pending a verifiable public
city permits endpoint (US-278 — municipal verification required before permits).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

ABILENE_CITY_ID: str = "abilene"

# Approximate Abilene metro extents: generous box that contains the urbanized
# area across the core communities (Abilene, Tye, Potosi) and I-20 corridor.
# Downtown is around (32.4487, -99.7331).
ABILENE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 32.30,
    "max_lat": 32.57,
    "min_lng": -99.90,
    "max_lng": -99.55,
}

# Registration-contract center: Abilene City Hall vicinity.
ABILENE_CENTER: Dict[str, float] = {"lat": 32.4487, "lng": -99.7331}

# Division bounding boxes (strict subsets of ABILENE_METRO_BBOX)
ABILENE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown core, SoDA District, and adjacent government/cultural anchors
    "CENTRAL_CORE": {"min_lat": 32.430, "max_lat": 32.470, "min_lng": -99.760, "max_lng": -99.700},
    # West Abilene corridors toward Tye and Buffalo Gap Rd commercial belts
    "WEST_SIDE": {"min_lat": 32.400, "max_lat": 32.500, "min_lng": -99.900, "max_lng": -99.720},
    # Southern growth belt toward Potosi and South 14th commercial spine
    "SOUTH_BELT": {"min_lat": 32.300, "max_lat": 32.420, "min_lng": -99.850, "max_lng": -99.650},
    # East Abilene gateways and university-adjacent growth toward Lytle Creek
    "EAST_GATE": {"min_lat": 32.440, "max_lat": 32.560, "min_lng": -99.730, "max_lng": -99.550},
    # North Abilene / I-20 logistics, retail clusters, and hospital campus belts
    "NORTH_LOOP": {"min_lat": 32.500, "max_lat": 32.570, "min_lng": -99.850, "max_lng": -99.600},
}


def is_in_abilene_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Abilene metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        ABILENE_METRO_BBOX["min_lat"] <= lat <= ABILENE_METRO_BBOX["max_lat"]
        and ABILENE_METRO_BBOX["min_lng"] <= lng <= ABILENE_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
ABILENE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown Abilene": SubmarketMeta(
        name="Downtown Abilene",
        borough="CENTRAL_CORE",
        lat=32.4487,
        lng=-99.7331,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.80,
        capex=5100000.0,
        permit_vel=20.0,
        shift_ratio=1.18,
        sla=45.0,
        description="Historic courthouse, cultural district, and mixed-use main-street blocks.",
        city_id=ABILENE_CITY_ID,
    ),
    "SoDA District": SubmarketMeta(
        name="SoDA District",
        borough="CENTRAL_CORE",
        lat=32.4440,
        lng=-99.7330,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.79,
        capex=4800000.0,
        permit_vel=18.0,
        shift_ratio=1.16,
        sla=44.0,
        description="South Downtown Abilene arts & dining corridor with adaptive reuse momentum.",
        city_id=ABILENE_CITY_ID,
    ),
    # WEST_SIDE
    "Buffalo Gap Road Corridor": SubmarketMeta(
        name="Buffalo Gap Road Corridor",
        borough="WEST_SIDE",
        lat=32.4300,
        lng=-99.7700,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.74,
        capex=4300000.0,
        permit_vel=16.0,
        shift_ratio=1.14,
        sla=43.0,
        description="Retail and services spine along Buffalo Gap Rd and SW 14th connectors.",
        city_id=ABILENE_CITY_ID,
    ),
    # SOUTH_BELT
    "South 14th Commercial": SubmarketMeta(
        name="South 14th Commercial",
        borough="SOUTH_BELT",
        lat=32.4100,
        lng=-99.7500,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.72,
        capex=4000000.0,
        permit_vel=15.0,
        shift_ratio=1.12,
        sla=42.0,
        description="South Abilene growth belt with highway-oriented retail and neighborhood services.",
        city_id=ABILENE_CITY_ID,
    ),
    "Mall of Abilene / Southwest Dr": SubmarketMeta(
        name="Mall of Abilene / Southwest Dr",
        borough="SOUTH_BELT",
        lat=32.3900,
        lng=-99.7556,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.71,
        capex=3800000.0,
        permit_vel=14.0,
        shift_ratio=1.10,
        sla=42.0,
        description="Regional mall area and Southwest Dr commercial clusters.",
        city_id=ABILENE_CITY_ID,
    ),
    "Airport Corridor": SubmarketMeta(
        name="Airport Corridor",
        borough="SOUTH_BELT",
        lat=32.4100,
        lng=-99.6800,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.70,
        capex=3600000.0,
        permit_vel=13.0,
        shift_ratio=1.10,
        sla=42.0,
        description="Abilene Regional Airport vicinity and industrial ribbons along TX-36.",
        city_id=ABILENE_CITY_ID,
    ),
    # EAST_GATE
    "ACU / Northeast District": SubmarketMeta(
        name="ACU / Northeast District",
        borough="EAST_GATE",
        lat=32.4700,
        lng=-99.7100,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.73,
        capex=4200000.0,
        permit_vel=16.0,
        shift_ratio=1.13,
        sla=43.0,
        description="Abilene Christian University vicinity and northeast neighborhood services.",
        city_id=ABILENE_CITY_ID,
    ),
    # NORTH_LOOP
    "North Abilene / I-20": SubmarketMeta(
        name="North Abilene / I-20",
        borough="NORTH_LOOP",
        lat=32.5400,
        lng=-99.7300,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.69,
        capex=3500000.0,
        permit_vel=12.0,
        shift_ratio=1.08,
        sla=41.0,
        description="I-20 logistics and retail corridor with hospital and hospitality clusters.",
        city_id=ABILENE_CITY_ID,
    ),
}


ABILENE_DIVISIONS: Dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=32.4480,
        center_lng=-99.7335,
        zoom=13.8,
        bbox=ABILENE_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in ABILENE_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=ABILENE_CITY_ID,
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=32.4550,
        center_lng=-99.8000,
        zoom=13.2,
        bbox=ABILENE_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in ABILENE_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id=ABILENE_CITY_ID,
    ),
    "SOUTH_BELT": BoroughMeta(
        name="SOUTH_BELT",
        center_lat=32.3650,
        center_lng=-99.7400,
        zoom=13.0,
        bbox=ABILENE_DIVISION_BBOXES["SOUTH_BELT"],
        submarkets=[k for k, v in ABILENE_SUBMARKETS.items() if v.borough == "SOUTH_BELT"],
        city_id=ABILENE_CITY_ID,
    ),
    "EAST_GATE": BoroughMeta(
        name="EAST_GATE",
        center_lat=32.5050,
        center_lng=-99.6400,
        zoom=13.2,
        bbox=ABILENE_DIVISION_BBOXES["EAST_GATE"],
        submarkets=[k for k, v in ABILENE_SUBMARKETS.items() if v.borough == "EAST_GATE"],
        city_id=ABILENE_CITY_ID,
    ),
    "NORTH_LOOP": BoroughMeta(
        name="NORTH_LOOP",
        center_lat=32.5350,
        center_lng=-99.7200,
        zoom=12.8,
        bbox=ABILENE_DIVISION_BBOXES["NORTH_LOOP"],
        submarkets=[k for k, v in ABILENE_SUBMARKETS.items() if v.borough == "NORTH_LOOP"],
        city_id=ABILENE_CITY_ID,
    ),
}

ABILENE_DIVISION_BBOXES_EXPORT = ABILENE_DIVISION_BBOXES
ABILENE_SUBMARKETS_EXPORT = ABILENE_SUBMARKETS
ABILENE_DIVISIONS_EXPORT = ABILENE_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=ABILENE_METRO_BBOX,
    division_bboxes=ABILENE_DIVISION_BBOXES,
    submarkets=ABILENE_SUBMARKETS,
    divisions=ABILENE_DIVISIONS,
    contains=is_in_abilene_metro,
)

__all__ = [
    "ABILENE_CENTER",
    "ABILENE_CITY_ID",
    "ABILENE_DIVISION_BBOXES",
    "ABILENE_DIVISION_BBOXES_EXPORT",
    "ABILENE_DIVISIONS",
    "ABILENE_DIVISIONS_EXPORT",
    "ABILENE_METRO_BBOX",
    "ABILENE_SUBMARKETS",
    "ABILENE_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_abilene_metro",
]

