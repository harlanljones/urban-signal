"""Alexandria, LA — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs register in the spine (city_registry)
and for Alexandria initially point to SNAP Retailers (LA slice) unless a
verifiable public permits endpoint is proven (Rapides Parish / City portal).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

ALEXANDRIA_CITY_ID: str = "alexandria"

# Approximate Alexandria metro extents: generous box that contains the
# urbanized area across Alexandria and Pineville along the Red River,
# including England Airpark/AEX and south corridors.
# Downtown is around (31.3113, -92.4451).
ALEXANDRIA_METRO_BBOX: Dict[str, float] = {
    "min_lat": 31.20,
    "max_lat": 31.43,
    "min_lng": -92.60,
    "max_lng": -92.27,
}

# Registration-contract center: Alexandria City Hall vicinity.
ALEXANDRIA_CENTER: Dict[str, float] = {"lat": 31.3113, "lng": -92.4451}

# Division bounding boxes (strict subsets of ALEXANDRIA_METRO_BBOX)
ALEXANDRIA_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown, Garden District, Red Riverfront
    "CENTRAL_CORE": {"min_lat": 31.290, "max_lat": 31.340, "min_lng": -92.480, "max_lng": -92.420},
    # MacArthur Dr commercial corridors and west-side districts
    "WEST_SIDE": {"min_lat": 31.280, "max_lat": 31.350, "min_lng": -92.600, "max_lng": -92.500},
    # Pineville and Red River east bank
    "EAST_BANK": {"min_lat": 31.310, "max_lat": 31.380, "min_lng": -92.460, "max_lng": -92.270},
    # South Alexandria growth belts and Coliseum Blvd area
    "SOUTH_STRIPS": {"min_lat": 31.200, "max_lat": 31.290, "min_lng": -92.530, "max_lng": -92.400},
    # North Alexandria / Pineville loop and England Airpark/AEX vicinity
    "NORTH_LOOP": {"min_lat": 31.350, "max_lat": 31.430, "min_lng": -92.550, "max_lng": -92.380},
}


def is_in_alexandria_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Alexandria metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        ALEXANDRIA_METRO_BBOX["min_lat"] <= lat <= ALEXANDRIA_METRO_BBOX["max_lat"]
        and ALEXANDRIA_METRO_BBOX["min_lng"] <= lng <= ALEXANDRIA_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
ALEXANDRIA_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown Alexandria": SubmarketMeta(
        name="Downtown Alexandria",
        borough="CENTRAL_CORE",
        lat=31.3120,
        lng=-92.4450,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.80,
        capex=4200000.0,
        permit_vel=20.0,
        shift_ratio=1.20,
        sla=48.0,
        description="Historic core and Red River riverfront with civic anchors and adaptive reuse.",
        city_id=ALEXANDRIA_CITY_ID,
    ),
    "Red Riverfront": SubmarketMeta(
        name="Red Riverfront",
        borough="CENTRAL_CORE",
        lat=31.3150,
        lng=-92.4400,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.79,
        capex=3900000.0,
        permit_vel=19.0,
        shift_ratio=1.18,
        sla=46.0,
        description="Riverfront entertainment, hospitality, and mixed-use frontage along the levee.",
        city_id=ALEXANDRIA_CITY_ID,
    ),
    "Garden District & Jackson St": SubmarketMeta(
        name="Garden District & Jackson St",
        borough="CENTRAL_CORE",
        lat=31.3010,
        lng=-92.4620,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.77,
        capex=3600000.0,
        permit_vel=18.0,
        shift_ratio=1.16,
        sla=44.0,
        description="Historic neighborhood fabric and Jackson Street corridor small-format reinvestment.",
        city_id=ALEXANDRIA_CITY_ID,
    ),
    # WEST_SIDE
    "MacArthur Corridor": SubmarketMeta(
        name="MacArthur Corridor",
        borough="WEST_SIDE",
        lat=31.3040,
        lng=-92.5200,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.74,
        capex=3300000.0,
        permit_vel=17.0,
        shift_ratio=1.14,
        sla=44.0,
        description="US-165/MacArthur Dr retail, services, and auto-oriented commercial ribbons.",
        city_id=ALEXANDRIA_CITY_ID,
    ),
    # EAST_BANK
    "Pineville Downtown": SubmarketMeta(
        name="Pineville Downtown",
        borough="EAST_BANK",
        lat=31.3230,
        lng=-92.4340,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.73,
        capex=3200000.0,
        permit_vel=16.0,
        shift_ratio=1.12,
        sla=42.0,
        description="Historic Pineville main street and east-bank civic core across the Red River.",
        city_id=ALEXANDRIA_CITY_ID,
    ),
    # SOUTH_STRIPS
    "Kingsville & Coliseum": SubmarketMeta(
        name="Kingsville & Coliseum",
        borough="SOUTH_STRIPS",
        lat=31.2620,
        lng=-92.4760,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.71,
        capex=3000000.0,
        permit_vel=15.0,
        shift_ratio=1.10,
        sla=42.0,
        description="South Alexandria growth belt near Coliseum Blvd with highway-oriented retail.",
        city_id=ALEXANDRIA_CITY_ID,
    ),
    # NORTH_LOOP
    "AEX / England Airpark": SubmarketMeta(
        name="AEX / England Airpark",
        borough="NORTH_LOOP",
        lat=31.3700,
        lng=-92.5200,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.70,
        capex=2900000.0,
        permit_vel=14.0,
        shift_ratio=1.08,
        sla=42.0,
        description="Alexandria International Airport and Airpark logistics/industrial campus.",
        city_id=ALEXANDRIA_CITY_ID,
    ),
    "Tioga & North Pineville": SubmarketMeta(
        name="Tioga & North Pineville",
        borough="NORTH_LOOP",
        lat=31.4000,
        lng=-92.4300,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.69,
        capex=2800000.0,
        permit_vel=14.0,
        shift_ratio=1.06,
        sla=42.0,
        description="Northern neighborhoods and commercial nodes spanning US-167 corridor.",
        city_id=ALEXANDRIA_CITY_ID,
    ),
}


ALEXANDRIA_DIVISIONS: Dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=31.3150,
        center_lng=-92.4450,
        zoom=13.8,
        bbox=ALEXANDRIA_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in ALEXANDRIA_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=ALEXANDRIA_CITY_ID,
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=31.3150,
        center_lng=-92.5500,
        zoom=13.2,
        bbox=ALEXANDRIA_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in ALEXANDRIA_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id=ALEXANDRIA_CITY_ID,
    ),
    "SOUTH_STRIPS": BoroughMeta(
        name="SOUTH_STRIPS",
        center_lat=31.2450,
        center_lng=-92.4650,
        zoom=13.0,
        bbox=ALEXANDRIA_DIVISION_BBOXES["SOUTH_STRIPS"],
        submarkets=[k for k, v in ALEXANDRIA_SUBMARKETS.items() if v.borough == "SOUTH_STRIPS"],
        city_id=ALEXANDRIA_CITY_ID,
    ),
    "EAST_BANK": BoroughMeta(
        name="EAST_BANK",
        center_lat=31.3450,
        center_lng=-92.3800,
        zoom=13.2,
        bbox=ALEXANDRIA_DIVISION_BBOXES["EAST_BANK"],
        submarkets=[k for k, v in ALEXANDRIA_SUBMARKETS.items() if v.borough == "EAST_BANK"],
        city_id=ALEXANDRIA_CITY_ID,
    ),
    "NORTH_LOOP": BoroughMeta(
        name="NORTH_LOOP",
        center_lat=31.3900,
        center_lng=-92.4700,
        zoom=12.8,
        bbox=ALEXANDRIA_DIVISION_BBOXES["NORTH_LOOP"],
        submarkets=[k for k, v in ALEXANDRIA_SUBMARKETS.items() if v.borough == "NORTH_LOOP"],
        city_id=ALEXANDRIA_CITY_ID,
    ),
}

ALEXANDRIA_DIVISION_BBOXES_EXPORT = ALEXANDRIA_DIVISION_BBOXES
ALEXANDRIA_SUBMARKETS_EXPORT = ALEXANDRIA_SUBMARKETS
ALEXANDRIA_DIVISIONS_EXPORT = ALEXANDRIA_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=ALEXANDRIA_METRO_BBOX,
    division_bboxes=ALEXANDRIA_DIVISION_BBOXES,
    submarkets=ALEXANDRIA_SUBMARKETS,
    divisions=ALEXANDRIA_DIVISIONS,
    contains=is_in_alexandria_metro,
)

__all__ = [
    "ALEXANDRIA_CENTER",
    "ALEXANDRIA_CITY_ID",
    "ALEXANDRIA_DIVISION_BBOXES",
    "ALEXANDRIA_DIVISION_BBOXES_EXPORT",
    "ALEXANDRIA_DIVISIONS",
    "ALEXANDRIA_DIVISIONS_EXPORT",
    "ALEXANDRIA_METRO_BBOX",
    "ALEXANDRIA_SUBMARKETS",
    "ALEXANDRIA_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_alexandria_metro",
]

