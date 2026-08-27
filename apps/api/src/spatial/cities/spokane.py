"""Spokane / Spokane County spatial registry and geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

SPOKANE_METRO_BBOX: dict[str, float] = {
    "min_lat": 47.00,
    "max_lat": 48.20,
    "min_lng": -118.50,
    "max_lng": -116.90,
}

SPOKANE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "SPOKANE_CORE": {
        "min_lat": 47.20,
        "max_lat": 47.95,
        "min_lng": -118.20,
        "max_lng": -117.00,
    },
}


def is_in_spokane_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the Spokane County extent."""
    if lat is None or lng is None:
        return False
    return (
        SPOKANE_METRO_BBOX["min_lat"] <= lat <= SPOKANE_METRO_BBOX["max_lat"]
        and SPOKANE_METRO_BBOX["min_lng"] <= lng <= SPOKANE_METRO_BBOX["max_lng"]
    )


SPOKANE_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Riverfront": SubmarketMeta(
        name="Downtown & Riverfront", borough="SPOKANE_CORE", lat=47.6588, lng=-117.4260,
        zoom=13.2, pitch=46.0, base_lims=0.83, capex=6500000.0, permit_vel=33.0,
        shift_ratio=1.39, sla=55.0,
        description="Civic core and riverfront with adaptive reuse, hospitality, and mixed-use infill.",
        city_id="spokane",
    ),
    "South Hill": SubmarketMeta(
        name="South Hill", borough="SPOKANE_CORE", lat=47.6280, lng=-117.3850,
        zoom=12.8, pitch=43.0, base_lims=0.79, capex=5600000.0, permit_vel=29.0,
        shift_ratio=1.35, sla=53.0,
        description="Established hillside neighborhoods with residential rehabilitation and neighborhood retail investment.",
        city_id="spokane",
    ),
    "North Spokane": SubmarketMeta(
        name="North Spokane", borough="SPOKANE_CORE", lat=47.7300, lng=-117.4100,
        zoom=12.7, pitch=42.0, base_lims=0.78, capex=6000000.0, permit_vel=31.0,
        shift_ratio=1.37, sla=54.0,
        description="North-side commercial and residential corridor with infill, services, and growth pressure.",
        city_id="spokane",
    ),
    "Spokane Valley": SubmarketMeta(
        name="Spokane Valley", borough="SPOKANE_CORE", lat=47.6732, lng=-117.2394,
        zoom=12.5, pitch=41.0, base_lims=0.80, capex=6800000.0, permit_vel=35.0,
        shift_ratio=1.41, sla=55.0,
        description="East-valley growth corridor with commercial expansion, housing delivery, and parcel turnover.",
        city_id="spokane",
    ),
    "Airway Heights / West Plains": SubmarketMeta(
        name="Airway Heights / West Plains", borough="SPOKANE_CORE", lat=47.6450, lng=-117.5600,
        zoom=12.2, pitch=39.0, base_lims=0.76, capex=5900000.0, permit_vel=30.0,
        shift_ratio=1.34, sla=52.0,
        description="West Plains logistics and airport-adjacent growth area with new construction and industrial expansion.",
        city_id="spokane",
    ),
}


SPOKANE_DIVISIONS: dict[str, BoroughMeta] = {
    "SPOKANE_CORE": BoroughMeta(
        name="Spokane / Spokane County", center_lat=47.6588, center_lng=-117.4260, zoom=10.8,
        bbox=SPOKANE_DIVISION_BBOXES["SPOKANE_CORE"], submarkets=list(SPOKANE_SUBMARKETS),
        city_id="spokane",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=SPOKANE_METRO_BBOX,
    division_bboxes=SPOKANE_DIVISION_BBOXES,
    submarkets=SPOKANE_SUBMARKETS,
    divisions=SPOKANE_DIVISIONS,
    contains=is_in_spokane_metro,
)
