"""Fort Worth / Tarrant County spatial registry and geometry.

Provides neighborhood metadata, submarket catalog, division bounding boxes, and
the Greater Fort Worth metropolitan extent for Urban Signal.

Fort Worth is registered as a **residential + commercial PERMITS** city (per the
US-150-style city-registration rule). The City of Fort Worth publishes building
permits as an ArcGIS FeatureServer — "CFW Development Permits Points"
(``mapit.fortworthtexas.gov/.../CIVIC/Permits/FeatureServer/0``) — with 759k+
point records in WGS84. The shared ArcGIS client requests ``outSR=4326`` so
``SHAPE__Y``/``SHAPE__X`` resolve directly to latitude/longitude; address
geocoding is retained only as a fallback for any geometry-less rows.

The PERMITS spec data below is the exact payload the spine ``city_registry.py``
copies into REGISTRY under ``CityId.FORT_WORTH``; it is declared here as data so
the spine edit is a pure copy.
"""

from typing import Dict

from src.producers.field_maps_fort_worth import FIELD_MAP as FORT_WORTH_PERMITS_FIELD_MAP
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Greater Fort Worth / Tarrant County core metro bounding box. Permissive: it
# only has to keep every live Fort Worth permit point inside (city center
# ~32.755, -97.33; edges span north Alliance ~32.90,-97.30 to Benbrook
# ~32.67,-97.57 and east toward the Arlington line ~-97.05).
FORT_WORTH_METRO_BBOX: Dict[str, float] = {
    "min_lat": 32.40,
    "max_lat": 33.05,
    "min_lng": -97.75,
    "max_lng": -96.95,
}

# Single Fort Worth division (city core). Hand-authored geography; borough
# resolution at ingest comes from coordinates via get_division_for_coordinate,
# so the bbox need only be sane and contain every submarket center.
FORT_WORTH_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "FORT_WORTH_CORE": {
        "min_lat": 32.55,
        "max_lat": 33.00,
        "min_lng": -97.65,
        "max_lng": -97.05,
    },
}


def is_in_fort_worth_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Fort Worth extent."""
    if lat is None or lng is None:
        return False
    return (
        FORT_WORTH_METRO_BBOX["min_lat"] <= lat <= FORT_WORTH_METRO_BBOX["max_lat"]
        and FORT_WORTH_METRO_BBOX["min_lng"] <= lng <= FORT_WORTH_METRO_BBOX["max_lng"]
    )


# Verbose alias kept for symmetry with the other city modules.
is_in_greater_fort_worth_metro = is_in_fort_worth_metro


FORT_WORTH_SUBMARKETS: Dict[str, SubmarketMeta] = {
    "Downtown & Sundance": SubmarketMeta(
        name="Downtown & Sundance",
        borough="FORT_WORTH_CORE",
        lat=32.7550,
        lng=-97.3300,
        zoom=14.2,
        pitch=52.0,
        base_lims=0.90,
        capex=12000000.0,
        permit_vel=58.0,
        shift_ratio=1.62,
        sla=68.0,
        description="Central business district and Sundance Square with mixed-use towers, hotel, and residential conversion permitting.",
        city_id="fort_worth",
    ),
    "Near Southside": SubmarketMeta(
        name="Near Southside",
        borough="FORT_WORTH_CORE",
        lat=32.7100,
        lng=-97.3200,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.85,
        capex=8200000.0,
        permit_vel=47.0,
        shift_ratio=1.55,
        sla=63.0,
        description="Medical-district-adjacent infill and adaptive-reuse neighborhood with steady residential and commercial permitting.",
        city_id="fort_worth",
    ),
    "Cultural District": SubmarketMeta(
        name="Cultural District",
        borough="FORT_WORTH_CORE",
        lat=32.7450,
        lng=-97.3650,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.87,
        capex=9800000.0,
        permit_vel=49.0,
        shift_ratio=1.58,
        sla=65.0,
        description="Museums, parks, and fabricating district with infill multifamily and hospitality permitting near the Trinity trails.",
        city_id="fort_worth",
    ),
    "TCU / West Cliff": SubmarketMeta(
        name="TCU / West Cliff",
        borough="FORT_WORTH_CORE",
        lat=32.7060,
        lng=-97.3650,
        zoom=13.8,
        pitch=44.0,
        base_lims=0.83,
        capex=7400000.0,
        permit_vel=43.0,
        shift_ratio=1.51,
        sla=61.0,
        description="University-adjacent streetcar-era neighborhoods with renovation-led and teardown/rebuild permitting.",
        city_id="fort_worth",
    ),
    "Arlington Heights & Hospital District": SubmarketMeta(
        name="Arlington Heights & Hospital District",
        borough="FORT_WORTH_CORE",
        lat=32.7350,
        lng=-97.3950,
        zoom=13.8,
        pitch=42.0,
        base_lims=0.82,
        capex=6900000.0,
        permit_vel=41.0,
        shift_ratio=1.49,
        sla=60.0,
        description="Established west-side residential corridors near the hospital district with steady redevelopment permitting.",
        city_id="fort_worth",
    ),
    "North Fort Worth / Alliance": SubmarketMeta(
        name="North Fort Worth / Alliance",
        borough="FORT_WORTH_CORE",
        lat=32.9000,
        lng=-97.3000,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.84,
        capex=7800000.0,
        permit_vel=45.0,
        shift_ratio=1.52,
        sla=62.0,
        description="High-growth northern edge around the Alliance logistics corridor with master-planned residential and industrial permitting.",
        city_id="fort_worth",
    ),
}


FORT_WORTH_DIVISIONS: Dict[str, BoroughMeta] = {
    "FORT_WORTH_CORE": BoroughMeta(
        name="Fort Worth Core",
        center_lat=32.76,
        center_lng=-97.33,
        zoom=11.8,
        bbox=FORT_WORTH_DIVISION_BBOXES["FORT_WORTH_CORE"],
        submarkets=list(FORT_WORTH_SUBMARKETS),
        city_id="fort_worth",
    ),
}

# Exact PERMITS DatasetSpec payload for the spine REGISTRY entry
# (CityId.FORT_WORTH). Mirrors the shape used by every other city;
# `extra["field_map"]` wires the per-city spellings from
# `field_maps_fort_worth.FIELD_MAP`, and `needs_geocode: True` flips the
# coordinate requirement so any geometry-less rows resolve via the ADR-0004
# geocoder (the point layer itself carries WGS84 geometry).
FORT_WORTH_PERMITS_SPEC: Dict[str, object] = {
    "endpoint": "settings.arcgis_fort_worth_permits_url",
    "platform": "arcgis",
    "watermark_col": "File_Date",
    "id_keys": ["Unique_ID", "Permit_No", "OBJECTID"],
    "topic": "settings.topic_permits",
    "interval_seconds": 300.0,
    "producer_key": "permits",
    "extra": {
        "expected_cadence_days": 7,
        "needs_geocode": True,
        "geocode_context": "Fort Worth, TX",
        "scope": "Building, mechanical, plumbing, and grading permits via CFW Development Permits Points (ArcGIS WGS84 point layer)",
        "oid_field": "OBJECTID",
        "max_record_count": 1000,
        "order_by": "File_Date DESC",
        "field_map": FORT_WORTH_PERMITS_FIELD_MAP,
    },
}

# Aliases for symmetry with other modules' verbose spellings.
GREATER_FORT_WORTH_METRO_BBOX = FORT_WORTH_METRO_BBOX
FORT_WORTH_DIVISION_BBOXES = FORT_WORTH_DIVISION_BBOXES
FORT_WORTH_DIVISIONS = FORT_WORTH_DIVISIONS
FORT_WORTH_SUBMARKETS = FORT_WORTH_SUBMARKETS


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=FORT_WORTH_METRO_BBOX,
    division_bboxes=FORT_WORTH_DIVISION_BBOXES,
    submarkets=FORT_WORTH_SUBMARKETS,
    divisions=FORT_WORTH_DIVISIONS,
    contains=is_in_fort_worth_metro,
)
