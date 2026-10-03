"""Portland, Maine Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Portland,
Maine (Cumberland County seat on Casco Bay — a compact peninsula/back-cove
metro that does not overlap the sibling Boston/Providence leaf boxes).

Feeds: SLA reads the SNAP retailer slice (``snap_sla_spec``, Maine stores inside
the metro box). The DEEDS feed registered until 2026-09-30 read
``ParcelsWGS84`` at a layer id that does not exist, and no public sale source
exists: the city's parcel layers carry no sale fields, its one deed-dated
layer holds seven dated rows (the newest from 2005), the assessor's sales tab
is a per-parcel search, and Maine publishes no statewide transfer dataset.
Permits and 311 remain unregistered.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

PORTLAND_MAINE_CITY_ID: str = "portland_maine"

# City-parcel bbox (Casco Bay peninsula + Back Cove + southwest neighborhoods).
# Center is downtown Portland (Congress Street CBD).
PORTLAND_MAINE_METRO_BBOX: dict[str, float] = {
    "min_lat": 43.60,
    "max_lat": 43.72,
    "min_lng": -70.32,
    "max_lng": -70.20,
}

# Registration-contract center: downtown Portland (Congress St CBD).
PORTLAND_MAINE_CENTER: dict[str, float] = {"lat": 43.6591, "lng": -70.2568}

# 5 Portland, Maine Division Bounding Boxes (strictly nested inside the metro bbox)
PORTLAND_MAINE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_PENINSULA": {"min_lat": 43.64, "max_lat": 43.67, "min_lng": -70.265, "max_lng": -70.245},
    "EAST_BAYSIDE":       {"min_lat": 43.66, "max_lat": 43.675, "min_lng": -70.260, "max_lng": -70.245},
    "WEST_END":           {"min_lat": 43.65, "max_lat": 43.675, "min_lng": -70.275, "max_lng": -70.255},
    "BACK_COVE":          {"min_lat": 43.67, "max_lat": 43.695, "min_lng": -70.280, "max_lng": -70.255},
    "SOUTHWEST_HILLS":    {"min_lat": 43.615, "max_lat": 43.645, "min_lng": -70.300, "max_lng": -70.265},
}


def is_in_portland_maine_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Portland, ME metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        PORTLAND_MAINE_METRO_BBOX["min_lat"] <= lat <= PORTLAND_MAINE_METRO_BBOX["max_lat"]
        and PORTLAND_MAINE_METRO_BBOX["min_lng"] <= lng <= PORTLAND_MAINE_METRO_BBOX["max_lng"]
    )


def is_in_portland_maine(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_portland_maine_metro`."""
    return is_in_portland_maine_metro(lat, lng)


# ---------------------------------------------------------------------------
# Portland, Maine Submarket Registry (8 Submarkets Across 5 Divisions)
# ---------------------------------------------------------------------------

PORTLAND_MAINE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # DOWNTOWN_PENINSULA (2 Submarkets)
    "Old Port": SubmarketMeta(
        name="Old Port",
        borough="DOWNTOWN_PENINSULA",
        lat=43.6570,
        lng=-70.2545,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.86,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The cobblestone waterfront district of boutiques, restaurants, and converted wharf condos at the foot of the Old Port.",
        city_id="portland_maine",
    ),
    "Arts District": SubmarketMeta(
        name="Arts District",
        borough="DOWNTOWN_PENINSULA",
        lat=43.6530,
        lng=-70.2600,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.83,
        capex=4800000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=52.0,
        description="The Congress Street corridor around the Portland Museum of Art and the State Theatre with mixed-use conversion and gallery-retail demand.",
        city_id="portland_maine",
    ),
    # EAST_BAYSIDE (2 Submarkets)
    "East Bayside": SubmarketMeta(
        name="East Bayside",
        borough="EAST_BAYSIDE",
        lat=43.6680,
        lng=-70.2550,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.82,
        capex=4600000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=50.0,
        description="The rapidly gentrifying grid east of Franklin Arterial with food-hall retail, micro-breweries, and infill residential.",
        city_id="portland_maine",
    ),
    "Munjoy Hill": SubmarketMeta(
        name="Munjoy Hill",
        borough="EAST_BAYSIDE",
        lat=43.6710,
        lng=-70.2500,
        zoom=15.0,
        pitch=38.0,
        base_lims=0.80,
        capex=5300000.0,
        permit_vel=26.0,
        shift_ratio=1.38,
        sla=49.0,
        description="The eastern bluff overlooking the bay with dense pre-war housing stock, the Eastern Prom, and steady renovation flow.",
        city_id="portland_maine",
    ),
    # WEST_END (2 Submarkets)
    "West End": SubmarketMeta(
        name="West End",
        borough="WEST_END",
        lat=43.6630,
        lng=-70.2650,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.84,
        capex=5000000.0,
        permit_vel=24.0,
        shift_ratio=1.36,
        sla=51.0,
        description="The Victorian mansion district west of downtown with landmarked rowhouses and high-end restoration trades.",
        city_id="portland_maine",
    ),
    "Parkside": SubmarketMeta(
        name="Parkside",
        borough="WEST_END",
        lat=43.6580,
        lng=-70.2700,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.72,
        capex=3300000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=40.0,
        description="The mixed-income ward around Deering Oaks with craftsman stock, a deep rental register, and block-by-block reinvestment.",
        city_id="portland_maine",
    ),
    # BACK_COVE (1 Submarket)
    "Back Cove": SubmarketMeta(
        name="Back Cove",
        borough="BACK_COVE",
        lat=43.6850,
        lng=-70.2700,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.74,
        capex=3800000.0,
        permit_vel=22.0,
        shift_ratio=1.28,
        sla=44.0,
        description="The ring-road residential basin north of downtown with solid double-lot housing and investor renovation flow.",
        city_id="portland_maine",
    ),
    # SOUTHWEST_HILLS (2 Submarkets)
    "Deering": SubmarketMeta(
        name="Deering",
        borough="SOUTHWEST_HILLS",
        lat=43.6300,
        lng=-70.2800,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.70,
        capex=3100000.0,
        permit_vel=18.0,
        shift_ratio=1.22,
        sla=38.0,
        description="The northern residential neighborhoods along Stevens Avenue with multi-family stock and immigrant-owned commercial corridors.",
        city_id="portland_maine",
    ),
    "Nasons Corner": SubmarketMeta(
        name="Nasons Corner",
        borough="SOUTHWEST_HILLS",
        lat=43.6200,
        lng=-70.2900,
        zoom=14.0,
        pitch=30.0,
        base_lims=0.66,
        capex=2700000.0,
        permit_vel=16.0,
        shift_ratio=1.18,
        sla=34.0,
        description="The southwest edge of the city with post-war subdivisions and the lowest sale prices meeting the heaviest acquisition flow.",
        city_id="portland_maine",
    ),
}


# ---------------------------------------------------------------------------
# Portland, Maine Divisions Catalog
# ---------------------------------------------------------------------------

PORTLAND_MAINE_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_PENINSULA": BoroughMeta(
        name="DOWNTOWN_PENINSULA",
        center_lat=43.6550,
        center_lng=-70.2550,
        zoom=13.5,
        bbox=PORTLAND_MAINE_DIVISION_BBOXES["DOWNTOWN_PENINSULA"],
        submarkets=[k for k, v in PORTLAND_MAINE_SUBMARKETS.items() if v.borough == "DOWNTOWN_PENINSULA"],
        city_id="portland_maine",
    ),
    "EAST_BAYSIDE": BoroughMeta(
        name="EAST_BAYSIDE",
        center_lat=43.6680,
        center_lng=-70.2520,
        zoom=13.5,
        bbox=PORTLAND_MAINE_DIVISION_BBOXES["EAST_BAYSIDE"],
        submarkets=[k for k, v in PORTLAND_MAINE_SUBMARKETS.items() if v.borough == "EAST_BAYSIDE"],
        city_id="portland_maine",
    ),
    "WEST_END": BoroughMeta(
        name="WEST_END",
        center_lat=43.6630,
        center_lng=-70.2650,
        zoom=13.5,
        bbox=PORTLAND_MAINE_DIVISION_BBOXES["WEST_END"],
        submarkets=[k for k, v in PORTLAND_MAINE_SUBMARKETS.items() if v.borough == "WEST_END"],
        city_id="portland_maine",
    ),
    "BACK_COVE": BoroughMeta(
        name="BACK_COVE",
        center_lat=43.6820,
        center_lng=-70.2680,
        zoom=13.0,
        bbox=PORTLAND_MAINE_DIVISION_BBOXES["BACK_COVE"],
        submarkets=[k for k, v in PORTLAND_MAINE_SUBMARKETS.items() if v.borough == "BACK_COVE"],
        city_id="portland_maine",
    ),
    "SOUTHWEST_HILLS": BoroughMeta(
        name="SOUTHWEST_HILLS",
        center_lat=43.6300,
        center_lng=-70.2820,
        zoom=13.0,
        bbox=PORTLAND_MAINE_DIVISION_BBOXES["SOUTHWEST_HILLS"],
        submarkets=[k for k, v in PORTLAND_MAINE_SUBMARKETS.items() if v.borough == "SOUTHWEST_HILLS"],
        city_id="portland_maine",
    ),
}

PMA_DIVISION_BBOXES = PORTLAND_MAINE_DIVISION_BBOXES
PMA_SUBMARKETS = PORTLAND_MAINE_SUBMARKETS
PMA_DIVISIONS = PORTLAND_MAINE_DIVISIONS


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=PORTLAND_MAINE_METRO_BBOX,
    division_bboxes=PORTLAND_MAINE_DIVISION_BBOXES,
    submarkets=PORTLAND_MAINE_SUBMARKETS,
    divisions=PORTLAND_MAINE_DIVISIONS,
    contains=is_in_portland_maine_metro,
)

__all__ = [
    "PMA_DIVISIONS",
    "PMA_DIVISION_BBOXES",
    "PMA_SUBMARKETS",
    "PORTLAND_MAINE_CENTER",
    "PORTLAND_MAINE_CITY_ID",
    "PORTLAND_MAINE_DIVISIONS",
    "PORTLAND_MAINE_DIVISION_BBOXES",
    "PORTLAND_MAINE_METRO_BBOX",
    "PORTLAND_MAINE_SUBMARKETS",
    "REGISTRATION",
    "is_in_portland_maine",
    "is_in_portland_maine_metro",
]
