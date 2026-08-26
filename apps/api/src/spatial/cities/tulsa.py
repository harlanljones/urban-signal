"""Tulsa, Oklahoma spatial registry and geometry.

Tulsa registers as a single-feed, rolling-window city (US-158): only
COMPLAINTS_311 is published, as the City of Tulsa's Verint customer-care cases
(`CustomerCare/VerintCasesPublic/FeatureServer/0`). The public view is an
approximately 30-day rolling window with no historical archive, so PERMITS /
SLA / DEEDS are deliberately left unregistered — ``get_dataset`` raises a
readable error for them and the scheduler skips them.

The 311 DatasetSpec payload below is the exact data the spine ``city_registry.py``
copies into REGISTRY under ``CityId.TULSA``; it is declared here so the spine
edit is a pure copy. ``extra["field_map"]`` wires the per-city spellings from
``field_maps_tulsa.FIELD_MAP``.
"""

from typing import Any, Dict

from src.producers.field_maps_tulsa import FIELD_MAP as TULSA_311_FIELD_MAP
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

TULSA_METRO_BBOX: dict[str, float] = {
    "min_lat": 35.80,
    "max_lat": 36.45,
    "min_lng": -96.45,
    "max_lng": -95.45,
}

TULSA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "TULSA_CORE": {
        "min_lat": 35.90,
        "max_lat": 36.30,
        "min_lng": -96.25,
        "max_lng": -95.60,
    },
}


def is_in_tulsa_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Tulsa extent."""
    if lat is None or lng is None:
        return False
    return (
        TULSA_METRO_BBOX["min_lat"] <= lat <= TULSA_METRO_BBOX["max_lat"]
        and TULSA_METRO_BBOX["min_lng"] <= lng <= TULSA_METRO_BBOX["max_lng"]
    )


TULSA_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Blue Dome": SubmarketMeta(
        name="Downtown & Blue Dome", borough="TULSA_CORE", lat=36.1550, lng=-95.9928,
        zoom=13.0, pitch=45.0, base_lims=0.81, capex=6200000.0, permit_vel=30.0,
        shift_ratio=1.37, sla=53.0,
        description="Civic and entertainment core with adaptive reuse, public-realm investment, and infill pressure.",
        city_id="tulsa",
    ),
    "Pearl District & Kendall Whittier": SubmarketMeta(
        name="Pearl District & Kendall Whittier", borough="TULSA_CORE", lat=36.1660, lng=-95.9700,
        zoom=12.8, pitch=43.0, base_lims=0.78, capex=5100000.0, permit_vel=27.0,
        shift_ratio=1.34, sla=51.0,
        description="Historic north-central neighborhoods with rehabilitation, small business, and neighborhood-service activity.",
        city_id="tulsa",
    ),
    "Brookside & Midtown": SubmarketMeta(
        name="Brookside & Midtown", borough="TULSA_CORE", lat=36.1120, lng=-95.9720,
        zoom=12.7, pitch=42.0, base_lims=0.79, capex=5600000.0, permit_vel=29.0,
        shift_ratio=1.35, sla=52.0,
        description="Established mixed-use corridor where renovation, retail turnover, and residential demand overlap.",
        city_id="tulsa",
    ),
    "East Tulsa": SubmarketMeta(
        name="East Tulsa", borough="TULSA_CORE", lat=36.1360, lng=-95.8700,
        zoom=12.4, pitch=40.0, base_lims=0.75, capex=4700000.0, permit_vel=25.0,
        shift_ratio=1.32, sla=50.0,
        description="Diverse east-side neighborhoods with service demand, commercial reinvestment, and corridor maintenance.",
        city_id="tulsa",
    ),
    "South Tulsa & Jenks": SubmarketMeta(
        name="South Tulsa & Jenks", borough="TULSA_CORE", lat=36.0400, lng=-95.9300,
        zoom=12.1, pitch=38.0, base_lims=0.76, capex=6400000.0, permit_vel=32.0,
        shift_ratio=1.36, sla=52.0,
        description="South metro growth corridor with housing expansion, retail development, and infrastructure extension.",
        city_id="tulsa",
    ),
}


TULSA_DIVISIONS: dict[str, BoroughMeta] = {
    "TULSA_CORE": BoroughMeta(
        name="Tulsa / Tulsa County", center_lat=36.1540, center_lng=-95.9928, zoom=10.8,
        bbox=TULSA_DIVISION_BBOXES["TULSA_CORE"], submarkets=list(TULSA_SUBMARKETS),
        city_id="tulsa",
    ),
}


# Exact COMPLAINTS_311 DatasetSpec payload for the spine REGISTRY entry
# (CityId.TULSA). Mirrors the Boise pattern: `extra["field_map"]` wires the
# per-city spellings from `field_maps_tulsa.FIELD_MAP`, and the rolling-window
# flags (`rolling_window_days` / `retention_days`) declare that the public layer
# is an approximately 30-day live view with no archive. The spine copies this
# block verbatim; it is the single source of truth for the Tulsa 311 spec.
TULSA_311_SPEC: Dict[str, Any] = {
    "endpoint": "settings.arcgis_tulsa_311_url",
    "platform": "arcgis",
    "watermark_col": "case_opened",
    "id_keys": ["case_id", "OBJECTID"],
    "topic": "settings.topic_311",
    "interval_seconds": 180.0,
    "producer_key": "311",
    "extra": {
        "expected_cadence_days": 7,
        "oid_field": "OBJECTID",
        "max_record_count": 2000,
        "rolling_window_days": 30,
        "retention_days": 30,
        "scope": "Tulsa Verint customer-care cases (approximately 30-day rolling window)",
        "field_map": TULSA_311_FIELD_MAP,
    },
}


# Verbose alias kept for symmetry with the other city modules' verbose spellings.
GREATER_TULSA_METRO_BBOX = TULSA_METRO_BBOX
TULSA_DIVISION_BBOXES = TULSA_DIVISION_BBOXES
TULSA_DIVISIONS = TULSA_DIVISIONS
TULSA_SUBMARKETS = TULSA_SUBMARKETS
