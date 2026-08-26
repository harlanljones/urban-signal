"""Hartford / Greater Hartford spatial registry and geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

HARTFORD_METRO_BBOX: dict[str, float] = {
    "min_lat": 41.55,
    "max_lat": 42.05,
    "min_lng": -73.00,
    "max_lng": -72.35,
}

HARTFORD_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "HARTFORD_CORE": {
        "min_lat": 41.65,
        "max_lat": 41.90,
        "min_lng": -72.85,
        "max_lng": -72.50,
    },
}


def is_in_hartford_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Hartford extent."""
    if lat is None or lng is None:
        return False
    return (
        HARTFORD_METRO_BBOX["min_lat"] <= lat <= HARTFORD_METRO_BBOX["max_lat"]
        and HARTFORD_METRO_BBOX["min_lng"] <= lng <= HARTFORD_METRO_BBOX["max_lng"]
    )


HARTFORD_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Sheldon-Charter Oak": SubmarketMeta(
        name="Downtown & Sheldon-Charter Oak", borough="HARTFORD_CORE", lat=41.7637, lng=-72.6734,
        zoom=13.4, pitch=48.0, base_lims=0.84, capex=6800000.0, permit_vel=35.0,
        shift_ratio=1.42, sla=57.0,
        description="Civic center and river-adjacent neighborhoods with institutional, hospitality, and adaptive-reuse activity.",
        city_id="hartford",
    ),
    "Asylum Hill & West End": SubmarketMeta(
        name="Asylum Hill & West End", borough="HARTFORD_CORE", lat=41.7737, lng=-72.7010,
        zoom=13.1, pitch=44.0, base_lims=0.81, capex=5200000.0, permit_vel=29.0,
        shift_ratio=1.37, sla=55.0,
        description="Historic residential and medical corridor with rehabilitation, neighborhood retail, and institutional demand.",
        city_id="hartford",
    ),
    "Frog Hollow & Parkville": SubmarketMeta(
        name="Frog Hollow & Parkville", borough="HARTFORD_CORE", lat=41.7520, lng=-72.7080,
        zoom=13.0, pitch=44.0, base_lims=0.79, capex=4600000.0, permit_vel=31.0,
        shift_ratio=1.39, sla=54.0,
        description="West-side mixed residential and industrial transition zone with infill and small-business reinvestment.",
        city_id="hartford",
    ),
    "South End & Barry Square": SubmarketMeta(
        name="South End & Barry Square", borough="HARTFORD_CORE", lat=41.7350, lng=-72.6800,
        zoom=12.9, pitch=42.0, base_lims=0.76, capex=3900000.0, permit_vel=26.0,
        shift_ratio=1.34, sla=52.0,
        description="South Hartford neighborhoods combining legacy housing stock, local commerce, and corridor-scale redevelopment.",
        city_id="hartford",
    ),
    "North Meadows & Blue Hills": SubmarketMeta(
        name="North Meadows & Blue Hills", borough="HARTFORD_CORE", lat=41.8000, lng=-72.6700,
        zoom=12.8, pitch=42.0, base_lims=0.74, capex=4300000.0, permit_vel=24.0,
        shift_ratio=1.32, sla=51.0,
        description="North-side employment and residential edge with logistics, neighborhood services, and public-realm investment.",
        city_id="hartford",
    ),
}


HARTFORD_DIVISIONS: dict[str, BoroughMeta] = {
    "HARTFORD_CORE": BoroughMeta(
        name="Hartford Core", center_lat=41.7637, center_lng=-72.6734, zoom=11.8,
        bbox=HARTFORD_DIVISION_BBOXES["HARTFORD_CORE"], submarkets=list(HARTFORD_SUBMARKETS),
        city_id="hartford",
    ),
}
