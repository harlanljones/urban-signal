"""Kansas City, Missouri spatial registry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

KANSAS_CITY_METRO_BBOX: dict[str, float] = {
    "min_lat": 38.75,
    "max_lat": 39.40,
    "min_lng": -94.80,
    "max_lng": -94.30,
}

KANSAS_CITY_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "KANSAS_CITY_CORE": {
        "min_lat": 38.85,
        "max_lat": 39.30,
        "min_lng": -94.72,
        "max_lng": -94.42,
    },
}


def is_in_kansas_city_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered metro extent."""
    if lat is None or lng is None:
        return False
    return (
        KANSAS_CITY_METRO_BBOX["min_lat"] <= lat <= KANSAS_CITY_METRO_BBOX["max_lat"]
        and KANSAS_CITY_METRO_BBOX["min_lng"] <= lng <= KANSAS_CITY_METRO_BBOX["max_lng"]
    )


KANSAS_CITY_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & River Market": SubmarketMeta(
        name="Downtown & River Market",
        borough="KANSAS_CITY_CORE",
        lat=39.1000,
        lng=-94.5800,
        zoom=13.8,
        pitch=48.0,
        base_lims=0.84,
        capex=6900000.0,
        permit_vel=36.0,
        shift_ratio=1.44,
        sla=60.0,
        description="CBD civic core and riverfront loft district linked by the streetcar loop, with office conversions, arena-adjacent hospitality, and infill demand.",
        city_id="kansas_city",
    ),
    "Country Club Plaza & Westport": SubmarketMeta(
        name="Country Club Plaza & Westport",
        borough="KANSAS_CITY_CORE",
        lat=39.0480,
        lng=-94.5885,
        zoom=13.6,
        pitch=50.0,
        base_lims=0.82,
        capex=6500000.0,
        permit_vel=34.0,
        shift_ratio=1.42,
        sla=58.0,
        description="Signature retail and nightlife corridors spanning the Spanish-styled Plaza and Westport entertainment district, anchored by sustained commercial reinvestment.",
        city_id="kansas_city",
    ),
    "Brookside & Waldo": SubmarketMeta(
        name="Brookside & Waldo",
        borough="KANSAS_CITY_CORE",
        lat=38.9980,
        lng=-94.5860,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.78,
        capex=5200000.0,
        permit_vel=29.0,
        shift_ratio=1.36,
        sla=55.0,
        description="Tree-lined inner-ring neighborhood business districts along Wornall and Holmes with stable single-family stock and boutique retail demand.",
        city_id="kansas_city",
    ),
    "Northland & Zona Rosa": SubmarketMeta(
        name="Northland & Zona Rosa",
        borough="KANSAS_CITY_CORE",
        lat=39.2100,
        lng=-94.6180,
        zoom=12.9,
        pitch=42.0,
        base_lims=0.76,
        capex=4800000.0,
        permit_vel=27.0,
        shift_ratio=1.33,
        sla=52.0,
        description="Fast-growing Clay County suburbs around Zona Rosa and Barry Road, mixing town-center retail, logistics employment, and greenfield residential buildout.",
        city_id="kansas_city",
    ),
    "18th & Vine Crossroads": SubmarketMeta(
        name="18th & Vine Crossroads",
        borough="KANSAS_CITY_CORE",
        lat=39.0820,
        lng=-94.5720,
        zoom=13.4,
        pitch=46.0,
        base_lims=0.80,
        capex=5600000.0,
        permit_vel=31.0,
        shift_ratio=1.39,
        sla=56.0,
        description="Historic jazz district and Crossroads arts corridor east of downtown, with adaptive-reuse warehouses, gallery retail, and cultural-anchor investment.",
        city_id="kansas_city",
    ),
}

KANSAS_CITY_DIVISIONS: dict[str, BoroughMeta] = {
    "KANSAS_CITY_CORE": BoroughMeta(
        name="Kansas City Core",
        center_lat=39.1000,
        center_lng=-94.5800,
        zoom=11.2,
        bbox=KANSAS_CITY_DIVISION_BBOXES["KANSAS_CITY_CORE"],
        submarkets=list(KANSAS_CITY_SUBMARKETS),
        city_id="kansas_city",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=KANSAS_CITY_METRO_BBOX,
    division_bboxes=KANSAS_CITY_DIVISION_BBOXES,
    submarkets=KANSAS_CITY_SUBMARKETS,
    divisions=KANSAS_CITY_DIVISIONS,
    contains=is_in_kansas_city_metro,
)
