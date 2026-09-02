"""Evansville / Vanderburgh County, Indiana spatial registry and geometry.

Evansville is the seat of Vanderburgh County on the Ohio River in southwest
Indiana. US-425 registers the Building Commission Permits layer hosted on the
Evansville/Vanderburgh County GIS Hub (maps.evansvillegis.com) plus USDA SNAP
SLA coverage. The metro bbox covers the city proper and Vanderburgh County's
urbanized area.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

EVANSVILLE_METRO_BBOX: dict[str, float] = {
    "min_lat": 37.80,
    "max_lat": 38.15,
    "min_lng": -87.75,
    "max_lng": -87.35,
}

EVANSVILLE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "EVANSVILLE_CORE": {
        "min_lat": 37.86,
        "max_lat": 38.10,
        "min_lng": -87.70,
        "max_lng": -87.38,
    },
}


def is_in_evansville_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Evansville extent."""
    if lat is None or lng is None:
        return False
    return (
        EVANSVILLE_METRO_BBOX["min_lat"] <= lat <= EVANSVILLE_METRO_BBOX["max_lat"]
        and EVANSVILLE_METRO_BBOX["min_lng"] <= lng <= EVANSVILLE_METRO_BBOX["max_lng"]
    )


EVANSVILLE_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown Evansville": SubmarketMeta(
        name="Downtown Evansville",
        borough="EVANSVILLE_CORE",
        lat=37.9716,
        lng=-87.5711,
        zoom=13.6,
        pitch=48.0,
        base_lims=0.82,
        capex=5600000.0,
        permit_vel=30.0,
        shift_ratio=1.36,
        sla=54.0,
        description="Ohio River waterfront civic core with office conversions, riverfront investment, and downtown housing.",
        city_id="evansville",
    ),
    "East Side": SubmarketMeta(
        name="East Side",
        borough="EVANSVILLE_CORE",
        lat=37.9700,
        lng=-87.5200,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.78,
        capex=4800000.0,
        permit_vel=27.0,
        shift_ratio=1.32,
        sla=51.0,
        description="East-side residential and commercial belt anchored by Eastland Mall and Green River Road retail.",
        city_id="evansville",
    ),
    "West Side": SubmarketMeta(
        name="West Side",
        borough="EVANSVILLE_CORE",
        lat=37.9800,
        lng=-87.6300,
        zoom=12.9,
        pitch=41.0,
        base_lims=0.75,
        capex=4200000.0,
        permit_vel=25.0,
        shift_ratio=1.30,
        sla=49.0,
        description="West-side neighborhoods with housing rehabilitation and industrial-commercial corridor reinvestment.",
        city_id="evansville",
    ),
    "Newburgh & East Corridor": SubmarketMeta(
        name="Newburgh & East Corridor",
        borough="EVANSVILLE_CORE",
        lat=37.9200,
        lng=-87.4000,
        zoom=12.4,
        pitch=39.0,
        base_lims=0.76,
        capex=4400000.0,
        permit_vel=25.0,
        shift_ratio=1.30,
        sla=50.0,
        description="River-adjacent growth corridor toward Newburgh with newer subdivisions and regional retail.",
        city_id="evansville",
    ),
}

EVANSVILLE_DIVISIONS: dict[str, BoroughMeta] = {
    "EVANSVILLE_CORE": BoroughMeta(
        name="Evansville Core",
        center_lat=37.9716,
        center_lng=-87.5711,
        zoom=11.6,
        bbox=EVANSVILLE_DIVISION_BBOXES["EVANSVILLE_CORE"],
        submarkets=list(EVANSVILLE_SUBMARKETS),
        city_id="evansville",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=EVANSVILLE_METRO_BBOX,
    division_bboxes=EVANSVILLE_DIVISION_BBOXES,
    submarkets=EVANSVILLE_SUBMARKETS,
    divisions=EVANSVILLE_DIVISIONS,
    contains=is_in_evansville_metro,
)
