"""Pierce County, Washington spatial registry and dashboard geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Layer extent (WGS84) for the permits/application FeatureServer, incl. the
# full county including the eastern Rainier-adjacent area.
PIERCE_METRO_BBOX: dict[str, float] = {
    "min_lat": 46.73,
    "max_lat": 47.42,
    "min_lng": -122.85,
    "max_lng": -121.46,
}

# Population corridor: Tacoma + Puyallup + south-sound communities, nested
# inside the metro bbox per the interlock containment invariant.
PIERCE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "PIERCE_COUNTY": {
        "min_lat": 46.90,
        "max_lat": 47.40,
        "min_lng": -122.85,
        "max_lng": -121.90,
    },
}


def is_in_pierce_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Pierce County extent."""
    if lat is None or lng is None:
        return False
    return (
        PIERCE_METRO_BBOX["min_lat"] <= lat <= PIERCE_METRO_BBOX["max_lat"]
        and PIERCE_METRO_BBOX["min_lng"] <= lng <= PIERCE_METRO_BBOX["max_lng"]
    )


PIERCE_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Tacoma Downtown & Waterfront": SubmarketMeta(
        name="Tacoma Downtown & Waterfront",
        borough="PIERCE_COUNTY",
        lat=47.2529,
        lng=-122.4443,
        zoom=12.4,
        pitch=48.0,
        base_lims=0.84,
        capex=9500000.0,
        permit_vel=42.0,
        shift_ratio=1.42,
        sla=58.0,
        description="County seat and port-city core with office conversions, waterfront redevelopment, and high-density residential demand.",
        city_id="pierce",
    ),
    "Puyallup Valley": SubmarketMeta(
        name="Puyallup Valley",
        borough="PIERCE_COUNTY",
        lat=47.1854,
        lng=-122.2929,
        zoom=12.2,
        pitch=46.0,
        base_lims=0.82,
        capex=7200000.0,
        permit_vel=36.0,
        shift_ratio=1.38,
        sla=54.0,
        description="Puyallup and South Hill growth corridor anchored by the fairgrounds district with steady single-family and multifamily infill.",
        city_id="pierce",
    ),
    "Lakewood & Steilacoom": SubmarketMeta(
        name="Lakewood & Steilacoom",
        borough="PIERCE_COUNTY",
        lat=47.1718,
        lng=-122.5185,
        zoom=12.0,
        pitch=44.0,
        base_lims=0.79,
        capex=6400000.0,
        permit_vel=31.0,
        shift_ratio=1.35,
        sla=52.0,
        description="Western county bedroom communities along I-5 with commercial redevelopment and military-adjacent housing demand.",
        city_id="pierce",
    ),
    "Gig Harbor & Key Peninsula": SubmarketMeta(
        name="Gig Harbor & Key Peninsula",
        borough="PIERCE_COUNTY",
        lat=47.3265,
        lng=-122.5860,
        zoom=12.0,
        pitch=44.0,
        base_lims=0.80,
        capex=6900000.0,
        permit_vel=33.0,
        shift_ratio=1.36,
        sla=53.0,
        description="Harbor and peninsula communities with waterfront residential construction and commercial infill along Highway 16.",
        city_id="pierce",
    ),
    "South Hill & Graham": SubmarketMeta(
        name="South Hill & Graham",
        borough="PIERCE_COUNTY",
        lat=47.1265,
        lng=-122.2985,
        zoom=12.0,
        pitch=42.0,
        base_lims=0.78,
        capex=5800000.0,
        permit_vel=34.0,
        shift_ratio=1.34,
        sla=50.0,
        description="Fast-growing southern plateau subdivisions where new-structure residential permits dominate the county mix.",
        city_id="pierce",
    ),
    "Sumner & Bonney Lake": SubmarketMeta(
        name="Sumner & Bonney Lake",
        borough="PIERCE_COUNTY",
        lat=47.2032,
        lng=-122.2401,
        zoom=12.0,
        pitch=42.0,
        base_lims=0.77,
        capex=5500000.0,
        permit_vel=32.0,
        shift_ratio=1.33,
        sla=50.0,
        description="East Pierce river-valley and lakeside corridor with distribution-window commercial growth and active residential subdivisions.",
        city_id="pierce",
    ),
}

PIERCE_DIVISIONS: dict[str, BoroughMeta] = {
    "PIERCE_COUNTY": BoroughMeta(
        name="Pierce County",
        center_lat=47.2529,
        center_lng=-122.4443,
        zoom=10.0,
        bbox=PIERCE_DIVISION_BBOXES["PIERCE_COUNTY"],
        submarkets=list(PIERCE_SUBMARKETS),
        city_id="pierce",
    ),
}

from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=PIERCE_METRO_BBOX,
    division_bboxes=PIERCE_DIVISION_BBOXES,
    submarkets=PIERCE_SUBMARKETS,
    divisions=PIERCE_DIVISIONS,
    contains=is_in_pierce_metro,
)
