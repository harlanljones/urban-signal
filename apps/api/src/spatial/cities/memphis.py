"""Memphis / Shelby County spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Memphis, TN
and inner Shelby County (Germantown / Cordova / Whitehaven / Frayser).

Memphis is a TWO-FEED PARTIAL metro like Austin/LA: PERMITS
(``DPD_Building_Permits`` on MEMEGIS AGOL) and COMPLAINTS_311
(``311_Request_Map_PROD`` layer 0 on ``311.memphistn.gov``). SLA and DEEDS
are Tier 3 (Accela / Register-of-Deeds UIs only) and stay unregistered.

Live-probe caveats that define this leaf (2026-08-27, US-201):

* PERMITS is a **monthly-batch** ArcGIS extract. Newest ``Issued_Date`` on
  the 27 Aug probe was 2026-07-31; 0 August 2026 rows is a month-end dump,
  not a dead archive (PG County 311 cadence precedent). Native WGS84
  ``Latitude``/``Longitude`` + point geometry; ``Address`` is complete.
  ``needs_geocode=True`` supplements the ~5% coordinate gap. OID is
  ``ObjectId`` (not ``OBJECTID``). Do not scrape Accela Develop 901.
* 311 is **same-day live**. Watermark ``REPORTED_DATE`` — do **not** use
  ``Closed_Date`` (future scheduled closes). Prefer ``outSR=4326`` geometry.
  Do not blindly map ``X``/``Y`` (mix of WGS84 and EPSG:2274). Drop PII at
  the field map. Do not register sibling views (Reported Today / Last 7 Days).
"""

from typing import Dict

from src.producers.field_maps_memphis import (
    COMPLAINTS_311_FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MEMPHIS_CITY_ID: str = "memphis"
MEMPHIS_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# Greater Memphis / inner Shelby County. Permissive enough to hold downtown
# (35.1495, -90.0490), Whitehaven, Frayser/Raleigh, Hickory Hill, and the
# east-side Germantown/Cordova edge that shows up in live permit/311 samples.
MEMPHIS_METRO_BBOX: Dict[str, float] = {
    "min_lat": 34.99,
    "max_lat": 35.28,
    "min_lng": -90.13,
    "max_lng": -89.68,
}

# 6 Memphis / Shelby divisions. Hand-authored; borough resolution at ingest
# comes from coordinates via get_division_for_coordinate, so bboxes need only
# be sane and contain their own submarket centers.
MEMPHIS_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_RIVERFRONT": {
        "min_lat": 35.125,
        "max_lat": 35.175,
        "min_lng": -90.075,
        "max_lng": -90.025,
    },
    "MIDTOWN_MEDICAL": {
        "min_lat": 35.115,
        "max_lat": 35.165,
        "min_lng": -90.030,
        "max_lng": -89.970,
    },
    "EAST_MEMPHIS_POPLAR": {
        "min_lat": 35.100,
        "max_lat": 35.160,
        "min_lng": -89.970,
        "max_lng": -89.850,
    },
    "SOUTH_WHITEHAVEN": {
        "min_lat": 34.995,
        "max_lat": 35.100,
        "min_lng": -90.080,
        "max_lng": -89.900,
    },
    "NORTH_FRAYSER_RALEIGH": {
        "min_lat": 35.175,
        "max_lat": 35.270,
        "min_lng": -90.080,
        "max_lng": -89.850,
    },
    "UNIVERSITY_HICKORY_HILL": {
        "min_lat": 35.040,
        "max_lat": 35.145,
        "min_lng": -89.950,
        "max_lng": -89.700,
    },
}


def is_in_memphis_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Greater Memphis / Shelby bounds."""
    if lat is None or lng is None:
        return False
    return (
        MEMPHIS_METRO_BBOX["min_lat"] <= lat <= MEMPHIS_METRO_BBOX["max_lat"]
        and MEMPHIS_METRO_BBOX["min_lng"] <= lng <= MEMPHIS_METRO_BBOX["max_lng"]
    )


is_in_greater_memphis_metro = is_in_memphis_metro


MEMPHIS_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_RIVERFRONT (3)
    # =======================================================================
    "Downtown Memphis": SubmarketMeta(
        name="Downtown Memphis",
        borough="DOWNTOWN_RIVERFRONT",
        lat=35.1495,
        lng=-90.0490,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.88,
        capex=9800000.0,
        permit_vel=44.0,
        shift_ratio=1.52,
        sla=64.0,
        description="Mississippi riverfront civic core around Court Square and Beale with office-to-residential conversions and the densest 311 volume in the metro.",
        city_id="memphis",
    ),
    "Harbor Town & Mud Island": SubmarketMeta(
        name="Harbor Town & Mud Island",
        borough="DOWNTOWN_RIVERFRONT",
        lat=35.165,
        lng=-90.055,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=8200000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=58.0,
        description="Planned river-island neighborhood north of downtown with renovation-led permitting and trail-adjacent residential stock.",
        city_id="memphis",
    ),
    "South Main": SubmarketMeta(
        name="South Main",
        borough="DOWNTOWN_RIVERFRONT",
        lat=35.135,
        lng=-90.058,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.84,
        capex=7400000.0,
        permit_vel=36.0,
        shift_ratio=1.48,
        sla=60.0,
        description="Arts-district warehouse conversions south of Beale with loft infill and entertainment-adjacent short-stay pressure.",
        city_id="memphis",
    ),
    # =======================================================================
    # MIDTOWN_MEDICAL (3)
    # =======================================================================
    "Midtown & Cooper-Young": SubmarketMeta(
        name="Midtown & Cooper-Young",
        borough="MIDTOWN_MEDICAL",
        lat=35.135,
        lng=-90.005,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=7600000.0,
        permit_vel=38.0,
        shift_ratio=1.50,
        sla=61.0,
        description="Streetcar-era bungalow grid and Cooper-Young commercial node with renovation-heavy residential permitting.",
        city_id="memphis",
    ),
    "Medical District": SubmarketMeta(
        name="Medical District",
        borough="MIDTOWN_MEDICAL",
        lat=35.140,
        lng=-90.018,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.82,
        capex=8800000.0,
        permit_vel=34.0,
        shift_ratio=1.44,
        sla=59.0,
        description="Hospital-anchored employment core between downtown and Midtown with institutional expansion and workforce housing.",
        city_id="memphis",
    ),
    "Overton Park & Evergreen": SubmarketMeta(
        name="Overton Park & Evergreen",
        borough="MIDTOWN_MEDICAL",
        lat=35.148,
        lng=-89.990,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=6900000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=56.0,
        description="Park-adjacent historic district with conservation overlays and steady single-family renovation.",
        city_id="memphis",
    ),
    # =======================================================================
    # EAST_MEMPHIS_POPLAR (2)
    # =======================================================================
    "East Memphis": SubmarketMeta(
        name="East Memphis",
        borough="EAST_MEMPHIS_POPLAR",
        lat=35.125,
        lng=-89.910,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.87,
        capex=9200000.0,
        permit_vel=40.0,
        shift_ratio=1.54,
        sla=63.0,
        description="Poplar-corridor professional and residential belt with the metro's highest-value single-family stock and office parks.",
        city_id="memphis",
    ),
    "Poplar Corridor": SubmarketMeta(
        name="Poplar Corridor",
        borough="EAST_MEMPHIS_POPLAR",
        lat=35.140,
        lng=-89.890,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.84,
        capex=8100000.0,
        permit_vel=36.0,
        shift_ratio=1.48,
        sla=60.0,
        description="East-Poplar commercial spine toward Germantown with medical-office and multifamily infill.",
        city_id="memphis",
    ),
    # =======================================================================
    # SOUTH_WHITEHAVEN (2)
    # =======================================================================
    "Whitehaven": SubmarketMeta(
        name="Whitehaven",
        borough="SOUTH_WHITEHAVEN",
        lat=35.033,
        lng=-90.025,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.72,
        capex=4100000.0,
        permit_vel=28.0,
        shift_ratio=1.32,
        sla=48.0,
        description="South-Memphis Graceland corridor with renovation and alteration permits on post-war tract housing.",
        city_id="memphis",
    ),
    "South Memphis": SubmarketMeta(
        name="South Memphis",
        borough="SOUTH_WHITEHAVEN",
        lat=35.075,
        lng=-90.045,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.68,
        capex=3600000.0,
        permit_vel=24.0,
        shift_ratio=1.28,
        sla=44.0,
        description="Industrial-adjacent south grid with sparse new construction and high 311 volume relative to permit activity.",
        city_id="memphis",
    ),
    # =======================================================================
    # NORTH_FRAYSER_RALEIGH (2)
    # =======================================================================
    "Frayser": SubmarketMeta(
        name="Frayser",
        borough="NORTH_FRAYSER_RALEIGH",
        lat=35.220,
        lng=-90.000,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.66,
        capex=3200000.0,
        permit_vel=22.0,
        shift_ratio=1.24,
        sla=42.0,
        description="North-Memphis residential plateau with alteration-led permitting and code-enforcement-heavy 311 demand.",
        city_id="memphis",
    ),
    "Raleigh": SubmarketMeta(
        name="Raleigh",
        borough="NORTH_FRAYSER_RALEIGH",
        lat=35.230,
        lng=-89.910,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.70,
        capex=3800000.0,
        permit_vel=26.0,
        shift_ratio=1.30,
        sla=46.0,
        description="Northeast Memphis / Raleigh Springs corridor with suburban-lot renovations and retail-node 311 volume.",
        city_id="memphis",
    ),
    # =======================================================================
    # UNIVERSITY_HICKORY_HILL (2)
    # =======================================================================
    "University District": SubmarketMeta(
        name="University District",
        borough="UNIVERSITY_HICKORY_HILL",
        lat=35.118,
        lng=-89.937,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.38,
        sla=52.0,
        description="University of Memphis-adjacent rental and small-lot stock with student-driven turnover and renovation permits.",
        city_id="memphis",
    ),
    "Hickory Hill & Parkway Village": SubmarketMeta(
        name="Hickory Hill & Parkway Village",
        borough="UNIVERSITY_HICKORY_HILL",
        lat=35.060,
        lng=-89.850,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.74,
        capex=4600000.0,
        permit_vel=29.0,
        shift_ratio=1.36,
        sla=50.0,
        description="Southeast Memphis suburban grid toward the Germantown line with townhome infill and solid-waste 311 load.",
        city_id="memphis",
    ),
}


MEMPHIS_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_RIVERFRONT": BoroughMeta(
        name="DOWNTOWN_RIVERFRONT",
        center_lat=35.1495,
        center_lng=-90.0490,
        zoom=13.5,
        bbox=MEMPHIS_DIVISION_BBOXES["DOWNTOWN_RIVERFRONT"],
        submarkets=[k for k, v in MEMPHIS_SUBMARKETS.items() if v.borough == "DOWNTOWN_RIVERFRONT"],
        city_id="memphis",
    ),
    "MIDTOWN_MEDICAL": BoroughMeta(
        name="MIDTOWN_MEDICAL",
        center_lat=35.140,
        center_lng=-90.000,
        zoom=13.0,
        bbox=MEMPHIS_DIVISION_BBOXES["MIDTOWN_MEDICAL"],
        submarkets=[k for k, v in MEMPHIS_SUBMARKETS.items() if v.borough == "MIDTOWN_MEDICAL"],
        city_id="memphis",
    ),
    "EAST_MEMPHIS_POPLAR": BoroughMeta(
        name="EAST_MEMPHIS_POPLAR",
        center_lat=35.130,
        center_lng=-89.910,
        zoom=12.5,
        bbox=MEMPHIS_DIVISION_BBOXES["EAST_MEMPHIS_POPLAR"],
        submarkets=[k for k, v in MEMPHIS_SUBMARKETS.items() if v.borough == "EAST_MEMPHIS_POPLAR"],
        city_id="memphis",
    ),
    "SOUTH_WHITEHAVEN": BoroughMeta(
        name="SOUTH_WHITEHAVEN",
        center_lat=35.040,
        center_lng=-90.020,
        zoom=12.5,
        bbox=MEMPHIS_DIVISION_BBOXES["SOUTH_WHITEHAVEN"],
        submarkets=[k for k, v in MEMPHIS_SUBMARKETS.items() if v.borough == "SOUTH_WHITEHAVEN"],
        city_id="memphis",
    ),
    "NORTH_FRAYSER_RALEIGH": BoroughMeta(
        name="NORTH_FRAYSER_RALEIGH",
        center_lat=35.220,
        center_lng=-89.955,
        zoom=12.0,
        bbox=MEMPHIS_DIVISION_BBOXES["NORTH_FRAYSER_RALEIGH"],
        submarkets=[k for k, v in MEMPHIS_SUBMARKETS.items() if v.borough == "NORTH_FRAYSER_RALEIGH"],
        city_id="memphis",
    ),
    "UNIVERSITY_HICKORY_HILL": BoroughMeta(
        name="UNIVERSITY_HICKORY_HILL",
        center_lat=35.090,
        center_lng=-89.850,
        zoom=12.0,
        bbox=MEMPHIS_DIVISION_BBOXES["UNIVERSITY_HICKORY_HILL"],
        submarkets=[k for k, v in MEMPHIS_SUBMARKETS.items() if v.borough == "UNIVERSITY_HICKORY_HILL"],
        city_id="memphis",
    ),
}

GREATER_MEMPHIS_METRO_BBOX = MEMPHIS_METRO_BBOX
MEM_DIVISION_BBOXES = MEMPHIS_DIVISION_BBOXES
MEM_SUBMARKETS = MEMPHIS_SUBMARKETS
MEM_DIVISIONS = MEMPHIS_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27. Do not register SLA, deeds, Accela, or sibling 311 views.
# ---------------------------------------------------------------------------
MEMPHIS_PERMITS_ENDPOINT = (
    "https://services2.arcgis.com/saWmpKJIUAjyyNVc/arcgis/rest/services/"
    "DPD_Building_Permits/FeatureServer/0"
)
MEMPHIS_311_ENDPOINT = (
    "https://311.memphistn.gov/server/rest/services/311/"
    "311_Request_Map_PROD/FeatureServer/0"
)

MEMPHIS_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": MEMPHIS_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Issued_Date",
        "id_keys": ["Record_ID", "ObjectId"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 31,
            "needs_geocode": True,
            "geocode_context": MEMPHIS_GEOCODE_CONTEXT,
            "oid_field": "ObjectId",
            "max_record_count": 1000,
            "order_by": "Issued_Date DESC",
            "scope": (
                "DPD building permits issued since 2021 (monthly dump; native "
                "WGS84 Latitude/Longitude with Address geocode supplement)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "311": {
        "endpoint": MEMPHIS_311_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "REPORTED_DATE",
        "id_keys": ["INCIDENT_NUMBER", "OBJECTID"],
        "topic_key": "topic_311",
        "interval_seconds": 180.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": MEMPHIS_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 3000,
            "order_by": "REPORTED_DATE DESC",
            "scope": (
                "Citywide 311 Request Map layer 0 (outSR=4326 geometry; do not "
                "map mixed X/Y; Location_Address geocode supplement; no PII)"
            ),
            "field_map": COMPLAINTS_311_FIELD_MAP,
        },
    },
}


def get_memphis_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Memphis feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in MEMPHIS_FEED_SPECS:
        available = ", ".join(sorted(MEMPHIS_FEED_SPECS))
        raise KeyError(
            f"'{MEMPHIS_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = MEMPHIS_FEED_SPECS[feed_name]
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
    metro_bbox=MEMPHIS_METRO_BBOX,
    division_bboxes=MEMPHIS_DIVISION_BBOXES,
    submarkets=MEMPHIS_SUBMARKETS,
    divisions=MEMPHIS_DIVISIONS,
    contains=is_in_memphis_metro,
)
