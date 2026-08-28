"""Jackson, MS — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
start with a verified fallback to SNAP Retailers (MS slice) unless/until a
public permits/311 GIS endpoint is proven on open.jacksonms.gov (US-288).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

JACKSON_MS_CITY_ID: str = "jackson_ms"

# Approximate Jackson metro extents covering core Hinds/Rankin/Madison communities:
# Jackson, Clinton, Ridgeland, Madison, Flowood, Pearl, Byram.
# Downtown is around (32.2989, -90.1847).
JACKSON_MS_METRO_BBOX: Dict[str, float] = {
    "min_lat": 32.15,
    "max_lat": 32.50,
    "min_lng": -90.45,
    "max_lng": -89.85,
}

# Registration-contract center: Jackson City Hall vicinity.
JACKSON_MS_CENTER: Dict[str, float] = {"lat": 32.2989, "lng": -90.1847}

# Division bounding boxes (strict subsets of JACKSON_MS_METRO_BBOX)
JACKSON_MS_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown core, Belhaven edge, Capitol complex
    "DOWNTOWN_CORE": {"min_lat": 32.280, "max_lat": 32.330, "min_lng": -90.220, "max_lng": -90.160},
    # North Jackson to Ridgeland/Madison commercial belts
    "NORTH_JACKSON_MADISON": {"min_lat": 32.340, "max_lat": 32.500, "min_lng": -90.350, "max_lng": -89.950},
    # West Jackson and Clinton corridors
    "WEST_CLINTON": {"min_lat": 32.300, "max_lat": 32.450, "min_lng": -90.450, "max_lng": -90.230},
    # Flowood/Pearl east-of-I-55 corridors and JAN airport approaches
    "EAST_FLOWOOD_RANKIN": {"min_lat": 32.260, "max_lat": 32.410, "min_lng": -90.150, "max_lng": -89.850},
    # South Jackson & Byram growth belt
    "SOUTH_BELT_BYRAM": {"min_lat": 32.150, "max_lat": 32.300, "min_lng": -90.350, "max_lng": -90.120},
}


def is_in_jackson_ms_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Jackson metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        JACKSON_MS_METRO_BBOX["min_lat"] <= lat <= JACKSON_MS_METRO_BBOX["max_lat"]
        and JACKSON_MS_METRO_BBOX["min_lng"] <= lng <= JACKSON_MS_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
JACKSON_MS_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # DOWNTOWN_CORE
    "Downtown Jackson": SubmarketMeta(
        name="Downtown Jackson",
        borough="DOWNTOWN_CORE",
        lat=32.2989,
        lng=-90.1847,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.82,
        capex=5200000.0,
        permit_vel=24.0,
        shift_ratio=1.28,
        sla=52.0,
        description="Capitol complex, government, and mixed-use reinvestment core.",
        city_id=JACKSON_MS_CITY_ID,
    ),
    "Fondren & Belhaven": SubmarketMeta(
        name="Fondren & Belhaven",
        borough="DOWNTOWN_CORE",
        lat=32.3235,
        lng=-90.1760,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.80,
        capex=4800000.0,
        permit_vel=22.0,
        shift_ratio=1.24,
        sla=50.0,
        description="Historic neighborhoods north of downtown with medical and cultural anchors.",
        city_id=JACKSON_MS_CITY_ID,
    ),
    # WEST_CLINTON
    "JSU & West Capitol": SubmarketMeta(
        name="JSU & West Capitol",
        borough="WEST_CLINTON",
        lat=32.2980,
        lng=-90.2100,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.76,
        capex=4200000.0,
        permit_vel=20.0,
        shift_ratio=1.20,
        sla=48.0,
        description="Jackson State University district and West Capitol corridor reinvestment.",
        city_id=JACKSON_MS_CITY_ID,
    ),
    "Clinton Main Street": SubmarketMeta(
        name="Clinton Main Street",
        borough="WEST_CLINTON",
        lat=32.3410,
        lng=-90.3280,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.74,
        capex=4000000.0,
        permit_vel=18.0,
        shift_ratio=1.18,
        sla=46.0,
        description="Historic downtown Clinton and MS College vicinity with corridor infill.",
        city_id=JACKSON_MS_CITY_ID,
    ),
    # EAST_FLOWOOD_RANKIN
    "Flowood & Dogwood": SubmarketMeta(
        name="Flowood & Dogwood",
        borough="EAST_FLOWOOD_RANKIN",
        lat=32.3320,
        lng=-90.0670,
        zoom=13.8,
        pitch=40.0,
        base_lims=0.78,
        capex=4600000.0,
        permit_vel=21.0,
        shift_ratio=1.22,
        sla=48.0,
        description="Lakeland Drive medical/retail spine and Dogwood Festival commercial hub.",
        city_id=JACKSON_MS_CITY_ID,
    ),
    "Pearl & Airport Corridor": SubmarketMeta(
        name="Pearl & Airport Corridor",
        borough="EAST_FLOWOOD_RANKIN",
        lat=32.2750,
        lng=-90.0800,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.72,
        capex=3800000.0,
        permit_vel=19.0,
        shift_ratio=1.18,
        sla=46.0,
        description="Pearl retail corridors and JAN airport approaches along MS-475.",
        city_id=JACKSON_MS_CITY_ID,
    ),
    # NORTH_JACKSON_MADISON
    "Ridgeland & Colony Park": SubmarketMeta(
        name="Ridgeland & Colony Park",
        borough="NORTH_JACKSON_MADISON",
        lat=32.4200,
        lng=-90.1400,
        zoom=13.8,
        pitch=40.0,
        base_lims=0.79,
        capex=5100000.0,
        permit_vel=23.0,
        shift_ratio=1.24,
        sla=50.0,
        description="I-55 frontage retail/office belts and mixed-use nodes in Ridgeland.",
        city_id=JACKSON_MS_CITY_ID,
    ),
    "Madison Town Center": SubmarketMeta(
        name="Madison Town Center",
        borough="NORTH_JACKSON_MADISON",
        lat=32.4620,
        lng=-90.1240,
        zoom=13.8,
        pitch=40.0,
        base_lims=0.77,
        capex=4700000.0,
        permit_vel=20.0,
        shift_ratio=1.20,
        sla=46.0,
        description="Madison center and Highland Colony nodes with steady suburban infill.",
        city_id=JACKSON_MS_CITY_ID,
    ),
    # SOUTH_BELT_BYRAM
    "Byram & South Jackson": SubmarketMeta(
        name="Byram & South Jackson",
        borough="SOUTH_BELT_BYRAM",
        lat=32.1960,
        lng=-90.2460,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.70,
        capex=3600000.0,
        permit_vel=18.0,
        shift_ratio=1.16,
        sla=44.0,
        description="South I-55 growth belt with highway-oriented retail and services.",
        city_id=JACKSON_MS_CITY_ID,
    ),
}


JACKSON_MS_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=32.3050,
        center_lng=-90.1850,
        zoom=13.8,
        bbox=JACKSON_MS_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in JACKSON_MS_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id=JACKSON_MS_CITY_ID,
    ),
    "NORTH_JACKSON_MADISON": BoroughMeta(
        name="NORTH_JACKSON_MADISON",
        center_lat=32.4100,
        center_lng=-90.1800,
        zoom=12.8,
        bbox=JACKSON_MS_DIVISION_BBOXES["NORTH_JACKSON_MADISON"],
        submarkets=[k for k, v in JACKSON_MS_SUBMARKETS.items() if v.borough == "NORTH_JACKSON_MADISON"],
        city_id=JACKSON_MS_CITY_ID,
    ),
    "WEST_CLINTON": BoroughMeta(
        name="WEST_CLINTON",
        center_lat=32.3650,
        center_lng=-90.3200,
        zoom=13.0,
        bbox=JACKSON_MS_DIVISION_BBOXES["WEST_CLINTON"],
        submarkets=[k for k, v in JACKSON_MS_SUBMARKETS.items() if v.borough == "WEST_CLINTON"],
        city_id=JACKSON_MS_CITY_ID,
    ),
    "EAST_FLOWOOD_RANKIN": BoroughMeta(
        name="EAST_FLOWOOD_RANKIN",
        center_lat=32.3300,
        center_lng=-90.0200,
        zoom=13.0,
        bbox=JACKSON_MS_DIVISION_BBOXES["EAST_FLOWOOD_RANKIN"],
        submarkets=[k for k, v in JACKSON_MS_SUBMARKETS.items() if v.borough == "EAST_FLOWOOD_RANKIN"],
        city_id=JACKSON_MS_CITY_ID,
    ),
    "SOUTH_BELT_BYRAM": BoroughMeta(
        name="SOUTH_BELT_BYRAM",
        center_lat=32.2200,
        center_lng=-90.2300,
        zoom=12.8,
        bbox=JACKSON_MS_DIVISION_BBOXES["SOUTH_BELT_BYRAM"],
        submarkets=[k for k, v in JACKSON_MS_SUBMARKETS.items() if v.borough == "SOUTH_BELT_BYRAM"],
        city_id=JACKSON_MS_CITY_ID,
    ),
}

JACKSON_MS_DIVISION_BBOXES_EXPORT = JACKSON_MS_DIVISION_BBOXES
JACKSON_MS_SUBMARKETS_EXPORT = JACKSON_MS_SUBMARKETS
JACKSON_MS_DIVISIONS_EXPORT = JACKSON_MS_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=JACKSON_MS_METRO_BBOX,
    division_bboxes=JACKSON_MS_DIVISION_BBOXES,
    submarkets=JACKSON_MS_SUBMARKETS,
    divisions=JACKSON_MS_DIVISIONS,
    contains=is_in_jackson_ms_metro,
)

__all__ = [
    "JACKSON_MS_CENTER",
    "JACKSON_MS_CITY_ID",
    "JACKSON_MS_DIVISION_BBOXES",
    "JACKSON_MS_DIVISION_BBOXES_EXPORT",
    "JACKSON_MS_DIVISIONS",
    "JACKSON_MS_DIVISIONS_EXPORT",
    "JACKSON_MS_METRO_BBOX",
    "JACKSON_MS_SUBMARKETS",
    "JACKSON_MS_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_jackson_ms_metro",
]

