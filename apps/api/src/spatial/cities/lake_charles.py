"""Lake Charles, LA — Urban Signal metro registry and spatial layer.

Jurisdiction: City of Lake Charles, LA (Calcasieu Parish context).
Region: South Central. Initial fit: Low (partial registration expected).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Lake Charles Metro bounding box — sized to cover the city limits, Westlake,
# and the Prien Lake corridor without extending into distant parish edges.
LAKE_CHARLES_METRO_BBOX: Dict[str, float] = {
    "min_lat": 30.05,
    "max_lat": 30.35,
    "min_lng": -93.35,
    "max_lng": -93.09,
}

# Three coarse divisions capturing core, Prien Lake retail, and Westlake/industrial.
LAKE_CHARLES_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "LAKE_CHARLES_CORE": {
        "min_lat": 30.19,
        "max_lat": 30.26,
        "min_lng": -93.25,
        "max_lng": -93.17,
    },
    "PRIEN_LAKE_SOUTH": {
        "min_lat": 30.17,
        "max_lat": 30.23,
        "min_lng": -93.26,
        "max_lng": -93.18,
    },
    "WESTLAKE_INDUSTRIAL": {
        "min_lat": 30.23,
        "max_lat": 30.30,
        "min_lng": -93.29,
        "max_lng": -93.19,
    },
}


def is_in_lake_charles_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate lies within the Lake Charles metro bbox."""
    if lat is None or lng is None:
        return False
    return (
        LAKE_CHARLES_METRO_BBOX["min_lat"] <= lat <= LAKE_CHARLES_METRO_BBOX["max_lat"]
        and LAKE_CHARLES_METRO_BBOX["min_lng"] <= lng <= LAKE_CHARLES_METRO_BBOX["max_lng"]
    )


LAKE_CHARLES_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # Core downtown and lakefront
    "Downtown Lake Charles & Lakefront": SubmarketMeta(
        name="Downtown Lake Charles & Lakefront",
        borough="LAKE_CHARLES_CORE",
        lat=30.2266,
        lng=-93.2174,
        zoom=13.8,
        pitch=44.0,
        base_lims=0.58,
        capex=2500000.0,
        permit_vel=22.0,
        shift_ratio=1.12,
        sla=28.0,
        description="Historic downtown and lakeshore activation with civic anchors and hospitality.",
        city_id="lake_charles",
    ),
    # South/Prien Lake retail spine
    "Prien Lake Retail Corridor": SubmarketMeta(
        name="Prien Lake Retail Corridor",
        borough="PRIEN_LAKE_SOUTH",
        lat=30.2005,
        lng=-93.2540,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.54,
        capex=2000000.0,
        permit_vel=24.0,
        shift_ratio=1.14,
        sla=24.0,
        description="Prien Lake Mall and Gauthier Road commercial corridor with steady small-format investment.",
        city_id="lake_charles",
    ),
    # Westlake / industrial river corridor
    "Westlake & Petrochemical District": SubmarketMeta(
        name="Westlake & Petrochemical District",
        borough="WESTLAKE_INDUSTRIAL",
        lat=30.2570,
        lng=-93.2540,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.50,
        capex=1800000.0,
        permit_vel=18.0,
        shift_ratio=1.08,
        sla=22.0,
        description="Industrial waterfront and Westlake city area with employment-driven demand signals.",
        city_id="lake_charles",
    ),
}

LAKE_CHARLES_DIVISIONS: Dict[str, BoroughMeta] = {
    "LAKE_CHARLES_CORE": BoroughMeta(
        name="LAKE_CHARLES_CORE",
        center_lat=30.226,
        center_lng=-93.215,
        zoom=12.0,
        bbox=LAKE_CHARLES_DIVISION_BBOXES["LAKE_CHARLES_CORE"],
        submarkets=[k for k, v in LAKE_CHARLES_SUBMARKETS.items() if v.borough == "LAKE_CHARLES_CORE"],
        city_id="lake_charles",
    ),
    "PRIEN_LAKE_SOUTH": BoroughMeta(
        name="PRIEN_LAKE_SOUTH",
        center_lat=30.202,
        center_lng=-93.242,
        zoom=12.0,
        bbox=LAKE_CHARLES_DIVISION_BBOXES["PRIEN_LAKE_SOUTH"],
        submarkets=[k for k, v in LAKE_CHARLES_SUBMARKETS.items() if v.borough == "PRIEN_LAKE_SOUTH"],
        city_id="lake_charles",
    ),
    "WESTLAKE_INDUSTRIAL": BoroughMeta(
        name="WESTLAKE_INDUSTRIAL",
        center_lat=30.260,
        center_lng=-93.245,
        zoom=11.8,
        bbox=LAKE_CHARLES_DIVISION_BBOXES["WESTLAKE_INDUSTRIAL"],
        submarkets=[k for k, v in LAKE_CHARLES_SUBMARKETS.items() if v.borough == "WESTLAKE_INDUSTRIAL"],
        city_id="lake_charles",
    ),
}

# Verbose aliases mirroring other city modules' constant re-exports
LAKE_CHARLES_METRO = LAKE_CHARLES_METRO_BBOX
LAKE_CHARLES_DIVISIONS_CATALOG = LAKE_CHARLES_DIVISIONS
LAKE_CHARLES_SUBMARKETS_CATALOG = LAKE_CHARLES_SUBMARKETS

from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=LAKE_CHARLES_METRO_BBOX,
    division_bboxes=LAKE_CHARLES_DIVISION_BBOXES,
    submarkets=LAKE_CHARLES_SUBMARKETS,
    divisions=LAKE_CHARLES_DIVISIONS,
    contains=is_in_lake_charles_metro,
)

