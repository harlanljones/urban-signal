"""Dayton / Montgomery County, Ohio spatial registry and geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

DAYTON_METRO_BBOX: dict[str, float] = {
    "min_lat": 39.55,
    "max_lat": 40.05,
    "min_lng": -84.65,
    "max_lng": -83.65,
}

DAYTON_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DAYTON_CORE": {
        "min_lat": 39.65,
        "max_lat": 39.95,
        "min_lng": -84.45,
        "max_lng": -83.95,
    },
}


def is_in_dayton_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the Dayton metro extent."""
    if lat is None or lng is None:
        return False
    return (
        DAYTON_METRO_BBOX["min_lat"] <= lat <= DAYTON_METRO_BBOX["max_lat"]
        and DAYTON_METRO_BBOX["min_lng"] <= lng <= DAYTON_METRO_BBOX["max_lng"]
    )


DAYTON_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Oregon District": SubmarketMeta(
        name="Downtown & Oregon District", borough="DAYTON_CORE", lat=39.7589, lng=-84.1916,
        zoom=13.2, pitch=46.0, base_lims=0.82, capex=6100000.0, permit_vel=32.0,
        shift_ratio=1.38, sla=54.0,
        description="Civic core and historic entertainment district with adaptive reuse, infill, and riverfront investment.",
        city_id="dayton",
    ),
    "South Dayton": SubmarketMeta(
        name="South Dayton", borough="DAYTON_CORE", lat=39.7250, lng=-84.1900,
        zoom=12.8, pitch=43.0, base_lims=0.78, capex=5200000.0, permit_vel=28.0,
        shift_ratio=1.34, sla=52.0,
        description="South-side neighborhoods with rehabilitation, neighborhood services, and small-scale redevelopment.",
        city_id="dayton",
    ),
    "North Dayton": SubmarketMeta(
        name="North Dayton", borough="DAYTON_CORE", lat=39.8050, lng=-84.1900,
        zoom=12.7, pitch=42.0, base_lims=0.76, capex=4800000.0, permit_vel=27.0,
        shift_ratio=1.33, sla=51.0,
        description="North-side residential and industrial corridor with reinvestment and service-oriented change.",
        city_id="dayton",
    ),
    "Kettering / Oakwood": SubmarketMeta(
        name="Kettering / Oakwood", borough="DAYTON_CORE", lat=39.6950, lng=-84.1680,
        zoom=12.5, pitch=41.0, base_lims=0.79, capex=5700000.0, permit_vel=30.0,
        shift_ratio=1.36, sla=53.0,
        description="Mature south-county communities with renovation, medical, and neighborhood retail activity.",
        city_id="dayton",
    ),
    "Huber Heights / North Corridor": SubmarketMeta(
        name="Huber Heights / North Corridor", borough="DAYTON_CORE", lat=39.8550, lng=-84.1100,
        zoom=12.3, pitch=40.0, base_lims=0.77, capex=5900000.0, permit_vel=31.0,
        shift_ratio=1.35, sla=52.0,
        description="Northeast growth corridor with commercial services, housing turnover, and suburban intensification.",
        city_id="dayton",
    ),
}


DAYTON_DIVISIONS: dict[str, BoroughMeta] = {
    "DAYTON_CORE": BoroughMeta(
        name="Dayton / Montgomery County", center_lat=39.7589, center_lng=-84.1916, zoom=10.8,
        bbox=DAYTON_DIVISION_BBOXES["DAYTON_CORE"], submarkets=list(DAYTON_SUBMARKETS),
        city_id="dayton",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=DAYTON_METRO_BBOX,
    division_bboxes=DAYTON_DIVISION_BBOXES,
    submarkets=DAYTON_SUBMARKETS,
    divisions=DAYTON_DIVISIONS,
    contains=is_in_dayton_metro,
)
