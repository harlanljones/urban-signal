"""Wilmington, DE spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Wilmington,
DE (New Castle County seat on the Christina River, at the head of the
Delaware Estuary — deliberately not overlapping the sibling Philadelphia
leaf box to the north).

Feeds: SLA reads the SNAP retailer slice (``snap_sla_spec``, Delaware stores
inside the metro box). The DEEDS feed registered until 2026-09-30 named a host
(gis.newcastlede.gov) that does not exist, and no verified public sale source
exists. New Castle County's ``BaseMaps/PropertySales`` MapServer on
gis.nccde.org could not be checked (the host answers HTTP 472 to automated
clients), and its ArcGIS Online records describe per-year residential layers
for 2013 to 2019 only. Permits and 311 remain unregistered.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

WILMINGTON_DE_CITY_ID: str = "wilmington_de"

# Wilmington, DE city-parcel bbox. Anchored on the downtown core
# (39.7447 / -75.5466): south edge at the Christina River / Southbridge line
# (39.70), north edge at the Brandywine / city-limit line (39.79), west edge
# near the I-95 / Newport border (-75.62), east edge at the riverfront /
# Edgemoor line (-75.51). The metro box stays clear of Philadelphia's leaf
# box to the northeast.
WILMINGTON_DE_METRO_BBOX: dict[str, float] = {
    "min_lat": 39.70,
    "max_lat": 39.79,
    "min_lng": -75.62,
    "max_lng": -75.51,
}

# Registration-contract center: downtown Wilmington (Market St CBD).
WILMINGTON_DE_CENTER: dict[str, float] = {"lat": 39.7447, "lng": -75.5466}

# 6 Wilmington Division Bounding Boxes (strictly nested inside the metro bbox)
WILMINGTON_DE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_CORE":   {"min_lat": 39.740, "max_lat": 39.760, "min_lng": -75.560, "max_lng": -75.540},
    "RIVERFRONT":      {"min_lat": 39.730, "max_lat": 39.750, "min_lng": -75.540, "max_lng": -75.520},
    "WEST_SIDE":       {"min_lat": 39.750, "max_lat": 39.780, "min_lng": -75.600, "max_lng": -75.560},
    "NORTH_SIDE":      {"min_lat": 39.770, "max_lat": 39.790, "min_lng": -75.560, "max_lng": -75.520},
    "SOUTH_SIDE":      {"min_lat": 39.700, "max_lat": 39.730, "min_lng": -75.570, "max_lng": -75.530},
    "EAST_SIDE":       {"min_lat": 39.730, "max_lat": 39.760, "min_lng": -75.530, "max_lng": -75.510},
}


def is_in_wilmington_de_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Wilmington, DE metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        WILMINGTON_DE_METRO_BBOX["min_lat"] <= lat <= WILMINGTON_DE_METRO_BBOX["max_lat"]
        and WILMINGTON_DE_METRO_BBOX["min_lng"] <= lng <= WILMINGTON_DE_METRO_BBOX["max_lng"]
    )


def is_in_wilmington_de(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_wilmington_de_metro`."""
    return is_in_wilmington_de_metro(lat, lng)


# ---------------------------------------------------------------------------
# Wilmington, DE Submarket Registry (7 Submarkets Across 6 Divisions)
# Anchor coordinates sit inside their declared division bbox (verified against
# the metro extent above).
# ---------------------------------------------------------------------------

WILMINGTON_DE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CORE (2 Submarkets)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN_CORE",
        lat=39.7447,
        lng=-75.5466,
        zoom=15.0,
        pitch=55.0,
        base_lims=0.85,
        capex=6800000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The Market Street CBD and Rodney Square core with office-to-residential conversions, the Wilmington renaissance pipeline, and the city's densest mixed-use activity.",
        city_id="wilmington_de",
    ),
    "Little Italy": SubmarketMeta(
        name="Little Italy",
        borough="DOWNTOWN_CORE",
        lat=39.7470,
        lng=-75.5530,
        zoom=15.0,
        pitch=48.0,
        base_lims=0.81,
        capex=4900000.0,
        permit_vel=26.0,
        shift_ratio=1.40,
        sla=49.0,
        description="The Union Street corridor south of downtown with rowhouse restoration trades, trattoria-row licensing, and steady infill reinvestment.",
        city_id="wilmington_de",
    ),
    # =======================================================================
    # RIVERFRONT (1 Submarket)
    # =======================================================================
    "Riverfront": SubmarketMeta(
        name="Riverfront",
        borough="RIVERFRONT",
        lat=39.7420,
        lng=-75.5350,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.83,
        capex=6200000.0,
        permit_vel=28.0,
        shift_ratio=1.44,
        sla=54.0,
        description="The Christina Riverfront east of the CBD with the Blue Rocks ballpark, convention-hotel licensing, and the metro's highest-energy waterfront renewal.",
        city_id="wilmington_de",
    ),
    # =======================================================================
    # EAST_SIDE (1 Submarket)
    # =======================================================================
    "Trolley Square": SubmarketMeta(
        name="Trolley Square",
        borough="EAST_SIDE",
        lat=39.7580,
        lng=-75.5230,
        zoom=14.5,
        pitch=46.0,
        base_lims=0.87,
        capex=7000000.0,
        permit_vel=24.0,
        shift_ratio=1.48,
        sla=58.0,
        description="The 17th Street / Delaware Avenue edge of the East Side with 1920s apartment stock, stable owner-occupancy, and the metro's most conservation-minded renovation flow.",
        city_id="wilmington_de",
    ),
    # =======================================================================
    # WEST_SIDE (1 Submarket)
    # =======================================================================
    "Highlands": SubmarketMeta(
        name="Highlands",
        borough="WEST_SIDE",
        lat=39.7610,
        lng=-75.5780,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.78,
        capex=4600000.0,
        permit_vel=20.0,
        shift_ratio=1.38,
        sla=48.0,
        description="The West Side's Highlands grid around the Pennsylvania Avenue branch with pre-war single-family stock and block-by-block reinvestment near the city line.",
        city_id="wilmington_de",
    ),
    # =======================================================================
    # NORTH_SIDE (1 Submarket)
    # =======================================================================
    "Brandywine": SubmarketMeta(
        name="Brandywine",
        borough="NORTH_SIDE",
        lat=39.7800,
        lng=-75.5450,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.75,
        capex=4300000.0,
        permit_vel=18.0,
        shift_ratio=1.34,
        sla=46.0,
        description="The Brandywine / 10th Street north side with the hospital-edge commercial spine, Highlands spillover, and value-priced family-housing reinvestment.",
        city_id="wilmington_de",
    ),
    # =======================================================================
    # SOUTH_SIDE (1 Submarket)
    # =======================================================================
    "Southbridge": SubmarketMeta(
        name="Southbridge",
        borough="SOUTH_SIDE",
        lat=39.7150,
        lng=-75.5450,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.71,
        capex=3700000.0,
        permit_vel=17.0,
        shift_ratio=1.30,
        sla=42.0,
        description="The Christina River / Southbridge village with early-stage waterfront reinvestment, the port-adjacent industrial edge, and the metro's lowest sale prices.",
        city_id="wilmington_de",
    ),
}


# ---------------------------------------------------------------------------
# Wilmington, DE Divisions Catalog
# ---------------------------------------------------------------------------

WILMINGTON_DE_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=39.7455,
        center_lng=-75.5490,
        zoom=14.5,
        bbox=WILMINGTON_DE_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in WILMINGTON_DE_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="wilmington_de",
    ),
    "RIVERFRONT": BoroughMeta(
        name="RIVERFRONT",
        center_lat=39.7420,
        center_lng=-75.5350,
        zoom=14.0,
        bbox=WILMINGTON_DE_DIVISION_BBOXES["RIVERFRONT"],
        submarkets=[k for k, v in WILMINGTON_DE_SUBMARKETS.items() if v.borough == "RIVERFRONT"],
        city_id="wilmington_de",
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=39.7610,
        center_lng=-75.5780,
        zoom=14.0,
        bbox=WILMINGTON_DE_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in WILMINGTON_DE_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id="wilmington_de",
    ),
    "NORTH_SIDE": BoroughMeta(
        name="NORTH_SIDE",
        center_lat=39.7800,
        center_lng=-75.5450,
        zoom=14.0,
        bbox=WILMINGTON_DE_DIVISION_BBOXES["NORTH_SIDE"],
        submarkets=[k for k, v in WILMINGTON_DE_SUBMARKETS.items() if v.borough == "NORTH_SIDE"],
        city_id="wilmington_de",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=39.7150,
        center_lng=-75.5450,
        zoom=14.0,
        bbox=WILMINGTON_DE_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in WILMINGTON_DE_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="wilmington_de",
    ),
    "EAST_SIDE": BoroughMeta(
        name="EAST_SIDE",
        center_lat=39.7580,
        center_lng=-75.5230,
        zoom=14.0,
        bbox=WILMINGTON_DE_DIVISION_BBOXES["EAST_SIDE"],
        submarkets=[k for k, v in WILMINGTON_DE_SUBMARKETS.items() if v.borough == "EAST_SIDE"],
        city_id="wilmington_de",
    ),
}

WILM_DE_DIVISION_BBOXES = WILMINGTON_DE_DIVISION_BBOXES
WILM_DE_SUBMARKETS = WILMINGTON_DE_SUBMARKETS
WILM_DE_DIVISIONS = WILMINGTON_DE_DIVISIONS


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=WILMINGTON_DE_METRO_BBOX,
    division_bboxes=WILMINGTON_DE_DIVISION_BBOXES,
    submarkets=WILMINGTON_DE_SUBMARKETS,
    divisions=WILMINGTON_DE_DIVISIONS,
    contains=is_in_wilmington_de_metro,
)

__all__ = [
    "REGISTRATION",
    "WILMINGTON_DE_CENTER",
    "WILMINGTON_DE_CITY_ID",
    "WILMINGTON_DE_DIVISIONS",
    "WILMINGTON_DE_DIVISION_BBOXES",
    "WILMINGTON_DE_METRO_BBOX",
    "WILMINGTON_DE_SUBMARKETS",
    "WILM_DE_DIVISIONS",
    "WILM_DE_DIVISION_BBOXES",
    "WILM_DE_SUBMARKETS",
    "is_in_wilmington_de",
    "is_in_wilmington_de_metro",
]
