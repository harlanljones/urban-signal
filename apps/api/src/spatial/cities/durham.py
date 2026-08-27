"""Durham, NC spatial registry and geometry.

Provides neighborhood metadata, submarket catalog, division bounding boxes, and
the Greater Durham metropolitan extent for Urban Signal.

Durham registers as a **two-feed partial city** (US-154): PERMITS
(``PublicServices/Inspections/MapServer/12`` "All Building Permits") and DEEDS
(``PublicServices/Property/MapServer/4`` "Parcels"). Both are live ArcGIS layers
on the City of Durham Open Data / GIS portal (``webgis2.durhamnc.gov``) and are
carried by the existing ArcGIS-backed shared producers via registry +
``field_map`` — no new producer archetype is required. Durham publishes no
open 311 / SLA-quality feed at the same tier, so those feeds are deliberately
absent (LA / Austin partial-city pattern) and ``get_dataset`` raises a readable
error for them.

The PERMITS / DEEDS spec payloads below are the exact data the spine
``city_registry.py`` copies into REGISTRY under ``CityId.DURHAM``; they are
declared here as data (mirroring ``src/spatial/cities/boise.py``) so the spine
edit is a pure copy and the module stays import-cycle-free (it never imports
``city_registry``).
"""

from typing import Dict

from src.producers.field_maps_durham import FIELD_MAP as DURHAM_FIELD_MAP
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Greater Durham metro bounding box. Permissive: it only has to keep every live
# Durham sample inside (downtown ~35.994, -78.899; Duke West Campus ~35.997,
# -78.939; North Durham ~36.08, -78.89; Southpoint ~35.905, -78.905; Eno River
# edge ~36.02, -78.965).
DURHAM_METRO_BBOX: Dict[str, float] = {
    "min_lat": 35.88,
    "max_lat": 36.18,
    "min_lng": -78.99,
    "max_lng": -78.78,
}

# 5 Durham Division Bounding Boxes. Hand-authored geographies; borough resolution
# at ingest comes from coordinates via get_division_for_coordinate, so bboxes
# need only be sane and contain every submarket center, and nest inside the metro
# bbox.
DURHAM_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_DUKE": {
        "min_lat": 35.97,
        "max_lat": 36.02,
        "min_lng": -78.94,
        "max_lng": -78.88,
    },
    "NORTH_DURHAM": {
        "min_lat": 36.02,
        "max_lat": 36.13,
        "min_lng": -78.92,
        "max_lng": -78.82,
    },
    "EAST_DURHAM": {
        "min_lat": 35.99,
        "max_lat": 36.05,
        "min_lng": -78.87,
        "max_lng": -78.80,
    },
    "SOUTH_DURHAM": {
        "min_lat": 35.88,
        "max_lat": 35.99,
        "min_lng": -78.95,
        "max_lng": -78.82,
    },
    "WEST_DURHAM": {
        "min_lat": 35.99,
        "max_lat": 36.06,
        "min_lng": -78.99,
        "max_lng": -78.94,
    },
}


def is_in_durham_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Durham extent."""
    if lat is None or lng is None:
        return False
    return (
        DURHAM_METRO_BBOX["min_lat"] <= lat <= DURHAM_METRO_BBOX["max_lat"]
        and DURHAM_METRO_BBOX["min_lng"] <= lng <= DURHAM_METRO_BBOX["max_lng"]
    )


# Alias kept for symmetry with the other city modules' verbose spellings.
is_in_greater_durham_metro = is_in_durham_metro


DURHAM_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_DUKE (4 Submarkets)
    # =======================================================================
    "Downtown Durham": SubmarketMeta(
        name="Downtown Durham",
        borough="DOWNTOWN_DUKE",
        lat=35.9940,
        lng=-78.8986,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.91,
        capex=11500000.0,
        permit_vel=54.0,
        shift_ratio=1.62,
        sla=68.0,
        description="City-core of Durham's revitalization with tower, office-to-residential, and hospitality permitting around the ballpark and Main Street.",
        city_id="durham",
    ),
    "Duke University & West Campus": SubmarketMeta(
        name="Duke University & West Campus",
        borough="DOWNTOWN_DUKE",
        lat=35.9970,
        lng=-78.9390,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.89,
        capex=10200000.0,
        permit_vel=41.0,
        shift_ratio=1.55,
        sla=64.0,
        description="University-anchored edge with institutional demand, graduate-housing construction, and West Campus expansion permits.",
        city_id="durham",
    ),
    "Ninth Street District": SubmarketMeta(
        name="Ninth Street District",
        borough="DOWNTOWN_DUKE",
        lat=35.9970,
        lng=-78.9300,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=7800000.0,
        permit_vel=38.0,
        shift_ratio=1.5,
        sla=61.0,
        description="Corridor of retail, student housing, and mixed-use infill between downtown and the Duke campus.",
        city_id="durham",
    ),
    "Trinity Park & Old West Durham": SubmarketMeta(
        name="Trinity Park & Old West Durham",
        borough="DOWNTOWN_DUKE",
        lat=35.9990,
        lng=-78.9180,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.86,
        capex=8200000.0,
        permit_vel=36.0,
        shift_ratio=1.48,
        sla=60.0,
        description="Historic streetcar-era bungalow districts with renovation-led permitting and neighborhood-conservation overlays.",
        city_id="durham",
    ),
    # =======================================================================
    # NORTH_DURHAM (3 Submarkets)
    # =======================================================================
    "Northgate & Duke North": SubmarketMeta(
        name="Northgate & Duke North",
        borough="NORTH_DURHAM",
        lat=36.0580,
        lng=-78.9050,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.8,
        capex=6400000.0,
        permit_vel=33.0,
        shift_ratio=1.42,
        sla=55.0,
        description="Northern growth edge with master-planned residential and North Durham commercial redevelopment near the beltline.",
        city_id="durham",
    ),
    "Roxboro Road Corridor": SubmarketMeta(
        name="Roxboro Road Corridor",
        borough="NORTH_DURHAM",
        lat=36.0800,
        lng=-78.8900,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.77,
        capex=5600000.0,
        permit_vel=30.0,
        shift_ratio=1.39,
        sla=53.0,
        description="Arterial corridor with infill multifamily, aging retail teardown/rebuild, and transit-adjacent reinvestment.",
        city_id="durham",
    ),
    "Bahama & Northern Edge": SubmarketMeta(
        name="Bahama & Northern Edge",
        borough="NORTH_DURHAM",
        lat=36.1100,
        lng=-78.8600,
        zoom=12.5,
        pitch=38.0,
        base_lims=0.6,
        capex=3200000.0,
        permit_vel=22.0,
        shift_ratio=1.22,
        sla=40.0,
        description="Exurban northern boundary of the metro with low-volume, high-lot residential permitting.",
        city_id="durham",
    ),
    # =======================================================================
    # EAST_DURHAM (3 Submarkets)
    # =======================================================================
    "East Durham & Holloway": SubmarketMeta(
        name="East Durham & Holloway",
        borough="EAST_DURHAM",
        lat=36.0050,
        lng=-78.8550,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=5900000.0,
        permit_vel=34.0,
        shift_ratio=1.41,
        sla=54.0,
        description="Established inner-ring neighborhoods with storefront renewal, infill housing, and corridor-scale improvement.",
        city_id="durham",
    ),
    "Wheeler Hill": SubmarketMeta(
        name="Wheeler Hill",
        borough="EAST_DURHAM",
        lat=35.9950,
        lng=-78.8400,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.75,
        capex=5200000.0,
        permit_vel=31.0,
        shift_ratio=1.37,
        sla=52.0,
        description="Hill-edge residential district with renovation capital and steady teardown/rebuild pressure.",
        city_id="durham",
    ),
    "Lyon Park": SubmarketMeta(
        name="Lyon Park",
        borough="EAST_DURHAM",
        lat=36.0200,
        lng=-78.8350,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.74,
        capex=5000000.0,
        permit_vel=29.0,
        shift_ratio=1.36,
        sla=51.0,
        description="Transitional east-side neighborhood with housing rehabilitation and small-lot development.",
        city_id="durham",
    ),
    # =======================================================================
    # SOUTH_DURHAM (4 Submarkets)
    # =======================================================================
    "Southpoint & 15-501": SubmarketMeta(
        name="Southpoint & 15-501",
        borough="SOUTH_DURHAM",
        lat=35.9050,
        lng=-78.9050,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.88,
        capex=9800000.0,
        permit_vel=47.0,
        shift_ratio=1.56,
        sla=62.0,
        description="Southern retail and mixed-use hub with continued multifamily and commercial permitting around the 15-501 / 54 interchange.",
        city_id="durham",
    ),
    "Hope Valley & Croasdaile": SubmarketMeta(
        name="Hope Valley & Croasdaile",
        borough="SOUTH_DURHAM",
        lat=35.9400,
        lng=-78.9200,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.82,
        capex=6900000.0,
        permit_vel=35.0,
        shift_ratio=1.45,
        sla=57.0,
        description="Established southwest neighborhoods with renovation-led permits and estate-stock teardown/rebuild.",
        city_id="durham",
    ),
    "Lakewood & Woodcroft": SubmarketMeta(
        name="Lakewood & Woodcroft",
        borough="SOUTH_DURHAM",
        lat=35.9700,
        lng=-78.9300,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.8,
        capex=6200000.0,
        permit_vel=33.0,
        shift_ratio=1.43,
        sla=56.0,
        description="Southwest residential hills with infill housing and corridor densification near Duke and Southpoint.",
        city_id="durham",
    ),
    "Research Triangle Park Edge": SubmarketMeta(
        name="Research Triangle Park Edge",
        borough="SOUTH_DURHAM",
        lat=35.9000,
        lng=-78.8700,
        zoom=12.5,
        pitch=40.0,
        base_lims=0.84,
        capex=8800000.0,
        permit_vel=39.0,
        shift_ratio=1.47,
        sla=58.0,
        description="Southern edge shading into Research Triangle Park with employment-adjacent commercial and residential permitting.",
        city_id="durham",
    ),
    # =======================================================================
    # WEST_DURHAM (2 Submarkets)
    # =======================================================================
    "Eno River & Hillsborough Rd": SubmarketMeta(
        name="Eno River & Hillsborough Rd",
        borough="WEST_DURHAM",
        lat=36.0200,
        lng=-78.9650,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.73,
        capex=4800000.0,
        permit_vel=27.0,
        shift_ratio=1.35,
        sla=49.0,
        description="Northwest river-edge edge with protected greenway, estate stock, and limited new-construction pressure.",
        city_id="durham",
    ),
    "Parkwood": SubmarketMeta(
        name="Parkwood",
        borough="WEST_DURHAM",
        lat=35.9950,
        lng=-78.9550,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.38,
        sla=53.0,
        description="Post-war west-side residential corridor with steady redevelopment and corridor densification.",
        city_id="durham",
    ),
}


DURHAM_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_DUKE": BoroughMeta(
        name="Downtown / Duke",
        center_lat=35.995,
        center_lng=-78.91,
        zoom=13.5,
        bbox=DURHAM_DIVISION_BBOXES["DOWNTOWN_DUKE"],
        submarkets=[k for k, v in DURHAM_SUBMARKETS.items() if v.borough == "DOWNTOWN_DUKE"],
        city_id="durham",
    ),
    "NORTH_DURHAM": BoroughMeta(
        name="North Durham",
        center_lat=36.06,
        center_lng=-78.88,
        zoom=12.5,
        bbox=DURHAM_DIVISION_BBOXES["NORTH_DURHAM"],
        submarkets=[k for k, v in DURHAM_SUBMARKETS.items() if v.borough == "NORTH_DURHAM"],
        city_id="durham",
    ),
    "EAST_DURHAM": BoroughMeta(
        name="East Durham",
        center_lat=36.01,
        center_lng=-78.84,
        zoom=13.0,
        bbox=DURHAM_DIVISION_BBOXES["EAST_DURHAM"],
        submarkets=[k for k, v in DURHAM_SUBMARKETS.items() if v.borough == "EAST_DURHAM"],
        city_id="durham",
    ),
    "SOUTH_DURHAM": BoroughMeta(
        name="South Durham",
        center_lat=35.93,
        center_lng=-78.90,
        zoom=12.5,
        bbox=DURHAM_DIVISION_BBOXES["SOUTH_DURHAM"],
        submarkets=[k for k, v in DURHAM_SUBMARKETS.items() if v.borough == "SOUTH_DURHAM"],
        city_id="durham",
    ),
    "WEST_DURHAM": BoroughMeta(
        name="West Durham",
        center_lat=36.00,
        center_lng=-78.96,
        zoom=12.5,
        bbox=DURHAM_DIVISION_BBOXES["WEST_DURHAM"],
        submarkets=[k for k, v in DURHAM_SUBMARKETS.items() if v.borough == "WEST_DURHAM"],
        city_id="durham",
    ),
}

# Exact PERMITS / DEEDS DatasetSpec payloads for the spine REGISTRY entry
# (CityId.DURHAM). Mirrors the shape used by boise.py: ``extra["field_map"]``
# wires the per-city spellings from ``field_maps_durham.FIELD_MAP``, and the
# ArcGIS ``oid_field`` pins the layer's true object-id field. The ``endpoint`` /
# ``topic`` values are written here as the settings attribute names the spine
# copies verbatim into ``settings.<name>`` references.
DURHAM_PERMITS_SPEC: Dict[str, object] = {
    "endpoint": "settings.arcgis_durham_permits_url",
    "platform": "arcgis",
    "watermark_col": "ISSUE_DATE",
    "id_keys": ["PermitNum", "OBJECTID", "id"],
    "topic": "settings.topic_permits",
    "interval_seconds": 300.0,
    "producer_key": "permits",
    "extra": {
        "expected_cadence_days": 7,
        "scope": "Durham (NC) building permits; Point geometry lifted to lat/lng by ArcGISClient",
        "oid_field": "OBJECTID",
        "max_record_count": 1000,
        "field_map": DURHAM_FIELD_MAP["permits"],
    },
}

DURHAM_DEEDS_SPEC: Dict[str, object] = {
    "endpoint": "settings.arcgis_durham_deeds_url",
    "platform": "arcgis",
    "watermark_col": "DEED_DATE",
    "id_keys": ["REID", "PIN", "PARCEL_PK", "OBJECTID_1", "id"],
    "topic": "settings.topic_deeds",
    "interval_seconds": 600.0,
    "producer_key": "deeds",
    "extra": {
        "expected_cadence_days": 7,
        "scope": "Durham (NC) parcel sales/deeds; Polygon centroid lifted to lat/lng by ArcGISClient",
        "oid_field": "OBJECTID_1",
        "max_record_count": 1000,
        "field_map": DURHAM_FIELD_MAP["deeds"],
    },
}

# Verbose aliases mirroring the other city modules' *_METRO_BBOX / *_* pairings.
GREATER_DURHAM_METRO_BBOX = DURHAM_METRO_BBOX
DURHAM_DIVISION_BBOXES = DURHAM_DIVISION_BBOXES
DURHAM_DIVISIONS = DURHAM_DIVISIONS
DURHAM_SUBMARKETS = DURHAM_SUBMARKETS


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=DURHAM_METRO_BBOX,
    division_bboxes=DURHAM_DIVISION_BBOXES,
    submarkets=DURHAM_SUBMARKETS,
    divisions=DURHAM_DIVISIONS,
    contains=is_in_durham_metro,
)
