"""Monroe, LA — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
are initially limited to SNAP Retailers (LA slice) pending a verifiable public
city permits endpoint (Ouachita Parish/Monroe currently publish citizen portals,
not an open-data API).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

MONROE_CITY_ID: str = "monroe"

# Approximate Monroe metro extents: generous box spanning Monroe + West Monroe
# and immediate growth belts (Richwood, Swartz, Sterlington corridor).
# Downtown Monroe is around (32.509, -92.119).
MONROE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 32.42,
    "max_lat": 32.62,
    "min_lng": -92.27,
    "max_lng": -91.98,
}

# Registration-contract center: Monroe City Hall vicinity.
MONROE_CENTER: Dict[str, float] = {"lat": 32.5093, "lng": -92.1193}

# Division bounding boxes (strict subsets of MONROE_METRO_BBOX)
MONROE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown Monroe, Riverfront, ULM-adjacent core
    "CENTRAL_CORE": {"min_lat": 32.495, "max_lat": 32.545, "min_lng": -92.140, "max_lng": -92.060},
    # West Monroe including Antique Alley and I-20 commercial corridor
    "WEST_BANK": {"min_lat": 32.490, "max_lat": 32.570, "min_lng": -92.230, "max_lng": -92.120},
    # North Monroe and Sterlington Road (US-165 North) corridor
    "NORTH_LOOP": {"min_lat": 32.560, "max_lat": 32.620, "min_lng": -92.180, "max_lng": -91.990},
    # South Monroe / Richwood belts near US-165/I-20 south of the core
    "SOUTH_STRIPS": {"min_lat": 32.420, "max_lat": 32.510, "min_lng": -92.200, "max_lng": -92.050},
    # East Monroe / Pecanland / Airport / Swartz approach
    "EAST_GATE": {"min_lat": 32.495, "max_lat": 32.590, "min_lng": -92.080, "max_lng": -91.980},
}


def is_in_monroe_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Monroe metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        MONROE_METRO_BBOX["min_lat"] <= lat <= MONROE_METRO_BBOX["max_lat"]
        and MONROE_METRO_BBOX["min_lng"] <= lng <= MONROE_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
MONROE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown Monroe & Riverfront": SubmarketMeta(
        name="Downtown Monroe & Riverfront",
        borough="CENTRAL_CORE",
        lat=32.5090,
        lng=-92.1185,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.78,
        capex=3800000.0,
        permit_vel=18.0,
        shift_ratio=1.20,
        sla=44.0,
        description="Historic downtown on the Ouachita River with civic anchors and small-scale adaptive reuse.",
        city_id=MONROE_CITY_ID,
    ),
    "ULM / Bayou Desiard": SubmarketMeta(
        name="ULM / Bayou Desiard",
        borough="CENTRAL_CORE",
        lat=32.5290,
        lng=-92.0670,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.76,
        capex=3600000.0,
        permit_vel=17.0,
        shift_ratio=1.18,
        sla=42.0,
        description="University of Louisiana at Monroe district; campus-adjacent residential and services.",
        city_id=MONROE_CITY_ID,
    ),
    # WEST_BANK
    "West Monroe / Antique Alley": SubmarketMeta(
        name="West Monroe / Antique Alley",
        borough="WEST_BANK",
        lat=32.5160,
        lng=-92.1450,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.74,
        capex=3400000.0,
        permit_vel=16.0,
        shift_ratio=1.16,
        sla=42.0,
        description="Antique Alley and West Monroe core across the Ouachita with main-street retail ribbons.",
        city_id=MONROE_CITY_ID,
    ),
    "I-20 Retail Corridor (West Monroe)": SubmarketMeta(
        name="I-20 Retail Corridor (West Monroe)",
        borough="WEST_BANK",
        lat=32.5110,
        lng=-92.1800,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.72,
        capex=3200000.0,
        permit_vel=15.0,
        shift_ratio=1.14,
        sla=40.0,
        description="Interstate-oriented commercial and hospitality nodes along I-20 in West Monroe.",
        city_id=MONROE_CITY_ID,
    ),
    # EAST_GATE
    "Pecanland Mall & Millhaven": SubmarketMeta(
        name="Pecanland Mall & Millhaven",
        borough="EAST_GATE",
        lat=32.5040,
        lng=-92.0620,
        zoom=13.8,
        pitch=40.0,
        base_lims=0.72,
        capex=3100000.0,
        permit_vel=15.0,
        shift_ratio=1.14,
        sla=40.0,
        description="Regional retail hub around Pecanland Mall and Millhaven corridor east of downtown.",
        city_id=MONROE_CITY_ID,
    ),
    "Monroe Regional Airport Vicinity": SubmarketMeta(
        name="Monroe Regional Airport Vicinity",
        borough="EAST_GATE",
        lat=32.5100,
        lng=-92.0370,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.70,
        capex=3000000.0,
        permit_vel=14.0,
        shift_ratio=1.12,
        sla=38.0,
        description="Airport-adjacent logistics and services east of the core along Central Ave/Millhaven.",
        city_id=MONROE_CITY_ID,
    ),
    # NORTH_LOOP
    "Sterlington Road / US-165 North": SubmarketMeta(
        name="Sterlington Road / US-165 North",
        borough="NORTH_LOOP",
        lat=32.5850,
        lng=-92.0770,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.70,
        capex=3000000.0,
        permit_vel=14.0,
        shift_ratio=1.12,
        sla=38.0,
        description="Growth corridor along US-165 toward Sterlington with medical and neighborhood services.",
        city_id=MONROE_CITY_ID,
    ),
    # SOUTH_STRIPS
    "South Monroe / Richwood": SubmarketMeta(
        name="South Monroe / Richwood",
        borough="SOUTH_STRIPS",
        lat=32.4450,
        lng=-92.1000,
        zoom=13.3,
        pitch=38.0,
        base_lims=0.68,
        capex=2800000.0,
        permit_vel=13.0,
        shift_ratio=1.10,
        sla=36.0,
        description="Southern belt toward Richwood along US-165 with highway services and residential infill.",
        city_id=MONROE_CITY_ID,
    ),
}


MONROE_DIVISIONS: Dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=32.5200,
        center_lng=-92.1100,
        zoom=13.6,
        bbox=MONROE_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in MONROE_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=MONROE_CITY_ID,
    ),
    "WEST_BANK": BoroughMeta(
        name="WEST_BANK",
        center_lat=32.5250,
        center_lng=-92.1700,
        zoom=13.2,
        bbox=MONROE_DIVISION_BBOXES["WEST_BANK"],
        submarkets=[k for k, v in MONROE_SUBMARKETS.items() if v.borough == "WEST_BANK"],
        city_id=MONROE_CITY_ID,
    ),
    "NORTH_LOOP": BoroughMeta(
        name="NORTH_LOOP",
        center_lat=32.5900,
        center_lng=-92.0850,
        zoom=12.8,
        bbox=MONROE_DIVISION_BBOXES["NORTH_LOOP"],
        submarkets=[k for k, v in MONROE_SUBMARKETS.items() if v.borough == "NORTH_LOOP"],
        city_id=MONROE_CITY_ID,
    ),
    "SOUTH_STRIPS": BoroughMeta(
        name="SOUTH_STRIPS",
        center_lat=32.4650,
        center_lng=-92.1200,
        zoom=13.0,
        bbox=MONROE_DIVISION_BBOXES["SOUTH_STRIPS"],
        submarkets=[k for k, v in MONROE_SUBMARKETS.items() if v.borough == "SOUTH_STRIPS"],
        city_id=MONROE_CITY_ID,
    ),
    "EAST_GATE": BoroughMeta(
        name="EAST_GATE",
        center_lat=32.5400,
        center_lng=-92.0300,
        zoom=13.2,
        bbox=MONROE_DIVISION_BBOXES["EAST_GATE"],
        submarkets=[k for k, v in MONROE_SUBMARKETS.items() if v.borough == "EAST_GATE"],
        city_id=MONROE_CITY_ID,
    ),
}

MONROE_DIVISION_BBOXES_EXPORT = MONROE_DIVISION_BBOXES
MONROE_SUBMARKETS_EXPORT = MONROE_SUBMARKETS
MONROE_DIVISIONS_EXPORT = MONROE_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=MONROE_METRO_BBOX,
    division_bboxes=MONROE_DIVISION_BBOXES,
    submarkets=MONROE_SUBMARKETS,
    divisions=MONROE_DIVISIONS,
    contains=is_in_monroe_metro,
)

__all__ = [
    "MONROE_CENTER",
    "MONROE_CITY_ID",
    "MONROE_DIVISION_BBOXES",
    "MONROE_DIVISION_BBOXES_EXPORT",
    "MONROE_DIVISIONS",
    "MONROE_DIVISIONS_EXPORT",
    "MONROE_METRO_BBOX",
    "MONROE_SUBMARKETS",
    "MONROE_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_monroe_metro",
]

