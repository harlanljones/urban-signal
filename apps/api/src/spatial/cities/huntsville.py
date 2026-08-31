"""Huntsville, AL — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry).

Geographic basis: Huntsville is the seat of Madison County (AL). The metro
bbox covers the city proper plus the surrounding Madison County urbanized area
west to Limestone County's Madison, south toward Redstone Arsenal, and east
along US-72. Downtown sits around (34.7301, -86.5863).
"""


from src.spatial.registration import SpatialRegistration
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

HUNTSVILLE_CITY_ID: str = "huntsville"

# Generous box containing the Huntsville urbanized area (Madison County seat +
# Madison, Redstone Arsenal, the US-72 corridor).
HUNTSVILLE_METRO_BBOX: dict[str, float] = {
    "min_lat": 34.42,
    "max_lat": 34.82,
    "min_lng": -86.78,
    "max_lng": -86.28,
}

# Registration-contract center: Huntsville City Hall / downtown vicinity.
HUNTSVILLE_CENTER: dict[str, float] = {"lat": 34.7301, "lng": -86.5863}

# Division bounding boxes (strict subsets of HUNTSVILLE_METRO_BBOX)
HUNTSVILLE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    # Downtown, MidCity, and the historic neighborhoods along Governors Dr / Memorial Pkwy
    "CENTRAL_CORE": {"min_lat": 34.68, "max_lat": 34.78, "min_lng": -86.62, "max_lng": -86.52},
    # West Huntsville / University Dr / Research Park Blvd tech corridor
    "WEST_HUNTSVILLE": {"min_lat": 34.64, "max_lat": 34.74, "min_lng": -86.72, "max_lng": -86.62},
    # South Huntsville / Whitesburg Dr toward Redstone Arsenal gateways
    "SOUTH_HUNTSVILLE": {"min_lat": 34.54, "max_lat": 34.64, "min_lng": -86.64, "max_lng": -86.50},
    # Northeast / US-72 corridor, airport, and residential growth belts
    "NORTHEAST": {"min_lat": 34.72, "max_lat": 34.82, "min_lng": -86.44, "max_lng": -86.28},
    # North / Meridianville-Hazel Green residential belts toward Limestone County
    "NORTH_MADISON": {"min_lat": 34.76, "max_lat": 34.82, "min_lng": -86.70, "max_lng": -86.44},
}


def is_in_huntsville_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Huntsville metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        HUNTSVILLE_METRO_BBOX["min_lat"] <= lat <= HUNTSVILLE_METRO_BBOX["max_lat"]
        and HUNTSVILLE_METRO_BBOX["min_lng"] <= lng <= HUNTSVILLE_METRO_BBOX["max_lng"]
    )


# Submarkets (minimal viable set across divisions; coordinates must live inside
# their division boxes for interlock containment).
HUNTSVILLE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown Huntsville": SubmarketMeta(
        name="Downtown Huntsville",
        borough="CENTRAL_CORE",
        lat=34.7301,
        lng=-86.5863,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.83,
        capex=7200000.0,
        permit_vel=38.0,
        shift_ratio=1.42,
        sla=52.0,
        description="Historic downtown core with courthouse, Clinton Row, and the Von Braun Center.",
        city_id=HUNTSVILLE_CITY_ID,
    ),
    "MidCity District": SubmarketMeta(
        name="MidCity District",
        borough="CENTRAL_CORE",
        lat=34.7310,
        lng=-86.5520,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.82,
        capex=6800000.0,
        permit_vel=36.0,
        shift_ratio=1.40,
        sla=50.0,
        description="MidCity mixed-use redevelopment at the old Madison Square Mall site (Memorial Pkwy).",
        city_id=HUNTSVILLE_CITY_ID,
    ),
    "Governors Drive / Medical": SubmarketMeta(
        name="Governors Drive / Medical",
        borough="CENTRAL_CORE",
        lat=34.7240,
        lng=-86.5850,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.79,
        capex=6000000.0,
        permit_vel=32.0,
        shift_ratio=1.35,
        sla=48.0,
        description="Governors Dr commercial spine between downtown and the hospital district.",
        city_id=HUNTSVILLE_CITY_ID,
    ),
    # WEST_HUNTSVILLE
    "University Drive Corridor": SubmarketMeta(
        name="University Drive Corridor",
        borough="WEST_HUNTSVILLE",
        lat=34.6980,
        lng=-86.6600,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=34.0,
        shift_ratio=1.38,
        sla=49.0,
        description="University Dr retail and multifamily corridor connecting to Research Park.",
        city_id=HUNTSVILLE_CITY_ID,
    ),
    "Research Park / West": SubmarketMeta(
        name="Research Park / West",
        borough="WEST_HUNTSVILLE",
        lat=34.6680,
        lng=-86.6600,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.81,
        capex=6500000.0,
        permit_vel=35.0,
        shift_ratio=1.39,
        sla=50.0,
        description="Cummings Research Park tech campus and west Huntsville employment core.",
        city_id=HUNTSVILLE_CITY_ID,
    ),
    # SOUTH_HUNTSVILLE
    "South Huntsville / Whitesburg": SubmarketMeta(
        name="South Huntsville / Whitesburg",
        borough="SOUTH_HUNTSVILLE",
        lat=34.5950,
        lng=-86.5650,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=29.0,
        shift_ratio=1.30,
        sla=46.0,
        description="Whitesburg Dr / Carl T Jones residential and commercial belts south of downtown.",
        city_id=HUNTSVILLE_CITY_ID,
    ),
    "Redstone Gateway / South": SubmarketMeta(
        name="Redstone Gateway / South",
        borough="SOUTH_HUNTSVILLE",
        lat=34.5750,
        lng=-86.5650,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.77,
        capex=5700000.0,
        permit_vel=30.0,
        shift_ratio=1.31,
        sla=46.0,
        description="Redstone Gateway commercial park and defense-adjacent growth near the Arsenal gates.",
        city_id=HUNTSVILLE_CITY_ID,
    ),
    # NORTHEAST
    "US-72 / Airport Corridor": SubmarketMeta(
        name="US-72 / Airport Corridor",
        borough="NORTHEAST",
        lat=34.7450,
        lng=-86.4100,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.74,
        capex=5100000.0,
        permit_vel=28.0,
        shift_ratio=1.28,
        sla=45.0,
        description="US-72 east commercial corridor and Huntsville International Airport adjacency.",
        city_id=HUNTSVILLE_CITY_ID,
    ),
    "East Huntsville": SubmarketMeta(
        name="East Huntsville",
        borough="NORTHEAST",
        lat=34.7350,
        lng=-86.4700,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.72,
        capex=4800000.0,
        permit_vel=27.0,
        shift_ratio=1.26,
        sla=44.0,
        description="East Huntsville residential growth belts along the Chapman Mountain approach.",
        city_id=HUNTSVILLE_CITY_ID,
    ),
    # NORTH_MADISON
    "Meridianville / Hazel Green": SubmarketMeta(
        name="Meridianville / Hazel Green",
        borough="NORTH_MADISON",
        lat=34.7900,
        lng=-86.5700,
        zoom=12.5,
        pitch=36.0,
        base_lims=0.70,
        capex=4400000.0,
        permit_vel=26.0,
        shift_ratio=1.24,
        sla=42.0,
        description="North Madison County bedroom communities and US-231 growth corridors.",
        city_id=HUNTSVILLE_CITY_ID,
    ),
}


HUNTSVILLE_DIVISIONS: dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=34.730,
        center_lng=-86.570,
        zoom=13.2,
        bbox=HUNTSVILLE_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in HUNTSVILLE_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=HUNTSVILLE_CITY_ID,
    ),
    "WEST_HUNTSVILLE": BoroughMeta(
        name="WEST_HUNTSVILLE",
        center_lat=34.690,
        center_lng=-86.670,
        zoom=12.8,
        bbox=HUNTSVILLE_DIVISION_BBOXES["WEST_HUNTSVILLE"],
        submarkets=[k for k, v in HUNTSVILLE_SUBMARKETS.items() if v.borough == "WEST_HUNTSVILLE"],
        city_id=HUNTSVILLE_CITY_ID,
    ),
    "SOUTH_HUNTSVILLE": BoroughMeta(
        name="SOUTH_HUNTSVILLE",
        center_lat=34.590,
        center_lng=-86.570,
        zoom=12.8,
        bbox=HUNTSVILLE_DIVISION_BBOXES["SOUTH_HUNTSVILLE"],
        submarkets=[k for k, v in HUNTSVILLE_SUBMARKETS.items() if v.borough == "SOUTH_HUNTSVILLE"],
        city_id=HUNTSVILLE_CITY_ID,
    ),
    "NORTHEAST": BoroughMeta(
        name="NORTHEAST",
        center_lat=34.760,
        center_lng=-86.400,
        zoom=12.5,
        bbox=HUNTSVILLE_DIVISION_BBOXES["NORTHEAST"],
        submarkets=[k for k, v in HUNTSVILLE_SUBMARKETS.items() if v.borough == "NORTHEAST"],
        city_id=HUNTSVILLE_CITY_ID,
    ),
    "NORTH_MADISON": BoroughMeta(
        name="NORTH_MADISON",
        center_lat=34.790,
        center_lng=-86.570,
        zoom=12.2,
        bbox=HUNTSVILLE_DIVISION_BBOXES["NORTH_MADISON"],
        submarkets=[k for k, v in HUNTSVILLE_SUBMARKETS.items() if v.borough == "NORTH_MADISON"],
        city_id=HUNTSVILLE_CITY_ID,
    ),
}

HUNTSVILLE_DIVISION_BBOXES_EXPORT = HUNTSVILLE_DIVISION_BBOXES
HUNTSVILLE_SUBMARKETS_EXPORT = HUNTSVILLE_SUBMARKETS
HUNTSVILLE_DIVISIONS_EXPORT = HUNTSVILLE_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=HUNTSVILLE_METRO_BBOX,
    division_bboxes=HUNTSVILLE_DIVISION_BBOXES,
    submarkets=HUNTSVILLE_SUBMARKETS,
    divisions=HUNTSVILLE_DIVISIONS,
    contains=is_in_huntsville_metro,
)

__all__ = [
    "HUNTSVILLE_CENTER",
    "HUNTSVILLE_CITY_ID",
    "HUNTSVILLE_DIVISIONS",
    "HUNTSVILLE_DIVISIONS_EXPORT",
    "HUNTSVILLE_DIVISION_BBOXES",
    "HUNTSVILLE_DIVISION_BBOXES_EXPORT",
    "HUNTSVILLE_METRO_BBOX",
    "HUNTSVILLE_SUBMARKETS",
    "HUNTSVILLE_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_huntsville_metro",
]
