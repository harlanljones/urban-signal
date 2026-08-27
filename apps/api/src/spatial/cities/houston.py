"""Houston, Texas spatial registry and dashboard geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Houston–Harris County metro extent (product boundary for the 311-only
# registration; US-140). Houston proper sits in the center, Harris County
# surrounds it across the entire product bbox.
HOUSTON_METRO_BBOX: dict[str, float] = {
    "min_lat": 29.20,
    "max_lat": 30.30,
    "min_lng": -95.90,
    "max_lng": -94.80,
}

# Houston city proper, nested inside the metro bbox per the interlock
# containment invariant.
HOUSTON_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "HOUSTON_CORE": {
        "min_lat": 29.58,
        "max_lat": 30.02,
        "min_lng": -95.65,
        "max_lng": -95.10,
    },
}


def is_in_houston_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Houston–Harris County extent."""
    if lat is None or lng is None:
        return False
    return (
        HOUSTON_METRO_BBOX["min_lat"] <= lat <= HOUSTON_METRO_BBOX["max_lat"]
        and HOUSTON_METRO_BBOX["min_lng"] <= lng <= HOUSTON_METRO_BBOX["max_lng"]
    )


HOUSTON_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="HOUSTON_CORE",
        lat=29.7604,
        lng=-95.3698,
        zoom=13.4,
        pitch=48.0,
        base_lims=0.84,
        capex=10500000.0,
        permit_vel=42.0,
        shift_ratio=1.45,
        sla=58.0,
        description="Central business district with the Theater District, tunnel network, and dense new high-rise residential development.",
        city_id="houston",
    ),
    "Midtown": SubmarketMeta(
        name="Midtown",
        borough="HOUSTON_CORE",
        lat=29.7280,
        lng=-95.3760,
        zoom=13.2,
        pitch=46.0,
        base_lims=0.81,
        capex=7600000.0,
        permit_vel=38.0,
        shift_ratio=1.42,
        sla=56.0,
        description="Tree-lined walkable district between Downtown and the Museum District with restaurant corridors and infill townhomes.",
        city_id="houston",
    ),
    "Montrose": SubmarketMeta(
        name="Montrose",
        borough="HOUSTON_CORE",
        lat=29.7412,
        lng=-95.3940,
        zoom=13.2,
        pitch=44.0,
        base_lims=0.78,
        capex=6900000.0,
        permit_vel=34.0,
        shift_ratio=1.38,
        sla=52.0,
        description="Historic bungalow neighborhood along Westheimer with galleries, boutiques, and steady adaptive restoration.",
        city_id="houston",
    ),
    "The Heights": SubmarketMeta(
        name="The Heights",
        borough="HOUSTON_CORE",
        lat=29.7990,
        lng=-95.3990,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.80,
        capex=7800000.0,
        permit_vel=40.0,
        shift_ratio=1.44,
        sla=55.0,
        description="Historic Heights district with Victorian cottage stock, 19th Street retail, and strong infill and renovation activity.",
        city_id="houston",
    ),
    "Museum District": SubmarketMeta(
        name="Museum District",
        borough="HOUSTON_CORE",
        lat=29.7250,
        lng=-95.3910,
        zoom=13.2,
        pitch=46.0,
        base_lims=0.77,
        capex=7100000.0,
        permit_vel=32.0,
        shift_ratio=1.36,
        sla=50.0,
        description="Cultural corridor around Hermann Park and the museum campuses with mixed-use development and stable demand.",
        city_id="houston",
    ),
    "Galleria / Uptown": SubmarketMeta(
        name="Galleria / Uptown",
        borough="HOUSTON_CORE",
        lat=29.7420,
        lng=-95.4620,
        zoom=13.0,
        pitch=46.0,
        base_lims=0.86,
        capex=9800000.0,
        permit_vel=41.0,
        shift_ratio=1.47,
        sla=60.0,
        description="Post Oak Boulevard mixed-use district with the Galleria, transit (Uptown BRT), and high-rise luxury development.",
        city_id="houston",
    ),
}

HOUSTON_DIVISIONS: dict[str, BoroughMeta] = {
    "HOUSTON_CORE": BoroughMeta(
        name="Houston",
        center_lat=29.7604,
        center_lng=-95.3698,
        zoom=10.8,
        bbox=HOUSTON_DIVISION_BBOXES["HOUSTON_CORE"],
        submarkets=list(HOUSTON_SUBMARKETS),
        city_id="houston",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=HOUSTON_METRO_BBOX,
    division_bboxes=HOUSTON_DIVISION_BBOXES,
    submarkets=HOUSTON_SUBMARKETS,
    divisions=HOUSTON_DIVISIONS,
    contains=is_in_houston_metro,
)
