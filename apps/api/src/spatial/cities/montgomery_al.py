"""Montgomery, AL — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the corpus YAML beside this
leaf (data/montgomery_al.yaml) and are re-bound to this REGISTRATION by the
registry derivation (US-429). US-424 onboarded Construction Permits
(All_Permit_viewlayer) and 311 Citizen Reports from the City of Montgomery's
ArcGIS Hub (services7.arcgis.com/xNUwUjOJqYE54USz).

Geographic basis: Montgomery is the state capital and seat of Montgomery
County, on the Alabama River. Downtown sits around (32.3792, -86.3077).
The metro bbox covers the city proper plus the Montgomery County urbanized
area (Pike Road, Prattville-adjacent east, and the Maxwell Air Force Base
southwest gateway).
"""

from src.spatial.registration import SpatialRegistration
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MONTGOMERY_AL_CITY_ID: str = "montgomery_al"

# Metro bbox covering the Montgomery, AL urbanized area (Montgomery County).
MONTGOMERY_AL_METRO_BBOX: dict[str, float] = {
    "min_lat": 32.18,
    "max_lat": 32.55,
    "min_lng": -86.52,
    "max_lng": -86.05,
}

# Registration-contract center: Montgomery City Hall / downtown vicinity.
MONTGOMERY_AL_CENTER: dict[str, float] = {"lat": 32.3792, "lng": -86.3077}

# Division bounding boxes (strict subsets of MONTGOMERY_AL_METRO_BBOX)
MONTGOMERY_AL_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    # Downtown, Capitol complex, and the historic Garden District
    "DOWNTOWN_CORE": {"min_lat": 32.35, "max_lat": 32.41, "min_lng": -86.33, "max_lng": -86.27},
    # East Montgomery / Eastchase commercial belt toward Pike Road
    "EAST_MONTGOMERY": {"min_lat": 32.34, "max_lat": 32.43, "min_lng": -86.22, "max_lng": -86.05},
    # West Montgomery / Maxwell Blvd and the industrial riverfront
    "WEST_MONTGOMERY": {"min_lat": 32.28, "max_lat": 32.40, "min_lng": -86.45, "max_lng": -86.33},
    # South Montgomery / South Blvd and the airport approaches
    "SOUTH_MONTGOMERY": {"min_lat": 32.20, "max_lat": 32.32, "min_lng": -86.38, "max_lng": -86.20},
    # North Montgomery / US-231 toward Prattville and the northern belts
    "NORTH_MONTGOMERY": {"min_lat": 32.40, "max_lat": 32.55, "min_lng": -86.36, "max_lng": -86.10},
}


def is_in_montgomery_al_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Montgomery, AL metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        MONTGOMERY_AL_METRO_BBOX["min_lat"] <= lat <= MONTGOMERY_AL_METRO_BBOX["max_lat"]
        and MONTGOMERY_AL_METRO_BBOX["min_lng"] <= lng <= MONTGOMERY_AL_METRO_BBOX["max_lng"]
    )


# Submarkets (coordinates must live inside their division boxes for interlock
# containment).
MONTGOMERY_AL_SUBMARKETS: dict[str, SubmarketMeta] = {
    # DOWNTOWN_CORE
    "Downtown Montgomery": SubmarketMeta(
        name="Downtown Montgomery",
        borough="DOWNTOWN_CORE",
        lat=32.3792,
        lng=-86.3077,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.80,
        capex=5400000.0,
        permit_vel=26.0,
        shift_ratio=1.32,
        sla=48.0,
        description="Capitol complex, historic downtown, and the riverfront mixed-use core.",
        city_id=MONTGOMERY_AL_CITY_ID,
    ),
    "Garden District": SubmarketMeta(
        name="Garden District",
        borough="DOWNTOWN_CORE",
        lat=32.3660,
        lng=-86.3060,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.77,
        capex=4600000.0,
        permit_vel=23.0,
        shift_ratio=1.27,
        sla=46.0,
        description="Historic residential district with steady rehabilitation and infill.",
        city_id=MONTGOMERY_AL_CITY_ID,
    ),
    # EAST_MONTGOMERY
    "Eastchase": SubmarketMeta(
        name="Eastchase",
        borough="EAST_MONTGOMERY",
        lat=32.3560,
        lng=-86.1850,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.78,
        capex=5100000.0,
        permit_vel=25.0,
        shift_ratio=1.30,
        sla=47.0,
        description="Eastchase retail and mixed-use hub anchoring east Montgomery growth.",
        city_id=MONTGOMERY_AL_CITY_ID,
    ),
    "Pike Road Corridor": SubmarketMeta(
        name="Pike Road Corridor",
        borough="EAST_MONTGOMERY",
        lat=32.3700,
        lng=-86.1000,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.72,
        capex=4200000.0,
        permit_vel=22.0,
        shift_ratio=1.24,
        sla=43.0,
        description="Eastern growth corridor toward Pike Road with residential expansion.",
        city_id=MONTGOMERY_AL_CITY_ID,
    ),
    # WEST_MONTGOMERY
    "Maxwell / West": SubmarketMeta(
        name="Maxwell / West",
        borough="WEST_MONTGOMERY",
        lat=32.3760,
        lng=-86.3640,
        zoom=13.8,
        pitch=42.0,
        base_lims=0.74,
        capex=4400000.0,
        permit_vel=21.0,
        shift_ratio=1.26,
        sla=44.0,
        description="Maxwell Air Force Base gateway and west Montgomery defense-adjacent belt.",
        city_id=MONTGOMERY_AL_CITY_ID,
    ),
    # SOUTH_MONTGOMERY
    "South Boulevard": SubmarketMeta(
        name="South Boulevard",
        borough="SOUTH_MONTGOMERY",
        lat=32.2950,
        lng=-86.2900,
        zoom=13.5,
        pitch=38.0,
        base_lims=0.70,
        capex=3600000.0,
        permit_vel=19.0,
        shift_ratio=1.22,
        sla=42.0,
        description="South Blvd corridor and south Montgomery residential reinvestment.",
        city_id=MONTGOMERY_AL_CITY_ID,
    ),
    # NORTH_MONTGOMERY
    "North Montgomery": SubmarketMeta(
        name="North Montgomery",
        borough="NORTH_MONTGOMERY",
        lat=32.4600,
        lng=-86.2900,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.73,
        capex=4000000.0,
        permit_vel=20.0,
        shift_ratio=1.23,
        sla=43.0,
        description="US-231 north corridor residential and commercial belts toward Prattville.",
        city_id=MONTGOMERY_AL_CITY_ID,
    ),
}


MONTGOMERY_AL_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=32.3790,
        center_lng=-86.3080,
        zoom=13.8,
        bbox=MONTGOMERY_AL_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in MONTGOMERY_AL_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id=MONTGOMERY_AL_CITY_ID,
    ),
    "EAST_MONTGOMERY": BoroughMeta(
        name="EAST_MONTGOMERY",
        center_lat=32.3600,
        center_lng=-86.1400,
        zoom=12.8,
        bbox=MONTGOMERY_AL_DIVISION_BBOXES["EAST_MONTGOMERY"],
        submarkets=[k for k, v in MONTGOMERY_AL_SUBMARKETS.items() if v.borough == "EAST_MONTGOMERY"],
        city_id=MONTGOMERY_AL_CITY_ID,
    ),
    "WEST_MONTGOMERY": BoroughMeta(
        name="WEST_MONTGOMERY",
        center_lat=32.3500,
        center_lng=-86.3900,
        zoom=12.8,
        bbox=MONTGOMERY_AL_DIVISION_BBOXES["WEST_MONTGOMERY"],
        submarkets=[k for k, v in MONTGOMERY_AL_SUBMARKETS.items() if v.borough == "WEST_MONTGOMERY"],
        city_id=MONTGOMERY_AL_CITY_ID,
    ),
    "SOUTH_MONTGOMERY": BoroughMeta(
        name="SOUTH_MONTGOMERY",
        center_lat=32.2600,
        center_lng=-86.3000,
        zoom=12.8,
        bbox=MONTGOMERY_AL_DIVISION_BBOXES["SOUTH_MONTGOMERY"],
        submarkets=[k for k, v in MONTGOMERY_AL_SUBMARKETS.items() if v.borough == "SOUTH_MONTGOMERY"],
        city_id=MONTGOMERY_AL_CITY_ID,
    ),
    "NORTH_MONTGOMERY": BoroughMeta(
        name="NORTH_MONTGOMERY",
        center_lat=32.4700,
        center_lng=-86.2300,
        zoom=12.5,
        bbox=MONTGOMERY_AL_DIVISION_BBOXES["NORTH_MONTGOMERY"],
        submarkets=[k for k, v in MONTGOMERY_AL_SUBMARKETS.items() if v.borough == "NORTH_MONTGOMERY"],
        city_id=MONTGOMERY_AL_CITY_ID,
    ),
}

REGISTRATION = SpatialRegistration(
    metro_bbox=MONTGOMERY_AL_METRO_BBOX,
    division_bboxes=MONTGOMERY_AL_DIVISION_BBOXES,
    submarkets=MONTGOMERY_AL_SUBMARKETS,
    divisions=MONTGOMERY_AL_DIVISIONS,
    contains=is_in_montgomery_al_metro,
)

__all__ = [
    "MONTGOMERY_AL_CENTER",
    "MONTGOMERY_AL_CITY_ID",
    "MONTGOMERY_AL_DIVISIONS",
    "MONTGOMERY_AL_DIVISION_BBOXES",
    "MONTGOMERY_AL_METRO_BBOX",
    "MONTGOMERY_AL_SUBMARKETS",
    "REGISTRATION",
    "is_in_montgomery_al_metro",
]
