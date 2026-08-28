"""Odessa, TX — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
are initially limited to SNAP Retailers (TX slice) pending a verifiable public
city permits endpoint (US-280).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

ODESSA_CITY_ID: str = "odessa"

# Approximate Odessa metro extents: generous box covering the urbanized area of
# Odessa proper (Ector County core). Downtown is around (31.845, -102.367).
ODESSA_METRO_BBOX: Dict[str, float] = {
    "min_lat": 31.760,
    "max_lat": 31.940,
    "min_lng": -102.450,
    "max_lng": -102.260,
}

# Registration-contract center: Odessa City Hall vicinity.
ODESSA_CENTER: Dict[str, float] = {"lat": 31.8450, "lng": -102.3670}

# Division bounding boxes (strict subsets of ODESSA_METRO_BBOX)
ODESSA_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown civic/commercial core
    "CENTRAL_CORE": {"min_lat": 31.830, "max_lat": 31.880, "min_lng": -102.390, "max_lng": -102.340},
    # West Odessa commercial and logistics corridors (Andrews Hwy, Loop 338 W)
    "WEST_SIDE": {"min_lat": 31.820, "max_lat": 31.880, "min_lng": -102.450, "max_lng": -102.390},
    # East Odessa / TX-191 growth belt and UTPB vicinity
    "EAST_GATE": {"min_lat": 31.840, "max_lat": 31.910, "min_lng": -102.320, "max_lng": -102.270},
    # I-20 service/industrial ribbon along the southern edge
    "SOUTH_STRIPS": {"min_lat": 31.760, "max_lat": 31.820, "min_lng": -102.430, "max_lng": -102.300},
    # North Odessa residential/retail belt + airport vicinity
    "NORTH_LOOP": {"min_lat": 31.880, "max_lat": 31.940, "min_lng": -102.430, "max_lng": -102.300},
}


def is_in_odessa_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Odessa metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        ODESSA_METRO_BBOX["min_lat"] <= lat <= ODESSA_METRO_BBOX["max_lat"]
        and ODESSA_METRO_BBOX["min_lng"] <= lng <= ODESSA_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
ODESSA_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown Odessa": SubmarketMeta(
        name="Downtown Odessa",
        borough="CENTRAL_CORE",
        lat=31.8450,
        lng=-102.3670,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.80,
        capex=5200000.0,
        permit_vel=24.0,
        shift_ratio=1.22,
        sla=48.0,
        description="Courthouse, city center, and downtown commercial core with hospitality and civic anchors.",
        city_id=ODESSA_CITY_ID,
    ),
    "Midtown JBS Parkway": SubmarketMeta(
        name="Midtown JBS Parkway",
        borough="CENTRAL_CORE",
        lat=31.8600,
        lng=-102.3520,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.78,
        capex=5000000.0,
        permit_vel=22.0,
        shift_ratio=1.20,
        sla=46.0,
        description="JBS Parkway commercial spine connecting downtown with east Odessa retail corridors.",
        city_id=ODESSA_CITY_ID,
    ),
    # WEST_SIDE
    "West Loop & Andrews Hwy": SubmarketMeta(
        name="West Loop & Andrews Hwy",
        borough="WEST_SIDE",
        lat=31.8550,
        lng=-102.4100,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.74,
        capex=4600000.0,
        permit_vel=20.0,
        shift_ratio=1.18,
        sla=44.0,
        description="Highway-oriented services and light industrial corridors west of Loop 338.",
        city_id=ODESSA_CITY_ID,
    ),
    # SOUTH_STRIPS
    "I-20 Service Corridor": SubmarketMeta(
        name="I-20 Service Corridor",
        borough="SOUTH_STRIPS",
        lat=31.7900,
        lng=-102.3600,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.72,
        capex=4300000.0,
        permit_vel=19.0,
        shift_ratio=1.16,
        sla=44.0,
        description="Logistics, equipment yards, and highway services along I-20 south of the core.",
        city_id=ODESSA_CITY_ID,
    ),
    # EAST_GATE
    "UTPB & TX-191": SubmarketMeta(
        name="UTPB & TX-191",
        borough="EAST_GATE",
        lat=31.8800,
        lng=-102.3000,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.73,
        capex=4400000.0,
        permit_vel=21.0,
        shift_ratio=1.19,
        sla=46.0,
        description="UT Permian Basin campus area and TX-191 retail/office growth corridor.",
        city_id=ODESSA_CITY_ID,
    ),
    # NORTH_LOOP
    "North Odessa Retail": SubmarketMeta(
        name="North Odessa Retail",
        borough="NORTH_LOOP",
        lat=31.9050,
        lng=-102.3500,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.71,
        capex=4100000.0,
        permit_vel=18.0,
        shift_ratio=1.15,
        sla=42.0,
        description="42nd Street retail corridors and surrounding residential belts.",
        city_id=ODESSA_CITY_ID,
    ),
    "Odessa-Schlemeyer Field": SubmarketMeta(
        name="Odessa-Schlemeyer Field",
        borough="NORTH_LOOP",
        lat=31.9150,
        lng=-102.4050,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.69,
        capex=3800000.0,
        permit_vel=17.0,
        shift_ratio=1.14,
        sla=42.0,
        description="General-aviation airport vicinity with logistics, hospitality, and industrial services.",
        city_id=ODESSA_CITY_ID,
    ),
}


ODESSA_DIVISIONS: Dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=31.8500,
        center_lng=-102.3600,
        zoom=13.8,
        bbox=ODESSA_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in ODESSA_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=ODESSA_CITY_ID,
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=31.8500,
        center_lng=-102.4200,
        zoom=13.2,
        bbox=ODESSA_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in ODESSA_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id=ODESSA_CITY_ID,
    ),
    "SOUTH_STRIPS": BoroughMeta(
        name="SOUTH_STRIPS",
        center_lat=31.7900,
        center_lng=-102.3500,
        zoom=13.0,
        bbox=ODESSA_DIVISION_BBOXES["SOUTH_STRIPS"],
        submarkets=[k for k, v in ODESSA_SUBMARKETS.items() if v.borough == "SOUTH_STRIPS"],
        city_id=ODESSA_CITY_ID,
    ),
    "EAST_GATE": BoroughMeta(
        name="EAST_GATE",
        center_lat=31.8750,
        center_lng=-102.2950,
        zoom=13.2,
        bbox=ODESSA_DIVISION_BBOXES["EAST_GATE"],
        submarkets=[k for k, v in ODESSA_SUBMARKETS.items() if v.borough == "EAST_GATE"],
        city_id=ODESSA_CITY_ID,
    ),
    "NORTH_LOOP": BoroughMeta(
        name="NORTH_LOOP",
        center_lat=31.9100,
        center_lng=-102.3800,
        zoom=12.8,
        bbox=ODESSA_DIVISION_BBOXES["NORTH_LOOP"],
        submarkets=[k for k, v in ODESSA_SUBMARKETS.items() if v.borough == "NORTH_LOOP"],
        city_id=ODESSA_CITY_ID,
    ),
}

ODESSA_DIVISION_BBOXES_EXPORT = ODESSA_DIVISION_BBOXES
ODESSA_SUBMARKETS_EXPORT = ODESSA_SUBMARKETS
ODESSA_DIVISIONS_EXPORT = ODESSA_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=ODESSA_METRO_BBOX,
    division_bboxes=ODESSA_DIVISION_BBOXES,
    submarkets=ODESSA_SUBMARKETS,
    divisions=ODESSA_DIVISIONS,
    contains=is_in_odessa_metro,
)

__all__ = [
    "ODESSA_CENTER",
    "ODESSA_CITY_ID",
    "ODESSA_DIVISION_BBOXES",
    "ODESSA_DIVISION_BBOXES_EXPORT",
    "ODESSA_DIVISIONS",
    "ODESSA_DIVISIONS_EXPORT",
    "ODESSA_METRO_BBOX",
    "ODESSA_SUBMARKETS",
    "ODESSA_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_odessa_metro",
]

