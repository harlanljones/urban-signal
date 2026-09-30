"""Dover Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Dover, DE
(Kent County seat and state capital — deliberately scoped to the Dover
municipal extent, not the broader Kent County parcel layer).

Feeds: SLA reads the SNAP retailer slice (``snap_sla_spec``, Delaware stores
inside the metro box). The DEEDS feed registered until 2026-09-30 named a host
(gis.delaware.gov) that does not exist, and no public sale source exists: Kent
County's parcel layer carries a deed book and page reference but no sale date
or price, its sales history sits in the per-parcel PRIDE site, and Delaware
publishes no statewide sales dataset. Permits and 311 remain unregistered.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

DOVER_CITY_ID: str = "dover"

# Dover municipal parcel bbox (WGS84). Center is the downtown Green at
# 39.1582/-75.5244; the box covers the city and immediate contiguous built
# area within Kent County, bounded east by the St. Jones River and the bay.
DOVER_METRO_BBOX: dict[str, float] = {
    "min_lat": 39.10,
    "max_lat": 39.21,
    "min_lng": -75.58,
    "max_lng": -75.46,
}

DOVER_CENTER: dict[str, float] = {"lat": 39.1582, "lng": -75.5244}

# 5 Dover Division Bounding Boxes (strictly nested inside the metro bbox)
DOVER_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN":       {"min_lat": 39.145, "max_lat": 39.172, "min_lng": -75.540, "max_lng": -75.505},
    "EAST_SIDE":      {"min_lat": 39.145, "max_lat": 39.172, "min_lng": -75.505, "max_lng": -75.470},
    "WEST_SIDE":      {"min_lat": 39.145, "max_lat": 39.172, "min_lng": -75.575, "max_lng": -75.540},
    "NORTH_DOVER":    {"min_lat": 39.172, "max_lat": 39.210, "min_lng": -75.560, "max_lng": -75.490},
    "SOUTH_DOVER":    {"min_lat": 39.100, "max_lat": 39.145, "min_lng": -75.560, "max_lng": -75.490},
}


def is_in_dover_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Dover metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        DOVER_METRO_BBOX["min_lat"] <= lat <= DOVER_METRO_BBOX["max_lat"]
        and DOVER_METRO_BBOX["min_lng"] <= lng <= DOVER_METRO_BBOX["max_lng"]
    )


def is_in_dover(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_dover_metro`."""
    return is_in_dover_metro(lat, lng)


# ---------------------------------------------------------------------------
# Dover Submarket Registry (7 Submarkets Across 5 Divisions)
# ---------------------------------------------------------------------------

DOVER_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Dover Downtown": SubmarketMeta(
        name="Dover Downtown",
        borough="DOWNTOWN",
        lat=39.1582,
        lng=-75.5244,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.84,
        capex=5200000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=54.0,
        description="The capital Green and Loockerman Street CBD with state-office adjacent mixed-use and courthouse-district reinvestment.",
        city_id="dover",
    ),
    "Loockerman": SubmarketMeta(
        name="Loockerman",
        borough="DOWNTOWN",
        lat=39.1560,
        lng=-75.5250,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.80,
        capex=4100000.0,
        permit_vel=24.0,
        shift_ratio=1.34,
        sla=46.0,
        description="The West Loockerman Street corridor west of the Green with pre-war housing stock and steady restoration trades.",
        city_id="dover",
    ),
    "East Dover": SubmarketMeta(
        name="East Dover",
        borough="EAST_SIDE",
        lat=39.1580,
        lng=-75.4900,
        zoom=15.0,
        pitch=38.0,
        base_lims=0.78,
        capex=3900000.0,
        permit_vel=22.0,
        shift_ratio=1.30,
        sla=44.0,
        description="The Route 13 / Bay Road commercial spine east of the Green with auto-row retail and investor multifamily flow.",
        city_id="dover",
    ),
    "Silver Lake": SubmarketMeta(
        name="Silver Lake",
        borough="WEST_SIDE",
        lat=39.1580,
        lng=-75.5550,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.72,
        capex=3300000.0,
        permit_vel=20.0,
        shift_ratio=1.26,
        sla=40.0,
        description="The Silver Lake residential grid northwest of downtown with solid mid-century housing stock and lake-adjacent turnover.",
        city_id="dover",
    ),
    "North Dover": SubmarketMeta(
        name="North Dover",
        borough="NORTH_DOVER",
        lat=39.1900,
        lng=-75.5250,
        zoom=14.0,
        pitch=34.0,
        base_lims=0.70,
        capex=3100000.0,
        permit_vel=18.0,
        shift_ratio=1.22,
        sla=38.0,
        description="The north-side growth wedge along Route 8 with the hospital and Big-box corridor driving the permit mix.",
        city_id="dover",
    ),
    "Water Works": SubmarketMeta(
        name="Water Works",
        borough="NORTH_DOVER",
        lat=39.1950,
        lng=-75.5100,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.66,
        capex=2800000.0,
        permit_vel=16.0,
        shift_ratio=1.18,
        sla=34.0,
        description="The far-north St. Jones watershed edge where the city's lowest sale prices meet the heaviest vacancy-to-acquisition flow.",
        city_id="dover",
    ),
    "South Dover": SubmarketMeta(
        name="South Dover",
        borough="SOUTH_DOVER",
        lat=39.1200,
        lng=-75.5250,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.68,
        capex=3000000.0,
        permit_vel=19.0,
        shift_ratio=1.24,
        sla=36.0,
        description="The south-side residential wards along Route 13 with craftsman-bungalow stock and block-by-block reinvestment.",
        city_id="dover",
    ),
}


# ---------------------------------------------------------------------------
# Dover Divisions Catalog
# ---------------------------------------------------------------------------

DOVER_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=39.1570,
        center_lng=-75.5245,
        zoom=13.5,
        bbox=DOVER_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in DOVER_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="dover",
    ),
    "EAST_SIDE": BoroughMeta(
        name="EAST_SIDE",
        center_lat=39.1570,
        center_lng=-75.4900,
        zoom=13.5,
        bbox=DOVER_DIVISION_BBOXES["EAST_SIDE"],
        submarkets=[k for k, v in DOVER_SUBMARKETS.items() if v.borough == "EAST_SIDE"],
        city_id="dover",
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=39.1580,
        center_lng=-75.5550,
        zoom=13.0,
        bbox=DOVER_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in DOVER_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id="dover",
    ),
    "NORTH_DOVER": BoroughMeta(
        name="NORTH_DOVER",
        center_lat=39.1920,
        center_lng=-75.5180,
        zoom=13.0,
        bbox=DOVER_DIVISION_BBOXES["NORTH_DOVER"],
        submarkets=[k for k, v in DOVER_SUBMARKETS.items() if v.borough == "NORTH_DOVER"],
        city_id="dover",
    ),
    "SOUTH_DOVER": BoroughMeta(
        name="SOUTH_DOVER",
        center_lat=39.1220,
        center_lng=-75.5250,
        zoom=13.0,
        bbox=DOVER_DIVISION_BBOXES["SOUTH_DOVER"],
        submarkets=[k for k, v in DOVER_SUBMARKETS.items() if v.borough == "SOUTH_DOVER"],
        city_id="dover",
    ),
}

DOV_DIVISION_BBOXES = DOVER_DIVISION_BBOXES
DOV_SUBMARKETS = DOVER_SUBMARKETS
DOV_DIVISIONS = DOVER_DIVISIONS


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=DOVER_METRO_BBOX,
    division_bboxes=DOVER_DIVISION_BBOXES,
    submarkets=DOVER_SUBMARKETS,
    divisions=DOVER_DIVISIONS,
    contains=is_in_dover_metro,
)

__all__ = [
    "DOVER_CENTER",
    "DOVER_CITY_ID",
    "DOVER_DIVISIONS",
    "DOVER_DIVISION_BBOXES",
    "DOVER_METRO_BBOX",
    "DOVER_SUBMARKETS",
    "DOV_DIVISIONS",
    "DOV_DIVISION_BBOXES",
    "DOV_SUBMARKETS",
    "REGISTRATION",
    "is_in_dover",
    "is_in_dover_metro",
]
