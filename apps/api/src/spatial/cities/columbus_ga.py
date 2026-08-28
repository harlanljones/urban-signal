"""Columbus, GA (Muscogee County) spatial registry.

Consolidated city–county on the Chattahoochee River (Alabama line).
This module declares the metro bounding box, a small divisions catalog,
and submarket presets used by the dashboard. Containment tests assert
every division box nests inside the metro box and every submarket's
lat/lng sits inside its division box.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

# Canonical id for this metro
COLUMBUS_GA_CITY_ID: str = "columbus_ga"

# Registration-contract center: Uptown/Downtown Columbus (Broadway & 11th)
COLUMBUS_GA_CENTER: Dict[str, float] = {"lat": 32.4610, "lng": -84.9877}

# Metro bbox (rounded, padded to the hundredth):
# Chattahoochee River west edge to Midland/Ellerslie east,
# Fort Benning south, North Columbus / US-27 north.
COLUMBUS_GA_METRO_BBOX: Dict[str, float] = {
    "min_lat": 32.35,
    "max_lat": 32.65,
    "min_lng": -85.15,
    "max_lng": -84.75,
}

# Three divisions across the metro. Boxes strictly nest in the metro bbox.
COLUMBUS_GA_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown/riverfront core including Uptown + GA side of Phenix City bridgehead
    "DOWNTOWN_RIVERFRONT": {
        "min_lat": 32.440,
        "max_lat": 32.490,
        "min_lng": -85.040,
        "max_lng": -84.960,
    },
    # Midtown medical/education spine east of downtown up to the CSU area
    "MIDTOWN": {
        "min_lat": 32.455,
        "max_lat": 32.525,
        "min_lng": -84.990,
        "max_lng": -84.910,
    },
    # North Columbus retail/employment and residential growth areas
    "NORTHSIDE": {
        "min_lat": 32.520,
        "max_lat": 32.615,
        "min_lng": -85.020,
        "max_lng": -84.880,
    },
    # South Columbus and Fort Benning gateway
    "SOUTH_GATEWAY": {
        "min_lat": 32.365,
        "max_lat": 32.440,
        "min_lng": -85.070,
        "max_lng": -84.910,
    },
}


def is_in_columbus_ga_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Columbus, GA metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        COLUMBUS_GA_METRO_BBOX["min_lat"] <= lat <= COLUMBUS_GA_METRO_BBOX["max_lat"]
        and COLUMBUS_GA_METRO_BBOX["min_lng"] <= lng <= COLUMBUS_GA_METRO_BBOX["max_lng"]
    )


def is_in_columbus_ga(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_columbus_ga_metro`."""
    return is_in_columbus_ga_metro(lat, lng)


# ---------------------------------------------------------------------------
# Columbus, GA Submarket Registry (8 submarkets across 4 divisions)
# ---------------------------------------------------------------------------

COLUMBUS_GA_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # DOWNTOWN_RIVERFRONT
    "Uptown": SubmarketMeta(
        name="Uptown",
        borough="DOWNTOWN_RIVERFRONT",
        lat=32.4610,
        lng=-84.9877,
        zoom=14.2,
        pitch=45.0,
        base_lims=0.82,
        capex=4200000.0,
        permit_vel=22.0,
        shift_ratio=1.34,
        sla=52.0,
        description="Broadway & riverwalk mixed-use core with adaptive reuse, hospitality, and student housing.",
        city_id=COLUMBUS_GA_CITY_ID,
    ),
    "Riverwalk": SubmarketMeta(
        name="Riverwalk",
        borough="DOWNTOWN_RIVERFRONT",
        lat=32.4665,
        lng=-84.9985,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.80,
        capex=3600000.0,
        permit_vel=18.0,
        shift_ratio=1.30,
        sla=48.0,
        description="Chattahoochee riverfront recreation and tourism corridor, west of Broadway.",
        city_id=COLUMBUS_GA_CITY_ID,
    ),
    # MIDTOWN
    "Midtown Medical": SubmarketMeta(
        name="Midtown Medical",
        borough="MIDTOWN",
        lat=32.4785,
        lng=-84.9675,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.74,
        capex=2500000.0,
        permit_vel=16.0,
        shift_ratio=1.22,
        sla=44.0,
        description="Columbus Midtown medical/education spine and surrounding residential blocks.",
        city_id=COLUMBUS_GA_CITY_ID,
    ),
    "East Midtown": SubmarketMeta(
        name="East Midtown",
        borough="MIDTOWN",
        lat=32.4920,
        lng=-84.9340,
        zoom=14.0,
        pitch=38.0,
        base_lims=0.72,
        capex=2100000.0,
        permit_vel=15.0,
        shift_ratio=1.20,
        sla=42.0,
        description="Residential grid and commercial nodes along Warm Springs Rd to CSU.",
        city_id=COLUMBUS_GA_CITY_ID,
    ),
    # NORTHSIDE
    "North Columbus": SubmarketMeta(
        name="North Columbus",
        borough="NORTHSIDE",
        lat=32.5750,
        lng=-84.9600,
        zoom=13.8,
        pitch=38.0,
        base_lims=0.78,
        capex=3400000.0,
        permit_vel=19.0,
        shift_ratio=1.28,
        sla=46.0,
        description="Retail and employment centers around Veterans Pkwy and Whitesville Rd.",
        city_id=COLUMBUS_GA_CITY_ID,
    ),
    "Bradley Park": SubmarketMeta(
        name="Bradley Park",
        borough="NORTHSIDE",
        lat=32.5600,
        lng=-84.9350,
        zoom=13.8,
        pitch=38.0,
        base_lims=0.76,
        capex=3000000.0,
        permit_vel=17.0,
        shift_ratio=1.26,
        sla=44.0,
        description="Master-planned retail/office district and surrounding residential infill.",
        city_id=COLUMBUS_GA_CITY_ID,
    ),
    # SOUTH_GATEWAY
    "South Columbus": SubmarketMeta(
        name="South Columbus",
        borough="SOUTH_GATEWAY",
        lat=32.4005,
        lng=-84.9680,
        zoom=13.8,
        pitch=36.0,
        base_lims=0.70,
        capex=1900000.0,
        permit_vel=13.0,
        shift_ratio=1.18,
        sla=40.0,
        description="US-280/Buena Vista Rd corridor reinvestment and Fort Benning-adjacent housing.",
        city_id=COLUMBUS_GA_CITY_ID,
    ),
    "Benning Gateway": SubmarketMeta(
        name="Benning Gateway",
        borough="SOUTH_GATEWAY",
        lat=32.3800,
        lng=-84.9400,
        zoom=13.6,
        pitch=36.0,
        base_lims=0.68,
        capex=1700000.0,
        permit_vel=12.0,
        shift_ratio=1.16,
        sla=38.0,
        description="Gateway area north of Fort Benning with service retail and residential turnover.",
        city_id=COLUMBUS_GA_CITY_ID,
    ),
}

# Divisions catalog built from the declared bboxes and submarket rosters
COLUMBUS_GA_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_RIVERFRONT": BoroughMeta(
        name="DOWNTOWN_RIVERFRONT",
        center_lat=32.4630,
        center_lng=-84.9870,
        zoom=14.2,
        bbox=COLUMBUS_GA_DIVISION_BBOXES["DOWNTOWN_RIVERFRONT"],
        submarkets=[k for k, v in COLUMBUS_GA_SUBMARKETS.items() if v.borough == "DOWNTOWN_RIVERFRONT"],
        city_id=COLUMBUS_GA_CITY_ID,
    ),
    "MIDTOWN": BoroughMeta(
        name="MIDTOWN",
        center_lat=32.4860,
        center_lng=-84.9560,
        zoom=13.8,
        bbox=COLUMBUS_GA_DIVISION_BBOXES["MIDTOWN"],
        submarkets=[k for k, v in COLUMBUS_GA_SUBMARKETS.items() if v.borough == "MIDTOWN"],
        city_id=COLUMBUS_GA_CITY_ID,
    ),
    "NORTHSIDE": BoroughMeta(
        name="NORTHSIDE",
        center_lat=32.5700,
        center_lng=-84.9520,
        zoom=13.6,
        bbox=COLUMBUS_GA_DIVISION_BBOXES["NORTHSIDE"],
        submarkets=[k for k, v in COLUMBUS_GA_SUBMARKETS.items() if v.borough == "NORTHSIDE"],
        city_id=COLUMBUS_GA_CITY_ID,
    ),
    "SOUTH_GATEWAY": BoroughMeta(
        name="SOUTH_GATEWAY",
        center_lat=32.3920,
        center_lng=-84.9550,
        zoom=13.4,
        bbox=COLUMBUS_GA_DIVISION_BBOXES["SOUTH_GATEWAY"],
        submarkets=[k for k, v in COLUMBUS_GA_SUBMARKETS.items() if v.borough == "SOUTH_GATEWAY"],
        city_id=COLUMBUS_GA_CITY_ID,
    ),
}

# Leaf registration — geometry only (datasets live in the spine registry).
REGISTRATION = SpatialRegistration(
    metro_bbox=COLUMBUS_GA_METRO_BBOX,
    division_bboxes=COLUMBUS_GA_DIVISION_BBOXES,
    submarkets=COLUMBUS_GA_SUBMARKETS,
    divisions=COLUMBUS_GA_DIVISIONS,
    contains=is_in_columbus_ga_metro,
)

__all__ = [
    "COLUMBUS_GA_CITY_ID",
    "COLUMBUS_GA_CENTER",
    "COLUMBUS_GA_METRO_BBOX",
    "COLUMBUS_GA_DIVISION_BBOXES",
    "COLUMBUS_GA_SUBMARKETS",
    "COLUMBUS_GA_DIVISIONS",
    "REGISTRATION",
    "is_in_columbus_ga",
    "is_in_columbus_ga_metro",
]

