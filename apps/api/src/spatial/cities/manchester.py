"""Manchester Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Manchester,
NH (Hillsborough County seat, the largest city in the state and the economic
hub of southern New Hampshire — deliberately not overlapping the sibling
Boston/Worcester leaf boxes).

Feeds: SLA reads the SNAP retailer slice (``snap_sla_spec``, New Hampshire
stores inside the metro box). The DEEDS feed registered until 2026-09-30 named
an ArcGIS Online organisation that does not exist, and no public sale source
exists: the assessor publishes through a per-property Vision site, NH GRANIT
parcels carry no sale fields, and the state's PA-34 sales go to municipalities
only. Permits and 311 remain unregistered.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MANCHESTER_CITY_ID: str = "manchester"

# Manchester metro bbox (city extent: SW ~42.93/-71.53, NE ~43.06/-71.40).
# The north edge approaches the Merrimack River, the west edge the Bedford
# line, the east edge the Hooksett line, and the south edge the Massabesic
# /Auburn line. Center is downtown Manchester near the Millyard.
MANCHESTER_METRO_BBOX: dict[str, float] = {
    "min_lat": 42.93,
    "max_lat": 43.06,
    "min_lng": -71.53,
    "max_lng": -71.40,
}

# Registration-contract center: downtown Manchester (Elm St CBD / Millyard).
MANCHESTER_CENTER: dict[str, float] = {"lat": 42.9956, "lng": -71.4548}

# 6 Manchester Division Bounding Boxes (strictly nested inside the metro bbox)
MANCHESTER_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_MILL":      {"min_lat": 42.975, "max_lat": 43.005, "min_lng": -71.475, "max_lng": -71.440},
    "WEST_SIDE":          {"min_lat": 42.985, "max_lat": 43.020, "min_lng": -71.510, "max_lng": -71.470},
    "NORTH_END":          {"min_lat": 43.000, "max_lat": 43.055, "min_lng": -71.490, "max_lng": -71.440},
    "SOUTH_COMMERCIAL":   {"min_lat": 42.935, "max_lat": 42.975, "min_lng": -71.470, "max_lng": -71.420},
    "EAST_INDUSTRIAL":    {"min_lat": 42.980, "max_lat": 43.010, "min_lng": -71.440, "max_lng": -71.400},
    "QUEENS_CITY":        {"min_lat": 42.940, "max_lat": 42.985, "min_lng": -71.500, "max_lng": -71.460},
}


def is_in_manchester_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Manchester metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        MANCHESTER_METRO_BBOX["min_lat"] <= lat <= MANCHESTER_METRO_BBOX["max_lat"]
        and MANCHESTER_METRO_BBOX["min_lng"] <= lng <= MANCHESTER_METRO_BBOX["max_lng"]
    )


def is_in_manchester(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_manchester_metro`."""
    return is_in_manchester_metro(lat, lng)


# ---------------------------------------------------------------------------
# Manchester Submarket Registry (8 Submarkets Across 6 Divisions)
# ---------------------------------------------------------------------------

MANCHESTER_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_MILL (2 Submarkets)
    # =======================================================================
    "Center City": SubmarketMeta(
        name="Center City",
        borough="DOWNTOWN_MILL",
        lat=42.9900,
        lng=-71.4620,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.85,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The Elm Street CBD and Millyard district: office-to-residential conversions, the SNHU/UNH extension anchors, and the city's densest mixed-use pipeline around the Merrimack.",
        city_id="manchester",
    ),
    "Millyard": SubmarketMeta(
        name="Millyard",
        borough="DOWNTOWN_MILL",
        lat=42.9880,
        lng=-71.4650,
        zoom=15.0,
        pitch=42.0,
        base_lims=0.81,
        capex=4000000.0,
        permit_vel=22.0,
        shift_ratio=1.34,
        sla=44.0,
        description="The historic Amoskeag Millyard along the river with loft conversions, brewery-retail, and steady restoration trades in the brick-mill stock.",
        city_id="manchester",
    ),
    # =======================================================================
    # WEST_SIDE (2 Submarkets)
    # =======================================================================
    "West End": SubmarketMeta(
        name="West End",
        borough="WEST_SIDE",
        lat=43.0000,
        lng=-71.4900,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.83,
        capex=4900000.0,
        permit_vel=29.0,
        shift_ratio=1.41,
        sla=53.0,
        description="The West Side grid west of the river with pre-war housing stock, the Striar West village mixed-use corridor, and investor renovation flow.",
        city_id="manchester",
    ),
    "Rimmon Heights": SubmarketMeta(
        name="Rimmon Heights",
        borough="WEST_SIDE",
        lat=42.9920,
        lng=-71.4950,
        zoom=14.0,
        pitch=38.0,
        base_lims=0.79,
        capex=3700000.0,
        permit_vel=21.0,
        shift_ratio=1.30,
        sla=42.0,
        description="The Rimmon Heights / Notre Dame neighborhood south of Bridge St with dense two-and-three-family stock and block-by-block reinvestment.",
        city_id="manchester",
    ),
    # =======================================================================
    # NORTH_END (1 Submarket)
    # =======================================================================
    "North End": SubmarketMeta(
        name="North End",
        borough="NORTH_END",
        lat=43.0300,
        lng=-71.4700,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.72,
        capex=3300000.0,
        permit_vel=20.0,
        shift_ratio=1.25,
        sla=41.0,
        description="The North End along the Merrimack and the riverfront redevelopment parcels north of downtown with steady infill and hospitality licensing.",
        city_id="manchester",
    ),
    # =======================================================================
    # SOUTH_COMMERCIAL (1 Submarket)
    # =======================================================================
    "South Willow": SubmarketMeta(
        name="South Willow",
        borough="SOUTH_COMMERCIAL",
        lat=42.9550,
        lng=-71.4400,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.70,
        capex=3100000.0,
        permit_vel=19.0,
        shift_ratio=1.23,
        sla=39.0,
        description="The South Willow Street commercial corridor and Mall of New Hampshire retail district with hotel/hospitality turnover and redevelopment pressure.",
        city_id="manchester",
    ),
    # =======================================================================
    # EAST_INDUSTRIAL (1 Submarket)
    # =======================================================================
    "Brown Ave": SubmarketMeta(
        name="Brown Ave",
        borough="EAST_INDUSTRIAL",
        lat=42.9950,
        lng=-71.4200,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.68,
        capex=2900000.0,
        permit_vel=17.0,
        shift_ratio=1.20,
        sla=37.0,
        description="The Brown Avenue / Queen City Avenue east side with light industrial, airport-adjacent parcels, and the city's lowest sale prices meeting conversion flow.",
        city_id="manchester",
    ),
    # =======================================================================
    # QUEENS_CITY (1 Submarket)
    # =======================================================================
    "Queen City": SubmarketMeta(
        name="Queen City",
        borough="QUEENS_CITY",
        lat=42.9600,
        lng=-71.4800,
        zoom=14.0,
        pitch=33.0,
        base_lims=0.71,
        capex=3200000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=40.0,
        description="The Piscataquog / Queen City Avenue southwest village with craftsman-bungalow stock, a deep rental register, and steady reinvestment.",
        city_id="manchester",
    ),
}


# ---------------------------------------------------------------------------
# Manchester Divisions Catalog
# ---------------------------------------------------------------------------

MANCHESTER_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_MILL": BoroughMeta(
        name="DOWNTOWN_MILL",
        center_lat=42.9890,
        center_lng=-71.4635,
        zoom=13.5,
        bbox=MANCHESTER_DIVISION_BBOXES["DOWNTOWN_MILL"],
        submarkets=[k for k, v in MANCHESTER_SUBMARKETS.items() if v.borough == "DOWNTOWN_MILL"],
        city_id="manchester",
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=42.9960,
        center_lng=-71.4925,
        zoom=13.5,
        bbox=MANCHESTER_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in MANCHESTER_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id="manchester",
    ),
    "NORTH_END": BoroughMeta(
        name="NORTH_END",
        center_lat=43.0300,
        center_lng=-71.4700,
        zoom=13.0,
        bbox=MANCHESTER_DIVISION_BBOXES["NORTH_END"],
        submarkets=[k for k, v in MANCHESTER_SUBMARKETS.items() if v.borough == "NORTH_END"],
        city_id="manchester",
    ),
    "SOUTH_COMMERCIAL": BoroughMeta(
        name="SOUTH_COMMERCIAL",
        center_lat=42.9550,
        center_lng=-71.4400,
        zoom=13.0,
        bbox=MANCHESTER_DIVISION_BBOXES["SOUTH_COMMERCIAL"],
        submarkets=[k for k, v in MANCHESTER_SUBMARKETS.items() if v.borough == "SOUTH_COMMERCIAL"],
        city_id="manchester",
    ),
    "EAST_INDUSTRIAL": BoroughMeta(
        name="EAST_INDUSTRIAL",
        center_lat=42.9950,
        center_lng=-71.4200,
        zoom=13.0,
        bbox=MANCHESTER_DIVISION_BBOXES["EAST_INDUSTRIAL"],
        submarkets=[k for k, v in MANCHESTER_SUBMARKETS.items() if v.borough == "EAST_INDUSTRIAL"],
        city_id="manchester",
    ),
    "QUEENS_CITY": BoroughMeta(
        name="QUEENS_CITY",
        center_lat=42.9600,
        center_lng=-71.4800,
        zoom=13.0,
        bbox=MANCHESTER_DIVISION_BBOXES["QUEENS_CITY"],
        submarkets=[k for k, v in MANCHESTER_SUBMARKETS.items() if v.borough == "QUEENS_CITY"],
        city_id="manchester",
    ),
}

MHT_DIVISION_BBOXES = MANCHESTER_DIVISION_BBOXES
MHT_SUBMARKETS = MANCHESTER_SUBMARKETS
MHT_DIVISIONS = MANCHESTER_DIVISIONS


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=MANCHESTER_METRO_BBOX,
    division_bboxes=MANCHESTER_DIVISION_BBOXES,
    submarkets=MANCHESTER_SUBMARKETS,
    divisions=MANCHESTER_DIVISIONS,
    contains=is_in_manchester_metro,
)

__all__ = [
    "MANCHESTER_CENTER",
    "MANCHESTER_CITY_ID",
    "MANCHESTER_DIVISIONS",
    "MANCHESTER_DIVISION_BBOXES",
    "MANCHESTER_METRO_BBOX",
    "MANCHESTER_SUBMARKETS",
    "MHT_DIVISIONS",
    "MHT_DIVISION_BBOXES",
    "MHT_SUBMARKETS",
    "REGISTRATION",
    "is_in_manchester",
    "is_in_manchester_metro",
]
