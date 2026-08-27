"""Denver, Colorado spatial registry and dashboard geometry."""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta


DENVER_METRO_BBOX: Dict[str, float] = {
    "min_lat": 39.55,
    "max_lat": 39.95,
    "min_lng": -105.20,
    "max_lng": -104.50,
}

DENVER_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DENVER_CORE": {
        "min_lat": 39.60,
        "max_lat": 39.85,
        "min_lng": -105.10,
        "max_lng": -104.70,
    },
}


def is_in_denver_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate lies inside the registered Denver extent."""
    if lat is None or lng is None:
        return False
    return (
        DENVER_METRO_BBOX["min_lat"] <= lat <= DENVER_METRO_BBOX["max_lat"]
        and DENVER_METRO_BBOX["min_lng"] <= lng <= DENVER_METRO_BBOX["max_lng"]
    )


DENVER_SUBMARKETS: Dict[str, SubmarketMeta] = {
    "Downtown & Union Station": SubmarketMeta(
        name="Downtown & Union Station",
        borough="DENVER_CORE",
        lat=39.7527,
        lng=-104.9992,
        zoom=13.6,
        pitch=48.0,
        base_lims=0.87,
        capex=8200000.0,
        permit_vel=44.0,
        shift_ratio=1.50,
        sla=62.0,
        description="Central business and transit district with office, hospitality, and high-density residential redevelopment.",
        city_id="denver",
    ),
    "RiNo & Five Points": SubmarketMeta(
        name="RiNo & Five Points",
        borough="DENVER_CORE",
        lat=39.7690,
        lng=-104.9780,
        zoom=13.4,
        pitch=46.0,
        base_lims=0.84,
        capex=7400000.0,
        permit_vel=41.0,
        shift_ratio=1.46,
        sla=59.0,
        description="North-central creative and industrial-reuse corridor with continuing mixed-use infill activity.",
        city_id="denver",
    ),
    "Capitol Hill & Cheesman Park": SubmarketMeta(
        name="Capitol Hill & Cheesman Park",
        borough="DENVER_CORE",
        lat=39.7340,
        lng=-104.9750,
        zoom=13.2,
        pitch=44.0,
        base_lims=0.80,
        capex=5900000.0,
        permit_vel=34.0,
        shift_ratio=1.41,
        sla=56.0,
        description="Established central neighborhoods with renovation, multifamily, and neighborhood-retail permit signals.",
        city_id="denver",
    ),
    "Cherry Creek & Congress Park": SubmarketMeta(
        name="Cherry Creek & Congress Park",
        borough="DENVER_CORE",
        lat=39.7170,
        lng=-104.9530,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.82,
        capex=6800000.0,
        permit_vel=36.0,
        shift_ratio=1.43,
        sla=58.0,
        description="Retail and residential corridor east of the core with redevelopment and high-value renovation activity.",
        city_id="denver",
    ),
}

DENVER_DIVISIONS: Dict[str, BoroughMeta] = {
    "DENVER_CORE": BoroughMeta(
        name="Denver Core",
        center_lat=39.7527,
        center_lng=-104.9992,
        zoom=11.8,
        bbox=DENVER_DIVISION_BBOXES["DENVER_CORE"],
        submarkets=list(DENVER_SUBMARKETS),
        city_id="denver",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=DENVER_METRO_BBOX,
    division_bboxes=DENVER_DIVISION_BBOXES,
    submarkets=DENVER_SUBMARKETS,
    divisions=DENVER_DIVISIONS,
    contains=is_in_denver_metro,
)
