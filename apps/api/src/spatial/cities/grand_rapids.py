"""Grand Rapids, Michigan spatial registry and dashboard geometry.

Grand Rapids is map-enabled as a geometry-only registration while its
transactional families remain unregistered: the verified public Hub catalog
contains reference geometry, and Accela Citizen Access is currently UI-only.
"""

from src.spatial.registration import SpatialRegistration
from src.spatial.submarkets import BoroughMeta, SubmarketMeta


GRAND_RAPIDS_METRO_BBOX: dict[str, float] = {
    "min_lat": 42.70,
    "max_lat": 43.25,
    "min_lng": -85.95,
    "max_lng": -85.25,
}

GRAND_RAPIDS_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "GRAND_RAPIDS_CORE": {
        "min_lat": 42.78,
        "max_lat": 43.18,
        "min_lng": -85.85,
        "max_lng": -85.45,
    },
}


def is_in_grand_rapids_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered metro extent."""
    if lat is None or lng is None:
        return False
    return (
        GRAND_RAPIDS_METRO_BBOX["min_lat"] <= lat <= GRAND_RAPIDS_METRO_BBOX["max_lat"]
        and GRAND_RAPIDS_METRO_BBOX["min_lng"] <= lng <= GRAND_RAPIDS_METRO_BBOX["max_lng"]
    )


GRAND_RAPIDS_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown Grand Rapids": SubmarketMeta(
        name="Downtown Grand Rapids", borough="GRAND_RAPIDS_CORE", lat=42.9634, lng=-85.6681,
        zoom=13.2, pitch=46.0, base_lims=0.83, capex=6900000.0, permit_vel=32.0,
        shift_ratio=1.39, sla=56.0,
        description="Riverfront civic and entertainment core with adaptive reuse, office conversion, and mixed-use investment.",
        city_id="grand_rapids",
    ),
    "Midtown & Medical Mile": SubmarketMeta(
        name="Midtown & Medical Mile", borough="GRAND_RAPIDS_CORE", lat=42.9650, lng=-85.6210,
        zoom=13.0, pitch=44.0, base_lims=0.80, capex=6100000.0, permit_vel=29.0,
        shift_ratio=1.36, sla=58.0,
        description="Medical and educational anchor corridor with institutional expansion, housing, and neighborhood services.",
        city_id="grand_rapids",
    ),
    "West Side": SubmarketMeta(
        name="West Side", borough="GRAND_RAPIDS_CORE", lat=42.9630, lng=-85.7040,
        zoom=12.8, pitch=43.0, base_lims=0.77, capex=4700000.0, permit_vel=27.0,
        shift_ratio=1.33, sla=53.0,
        description="Historic west-side neighborhoods with small-business corridors, rehabilitation, and infill housing.",
        city_id="grand_rapids",
    ),
    "Eastown & Wealthy Street": SubmarketMeta(
        name="Eastown & Wealthy Street", borough="GRAND_RAPIDS_CORE", lat=42.9560, lng=-85.6260,
        zoom=12.9, pitch=44.0, base_lims=0.79, capex=5200000.0, permit_vel=28.0,
        shift_ratio=1.35, sla=55.0,
        description="Walkable east-side commercial nodes with independent retail, dining, and residential reinvestment.",
        city_id="grand_rapids",
    ),
    "North Kent Growth Corridor": SubmarketMeta(
        name="North Kent Growth Corridor", borough="GRAND_RAPIDS_CORE", lat=43.0400, lng=-85.6000,
        zoom=12.4, pitch=40.0, base_lims=0.76, capex=6400000.0, permit_vel=31.0,
        shift_ratio=1.34, sla=54.0,
        description="North-side employment and suburban growth corridor with commercial expansion and new housing supply.",
        city_id="grand_rapids",
    ),
}


GRAND_RAPIDS_DIVISIONS: dict[str, BoroughMeta] = {
    "GRAND_RAPIDS_CORE": BoroughMeta(
        name="Grand Rapids / Kent County", center_lat=42.9634, center_lng=-85.6681,
        zoom=10.8, bbox=GRAND_RAPIDS_DIVISION_BBOXES["GRAND_RAPIDS_CORE"],
        submarkets=list(GRAND_RAPIDS_SUBMARKETS), city_id="grand_rapids",
    ),
}


REGISTRATION = SpatialRegistration(
    metro_bbox=GRAND_RAPIDS_METRO_BBOX,
    division_bboxes=GRAND_RAPIDS_DIVISION_BBOXES,
    submarkets=GRAND_RAPIDS_SUBMARKETS,
    divisions=GRAND_RAPIDS_DIVISIONS,
    contains=is_in_grand_rapids_metro,
)

