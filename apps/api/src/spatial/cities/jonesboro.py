"""Jonesboro, AR — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
for initial registration are limited to SNAP Retailers (AR slice) pending a
verifiable public city permits endpoint (US-283).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

JONESBORO_CITY_ID: str = "jonesboro"

# Approximate Jonesboro metro extents: generous box that contains the urbanized
# area across Jonesboro and nearby communities (Valley View, Bono, Brookland, Bay).
# Downtown is around (35.8423, -90.7043).
JONESBORO_METRO_BBOX: Dict[str, float] = {
    "min_lat": 35.70,
    "max_lat": 36.00,
    "min_lng": -90.85,
    "max_lng": -90.55,
}

# Registration-contract center: Jonesboro City Hall vicinity.
JONESBORO_CENTER: Dict[str, float] = {"lat": 35.8423, "lng": -90.7043}

# Division bounding boxes (strict subsets of JONESBORO_METRO_BBOX)
JONESBORO_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown, Main Street, A-State south edge
    "CENTRAL_CORE": {
        "min_lat": 35.810,
        "max_lat": 35.880,
        "min_lng": -90.740,
        "max_lng": -90.660,
    },
    # Arkansas State University and Johnson Ave corridor
    "A_STATE_DISTRICT": {
        "min_lat": 35.830,
        "max_lat": 35.920,
        "min_lng": -90.710,
        "max_lng": -90.600,
    },
    # West Jonesboro / Valley View growth belt
    "WEST_BELT": {
        "min_lat": 35.780,
        "max_lat": 35.900,
        "min_lng": -90.850,
        "max_lng": -90.730,
    },
    # South Jonesboro / Industrial and retail strips
    "SOUTH_GATE": {
        "min_lat": 35.700,
        "max_lat": 35.820,
        "min_lng": -90.820,
        "max_lng": -90.650,
    },
    # Northeast Jonesboro (Brookland / Nettleton vicinity)
    "NORTHEAST_BELT": {
        "min_lat": 35.880,
        "max_lat": 36.000,
        "min_lng": -90.740,
        "max_lng": -90.560,
    },
}


def is_in_jonesboro_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Jonesboro metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        JONESBORO_METRO_BBOX["min_lat"] <= lat <= JONESBORO_METRO_BBOX["max_lat"]
        and JONESBORO_METRO_BBOX["min_lng"] <= lng <= JONESBORO_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
JONESBORO_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown Jonesboro": SubmarketMeta(
        name="Downtown Jonesboro",
        borough="CENTRAL_CORE",
        lat=35.8350,
        lng=-90.7040,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.78,
        capex=3600000.0,
        permit_vel=18.0,
        shift_ratio=1.18,
        sla=46.0,
        description="Historic Main Street core with courthouse square, small business reinvestment, and adaptive reuse.",
        city_id=JONESBORO_CITY_ID,
    ),
    "Main & Union Corridor": SubmarketMeta(
        name="Main & Union Corridor",
        borough="CENTRAL_CORE",
        lat=35.8420,
        lng=-90.6900,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.76,
        capex=3200000.0,
        permit_vel=16.0,
        shift_ratio=1.16,
        sla=44.0,
        description="Central east-west spine linking downtown to Caraway with mixed small-format commercial.",
        city_id=JONESBORO_CITY_ID,
    ),
    # A_STATE_DISTRICT
    "Arkansas State University": SubmarketMeta(
        name="Arkansas State University",
        borough="A_STATE_DISTRICT",
        lat=35.8445,
        lng=-90.6530,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.74,
        capex=3000000.0,
        permit_vel=15.0,
        shift_ratio=1.14,
        sla=42.0,
        description="Campus and Johnson Ave corridor with student housing infill and institutional projects.",
        city_id=JONESBORO_CITY_ID,
    ),
    "Caraway & Highland Retail": SubmarketMeta(
        name="Caraway & Highland Retail",
        borough="A_STATE_DISTRICT",
        lat=35.8550,
        lng=-90.6800,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.72,
        capex=2800000.0,
        permit_vel=14.0,
        shift_ratio=1.12,
        sla=40.0,
        description="Commercial strips serving the campus and neighborhoods along Caraway and Highland.",
        city_id=JONESBORO_CITY_ID,
    ),
    # WEST_BELT
    "West Jonesboro & Valley View": SubmarketMeta(
        name="West Jonesboro & Valley View",
        borough="WEST_BELT",
        lat=35.8200,
        lng=-90.7750,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.70,
        capex=2600000.0,
        permit_vel=13.0,
        shift_ratio=1.10,
        sla=38.0,
        description="Westside growth belt toward Valley View with suburban residential and service nodes.",
        city_id=JONESBORO_CITY_ID,
    ),
    # SOUTH_GATE
    "South Jonesboro Industrial": SubmarketMeta(
        name="South Jonesboro Industrial",
        borough="SOUTH_GATE",
        lat=35.7600,
        lng=-90.7200,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.68,
        capex=2400000.0,
        permit_vel=12.0,
        shift_ratio=1.08,
        sla=36.0,
        description="Industrial and logistics corridor south of downtown with highway-oriented retail.",
        city_id=JONESBORO_CITY_ID,
    ),
    # NORTHEAST_BELT
    "Nettleton & NE Commercial": SubmarketMeta(
        name="Nettleton & NE Commercial",
        borough="NORTHEAST_BELT",
        lat=35.9050,
        lng=-90.6500,
        zoom=13.8,
        pitch=40.0,
        base_lims=0.69,
        capex=2500000.0,
        permit_vel=12.0,
        shift_ratio=1.10,
        sla=38.0,
        description="Northeast belt around Nettleton and Brookland approach with steady small-scale reinvestment.",
        city_id=JONESBORO_CITY_ID,
    ),
}


JONESBORO_DIVISIONS: Dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=35.8423,
        center_lng=-90.7043,
        zoom=13.8,
        bbox=JONESBORO_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in JONESBORO_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=JONESBORO_CITY_ID,
    ),
    "A_STATE_DISTRICT": BoroughMeta(
        name="A_STATE_DISTRICT",
        center_lat=35.8500,
        center_lng=-90.6600,
        zoom=13.5,
        bbox=JONESBORO_DIVISION_BBOXES["A_STATE_DISTRICT"],
        submarkets=[k for k, v in JONESBORO_SUBMARKETS.items() if v.borough == "A_STATE_DISTRICT"],
        city_id=JONESBORO_CITY_ID,
    ),
    "WEST_BELT": BoroughMeta(
        name="WEST_BELT",
        center_lat=35.8400,
        center_lng=-90.7900,
        zoom=13.2,
        bbox=JONESBORO_DIVISION_BBOXES["WEST_BELT"],
        submarkets=[k for k, v in JONESBORO_SUBMARKETS.items() if v.borough == "WEST_BELT"],
        city_id=JONESBORO_CITY_ID,
    ),
    "SOUTH_GATE": BoroughMeta(
        name="SOUTH_GATE",
        center_lat=35.7600,
        center_lng=-90.7200,
        zoom=13.0,
        bbox=JONESBORO_DIVISION_BBOXES["SOUTH_GATE"],
        submarkets=[k for k, v in JONESBORO_SUBMARKETS.items() if v.borough == "SOUTH_GATE"],
        city_id=JONESBORO_CITY_ID,
    ),
    "NORTHEAST_BELT": BoroughMeta(
        name="NORTHEAST_BELT",
        center_lat=35.9300,
        center_lng=-90.6400,
        zoom=13.0,
        bbox=JONESBORO_DIVISION_BBOXES["NORTHEAST_BELT"],
        submarkets=[k for k, v in JONESBORO_SUBMARKETS.items() if v.borough == "NORTHEAST_BELT"],
        city_id=JONESBORO_CITY_ID,
    ),
}

JONESBORO_DIVISION_BBOXES_EXPORT = JONESBORO_DIVISION_BBOXES
JONESBORO_SUBMARKETS_EXPORT = JONESBORO_SUBMARKETS
JONESBORO_DIVISIONS_EXPORT = JONESBORO_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=JONESBORO_METRO_BBOX,
    division_bboxes=JONESBORO_DIVISION_BBOXES,
    submarkets=JONESBORO_SUBMARKETS,
    divisions=JONESBORO_DIVISIONS,
    contains=is_in_jonesboro_metro,
)

__all__ = [
    "JONESBORO_CENTER",
    "JONESBORO_CITY_ID",
    "JONESBORO_DIVISION_BBOXES",
    "JONESBORO_DIVISION_BBOXES_EXPORT",
    "JONESBORO_DIVISIONS",
    "JONESBORO_DIVISIONS_EXPORT",
    "JONESBORO_METRO_BBOX",
    "JONESBORO_SUBMARKETS",
    "JONESBORO_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_jonesboro_metro",
]

