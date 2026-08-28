"""Ocala / Marion County, Florida spatial registry and geometry (US-297)."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Marion County envelope (approximate; bounded tightly around metro activity)
OCALA_METRO_BBOX: dict[str, float] = {
    "min_lat": 28.95,
    "max_lat": 29.45,
    "min_lng": -82.45,
    "max_lng": -81.95,
}

# One core division capturing the Ocala urban area and near corridors
OCALA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "OCALA_CORE": {
        "min_lat": 29.08,
        "max_lat": 29.28,
        "min_lng": -82.22,
        "max_lng": -82.02,
    },
}


def is_in_ocala_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the Ocala metro extent."""
    if lat is None or lng is None:
        return False
    return (
        OCALA_METRO_BBOX["min_lat"] <= lat <= OCALA_METRO_BBOX["max_lat"]
        and OCALA_METRO_BBOX["min_lng"] <= lng <= OCALA_METRO_BBOX["max_lng"]
    )


OCALA_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown Ocala": SubmarketMeta(
        name="Downtown Ocala",
        borough="OCALA_CORE",
        lat=29.1872,
        lng=-82.1401,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.80,
        capex=5200000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=50.0,
        description="Historic courthouse square and Magnolia Ave corridor with mixed-use infill and neighborhood services.",
        city_id="ocala",
    ),
    "West Ocala": SubmarketMeta(
        name="West Ocala",
        borough="OCALA_CORE",
        lat=29.185,
        lng=-82.180,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.72,
        capex=4100000.0,
        permit_vel=24.0,
        shift_ratio=1.24,
        sla=44.0,
        description="Residential and commercial reinvestment west of US‑441 with corridor retail and small‑lot rehab.",
        city_id="ocala",
    ),
    "Silver Springs": SubmarketMeta(
        name="Silver Springs",
        borough="OCALA_CORE",
        lat=29.216,
        lng=-82.059,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.74,
        capex=4300000.0,
        permit_vel=25.0,
        shift_ratio=1.26,
        sla=46.0,
        description="East‑side gateway anchored by Silver Springs State Park and commercial corridors along SR‑40.",
        city_id="ocala",
    ),
    "Southeast Ocala": SubmarketMeta(
        name="Southeast Ocala",
        borough="OCALA_CORE",
        lat=29.150,
        lng=-82.120,
        zoom=12.8,
        pitch=40.0,
        base_lims=0.71,
        capex=3900000.0,
        permit_vel=23.0,
        shift_ratio=1.22,
        sla=43.0,
        description="Established neighborhoods and medical/office clusters southeast of downtown with steady renovation.",
        city_id="ocala",
    ),
    "Northeast Ocala": SubmarketMeta(
        name="Northeast Ocala",
        borough="OCALA_CORE",
        lat=29.230,
        lng=-82.120,
        zoom=12.8,
        pitch=40.0,
        base_lims=0.70,
        capex=3800000.0,
        permit_vel=22.0,
        shift_ratio=1.20,
        sla=42.0,
        description="Northeast residential districts and neighborhood retail along NE 36th Ave and Bonnie Heath Blvd.",
        city_id="ocala",
    ),
}


OCALA_DIVISIONS: dict[str, BoroughMeta] = {
    "OCALA_CORE": BoroughMeta(
        name="Ocala / Marion County",
        center_lat=29.1872,
        center_lng=-82.1401,
        zoom=11.2,
        bbox=OCALA_DIVISION_BBOXES["OCALA_CORE"],
        submarkets=list(OCALA_SUBMARKETS),
        city_id="ocala",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=OCALA_METRO_BBOX,
    division_bboxes=OCALA_DIVISION_BBOXES,
    submarkets=OCALA_SUBMARKETS,
    divisions=OCALA_DIVISIONS,
    contains=is_in_ocala_metro,
)

