"""Peoria, Illinois spatial registry and geometry (US-260)."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Peoria MSA envelope (Peoria / Tazewell / Woodford counties). Bounded a little
# wider than the recorded-sales extent, which spans lat 40.56..40.96 and
# lng -89.97..-89.48 as sampled from the county feed.
PEORIA_METRO_BBOX: dict[str, float] = {
    "min_lat": 40.45,
    "max_lat": 41.05,
    "min_lng": -90.05,
    "max_lng": -89.35,
}

# Two divisions split by the Illinois River: the city of Peoria on the west
# bank, and the Tazewell County communities on the east.
PEORIA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "PEORIA_CORE": {
        "min_lat": 40.66,
        "max_lat": 40.83,
        "min_lng": -89.72,
        "max_lng": -89.55,
    },
    "PEORIA_EAST": {
        "min_lat": 40.52,
        "max_lat": 40.72,
        "min_lng": -89.68,
        "max_lng": -89.40,
    },
}


def is_in_peoria_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the Peoria metro extent."""
    if lat is None or lng is None:
        return False
    return (
        PEORIA_METRO_BBOX["min_lat"] <= lat <= PEORIA_METRO_BBOX["max_lat"]
        and PEORIA_METRO_BBOX["min_lng"] <= lng <= PEORIA_METRO_BBOX["max_lng"]
    )


PEORIA_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown Peoria": SubmarketMeta(
        name="Downtown Peoria",
        borough="PEORIA_CORE",
        lat=40.6936,
        lng=-89.5890,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=6100000.0,
        permit_vel=30.0,
        shift_ratio=1.32,
        sla=52.0,
        description="Riverfront core around the Warehouse District with mixed-use conversion and medical-campus spillover.",
        city_id="peoria",
    ),
    "North Peoria": SubmarketMeta(
        name="North Peoria",
        borough="PEORIA_CORE",
        lat=40.7600,
        lng=-89.6000,
        zoom=12.8,
        pitch=40.0,
        base_lims=0.74,
        capex=4900000.0,
        permit_vel=26.0,
        shift_ratio=1.26,
        sla=47.0,
        description="Northern growth corridor along Knoxville and Sheridan with retail centres and newer subdivisions.",
        city_id="peoria",
    ),
    "West Bluff": SubmarketMeta(
        name="West Bluff",
        borough="PEORIA_CORE",
        lat=40.6980,
        lng=-89.6180,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.72,
        capex=4200000.0,
        permit_vel=24.0,
        shift_ratio=1.23,
        sla=45.0,
        description="Historic bluff neighbourhoods west of downtown anchored by Bradley University and steady rehab activity.",
        city_id="peoria",
    ),
    "Peoria Heights": SubmarketMeta(
        name="Peoria Heights",
        borough="PEORIA_CORE",
        lat=40.7472,
        lng=-89.5720,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.73,
        capex=4400000.0,
        permit_vel=25.0,
        shift_ratio=1.25,
        sla=46.0,
        description="Village district above the river bluff with boutique retail along Prospect Road and infill housing.",
        city_id="peoria",
    ),
    "East Peoria": SubmarketMeta(
        name="East Peoria",
        borough="PEORIA_EAST",
        lat=40.6664,
        lng=-89.5801,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.71,
        capex=4000000.0,
        permit_vel=23.0,
        shift_ratio=1.22,
        sla=44.0,
        description="East-bank commercial strip along IL-8 and the Levee District with riverfront redevelopment.",
        city_id="peoria",
    ),
    "Morton": SubmarketMeta(
        name="Morton",
        borough="PEORIA_EAST",
        lat=40.6114,
        lng=-89.4587,
        zoom=12.8,
        pitch=38.0,
        base_lims=0.69,
        capex=3700000.0,
        permit_vel=21.0,
        shift_ratio=1.19,
        sla=42.0,
        description="Suburban Tazewell village with distribution employment and consistent single-family construction.",
        city_id="peoria",
    ),
    "Pekin": SubmarketMeta(
        name="Pekin",
        borough="PEORIA_EAST",
        lat=40.5675,
        lng=-89.6407,
        zoom=12.8,
        pitch=38.0,
        base_lims=0.67,
        capex=3400000.0,
        permit_vel=20.0,
        shift_ratio=1.17,
        sla=41.0,
        description="Tazewell County seat south of the metro with industrial riverfront and established residential stock.",
        city_id="peoria",
    ),
}


PEORIA_DIVISIONS: dict[str, BoroughMeta] = {
    "PEORIA_CORE": BoroughMeta(
        name="Peoria",
        center_lat=40.6936,
        center_lng=-89.5890,
        zoom=11.6,
        bbox=PEORIA_DIVISION_BBOXES["PEORIA_CORE"],
        submarkets=[
            name
            for name, meta in PEORIA_SUBMARKETS.items()
            if meta.borough == "PEORIA_CORE"
        ],
        city_id="peoria",
    ),
    "PEORIA_EAST": BoroughMeta(
        name="East Peoria / Tazewell",
        center_lat=40.6664,
        center_lng=-89.5801,
        zoom=11.4,
        bbox=PEORIA_DIVISION_BBOXES["PEORIA_EAST"],
        submarkets=[
            name
            for name, meta in PEORIA_SUBMARKETS.items()
            if meta.borough == "PEORIA_EAST"
        ],
        city_id="peoria",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=PEORIA_METRO_BBOX,
    division_bboxes=PEORIA_DIVISION_BBOXES,
    submarkets=PEORIA_SUBMARKETS,
    divisions=PEORIA_DIVISIONS,
    contains=is_in_peoria_metro,
)
