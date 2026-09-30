"""Huntington, WV Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Huntington,
WV (Cabell County seat on the Ohio River — deliberately not overlapping the
sibling Charleston/Huntington-corridor leaf boxes).

Feeds: SLA reads the SNAP retailer slice (``snap_sla_spec``, West Virginia
stores inside the metro box). The DEEDS feed registered until 2026-09-30 named
a service huntingtonwv.gov never hosted, and no public sale source exists:
Cabell County's parcel layer and the WV GIS Technical Center parcel tables
carry deed book and page but no sale date or price (Kanawha County, which feeds
Charleston, is the exception in this corridor). Permits and 311 remain
unregistered.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

HUNTINGTON_WV_CITY_ID: str = "huntington_wv"

# Huntington metro bbox around the downtown core (lat 38.4192, lng -82.4454).
HUNTINGTON_WV_METRO_BBOX: dict[str, float] = {
    "min_lat": 38.35,
    "max_lat": 38.49,
    "min_lng": -82.55,
    "max_lng": -82.36,
}

# Registration-contract center: downtown Huntington (8th St / 4th Ave core).
HUNTINGTON_WV_CENTER: dict[str, float] = {"lat": 38.4192, "lng": -82.4454}

# 5 Huntington Division Bounding Boxes (strictly nested inside the metro bbox)
HUNTINGTON_WV_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_RIVERFRONT": {"min_lat": 38.40, "max_lat": 38.44, "min_lng": -82.46, "max_lng": -82.43},
    "HIGHLAND_PARK":       {"min_lat": 38.44, "max_lat": 38.48, "min_lng": -82.46, "max_lng": -82.42},
    "SOUTH_SIDE":          {"min_lat": 38.35, "max_lat": 38.40, "min_lng": -82.50, "max_lng": -82.44},
    "EAST_HUNTINGTON":     {"min_lat": 38.40, "max_lat": 38.46, "min_lng": -82.43, "max_lng": -82.40},
    "WEST_END":            {"min_lat": 38.37, "max_lat": 38.43, "min_lng": -82.55, "max_lng": -82.48},
}


def is_in_huntington_wv_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Huntington metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        HUNTINGTON_WV_METRO_BBOX["min_lat"] <= lat <= HUNTINGTON_WV_METRO_BBOX["max_lat"]
        and HUNTINGTON_WV_METRO_BBOX["min_lng"] <= lng <= HUNTINGTON_WV_METRO_BBOX["max_lng"]
    )


def is_in_huntington_wv(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_huntington_wv_metro`."""
    return is_in_huntington_wv_metro(lat, lng)


# ---------------------------------------------------------------------------
# Huntington Submarket Registry (7 Submarkets Across 5 Divisions)
# ---------------------------------------------------------------------------

HUNTINGTON_WV_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_RIVERFRONT (2 Submarkets)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN_RIVERFRONT",
        lat=38.4200,
        lng=-82.4450,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.85,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The 9th Street civic core and Ohio River riverfront with mixed-use conversions, the Marshall University edge, and the city's densest downtown pipeline.",
        city_id="huntington_wv",
    ),
    "Riverfront": SubmarketMeta(
        name="Riverfront",
        borough="DOWNTOWN_RIVERFRONT",
        lat=38.4130,
        lng=-82.4480,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.81,
        capex=4100000.0,
        permit_vel=23.0,
        shift_ratio=1.34,
        sla=45.0,
        description="The Harris Riverfront Park and Pullman Square district with hospitality licensing, festival-trade retail, and riverfront redevelopment.",
        city_id="huntington_wv",
    ),
    # =======================================================================
    # HIGHLAND_PARK (2 Submarkets)
    # =======================================================================
    "Highland Park": SubmarketMeta(
        name="Highland Park",
        borough="HIGHLAND_PARK",
        lat=38.4580,
        lng=-82.4450,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.79,
        capex=3800000.0,
        permit_vel=27.0,
        shift_ratio=1.38,
        sla=50.0,
        description="The Hal Greer corridor and historic residential grid around the namesake park with steady renovation trades and student-adjacent rental stock.",
        city_id="huntington_wv",
    ),
    "Ritter Park": SubmarketMeta(
        name="Ritter Park",
        borough="HIGHLAND_PARK",
        lat=38.4450,
        lng=-82.4350,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.82,
        capex=4400000.0,
        permit_vel=29.0,
        shift_ratio=1.40,
        sla=52.0,
        description="The Ritter Park / 5th Avenue estate district with high-value pre-war housing stock and investor restoration flow.",
        city_id="huntington_wv",
    ),
    # =======================================================================
    # SOUTH_SIDE (1 Submarket)
    # =======================================================================
    "Southside": SubmarketMeta(
        name="Southside",
        borough="SOUTH_SIDE",
        lat=38.3750,
        lng=-82.4700,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.70,
        capex=3100000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=40.0,
        description="The South Side / 29th Street ward across the 4th Avenue viaduct with craftsman-bungalow stock, a deep rental register, and block-by-block reinvestment.",
        city_id="huntington_wv",
    ),
    # =======================================================================
    # EAST_HUNTINGTON (1 Submarket)
    # =======================================================================
    "East End": SubmarketMeta(
        name="East End",
        borough="EAST_HUNTINGTON",
        lat=38.4250,
        lng=-82.4150,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.73,
        capex=3500000.0,
        permit_vel=22.0,
        shift_ratio=1.28,
        sla=43.0,
        description="The east-bank neighborhoods along the 31st Street bridge approach with solid mid-century housing and vacancy-to-acquisition conversion flow.",
        city_id="huntington_wv",
    ),
    # =======================================================================
    # WEST_END (1 Submarket)
    # =======================================================================
    "West End": SubmarketMeta(
        name="West End",
        borough="WEST_END",
        lat=38.4000,
        lng=-82.5150,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.66,
        capex=2700000.0,
        permit_vel=16.0,
        shift_ratio=1.18,
        sla=34.0,
        description="The West End / Guyandotte fringe along US-60 with the city's lowest sale prices and the heaviest acquisition-conversion flow.",
        city_id="huntington_wv",
    ),
}


# ---------------------------------------------------------------------------
# Huntington Divisions Catalog
# ---------------------------------------------------------------------------

HUNTINGTON_WV_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_RIVERFRONT": BoroughMeta(
        name="DOWNTOWN_RIVERFRONT",
        center_lat=38.4165,
        center_lng=-82.4450,
        zoom=13.5,
        bbox=HUNTINGTON_WV_DIVISION_BBOXES["DOWNTOWN_RIVERFRONT"],
        submarkets=[k for k, v in HUNTINGTON_WV_SUBMARKETS.items() if v.borough == "DOWNTOWN_RIVERFRONT"],
        city_id="huntington_wv",
    ),
    "HIGHLAND_PARK": BoroughMeta(
        name="HIGHLAND_PARK",
        center_lat=38.4515,
        center_lng=-82.4425,
        zoom=13.0,
        bbox=HUNTINGTON_WV_DIVISION_BBOXES["HIGHLAND_PARK"],
        submarkets=[k for k, v in HUNTINGTON_WV_SUBMARKETS.items() if v.borough == "HIGHLAND_PARK"],
        city_id="huntington_wv",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=38.3750,
        center_lng=-82.4700,
        zoom=13.0,
        bbox=HUNTINGTON_WV_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in HUNTINGTON_WV_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="huntington_wv",
    ),
    "EAST_HUNTINGTON": BoroughMeta(
        name="EAST_HUNTINGTON",
        center_lat=38.4300,
        center_lng=-82.4150,
        zoom=13.0,
        bbox=HUNTINGTON_WV_DIVISION_BBOXES["EAST_HUNTINGTON"],
        submarkets=[k for k, v in HUNTINGTON_WV_SUBMARKETS.items() if v.borough == "EAST_HUNTINGTON"],
        city_id="huntington_wv",
    ),
    "WEST_END": BoroughMeta(
        name="WEST_END",
        center_lat=38.4000,
        center_lng=-82.5150,
        zoom=13.0,
        bbox=HUNTINGTON_WV_DIVISION_BBOXES["WEST_END"],
        submarkets=[k for k, v in HUNTINGTON_WV_SUBMARKETS.items() if v.borough == "WEST_END"],
        city_id="huntington_wv",
    ),
}

HNT_DIVISION_BBOXES = HUNTINGTON_WV_DIVISION_BBOXES
HNT_SUBMARKETS = HUNTINGTON_WV_SUBMARKETS
HNT_DIVISIONS = HUNTINGTON_WV_DIVISIONS


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=HUNTINGTON_WV_METRO_BBOX,
    division_bboxes=HUNTINGTON_WV_DIVISION_BBOXES,
    submarkets=HUNTINGTON_WV_SUBMARKETS,
    divisions=HUNTINGTON_WV_DIVISIONS,
    contains=is_in_huntington_wv_metro,
)

__all__ = [
    "HNT_DIVISIONS",
    "HNT_DIVISION_BBOXES",
    "HNT_SUBMARKETS",
    "HUNTINGTON_WV_CENTER",
    "HUNTINGTON_WV_CITY_ID",
    "HUNTINGTON_WV_DIVISIONS",
    "HUNTINGTON_WV_DIVISION_BBOXES",
    "HUNTINGTON_WV_METRO_BBOX",
    "HUNTINGTON_WV_SUBMARKETS",
    "REGISTRATION",
    "is_in_huntington_wv",
    "is_in_huntington_wv_metro",
]
