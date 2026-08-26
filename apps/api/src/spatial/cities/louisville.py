"""Louisville Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Louisville and
greater Jefferson County, KY.

Louisville registers as a TWO-FEED partial city: COMPLAINTS_311 from the
Louisville Metro ArcGIS layer and SLA from the Kentucky ABC active-license
ArcGIS layer, filtered to Jefferson County. DEEDS and PERMITS remain absent.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Greater Louisville metro bounding box. Jefferson County seat; the metro is
# single-county for this registration (Louisville-Jefferson County Metro
# government consolidated in 2003). The bbox is permissive — it only has to keep
# every live sample inside. Center downtown ~38.2527,-85.7585; Highlands
# ~38.23,-85.69; St. Matthews ~38.26,-85.65; Portland ~38.265,-85.80.
LOUISVILLE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 38.10,
    "max_lat": 38.35,
    "min_lng": -85.95,
    "max_lng": -85.55,
}

# 6 Louisville Division Bounding Boxes. Approximate hand-authored geographies;
# borough resolution at ingest comes from coordinates via
# get_division_for_coordinate, so bboxes need only be sane and disjoint enough
# to resolve unambiguously near their centers.
LOUISVILLE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_NULU":          {"min_lat": 38.24,  "max_lat": 38.27,  "min_lng": -85.775, "max_lng": -85.735},
    "HIGHLANDS_GERMANTOWN":   {"min_lat": 38.20,  "max_lat": 38.255, "min_lng": -85.75,  "max_lng": -85.66},
    "CLIFTON_CRESCENT_HILL":  {"min_lat": 38.245, "max_lat": 38.285, "min_lng": -85.73,  "max_lng": -85.66},
    "OLD_LOUISVILLE_SHELBY_PARK": {"min_lat": 38.195, "max_lat": 38.235, "min_lng": -85.79, "max_lng": -85.74},
    "ST_MATTHEWS_EAST":       {"min_lat": 38.245, "max_lat": 38.285, "min_lng": -85.69,  "max_lng": -85.61},
    "WEST_PORTLAND":          {"min_lat": 38.245, "max_lat": 38.285, "min_lng": -85.83,  "max_lng": -85.78},
}


def is_in_louisville_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Greater Louisville Metropolitan bounds."""
    if lat is None or lng is None:
        return False
    return (
        LOUISVILLE_METRO_BBOX["min_lat"] <= lat <= LOUISVILLE_METRO_BBOX["max_lat"]
        and LOUISVILLE_METRO_BBOX["min_lng"] <= lng <= LOUISVILLE_METRO_BBOX["max_lng"]
    )


# Alias kept for symmetry with the other city modules' verbose spellings.
is_in_greater_louisville_metro = is_in_louisville_metro


LOUISVILLE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_NULU (3 Submarkets)
    # =======================================================================
    "Downtown & Waterfront": SubmarketMeta(
        name="Downtown & Waterfront",
        borough="DOWNTOWN_NULU",
        lat=38.2570,
        lng=-85.7580,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.90,
        capex=11000000.0,
        permit_vel=52.0,
        shift_ratio=1.62,
        sla=72.0,
        description="Central business district along the Ohio River waterfront with the KFC Yum! Center and riverfront redevelopment driving mixed-use permits.",
        city_id="louisville",
    ),
    "NuLu (East Market District)": SubmarketMeta(
        name="NuLu (East Market District)",
        borough="DOWNTOWN_NULU",
        lat=38.2470,
        lng=-85.7450,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.87,
        capex=9200000.0,
        permit_vel=46.0,
        shift_ratio=1.57,
        sla=68.0,
        description="East Market Street gallery-and-boutique corridor converting industrial stock to hospitality and residential above retail.",
        city_id="louisville",
    ),
    "Phoenix Hill & Shelby Street": SubmarketMeta(
        name="Phoenix Hill & Shelby Street",
        borough="DOWNTOWN_NULU",
        lat=38.2420,
        lng=-85.7520,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.83,
        capex=6400000.0,
        permit_vel=39.0,
        shift_ratio=1.49,
        sla=60.0,
        description="Hill-edge infill between downtown and the Highlands with small-lot townhome and adaptive-reuse activity.",
        city_id="louisville",
    ),
    # =======================================================================
    # HIGHLANDS_GERMANTOWN (3 Submarkets)
    # =======================================================================
    "Bardstown Road Highlands": SubmarketMeta(
        name="Bardstown Road Highlands",
        borough="HIGHLANDS_GERMANTOWN",
        lat=38.2350,
        lng=-85.6850,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.86,
        capex=8600000.0,
        permit_vel=41.0,
        shift_ratio=1.54,
        sla=65.0,
        description="The commercial spine of the Highlands — independent retail, music venues, and dense mid-rise multifamily.",
        city_id="louisville",
    ),
    "GermanTown & Paristown": SubmarketMeta(
        name="GermanTown & Paristown",
        borough="HIGHLANDS_GERMANTOWN",
        lat=38.2250,
        lng=-85.7350,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.82,
        capex=6100000.0,
        permit_vel=35.0,
        shift_ratio=1.46,
        sla=58.0,
        description="Post-industrial bungalow grid rehabbing into breweries, maker spaces, and infill townhomes.",
        city_id="louisville",
    ),
    "Douglass Loop": SubmarketMeta(
        name="Douglass Loop",
        borough="HIGHLANDS_GERMANTOWN",
        lat=38.2150,
        lng=-85.6750,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.80,
        capex=5500000.0,
        permit_vel=31.0,
        shift_ratio=1.43,
        sla=55.0,
        description="South Highlands village node with renovation-led permitting and strict neighborhood overlay review.",
        city_id="louisville",
    ),
    # =======================================================================
    # CLIFTON_CRESCENT_HILL (3 Submarkets)
    # =======================================================================
    "Clifton & Frankfort Ave": SubmarketMeta(
        name="Clifton & Frankfort Ave",
        borough="CLIFTON_CRESCENT_HILL",
        lat=38.2650,
        lng=-85.7150,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=7900000.0,
        permit_vel=43.0,
        shift_ratio=1.52,
        sla=63.0,
        description="Walkable neighborhood commercial corridor with mixed-use infill and hospitality conversions.",
        city_id="louisville",
    ),
    "Crescent Hill": SubmarketMeta(
        name="Crescent Hill",
        borough="CLIFTON_CRESCENT_HILL",
        lat=38.2750,
        lng=-85.6850,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.83,
        capex=6800000.0,
        permit_vel=37.0,
        shift_ratio=1.47,
        sla=59.0,
        description="Streetcar-era bungalow district around the reservoir with renovation-heavy permits.",
        city_id="louisville",
    ),
    "Bonnycastle": SubmarketMeta(
        name="Bonnycastle",
        borough="CLIFTON_CRESCENT_HILL",
        lat=38.2550,
        lng=-85.6900,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.81,
        capex=6200000.0,
        permit_vel=33.0,
        shift_ratio=1.45,
        sla=57.0,
        description="Established residential pocket between the Highlands and Crescent Hill with teardown/rebuild pressure.",
        city_id="louisville",
    ),
    # =======================================================================
    # OLD_LOUISVILLE_SHELBY_PARK (3 Submarkets)
    # =======================================================================
    "Old Louisville": SubmarketMeta(
        name="Old Louisville",
        borough="OLD_LOUISVILLE_SHELBY_PARK",
        lat=38.2150,
        lng=-85.7650,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.84,
        capex=7000000.0,
        permit_vel=34.0,
        shift_ratio=1.48,
        sla=58.0,
        description="Nationally significant Victorian residential district with historic-preservation overlay permitting.",
        city_id="louisville",
    ),
    "Shelby Park": SubmarketMeta(
        name="Shelby Park",
        borough="OLD_LOUISVILLE_SHELBY_PARK",
        lat=38.2250,
        lng=-85.7550,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.83,
        capex=6600000.0,
        permit_vel=38.0,
        shift_ratio=1.46,
        sla=57.0,
        description="South-of-downtown park neighborhood undergoing cafe-and-townhome infill.",
        city_id="louisville",
    ),
    "Smoketown": SubmarketMeta(
        name="Smoketown",
        borough="OLD_LOUISVILLE_SHELBY_PARK",
        lat=38.2350,
        lng=-85.7550,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.79,
        capex=5200000.0,
        permit_vel=29.0,
        shift_ratio=1.40,
        sla=53.0,
        description="Historic Black neighborhood near downtown with early-stage redevelopment and new-construction permits.",
        city_id="louisville",
    ),
    # =======================================================================
    # ST_MATTHEWS_EAST (3 Submarkets)
    # =======================================================================
    "St. Matthews": SubmarketMeta(
        name="St. Matthews",
        borough="ST_MATTHEWS_EAST",
        lat=38.2600,
        lng=-85.6500,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.88,
        capex=9400000.0,
        permit_vel=49.0,
        shift_ratio=1.58,
        sla=64.0,
        description="Established inner-suburb retail node with mall-adjacent mixed-use and multifamily redevelopment.",
        city_id="louisville",
    ),
    "Eastpoint & Lyndon": SubmarketMeta(
        name="Eastpoint & Lyndon",
        borough="ST_MATTHEWS_EAST",
        lat=38.2700,
        lng=-85.6300,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.76,
        capex=4900000.0,
        permit_vel=27.0,
        shift_ratio=1.36,
        sla=50.0,
        description="Eastern Jefferson County edge with office-to-residential conversions and suburban infill.",
        city_id="louisville",
    ),
    "Hurstbourne": SubmarketMeta(
        name="Hurstbourne",
        borough="ST_MATTHEWS_EAST",
        lat=38.2750,
        lng=-85.6200,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.74,
        capex=4400000.0,
        permit_vel=24.0,
        shift_ratio=1.32,
        sla=47.0,
        description="I-64 corridor office park and hotel district with selective redevelopment pressure.",
        city_id="louisville",
    ),
    # =======================================================================
    # WEST_PORTLAND (3 Submarkets)
    # =======================================================================
    "Portland": SubmarketMeta(
        name="Portland",
        borough="WEST_PORTLAND",
        lat=38.2650,
        lng=-85.8000,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.79,
        capex=5600000.0,
        permit_vel=33.0,
        shift_ratio=1.45,
        sla=55.0,
        description="River-front historic neighborhood with early-stage industrial-to-residential conversion and flood-recovery investment.",
        city_id="louisville",
    ),
    "Shawnee & Chickasaw": SubmarketMeta(
        name="Shawnee & Chickasaw",
        borough="WEST_PORTLAND",
        lat=38.2550,
        lng=-85.8150,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.75,
        capex=4700000.0,
        permit_vel=26.0,
        shift_ratio=1.37,
        sla=49.0,
        description="Western Louisville park-side neighborhoods with renovation-led permits and affordability overlays.",
        city_id="louisville",
    ),
    "Russell": SubmarketMeta(
        name="Russell",
        borough="WEST_PORTLAND",
        lat=38.2450,
        lng=-85.7950,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.77,
        capex=5100000.0,
        permit_vel=30.0,
        shift_ratio=1.41,
        sla=52.0,
        description="Historic West End neighborhood with new-construction and rehab permitting near the Portland renewal zone.",
        city_id="louisville",
    ),
}


LOUISVILLE_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_NULU": BoroughMeta(
        name="DOWNTOWN_NULU",
        center_lat=38.249,
        center_lng=-85.750,
        zoom=13.5,
        bbox=LOUISVILLE_DIVISION_BBOXES["DOWNTOWN_NULU"],
        submarkets=[k for k, v in LOUISVILLE_SUBMARKETS.items() if v.borough == "DOWNTOWN_NULU"],
        city_id="louisville",
    ),
    "HIGHLANDS_GERMANTOWN": BoroughMeta(
        name="HIGHLANDS_GERMANTOWN",
        center_lat=38.225,
        center_lng=-85.705,
        zoom=13.0,
        bbox=LOUISVILLE_DIVISION_BBOXES["HIGHLANDS_GERMANTOWN"],
        submarkets=[k for k, v in LOUISVILLE_SUBMARKETS.items() if v.borough == "HIGHLANDS_GERMANTOWN"],
        city_id="louisville",
    ),
    "CLIFTON_CRESCENT_HILL": BoroughMeta(
        name="CLIFTON_CRESCENT_HILL",
        center_lat=38.265,
        center_lng=-85.700,
        zoom=13.0,
        bbox=LOUISVILLE_DIVISION_BBOXES["CLIFTON_CRESCENT_HILL"],
        submarkets=[k for k, v in LOUISVILLE_SUBMARKETS.items() if v.borough == "CLIFTON_CRESCENT_HILL"],
        city_id="louisville",
    ),
    "OLD_LOUISVILLE_SHELBY_PARK": BoroughMeta(
        name="OLD_LOUISVILLE_SHELBY_PARK",
        center_lat=38.218,
        center_lng=-85.760,
        zoom=13.0,
        bbox=LOUISVILLE_DIVISION_BBOXES["OLD_LOUISVILLE_SHELBY_PARK"],
        submarkets=[k for k, v in LOUISVILLE_SUBMARKETS.items() if v.borough == "OLD_LOUISVILLE_SHELBY_PARK"],
        city_id="louisville",
    ),
    "ST_MATTHEWS_EAST": BoroughMeta(
        name="ST_MATTHEWS_EAST",
        center_lat=38.268,
        center_lng=-85.635,
        zoom=12.5,
        bbox=LOUISVILLE_DIVISION_BBOXES["ST_MATTHEWS_EAST"],
        submarkets=[k for k, v in LOUISVILLE_SUBMARKETS.items() if v.borough == "ST_MATTHEWS_EAST"],
        city_id="louisville",
    ),
    "WEST_PORTLAND": BoroughMeta(
        name="WEST_PORTLAND",
        center_lat=38.255,
        center_lng=-85.805,
        zoom=12.5,
        bbox=LOUISVILLE_DIVISION_BBOXES["WEST_PORTLAND"],
        submarkets=[k for k, v in LOUISVILLE_SUBMARKETS.items() if v.borough == "WEST_PORTLAND"],
        city_id="louisville",
    ),
}

# Verbose aliases mirroring the other city modules' verbose pairs.
GREATER_LOUISVILLE_METRO_BBOX = LOUISVILLE_METRO_BBOX
LOU_DIVISION_BBOXES = LOUISVILLE_DIVISION_BBOXES
LOU_SUBMARKETS = LOUISVILLE_SUBMARKETS
LOU_DIVISIONS = LOUISVILLE_DIVISIONS

# Exact DatasetSpec payloads for the registry spine. Dicts avoid importing
# city_registry.DatasetSpec while city_registry imports this module.
from src.producers.field_maps_louisville import (  # noqa: E402
    LOUISVILLE_311_FIELD_MAP,
    LOUISVILLE_SLA_FIELD_MAP,
)

LOUISVILLE_311_SPEC: Dict[str, object] = {
    "endpoint": "settings.arcgis_louisville_311_url",
    "platform": "arcgis",
    "watermark_col": "requested_datetime",
    "id_keys": ["service_request_id", "ObjectId"],
    "topic": "settings.topic_311",
    "interval_seconds": 180.0,
    "producer_key": "311",
    "extra": {
        "expected_cadence_days": 30,
        "oid_field": "ObjectId",
        "max_record_count": 2000,
        "annual_rotation": True,
        "scope": "Louisville Metro 311 service requests (2026 annual ArcGIS layer)",
        "field_map": LOUISVILLE_311_FIELD_MAP,
    },
}

LOUISVILLE_SLA_SPEC: Dict[str, object] = {
    "endpoint": "settings.arcgis_louisville_abc_url",
    "platform": "arcgis",
    "watermark_col": "IssueDate",
    "id_keys": ["LicenseNumber", "ObjectId"],
    "topic": "settings.topic_sla",
    "interval_seconds": 600.0,
    "producer_key": "sla",
    "extra": {
        "expected_cadence_days": 7,
        "oid_field": "ObjectId",
        "max_record_count": 2000,
        "where_clause": "County = 'Jefferson'",
        "scope": "Kentucky ABC active alcohol licenses in Jefferson County",
        "field_map": LOUISVILLE_SLA_FIELD_MAP,
    },
}
