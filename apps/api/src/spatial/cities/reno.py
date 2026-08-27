"""Reno / Washoe County spatial registry and geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

RENO_METRO_BBOX: dict[str, float] = {
    "min_lat": 39.30,
    "max_lat": 40.00,
    "min_lng": -120.20,
    "max_lng": -119.40,
}

RENO_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "RENO_CORE": {
        "min_lat": 39.30,
        "max_lat": 39.80,
        "min_lng": -120.15,
        "max_lng": -119.55,
    },
}


def is_in_reno_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Reno extent."""
    if lat is None or lng is None:
        return False
    return (
        RENO_METRO_BBOX["min_lat"] <= lat <= RENO_METRO_BBOX["max_lat"]
        and RENO_METRO_BBOX["min_lng"] <= lng <= RENO_METRO_BBOX["max_lng"]
    )


RENO_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Midtown": SubmarketMeta(
        name="Downtown & Midtown", borough="RENO_CORE", lat=39.5296, lng=-119.8138,
        zoom=13.2, pitch=46.0, base_lims=0.82, capex=6500000.0, permit_vel=31.0,
        shift_ratio=1.38, sla=54.0,
        description="Truckee River and civic core with hospitality, adaptive reuse, and urban infill activity.",
        city_id="reno",
    ),
    "South Reno": SubmarketMeta(
        name="South Reno", borough="RENO_CORE", lat=39.4550, lng=-119.7600,
        zoom=12.6, pitch=42.0, base_lims=0.79, capex=7100000.0, permit_vel=34.0,
        shift_ratio=1.40, sla=55.0,
        description="High-growth residential corridor with new construction, retail expansion, and suburban intensification.",
        city_id="reno",
    ),
    "Northwest Reno": SubmarketMeta(
        name="Northwest Reno", borough="RENO_CORE", lat=39.5800, lng=-119.8800,
        zoom=12.7, pitch=43.0, base_lims=0.78, capex=6000000.0, permit_vel=29.0,
        shift_ratio=1.35, sla=53.0,
        description="Established foothill neighborhoods with renovation, infill, and county parcel turnover.",
        city_id="reno",
    ),
    "Sparks": SubmarketMeta(
        name="Sparks", borough="RENO_CORE", lat=39.5349, lng=-119.7527,
        zoom=12.8, pitch=43.0, base_lims=0.80, capex=6800000.0, permit_vel=33.0,
        shift_ratio=1.39, sla=54.0,
        description="Industrial and residential east valley with logistics investment, redevelopment, and active parcel sales.",
        city_id="reno",
    ),
    "Spanish Springs": SubmarketMeta(
        name="Spanish Springs", borough="RENO_CORE", lat=39.6400, lng=-119.6800,
        zoom=12.2, pitch=39.0, base_lims=0.75, capex=5700000.0, permit_vel=27.0,
        shift_ratio=1.33, sla=51.0,
        description="Northern growth area where new housing, infrastructure extension, and unincorporated county development meet.",
        city_id="reno",
    ),
}


RENO_DIVISIONS: dict[str, BoroughMeta] = {
    "RENO_CORE": BoroughMeta(
        name="Reno / Washoe County", center_lat=39.5296, center_lng=-119.8138, zoom=10.8,
        bbox=RENO_DIVISION_BBOXES["RENO_CORE"], submarkets=list(RENO_SUBMARKETS),
        city_id="reno",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=RENO_METRO_BBOX,
    division_bboxes=RENO_DIVISION_BBOXES,
    submarkets=RENO_SUBMARKETS,
    divisions=RENO_DIVISIONS,
    contains=is_in_reno_metro,
)
