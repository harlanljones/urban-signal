"""Des Moines, IA — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the corpus YAML beside this
leaf (data/des_moines.yaml) and are re-bound to this REGISTRATION by the
registry derivation (US-429). The one registered feed is the City of Des
Moines Rental License layer:
https://maps.dsm.city/p2/rest/services/External/EXTDynamicCodeCaseRentalLicense/MapServer/1
See docs/research/probe-des_moines.md for the row-level probe, the families
that did not qualify, and the re-probe triggers.

Geographic basis: Des Moines is Iowa's capital and the Polk County seat. The
center is City Hall (400 Robert D Ray Dr), as matched by the Census geocoder
(41.588722, -93.616145).

Where the numbers come from (all read live on 2026-09-29, none from memory):

* Metro bbox: the union of the Census TIGERweb place extents for Des Moines
  (GEOID 1921000: 41.4796..41.6586 N, -93.7096..-93.4938 E), West Des Moines,
  Urbandale, Clive, Windsor Heights, Johnston, Ankeny, Altoona, Pleasant Hill
  and Norwalk, rounded outward to a 0.01 degree grid. Every one of the layer's
  15,475 rental rows lies inside it.
* Division bboxes tile the metro bbox exactly (no overlap, no gap) on the cut
  lines lat 41.57 / 41.61 / 41.66 and lng -93.71 / -93.585. The city proper lies
  south of 41.66 and east of -93.71 (its TIGERweb extent), so the four city
  divisions split the city and the two suburban divisions hold the ring.
* City submarket anchors are the mean of the member neighborhood-association
  centroids from the City's own Neighborhoods layer
  (services.arcgis.com/HT7H9QGiZQoRJDpJ/ArcGIS/rest/services/Neighborhoods_view/
  FeatureServer/0, 51 polygons, field NHNAME). Suburban anchors are the TIGERweb
  place internal points (mean of the two points for the paired suburbs).

Numeric seeds. ``sla`` is MEASURED: unique LicenseNumber values (feed filter
ContactType = 'Property Owner') with IssuedDate from 2026-07-01 through
2026-09-29, each assigned to its nearest anchor by great-circle distance, from
the live layer. It is a static snapshot seed, and 0 for the four suburban
submarkets because the registered feed covers the City of Des Moines only.
``base_lims`` / ``capex`` / ``permit_vel`` / ``shift_ratio`` are NOT measured:
no permits, 311 or scored feed is registered for Des Moines. Every leaf carries
such interface seeds (scripts/export_site_facts.py excludes them from site
facts); here one neutral value is used for every submarket so that no ranking
between submarkets is implied. ``zoom`` / ``pitch`` are viewport settings.
"""

from src.spatial.registration import SpatialRegistration
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

DES_MOINES_CITY_ID: str = "des_moines"

# Registration-contract center: Des Moines City Hall (Census geocoder match).
DES_MOINES_CENTER: dict[str, float] = {"lat": 41.5887, "lng": -93.6161}

# Union of the TIGERweb place extents for the city and its contiguous suburbs,
# rounded outward (see module docstring).
DES_MOINES_METRO_BBOX: dict[str, float] = {
    "min_lat": 41.44,
    "max_lat": 41.81,
    "min_lng": -93.90,
    "max_lng": -93.42,
}

# Division bounding boxes tile the metro bbox: a central belt between the north
# and south sides, an east band (the city's east side plus Altoona / Pleasant
# Hill), and the west and north suburban rings.
DES_MOINES_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    # Downtown, East Village, Sherman Hill, Drake and the west-central neighborhoods
    "CENTRAL_CORE": {"min_lat": 41.57, "max_lat": 41.61, "min_lng": -93.71, "max_lng": -93.585},
    # Beaverdale, Merle Hay, Highland Park, Union Park
    "NORTH_SIDE": {"min_lat": 41.61, "max_lat": 41.66, "min_lng": -93.71, "max_lng": -93.585},
    # Indianola Hills, Grays Lake, Watrous, South Central
    "SOUTH_SIDE": {"min_lat": 41.44, "max_lat": 41.57, "min_lng": -93.71, "max_lng": -93.585},
    # Fairground, Fairmont Park, Easter Lake, River Woods and Altoona / Pleasant Hill
    "EAST_SIDE": {"min_lat": 41.44, "max_lat": 41.66, "min_lng": -93.585, "max_lng": -93.42},
    # West Des Moines, Urbandale, Clive, Windsor Heights
    "WEST_SUBURBS": {"min_lat": 41.44, "max_lat": 41.66, "min_lng": -93.90, "max_lng": -93.71},
    # Ankeny, Johnston and the northern ring
    "NORTH_SUBURBS": {"min_lat": 41.66, "max_lat": 41.81, "min_lng": -93.90, "max_lng": -93.42},
}


def is_in_des_moines_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Des Moines metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        DES_MOINES_METRO_BBOX["min_lat"] <= lat <= DES_MOINES_METRO_BBOX["max_lat"]
        and DES_MOINES_METRO_BBOX["min_lng"] <= lng <= DES_MOINES_METRO_BBOX["max_lng"]
    )


# Submarkets (coordinates must live inside their division boxes for interlock
# containment). Neutral seeds: base_lims 0.75 / capex 5.0M / permit_vel 28 /
# shift_ratio 1.30 everywhere; ``sla`` is the measured 90-day count.
DES_MOINES_SUBMARKETS: dict[str, SubmarketMeta] = {
    # CENTRAL_CORE
    "Downtown / Sherman Hill": SubmarketMeta(
        name="Downtown / Sherman Hill",
        borough="CENTRAL_CORE",
        lat=41.5862,
        lng=-93.6350,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=139.0,
        description=(
            "Downtown Des Moines and Sherman Hill, with Woodland Heights, Good Park, "
            "Cheatom Park, King Irving and Greenwood Historic."
        ),
        city_id=DES_MOINES_CITY_ID,
    ),
    "East Village / Capitol": SubmarketMeta(
        name="East Village / Capitol",
        borough="CENTRAL_CORE",
        lat=41.5937,
        lng=-93.6010,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=27.0,
        description=(
            "Historic East Village, Capitol Park, Capitol East and Martin Luther King Jr. Park."
        ),
        city_id=DES_MOINES_CITY_ID,
    ),
    "Drake / Waveland Park": SubmarketMeta(
        name="Drake / Waveland Park",
        borough="CENTRAL_CORE",
        lat=41.6020,
        lng=-93.6714,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=124.0,
        description=(
            "Drake, Waveland Park and North of Grand, out to the Waterbury and Westwood "
            "neighborhoods on the west side."
        ),
        city_id=DES_MOINES_CITY_ID,
    ),
    # NORTH_SIDE
    "Beaverdale / Merle Hay": SubmarketMeta(
        name="Beaverdale / Merle Hay",
        borough="NORTH_SIDE",
        lat=41.6222,
        lng=-93.6853,
        zoom=13.8,
        pitch=42.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=146.0,
        description="Beaverdale, Merle Hay and Lower Beaver on the northwest side.",
        city_id=DES_MOINES_CITY_ID,
    ),
    "Highland Park / Union Park": SubmarketMeta(
        name="Highland Park / Union Park",
        borough="NORTH_SIDE",
        lat=41.6225,
        lng=-93.6123,
        zoom=13.8,
        pitch=42.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=72.0,
        description=(
            "Highland Park/Oak Park, Union Park, River Bend, Chautauqua Park and Mondamin "
            "Presidential on the north side."
        ),
        city_id=DES_MOINES_CITY_ID,
    ),
    # SOUTH_SIDE
    "Indianola Hills / Grays Lake": SubmarketMeta(
        name="Indianola Hills / Grays Lake",
        borough="SOUTH_SIDE",
        lat=41.5624,
        lng=-93.6233,
        zoom=13.8,
        pitch=42.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=51.0,
        description="Indianola Hills, Grays Lake and McKinley School/Columbus Park south of downtown.",
        city_id=DES_MOINES_CITY_ID,
    ),
    "South Central / Watrous": SubmarketMeta(
        name="South Central / Watrous",
        borough="SOUTH_SIDE",
        lat=41.5392,
        lng=-93.6208,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=65.0,
        description=(
            "South Central DSM, Watrous Heights, Watrous South and Southwestern Hills on the "
            "south side."
        ),
        city_id=DES_MOINES_CITY_ID,
    ),
    # EAST_SIDE
    "Fairground / Fairmont Park": SubmarketMeta(
        name="Fairground / Fairmont Park",
        borough="EAST_SIDE",
        lat=41.6070,
        lng=-93.5706,
        zoom=13.8,
        pitch=42.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=67.0,
        description=(
            "Fairground, Fairmont Park, ACCENT, Sheridan Gardens, Douglas Acres, Grays Woods "
            "and Valley High Manor on the east side."
        ),
        city_id=DES_MOINES_CITY_ID,
    ),
    "Easter Lake / River Woods": SubmarketMeta(
        name="Easter Lake / River Woods",
        borough="EAST_SIDE",
        lat=41.5470,
        lng=-93.5721,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=35.0,
        description="Easter Lake Area and River Woods on the southeast side.",
        city_id=DES_MOINES_CITY_ID,
    ),
    "Altoona / Pleasant Hill": SubmarketMeta(
        name="Altoona / Pleasant Hill",
        borough="EAST_SIDE",
        lat=41.6263,
        lng=-93.4939,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=16.0,
        description=(
            "Altoona and Pleasant Hill at the city's eastern edge; Brook Run is the nearest "
            "Des Moines neighborhood."
        ),
        city_id=DES_MOINES_CITY_ID,
    ),
    # WEST_SUBURBS
    "West Des Moines": SubmarketMeta(
        name="West Des Moines",
        borough="WEST_SUBURBS",
        lat=41.5499,
        lng=-93.7814,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=0.0,
        description=(
            "West Des Moines (Census place 1983910); outside the registered City of Des Moines "
            "rental license feed."
        ),
        city_id=DES_MOINES_CITY_ID,
    ),
    "Urbandale / Clive": SubmarketMeta(
        name="Urbandale / Clive",
        borough="WEST_SUBURBS",
        lat=41.6244,
        lng=-93.7904,
        zoom=13.3,
        pitch=40.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=0.0,
        description=(
            "Urbandale and Clive (Census places 1979950 and 1914520); outside the registered "
            "City of Des Moines rental license feed."
        ),
        city_id=DES_MOINES_CITY_ID,
    ),
    # NORTH_SUBURBS
    "Ankeny": SubmarketMeta(
        name="Ankeny",
        borough="NORTH_SUBURBS",
        lat=41.7336,
        lng=-93.5994,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=0.0,
        description=(
            "Ankeny (Census place 1902305); outside the registered City of Des Moines rental "
            "license feed."
        ),
        city_id=DES_MOINES_CITY_ID,
    ),
    "Johnston": SubmarketMeta(
        name="Johnston",
        borough="NORTH_SUBURBS",
        lat=41.6919,
        lng=-93.7245,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.30,
        sla=0.0,
        description=(
            "Johnston (Census place 1939765); outside the registered City of Des Moines rental "
            "license feed."
        ),
        city_id=DES_MOINES_CITY_ID,
    ),
}


DES_MOINES_DIVISIONS: dict[str, BoroughMeta] = {
    "CENTRAL_CORE": BoroughMeta(
        name="CENTRAL_CORE",
        center_lat=41.594,
        center_lng=-93.636,
        zoom=13.2,
        bbox=DES_MOINES_DIVISION_BBOXES["CENTRAL_CORE"],
        submarkets=[k for k, v in DES_MOINES_SUBMARKETS.items() if v.borough == "CENTRAL_CORE"],
        city_id=DES_MOINES_CITY_ID,
    ),
    "NORTH_SIDE": BoroughMeta(
        name="NORTH_SIDE",
        center_lat=41.622,
        center_lng=-93.649,
        zoom=13.0,
        bbox=DES_MOINES_DIVISION_BBOXES["NORTH_SIDE"],
        submarkets=[k for k, v in DES_MOINES_SUBMARKETS.items() if v.borough == "NORTH_SIDE"],
        city_id=DES_MOINES_CITY_ID,
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=41.551,
        center_lng=-93.622,
        zoom=13.0,
        bbox=DES_MOINES_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in DES_MOINES_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id=DES_MOINES_CITY_ID,
    ),
    "EAST_SIDE": BoroughMeta(
        name="EAST_SIDE",
        center_lat=41.593,
        center_lng=-93.546,
        zoom=12.8,
        bbox=DES_MOINES_DIVISION_BBOXES["EAST_SIDE"],
        submarkets=[k for k, v in DES_MOINES_SUBMARKETS.items() if v.borough == "EAST_SIDE"],
        city_id=DES_MOINES_CITY_ID,
    ),
    "WEST_SUBURBS": BoroughMeta(
        name="WEST_SUBURBS",
        center_lat=41.587,
        center_lng=-93.786,
        zoom=12.5,
        bbox=DES_MOINES_DIVISION_BBOXES["WEST_SUBURBS"],
        submarkets=[k for k, v in DES_MOINES_SUBMARKETS.items() if v.borough == "WEST_SUBURBS"],
        city_id=DES_MOINES_CITY_ID,
    ),
    "NORTH_SUBURBS": BoroughMeta(
        name="NORTH_SUBURBS",
        center_lat=41.713,
        center_lng=-93.662,
        zoom=12.3,
        bbox=DES_MOINES_DIVISION_BBOXES["NORTH_SUBURBS"],
        submarkets=[k for k, v in DES_MOINES_SUBMARKETS.items() if v.borough == "NORTH_SUBURBS"],
        city_id=DES_MOINES_CITY_ID,
    ),
}

DES_MOINES_DIVISION_BBOXES_EXPORT = DES_MOINES_DIVISION_BBOXES
DES_MOINES_SUBMARKETS_EXPORT = DES_MOINES_SUBMARKETS
DES_MOINES_DIVISIONS_EXPORT = DES_MOINES_DIVISIONS

REGISTRATION = SpatialRegistration(
    metro_bbox=DES_MOINES_METRO_BBOX,
    division_bboxes=DES_MOINES_DIVISION_BBOXES,
    submarkets=DES_MOINES_SUBMARKETS,
    divisions=DES_MOINES_DIVISIONS,
    contains=is_in_des_moines_metro,
)

__all__ = [
    "DES_MOINES_CENTER",
    "DES_MOINES_CITY_ID",
    "DES_MOINES_DIVISIONS",
    "DES_MOINES_DIVISIONS_EXPORT",
    "DES_MOINES_DIVISION_BBOXES",
    "DES_MOINES_DIVISION_BBOXES_EXPORT",
    "DES_MOINES_METRO_BBOX",
    "DES_MOINES_SUBMARKETS",
    "DES_MOINES_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_des_moines_metro",
]
