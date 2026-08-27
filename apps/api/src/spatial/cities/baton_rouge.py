"""Baton Rouge / East Baton Rouge Parish spatial registry."""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta


BATON_ROUGE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 30.25,
    "max_lat": 30.65,
    "min_lng": -91.35,
    "max_lng": -90.85,
}

BATON_ROUGE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "BATON_ROUGE_CORE": {
        "min_lat": 30.30,
        "max_lat": 30.60,
        "min_lng": -91.25,
        "max_lng": -90.95,
    },
}


def is_in_baton_rouge_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered parish extent."""
    if lat is None or lng is None:
        return False
    return (
        BATON_ROUGE_METRO_BBOX["min_lat"] <= lat <= BATON_ROUGE_METRO_BBOX["max_lat"]
        and BATON_ROUGE_METRO_BBOX["min_lng"] <= lng <= BATON_ROUGE_METRO_BBOX["max_lng"]
    )


BATON_ROUGE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    "Downtown & North Boulevard": SubmarketMeta(
        name="Downtown & North Boulevard",
        borough="BATON_ROUGE_CORE",
        lat=30.4505,
        lng=-91.1870,
        zoom=13.6,
        pitch=48.0,
        base_lims=0.84,
        capex=6800000.0,
        permit_vel=36.0,
        shift_ratio=1.43,
        sla=60.0,
        description="Central Baton Rouge civic and riverfront corridor with downtown offices, government uses, and adaptive-reuse demand.",
        city_id="baton_rouge",
    ),
    "Mid City & North Baton Rouge": SubmarketMeta(
        name="Mid City & North Baton Rouge",
        borough="BATON_ROUGE_CORE",
        lat=30.4750,
        lng=-91.1600,
        zoom=13.2,
        pitch=44.0,
        base_lims=0.78,
        capex=5100000.0,
        permit_vel=30.0,
        shift_ratio=1.37,
        sla=55.0,
        description="Established north-of-downtown neighborhoods with neighborhood retail, infill, and public-realm investment signals.",
        city_id="baton_rouge",
    ),
    "South Baton Rouge & Perkins": SubmarketMeta(
        name="South Baton Rouge & Perkins",
        borough="BATON_ROUGE_CORE",
        lat=30.3950,
        lng=-91.1050,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.81,
        capex=6200000.0,
        permit_vel=34.0,
        shift_ratio=1.40,
        sla=58.0,
        description="South-parish growth corridor around Perkins Road and LSU-adjacent employment, retail, and residential demand.",
        city_id="baton_rouge",
    ),
}

BATON_ROUGE_DIVISIONS: Dict[str, BoroughMeta] = {
    "BATON_ROUGE_CORE": BoroughMeta(
        name="Baton Rouge Core",
        center_lat=30.4505,
        center_lng=-91.1870,
        zoom=11.8,
        bbox=BATON_ROUGE_DIVISION_BBOXES["BATON_ROUGE_CORE"],
        submarkets=list(BATON_ROUGE_SUBMARKETS),
        city_id="baton_rouge",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=BATON_ROUGE_METRO_BBOX,
    division_bboxes=BATON_ROUGE_DIVISION_BBOXES,
    submarkets=BATON_ROUGE_SUBMARKETS,
    divisions=BATON_ROUGE_DIVISIONS,
    contains=is_in_baton_rouge_metro,
)
