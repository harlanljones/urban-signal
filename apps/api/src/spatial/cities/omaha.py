"""Omaha / Douglas County spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Omaha, NE
(Nebraska side of the metro only).

Omaha is a ONE-FEED PARTIAL metro: COMPLAINTS_311 — the city's Mayor's
Hotline (Omaha 311) published as an anonymous Cityworks extract on the DCGIS
ArcGIS Server. PERMITS are Accela (``aca-prod.accela.com/OMAHA``, UI-only),
SLA liquor licenses are an unwatermarkable registry (no date column), and
there is no deeds stream — all Tier 3 and stay unregistered. The historical
Socrata domain (``data-cityofomaha-ne.gov``) does not resolve.

Live-probe caveats that define this leaf (2026-08-28 re-stamp, US-358):

* 311 is **same-day live**. Watermark ``DATETIMEINIT`` is
  ``esriFieldTypeDateOnly`` (day precision — same-day rows after a poll can
  lag one cycle; ``DATETIMEINITFULL`` carries the epoch-ms truth). Do **not**
  watermark on ``DATETIMECLOSED`` (nullable on open rows).
* Native WGS84 geometry via ``outSR=4326``; do **not** map ``SRX``/``SRY``
  (State Plane feet). ``PROBADDRESS`` is the geocode supplement and already
  carries ", Omaha, NE," so ADR-0004 appends no context.
* Drop PII at the field map: ``INITIATEDBY`` / ``CLOSEDBY`` (Memphis
  contact-field precedent); ``SUBMITTO`` is internal staff assignment.
* Council Bluffs / Pottawattamie County (Iowa) sits across the river and is
  NOT evidenced by this feed — the metro bbox stops at the Missouri River
  (-95.88) and excludes it. Partial registration = register only what is
  evidenced. Do not register sibling HubPage views (12-month / counts).
"""

from typing import Dict

from src.producers.field_maps_omaha import (
    COMPLAINTS_311_FIELD_MAP,
    GEOCODE_CONTEXT,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

OMAHA_CITY_ID: str = "omaha"
OMAHA_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Omaha / inner Douglas County, Nebraska side only. Permissive enough
# to hold Downtown/Old Market (-95.937), Eppley Airfield (-95.894), South
# Omaha (41.19), and the Millard edge (-96.12) shown in live 311 samples.
# max_lng -95.88 stops at the Missouri River: Council Bluffs, IA (-95.862)
# is excluded.
OMAHA_METRO_BBOX: Dict[str, float] = {
    "min_lat": 41.17,
    "max_lat": 41.37,
    "min_lng": -96.25,
    "max_lng": -95.88,
}

# 6 Omaha divisions. Hand-authored; borough resolution at ingest comes from
# coordinates via get_division_for_coordinate, so bboxes need only be sane
# and contain their own submarket centers.
OMAHA_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_OLD_MARKET": {
        "min_lat": 41.249,
        "max_lat": 41.268,
        "min_lng": -95.950,
        "max_lng": -95.925,
    },
    "MIDTOWN_DUNDEE": {
        "min_lat": 41.250,
        "max_lat": 41.274,
        "min_lng": -95.992,
        "max_lng": -95.958,
    },
    "AKSARBEN_VILLAGE": {
        "min_lat": 41.242,
        "max_lat": 41.256,
        "min_lng": -95.992,
        "max_lng": -95.972,
    },
    "NORTH_OMAHA": {
        "min_lat": 41.262,
        "max_lat": 41.330,
        "min_lng": -96.010,
        "max_lng": -95.938,
    },
    "SOUTH_OMAHA": {
        "min_lat": 41.200,
        "max_lat": 41.248,
        "min_lng": -95.950,
        "max_lng": -95.918,
    },
    "WEST_MILLARD": {
        "min_lat": 41.205,
        "max_lat": 41.290,
        "min_lng": -96.240,
        "max_lng": -96.080,
    },
}


def is_in_omaha_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Omaha / Douglas County bounds."""
    if lat is None or lng is None:
        return False
    return (
        OMAHA_METRO_BBOX["min_lat"] <= lat <= OMAHA_METRO_BBOX["max_lat"]
        and OMAHA_METRO_BBOX["min_lng"] <= lng <= OMAHA_METRO_BBOX["max_lng"]
    )


is_in_greater_omaha_metro = is_in_omaha_metro


OMAHA_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_OLD_MARKET (1)
    # =======================================================================
    "Downtown & Old Market": SubmarketMeta(
        name="Downtown & Old Market",
        borough="DOWNTOWN_OLD_MARKET",
        lat=41.2580,
        lng=-95.9370,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.88,
        capex=7200000.0,
        permit_vel=38.0,
        shift_ratio=1.48,
        sla=60.0,
        description="Gene Leahy Mall riverfront core with the Old Market entertainment grid, office conversions, and the densest Mayor's Hotline volume in the metro.",
        city_id="omaha",
    ),
    # =======================================================================
    # MIDTOWN_DUNDEE (2)
    # =======================================================================
    "Midtown Crossing": SubmarketMeta(
        name="Midtown Crossing",
        borough="MIDTOWN_DUNDEE",
        lat=41.2565,
        lng=-95.9680,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=6400000.0,
        permit_vel=34.0,
        shift_ratio=1.45,
        sla=58.0,
        description="Turner Park mixed-use district between downtown and Dundee with multifamily infill and steady restaurant-corridor 311 demand.",
        city_id="omaha",
    ),
    "Dundee": SubmarketMeta(
        name="Dundee",
        borough="MIDTOWN_DUNDEE",
        lat=41.2680,
        lng=-95.9800,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.84,
        capex=5800000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=56.0,
        description="Historic bungalow neighborhood around Underwood Avenue with renovation-led permitting and tree-canopy service requests.",
        city_id="omaha",
    ),
    # =======================================================================
    # AKSARBEN_VILLAGE (1)
    # =======================================================================
    "Aksarben Village": SubmarketMeta(
        name="Aksarben Village",
        borough="AKSARBEN_VILLAGE",
        lat=41.2490,
        lng=-95.9810,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.87,
        capex=8100000.0,
        permit_vel=36.0,
        shift_ratio=1.50,
        sla=60.0,
        description="Former racetrack redevelopment anchored by the Chromatin riverfront-adjacent office campus, University of Nebraska Omaha expansion, and apartment growth.",
        city_id="omaha",
    ),
    # =======================================================================
    # NORTH_OMAHA (2)
    # =======================================================================
    "North Omaha": SubmarketMeta(
        name="North Omaha",
        borough="NORTH_OMAHA",
        lat=41.2950,
        lng=-95.9600,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.68,
        capex=3100000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=44.0,
        description="Historic northside corridor with concentrated disinvestment signals, code-enforcement-heavy 311 demand, and targeted reinvestment along Ames Avenue.",
        city_id="omaha",
    ),
    "Benson": SubmarketMeta(
        name="Benson",
        borough="NORTH_OMAHA",
        lat=41.2720,
        lng=-95.9960,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.80,
        capex=4600000.0,
        permit_vel=28.0,
        shift_ratio=1.38,
        sla=52.0,
        description="Music-venue and brewery commercial node on Maple Street with older housing stock and active neighborhood-association permit engagement.",
        city_id="omaha",
    ),
    # =======================================================================
    # SOUTH_OMAHA (1)
    # =======================================================================
    "South Omaha": SubmarketMeta(
        name="South Omaha",
        borough="SOUTH_OMAHA",
        lat=41.2200,
        lng=-95.9350,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.72,
        capex=3900000.0,
        permit_vel=24.0,
        shift_ratio=1.30,
        sla=48.0,
        description="Stockyards-heritage Latino commercial district around 24th Street with owner-occupied infill and high trash/dumping 311 volume.",
        city_id="omaha",
    ),
    # =======================================================================
    # WEST_MILLARD (2)
    # =======================================================================
    "West Omaha": SubmarketMeta(
        name="West Omaha",
        borough="WEST_MILLARD",
        lat=41.2710,
        lng=-96.1700,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.90,
        capex=9400000.0,
        permit_vel=42.0,
        shift_ratio=1.55,
        sla=64.0,
        description="Employment and retail belt along Dodge Street toward 180th with the metro's newest single-family stock and highest permit velocity.",
        city_id="omaha",
    ),
    "Millard": SubmarketMeta(
        name="Millard",
        borough="WEST_MILLARD",
        lat=41.2290,
        lng=-96.1230,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.86,
        capex=7000000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=58.0,
        description="Annexed southwest suburban grid with school-driven residential growth, teardown-rebuild lots, and storm-drain 311 clusters.",
        city_id="omaha",
    ),
}


OMAHA_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_OLD_MARKET": BoroughMeta(
        name="DOWNTOWN_OLD_MARKET",
        center_lat=41.2580,
        center_lng=-95.9370,
        zoom=14.5,
        bbox=OMAHA_DIVISION_BBOXES["DOWNTOWN_OLD_MARKET"],
        submarkets=[k for k, v in OMAHA_SUBMARKETS.items() if v.borough == "DOWNTOWN_OLD_MARKET"],
        city_id="omaha",
    ),
    "MIDTOWN_DUNDEE": BoroughMeta(
        name="MIDTOWN_DUNDEE",
        center_lat=41.2620,
        center_lng=-95.9740,
        zoom=14.0,
        bbox=OMAHA_DIVISION_BBOXES["MIDTOWN_DUNDEE"],
        submarkets=[k for k, v in OMAHA_SUBMARKETS.items() if v.borough == "MIDTOWN_DUNDEE"],
        city_id="omaha",
    ),
    "AKSARBEN_VILLAGE": BoroughMeta(
        name="AKSARBEN_VILLAGE",
        center_lat=41.2490,
        center_lng=-95.9810,
        zoom=14.0,
        bbox=OMAHA_DIVISION_BBOXES["AKSARBEN_VILLAGE"],
        submarkets=[k for k, v in OMAHA_SUBMARKETS.items() if v.borough == "AKSARBEN_VILLAGE"],
        city_id="omaha",
    ),
    "NORTH_OMAHA": BoroughMeta(
        name="NORTH_OMAHA",
        center_lat=41.2840,
        center_lng=-95.9750,
        zoom=12.5,
        bbox=OMAHA_DIVISION_BBOXES["NORTH_OMAHA"],
        submarkets=[k for k, v in OMAHA_SUBMARKETS.items() if v.borough == "NORTH_OMAHA"],
        city_id="omaha",
    ),
    "SOUTH_OMAHA": BoroughMeta(
        name="SOUTH_OMAHA",
        center_lat=41.2200,
        center_lng=-95.9350,
        zoom=13.0,
        bbox=OMAHA_DIVISION_BBOXES["SOUTH_OMAHA"],
        submarkets=[k for k, v in OMAHA_SUBMARKETS.items() if v.borough == "SOUTH_OMAHA"],
        city_id="omaha",
    ),
    "WEST_MILLARD": BoroughMeta(
        name="WEST_MILLARD",
        center_lat=41.2500,
        center_lng=-96.1450,
        zoom=12.0,
        bbox=OMAHA_DIVISION_BBOXES["WEST_MILLARD"],
        submarkets=[k for k, v in OMAHA_SUBMARKETS.items() if v.borough == "WEST_MILLARD"],
        city_id="omaha",
    ),
}

GREATER_OMAHA_METRO_BBOX = OMAHA_METRO_BBOX
OMA_DIVISION_BBOXES = OMAHA_DIVISION_BBOXES
OMA_SUBMARKETS = OMAHA_SUBMARKETS
OMA_DIVISIONS = OMAHA_DIVISIONS

__all__ = [
    "GREATER_OMAHA_METRO_BBOX",
    "OMAHA_311_ENDPOINT",
    "OMAHA_CITY_ID",
    "OMAHA_DIVISIONS",
    "OMAHA_DIVISION_BBOXES",
    "OMAHA_FEED_SPECS",
    "OMAHA_GEOCODE_CONTEXT",
    "OMAHA_METRO_BBOX",
    "OMAHA_SUBMARKETS",
    "REGISTRATION",
    "get_omaha_dataset",
    "is_in_omaha_metro",
]

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28 (re-stamp). Do not register permits (Accela UI), liquor
# licenses (no date column), deeds, or sibling HubPage views.
# ---------------------------------------------------------------------------
OMAHA_311_ENDPOINT = (
    "https://dcgis.org/server/rest/services/Cityworks/"
    "Mayors_Hotline_Dashboard_Interactive/MapServer/0"
)

OMAHA_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "311": {
        "endpoint": OMAHA_311_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "DATETIMEINIT",
        "id_keys": ["OBJECTID", "REQUESTID"],
        "topic_key": "topic_311",
        "interval_seconds": 180.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": OMAHA_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "DATETIMEINIT DESC",
            "scope": (
                "Mayor's Hotline (Omaha 311) Cityworks extract, citywide "
                "MapServer layer 0 (outSR=4326 native points; do not map "
                "SRX/SRY State Plane; PROBADDRESS geocode supplement; "
                "DATETIMEINIT is DateOnly; no PII)"
            ),
            "field_map": COMPLAINTS_311_FIELD_MAP,
        },
    },
}


def get_omaha_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Omaha feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in OMAHA_FEED_SPECS:
        available = ", ".join(sorted(OMAHA_FEED_SPECS))
        raise KeyError(
            f"'{OMAHA_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = OMAHA_FEED_SPECS[feed_name]
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
    metro_bbox=OMAHA_METRO_BBOX,
    division_bboxes=OMAHA_DIVISION_BBOXES,
    submarkets=OMAHA_SUBMARKETS,
    divisions=OMAHA_DIVISIONS,
    contains=is_in_omaha_metro,
)
