"""Harrisburg Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Harrisburg,
PA (the state capital, on the Susquehanna River in Dauphin County — the
sibling Lancaster/York leaf boxes sit east/southeast and must stay clear of
this box).

Feeds: SLA reads the SNAP retailer slice (``snap_sla_spec``, Pennsylvania
stores inside the metro box). The DEEDS feed registered until 2026-09-30 named
a service the city website never hosted, and no public sale source exists: the
city's tax-parcel snapshots carry a purchase date frozen at 2022-12-30 and no
price, Dauphin County's open tables carry only a recorder document number, and
the county's sales search has no export or API. Permits and 311 remain
unregistered.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

HARRISBURG_CITY_ID: str = "harrisburg"

# City-parcel bbox around the Harrisburg metro (center 40.2732/-76.8867): SW
# approx 40.22/-76.94, NE approx 40.32/-76.83. The west edge is the
# Susquehanna River; the east edge the Blue Mountain foothills. Lancaster and
# York sit outside this box and must stay out.
HARRISBURG_METRO_BBOX: dict[str, float] = {
    "min_lat": 40.22,
    "max_lat": 40.32,
    "min_lng": -76.94,
    "max_lng": -76.83,
}

# Registration-contract center: downtown Harrisburg (State Capitol area).
HARRISBURG_CENTER: dict[str, float] = {"lat": 40.2732, "lng": -76.8867}

# 6 Harrisburg Division Bounding Boxes (strictly nested inside the metro bbox)
HARRISBURG_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_CAPITOL":  {"min_lat": 40.255, "max_lat": 40.290, "min_lng": -76.905, "max_lng": -76.875},
    "RIVERFRONT_EAST":   {"min_lat": 40.250, "max_lat": 40.285, "min_lng": -76.890, "max_lng": -76.855},
    "NORTH_SUSQUEHANNA": {"min_lat": 40.290, "max_lat": 40.320, "min_lng": -76.900, "max_lng": -76.860},
    "SOUTH_SIDE":        {"min_lat": 40.220, "max_lat": 40.255, "min_lng": -76.900, "max_lng": -76.860},
    "EAST_SHORE":        {"min_lat": 40.240, "max_lat": 40.280, "min_lng": -76.870, "max_lng": -76.835},
    "WEST_ENOLA":        {"min_lat": 40.240, "max_lat": 40.275, "min_lng": -76.938, "max_lng": -76.905},
}


def is_in_harrisburg_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Harrisburg metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        HARRISBURG_METRO_BBOX["min_lat"] <= lat <= HARRISBURG_METRO_BBOX["max_lat"]
        and HARRISBURG_METRO_BBOX["min_lng"] <= lng <= HARRISBURG_METRO_BBOX["max_lng"]
    )


def is_in_harrisburg(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_harrisburg_metro`."""
    return is_in_harrisburg_metro(lat, lng)


# ---------------------------------------------------------------------------
# Harrisburg Submarket Registry (7 Submarkets Across 6 Divisions)
# ---------------------------------------------------------------------------

HARRISBURG_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CAPITOL (1 Submarket)
    # =======================================================================
    "Capitol District": SubmarketMeta(
        name="Capitol District",
        borough="DOWNTOWN_CAPITOL",
        lat=40.2650,
        lng=-76.8850,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.85,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The State Capitol complex and downtown office core with adaptive-reuse conversions and the densest mixed-use pipeline in the metro.",
        city_id="harrisburg",
    ),
    # =======================================================================
    # RIVERFRONT_EAST (1 Submarket)
    # =======================================================================
    "Riverfront East": SubmarketMeta(
        name="Riverfront East",
        borough="RIVERFRONT_EAST",
        lat=40.2620,
        lng=-76.8750,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.82,
        capex=4400000.0,
        permit_vel=26.0,
        shift_ratio=1.36,
        sla=48.0,
        description="The Susquehanna riverfront east of downtown with marina-adjacent hospitality licensing and steady townhome reinvestment.",
        city_id="harrisburg",
    ),
    # =======================================================================
    # NORTH_SUSQUEHANNA (1 Submarket)
    # =======================================================================
    "Uptown Harrisburg": SubmarketMeta(
        name="Uptown Harrisburg",
        borough="NORTH_SUSQUEHANNA",
        lat=40.2980,
        lng=-76.8850,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.74,
        capex=3500000.0,
        permit_vel=22.0,
        shift_ratio=1.28,
        sla=42.0,
        description="The north-central grid above the Capitol with pre-war housing stock and investor renovation flow along the Susquehanna bluff.",
        city_id="harrisburg",
    ),
    # =======================================================================
    # SOUTH_SIDE (1 Submarket)
    # =======================================================================
    "South Harrisburg": SubmarketMeta(
        name="South Harrisburg",
        borough="SOUTH_SIDE",
        lat=40.2350,
        lng=-76.8800,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.70,
        capex=3100000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=40.0,
        description="The South Side ward south of the Capitol with craftsman-bungalow stock, a deep rental register, and block-by-block reinvestment.",
        city_id="harrisburg",
    ),
    # =======================================================================
    # EAST_SHORE (2 Submarkets)
    # =======================================================================
    "Allison Hill": SubmarketMeta(
        name="Allison Hill",
        borough="EAST_SHORE",
        lat=40.2580,
        lng=-76.8550,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.68,
        capex=2900000.0,
        permit_vel=18.0,
        shift_ratio=1.22,
        sla=38.0,
        description="The East Shore hill neighborhood with the metro's most active block-level acquisition and the heaviest vacancy-to-rehab conversion flow.",
        city_id="harrisburg",
    ),
    "Bellevue Park": SubmarketMeta(
        name="Bellevue Park",
        borough="EAST_SHORE",
        lat=40.2680,
        lng=-76.8480,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.72,
        capex=3300000.0,
        permit_vel=21.0,
        shift_ratio=1.26,
        sla=41.0,
        description="The eastern garden-suburb grid off Paxton Street with solid early-20th-century stock and steady owner-occupier demand.",
        city_id="harrisburg",
    ),
    # =======================================================================
    # WEST_ENOLA (1 Submarket)
    # =======================================================================
    "West Shore Enola": SubmarketMeta(
        name="West Shore Enola",
        borough="WEST_ENOLA",
        lat=40.2580,
        lng=-76.9250,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.66,
        capex=2700000.0,
        permit_vel=16.0,
        shift_ratio=1.18,
        sla=34.0,
        description="The Cumberland County shore across the river at Enola with commuter-served suburban turnover and rail-adjacent redevelopment.",
        city_id="harrisburg",
    ),
}


# ---------------------------------------------------------------------------
# Harrisburg Divisions Catalog
# ---------------------------------------------------------------------------

HARRISBURG_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_CAPITOL": BoroughMeta(
        name="DOWNTOWN_CAPITOL",
        center_lat=40.2650,
        center_lng=-76.8850,
        zoom=13.5,
        bbox=HARRISBURG_DIVISION_BBOXES["DOWNTOWN_CAPITOL"],
        submarkets=[k for k, v in HARRISBURG_SUBMARKETS.items() if v.borough == "DOWNTOWN_CAPITOL"],
        city_id="harrisburg",
    ),
    "RIVERFRONT_EAST": BoroughMeta(
        name="RIVERFRONT_EAST",
        center_lat=40.2620,
        center_lng=-76.8750,
        zoom=13.5,
        bbox=HARRISBURG_DIVISION_BBOXES["RIVERFRONT_EAST"],
        submarkets=[k for k, v in HARRISBURG_SUBMARKETS.items() if v.borough == "RIVERFRONT_EAST"],
        city_id="harrisburg",
    ),
    "NORTH_SUSQUEHANNA": BoroughMeta(
        name="NORTH_SUSQUEHANNA",
        center_lat=40.2980,
        center_lng=-76.8850,
        zoom=13.0,
        bbox=HARRISBURG_DIVISION_BBOXES["NORTH_SUSQUEHANNA"],
        submarkets=[k for k, v in HARRISBURG_SUBMARKETS.items() if v.borough == "NORTH_SUSQUEHANNA"],
        city_id="harrisburg",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=40.2350,
        center_lng=-76.8800,
        zoom=13.0,
        bbox=HARRISBURG_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in HARRISBURG_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="harrisburg",
    ),
    "EAST_SHORE": BoroughMeta(
        name="EAST_SHORE",
        center_lat=40.2630,
        center_lng=-76.8520,
        zoom=13.0,
        bbox=HARRISBURG_DIVISION_BBOXES["EAST_SHORE"],
        submarkets=[k for k, v in HARRISBURG_SUBMARKETS.items() if v.borough == "EAST_SHORE"],
        city_id="harrisburg",
    ),
    "WEST_ENOLA": BoroughMeta(
        name="WEST_ENOLA",
        center_lat=40.2580,
        center_lng=-76.9250,
        zoom=13.0,
        bbox=HARRISBURG_DIVISION_BBOXES["WEST_ENOLA"],
        submarkets=[k for k, v in HARRISBURG_SUBMARKETS.items() if v.borough == "WEST_ENOLA"],
        city_id="harrisburg",
    ),
}

HBG_DIVISION_BBOXES = HARRISBURG_DIVISION_BBOXES
HBG_SUBMARKETS = HARRISBURG_SUBMARKETS
HBG_DIVISIONS = HARRISBURG_DIVISIONS


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=HARRISBURG_METRO_BBOX,
    division_bboxes=HARRISBURG_DIVISION_BBOXES,
    submarkets=HARRISBURG_SUBMARKETS,
    divisions=HARRISBURG_DIVISIONS,
    contains=is_in_harrisburg_metro,
)

__all__ = [
    "HARRISBURG_CENTER",
    "HARRISBURG_CITY_ID",
    "HARRISBURG_DIVISIONS",
    "HARRISBURG_DIVISION_BBOXES",
    "HARRISBURG_METRO_BBOX",
    "HARRISBURG_SUBMARKETS",
    "HBG_DIVISIONS",
    "HBG_DIVISION_BBOXES",
    "HBG_SUBMARKETS",
    "REGISTRATION",
    "is_in_harrisburg",
    "is_in_harrisburg_metro",
]
