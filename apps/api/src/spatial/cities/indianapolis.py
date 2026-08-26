"""Indianapolis / Marion County, Indiana spatial registry and dashboard geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

INDIANAPOLIS_METRO_BBOX: dict[str, float] = {
    "min_lat": 39.60,
    "max_lat": 39.95,
    "min_lng": -86.38,
    "max_lng": -85.90,
}

INDIANAPOLIS_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "INDIANAPOLIS_CORE": {
        "min_lat": 39.63,
        "max_lat": 39.92,
        "min_lng": -86.35,
        "max_lng": -85.92,
    },
}


def is_in_indianapolis_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Marion County extent."""
    if lat is None or lng is None:
        return False
    return (
        INDIANAPOLIS_METRO_BBOX["min_lat"] <= lat <= INDIANAPOLIS_METRO_BBOX["max_lat"]
        and INDIANAPOLIS_METRO_BBOX["min_lng"] <= lng <= INDIANAPOLIS_METRO_BBOX["max_lng"]
    )


INDIANAPOLIS_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Mile Square": SubmarketMeta(
        name="Downtown & Mile Square",
        borough="INDIANAPOLIS_CORE",
        lat=39.7684,
        lng=-86.1581,
        zoom=13.4,
        pitch=48.0,
        base_lims=0.84,
        capex=7200000.0,
        permit_vel=36.0,
        shift_ratio=1.42,
        sla=58.0,
        description="Central business and Mile Square core with the Monon/East Street corridors, office-to-residential conversions, and statehouse/civic demand.",
        city_id="indianapolis",
    ),
    "Mass Ave & Chatham Arch": SubmarketMeta(
        name="Mass Ave & Chatham Arch",
        borough="INDIANAPOLIS_CORE",
        lat=39.7753,
        lng=-86.1476,
        zoom=13.4,
        pitch=46.0,
        base_lims=0.85,
        capex=6800000.0,
        permit_vel=38.0,
        shift_ratio=1.44,
        sla=60.0,
        description="Massachusetts Avenue arts, dining, and theater district with brick rowhouse conversion and boutique hospitality demand.",
        city_id="indianapolis",
    ),
    "Fountain Square & Fletcher Place": SubmarketMeta(
        name="Fountain Square & Fletcher Place",
        borough="INDIANAPOLIS_CORE",
        lat=39.7520,
        lng=-86.1376,
        zoom=13.2,
        pitch=44.0,
        base_lims=0.80,
        capex=5400000.0,
        permit_vel=32.0,
        shift_ratio=1.38,
        sla=54.0,
        description="South-side historic commercial node on the Cultural Trail with Victorian infill, brewery-led adaptive reuse, and neighborhood retail.",
        city_id="indianapolis",
    ),
    "Broad Ripple": SubmarketMeta(
        name="Broad Ripple",
        borough="INDIANAPOLIS_CORE",
        lat=39.8664,
        lng=-86.1349,
        zoom=13.2,
        pitch=44.0,
        base_lims=0.78,
        capex=4900000.0,
        permit_vel=29.0,
        shift_ratio=1.34,
        sla=57.0,
        description="North-side riverside village with a dense entertainment strip, canal-front retail, and steady single-family and small-multifamily renovation.",
        city_id="indianapolis",
    ),
    "Irvington": SubmarketMeta(
        name="Irvington",
        borough="INDIANAPOLIS_CORE",
        lat=39.7690,
        lng=-86.0640,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.76,
        capex=4600000.0,
        permit_vel=28.0,
        shift_ratio=1.31,
        sla=52.0,
        description="Historic east-side National Register district along Washington Street with craftsman stock, commercial-corridor reinvestment, and infill housing.",
        city_id="indianapolis",
    ),
}

INDIANAPOLIS_DIVISIONS: dict[str, BoroughMeta] = {
    "INDIANAPOLIS_CORE": BoroughMeta(
        name="Marion County",
        center_lat=39.7684,
        center_lng=-86.1581,
        zoom=11.0,
        bbox=INDIANAPOLIS_DIVISION_BBOXES["INDIANAPOLIS_CORE"],
        submarkets=list(INDIANAPOLIS_SUBMARKETS),
        city_id="indianapolis",
    ),
}
