"""Charlotte / Mecklenburg, North Carolina spatial registry and dashboard geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Charlotte-Mecklenburg metro extent (product boundary for the 311-only
# registration; US-88). Charlotte proper sits in the center, Mecklenburg
# County suburbs surround it.
CHARLOTTE_METRO_BBOX: dict[str, float] = {
    "min_lat": 34.98,
    "max_lat": 35.55,
    "min_lng": -81.10,
    "max_lng": -80.45,
}

# Charlotte city proper, nested inside the metro bbox per the interlock
# containment invariant.
CHARLOTTE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "CHARLOTTE_CORE": {
        "min_lat": 35.05,
        "max_lat": 35.40,
        "min_lng": -81.00,
        "max_lng": -80.60,
    },
}


def is_in_charlotte_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Charlotte-Mecklenburg extent."""
    if lat is None or lng is None:
        return False
    return (
        CHARLOTTE_METRO_BBOX["min_lat"] <= lat <= CHARLOTTE_METRO_BBOX["max_lat"]
        and CHARLOTTE_METRO_BBOX["min_lng"] <= lng <= CHARLOTTE_METRO_BBOX["max_lng"]
    )


CHARLOTTE_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Uptown": SubmarketMeta(
        name="Uptown",
        borough="CHARLOTTE_CORE",
        lat=35.2271,
        lng=-80.8431,
        zoom=13.4,
        pitch=48.0,
        base_lims=0.82,
        capex=11000000.0,
        permit_vel=40.0,
        shift_ratio=1.44,
        sla=60.0,
        description="Central business district with banks, towers, transit, and dense mixed-use residential development.",
        city_id="charlotte",
    ),
    "South End": SubmarketMeta(
        name="South End",
        borough="CHARLOTTE_CORE",
        lat=35.2150,
        lng=-80.8550,
        zoom=13.2,
        pitch=46.0,
        base_lims=0.84,
        capex=9600000.0,
        permit_vel=46.0,
        shift_ratio=1.46,
        sla=58.0,
        description="Former mill district along the rail line with explosive apartment and brewery-driven redevelopment.",
        city_id="charlotte",
    ),
    "Plaza Midwood": SubmarketMeta(
        name="Plaza Midwood",
        borough="CHARLOTTE_CORE",
        lat=35.2180,
        lng=-80.8000,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.80,
        capex=7200000.0,
        permit_vel=35.0,
        shift_ratio=1.40,
        sla=56.0,
        description="Historic bungalow district with restaurant/retail corridors and steady infill and renovation activity.",
        city_id="charlotte",
    ),
    "NoDa & Plaza Hills": SubmarketMeta(
        name="NoDa & Plaza Hills",
        borough="CHARLOTTE_CORE",
        lat=35.2450,
        lng=-80.8000,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.81,
        capex=8000000.0,
        permit_vel=38.0,
        shift_ratio=1.42,
        sla=57.0,
        description="Arts district north of Uptown with galleries, music venues, and infill townhomes along the Blue Line.",
        city_id="charlotte",
    ),
    "Elizabeth & Dilworth": SubmarketMeta(
        name="Elizabeth & Dilworth",
        borough="CHARLOTTE_CORE",
        lat=35.2140,
        lng=-80.8320,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.79,
        capex=6900000.0,
        permit_vel=33.0,
        shift_ratio=1.38,
        sla=55.0,
        description="Leafy streetcar-era neighborhoods with boutique multifamily infill and active renovation permits.",
        city_id="charlotte",
    ),
}

CHARLOTTE_DIVISIONS: dict[str, BoroughMeta] = {
    "CHARLOTTE_CORE": BoroughMeta(
        name="Charlotte",
        center_lat=35.2271,
        center_lng=-80.8431,
        zoom=11.2,
        bbox=CHARLOTTE_DIVISION_BBOXES["CHARLOTTE_CORE"],
        submarkets=list(CHARLOTTE_SUBMARKETS),
        city_id="charlotte",
    ),
}