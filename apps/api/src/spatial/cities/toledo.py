"""Toledo / Lucas County spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Toledo, OH
and inner Lucas County (Ottawa Hills / Maumee edge / Sylvania Township edge).

Toledo is a ONE-FEED PARTIAL metro: COMPLAINTS_311 (``Public/
CityWorks_ServiceRequest_2022`` layer 0 on ``gis.toledo.oh.gov``). PERMITS
(`permits.toledo.oh.gov` portal, 403 to anonymous probes, no Accela tenant),
SLA (static Rental Registry shapefile export only) and DEEDS (For_Sale_Data
is city-surplus parcels, no transfer stream) are Tier 3 and stay
unregistered.

Live-probe caveats that define this leaf (2026-08-28, US-359; re-probed
2026-08-27 23:04 UTC, newest ``INIT_DATE`` 2026-08-27T23:04:37+00:00,
REQUEST_ID 796130):

* 311 is **same-day live** but the layer name says "2022" — it is a
  **current-year rolling extract** (43,260 = count since 2026-01-01 at the
  re-probe, vs 43,252 in the Phase-0 doc). History truncates on Jan 1;
  treat the layer as today-forward and register with
  ``expected_cadence_days: 1``. Do not register the sibling
  ``CityworksSRDash`` dashboard item or the Hub's static exports.
* Watermark is ``INIT_DATE`` only — ``CLOSED_DATE`` is nullable on open
  rows (future-scheduled-close precedent, Memphis 311).
* Prefer ``outSR=4326`` geometry. Do **not** map ``X_COORD``/``Y_COORD``:
  they are projected but **mixed-CRS** — Web Mercator meters (-9.3M/+5.1M)
  on most rows, Ohio State Plane feet (1.67M/0.74M) on the 796130 re-probe
  row. Neither variant is degrees.
* Re-probe geometry reliability: 19/20 newest rows returned clean in-city
  WGS84 via ``outSR=4326``. The newest (796130) came back as a corrupted
  non-geographic point (15.04, 6.67) that the producer's abs() guard does
  not flag (<90/<180). Metro filtering drops it downstream; the
  ``LOCATION`` address is the ``needs_geocode`` supplement for address-only
  and geometry-less rows.
* Drop PII at the field map: ``INIT_BY`` (submitter identity). ``REQUEST_ID``
  is the layer OID and business key.
"""

from typing import Dict

from src.producers.field_maps_toledo import COMPLAINTS_311_FIELD_MAP, GEOCODE_CONTEXT
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

TOLEDO_CITY_ID: str = "toledo"
TOLEDO_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# Toledo / inner Lucas County. Permissive enough to hold downtown
# (41.6528, -83.5379), Point Place, the Old West End, the Monastery area,
# the Ottawa Hills village, and the Lucas County cores of Maumee, Sylvania
# Township, and Oregon that show up in live 311 samples. South edge keeps
# Maumee/Perrysburg; west edge keeps Sylvania; not the full county extent.
TOLEDO_METRO_BBOX: Dict[str, float] = {
    "min_lat": 41.52,
    "max_lat": 41.76,
    "min_lng": -83.78,
    "max_lng": -83.38,
}

# 7 Toledo / Lucas divisions. Hand-authored; division resolution at ingest
# comes from coordinates via get_division_for_coordinate, so bboxes need only
# be sane and contain their own submarket centers.
TOLEDO_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_RIVERFRONT": {
        "min_lat": 41.638,
        "max_lat": 41.668,
        "min_lng": -83.555,
        "max_lng": -83.520,
    },
    "OLD_WEST_END": {
        "min_lat": 41.652,
        "max_lat": 41.672,
        "min_lng": -83.585,
        "max_lng": -83.553,
    },
    "OTTAWA_HILLS_AREA": {
        "min_lat": 41.660,
        "max_lat": 41.690,
        "min_lng": -83.652,
        "max_lng": -83.615,
    },
    "WEST_TOLEDO": {
        "min_lat": 41.665,
        "max_lat": 41.712,
        "min_lng": -83.645,
        "max_lng": -83.560,
    },
    "NORTH_POINT_PLACE": {
        "min_lat": 41.682,
        "max_lat": 41.726,
        "min_lng": -83.535,
        "max_lng": -83.468,
    },
    "SOUTH_TOLEDO_MONASTERY": {
        "min_lat": 41.592,
        "max_lat": 41.668,
        "min_lng": -83.625,
        "max_lng": -83.558,
    },
    "EAST_SIDE_BIRMINGHAM": {
        "min_lat": 41.640,
        "max_lat": 41.678,
        "min_lng": -83.522,
        "max_lng": -83.455,
    },
}


def is_in_toledo_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Toledo / Lucas County bounds."""
    if lat is None or lng is None:
        return False
    return (
        TOLEDO_METRO_BBOX["min_lat"] <= lat <= TOLEDO_METRO_BBOX["max_lat"]
        and TOLEDO_METRO_BBOX["min_lng"] <= lng <= TOLEDO_METRO_BBOX["max_lng"]
    )


is_in_greater_toledo_metro = is_in_toledo_metro


TOLEDO_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_RIVERFRONT (3)
    # =======================================================================
    "Downtown Toledo": SubmarketMeta(
        name="Downtown Toledo",
        borough="DOWNTOWN_RIVERFRONT",
        lat=41.6528,
        lng=-83.5379,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.86,
        capex=8600000.0,
        permit_vel=38.0,
        shift_ratio=1.48,
        sla=62.0,
        description="Maumee River civic core around Government Center and Fifth Third Field with the densest same-day 311 volume in the metro.",
        city_id="toledo",
    ),
    "Warehouse District": SubmarketMeta(
        name="Warehouse District",
        borough="DOWNTOWN_RIVERFRONT",
        lat=41.6463,
        lng=-83.5438,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.83,
        capex=7200000.0,
        permit_vel=33.0,
        shift_ratio=1.44,
        sla=58.0,
        description="Nineteenth-century warehouse loft conversions south of downtown with restaurant infill and renovation-led service demand.",
        city_id="toledo",
    ),
    "Vistula & Riverfront": SubmarketMeta(
        name="Vistula & Riverfront",
        borough="DOWNTOWN_RIVERFRONT",
        lat=41.6617,
        lng=-83.5306,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.80,
        capex=6300000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=56.0,
        description="Historic Vistula district north of downtown with Italianate stock, riverfront trail investment, and steady code-enforcement load.",
        city_id="toledo",
    ),
    # =======================================================================
    # OLD_WEST_END (2)
    # =======================================================================
    "Old West End": SubmarketMeta(
        name="Old West End",
        borough="OLD_WEST_END",
        lat=41.6641,
        lng=-83.5655,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.78,
        capex=5900000.0,
        permit_vel=27.0,
        shift_ratio=1.38,
        sla=54.0,
        description="Victorian mansion district around the Toledo Museum of Art with the Midwest's largest collection of period housing and heavy restoration pressure.",
        city_id="toledo",
    ),
    "Westmoreland": SubmarketMeta(
        name="Westmoreland",
        borough="OLD_WEST_END",
        lat=41.6594,
        lng=-83.5776,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=25.0,
        shift_ratio=1.36,
        sla=52.0,
        description="Museum-adjacent historic district with ambleside-era housing, the Monastery of the Visitation edge, and renovation-heavy 311 demand.",
        city_id="toledo",
    ),
    # =======================================================================
    # OTTAWA_HILLS_AREA (2)
    # =======================================================================
    "Ottawa Hills": SubmarketMeta(
        name="Ottawa Hills",
        borough="OTTAWA_HILLS_AREA",
        lat=41.6689,
        lng=-83.6370,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.92,
        capex=10500000.0,
        permit_vel=36.0,
        shift_ratio=1.50,
        sla=66.0,
        description="Village enclave around the Ottawa River with the metro's highest-value single-family stock and low-volume, high-cost service requests.",
        city_id="toledo",
    ),
    "Westgate Village": SubmarketMeta(
        name="Westgate Village",
        borough="OTTAWA_HILLS_AREA",
        lat=41.6793,
        lng=-83.6301,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.84,
        capex=7600000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=58.0,
        description="Central Avenue retail node at the Toledo/Ottawa Hills line with mixed commercial-residential turnover and solid-waste 311 load.",
        city_id="toledo",
    ),
    # =======================================================================
    # WEST_TOLEDO (4)
    # =======================================================================
    "West Toledo": SubmarketMeta(
        name="West Toledo",
        borough="WEST_TOLEDO",
        lat=41.6885,
        lng=-83.5770,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=6800000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=58.0,
        description="Streetcar-era residential belt between Monroe and Sylvania with bungalow renovation and steady tree/waste service demand.",
        city_id="toledo",
    ),
    "Library Village": SubmarketMeta(
        name="Library Village",
        borough="WEST_TOLEDO",
        lat=41.6726,
        lng=-83.5909,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.79,
        capex=6100000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=56.0,
        description="Monroe Street corridor around the historic branch library with small-commercial storefronts and rental turnover.",
        city_id="toledo",
    ),
    "Franklin Park": SubmarketMeta(
        name="Franklin Park",
        borough="WEST_TOLEDO",
        lat=41.6999,
        lng=-83.6140,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.83,
        capex=7400000.0,
        permit_vel=31.0,
        shift_ratio=1.44,
        sla=59.0,
        description="Mall-anchored northwest retail and residential belt with high traffic-related 311 volume and apartment infill.",
        city_id="toledo",
    ),
    "DeVeaux": SubmarketMeta(
        name="DeVeaux",
        borough="WEST_TOLEDO",
        lat=41.6828,
        lng=-83.6279,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.75,
        capex=5300000.0,
        permit_vel=24.0,
        shift_ratio=1.34,
        sla=51.0,
        description="DeVeaux school-area post-war neighborhoods with owner-occupied stock and modest alteration activity.",
        city_id="toledo",
    ),
    # =======================================================================
    # NORTH_POINT_PLACE (2)
    # =======================================================================
    "Point Place": SubmarketMeta(
        name="Point Place",
        borough="NORTH_POINT_PLACE",
        lat=41.7150,
        lng=-83.4900,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.77,
        capex=5800000.0,
        permit_vel=26.0,
        shift_ratio=1.38,
        sla=54.0,
        description="Maumee Bay peninsula of marinas and canal housing with flood- and drainage-heavy service requests.",
        city_id="toledo",
    ),
    "North Towne": SubmarketMeta(
        name="North Towne",
        borough="NORTH_POINT_PLACE",
        lat=41.6960,
        lng=-83.5216,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.72,
        capex=4700000.0,
        permit_vel=23.0,
        shift_ratio=1.32,
        sla=49.0,
        description="North Summit Street corridor with mixed industrial-residential edges and code-enforcement 311 load.",
        city_id="toledo",
    ),
    # =======================================================================
    # SOUTH_TOLEDO_MONASTERY (2)
    # =======================================================================
    "South Toledo": SubmarketMeta(
        name="South Toledo",
        borough="SOUTH_TOLEDO_MONASTERY",
        lat=41.6092,
        lng=-83.5898,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.74,
        capex=5000000.0,
        permit_vel=25.0,
        shift_ratio=1.36,
        sla=52.0,
        description="Bowsher-area residential belt south of the Maumee with high same-day 311 volume relative to permit activity.",
        city_id="toledo",
    ),
    "Monastery & Parkside": SubmarketMeta(
        name="Monastery & Parkside",
        borough="SOUTH_TOLEDO_MONASTERY",
        lat=41.6581,
        lng=-83.5956,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.80,
        capex=6500000.0,
        permit_vel=27.0,
        shift_ratio=1.40,
        sla=56.0,
        description="Parkside Boulevard corridor around the Visitation monastery grounds with stable owner-occupied stock and park-edge 311 demand.",
        city_id="toledo",
    ),
    # =======================================================================
    # EAST_SIDE_BIRMINGHAM (2)
    # =======================================================================
    "East Toledo": SubmarketMeta(
        name="East Toledo",
        borough="EAST_SIDE_BIRMINGHAM",
        lat=41.6547,
        lng=-83.5057,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.70,
        capex=4300000.0,
        permit_vel=21.0,
        shift_ratio=1.30,
        sla=47.0,
        description="East-of-river residential plateau around East Broadway with infrastructure-heavy 311 demand and sparse new construction.",
        city_id="toledo",
    ),
    "Birmingham": SubmarketMeta(
        name="Birmingham",
        borough="EAST_SIDE_BIRMINGHAM",
        lat=41.6629,
        lng=-83.4760,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.72,
        capex=4600000.0,
        permit_vel=22.0,
        shift_ratio=1.32,
        sla=49.0,
        description="Historic Hungarian neighborhood around Birmingham Festival with intact ethnic housing stock and steady renovation.",
        city_id="toledo",
    ),
}


TOLEDO_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_RIVERFRONT": BoroughMeta(
        name="DOWNTOWN_RIVERFRONT",
        center_lat=41.6528,
        center_lng=-83.5379,
        zoom=13.5,
        bbox=TOLEDO_DIVISION_BBOXES["DOWNTOWN_RIVERFRONT"],
        submarkets=[k for k, v in TOLEDO_SUBMARKETS.items() if v.borough == "DOWNTOWN_RIVERFRONT"],
        city_id="toledo",
    ),
    "OLD_WEST_END": BoroughMeta(
        name="OLD_WEST_END",
        center_lat=41.6618,
        center_lng=-83.5716,
        zoom=13.5,
        bbox=TOLEDO_DIVISION_BBOXES["OLD_WEST_END"],
        submarkets=[k for k, v in TOLEDO_SUBMARKETS.items() if v.borough == "OLD_WEST_END"],
        city_id="toledo",
    ),
    "OTTAWA_HILLS_AREA": BoroughMeta(
        name="OTTAWA_HILLS_AREA",
        center_lat=41.6741,
        center_lng=-83.6336,
        zoom=13.0,
        bbox=TOLEDO_DIVISION_BBOXES["OTTAWA_HILLS_AREA"],
        submarkets=[k for k, v in TOLEDO_SUBMARKETS.items() if v.borough == "OTTAWA_HILLS_AREA"],
        city_id="toledo",
    ),
    "WEST_TOLEDO": BoroughMeta(
        name="WEST_TOLEDO",
        center_lat=41.6860,
        center_lng=-83.6025,
        zoom=13.0,
        bbox=TOLEDO_DIVISION_BBOXES["WEST_TOLEDO"],
        submarkets=[k for k, v in TOLEDO_SUBMARKETS.items() if v.borough == "WEST_TOLEDO"],
        city_id="toledo",
    ),
    "NORTH_POINT_PLACE": BoroughMeta(
        name="NORTH_POINT_PLACE",
        center_lat=41.7055,
        center_lng=-83.5058,
        zoom=12.5,
        bbox=TOLEDO_DIVISION_BBOXES["NORTH_POINT_PLACE"],
        submarkets=[k for k, v in TOLEDO_SUBMARKETS.items() if v.borough == "NORTH_POINT_PLACE"],
        city_id="toledo",
    ),
    "SOUTH_TOLEDO_MONASTERY": BoroughMeta(
        name="SOUTH_TOLEDO_MONASTERY",
        center_lat=41.6337,
        center_lng=-83.5927,
        zoom=12.5,
        bbox=TOLEDO_DIVISION_BBOXES["SOUTH_TOLEDO_MONASTERY"],
        submarkets=[k for k, v in TOLEDO_SUBMARKETS.items() if v.borough == "SOUTH_TOLEDO_MONASTERY"],
        city_id="toledo",
    ),
    "EAST_SIDE_BIRMINGHAM": BoroughMeta(
        name="EAST_SIDE_BIRMINGHAM",
        center_lat=41.6588,
        center_lng=-83.4909,
        zoom=13.0,
        bbox=TOLEDO_DIVISION_BBOXES["EAST_SIDE_BIRMINGHAM"],
        submarkets=[k for k, v in TOLEDO_SUBMARKETS.items() if v.borough == "EAST_SIDE_BIRMINGHAM"],
        city_id="toledo",
    ),
}

GREATER_TOLEDO_METRO_BBOX = TOLEDO_METRO_BBOX
TOL_DIVISION_BBOXES = TOLEDO_DIVISION_BBOXES
TOL_SUBMARKETS = TOLEDO_SUBMARKETS
TOL_DIVISIONS = TOLEDO_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28 (US-359). Do not register permits, SLA, deeds, the
# CityworksSRDash dashboard item, or the Hub's static exports.
# ---------------------------------------------------------------------------
TOLEDO_311_ENDPOINT = (
    "https://gis.toledo.oh.gov/arcgis/rest/services/Public/"
    "CityWorks_ServiceRequest_2022/MapServer/0"
)

TOLEDO_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "311": {
        "endpoint": TOLEDO_311_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "INIT_DATE",
        "id_keys": ["REQUEST_ID"],
        "topic_key": "topic_311",
        "interval_seconds": 300.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": TOLEDO_GEOCODE_CONTEXT,
            "oid_field": "REQUEST_ID",
            "max_record_count": 2000,
            "order_by": "INIT_DATE DESC",
            "scope": (
                "Engage Toledo / Cityworks service-request extract, layer 0 "
                "(current-year rolling window despite the 2022 name; "
                "outSR=4326 geometry; do not map Web Mercator X_COORD/Y_COORD; "
                "LOCATION geocode supplement; INIT_BY PII dropped)"
            ),
            "field_map": COMPLAINTS_311_FIELD_MAP,
        },
    },
}


def get_toledo_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Toledo feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in TOLEDO_FEED_SPECS:
        available = ", ".join(sorted(TOLEDO_FEED_SPECS))
        raise KeyError(
            f"'{TOLEDO_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = TOLEDO_FEED_SPECS[feed_name]
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

TOLEDO_COMPLAINTS_311_FIELD_MAP = COMPLAINTS_311_FIELD_MAP

REGISTRATION = SpatialRegistration(
    metro_bbox=TOLEDO_METRO_BBOX,
    division_bboxes=TOLEDO_DIVISION_BBOXES,
    submarkets=TOLEDO_SUBMARKETS,
    divisions=TOLEDO_DIVISIONS,
    contains=is_in_toledo_metro,
)

__all__ = [
    "GREATER_TOLEDO_METRO_BBOX",
    "REGISTRATION",
    "TOL_DIVISION_BBOXES",
    "TOL_DIVISIONS",
    "TOL_SUBMARKETS",
    "TOLEDO_311_ENDPOINT",
    "TOLEDO_CITY_ID",
    "TOLEDO_COMPLAINTS_311_FIELD_MAP",
    "TOLEDO_DIVISION_BBOXES",
    "TOLEDO_DIVISIONS",
    "TOLEDO_FEED_SPECS",
    "TOLEDO_GEOCODE_CONTEXT",
    "TOLEDO_METRO_BBOX",
    "TOLEDO_SUBMARKETS",
    "get_toledo_dataset",
    "is_in_greater_toledo_metro",
    "is_in_toledo_metro",
]
