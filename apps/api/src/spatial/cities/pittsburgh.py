"""Pittsburgh, Pennsylvania spatial registry and dashboard geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

PITTSBURGH_METRO_BBOX: dict[str, float] = {
    "min_lat": 40.35,
    "max_lat": 40.55,
    "min_lng": -80.10,
    "max_lng": -79.80,
}

# City proper (the river valleys), nested inside the metro bbox per the
# interlock containment invariant.
PITTSBURGH_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "PITTSBURGH_CORE": {
        "min_lat": 40.40,
        "max_lat": 40.50,
        "min_lng": -80.05,
        "max_lng": -79.90,
    },
}


def is_in_pittsburgh_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Pittsburgh extent."""
    if lat is None or lng is None:
        return False
    return (
        PITTSBURGH_METRO_BBOX["min_lat"] <= lat <= PITTSBURGH_METRO_BBOX["max_lat"]
        and PITTSBURGH_METRO_BBOX["min_lng"] <= lng <= PITTSBURGH_METRO_BBOX["max_lng"]
    )


PITTSBURGH_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown (Golden Triangle)": SubmarketMeta(
        name="Downtown (Golden Triangle)",
        borough="PITTSBURGH_CORE",
        lat=40.4417,
        lng=-80.0000,
        zoom=13.2,
        pitch=48.0,
        base_lims=0.83,
        capex=9800000.0,
        permit_vel=42.0,
        shift_ratio=1.43,
        sla=56.0,
        description="Confluence of the three rivers with towers, transit, and dense mixed-use residential conversion activity.",
        city_id="pittsburgh",
    ),
    "North Side & Allegheny Center": SubmarketMeta(
        name="North Side & Allegheny Center",
        borough="PITTSBURGH_CORE",
        lat=40.4564,
        lng=-80.0064,
        zoom=13.0,
        pitch=46.0,
        base_lims=0.81,
        capex=7600000.0,
        permit_vel=37.0,
        shift_ratio=1.40,
        sla=54.0,
        description="Stadium-adjacent historic district with the Mexican War Streets, infill townhomes, and civic redevelopment.",
        city_id="pittsburgh",
    ),
    "East Liberty & Shadyside": SubmarketMeta(
        name="East Liberty & Shadyside",
        borough="PITTSBURGH_CORE",
        lat=40.4609,
        lng=-79.9164,
        zoom=13.0,
        pitch=46.0,
        base_lims=0.85,
        capex=8900000.0,
        permit_vel=44.0,
        shift_ratio=1.45,
        sla=58.0,
        description="East-end transit corridor with the most concentrated multifamily construction pipeline in the city.",
        city_id="pittsburgh",
    ),
    "South Side Flats": SubmarketMeta(
        name="South Side Flats",
        borough="PITTSBURGH_CORE",
        lat=40.4305,
        lng=-79.9860,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.80,
        capex=7100000.0,
        permit_vel=36.0,
        shift_ratio=1.39,
        sla=55.0,
        description="Riverfront entertainment corridor with dense commercial streets, adaptive reuse, and bar/restaurant turnover.",
        city_id="pittsburgh",
    ),
    "Lawrenceville & Strip District": SubmarketMeta(
        name="Lawrenceville & Strip District",
        borough="PITTSBURGH_CORE",
        lat=40.4707,
        lng=-79.9664,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.84,
        capex=8200000.0,
        permit_vel=40.0,
        shift_ratio=1.44,
        sla=57.0,
        description="Butler Street arts corridor with rapid retail, brewery, and residential loft conversion activity.",
        city_id="pittsburgh",
    ),
}

PITTSBURGH_DIVISIONS: dict[str, BoroughMeta] = {
    "PITTSBURGH_CORE": BoroughMeta(
        name="Pittsburgh",
        center_lat=40.4417,
        center_lng=-80.0000,
        zoom=11.8,
        bbox=PITTSBURGH_DIVISION_BBOXES["PITTSBURGH_CORE"],
        submarkets=list(PITTSBURGH_SUBMARKETS),
        city_id="pittsburgh",
    ),
}