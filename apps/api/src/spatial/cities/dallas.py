"""Dallas Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Dallas and the
greater metro (Plano / Irving / Garland corridor), TX.

Dallas registers as a partial city for US-149: live right-of-way permits plus
the audited Building Services 30-day CRM view. The permit layer is a ROW
proxy for construction activity, not a standard building-permit feed. The 311
view is department-scoped and has no historical archive. SLA and DEEDS remain
unregistered.
"""

from typing import Any, Dict

from src.producers.field_maps_dallas import DALLAS_311_FIELD_MAP, DALLAS_FIELD_MAP
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Greater Dallas metro bounding box: City of Dallas core plus the Irving /
# Plano / Garland growth ring to the north and east. The two registered-ish
# proxy samples sit comfortably inside (Uptown ~32.795,-96.80; Plano edge
# ~33.02,-96.70; Oak Cliff ~32.70,-96.82).
DALLAS_METRO_BBOX: Dict[str, float] = {
    "min_lat": 32.60,
    "max_lat": 33.10,
    "min_lng": -97.05,
    "max_lng": -96.55,
}

# 6 Dallas Division Bounding Boxes, hand-authored. Borough resolution at ingest
# comes from coordinates via get_division_for_coordinate (Dallas council
# districts arrive as bare numerals like "1".."14", not division names), so
# bboxes need only be sane and disjoint enough to resolve near their centers.
DALLAS_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_EAST":        {"min_lat": 32.74,  "max_lat": 32.82,  "min_lng": -96.82,  "max_lng": -96.74},
    "OAK_LAWN_UPTOWN":      {"min_lat": 32.76,  "max_lat": 32.84,  "min_lng": -96.83,  "max_lng": -96.78},
    "NORTH_DALLAS_PRESTON": {"min_lat": 32.85,  "max_lat": 33.00,  "min_lng": -96.88,  "max_lng": -96.72},
    "EAST_DALLAS_WHITE_ROCK": {"min_lat": 32.78, "max_lat": 32.88, "min_lng": -96.78, "max_lng": -96.66},
    "SOUTH_DALLAS_OAK_CLIFF": {"min_lat": 32.62, "max_lat": 32.77, "min_lng": -96.88, "max_lng": -96.74},
    "PARK_CITIES_HIGHLAND_PARK": {"min_lat": 32.80, "max_lat": 32.86, "min_lng": -96.81, "max_lng": -96.76},
}


def is_in_dallas_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Greater Dallas Metropolitan bounds."""
    if lat is None or lng is None:
        return False
    return (
        DALLAS_METRO_BBOX["min_lat"] <= lat <= DALLAS_METRO_BBOX["max_lat"]
        and DALLAS_METRO_BBOX["min_lng"] <= lng <= DALLAS_METRO_BBOX["max_lng"]
    )


# Alias kept for symmetry with the other city modules' verbose spellings.
is_in_greater_dallas_metro = is_in_dallas_metro


DALLAS_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_EAST (3 Submarkets)
    # =======================================================================
    "Downtown Core & Main Street": SubmarketMeta(
        name="Downtown Core & Main Street",
        borough="DOWNTOWN_EAST",
        lat=32.7845,
        lng=-96.7930,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.92,
        capex=11500000.0,
        permit_vel=54.0,
        shift_ratio=1.66,
        sla=72.0,
        description="CBD towers and Deep Ellum edge where ROW/permit velocity tracks transit-oriented redevelopment along the DART core.",
        city_id="dallas",
    ),
    "Deep Ellum": SubmarketMeta(
        name="Deep Ellum",
        borough="DOWNTOWN_EAST",
        lat=32.7885,
        lng=-96.7780,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.84,
        capex=7600000.0,
        permit_vel=49.0,
        shift_ratio=1.58,
        sla=63.0,
        description="Music-venue and adaptive-reuse district east of the core, mixed-use infill driving small-lot ROW work.",
        city_id="dallas",
    ),
    "Baylor & Cedars": SubmarketMeta(
        name="Baylor & Cedars",
        borough="DOWNTOWN_EAST",
        lat=32.8005,
        lng=-96.8105,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=6400000.0,
        permit_vel=38.0,
        shift_ratio=1.49,
        sla=58.0,
        description="Medical-district-adjacent residential conversion belt with hospital-anchored demand and steady renovation permits.",
        city_id="dallas",
    ),
    # =======================================================================
    # OAK_LAWN_UPTOWN (3 Submarkets)
    # =======================================================================
    "Uptown & West Village": SubmarketMeta(
        name="Uptown & West Village",
        borough="OAK_LAWN_UPTOWN",
        lat=32.7955,
        lng=-96.8015,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.90,
        capex=11800000.0,
        permit_vel=57.0,
        shift_ratio=1.64,
        sla=70.0,
        description="Streetcar-era high-density multifamily spine with the metro's densest vertical construction outside downtown.",
        city_id="dallas",
    ),
    "Oak Lawn & Turtle Creek": SubmarketMeta(
        name="Oak Lawn & Turtle Creek",
        borough="OAK_LAWN_UPTOWN",
        lat=32.8175,
        lng=-96.8085,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.86,
        capex=9200000.0,
        permit_vel=44.0,
        shift_ratio=1.55,
        sla=64.0,
        description="Established estate-and-highrise corridor with teardown-rebuild mansions and luxury mid-rise permitting.",
        city_id="dallas",
    ),
    "Victory Park": SubmarketMeta(
        name="Victory Park",
        borough="OAK_LAWN_UPTOWN",
        lat=32.7895,
        lng=-96.8085,
        zoom=14.0,
        pitch=52.0,
        base_lims=0.83,
        capex=8800000.0,
        permit_vel=41.0,
        shift_ratio=1.52,
        sla=61.0,
        description="Arena-and-residential mixed-use node northwest of downtown with ground-up tower activity.",
        city_id="dallas",
    ),
    # =======================================================================
    # NORTH_DALLAS_PRESTON (3 Submarkets)
    # =======================================================================
    "Preston Hollow": SubmarketMeta(
        name="Preston Hollow",
        borough="NORTH_DALLAS_PRESTON",
        lat=32.8845,
        lng=-96.8055,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.89,
        capex=10500000.0,
        permit_vel=33.0,
        shift_ratio=1.46,
        sla=55.0,
        description="Hill-country estate stock with teardown-rebuild mansions dominating a low-volume, high-value permit mix.",
        city_id="dallas",
    ),
    "Preston Center & Bluffview": SubmarketMeta(
        name="Preston Center & Bluffview",
        borough="NORTH_DALLAS_PRESTON",
        lat=32.8655,
        lng=-96.8055,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.85,
        capex=8400000.0,
        permit_vel=39.0,
        shift_ratio=1.5,
        sla=60.0,
        description="Office-to-residential conversion belt and cottage-grid neighborhoods under the Preston overlay.",
        city_id="dallas",
    ),
    "North Dallas & LBJ Freeway": SubmarketMeta(
        name="North Dallas & LBJ Freeway",
        borough="NORTH_DALLAS_PRESTON",
        lat=32.9155,
        lng=-96.7555,
        zoom=12.5,
        pitch=38.0,
        base_lims=0.74,
        capex=5200000.0,
        permit_vel=31.0,
        shift_ratio=1.36,
        sla=49.0,
        description="Freeway-adjacent commercial edge with mid-rise multifamily replacements of aging retail and office stock.",
        city_id="dallas",
    ),
    # =======================================================================
    # EAST_DALLAS_WHITE_ROCK (3 Submarkets)
    # =======================================================================
    "White Rock Lake": SubmarketMeta(
        name="White Rock Lake",
        borough="EAST_DALLAS_WHITE_ROCK",
        lat=32.8275,
        lng=-96.7155,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.81,
        capex=6700000.0,
        permit_vel=28.0,
        shift_ratio=1.41,
        sla=54.0,
        description="Park-adjacent post-war residential hills drawing renovation capital from greenbelt access.",
        city_id="dallas",
    ),
    "Lake Highlands": SubmarketMeta(
        name="Lake Highlands",
        borough="EAST_DALLAS_WHITE_ROCK",
        lat=32.8555,
        lng=-96.7155,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=26.0,
        shift_ratio=1.34,
        sla=47.0,
        description="Suburban-style subdivisions along the northeastern growth spine, permitted through Dallas rather than Richardson.",
        city_id="dallas",
    ),
    "East Dallas & Lower Greenville": SubmarketMeta(
        name="East Dallas & Lower Greenville",
        borough="EAST_DALLAS_WHITE_ROCK",
        lat=32.8205,
        lng=-96.7705,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.83,
        capex=6900000.0,
        permit_vel=35.0,
        shift_ratio=1.45,
        sla=56.0,
        description="Indie-retail strip meeting streetcar-era bungalow stock, renovation-led permits under neighborhood overlays.",
        city_id="dallas",
    ),
    # =======================================================================
    # SOUTH_DALLAS_OAK_CLIFF (3 Submarkets)
    # =======================================================================
    "Bishop Arts District": SubmarketMeta(
        name="Bishop Arts District",
        borough="SOUTH_DALLAS_OAK_CLIFF",
        lat=32.7415,
        lng=-96.8255,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.84,
        capex=8200000.0,
        permit_vel=42.0,
        shift_ratio=1.53,
        sla=60.0,
        description="Boutique retail and hotel flagship corridor with infill multifamily on its side streets in North Oak Cliff.",
        city_id="dallas",
    ),
    "Kessler & Stevens Park": SubmarketMeta(
        name="Kessler & Stevens Park",
        borough="SOUTH_DALLAS_OAK_CLIFF",
        lat=32.7155,
        lng=-96.8355,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.79,
        capex=6000000.0,
        permit_vel=27.0,
        shift_ratio=1.4,
        sla=52.0,
        description="Hill-country estate stock at the Oak Cliff village boundary with teardown-rebuild pressure.",
        city_id="dallas",
    ),
    "South Dallas & Fair Park": SubmarketMeta(
        name="South Dallas & Fair Park",
        borough="SOUTH_DALLAS_OAK_CLIFF",
        lat=32.7655,
        lng=-96.7555,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.70,
        capex=4200000.0,
        permit_vel=22.0,
        shift_ratio=1.28,
        sla=43.0,
        description="Fair Park-adjacent redevelopment belt with renovation-heavy permitting and historic-district overlays.",
        city_id="dallas",
    ),
    # =======================================================================
    # PARK_CITIES_HIGHLAND_PARK (3 Submarkets)
    # =======================================================================
    "Highland Park": SubmarketMeta(
        name="Highland Park",
        borough="PARK_CITIES_HIGHLAND_PARK",
        lat=32.8265,
        lng=-96.7925,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.91,
        capex=11000000.0,
        permit_vel=24.0,
        shift_ratio=1.5,
        sla=51.0,
        description="Incorporated estate enclave inside Dallas with teardown-rebuild mansions dominating a low-volume, high-value mix.",
        city_id="dallas",
    ),
    "University Park": SubmarketMeta(
        name="University Park",
        borough="PARK_CITIES_HIGHLAND_PARK",
        lat=32.8355,
        lng=-96.7955,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.87,
        capex=9600000.0,
        permit_vel=29.0,
        shift_ratio=1.47,
        sla=55.0,
        description="SMU-anchored residential enclave with renovation-led permits and strict tree/single-family overlays.",
        city_id="dallas",
    ),
    "Highland Park Village Edge": SubmarketMeta(
        name="Highland Park Village Edge",
        borough="PARK_CITIES_HIGHLAND_PARK",
        lat=32.8305,
        lng=-96.8005,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.82,
        capex=7300000.0,
        permit_vel=21.0,
        shift_ratio=1.42,
        sla=48.0,
        description="Retail-and-residential node at the Park Cities boundary, ground-up luxury mixed-use on side streets.",
        city_id="dallas",
    ),
}


DALLAS_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_EAST": BoroughMeta(
        name="DOWNTOWN_EAST",
        center_lat=32.79,
        center_lng=-96.79,
        zoom=13.5,
        bbox=DALLAS_DIVISION_BBOXES["DOWNTOWN_EAST"],
        submarkets=[k for k, v in DALLAS_SUBMARKETS.items() if v.borough == "DOWNTOWN_EAST"],
        city_id="dallas",
    ),
    "OAK_LAWN_UPTOWN": BoroughMeta(
        name="OAK_LAWN_UPTOWN",
        center_lat=32.80,
        center_lng=-96.80,
        zoom=13.0,
        bbox=DALLAS_DIVISION_BBOXES["OAK_LAWN_UPTOWN"],
        submarkets=[k for k, v in DALLAS_SUBMARKETS.items() if v.borough == "OAK_LAWN_UPTOWN"],
        city_id="dallas",
    ),
    "NORTH_DALLAS_PRESTON": BoroughMeta(
        name="NORTH_DALLAS_PRESTON",
        center_lat=32.89,
        center_lng=-96.80,
        zoom=12.5,
        bbox=DALLAS_DIVISION_BBOXES["NORTH_DALLAS_PRESTON"],
        submarkets=[k for k, v in DALLAS_SUBMARKETS.items() if v.borough == "NORTH_DALLAS_PRESTON"],
        city_id="dallas",
    ),
    "EAST_DALLAS_WHITE_ROCK": BoroughMeta(
        name="EAST_DALLAS_WHITE_ROCK",
        center_lat=32.83,
        center_lng=-96.71,
        zoom=13.0,
        bbox=DALLAS_DIVISION_BBOXES["EAST_DALLAS_WHITE_ROCK"],
        submarkets=[k for k, v in DALLAS_SUBMARKETS.items() if v.borough == "EAST_DALLAS_WHITE_ROCK"],
        city_id="dallas",
    ),
    "SOUTH_DALLAS_OAK_CLIFF": BoroughMeta(
        name="SOUTH_DALLAS_OAK_CLIFF",
        center_lat=32.71,
        center_lng=-96.82,
        zoom=12.5,
        bbox=DALLAS_DIVISION_BBOXES["SOUTH_DALLAS_OAK_CLIFF"],
        submarkets=[k for k, v in DALLAS_SUBMARKETS.items() if v.borough == "SOUTH_DALLAS_OAK_CLIFF"],
        city_id="dallas",
    ),
    "PARK_CITIES_HIGHLAND_PARK": BoroughMeta(
        name="PARK_CITIES_HIGHLAND_PARK",
        center_lat=32.83,
        center_lng=-96.80,
        zoom=13.5,
        bbox=DALLAS_DIVISION_BBOXES["PARK_CITIES_HIGHLAND_PARK"],
        submarkets=[k for k, v in DALLAS_SUBMARKETS.items() if v.borough == "PARK_CITIES_HIGHLAND_PARK"],
        city_id="dallas",
    ),
}

# Verbose aliases mirroring the other city modules' *META_BBOX / *_SUBMARKETS pairs.
GREATER_DALLAS_METRO_BBOX = DALLAS_METRO_BBOX
DAL_DIVISION_BBOXES = DALLAS_DIVISION_BBOXES
DAL_SUBMARKETS = DALLAS_SUBMARKETS
DAL_DIVISIONS = DALLAS_DIVISIONS

# Exact DatasetSpec payloads for the registry spine. They remain dicts here to
# avoid importing city_registry.DatasetSpec while city_registry imports this
# module.
DALLAS_ROW_PERMITS_SPEC: Dict[str, Any] = {
    "endpoint": "settings.arcgis_dallas_row_permits_url",
    "platform": "arcgis",
    "watermark_col": "CREATEDDATE",
    "id_keys": ["EXTERNALFILENUM", "JOBID", "OBJECTID"],
    "topic": "settings.topic_permits",
    "interval_seconds": 300.0,
    "producer_key": "permits",
    "extra": {
        "expected_cadence_days": 7,
        "oid_field": "OBJECTID",
        "max_record_count": 2000,
        "order_by": "CREATEDDATE DESC",
        "proxy_for": "row_permits",
        "scope": "Dallas right-of-way and traffic-control permits (construction proxy, not building permits)",
        "field_map": DALLAS_FIELD_MAP,
    },
}

DALLAS_311_SPEC: Dict[str, Any] = {
    "endpoint": "settings.arcgis_dallas_311_url",
    "platform": "arcgis",
    "watermark_col": "CreatedDate",
    "id_keys": ["Service_Request_Number_c", "CaseNumber", "OBJECTID"],
    "topic": "settings.topic_311",
    "interval_seconds": 180.0,
    "producer_key": "311",
    "extra": {
        "expected_cadence_days": 1,
        "oid_field": "OBJECTID",
        "max_record_count": 2000,
        "rolling_window_days": 30,
        "retention_days": 30,
        "scope": "Dallas Building Services CRM requests (approximately 30-day rolling partial view)",
        "field_map": DALLAS_311_FIELD_MAP,
    },
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=DALLAS_METRO_BBOX,
    division_bboxes=DALLAS_DIVISION_BBOXES,
    submarkets=DALLAS_SUBMARKETS,
    divisions=DALLAS_DIVISIONS,
    contains=is_in_dallas_metro,
)
