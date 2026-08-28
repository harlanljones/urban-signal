"""Amarillo, TX — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
are currently limited to SNAP Retailers (TX slice) pending a verifiable public
city permits endpoint (data.texas.gov probe returned none; MGO Connect is not
an open data API).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

AMARILLO_CITY_ID: str = "amarillo"

# Approximate Amarillo city extents: generous box that contains the urbanized
# area across Potter/Randall counties. Downtown is around (35.207, -101.833).
AMARILLO_METRO_BBOX: Dict[str, float] = {
    "min_lat": 35.06,
    "max_lat": 35.35,
    "min_lng": -102.00,
    "max_lng": -101.65,
}

# Registration-contract center: City Hall / Civic Center vicinity.
AMARILLO_CENTER: Dict[str, float] = {"lat": 35.2070, "lng": -101.8330}

# Division bounding boxes (strict subsets of AMARILLO_METRO_BBOX)
AMARILLO_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "CENTRAL_CORE": {"min_lat": 35.175, "max_lat": 35.235, "min_lng": -101.885, "max_lng": -101.780},
    "WEST_SIDE": {"min_lat": 35.150, "max_lat": 35.270, "min_lng": -102.000, "max_lng": -101.885},
    "EAST_GATE": {"min_lat": 35.160, "max_lat": 35.260, "min_lng": -101.780, "max_lng": -101.650},
    "SOUTH_STRIPS": {"min_lat": 35.080, "max_lat": 35.175, "min_lng": -101.960, "max_lng": -101.780},
    "NORTH_LOOP": {"min_lat": 35.235, "max_lat": 35.330, "min_lng": -101.930, "max_lng": -101.760},
}


def is_in_amarillo_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Amarillo metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        AMARILLO_METRO_BBOX["min_lat"] <= lat <= AMARILLO_METRO_BBOX["max_lat"]
        and AMARILLO_METRO_BBOX["min_lng"] <= lng <= AMARILLO_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
AMARILLO_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown Amarillo": SubmarketMeta(
        name="Downtown Amarillo",
        borough="CENTRAL_CORE",
        lat=35.2088,
        lng=-101.8355,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.82,
        capex=6200000.0,
        permit_vel=34.0,
        shift_ratio=1.36,
        sla=58.0,
        description="Civic Center, Polk Street corridor, and historic Route 66 core with mixed commercial renovation and infill.",
        city_id=AMARILLO_CITY_ID,
    ),
    "Polk Street District": SubmarketMeta(
        name="Polk Street District",
        borough="CENTRAL_CORE",
        lat=35.2105,
        lng=-101.8350,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.80,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.30,
        sla=54.0,
        description="Historic main-street blocks with restaurants, nightlife, and adaptive reuse loft conversions.",
        city_id=AMARILLO_CITY_ID,
    ),
    # WEST_SIDE
    "Westgate / Soncy": SubmarketMeta(
        name="Westgate / Soncy",
        borough="WEST_SIDE",
        lat=35.1870,
        lng=-101.9380,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.78,
        capex=5800000.0,
        permit_vel=28.0,
        shift_ratio=1.28,
        sla=52.0,
        description="Regional mall and Soncy Road retail corridor with outparcel medical, hospitality, and steady tenant rollover.",
        city_id=AMARILLO_CITY_ID,
    ),
    "Medical Center & Wolflin": SubmarketMeta(
        name="Medical Center & Wolflin",
        borough="WEST_SIDE",
        lat=35.1805,
        lng=-101.9050,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.79,
        capex=5600000.0,
        permit_vel=29.0,
        shift_ratio=1.30,
        sla=53.0,
        description="BSA / Northwest Texas healthcare cluster and Wolflin residential-adjacent commercial grid.",
        city_id=AMARILLO_CITY_ID,
    ),
    # SOUTH_STRIPS
    "Southwest Amarillo": SubmarketMeta(
        name="Southwest Amarillo",
        borough="SOUTH_STRIPS",
        lat=35.1500,
        lng=-101.9000,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.74,
        capex=4700000.0,
        permit_vel=26.0,
        shift_ratio=1.24,
        sla=48.0,
        description="Southwestern growth belt of newer subdivisions and highway-oriented retail.",
        city_id=AMARILLO_CITY_ID,
    ),
    "Amarillo College Area": SubmarketMeta(
        name="Amarillo College Area",
        borough="SOUTH_STRIPS",
        lat=35.1840,
        lng=-101.8780,
        zoom=14.0,
        pitch=38.0,
        base_lims=0.76,
        capex=5000000.0,
        permit_vel=27.0,
        shift_ratio=1.26,
        sla=50.0,
        description="Campus-adjacent district and Wolflin Heights edges with steady renovation and services.",
        city_id=AMARILLO_CITY_ID,
    ),
    # EAST_GATE
    "East Gateway & Airport": SubmarketMeta(
        name="East Gateway & Airport",
        borough="EAST_GATE",
        lat=35.2200,
        lng=-101.7400,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.70,
        capex=4200000.0,
        permit_vel=22.0,
        shift_ratio=1.20,
        sla=46.0,
        description="Eastern industrial and airport approach corridor along I-40 with logistics and highway services.",
        city_id=AMARILLO_CITY_ID,
    ),
    # NORTH_LOOP
    "Eastridge & North Heights": SubmarketMeta(
        name="Eastridge & North Heights",
        borough="NORTH_LOOP",
        lat=35.2550,
        lng=-101.8200,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.68,
        capex=3600000.0,
        permit_vel=21.0,
        shift_ratio=1.18,
        sla=44.0,
        description="Northern residential plateaus and historic neighborhoods with infrastructure-driven service demand.",
        city_id=AMARILLO_CITY_ID,
    ),
}


AMARILLO_DIVISIONS: Dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=35.2085,
        center_lng=-101.8330,
        zoom=13.5,
        bbox=AMARILLO_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in AMARILLO_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=AMARILLO_CITY_ID,
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=35.1850,
        center_lng=-101.9250,
        zoom=13.0,
        bbox=AMARILLO_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in AMARILLO_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id=AMARILLO_CITY_ID,
    ),
    "SOUTH_STRIPS": BoroughMeta(
        name="SOUTH_STRIPS",
        center_lat=35.1500,
        center_lng=-101.9000,
        zoom=13.0,
        bbox=AMARILLO_DIVISION_BBOXES["SOUTH_STRIPS"],
        submarkets=[k for k, v in AMARILLO_SUBMARKETS.items() if v.borough == "SOUTH_STRIPS"],
        city_id=AMARILLO_CITY_ID,
    ),
    "EAST_GATE": BoroughMeta(
        name="EAST_GATE",
        center_lat=35.2150,
        center_lng=-101.7450,
        zoom=13.0,
        bbox=AMARILLO_DIVISION_BBOXES["EAST_GATE"],
        submarkets=[k for k, v in AMARILLO_SUBMARKETS.items() if v.borough == "EAST_GATE"],
        city_id=AMARILLO_CITY_ID,
    ),
    "NORTH_LOOP": BoroughMeta(
        name="NORTH_LOOP",
        center_lat=35.2700,
        center_lng=-101.8350,
        zoom=12.8,
        bbox=AMARILLO_DIVISION_BBOXES["NORTH_LOOP"],
        submarkets=[k for k, v in AMARILLO_SUBMARKETS.items() if v.borough == "NORTH_LOOP"],
        city_id=AMARILLO_CITY_ID,
    ),
}

AMARILLO_DIVISION_BBOXES_EXPORT = AMARILLO_DIVISION_BBOXES
AMARILLO_SUBMARKETS_EXPORT = AMARILLO_SUBMARKETS
AMARILLO_DIVISIONS_EXPORT = AMARILLO_DIVISIONS

from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=AMARILLO_METRO_BBOX,
    division_bboxes=AMARILLO_DIVISION_BBOXES,
    submarkets=AMARILLO_SUBMARKETS,
    divisions=AMARILLO_DIVISIONS,
    contains=is_in_amarillo_metro,
)

__all__ = [
    "AMARILLO_CENTER",
    "AMARILLO_CITY_ID",
    "AMARILLO_DIVISION_BBOXES",
    "AMARILLO_DIVISION_BBOXES_EXPORT",
    "AMARILLO_DIVISIONS",
    "AMARILLO_DIVISIONS_EXPORT",
    "AMARILLO_METRO_BBOX",
    "AMARILLO_SUBMARKETS",
    "AMARILLO_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_amarillo_metro",
]

