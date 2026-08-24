"""Columbus, Ohio spatial registry and dashboard geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

COLUMBUS_METRO_BBOX: dict[str, float] = {
    "min_lat": 39.75,
    "max_lat": 40.20,
    "min_lng": -83.30,
    "max_lng": -82.70,
}

COLUMBUS_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "COLUMBUS_CORE": {
        "min_lat": 39.85,
        "max_lat": 40.12,
        "min_lng": -83.15,
        "max_lng": -82.80,
    },
}


def is_in_columbus_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Franklin County extent."""
    if lat is None or lng is None:
        return False
    return (
        COLUMBUS_METRO_BBOX["min_lat"] <= lat <= COLUMBUS_METRO_BBOX["max_lat"]
        and COLUMBUS_METRO_BBOX["min_lng"] <= lng <= COLUMBUS_METRO_BBOX["max_lng"]
    )


COLUMBUS_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Scioto Mile": SubmarketMeta(
        name="Downtown & Scioto Mile",
        borough="COLUMBUS_CORE",
        lat=39.9612,
        lng=-83.0007,
        zoom=13.6,
        pitch=48.0,
        base_lims=0.86,
        capex=7800000.0,
        permit_vel=38.0,
        shift_ratio=1.45,
        sla=60.0,
        description="Central business and riverfront district with office conversions, civic investment, and high-density residential demand.",
        city_id="columbus",
    ),
    "Short North & Italian Village": SubmarketMeta(
        name="Short North & Italian Village",
        borough="COLUMBUS_CORE",
        lat=39.9780,
        lng=-83.0080,
        zoom=13.6,
        pitch=46.0,
        base_lims=0.87,
        capex=7400000.0,
        permit_vel=41.0,
        shift_ratio=1.47,
        sla=58.0,
        description="High Street arts and gallery corridor with mixed-use infill, boutique hospitality, and historic rowhouse renovation.",
        city_id="columbus",
    ),
    "German Village & Brewery District": SubmarketMeta(
        name="German Village & Brewery District",
        borough="COLUMBUS_CORE",
        lat=39.9410,
        lng=-83.0060,
        zoom=13.2,
        pitch=44.0,
        base_lims=0.82,
        capex=5900000.0,
        permit_vel=32.0,
        shift_ratio=1.40,
        sla=56.0,
        description="Preserved south-side brick neighborhoods with restoration-driven permit activity and adaptive brewery reuse.",
        city_id="columbus",
    ),
    "Easton & Northeast Corridor": SubmarketMeta(
        name="Easton & Northeast Corridor",
        borough="COLUMBUS_CORE",
        lat=40.0430,
        lng=-82.9200,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.83,
        capex=6900000.0,
        permit_vel=35.0,
        shift_ratio=1.43,
        sla=58.0,
        description="Northeast retail and employment anchor with continued commercial buildout and surrounding residential growth.",
        city_id="columbus",
    ),
    "Hilltop": SubmarketMeta(
        name="Hilltop",
        borough="COLUMBUS_CORE",
        lat=39.9510,
        lng=-83.0880,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.76,
        capex=4800000.0,
        permit_vel=28.0,
        shift_ratio=1.36,
        sla=54.0,
        description="West-side neighborhood corridor targeted by reinvestment programs with infill housing and rehab activity.",
        city_id="columbus",
    ),
}

COLUMBUS_DIVISIONS: dict[str, BoroughMeta] = {
    "COLUMBUS_CORE": BoroughMeta(
        name="Columbus Core",
        center_lat=39.9612,
        center_lng=-83.0007,
        zoom=11.8,
        bbox=COLUMBUS_DIVISION_BBOXES["COLUMBUS_CORE"],
        submarkets=list(COLUMBUS_SUBMARKETS),
        city_id="columbus",
    ),
}
