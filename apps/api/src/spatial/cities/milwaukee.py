"""Milwaukee, Wisconsin spatial registry and dashboard geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MILWAUKEE_METRO_BBOX: dict[str, float] = {
    "min_lat": 42.85,
    "max_lat": 43.20,
    "min_lng": -88.10,
    "max_lng": -87.80,
}

# Population corridor: the city proper within Milwaukee County, nested inside
# the metro bbox per the interlock containment invariant.
MILWAUKEE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "MILWAUKEE_CORE": {
        "min_lat": 42.90,
        "max_lat": 43.18,
        "min_lng": -88.08,
        "max_lng": -87.85,
    },
}


def is_in_milwaukee_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Milwaukee extent."""
    if lat is None or lng is None:
        return False
    return (
        MILWAUKEE_METRO_BBOX["min_lat"] <= lat <= MILWAUKEE_METRO_BBOX["max_lat"]
        and MILWAUKEE_METRO_BBOX["min_lng"] <= lng <= MILWAUKEE_METRO_BBOX["max_lng"]
    )


MILWAUKEE_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & East Town": SubmarketMeta(
        name="Downtown & East Town",
        borough="MILWAUKEE_CORE",
        lat=43.0389,
        lng=-87.9065,
        zoom=13.2,
        pitch=48.0,
        base_lims=0.81,
        capex=8200000.0,
        permit_vel=36.0,
        shift_ratio=1.40,
        sla=64.0,
        description="Lakefront central business district with the Deer District, arena-adjacent hospitality, and dense bar/restaurant license activity.",
        city_id="milwaukee",
    ),
    "Bay View": SubmarketMeta(
        name="Bay View",
        borough="MILWAUKEE_CORE",
        lat=42.9998,
        lng=-87.9057,
        zoom=13.0,
        pitch=46.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=30.0,
        shift_ratio=1.36,
        sla=58.0,
        description="South-side historic mill district with a strong independent tavern and restaurant corridor along Kinnickinnic Avenue.",
        city_id="milwaukee",
    ),
    "Walker's Point": SubmarketMeta(
        name="Walker's Point",
        borough="MILWAUKEE_CORE",
        lat=43.0220,
        lng=-87.9147,
        zoom=13.0,
        pitch=46.0,
        base_lims=0.79,
        capex=6100000.0,
        permit_vel=32.0,
        shift_ratio=1.37,
        sla=60.0,
        description="South-of-downtown food-and-beverage hub with concentrated liquor license turnover and adaptive reuse of industrial buildings.",
        city_id="milwaukee",
    ),
    "Riverwest & Brewers Hill": SubmarketMeta(
        name="Riverwest & Brewers Hill",
        borough="MILWAUKEE_CORE",
        lat=43.0604,
        lng=-87.9179,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.75,
        capex=4800000.0,
        permit_vel=27.0,
        shift_ratio=1.33,
        sla=56.0,
        description="North-side river neighborhoods with neighborhood taverns, music venues, and owner-operator license density.",
        city_id="milwaukee",
    ),
    "Westown & Washington Heights": SubmarketMeta(
        name="Westown & Washington Heights",
        borough="MILWAUKEE_CORE",
        lat=43.0520,
        lng=-87.9700,
        zoom=12.8,
        pitch=42.0,
        base_lims=0.74,
        capex=5200000.0,
        permit_vel=26.0,
        shift_ratio=1.32,
        sla=54.0,
        description="West-side corridor with mixed commercial-residential stock and steady service-sector license renewal activity.",
        city_id="milwaukee",
    ),
}

MILWAUKEE_DIVISIONS: dict[str, BoroughMeta] = {
    "MILWAUKEE_CORE": BoroughMeta(
        name="Milwaukee",
        center_lat=43.0389,
        center_lng=-87.9065,
        zoom=11.2,
        bbox=MILWAUKEE_DIVISION_BBOXES["MILWAUKEE_CORE"],
        submarkets=list(MILWAUKEE_SUBMARKETS),
        city_id="milwaukee",
    ),
}