"""Baltimore, Maryland spatial registry and dashboard geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

BALTIMORE_METRO_BBOX: dict[str, float] = {
    "min_lat": 39.15,
    "max_lat": 39.75,
    "min_lng": -76.85,
    "max_lng": -76.25,
}

BALTIMORE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "BALTIMORE_CORE": {
        "min_lat": 39.20,
        "max_lat": 39.45,
        "min_lng": -76.75,
        "max_lng": -76.45,
    },
}


def is_in_baltimore_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Baltimore extent."""
    if lat is None or lng is None:
        return False
    return (
        BALTIMORE_METRO_BBOX["min_lat"] <= lat <= BALTIMORE_METRO_BBOX["max_lat"]
        and BALTIMORE_METRO_BBOX["min_lng"] <= lng <= BALTIMORE_METRO_BBOX["max_lng"]
    )


BALTIMORE_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Inner Harbor": SubmarketMeta(
        name="Downtown & Inner Harbor", borough="BALTIMORE_CORE", lat=39.287, lng=-76.612,
        zoom=13.4, pitch=48.0, base_lims=0.82, capex=7200000.0, permit_vel=38.0,
        shift_ratio=1.44, sla=58.0,
        description="Downtown, Inner Harbor, and waterfront redevelopment corridor.", city_id="baltimore",
    ),
    "Fells Point & Canton": SubmarketMeta(
        name="Fells Point & Canton", borough="BALTIMORE_CORE", lat=39.282, lng=-76.580,
        zoom=13.4, pitch=46.0, base_lims=0.80, capex=6100000.0, permit_vel=34.0,
        shift_ratio=1.40, sla=55.0,
        description="Historic waterfront neighborhoods with residential and hospitality investment.", city_id="baltimore",
    ),
    "Mount Vernon & Bolton Hill": SubmarketMeta(
        name="Mount Vernon & Bolton Hill", borough="BALTIMORE_CORE", lat=39.305, lng=-76.620,
        zoom=13.4, pitch=45.0, base_lims=0.76, capex=5200000.0, permit_vel=29.0,
        shift_ratio=1.36, sla=52.0,
        description="Historic central neighborhoods with adaptive reuse and institutional demand.", city_id="baltimore",
    ),
    "North Baltimore": SubmarketMeta(
        name="North Baltimore", borough="BALTIMORE_CORE", lat=39.345, lng=-76.625,
        zoom=12.8, pitch=43.0, base_lims=0.72, capex=4600000.0, permit_vel=25.0,
        shift_ratio=1.32, sla=50.0,
        description="North-side residential and education corridor with steady permit activity.", city_id="baltimore",
    ),
}

BALTIMORE_DIVISIONS: dict[str, BoroughMeta] = {
    "BALTIMORE_CORE": BoroughMeta(
        name="Baltimore Core", center_lat=39.290, center_lng=-76.612, zoom=11.8,
        bbox=BALTIMORE_DIVISION_BBOXES["BALTIMORE_CORE"],
        submarkets=list(BALTIMORE_SUBMARKETS), city_id="baltimore",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=BALTIMORE_METRO_BBOX,
    division_bboxes=BALTIMORE_DIVISION_BBOXES,
    submarkets=BALTIMORE_SUBMARKETS,
    divisions=BALTIMORE_DIVISIONS,
    contains=is_in_baltimore_metro,
)
