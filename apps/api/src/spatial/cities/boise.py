"""Boise / Ada County spatial registry and geometry.

Provides neighborhood metadata, submarket catalog, division bounding boxes, and
the Greater Boise metropolitan extent for Urban Signal.

Boise is registered as a **residential-only, thin, single-feed** city (see
US-150 / AGENTS.md city-registration rule). The City of Boise Open Data Hub
publishes building permits as an ArcGIS FeatureServer whose layer metadata
advertises Idaho state-plane geometry (WKID 102459). The shared ArcGIS client
requests WGS84 output for H3 indexing, with the ADR-0004 geocoder as a fallback.
No 311/SLA/DEEDS feeds are published at open-data quality, so only PERMITS is
registered.

The PERMITS spec data below is the exact payload the spine `city_registry.py`
copies into REGISTRY under `CityId.BOISE`; it is declared here as data so the
spine edit is a pure copy.
"""

from typing import Dict

from src.producers.field_maps_boise import FIELD_MAP as BOISE_PERMITS_FIELD_MAP
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Greater Boise / Ada County metro bounding box. Permissive: it only has to keep
# every live Ada County sample inside (downtown ~43.613, -116.211; NW Boise
# ~43.66, -116.28; SE ~43.53, -116.16; Eagle edge ~43.69, -116.35).
BOISE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 43.43,
    "max_lat": 43.74,
    "min_lng": -116.42,
    "max_lng": -116.03,
}

# Single Boise division (Ada County core). Hand-authored geography; borough
# resolution at ingest comes from coordinates via get_division_for_coordinate,
# so the bbox need only be sane and contain every submarket center.
BOISE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "BOISE_CORE": {
        "min_lat": 43.50,
        "max_lat": 43.70,
        "min_lng": -116.34,
        "max_lng": -116.08,
    },
}


def is_in_boise_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Boise extent."""
    if lat is None or lng is None:
        return False
    return (
        BOISE_METRO_BBOX["min_lat"] <= lat <= BOISE_METRO_BBOX["max_lat"]
        and BOISE_METRO_BBOX["min_lng"] <= lng <= BOISE_METRO_BBOX["max_lng"]
    )


# Verbose alias kept for symmetry with the other city modules.
is_in_greater_boise_metro = is_in_boise_metro


BOISE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    "Downtown & Capitol": SubmarketMeta(
        name="Downtown & Capitol",
        borough="BOISE_CORE",
        lat=43.6165,
        lng=-116.2140,
        zoom=14.2,
        pitch=52.0,
        base_lims=0.88,
        capex=9800000.0,
        permit_vel=51.0,
        shift_ratio=1.58,
        sla=66.0,
        description="State-government and riverfront core with dense residential conversion and mixed-use infill along the Boise River.",
        city_id="boise",
    ),
    "North End & Hyde Park": SubmarketMeta(
        name="North End & Hyde Park",
        borough="BOISE_CORE",
        lat=43.6570,
        lng=-116.2360,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.84,
        capex=7600000.0,
        permit_vel=44.0,
        shift_ratio=1.52,
        sla=62.0,
        description="Historic streetcar-era bungalow district with renovation-led permitting and neighborhood-conservation overlays.",
        city_id="boise",
    ),
    "Boise Bench & South Cole": SubmarketMeta(
        name="Boise Bench & South Cole",
        borough="BOISE_CORE",
        lat=43.5800,
        lng=-116.2300,
        zoom=13.6,
        pitch=42.0,
        base_lims=0.80,
        capex=5800000.0,
        permit_vel=36.0,
        shift_ratio=1.46,
        sla=58.0,
        description="Post-war residential bench south of the core with teardown/rebuild pressure and infill multifamily.",
        city_id="boise",
    ),
    "East Boise & Harris Ranch": SubmarketMeta(
        name="East Boise & Harris Ranch",
        borough="BOISE_CORE",
        lat=43.6000,
        lng=-116.1000,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.82,
        capex=6400000.0,
        permit_vel=39.0,
        shift_ratio=1.49,
        sla=59.0,
        description="East-growth edge with master-planned residential subdivisions and new-construction permitting.",
        city_id="boise",
    ),
    "West Boise & Vista": SubmarketMeta(
        name="West Boise & Vista",
        borough="BOISE_CORE",
        lat=43.5900,
        lng=-116.2800,
        zoom=13.2,
        pitch=42.0,
        base_lims=0.79,
        capex=5200000.0,
        permit_vel=32.0,
        shift_ratio=1.44,
        sla=56.0,
        description="Established west-side residential corridors with steady redevelopment and corridor densification.",
        city_id="boise",
    ),
    "BoDo & Riverfront": SubmarketMeta(
        name="BoDo & Riverfront",
        borough="BOISE_CORE",
        lat=43.6090,
        lng=-116.2060,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.86,
        capex=8900000.0,
        permit_vel=48.0,
        shift_ratio=1.55,
        sla=64.0,
        description="Boise Downtown / riverfront entertainment district with hotel, retail, and residential tower permitting.",
        city_id="boise",
    ),
}


BOISE_DIVISIONS: Dict[str, BoroughMeta] = {
    "BOISE_CORE": BoroughMeta(
        name="Boise Core",
        center_lat=43.61,
        center_lng=-116.21,
        zoom=11.8,
        bbox=BOISE_DIVISION_BBOXES["BOISE_CORE"],
        submarkets=list(BOISE_SUBMARKETS),
        city_id="boise",
    ),
}

# Exact PERMITS DatasetSpec payload for the spine REGISTRY entry (CityId.BOISE).
# Mirrors the shape used by every other city; `extra["field_map"]` wires the
# per-city spellings from `field_maps_boise.FIELD_MAP`, and `needs_geocode: True`
# flips the coordinate requirement so rows resolve via the ADR-0004 geocoder.
BOISE_PERMITS_SPEC: Dict[str, object] = {
    "endpoint": "settings.arcgis_boise_permits_url",
    "platform": "arcgis",
    "watermark_col": "IssuedDate",
    "id_keys": ["RecordID", "OBJECTID", "id"],
    "topic": "settings.topic_permits",
    "interval_seconds": 300.0,
    "producer_key": "permits",
    "extra": {
        "expected_cadence_days": 7,
        "needs_geocode": True,
        "geocode_context": "Boise, ID",
        "scope": "Residential-only building permits; ArcGIS state-plane source requested as WGS84 with address fallback",
        "oid_field": "OBJECTID",
        "max_record_count": 2000,
        "order_by": "IssuedDate DESC",
        "field_map": BOISE_PERMITS_FIELD_MAP,
    },
}

# Aliases for symmetry with other modules' verbose spellings.
GREATER_BOISE_METRO_BBOX = BOISE_METRO_BBOX
BOISE_DIVISION_BBOXES = BOISE_DIVISION_BBOXES
BOISE_DIVISIONS = BOISE_DIVISIONS
BOISE_SUBMARKETS = BOISE_SUBMARKETS
