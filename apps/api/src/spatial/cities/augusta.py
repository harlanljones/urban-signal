"""Augusta, GA — Metro geometry and submarket catalog for Urban Signal.

Provides camera metadata, division catalog, and geographic bounding boxes for
the Augusta metropolitan area (Richmond County focus).

This leaf declares only spatial structures; feed registrations live in the spine
registry. The registry will register a verified permits dataset (ArcGIS table,
address-geocoded) and a SNAP SLA state slice for Georgia.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.spatial.registration import SpatialRegistration

# Canonical, stable city id
AUGUSTA_CITY_ID: str = "augusta"

# A permissive metro bbox that comfortably contains divisions and submarkets.
# Approx bounds: lat 33.25–33.65, lng −82.20 – −81.85
AUGUSTA_METRO_BBOX: Dict[str, float] = {
    "min_lat": 33.25,
    "max_lat": 33.65,
    "min_lng": -82.20,
    "max_lng": -81.85,
}

# Four coarse divisions hand-authored to be disjoint and unambiguous.
AUGUSTA_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown, Broad St, Riverwalk, Medical District
    "DOWNTOWN_MEDICAL": {"min_lat": 33.450, "max_lat": 33.505, "min_lng": -81.995, "max_lng": -81.955},
    # Western neighborhoods (Summerville / Augusta University area, West Augusta)
    "WEST_AUGUSTA": {"min_lat": 33.470, "max_lat": 33.560, "min_lng": -82.120, "max_lng": -82.010},
    # South Augusta / Deans Bridge Rd corridor
    "SOUTH_AUGUSTA": {"min_lat": 33.300, "max_lat": 33.430, "min_lng": -82.110, "max_lng": -81.970},
    # East Augusta / Industrial Riverport (kept within GA side of river)
    "EAST_AUGUSTA": {"min_lat": 33.450, "max_lat": 33.540, "min_lng": -81.950, "max_lng": -81.890},
}


def is_in_augusta_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Augusta metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        AUGUSTA_METRO_BBOX["min_lat"] <= lat <= AUGUSTA_METRO_BBOX["max_lat"]
        and AUGUSTA_METRO_BBOX["min_lng"] <= lng <= AUGUSTA_METRO_BBOX["max_lng"]
    )


# Alias for symmetry with other modules.
is_in_greater_augusta_metro = is_in_augusta_metro


AUGUSTA_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # DOWNTOWN_MEDICAL
    "Downtown & Broad Street": SubmarketMeta(
        name="Downtown & Broad Street",
        borough="DOWNTOWN_MEDICAL",
        lat=33.475,
        lng=-81.970,
        zoom=15.0,
        pitch=52.0,
        base_lims=0.86,
        capex=6500000.0,
        permit_vel=38.0,
        shift_ratio=1.45,
        sla=60.0,
        description="Historic Broad Street corridor and Riverwalk mixed-use spine with steady renovation permits.",
        city_id="augusta",
    ),
    "Medical District & AU": SubmarketMeta(
        name="Medical District & AU",
        borough="DOWNTOWN_MEDICAL",
        lat=33.476,
        lng=-81.962,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.84,
        capex=7200000.0,
        permit_vel=35.0,
        shift_ratio=1.42,
        sla=58.0,
        description="Augusta University and adjacent medical complex with institutional capital and infill housing.",
        city_id="augusta",
    ),
    # WEST_AUGUSTA
    "Summerville & AU Campus": SubmarketMeta(
        name="Summerville & AU Campus",
        borough="WEST_AUGUSTA",
        lat=33.486,
        lng=-82.022,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.82,
        capex=6000000.0,
        permit_vel=30.0,
        shift_ratio=1.38,
        sla=56.0,
        description="Historic Summerville neighborhood around AU Summerville campus; renovation-led permits.",
        city_id="augusta",
    ),
    "West Augusta Retail Spine": SubmarketMeta(
        name="West Augusta Retail Spine",
        borough="WEST_AUGUSTA",
        lat=33.505,
        lng=-82.070,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=4800000.0,
        permit_vel=24.0,
        shift_ratio=1.30,
        sla=50.0,
        description="Washington Rd commercial corridor and adjacent residential pockets with steady tenant improvements.",
        city_id="augusta",
    ),
    # SOUTH_AUGUSTA
    "Deans Bridge & Regency": SubmarketMeta(
        name="Deans Bridge & Regency",
        borough="SOUTH_AUGUSTA",
        lat=33.390,
        lng=-82.030,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.70,
        capex=3500000.0,
        permit_vel=22.0,
        shift_ratio=1.24,
        sla=46.0,
        description="South Augusta arterial corridor with small-format commercial rehab and single-family turnover.",
        city_id="augusta",
    ),
    "Fort Eisenhower Gateway": SubmarketMeta(
        name="Fort Eisenhower Gateway",
        borough="SOUTH_AUGUSTA",
        lat=33.405,
        lng=-81.995,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.72,
        capex=3800000.0,
        permit_vel=20.0,
        shift_ratio=1.26,
        sla=47.0,
        description="Gateway area serving Fort Eisenhower with workforce housing and service permitting.",
        city_id="augusta",
    ),
    # EAST_AUGUSTA
    "East Augusta Riverport": SubmarketMeta(
        name="East Augusta Riverport",
        borough="EAST_AUGUSTA",
        lat=33.505,
        lng=-81.925,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.74,
        capex=4200000.0,
        permit_vel=21.0,
        shift_ratio=1.28,
        sla=48.0,
        description="Industrial riverfront and logistics-adjacent redevelopment on the GA side of the Savannah River.",
        city_id="augusta",
    ),
    "Laney-Walker & Bethlehem": SubmarketMeta(
        name="Laney-Walker & Bethlehem",
        borough="EAST_AUGUSTA",
        lat=33.470,
        lng=-81.930,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=5200000.0,
        permit_vel=28.0,
        shift_ratio=1.34,
        sla=52.0,
        description="Historic neighborhoods east of downtown with ongoing small-lot infill and rehab.",
        city_id="augusta",
    ),
}


AUGUSTA_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_MEDICAL": BoroughMeta(
        name="DOWNTOWN_MEDICAL",
        center_lat=33.478,
        center_lng=-81.968,
        zoom=13.5,
        bbox=AUGUSTA_DIVISION_BBOXES["DOWNTOWN_MEDICAL"],
        submarkets=[k for k, v in AUGUSTA_SUBMARKETS.items() if v.borough == "DOWNTOWN_MEDICAL"],
        city_id="augusta",
    ),
    "WEST_AUGUSTA": BoroughMeta(
        name="WEST_AUGUSTA",
        center_lat=33.508,
        center_lng=-82.050,
        zoom=13.0,
        bbox=AUGUSTA_DIVISION_BBOXES["WEST_AUGUSTA"],
        submarkets=[k for k, v in AUGUSTA_SUBMARKETS.items() if v.borough == "WEST_AUGUSTA"],
        city_id="augusta",
    ),
    "SOUTH_AUGUSTA": BoroughMeta(
        name="SOUTH_AUGUSTA",
        center_lat=33.385,
        center_lng=-82.015,
        zoom=13.0,
        bbox=AUGUSTA_DIVISION_BBOXES["SOUTH_AUGUSTA"],
        submarkets=[k for k, v in AUGUSTA_SUBMARKETS.items() if v.borough == "SOUTH_AUGUSTA"],
        city_id="augusta",
    ),
    "EAST_AUGUSTA": BoroughMeta(
        name="EAST_AUGUSTA",
        center_lat=33.500,
        center_lng=-81.925,
        zoom=13.0,
        bbox=AUGUSTA_DIVISION_BBOXES["EAST_AUGUSTA"],
        submarkets=[k for k, v in AUGUSTA_SUBMARKETS.items() if v.borough == "EAST_AUGUSTA"],
        city_id="augusta",
    ),
}

# Verbose aliases for compatibility (mirrors other city modules).
GREATER_AUGUSTA_METRO_BBOX = AUGUSTA_METRO_BBOX
AUGUSTA_CENTER = {"lat": 33.476, "lng": -82.010}

# Leaf-local spatial registration object (the spine references these dicts).
REGISTRATION = SpatialRegistration(
    metro_bbox=AUGUSTA_METRO_BBOX,
    division_bboxes=AUGUSTA_DIVISION_BBOXES,
    submarkets=AUGUSTA_SUBMARKETS,
    divisions=AUGUSTA_DIVISIONS,
    contains=is_in_augusta_metro,
)

