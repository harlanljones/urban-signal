"""Aurora / Arapahoe-Adams County spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Aurora, CO
and its county-fringe context (Arapahoe / Adams / Douglas edges).

Aurora is a TWO-FEED TIER-1 metro like Denver: PERMITS (``Building Permits``,
OpenData/MapServer/44 on the city ArcGIS Server) and SLA (``Businesses (All
Non-Home)`` MapServer/77 with the liquor MapServer/34 companion). COMPLAINTS_311
and DEEDS are Tier 3 (no bulk "Access Aurora" 311 surface; Arapahoe/Adams/
Douglas recording is county-held) and stay unregistered.

Live-probe caveats that define this leaf (2026-08-27, US-326):

* PERMITS native SR is **WKID 2232 (NAD83 Colorado South ftUS)**. Every
  query goes out with ``outSR=4326`` per ``ArcGISClient``, so point geometry
  arrives as WGS84 ``latitude``/``longitude``; the attribute ``PropX``/
  ``PropY`` fallback pair stays in state-plane feet and must never be mapped
  as degrees. Geometry is the primary path (PropX nulls 8,231/162,767 ≈
  5.1%; Address null 8,082), ``needs_geocode=False``. Rolling views L156
  (6mo) / L157 (1mo) age rows out — do not register them.
* SLA (L34 liquor / L77 non-home businesses) carries **native ``X``/``Y`` in
  WKID 2232 state-plane feet** (live-verified: X≈3.18e6 ft, Y≈1.69e6 ft),
  NOT WGS84 degrees. The coordinate path is the ``outSR=4326`` geometry
  lift; a Boston-style ``_transform_state_plane`` branch (EPSG:2232 →
  EPSG:4326) is the fallback for null-geometry rows and reproduces the
  geometry to ~1m. License rows are current-license snapshots — the
  freshness watermark is max ``Issue_Date``, not window counts.
* ``valuation`` is a string column ("8000.00"); the shared cost chain
  strips and floats it. ``FolderCondition`` is free-text — mapped as the
  status source per the probe contract.
"""

from typing import Dict

from src.producers.field_maps_aurora import (
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

AURORA_CITY_ID: str = "aurora"
AURORA_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# NAD83 Colorado South state plane, US survey feet — native SR of the
# permits PropX/PropY pair and the SLA X/Y attributes (WKID 2232).
AURORA_STATE_PLANE_CRS: str = "EPSG:2232"
AURORA_STATE_PLANE_UNITS: str = "ftUS"

# City of Aurora plus Arapahoe/Adams county-fringe context. Permissive
# enough to hold Original Aurora (-104.868), the Anschutz corridor
# (-104.834), Aurora Highlands / Painted Prairie (-104.795..-104.746),
# Southlands (-104.730), and Piney Creek (-104.793) while rejecting
# downtown Denver (-104.99).
AURORA_METRO_BBOX: Dict[str, float] = {
    "min_lat": 39.54,
    "max_lat": 39.83,
    "min_lng": -104.98,
    "max_lng": -104.60,
}

# 6 Aurora / county-fringe divisions. Hand-authored; borough resolution at
# ingest comes from coordinates via get_division_for_coordinate, so bboxes
# need only be sane, mutually non-overlapping, and contain their own
# submarket centers.
AURORA_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "NORTHWEST_URBAN_CORE": {
        "min_lat": 39.72,
        "max_lat": 39.80,
        "min_lng": -104.98,
        "max_lng": -104.85,
    },
    "FITZSIMONS_ANSHUTZ": {
        "min_lat": 39.72,
        "max_lat": 39.80,
        "min_lng": -104.85,
        "max_lng": -104.80,
    },
    "AURORA_HIGHLANDS_EAST": {
        "min_lat": 39.70,
        "max_lat": 39.83,
        "min_lng": -104.80,
        "max_lng": -104.60,
    },
    "CENTRAL_HAVANA": {
        "min_lat": 39.66,
        "max_lat": 39.72,
        "min_lng": -104.90,
        "max_lng": -104.82,
    },
    "SOUTHEAST_SOUTHLANDS": {
        "min_lat": 39.54,
        "max_lat": 39.67,
        "min_lng": -104.78,
        "max_lng": -104.60,
    },
    "SOUTHWEST_SMOKY_HILL": {
        "min_lat": 39.54,
        "max_lat": 39.66,
        "min_lng": -104.92,
        "max_lng": -104.78,
    },
}


def is_in_aurora_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Aurora / county-fringe bounds."""
    if lat is None or lng is None:
        return False
    return (
        AURORA_METRO_BBOX["min_lat"] <= lat <= AURORA_METRO_BBOX["max_lat"]
        and AURORA_METRO_BBOX["min_lng"] <= lng <= AURORA_METRO_BBOX["max_lng"]
    )


is_in_greater_aurora_metro = is_in_aurora_metro


AURORA_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # NORTHWEST_URBAN_CORE (2)
    # =======================================================================
    "Original Aurora & Colfax": SubmarketMeta(
        name="Original Aurora & Colfax",
        borough="NORTHWEST_URBAN_CORE",
        lat=39.7405,
        lng=-104.8680,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=32.0,
        shift_ratio=1.44,
        sla=54.0,
        description=(
            "East Colfax cultural arts district and the city's oldest grid "
            "with facade grants, mixed-use conversions, and steady "
            "alteration permitting."
        ),
        city_id="aurora",
    ),
    "Northwest Aurora MLK": SubmarketMeta(
        name="Northwest Aurora MLK",
        borough="NORTHWEST_URBAN_CORE",
        lat=39.7720,
        lng=-104.8900,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.72,
        capex=4400000.0,
        permit_vel=26.0,
        shift_ratio=1.34,
        sla=47.0,
        description=(
            "MLK Boulevard corridor of post-war tract housing with "
            "renovation-led permitting and infill on former school sites."
        ),
        city_id="aurora",
    ),
    # =======================================================================
    # FITZSIMONS_ANSHUTZ (1)
    # =======================================================================
    "Anschutz Medical Campus": SubmarketMeta(
        name="Anschutz Medical Campus",
        borough="FITZSIMONS_ANSHUTZ",
        lat=39.7433,
        lng=-104.8342,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.90,
        capex=10800000.0,
        permit_vel=46.0,
        shift_ratio=1.58,
        sla=66.0,
        description=(
            "Fitzsimons life-sciences anchor with continuous institutional "
            "expansion, med-ed tenancy, and the metro's densest permit "
            "velocity per parcel."
        ),
        city_id="aurora",
    ),
    # =======================================================================
    # AURORA_HIGHLANDS_EAST (2)
    # =======================================================================
    "Aurora Highlands": SubmarketMeta(
        name="Aurora Highlands",
        borough="AURORA_HIGHLANDS_EAST",
        lat=39.7740,
        lng=-104.7460,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.86,
        capex=8600000.0,
        permit_vel=42.0,
        shift_ratio=1.52,
        sla=60.0,
        description=(
            "Master-planned northeast growth corridor with new-build "
            "tract permitting, school-package filings, and Gaylord-scale "
            "commercial pads."
        ),
        city_id="aurora",
    ),
    "Painted Prairie": SubmarketMeta(
        name="Painted Prairie",
        borough="AURORA_HIGHLANDS_EAST",
        lat=39.7866,
        lng=-104.7952,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.84,
        capex=7400000.0,
        permit_vel=38.0,
        shift_ratio=1.48,
        sla=57.0,
        description=(
            "Newer mixed-housing development near Tower Road with "
            "builder-driven permit volume and neighborhood-retail pads."
        ),
        city_id="aurora",
    ),
    # =======================================================================
    # CENTRAL_HAVANA (2)
    # =======================================================================
    "Havana Business District": SubmarketMeta(
        name="Havana Business District",
        borough="CENTRAL_HAVANA",
        lat=39.7100,
        lng=-104.8660,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.76,
        capex=5200000.0,
        permit_vel=30.0,
        shift_ratio=1.40,
        sla=52.0,
        description=(
            "Havana BID strip with immigrant-owned small business "
            "licensing, facade improvements, and transit-adjacent infill."
        ),
        city_id="aurora",
    ),
    "Mission Viejo & Aurora Hills": SubmarketMeta(
        name="Mission Viejo & Aurora Hills",
        borough="CENTRAL_HAVANA",
        lat=39.6800,
        lng=-104.8300,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.74,
        capex=4800000.0,
        permit_vel=28.0,
        shift_ratio=1.36,
        sla=49.0,
        description=(
            "Mid-century residential belt around Aurora Hills library with "
            "basement-finish and roof-permit cadence."
        ),
        city_id="aurora",
    ),
    # =======================================================================
    # SOUTHEAST_SOUTHLANDS (2)
    # =======================================================================
    "Southlands": SubmarketMeta(
        name="Southlands",
        borough="SOUTHEAST_SOUTHLANDS",
        lat=39.6000,
        lng=-104.7300,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.82,
        capex=7200000.0,
        permit_vel=36.0,
        shift_ratio=1.46,
        sla=56.0,
        description=(
            "Southeast lifestyle-retail anchor with townhome infill, "
            "E-470 pad sites, and the metro's newest-roof stock."
        ),
        city_id="aurora",
    ),
    "Seven Hills & Saddle Rock": SubmarketMeta(
        name="Seven Hills & Saddle Rock",
        borough="SOUTHEAST_SOUTHLANDS",
        lat=39.6450,
        lng=-104.7700,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.80,
        capex=6800000.0,
        permit_vel=34.0,
        shift_ratio=1.44,
        sla=54.0,
        description=(
            "Golf-course custom-build belt with high-valuation new "
            "construction and pool/deck auxiliary permits."
        ),
        city_id="aurora",
    ),
    # =======================================================================
    # SOUTHWEST_SMOKY_HILL (1)
    # =======================================================================
    "Piney Creek & Smoky Hill": SubmarketMeta(
        name="Piney Creek & Smoky Hill",
        borough="SOUTHWEST_SMOKY_HILL",
        lat=39.6140,
        lng=-104.7930,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.38,
        sla=50.0,
        description=(
            "Piney Creek village housing next to the Smoky Hill Road "
            "retail spine with steady renovation and business-license "
            "churn."
        ),
        city_id="aurora",
    ),
}


AURORA_DIVISIONS: Dict[str, BoroughMeta] = {
    "NORTHWEST_URBAN_CORE": BoroughMeta(
        name="NORTHWEST_URBAN_CORE",
        center_lat=39.750,
        center_lng=-104.875,
        zoom=13.5,
        bbox=AURORA_DIVISION_BBOXES["NORTHWEST_URBAN_CORE"],
        submarkets=[k for k, v in AURORA_SUBMARKETS.items() if v.borough == "NORTHWEST_URBAN_CORE"],
        city_id="aurora",
    ),
    "FITZSIMONS_ANSHUTZ": BoroughMeta(
        name="FITZSIMONS_ANSHUTZ",
        center_lat=39.740,
        center_lng=-104.835,
        zoom=13.5,
        bbox=AURORA_DIVISION_BBOXES["FITZSIMONS_ANSHUTZ"],
        submarkets=[k for k, v in AURORA_SUBMARKETS.items() if v.borough == "FITZSIMONS_ANSHUTZ"],
        city_id="aurora",
    ),
    "AURORA_HIGHLANDS_EAST": BoroughMeta(
        name="AURORA_HIGHLANDS_EAST",
        center_lat=39.765,
        center_lng=-104.740,
        zoom=12.5,
        bbox=AURORA_DIVISION_BBOXES["AURORA_HIGHLANDS_EAST"],
        submarkets=[k for k, v in AURORA_SUBMARKETS.items() if v.borough == "AURORA_HIGHLANDS_EAST"],
        city_id="aurora",
    ),
    "CENTRAL_HAVANA": BoroughMeta(
        name="CENTRAL_HAVANA",
        center_lat=39.700,
        center_lng=-104.855,
        zoom=13.0,
        bbox=AURORA_DIVISION_BBOXES["CENTRAL_HAVANA"],
        submarkets=[k for k, v in AURORA_SUBMARKETS.items() if v.borough == "CENTRAL_HAVANA"],
        city_id="aurora",
    ),
    "SOUTHEAST_SOUTHLANDS": BoroughMeta(
        name="SOUTHEAST_SOUTHLANDS",
        center_lat=39.615,
        center_lng=-104.745,
        zoom=12.5,
        bbox=AURORA_DIVISION_BBOXES["SOUTHEAST_SOUTHLANDS"],
        submarkets=[k for k, v in AURORA_SUBMARKETS.items() if v.borough == "SOUTHEAST_SOUTHLANDS"],
        city_id="aurora",
    ),
    "SOUTHWEST_SMOKY_HILL": BoroughMeta(
        name="SOUTHWEST_SMOKY_HILL",
        center_lat=39.610,
        center_lng=-104.850,
        zoom=12.5,
        bbox=AURORA_DIVISION_BBOXES["SOUTHWEST_SMOKY_HILL"],
        submarkets=[k for k, v in AURORA_SUBMARKETS.items() if v.borough == "SOUTHWEST_SMOKY_HILL"],
        city_id="aurora",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27 (re-stamped same day; watermarks advanced L34/L77 +1d).
# Do not register 311, deeds, or the L156/L157 rolling permit windows.
# ---------------------------------------------------------------------------
AURORA_PERMITS_ENDPOINT = (
    "https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/44"
)
AURORA_SLA_ENDPOINT = (
    "https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/77"
)
AURORA_SLA_LIQUOR_ENDPOINT = (
    "https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/34"
)
AURORA_SLA_ALL_BUSINESSES_ENDPOINT = (
    "https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/36"
)
AURORA_SLA_MARIJUANA_ENDPOINT = (
    "https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/4"
)

AURORA_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": AURORA_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "IssueDate",
        "id_keys": ["Permit_", "FolderRSN", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "IssueDate DESC",
            "state_plane_crs": AURORA_STATE_PLANE_CRS,
            "state_plane_units": AURORA_STATE_PLANE_UNITS,
            "state_plane_x_col": "PropX",
            "state_plane_y_col": "PropY",
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": AURORA_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Issue_Date",
        "id_keys": ["License_Number", "entity_key", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 300.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "ingestion_mode": "snapshot",
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "Issue_Date DESC",
            "state_plane_crs": AURORA_STATE_PLANE_CRS,
            "state_plane_units": AURORA_STATE_PLANE_UNITS,
            "state_plane_x_col": "X",
            "state_plane_y_col": "Y",
            "companion_endpoints": {
                "liquor": AURORA_SLA_LIQUOR_ENDPOINT,
                "all_businesses": AURORA_SLA_ALL_BUSINESSES_ENDPOINT,
                "marijuana": AURORA_SLA_MARIJUANA_ENDPOINT,
            },
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_aurora_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a (pending-spine) Aurora feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in AURORA_FEED_SPECS:
        available = ", ".join(sorted(AURORA_FEED_SPECS))
        raise KeyError(
            f"'{AURORA_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = AURORA_FEED_SPECS[feed_name]
    extra_kwargs = {
        k: v for k, v in payload.get("extra", {}).items() if k != "scope"
    }
    return DatasetSpec(
        endpoint=payload["endpoint"],
        platform=payload["platform"],
        watermark_col=payload["watermark_col"],
        id_keys=payload["id_keys"],
        topic=getattr(settings, payload["topic_key"]),
        interval_seconds=payload["interval_seconds"],
        producer_key=payload["producer_key"],
        **extra_kwargs,
    )


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=AURORA_METRO_BBOX,
    division_bboxes=AURORA_DIVISION_BBOXES,
    submarkets=AURORA_SUBMARKETS,
    divisions=AURORA_DIVISIONS,
    contains=is_in_aurora_metro,
)

__all__ = [
    "AURORA_CITY_ID",
    "AURORA_DIVISIONS",
    "AURORA_DIVISION_BBOXES",
    "AURORA_FEED_SPECS",
    "AURORA_GEOCODE_CONTEXT",
    "AURORA_METRO_BBOX",
    "AURORA_PERMITS_ENDPOINT",
    "AURORA_SLA_ALL_BUSINESSES_ENDPOINT",
    "AURORA_SLA_ENDPOINT",
    "AURORA_SLA_LIQUOR_ENDPOINT",
    "AURORA_SLA_MARIJUANA_ENDPOINT",
    "AURORA_STATE_PLANE_CRS",
    "AURORA_STATE_PLANE_UNITS",
    "AURORA_SUBMARKETS",
    "REGISTRATION",
    "get_aurora_dataset",
    "is_in_aurora_metro",
]
