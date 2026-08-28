"""Melbourne / Palm Bay / Titusville (Brevard County, FL) metro configuration.

Provides neighborhood metadata, camera positioning, division catalog, and
geographic bounding boxes for the south‑central Brevard County metro anchored
by Melbourne and Palm Bay, with Titusville at the north end and the barrier‑
island beach communities east of the Indian River Lagoon.

Fit: High (US-296). ArcGIS public permits verified via Brevard GIS Hub.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Canonical, stable city id for Melbourne / Palm Bay metro
MELBOURNE_CITY_ID: str = "melbourne"

# Metro bbox: permissive bounds covering Palm Bay (south) through Titusville
# (north), including the barrier islands from Indialantic/Satellite Beach up
# to the Titusville/Cape Canaveral approach.
MELBOURNE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 27.88,
    "max_lat": 28.72,
    "min_lng": -80.90,
    "max_lng": -80.40,
}

# Hand-authored division bboxes — broad disjoint envelopes that unambiguously
# contain their own submarket centers and nest within the metro bbox.
MELBOURNE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "MELBOURNE_CORE":         {"min_lat": 28.03, "max_lat": 28.18, "min_lng": -80.70, "max_lng": -80.55},
    "PALM_BAY_SOUTH":         {"min_lat": 27.90, "max_lat": 28.05, "min_lng": -80.75, "max_lng": -80.58},
    "BEACH_BARRIER":          {"min_lat": 28.04, "max_lat": 28.28, "min_lng": -80.62, "max_lng": -80.52},
    "VIERA_SUNTREE":          {"min_lat": 28.18, "max_lat": 28.36, "min_lng": -80.80, "max_lng": -80.58},
    "TITUSVILLE_NORTH":       {"min_lat": 28.50, "max_lat": 28.70, "min_lng": -80.90, "max_lng": -80.70},
}


def is_in_melbourne_metro(lat: float, lng: float) -> bool:
    """Return True when a coordinate lies within the Melbourne/Palm Bay metro."""
    if lat is None or lng is None:
        return False
    return (
        MELBOURNE_METRO_BBOX["min_lat"] <= lat <= MELBOURNE_METRO_BBOX["max_lat"]
        and MELBOURNE_METRO_BBOX["min_lng"] <= lng <= MELBOURNE_METRO_BBOX["max_lng"]
    )


# Alias retained for symmetry with other city modules
is_in_greater_melbourne_metro = is_in_melbourne_metro


MELBOURNE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # MELBOURNE_CORE (3)
    # =======================================================================
    "Downtown Melbourne": SubmarketMeta(
        name="Downtown Melbourne",
        borough="MELBOURNE_CORE",
        lat=28.078,
        lng=-80.608,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.86,
        capex=7200000.0,
        permit_vel=30.0,
        shift_ratio=1.45,
        sla=60.0,
        description="Historic downtown along New Haven Ave with infill mixed-use and renovation permits.",
        city_id=MELBOURNE_CITY_ID,
    ),
    "Eau Gallie Arts District": SubmarketMeta(
        name="Eau Gallie Arts District",
        borough="MELBOURNE_CORE",
        lat=28.128,
        lng=-80.626,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.84,
        capex=6400000.0,
        permit_vel=27.0,
        shift_ratio=1.41,
        sla=58.0,
        description="EGAD waterfront arts district with adaptive reuse and small‑format retail licensing.",
        city_id=MELBOURNE_CITY_ID,
    ),
    "West Melbourne Gateway": SubmarketMeta(
        name="West Melbourne Gateway",
        borough="MELBOURNE_CORE",
        lat=28.071,
        lng=-80.660,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.78,
        capex=5200000.0,
        permit_vel=24.0,
        shift_ratio=1.34,
        sla=52.0,
        description="West Melbourne retail/industrial edge and SR‑192 corridor redevelopment.",
        city_id=MELBOURNE_CITY_ID,
    ),
    # =======================================================================
    # PALM_BAY_SOUTH (3)
    # =======================================================================
    "Palm Bay Center": SubmarketMeta(
        name="Palm Bay Center",
        borough="PALM_BAY_SOUTH",
        lat=28.034,
        lng=-80.620,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.82,
        capex=6000000.0,
        permit_vel=26.0,
        shift_ratio=1.38,
        sla=56.0,
        description="Palm Bay municipal center and Malabar Road corridor with steady renovation permitting.",
        city_id=MELBOURNE_CITY_ID,
    ),
    "Malabar & South Babcock": SubmarketMeta(
        name="Malabar & South Babcock",
        borough="PALM_BAY_SOUTH",
        lat=27.990,
        lng=-80.623,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.74,
        capex=4200000.0,
        permit_vel=20.0,
        shift_ratio=1.28,
        sla=48.0,
        description="South Palm Bay neighborhoods around Malabar Road and Babcock Street.",
        city_id=MELBOURNE_CITY_ID,
    ),
    "St. Johns Heritage Parkway": SubmarketMeta(
        name="St. Johns Heritage Parkway",
        borough="PALM_BAY_SOUTH",
        lat=27.965,
        lng=-80.678,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.70,
        capex=3800000.0,
        permit_vel=18.0,
        shift_ratio=1.24,
        sla=45.0,
        description="Exurban growth corridor west of I‑95 with single‑family subdivision activity.",
        city_id=MELBOURNE_CITY_ID,
    ),
    # =======================================================================
    # BEACH_BARRIER (3)
    # =======================================================================
    "Indialantic & Indian Harbour": SubmarketMeta(
        name="Indialantic & Indian Harbour",
        borough="BEACH_BARRIER",
        lat=28.109,
        lng=-80.577,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.88,
        capex=9600000.0,
        permit_vel=34.0,
        shift_ratio=1.50,
        sla=64.0,
        description="Barrier‑island beachfront communities with teardowns, additions, and hospitality licensing.",
        city_id=MELBOURNE_CITY_ID,
    ),
    "Satellite Beach": SubmarketMeta(
        name="Satellite Beach",
        borough="BEACH_BARRIER",
        lat=28.176,
        lng=-80.593,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.84,
        capex=7400000.0,
        permit_vel=28.0,
        shift_ratio=1.42,
        sla=58.0,
        description="Mid‑island coastal neighborhoods with renovations and small mixed‑use infill.",
        city_id=MELBOURNE_CITY_ID,
    ),
    "Patrick & South Beaches": SubmarketMeta(
        name="Patrick & South Beaches",
        borough="BEACH_BARRIER",
        lat=28.070,
        lng=-80.565,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=5200000.0,
        permit_vel=22.0,
        shift_ratio=1.30,
        sla=50.0,
        description="South beaches and Patrick SFB edge; lower‑volume, higher‑value residential work.",
        city_id=MELBOURNE_CITY_ID,
    ),
    # =======================================================================
    # VIERA_SUNTREE (2)
    # =======================================================================
    "Viera Town Center": SubmarketMeta(
        name="Viera Town Center",
        borough="VIERA_SUNTREE",
        lat=28.243,
        lng=-80.728,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.82,
        capex=7800000.0,
        permit_vel=32.0,
        shift_ratio=1.40,
        sla=58.0,
        description="Planned town‑center mixed‑use and institutional buildout west of I‑95.",
        city_id=MELBOURNE_CITY_ID,
    ),
    "Suntree": SubmarketMeta(
        name="Suntree",
        borough="VIERA_SUNTREE",
        lat=28.210,
        lng=-80.673,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=24.0,
        shift_ratio=1.32,
        sla=52.0,
        description="Established golf‑course community with steady renovation permitting.",
        city_id=MELBOURNE_CITY_ID,
    ),
    # =======================================================================
    # TITUSVILLE_NORTH (2)
    # =======================================================================
    "Titusville Historic Core": SubmarketMeta(
        name="Titusville Historic Core",
        borough="TITUSVILLE_NORTH",
        lat=28.613,
        lng=-80.807,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=25.0,
        shift_ratio=1.36,
        sla=54.0,
        description="US‑1 riverfront historic core with adaptive reuse and small hospitality licensing.",
        city_id=MELBOURNE_CITY_ID,
    ),
    "Mims & Space Coast Gateway": SubmarketMeta(
        name="Mims & Space Coast Gateway",
        borough="TITUSVILLE_NORTH",
        lat=28.650,
        lng=-80.840,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.70,
        capex=4000000.0,
        permit_vel=18.0,
        shift_ratio=1.24,
        sla=46.0,
        description="Northern gateway communities with industrial and logistics permitting along I‑95.",
        city_id=MELBOURNE_CITY_ID,
    ),
}


MELBOURNE_DIVISIONS: Dict[str, BoroughMeta] = {
    "MELBOURNE_CORE": BoroughMeta(
        name="MELBOURNE_CORE",
        center_lat=28.105,
        center_lng=-80.620,
        zoom=13.5,
        bbox=MELBOURNE_DIVISION_BBOXES["MELBOURNE_CORE"],
        submarkets=[k for k, v in MELBOURNE_SUBMARKETS.items() if v.borough == "MELBOURNE_CORE"],
        city_id=MELBOURNE_CITY_ID,
    ),
    "PALM_BAY_SOUTH": BoroughMeta(
        name="PALM_BAY_SOUTH",
        center_lat=28.000,
        center_lng=-80.640,
        zoom=13.0,
        bbox=MELBOURNE_DIVISION_BBOXES["PALM_BAY_SOUTH"],
        submarkets=[k for k, v in MELBOURNE_SUBMARKETS.items() if v.borough == "PALM_BAY_SOUTH"],
        city_id=MELBOURNE_CITY_ID,
    ),
    "BEACH_BARRIER": BoroughMeta(
        name="BEACH_BARRIER",
        center_lat=28.140,
        center_lng=-80.580,
        zoom=13.0,
        bbox=MELBOURNE_DIVISION_BBOXES["BEACH_BARRIER"],
        submarkets=[k for k, v in MELBOURNE_SUBMARKETS.items() if v.borough == "BEACH_BARRIER"],
        city_id=MELBOURNE_CITY_ID,
    ),
    "VIERA_SUNTREE": BoroughMeta(
        name="VIERA_SUNTREE",
        center_lat=28.255,
        center_lng=-80.690,
        zoom=12.8,
        bbox=MELBOURNE_DIVISION_BBOXES["VIERA_SUNTREE"],
        submarkets=[k for k, v in MELBOURNE_SUBMARKETS.items() if v.borough == "VIERA_SUNTREE"],
        city_id=MELBOURNE_CITY_ID,
    ),
    "TITUSVILLE_NORTH": BoroughMeta(
        name="TITUSVILLE_NORTH",
        center_lat=28.610,
        center_lng=-80.800,
        zoom=12.8,
        bbox=MELBOURNE_DIVISION_BBOXES["TITUSVILLE_NORTH"],
        submarkets=[k for k, v in MELBOURNE_SUBMARKETS.items() if v.borough == "TITUSVILLE_NORTH"],
        city_id=MELBOURNE_CITY_ID,
    ),
}

# Verbose aliases mirroring other city modules
GREATER_MELBOURNE_METRO_BBOX = MELBOURNE_METRO_BBOX
MLB_DIVISION_BBOXES = MELBOURNE_DIVISION_BBOXES
MLB_SUBMARKETS = MELBOURNE_SUBMARKETS
MLB_DIVISIONS = MELBOURNE_DIVISIONS


# Leaf-local feed notes (for parity with other city modules):
# Brevard County Building Permits (2010‑Present), ArcGIS FeatureServer layer 0:
# https://services6.arcgis.com/Yx1h0qHJ9wIpQWuU/arcgis/rest/services/Building_Permits_Public/FeatureServer/0
# Watermark: ISSUEDATE; OID field: OBJECTID0; max_record_count: 1000
# SLA fallback: USDA SNAP Retailers (state = 'FL') via snap_sla_spec("FL")

from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=MELBOURNE_METRO_BBOX,
    division_bboxes=MELBOURNE_DIVISION_BBOXES,
    submarkets=MELBOURNE_SUBMARKETS,
    divisions=MELBOURNE_DIVISIONS,
    contains=is_in_melbourne_metro,
)

