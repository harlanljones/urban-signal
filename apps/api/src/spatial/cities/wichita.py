"""Wichita, Kansas spatial registry and dashboard geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

WICHITA_METRO_BBOX: dict[str, float] = {
    "min_lat": 37.40,
    "max_lat": 37.95,
    "min_lng": -97.85,
    "max_lng": -97.05,
}

WICHITA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "WICHITA_CORE": {
        "min_lat": 37.52,
        "max_lat": 37.80,
        "min_lng": -97.47,
        "max_lng": -97.11,
    },
}


def is_in_wichita_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Sedgwick County extent."""
    if lat is None or lng is None:
        return False
    return (
        WICHITA_METRO_BBOX["min_lat"] <= lat <= WICHITA_METRO_BBOX["max_lat"]
        and WICHITA_METRO_BBOX["min_lng"] <= lng <= WICHITA_METRO_BBOX["max_lng"]
    )


WICHITA_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Old Town": SubmarketMeta(
        name="Downtown & Old Town",
        borough="WICHITA_CORE",
        lat=37.6900,
        lng=-97.3330,
        zoom=13.6,
        pitch=48.0,
        base_lims=0.86,
        capex=7200000.0,
        permit_vel=36.0,
        shift_ratio=1.44,
        sla=58.0,
        description="Central business district and Old Town loft corridor with office conversions, heritage adaptive reuse, and high-density residential demand.",
        city_id="wichita",
    ),
    "Delano": SubmarketMeta(
        name="Delano",
        borough="WICHITA_CORE",
        lat=37.6860,
        lng=-97.3540,
        zoom=13.4,
        pitch=46.0,
        base_lims=0.85,
        capex=6800000.0,
        permit_vel=34.0,
        shift_ratio=1.43,
        sla=57.0,
        description="West-side riverfront district along Douglas Avenue with boutique hospitality, mixed-use infill, and entertainment-driven reinvestment.",
        city_id="wichita",
    ),
    "College Hill": SubmarketMeta(
        name="College Hill",
        borough="WICHITA_CORE",
        lat=37.7020,
        lng=-97.2810,
        zoom=13.2,
        pitch=44.0,
        base_lims=0.83,
        capex=6200000.0,
        permit_vel=31.0,
        shift_ratio=1.40,
        sla=55.0,
        description="East-side historic residential corridor with restored early-century housing and steady owner-occupant renovation activity.",
        city_id="wichita",
    ),
    "Riverside": SubmarketMeta(
        name="Riverside",
        borough="WICHITA_CORE",
        lat=37.7160,
        lng=-97.3430,
        zoom=13.2,
        pitch=44.0,
        base_lims=0.82,
        capex=5900000.0,
        permit_vel=30.0,
        shift_ratio=1.39,
        sla=54.0,
        description="Northwest riverfront and park-adjacent neighborhood with historic homes, civic investment, and enclave infill activity.",
        city_id="wichita",
    ),
    "Crown Heights & Midtown": SubmarketMeta(
        name="Crown Heights & Midtown",
        borough="WICHITA_CORE",
        lat=37.7350,
        lng=-97.3090,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.80,
        capex=5400000.0,
        permit_vel=28.0,
        shift_ratio=1.37,
        sla=53.0,
        description="North-central residential district targeted by reinvestment programs with rehabilitation and infill housing momentum.",
        city_id="wichita",
    ),
}

WICHITA_DIVISIONS: dict[str, BoroughMeta] = {
    "WICHITA_CORE": BoroughMeta(
        name="Wichita Core",
        center_lat=37.6900,
        center_lng=-97.3330,
        zoom=11.8,
        bbox=WICHITA_DIVISION_BBOXES["WICHITA_CORE"],
        submarkets=list(WICHITA_SUBMARKETS),
        city_id="wichita",
    ),
}
