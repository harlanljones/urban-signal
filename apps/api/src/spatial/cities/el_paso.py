"""El Paso, Texas spatial registry and geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

EL_PASO_METRO_BBOX: dict[str, float] = {
    "min_lat": 31.55,
    "max_lat": 32.20,
    "min_lng": -107.20,
    "max_lng": -106.00,
}

EL_PASO_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "EL_PASO_CORE": {
        "min_lat": 31.65,
        "max_lat": 32.10,
        "min_lng": -107.05,
        "max_lng": -106.25,
    },
}


def is_in_el_paso_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered El Paso extent."""
    if lat is None or lng is None:
        return False
    return (
        EL_PASO_METRO_BBOX["min_lat"] <= lat <= EL_PASO_METRO_BBOX["max_lat"]
        and EL_PASO_METRO_BBOX["min_lng"] <= lng <= EL_PASO_METRO_BBOX["max_lng"]
    )


EL_PASO_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Segundo Barrio": SubmarketMeta(
        name="Downtown & Segundo Barrio", borough="EL_PASO_CORE", lat=31.7587, lng=-106.4869,
        zoom=13.0, pitch=45.0, base_lims=0.80, capex=5600000.0, permit_vel=28.0,
        shift_ratio=1.35, sla=52.0,
        description="Border-adjacent civic core with historic rehabilitation, cross-border commerce, and public-realm investment.",
        city_id="el_paso",
    ),
    "Westside & UTEP": SubmarketMeta(
        name="Westside & UTEP", borough="EL_PASO_CORE", lat=31.7760, lng=-106.5050,
        zoom=12.7, pitch=42.0, base_lims=0.78, capex=5200000.0, permit_vel=26.0,
        shift_ratio=1.33, sla=51.0,
        description="University and west-side neighborhoods with infill, student-oriented services, and housing turnover.",
        city_id="el_paso",
    ),
    "Central El Paso": SubmarketMeta(
        name="Central El Paso", borough="EL_PASO_CORE", lat=31.7900, lng=-106.4350,
        zoom=12.6, pitch=41.0, base_lims=0.76, capex=4800000.0, permit_vel=25.0,
        shift_ratio=1.32, sla=50.0,
        description="Mature central neighborhoods with repair activity, municipal service demand, and corridor reinvestment.",
        city_id="el_paso",
    ),
    "East El Paso": SubmarketMeta(
        name="East El Paso", borough="EL_PASO_CORE", lat=31.8050, lng=-106.2750,
        zoom=12.2, pitch=39.0, base_lims=0.77, capex=6500000.0, permit_vel=34.0,
        shift_ratio=1.38, sla=53.0,
        description="Fast-growing east-side corridor where new housing, retail, and infrastructure extension converge.",
        city_id="el_paso",
    ),
    "Upper Valley": SubmarketMeta(
        name="Upper Valley", borough="EL_PASO_CORE", lat=31.8700, lng=-106.5350,
        zoom=11.9, pitch=37.0, base_lims=0.74, capex=5100000.0, permit_vel=24.0,
        shift_ratio=1.30, sla=49.0,
        description="Northwest valley communities balancing low-density growth, agricultural land, and service access.",
        city_id="el_paso",
    ),
}


EL_PASO_DIVISIONS: dict[str, BoroughMeta] = {
    "EL_PASO_CORE": BoroughMeta(
        name="El Paso / El Paso County", center_lat=31.7619, center_lng=-106.4850, zoom=10.8,
        bbox=EL_PASO_DIVISION_BBOXES["EL_PASO_CORE"], submarkets=list(EL_PASO_SUBMARKETS),
        city_id="el_paso",
    ),
}
