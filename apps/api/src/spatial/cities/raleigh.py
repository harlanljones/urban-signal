"""Raleigh / Wake County, North Carolina spatial registry and geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

RALEIGH_METRO_BBOX: dict[str, float] = {
    "min_lat": 35.40,
    "max_lat": 36.15,
    "min_lng": -79.50,
    "max_lng": -78.00,
}

RALEIGH_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "RALEIGH_CORE": {
        "min_lat": 35.65,
        "max_lat": 36.00,
        "min_lng": -79.00,
        "max_lng": -78.40,
    },
}


def is_in_raleigh_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Raleigh extent."""
    if lat is None or lng is None:
        return False
    return (
        RALEIGH_METRO_BBOX["min_lat"] <= lat <= RALEIGH_METRO_BBOX["max_lat"]
        and RALEIGH_METRO_BBOX["min_lng"] <= lng <= RALEIGH_METRO_BBOX["max_lng"]
    )


RALEIGH_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Warehouse District": SubmarketMeta(
        name="Downtown & Warehouse District", borough="RALEIGH_CORE", lat=35.7796, lng=-78.6382,
        zoom=13.4, pitch=48.0, base_lims=0.85, capex=8900000.0, permit_vel=42.0,
        shift_ratio=1.44, sla=59.0,
        description="State-capital core and warehouse edge with office, residential, hospitality, and public-realm investment.",
        city_id="raleigh",
    ),
    "North Hills & Midtown": SubmarketMeta(
        name="North Hills & Midtown", borough="RALEIGH_CORE", lat=35.8370, lng=-78.6400,
        zoom=13.1, pitch=44.0, base_lims=0.83, capex=7600000.0, permit_vel=39.0,
        shift_ratio=1.42, sla=58.0,
        description="North-side mixed-use and employment corridor with multifamily, retail, and transit-oriented redevelopment.",
        city_id="raleigh",
    ),
    "Five Points & Village District": SubmarketMeta(
        name="Five Points & Village District", borough="RALEIGH_CORE", lat=35.8070, lng=-78.6530,
        zoom=13.0, pitch=44.0, base_lims=0.80, capex=6100000.0, permit_vel=33.0,
        shift_ratio=1.39, sla=56.0,
        description="Established inner-ring neighborhoods with storefront renewal, infill housing, and corridor-scale improvements.",
        city_id="raleigh",
    ),
    "Southeast Raleigh": SubmarketMeta(
        name="Southeast Raleigh", borough="RALEIGH_CORE", lat=35.7350, lng=-78.6000,
        zoom=12.9, pitch=42.0, base_lims=0.77, capex=5400000.0, permit_vel=31.0,
        shift_ratio=1.36, sla=54.0,
        description="Growth and reinvestment corridor with neighborhood services, housing rehabilitation, and institutional anchors.",
        city_id="raleigh",
    ),
    "West Raleigh & Hillsborough Street": SubmarketMeta(
        name="West Raleigh & Hillsborough Street", borough="RALEIGH_CORE", lat=35.7890, lng=-78.6850,
        zoom=12.9, pitch=42.0, base_lims=0.79, capex=6300000.0, permit_vel=35.0,
        shift_ratio=1.40, sla=57.0,
        description="University and research-adjacent district with student housing, innovation activity, and commercial infill.",
        city_id="raleigh",
    ),
}


RALEIGH_DIVISIONS: dict[str, BoroughMeta] = {
    "RALEIGH_CORE": BoroughMeta(
        name="Raleigh / Wake County", center_lat=35.7796, center_lng=-78.6382, zoom=11.8,
        bbox=RALEIGH_DIVISION_BBOXES["RALEIGH_CORE"], submarkets=list(RALEIGH_SUBMARKETS),
        city_id="raleigh",
    ),
}
