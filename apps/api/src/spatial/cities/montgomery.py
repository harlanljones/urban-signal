"""Montgomery County, Maryland spatial registry and dashboard geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MONTGOMERY_METRO_BBOX: dict[str, float] = {
    "min_lat": 38.90, "max_lat": 39.35, "min_lng": -77.60, "max_lng": -76.80,
}
MONTGOMERY_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "MONTGOMERY_CORE": {"min_lat": 38.98, "max_lat": 39.30, "min_lng": -77.45, "max_lng": -77.00},
}


def is_in_montgomery_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside Montgomery County's extent."""
    if lat is None or lng is None:
        return False
    return (
        MONTGOMERY_METRO_BBOX["min_lat"] <= lat <= MONTGOMERY_METRO_BBOX["max_lat"]
        and MONTGOMERY_METRO_BBOX["min_lng"] <= lng <= MONTGOMERY_METRO_BBOX["max_lng"]
    )


MONTGOMERY_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Bethesda & Friendship Heights": SubmarketMeta(
        name="Bethesda & Friendship Heights", borough="MONTGOMERY_CORE", lat=38.995, lng=-77.095,
        zoom=12.8, pitch=45.0, base_lims=0.82, capex=7200000.0, permit_vel=34.0, shift_ratio=1.40, sla=55.0,
        description="Dense urban and mixed-use corridor along the District boundary.", city_id="montgomery",
    ),
    "Rockville & Gaithersburg": SubmarketMeta(
        name="Rockville & Gaithersburg", borough="MONTGOMERY_CORE", lat=39.120, lng=-77.190,
        zoom=11.8, pitch=43.0, base_lims=0.78, capex=6100000.0, permit_vel=38.0, shift_ratio=1.36, sla=52.0,
        description="County employment and civic center with sustained permit activity.", city_id="montgomery",
    ),
    "Silver Spring & Wheaton": SubmarketMeta(
        name="Silver Spring & Wheaton", borough="MONTGOMERY_CORE", lat=39.045, lng=-77.045,
        zoom=12.2, pitch=44.0, base_lims=0.76, capex=5400000.0, permit_vel=31.0, shift_ratio=1.34, sla=50.0,
        description="Transit-oriented inner-county neighborhoods with redevelopment pressure.", city_id="montgomery",
    ),
    "Upcounty": SubmarketMeta(
        name="Upcounty", borough="MONTGOMERY_CORE", lat=39.235, lng=-77.300,
        zoom=11.2, pitch=40.0, base_lims=0.70, capex=4300000.0, permit_vel=26.0, shift_ratio=1.28, sla=46.0,
        description="Growing northern county communities and lower-density development belt.", city_id="montgomery",
    ),
}

MONTGOMERY_DIVISIONS: dict[str, BoroughMeta] = {
    "MONTGOMERY_CORE": BoroughMeta(
        name="Montgomery County", center_lat=39.140, center_lng=-77.190, zoom=10.8,
        bbox=MONTGOMERY_DIVISION_BBOXES["MONTGOMERY_CORE"], submarkets=list(MONTGOMERY_SUBMARKETS), city_id="montgomery",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=MONTGOMERY_METRO_BBOX,
    division_bboxes=MONTGOMERY_DIVISION_BBOXES,
    submarkets=MONTGOMERY_SUBMARKETS,
    divisions=MONTGOMERY_DIVISIONS,
    contains=is_in_montgomery_metro,
)
