"""Madison, Wisconsin spatial registration and Accela feed contract."""

from src.spatial.registration import SpatialRegistration
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MADISON_METRO_BBOX: dict[str, float] = {
    "min_lat": 42.90,
    "max_lat": 43.25,
    "min_lng": -89.65,
    "max_lng": -89.15,
}

MADISON_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "MADISON_CORE": {
        "min_lat": 42.95,
        "max_lat": 43.18,
        "min_lng": -89.55,
        "max_lng": -89.25,
    },
}


def is_in_madison_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the Madison metro extent."""
    if lat is None or lng is None:
        return False
    return (
        MADISON_METRO_BBOX["min_lat"] <= lat <= MADISON_METRO_BBOX["max_lat"]
        and MADISON_METRO_BBOX["min_lng"] <= lng <= MADISON_METRO_BBOX["max_lng"]
    )


MADISON_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Capitol": SubmarketMeta(
        name="Downtown & Capitol", borough="MADISON_CORE", lat=43.0747, lng=-89.3844,
        zoom=13.2, pitch=46.0, base_lims=0.84, capex=6200000.0, permit_vel=31.0,
        shift_ratio=1.38, sla=57.0,
        description="State Street, Capitol Square, and the downtown lakefront civic and mixed-use core.",
        city_id="madison",
    ),
    "Near West": SubmarketMeta(
        name="Near West", borough="MADISON_CORE", lat=43.0612, lng=-89.4335,
        zoom=12.8, pitch=43.0, base_lims=0.79, capex=5100000.0, permit_vel=27.0,
        shift_ratio=1.34, sla=54.0,
        description="University-adjacent neighborhoods and established commercial corridors west of downtown.",
        city_id="madison",
    ),
    "Near East & Atwood": SubmarketMeta(
        name="Near East & Atwood", borough="MADISON_CORE", lat=43.0898, lng=-89.3472,
        zoom=13.0, pitch=44.0, base_lims=0.81, capex=5400000.0, permit_vel=29.0,
        shift_ratio=1.36, sla=55.0,
        description="Atwood and Williamson Street corridors with neighborhood retail and adaptive reuse.",
        city_id="madison",
    ),
    "South Madison": SubmarketMeta(
        name="South Madison", borough="MADISON_CORE", lat=43.0334, lng=-89.3848,
        zoom=12.8, pitch=42.0, base_lims=0.77, capex=4700000.0, permit_vel=25.0,
        shift_ratio=1.31, sla=52.0,
        description="South-side reinvestment and redevelopment corridors linking the central city to suburban growth.",
        city_id="madison",
    ),
    "West Beltline": SubmarketMeta(
        name="West Beltline", borough="MADISON_CORE", lat=43.0520, lng=-89.5050,
        zoom=12.6, pitch=40.0, base_lims=0.75, capex=4300000.0, permit_vel=23.0,
        shift_ratio=1.29, sla=51.0,
        description="Employment, retail, and residential growth nodes along Madison's western Beltline edge.",
        city_id="madison",
    ),
}

MADISON_DIVISIONS: dict[str, BoroughMeta] = {
    "MADISON_CORE": BoroughMeta(
        name="Madison", center_lat=43.0747, center_lng=-89.3844, zoom=11.5,
        bbox=MADISON_DIVISION_BBOXES["MADISON_CORE"],
        submarkets=list(MADISON_SUBMARKETS), city_id="madison",
    ),
}

# Accela Citizen Access is Madison's authoritative permitting surface. The
# shared Accela client handles its JSON/REST pagination; keeping the mapping in
# this leaf lets Grand Rapids reuse the client without sharing Madison fields.
MADISON_PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["RecordID", "RecordNumber", "B1_ALT_ID", "permit_number"],
    "address_street": ["Address", "SITE_ADDRESS", "address"],
    "issuance_date": ["IssuedDate", "ISSUED_DT", "issued_date"],
    "filing_date": ["OpenedDate", "CREATE_DT", "created_date"],
    "job_type": ["RecordType", "PERMIT_TYPE", "permit_type"],
    "cost": ["TotalJobCost", "JOBVALUE", "estimated_cost"],
    "latitude": ["Latitude", "latitude"],
    "longitude": ["Longitude", "longitude"],
}

MADISON_PERMITS_ENDPOINT = "https://aca-prod.accela.com/MADISON/Cap/CapHome.aspx"

REGISTRATION = SpatialRegistration(
    metro_bbox=MADISON_METRO_BBOX,
    division_bboxes=MADISON_DIVISION_BBOXES,
    submarkets=MADISON_SUBMARKETS,
    divisions=MADISON_DIVISIONS,
    contains=is_in_madison_metro,
)
