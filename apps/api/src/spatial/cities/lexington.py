"""Lexington, KY — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry). Initial
registration will land SLA via the Kentucky ABC active-license ArcGIS layer
filtered to Fayette County; permits remain unregistered pending a verifiable
public feed on `data.lexingtonky.gov`.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

LEXINGTON_CITY_ID: str = "lexington"

# Approximate Lexington metro extents focused on Fayette County core.
# Downtown is around (38.046, -84.497).
LEXINGTON_METRO_BBOX: Dict[str, float] = {
    "min_lat": 37.90,
    "max_lat": 38.15,
    "min_lng": -84.65,
    "max_lng": -84.30,
}

# Registration-contract center: Government Center / Rupp Arena vicinity.
LEXINGTON_CENTER: Dict[str, float] = {"lat": 38.0460, "lng": -84.4970}

# Division bounding boxes (strict subsets of LEXINGTON_METRO_BBOX)
LEXINGTON_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown, UK campus, Chevy Chase
    "DOWNTOWN_UK": {"min_lat": 38.020, "max_lat": 38.075, "min_lng": -84.530, "max_lng": -84.470},
    # Northside neighborhoods inside New Circle Rd (NoLi, Meadow Park)
    "NORTHSIDE": {"min_lat": 38.075, "max_lat": 38.130, "min_lng": -84.550, "max_lng": -84.450},
    # South/east corridors (Hamburg, Richmond Rd)
    "SOUTHEAST": {"min_lat": 37.980, "max_lat": 38.050, "min_lng": -84.480, "max_lng": -84.340},
    # Southwest belts (Harrodsburg Rd, Beaumont Centre)
    "SOUTHWEST": {"min_lat": 37.980, "max_lat": 38.050, "min_lng": -84.650, "max_lng": -84.530},
    # East of downtown toward Winchester Rd and I-75
    "EAST_NEW_CIRCLE": {"min_lat": 38.030, "max_lat": 38.110, "min_lng": -84.450, "max_lng": -84.340},
}


def is_in_lexington_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Lexington metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        LEXINGTON_METRO_BBOX["min_lat"] <= lat <= LEXINGTON_METRO_BBOX["max_lat"]
        and LEXINGTON_METRO_BBOX["min_lng"] <= lng <= LEXINGTON_METRO_BBOX["max_lng"]
    )


# Submarkets (coordinates must live inside their division boxes for containment).
LEXINGTON_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # DOWNTOWN_UK
    "Downtown & Rupp Arena": SubmarketMeta(
        name="Downtown & Rupp Arena",
        borough="DOWNTOWN_UK",
        lat=38.0470,
        lng=-84.5020,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=7200000.0,
        permit_vel=36.0,
        shift_ratio=1.42,
        sla=60.0,
        description="Civic core around Rupp Arena and the Convention Center with adaptive reuse and hospitality infill.",
        city_id=LEXINGTON_CITY_ID,
    ),
    "University of Kentucky": SubmarketMeta(
        name="University of Kentucky",
        borough="DOWNTOWN_UK",
        lat=38.0300,
        lng=-84.5050,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.84,
        capex=6500000.0,
        permit_vel=33.0,
        shift_ratio=1.38,
        sla=58.0,
        description="Campus-adjacent mixed-use and student housing along Limestone, Euclid, and Nicholasville corridors.",
        city_id=LEXINGTON_CITY_ID,
    ),
    "Chevy Chase & Euclid Ave": SubmarketMeta(
        name="Chevy Chase & Euclid Ave",
        borough="DOWNTOWN_UK",
        lat=38.0310,
        lng=-84.4880,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.82,
        capex=5800000.0,
        permit_vel=30.0,
        shift_ratio=1.34,
        sla=56.0,
        description="Neighborhood retail corridor east of campus with small-lot infill and renovations.",
        city_id=LEXINGTON_CITY_ID,
    ),
    # NORTHSIDE
    "North Limestone (NoLi)": SubmarketMeta(
        name="North Limestone (NoLi)",
        borough="NORTHSIDE",
        lat=38.0950,
        lng=-84.4750,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.78,
        capex=4800000.0,
        permit_vel=26.0,
        shift_ratio=1.28,
        sla=52.0,
        description="Arts and maker corridor north of downtown with steady small-scale reinvestment.",
        city_id=LEXINGTON_CITY_ID,
    ),
    "Meadow Park & Russell Cave": SubmarketMeta(
        name="Meadow Park & Russell Cave",
        borough="NORTHSIDE",
        lat=38.1100,
        lng=-84.5200,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.74,
        capex=4200000.0,
        permit_vel=22.0,
        shift_ratio=1.22,
        sla=48.0,
        description="Northside neighborhoods along Russell Cave Rd and Loudon Ave.",
        city_id=LEXINGTON_CITY_ID,
    ),
    # SOUTHEAST
    "Hamburg Pavilion": SubmarketMeta(
        name="Hamburg Pavilion",
        borough="SOUTHEAST",
        lat=38.0300,
        lng=-84.4200,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=54.0,
        description="I-75 retail and mixed-use node with ongoing pad-site development and hospitality.",
        city_id=LEXINGTON_CITY_ID,
    ),
    "Richmond Rd Corridor": SubmarketMeta(
        name="Richmond Rd Corridor",
        borough="SOUTHEAST",
        lat=38.0050,
        lng=-84.4550,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.76,
        capex=5000000.0,
        permit_vel=24.0,
        shift_ratio=1.24,
        sla=50.0,
        description="Established corridor with renovation-led permits and selective infill.",
        city_id=LEXINGTON_CITY_ID,
    ),
    # SOUTHWEST
    "Beaumont Centre & Harrodsburg": SubmarketMeta(
        name="Beaumont Centre & Harrodsburg",
        borough="SOUTHWEST",
        lat=37.9950,
        lng=-84.5700,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.77,
        capex=5200000.0,
        permit_vel=25.0,
        shift_ratio=1.25,
        sla=50.0,
        description="Southwest growth belt with office, retail, and multifamily infill.",
        city_id=LEXINGTON_CITY_ID,
    ),
    "Nicholasville Rd South": SubmarketMeta(
        name="Nicholasville Rd South",
        borough="SOUTHWEST",
        lat=37.9900,
        lng=-84.5350,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.75,
        capex=4800000.0,
        permit_vel=23.0,
        shift_ratio=1.22,
        sla=48.0,
        description="Regional commercial spine with redevelopment pressure around major intersections.",
        city_id=LEXINGTON_CITY_ID,
    ),
    # EAST_NEW_CIRCLE
    "Winchester Rd & Industrial": SubmarketMeta(
        name="Winchester Rd & Industrial",
        borough="EAST_NEW_CIRCLE",
        lat=38.0800,
        lng=-84.4100,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.73,
        capex=4300000.0,
        permit_vel=21.0,
        shift_ratio=1.20,
        sla=46.0,
        description="Industrial and logistics corridor with selective commercial reinvestment.",
        city_id=LEXINGTON_CITY_ID,
    ),
    "Andover & Pleasant Ridge": SubmarketMeta(
        name="Andover & Pleasant Ridge",
        borough="EAST_NEW_CIRCLE",
        lat=38.0650,
        lng=-84.3850,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.72,
        capex=4100000.0,
        permit_vel=20.0,
        shift_ratio=1.18,
        sla=44.0,
        description="East-side neighborhoods with steady residential improvements and services.",
        city_id=LEXINGTON_CITY_ID,
    ),
}


LEXINGTON_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_UK": BoroughMeta(
        name="DOWNTOWN_UK",
        center_lat=38.0420,
        center_lng=-84.5000,
        zoom=13.8,
        bbox=LEXINGTON_DIVISION_BBOXES["DOWNTOWN_UK"],
        submarkets=[k for k, v in LEXINGTON_SUBMARKETS.items() if v.borough == "DOWNTOWN_UK"],
        city_id=LEXINGTON_CITY_ID,
    ),
    "NORTHSIDE": BoroughMeta(
        name="NORTHSIDE",
        center_lat=38.1050,
        center_lng=-84.5000,
        zoom=13.2,
        bbox=LEXINGTON_DIVISION_BBOXES["NORTHSIDE"],
        submarkets=[k for k, v in LEXINGTON_SUBMARKETS.items() if v.borough == "NORTHSIDE"],
        city_id=LEXINGTON_CITY_ID,
    ),
    "SOUTHEAST": BoroughMeta(
        name="SOUTHEAST",
        center_lat=38.0150,
        center_lng=-84.4400,
        zoom=13.2,
        bbox=LEXINGTON_DIVISION_BBOXES["SOUTHEAST"],
        submarkets=[k for k, v in LEXINGTON_SUBMARKETS.items() if v.borough == "SOUTHEAST"],
        city_id=LEXINGTON_CITY_ID,
    ),
    "SOUTHWEST": BoroughMeta(
        name="SOUTHWEST",
        center_lat=38.0100,
        center_lng=-84.5900,
        zoom=13.0,
        bbox=LEXINGTON_DIVISION_BBOXES["SOUTHWEST"],
        submarkets=[k for k, v in LEXINGTON_SUBMARKETS.items() if v.borough == "SOUTHWEST"],
        city_id=LEXINGTON_CITY_ID,
    ),
    "EAST_NEW_CIRCLE": BoroughMeta(
        name="EAST_NEW_CIRCLE",
        center_lat=38.0700,
        center_lng=-84.3950,
        zoom=13.2,
        bbox=LEXINGTON_DIVISION_BBOXES["EAST_NEW_CIRCLE"],
        submarkets=[k for k, v in LEXINGTON_SUBMARKETS.items() if v.borough == "EAST_NEW_CIRCLE"],
        city_id=LEXINGTON_CITY_ID,
    ),
}

# Export aliases mirroring convention in other city modules
LEX_DIVISION_BBOXES = LEXINGTON_DIVISION_BBOXES
LEX_SUBMARKETS = LEXINGTON_SUBMARKETS
LEX_DIVISIONS = LEXINGTON_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=LEXINGTON_METRO_BBOX,
    division_bboxes=LEXINGTON_DIVISION_BBOXES,
    submarkets=LEXINGTON_SUBMARKETS,
    divisions=LEXINGTON_DIVISIONS,
    contains=is_in_lexington_metro,
)

__all__ = [
    "LEXINGTON_CENTER",
    "LEXINGTON_CITY_ID",
    "LEXINGTON_DIVISION_BBOXES",
    "LEX_DIVISION_BBOXES",
    "LEXINGTON_DIVISIONS",
    "LEX_DIVISIONS",
    "LEXINGTON_METRO_BBOX",
    "LEXINGTON_SUBMARKETS",
    "LEX_SUBMARKETS",
    "REGISTRATION",
    "is_in_lexington_metro",
]

