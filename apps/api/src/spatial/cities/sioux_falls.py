PERMITS_FIELD_MAP = {
    "job_id": ["PERMITNUMBER", "OBJECTID"],
    "issuance_date": ["ISSUEDATE"],
    "filing_date": ["APPLYDATE"],
    "status": ["PERMITSTATUS"],
    "job_type": ["PERMITTYPE", "WORKCLASS"],
    "address_street": ["MAINADDRESS"],
    "proposed_units": ["DwellingUnits"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT = "Sioux Falls, SD"

DROPPED_PII_COLUMNS = ()

"""Sioux Falls, SD spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Sioux Falls
(Minnehaha County, SD).

Sioux Falls is a ONE-FEED PARTIAL metro: PERMITS only, from the DataWorks
hosted layer ``Data/Community/MapServer/3`` (``Building Permits``) on
``gis.siouxfalls.gov``. 311 / SLA / DEEDS stay Tier 3: Rapid City and the
surrounding metros are covered at state level, and South Dakota is a statutory
non-disclosure state (SDCL 7-9-7.2) — Certificates of Real Estate Value are
confidential, so no deed-sales feed exists (probe 2026-08-30).

Live-probe caveats that define this leaf (2026-08-30, US-426):

* PERMITS is the ``Building Permits`` layer at
  ``gis.siouxfalls.gov/arcgis/rest/services/Data/Community/MapServer/3``,
  native point geometry, 180,676 rows live. ``ISSUEDATE`` is the watermark
  (epoch ms); ``APPLYDATE`` / ``FINALIZEDATE`` are companion dates. The layer
  is continuously updated (DataWorks / AGOL Hub publishing).
* ``PERMITSTATUS`` is the status column; ``PERMITTYPE`` + ``WORKCLASS`` split
  the work class; ``MAINADDRESS`` is the street address; ``DwellingUnits``
  feeds proposed_units.
* No neighborhood/district column exists on the layer, so no ``borough``
  field-map candidate is declared: division resolution comes from coordinates
  at ingest.
* Coordinates are native point geometry (``outSR=4326`` lifts to WGS84), so
  ``needs_geocode=False``.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

SIOUX_FALLS_CITY_ID: str = "sioux_falls"
SIOUX_FALLS_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Sioux Falls. Permissive enough to hold the downtown core
# (43.549, -96.729), the East Bank / Arena District (43.535, -96.716), the
# central Falls Park corridor, the Western belt (43.550, -96.790), the
# southern expansion (43.51, -96.73), and the northern industrial edge
# (43.575, -96.72) — while excluding Brandon (43.59, -96.57), Harrisburg
# (43.43, -96.70), and the surrounding Minnehaha County farmland.
SIOUX_FALLS_METRO_BBOX: dict[str, float] = {
    "min_lat": 43.48,
    "max_lat": 43.60,
    "min_lng": -96.82,
    "max_lng": -96.63,
}

SIOUX_FALLS_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 43.540,
        "max_lat": 43.560,
        "min_lng": -96.745,
        "max_lng": -96.710,
    },
    "EAST_BANK": {
        "min_lat": 43.520,
        "max_lat": 43.545,
        "min_lng": -96.735,
        "max_lng": -96.690,
    },
    "WEST_SIOUX_FALLS": {
        "min_lat": 43.500,
        "max_lat": 43.590,
        "min_lng": -96.815,
        "max_lng": -96.745,
    },
    "SOUTH_SIOUX_FALLS": {
        "min_lat": 43.480,
        "max_lat": 43.535,
        "min_lng": -96.780,
        "max_lng": -96.690,
    },
    "NORTH_SIOUX_FALLS": {
        "min_lat": 43.560,
        "max_lat": 43.600,
        "min_lng": -96.790,
        "max_lng": -96.640,
    },
}


def is_in_sioux_falls_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Sioux Falls metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        SIOUX_FALLS_METRO_BBOX["min_lat"] <= lat <= SIOUX_FALLS_METRO_BBOX["max_lat"]
        and SIOUX_FALLS_METRO_BBOX["min_lng"] <= lng <= SIOUX_FALLS_METRO_BBOX["max_lng"]
    )


is_in_greater_sioux_falls_metro = is_in_sioux_falls_metro


SIOUX_FALLS_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (2)
    # =======================================================================
    "Downtown Sioux Falls": SubmarketMeta(
        name="Downtown Sioux Falls",
        borough="DOWNTOWN",
        lat=43.5490,
        lng=-96.7290,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.84,
        capex=8200000.0,
        permit_vel=36.0,
        shift_ratio=1.48,
        sla=62.0,
        description="Phillips Avenue retail and office core with the Levitt Shell, the Washington Pavilion, and high-value adaptive-reuse and mixed-use permitting.",
        city_id="sioux_falls",
    ),
    "Falls Park": SubmarketMeta(
        name="Falls Park",
        borough="DOWNTOWN",
        lat=43.5500,
        lng=-96.7200,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.82,
        capex=6800000.0,
        permit_vel=30.0,
        shift_ratio=1.44,
        sla=58.0,
        description="Big Sioux riverfront around Falls Park with hotel and entertainment investment and the Cherapa Place mixed-use corridor.",
        city_id="sioux_falls",
    ),
    # =======================================================================
    # EAST_BANK (2)
    # =======================================================================
    "East Bank / Arena District": SubmarketMeta(
        name="East Bank / Arena District",
        borough="EAST_BANK",
        lat=43.5350,
        lng=-96.7160,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.80,
        capex=7200000.0,
        permit_vel=32.0,
        shift_ratio=1.42,
        sla=56.0,
        description="East of the river with the Denny Sanford PREMIER Center, the Levitt adjacency, and residential infill and entertainment-adjacent commercial.",
        city_id="sioux_falls",
    ),
    "All Saints / Eastside": SubmarketMeta(
        name="All Saints / Eastside",
        borough="EAST_BANK",
        lat=43.5280,
        lng=-96.7050,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.76,
        capex=5200000.0,
        permit_vel=26.0,
        shift_ratio=1.38,
        sla=52.0,
        description="Historic east-side neighborhoods with tree-lined blocks, steady single-family renovation, and the Augustana University adjacency.",
        city_id="sioux_falls",
    ),
    # =======================================================================
    # WEST_SIOUX_FALLS (2)
    # =======================================================================
    "Western Sioux Falls": SubmarketMeta(
        name="Western Sioux Falls",
        borough="WEST_SIOUX_FALLS",
        lat=43.5450,
        lng=-96.7850,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.80,
        capex=6400000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=56.0,
        description="Western growth corridor with new subdivisions, the Sanford Health western campus expansion, and steady new-build residential permitting.",
        city_id="sioux_falls",
    ),
    "Empire Mall / Southwest": SubmarketMeta(
        name="Empire Mall / Southwest",
        borough="WEST_SIOUX_FALLS",
        lat=43.5280,
        lng=-96.7600,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=5800000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=54.0,
        description="Empire Mall retail node and the 41st Street commercial strip with tenant-improvement and big-box commercial permitting.",
        city_id="sioux_falls",
    ),
    # =======================================================================
    # SOUTH_SIOUX_FALLS (2)
    # =======================================================================
    "Southern Sioux Falls": SubmarketMeta(
        name="Southern Sioux Falls",
        borough="SOUTH_SIOUX_FALLS",
        lat=43.5200,
        lng=-96.7400,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.82,
        capex=7200000.0,
        permit_vel=34.0,
        shift_ratio=1.46,
        sla=60.0,
        description="Southside growth area along Minnesota Avenue and Louise Avenue with master-planned subdivisions and strong new-home permit volume.",
        city_id="sioux_falls",
    ),
    "Marion Road / Southeast": SubmarketMeta(
        name="Marion Road / Southeast",
        borough="SOUTH_SIOUX_FALLS",
        lat=43.5050,
        lng=-96.7100,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=26.0,
        shift_ratio=1.38,
        sla=52.0,
        description="Southeast residential belt along Marion Road with subdivision infill, schools, and community-serving commercial.",
        city_id="sioux_falls",
    ),
    # =======================================================================
    # NORTH_SIOUX_FALLS (1)
    # =======================================================================
    "North Sioux Falls": SubmarketMeta(
        name="North Sioux Falls",
        borough="NORTH_SIOUX_FALLS",
        lat=43.5700,
        lng=-96.7300,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.74,
        capex=5000000.0,
        permit_vel=24.0,
        shift_ratio=1.36,
        sla=50.0,
        description="Northern industrial and gateway corridor with logistics, the airport adjacency, and commercial-industrial permitting.",
        city_id="sioux_falls",
    ),
}


SIOUX_FALLS_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=43.5490,
        center_lng=-96.7290,
        zoom=14.0,
        bbox=SIOUX_FALLS_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in SIOUX_FALLS_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="sioux_falls",
    ),
    "EAST_BANK": BoroughMeta(
        name="EAST_BANK",
        center_lat=43.5300,
        center_lng=-96.7100,
        zoom=14.0,
        bbox=SIOUX_FALLS_DIVISION_BBOXES["EAST_BANK"],
        submarkets=[k for k, v in SIOUX_FALLS_SUBMARKETS.items() if v.borough == "EAST_BANK"],
        city_id="sioux_falls",
    ),
    "WEST_SIOUX_FALLS": BoroughMeta(
        name="WEST_SIOUX_FALLS",
        center_lat=43.5450,
        center_lng=-96.7900,
        zoom=13.5,
        bbox=SIOUX_FALLS_DIVISION_BBOXES["WEST_SIOUX_FALLS"],
        submarkets=[k for k, v in SIOUX_FALLS_SUBMARKETS.items() if v.borough == "WEST_SIOUX_FALLS"],
        city_id="sioux_falls",
    ),
    "SOUTH_SIOUX_FALLS": BoroughMeta(
        name="SOUTH_SIOUX_FALLS",
        center_lat=43.5100,
        center_lng=-96.7400,
        zoom=13.5,
        bbox=SIOUX_FALLS_DIVISION_BBOXES["SOUTH_SIOUX_FALLS"],
        submarkets=[k for k, v in SIOUX_FALLS_SUBMARKETS.items() if v.borough == "SOUTH_SIOUX_FALLS"],
        city_id="sioux_falls",
    ),
    "NORTH_SIOUX_FALLS": BoroughMeta(
        name="NORTH_SIOUX_FALLS",
        center_lat=43.5800,
        center_lng=-96.7300,
        zoom=13.5,
        bbox=SIOUX_FALLS_DIVISION_BBOXES["NORTH_SIOUX_FALLS"],
        submarkets=[k for k, v in SIOUX_FALLS_SUBMARKETS.items() if v.borough == "NORTH_SIOUX_FALLS"],
        city_id="sioux_falls",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-30 (US-426). Do not register Rapid City (Tier 3, RapidMap UI
# only) or any SD deed feed (SDCL 7-9-7.2 non-disclosure).
# ---------------------------------------------------------------------------
SIOUX_FALLS_PERMITS_ENDPOINT = (
    "https://gis.siouxfalls.gov/arcgis/rest/services/Data/Community/MapServer/3"
)

SIOUX_FALLS_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": SIOUX_FALLS_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ISSUEDATE",
        "id_keys": ["PERMITNUMBER", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 1000,
            "order_by": "ISSUEDATE DESC",
            "scope": (
                "Building Permits (MapServer/3, 180,676 rows; native point "
                "geometry; ISSUEDATE watermark; continuously updated via "
                "DataWorks; PERMITSTATUS / PERMITTYPE + WORKCLASS; "
                "MAINADDRESS; DwellingUnits)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
}


def get_sioux_falls_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Sioux Falls feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in SIOUX_FALLS_FEED_SPECS:
        available = ", ".join(sorted(SIOUX_FALLS_FEED_SPECS))
        raise KeyError(
            f"'{SIOUX_FALLS_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = SIOUX_FALLS_FEED_SPECS[feed_name]
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
    metro_bbox=SIOUX_FALLS_METRO_BBOX,
    division_bboxes=SIOUX_FALLS_DIVISION_BBOXES,
    submarkets=SIOUX_FALLS_SUBMARKETS,
    divisions=SIOUX_FALLS_DIVISIONS,
    contains=is_in_sioux_falls_metro,
)

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "REGISTRATION",
    "SIOUX_FALLS_CITY_ID",
    "SIOUX_FALLS_DIVISIONS",
    "SIOUX_FALLS_DIVISION_BBOXES",
    "SIOUX_FALLS_FEED_SPECS",
    "SIOUX_FALLS_GEOCODE_CONTEXT",
    "SIOUX_FALLS_METRO_BBOX",
    "SIOUX_FALLS_PERMITS_ENDPOINT",
    "SIOUX_FALLS_SUBMARKETS",
    "get_sioux_falls_dataset",
    "is_in_greater_sioux_falls_metro",
    "is_in_sioux_falls_metro",
]
