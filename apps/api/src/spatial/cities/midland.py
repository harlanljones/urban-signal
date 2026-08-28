"""Midland, TX — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
are currently limited to SNAP Retailers (TX slice) pending a verifiable public
city permits endpoint (EnerGov/PermitMidland has no open data API).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MIDLAND_CITY_ID: str = "midland"

# Approximate Midland city extents: generous box that contains the urbanized
# area along Loop 250 and the I-20 corridor. Downtown is around (31.997, -102.078).
MIDLAND_METRO_BBOX: Dict[str, float] = {
    "min_lat": 31.85,
    "max_lat": 32.10,
    "min_lng": -102.25,
    "max_lng": -101.90,
}

# Registration-contract center: City Hall / Centennial Park vicinity.
MIDLAND_CENTER: Dict[str, float] = {"lat": 31.9970, "lng": -102.0780}

# Division bounding boxes (strict subsets of MIDLAND_METRO_BBOX)
MIDLAND_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "CENTRAL_CORE": {"min_lat": 31.975, "max_lat": 32.025, "min_lng": -102.115, "max_lng": -102.035},
    "WEST_SIDE": {"min_lat": 31.960, "max_lat": 32.060, "min_lng": -102.250, "max_lng": -102.115},
    "EAST_GATE": {"min_lat": 31.960, "max_lat": 32.060, "min_lng": -102.035, "max_lng": -101.900},
    "SOUTH_CORRIDOR": {"min_lat": 31.850, "max_lat": 31.970, "min_lng": -102.220, "max_lng": -101.980},
    "NORTH_LOOP": {"min_lat": 32.025, "max_lat": 32.100, "min_lng": -102.200, "max_lng": -101.980},
}


def is_in_midland_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Midland metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        MIDLAND_METRO_BBOX["min_lat"] <= lat <= MIDLAND_METRO_BBOX["max_lat"]
        and MIDLAND_METRO_BBOX["min_lng"] <= lng <= MIDLAND_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
MIDLAND_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown Midland": SubmarketMeta(
        name="Downtown Midland",
        borough="CENTRAL_CORE",
        lat=31.9970,
        lng=-102.0780,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.82,
        capex=5200000.0,
        permit_vel=22.0,
        shift_ratio=1.24,
        sla=52.0,
        description="Civic/office core centered on Centennial Park, Wadley Ave, and Colorado Ave with mixed-use infill.",
        city_id=MIDLAND_CITY_ID,
    ),
    "Centennial Park & Convention District": SubmarketMeta(
        name="Centennial Park & Convention District",
        borough="CENTRAL_CORE",
        lat=31.9990,
        lng=-102.0740,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.80,
        capex=4800000.0,
        permit_vel=20.0,
        shift_ratio=1.22,
        sla=50.0,
        description="Park-front hospitality and meeting venues with adjacent retail and small-footprint office.",
        city_id=MIDLAND_CITY_ID,
    ),
    # WEST_SIDE
    "Medical Center & Andrews Hwy": SubmarketMeta(
        name="Medical Center & Andrews Hwy",
        borough="WEST_SIDE",
        lat=32.0000,
        lng=-102.1500,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.78,
        capex=4900000.0,
        permit_vel=21.0,
        shift_ratio=1.22,
        sla=50.0,
        description="Midland Memorial vicinity and Andrews Highway corridor with clinic, MOB, and supportive retail.",
        city_id=MIDLAND_CITY_ID,
    ),
    "Loop 250 West Retail": SubmarketMeta(
        name="Loop 250 West Retail",
        borough="WEST_SIDE",
        lat=32.0300,
        lng=-102.1700,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.76,
        capex=4600000.0,
        permit_vel=19.0,
        shift_ratio=1.20,
        sla=48.0,
        description="Power-center retail along Loop 250 with outparcel services and steady tenant rollover.",
        city_id=MIDLAND_CITY_ID,
    ),
    # EAST_GATE
    "Fairgrounds & East Industrial": SubmarketMeta(
        name="Fairgrounds & East Industrial",
        borough="EAST_GATE",
        lat=31.9900,
        lng=-101.9800,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.72,
        capex=4200000.0,
        permit_vel=18.0,
        shift_ratio=1.18,
        sla=46.0,
        description="Scharbauer, fairgrounds vicinity, and east-side light industrial approaching FM 715.",
        city_id=MIDLAND_CITY_ID,
    ),
    # SOUTH_CORRIDOR
    "I-20 Logistics & Bush Rd": SubmarketMeta(
        name="I-20 Logistics & Bush Rd",
        borough="SOUTH_CORRIDOR",
        lat=31.9000,
        lng=-102.1000,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.70,
        capex=4100000.0,
        permit_vel=17.0,
        shift_ratio=1.16,
        sla=44.0,
        description="I-20 frontage logistics, Bush Road industrial clusters, and service yards.",
        city_id=MIDLAND_CITY_ID,
    ),
    "Airport & I-20 West": SubmarketMeta(
        name="Airport & I-20 West",
        borough="SOUTH_CORRIDOR",
        lat=31.9400,
        lng=-102.2100,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.69,
        capex=4000000.0,
        permit_vel=16.0,
        shift_ratio=1.15,
        sla=44.0,
        description="Midland International Air & Space Port area and western I-20 service/industrial corridor.",
        city_id=MIDLAND_CITY_ID,
    ),
    # NORTH_LOOP
    "Wadley & Loop 250 North": SubmarketMeta(
        name="Wadley & Loop 250 North",
        borough="NORTH_LOOP",
        lat=32.0550,
        lng=-102.0500,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.74,
        capex=4400000.0,
        permit_vel=19.0,
        shift_ratio=1.20,
        sla=48.0,
        description="Northern Loop 250 retail and residential-adjacent services concentrated near Wadley Ave.",
        city_id=MIDLAND_CITY_ID,
    ),
    "Midland Park Mall": SubmarketMeta(
        name="Midland Park Mall",
        borough="NORTH_LOOP",
        lat=32.0500,
        lng=-102.1200,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.75,
        capex=4500000.0,
        permit_vel=20.0,
        shift_ratio=1.22,
        sla=50.0,
        description="Legacy regional mall node with surrounding outparcels and medical/professional infill.",
        city_id=MIDLAND_CITY_ID,
    ),
}


MIDLAND_DIVISIONS: Dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=31.9975,
        center_lng=-102.0750,
        zoom=13.5,
        bbox=MIDLAND_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in MIDLAND_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=MIDLAND_CITY_ID,
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=32.0050,
        center_lng=-102.1600,
        zoom=13.0,
        bbox=MIDLAND_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in MIDLAND_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id=MIDLAND_CITY_ID,
    ),
    "EAST_GATE": BoroughMeta(
        name="EAST_GATE",
        center_lat=31.9950,
        center_lng=-101.9700,
        zoom=13.0,
        bbox=MIDLAND_DIVISION_BBOXES["EAST_GATE"],
        submarkets=[k for k, v in MIDLAND_SUBMARKETS.items() if v.borough == "EAST_GATE"],
        city_id=MIDLAND_CITY_ID,
    ),
    "SOUTH_CORRIDOR": BoroughMeta(
        name="SOUTH_CORRIDOR",
        center_lat=31.9150,
        center_lng=-102.1200,
        zoom=13.0,
        bbox=MIDLAND_DIVISION_BBOXES["SOUTH_CORRIDOR"],
        submarkets=[k for k, v in MIDLAND_SUBMARKETS.items() if v.borough == "SOUTH_CORRIDOR"],
        city_id=MIDLAND_CITY_ID,
    ),
    "NORTH_LOOP": BoroughMeta(
        name="NORTH_LOOP",
        center_lat=32.0600,
        center_lng=-102.0900,
        zoom=12.8,
        bbox=MIDLAND_DIVISION_BBOXES["NORTH_LOOP"],
        submarkets=[k for k, v in MIDLAND_SUBMARKETS.items() if v.borough == "NORTH_LOOP"],
        city_id=MIDLAND_CITY_ID,
    ),
}

MIDLAND_DIVISION_BBOXES_EXPORT = MIDLAND_DIVISION_BBOXES
MIDLAND_SUBMARKETS_EXPORT = MIDLAND_SUBMARKETS
MIDLAND_DIVISIONS_EXPORT = MIDLAND_DIVISIONS

from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=MIDLAND_METRO_BBOX,
    division_bboxes=MIDLAND_DIVISION_BBOXES,
    submarkets=MIDLAND_SUBMARKETS,
    divisions=MIDLAND_DIVISIONS,
    contains=is_in_midland_metro,
)

__all__ = [
    "MIDLAND_CENTER",
    "MIDLAND_CITY_ID",
    "MIDLAND_DIVISION_BBOXES",
    "MIDLAND_DIVISION_BBOXES_EXPORT",
    "MIDLAND_DIVISIONS",
    "MIDLAND_DIVISIONS_EXPORT",
    "MIDLAND_METRO_BBOX",
    "MIDLAND_SUBMARKETS",
    "MIDLAND_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_midland_metro",
]

