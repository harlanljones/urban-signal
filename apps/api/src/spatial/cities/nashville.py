"""Nashville / Davidson County, Tennessee spatial registry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

NASHVILLE_METRO_BBOX: dict[str, float] = {
    "min_lat": 35.94,
    "max_lat": 36.44,
    "min_lng": -87.16,
    "max_lng": -86.46,
}

NASHVILLE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "NASHVILLE_CORE": {
        "min_lat": 35.98,
        "max_lat": 36.40,
        "min_lng": -87.10,
        "max_lng": -86.50,
    },
}


def is_in_nashville_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered county extent."""
    if lat is None or lng is None:
        return False
    return (
        NASHVILLE_METRO_BBOX["min_lat"] <= lat <= NASHVILLE_METRO_BBOX["max_lat"]
        and NASHVILLE_METRO_BBOX["min_lng"] <= lng <= NASHVILLE_METRO_BBOX["max_lng"]
    )


NASHVILLE_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Riverfront": SubmarketMeta(
        name="Downtown & Riverfront",
        borough="NASHVILLE_CORE",
        lat=36.1612,
        lng=-86.7775,
        zoom=13.8,
        pitch=50.0,
        base_lims=0.86,
        capex=7900000.0,
        permit_vel=40.0,
        shift_ratio=1.48,
        sla=61.0,
        description="Cumberland River core spanning Broadway honky-tonk blocks, the East Bank stadium district, "
        "and high-rise hotel and multifamily redevelopment.",
        city_id="nashville",
    ),
    "The Gulch & Midtown": SubmarketMeta(
        name="The Gulch & Midtown",
        borough="NASHVILLE_CORE",
        lat=36.1500,
        lng=-86.8000,
        zoom=13.6,
        pitch=48.0,
        base_lims=0.85,
        capex=7200000.0,
        permit_vel=38.0,
        shift_ratio=1.45,
        sla=59.0,
        description="Transit-adjacent mixed-use corridor between the Gulch towers, Music Row, and the "
        "Vanderbilt-adjacent Midtown bar and residential strip.",
        city_id="nashville",
    ),
    "East Nashville & Five Points": SubmarketMeta(
        name="East Nashville & Five Points",
        borough="NASHVILLE_CORE",
        lat=36.1800,
        lng=-86.7510,
        zoom=13.4,
        pitch=46.0,
        base_lims=0.82,
        capex=5500000.0,
        permit_vel=33.0,
        shift_ratio=1.41,
        sla=56.0,
        description="River-east bungalow neighborhoods anchored by the Five Points commercial node with steady "
        "residential infill and renovation demand.",
        city_id="nashville",
    ),
    "Belmont & Hillsboro Village": SubmarketMeta(
        name="Belmont & Hillsboro Village",
        borough="NASHVILLE_CORE",
        lat=36.1285,
        lng=-86.8010,
        zoom=13.4,
        pitch=46.0,
        base_lims=0.83,
        capex=5200000.0,
        permit_vel=31.0,
        shift_ratio=1.39,
        sla=55.0,
        description="University-district market between Belmont and Vanderbilt campuses with student rental "
        "demand, retail frontage, and older-stock renovation.",
        city_id="nashville",
    ),
    "Antioch & Southeast Corridor": SubmarketMeta(
        name="Antioch & Southeast Corridor",
        borough="NASHVILLE_CORE",
        lat=36.0545,
        lng=-86.6010,
        zoom=12.8,
        pitch=44.0,
        base_lims=0.76,
        capex=4300000.0,
        permit_vel=27.0,
        shift_ratio=1.34,
        sla=52.0,
        description="Southeast Davidson growth belt along Antioch Pike and the Cullum/Percy Priest corridors with "
        "townhome and big-box repositioning activity.",
        city_id="nashville",
    ),
}

NASHVILLE_DIVISIONS: dict[str, BoroughMeta] = {
    "NASHVILLE_CORE": BoroughMeta(
        name="Davidson County",
        center_lat=36.1627,
        center_lng=-86.7818,
        zoom=10.8,
        bbox=NASHVILLE_DIVISION_BBOXES["NASHVILLE_CORE"],
        submarkets=list(NASHVILLE_SUBMARKETS),
        city_id="nashville",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=NASHVILLE_METRO_BBOX,
    division_bboxes=NASHVILLE_DIVISION_BBOXES,
    submarkets=NASHVILLE_SUBMARKETS,
    divisions=NASHVILLE_DIVISIONS,
    contains=is_in_nashville_metro,
)
