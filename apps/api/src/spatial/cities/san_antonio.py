"""San Antonio / Bexar County, Texas spatial registry and geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

SAN_ANTONIO_METRO_BBOX: dict[str, float] = {
    "min_lat": 28.90,
    "max_lat": 29.90,
    "min_lng": -99.40,
    "max_lng": -98.00,
}

SAN_ANTONIO_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "SAN_ANTONIO_CORE": {
        "min_lat": 29.20,
        "max_lat": 29.75,
        "min_lng": -99.00,
        "max_lng": -98.25,
    },
}


def is_in_san_antonio_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered San Antonio extent."""
    if lat is None or lng is None:
        return False
    return (
        SAN_ANTONIO_METRO_BBOX["min_lat"] <= lat <= SAN_ANTONIO_METRO_BBOX["max_lat"]
        and SAN_ANTONIO_METRO_BBOX["min_lng"] <= lng <= SAN_ANTONIO_METRO_BBOX["max_lng"]
    )


SAN_ANTONIO_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & River Walk": SubmarketMeta(
        name="Downtown & River Walk", borough="SAN_ANTONIO_CORE", lat=29.4241, lng=-98.4936,
        zoom=13.3, pitch=48.0, base_lims=0.84, capex=8200000.0, permit_vel=40.0,
        shift_ratio=1.43, sla=58.0,
        description="Civic, hospitality, and riverfront core with adaptive reuse, visitor economy, and mixed-use redevelopment.",
        city_id="san_antonio",
    ),
    "Southtown & King William": SubmarketMeta(
        name="Southtown & King William", borough="SAN_ANTONIO_CORE", lat=29.4110, lng=-98.4890,
        zoom=13.1, pitch=46.0, base_lims=0.82, capex=6800000.0, permit_vel=36.0,
        shift_ratio=1.41, sla=57.0,
        description="Historic south-side neighborhoods with arts, hospitality, residential rehabilitation, and infill demand.",
        city_id="san_antonio",
    ),
    "Pearl & Broadway": SubmarketMeta(
        name="Pearl & Broadway", borough="SAN_ANTONIO_CORE", lat=29.4420, lng=-98.4800,
        zoom=13.0, pitch=44.0, base_lims=0.83, capex=7500000.0, permit_vel=38.0,
        shift_ratio=1.44, sla=59.0,
        description="North-central destination corridor with institutional, culinary, residential, and mobility-oriented investment.",
        city_id="san_antonio",
    ),
    "Medical Center & Northwest": SubmarketMeta(
        name="Medical Center & Northwest", borough="SAN_ANTONIO_CORE", lat=29.5100, lng=-98.5800,
        zoom=12.8, pitch=42.0, base_lims=0.79, capex=7200000.0, permit_vel=34.0,
        shift_ratio=1.39, sla=56.0,
        description="Major employment and medical corridor with apartments, clinics, retail, and redevelopment pressure.",
        city_id="san_antonio",
    ),
    "West Side & South San Antonio": SubmarketMeta(
        name="West Side & South San Antonio", borough="SAN_ANTONIO_CORE", lat=29.3650, lng=-98.5400,
        zoom=12.8, pitch=42.0, base_lims=0.76, capex=5100000.0, permit_vel=30.0,
        shift_ratio=1.35, sla=53.0,
        description="Established working neighborhoods with small-business activity, housing repair, and public infrastructure needs.",
        city_id="san_antonio",
    ),
}


SAN_ANTONIO_DIVISIONS: dict[str, BoroughMeta] = {
    "SAN_ANTONIO_CORE": BoroughMeta(
        name="San Antonio / Bexar County", center_lat=29.4241, center_lng=-98.4936, zoom=11.8,
        bbox=SAN_ANTONIO_DIVISION_BBOXES["SAN_ANTONIO_CORE"], submarkets=list(SAN_ANTONIO_SUBMARKETS),
        city_id="san_antonio",
    ),
}
