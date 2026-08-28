"""Bozeman, MT spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Bozeman
(southwest Montana, Gallatin County).

Bozeman is a TWO-FEED PARTIAL metro: PERMITS (``BP_Comm_Dev_Report_Data_view``
hosted FeatureServer on ``services3.arcgis.com``, Tier 1, ~24k rows, daily)
and CRIME (``BPD_CFS_Public_30_Days``, Tier 1, ~5k rows, 30-day rolling window,
native point geometry — ADR 0004 satisfied). COMPLAINTS_311, SLA (business
licenses), and Gallatin County recorded deeds are Tier 3: no bulk 311 feed,
no business license registry, and Gallatin County recorder not bulk-accessible.

Live-probe caveats that define this leaf (probed 2026-08-28, US-236):

* The PERMITS feed is the cleaned public view (``BP_Comm_Dev_Report_Data_view``
  on AGOL hosted FeatureServer) — not the ``Internal/Building_Permits/MapServer``
  (3 layers, 6-month rolling window, carries contractor/owner PII). The
  view has no PII columns and is the registration target.
* **Mixed-CRS trap**: the view's ``LATITUDE``/``LONGITUDE`` attribute columns are
  **Montana State Plane (NAD83 26912) feet**, not decimal degrees (live values
  ≈ 5.06e6 / 4.9e5). The geometry is the real coordinate source: every query
  requests ``outSR=4326`` and the ``ArcGISClient`` lift produces proper WGS84
  lat/lng. The producer's projected-coordinate guard (``abs > 90``) catches
  any accidental mapping of these columns.
* PERMITS watermark is ``PERMIT_ISSUE_DATE`` (esriFieldTypeDate, epoch-ms).
  Newest live row: 1787814000000 = 2026-08-27T07:00 UTC. Where-clause on
  ``PERMIT_ISSUE_DATE`` works with ANSI ``DATE`` literal.
* CRIME (BPD CFS) is a **30-day rolling window** — ``min(date)`` is not
  staleness evidence. Newest ``DATE`` = 1787814000000 = 2026-08-27T07:00 UTC.
  Native point geometry in WGS84 (store SR 102100/3857, outSR=4326 honored).
* No borough/neighborhood/district column exists on either layer (Omaha
  discipline): ``source_neighborhood`` passes through None and division
  resolution comes from coordinates at ingest.
* No site-zip column exists on either layer, so ``zipcode`` stays undeclared.
* 7 divisions based on the city's 5 official Tax Increment District / Urban
  Renewal Districts (TIF/URD) plus the Valley West and Bridger/College
  corridors (real neighborhoods named in city planning documents).
"""

from src.producers.field_maps_bozeman import (
    CRIME_FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

BOZEMAN_CITY_ID: str = "bozeman"
BOZEMAN_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Bozeman, MT (Gallatin County). Bbox from the official city limits
# layer (verified 2026-08-28: extent -111.12..-110.984 / 45.633..45.733)
# with a small buffer to include near-city edge fixtures.
BOZEMAN_METRO_BBOX: dict[str, float] = {
    "min_lat": 45.63,
    "max_lat": 45.74,
    "min_lng": -111.13,
    "max_lng": -110.98,
}

# 7 Bozeman divisions. Hand-authored; borough resolution at ingest
# comes from coordinates via get_division_for_coordinate, so bboxes need only
# be sane and contain their own submarket centers.
# Divisions are anchored on the city's five official Tax Increment / Urban
# Renewal Districts (TIDs/URDs) plus Valley West (SW corridor) and
# Bridger/College (MSU campus area).
BOZEMAN_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 45.673,
        "max_lat": 45.682,
        "min_lng": -111.044,
        "max_lng": -111.025,
    },
    "MIDTOWN": {
        "min_lat": 45.678,
        "max_lat": 45.706,
        "min_lng": -111.057,
        "max_lng": -111.035,
    },
    "NORTH_PARK": {
        "min_lat": 45.700,
        "max_lat": 45.717,
        "min_lng": -111.064,
        "max_lng": -111.046,
    },
    "STORY_MILL": {
        "min_lat": 45.684,
        "max_lat": 45.690,
        "min_lng": -111.032,
        "max_lng": -111.024,
    },
    "SOUTH_TECH": {
        "min_lat": 45.667,
        "max_lat": 45.672,
        "min_lng": -111.074,
        "max_lng": -111.067,
    },
    "VALLEY_WEST": {
        "min_lat": 45.645,
        "max_lat": 45.675,
        "min_lng": -111.090,
        "max_lng": -111.060,
    },
    "BRIDGER_COLLEGE": {
        "min_lat": 45.650,
        "max_lat": 45.675,
        "min_lng": -111.055,
        "max_lng": -111.035,
    },
}


def is_in_bozeman_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Bozeman metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        BOZEMAN_METRO_BBOX["min_lat"] <= lat <= BOZEMAN_METRO_BBOX["max_lat"]
        and BOZEMAN_METRO_BBOX["min_lng"] <= lng <= BOZEMAN_METRO_BBOX["max_lng"]
    )


is_in_greater_bozeman_metro = is_in_bozeman_metro


BOZEMAN_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (2)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN",
        lat=45.6777,
        lng=-111.0387,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.85,
        capex=7800000.0,
        permit_vel=35.0,
        shift_ratio=1.48,
        sla=55.0,
        description="Main Street core with the Emerson Center, the Ellen Theatre, and the downtown mixed-use corridor anchored by redevelopment along Main, Willson, and Tracy.",
        city_id="bozeman",
    ),
    "Bozeman Armory": SubmarketMeta(
        name="Bozeman Armory",
        borough="DOWNTOWN",
        lat=45.6760,
        lng=-111.0410,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.83,
        capex=7200000.0,
        permit_vel=32.0,
        shift_ratio=1.45,
        sla=53.0,
        description="Armory block south of Main with the historic Armory Hall, gallery district, and craft-beer-anchored infill along the MSU boulevard edge.",
        city_id="bozeman",
    ),
    # =======================================================================
    # MIDTOWN (2)
    # =======================================================================
    "North 7th Avenue": SubmarketMeta(
        name="North 7th Avenue",
        borough="MIDTOWN",
        lat=45.6900,
        lng=-111.0470,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.84,
        capex=7500000.0,
        permit_vel=33.0,
        shift_ratio=1.46,
        sla=54.0,
        description="North 7th Avenue industrial-to-residential corridor with Midtown Urban Renewal District incentives, warehouse conversions, and the Cannery District redevelopment.",
        city_id="bozeman",
    ),
    "Bozeman Health": SubmarketMeta(
        name="Bozeman Health",
        borough="MIDTOWN",
        lat=45.6850,
        lng=-111.0450,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.86,
        capex=8200000.0,
        permit_vel=36.0,
        shift_ratio=1.50,
        sla=57.0,
        description="Bozeman Health Deaconess Hospital anchor corridor with medical-office demand, clinic expansion, and associated multifamily development.",
        city_id="bozeman",
    ),
    # =======================================================================
    # NORTH_PARK (1)
    # =======================================================================
    "North Park": SubmarketMeta(
        name="North Park",
        borough="NORTH_PARK",
        lat=45.7080,
        lng=-111.0550,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.82,
        capex=6900000.0,
        permit_vel=30.0,
        shift_ratio=1.43,
        sla=51.0,
        description="North Park Urban Renewal District at the city's north edge with master-planned residential subdivisions, the North Park business park, and new-build hometracts.",
        city_id="bozeman",
    ),
    # =======================================================================
    # STORY_MILL (1)
    # =======================================================================
    "Story Mill": SubmarketMeta(
        name="Story Mill",
        borough="STORY_MILL",
        lat=45.6870,
        lng=-111.0280,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.83,
        capex=7100000.0,
        permit_vel=31.0,
        shift_ratio=1.44,
        sla=52.0,
        description="Northeast Neighborhood Urban Renewal District with the Story Mill community garden, Baxter Meadows, and the historic mill-redevelopment corridor along E Story Mill Road.",
        city_id="bozeman",
    ),
    # =======================================================================
    # SOUTH_TECH (1)
    # =======================================================================
    "South Bozeman Tech": SubmarketMeta(
        name="South Bozeman Tech",
        borough="SOUTH_TECH",
        lat=45.6695,
        lng=-111.0705,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.85,
        capex=8500000.0,
        permit_vel=34.0,
        shift_ratio=1.49,
        sla=56.0,
        description="South Bozeman Technology District west of 19th Avenue with tech-firm campuses, R&D flex space, and the metro's highest commercial-valuation corridor.",
        city_id="bozeman",
    ),
    # =======================================================================
    # VALLEY_WEST (1)
    # =======================================================================
    "Valley West": SubmarketMeta(
        name="Valley West",
        borough="VALLEY_WEST",
        lat=45.6610,
        lng=-111.0770,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=6800000.0,
        permit_vel=28.0,
        shift_ratio=1.42,
        sla=50.0,
        description="Valley West Drive and West Main Street corridor with low-density residential subdivisions, big-box retail, and the West Main auto-oriented commercial strip.",
        city_id="bozeman",
    ),
    # =======================================================================
    # BRIDGER_COLLEGE (2)
    # =======================================================================
    "Bridger College": SubmarketMeta(
        name="Bridger College",
        borough="BRIDGER_COLLEGE",
        lat=45.6699,
        lng=-111.0482,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.87,
        capex=9000000.0,
        permit_vel=38.0,
        shift_ratio=1.54,
        sla=60.0,
        description="Montana State University campus anchor corridor with College Street student housing, university mixed-use development, and the Grant Street innovation belt.",
        city_id="bozeman",
    ),
    "Baxter/Highland": SubmarketMeta(
        name="Baxter/Highland",
        borough="BRIDGER_COLLEGE",
        lat=45.6530,
        lng=-111.0500,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.80,
        capex=6500000.0,
        permit_vel=27.0,
        shift_ratio=1.40,
        sla=49.0,
        description="Baxter Lane and Highland Boulevard southern corridor with single-family stock, the Highland Park subdivision, and steady low-valuation alteration permits.",
        city_id="bozeman",
    ),
}


BOZEMAN_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=45.6777,
        center_lng=-111.0387,
        zoom=14.0,
        bbox=BOZEMAN_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in BOZEMAN_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="bozeman",
    ),
    "MIDTOWN": BoroughMeta(
        name="MIDTOWN",
        center_lat=45.6900,
        center_lng=-111.0470,
        zoom=13.5,
        bbox=BOZEMAN_DIVISION_BBOXES["MIDTOWN"],
        submarkets=[k for k, v in BOZEMAN_SUBMARKETS.items() if v.borough == "MIDTOWN"],
        city_id="bozeman",
    ),
    "NORTH_PARK": BoroughMeta(
        name="NORTH_PARK",
        center_lat=45.7080,
        center_lng=-111.0550,
        zoom=13.0,
        bbox=BOZEMAN_DIVISION_BBOXES["NORTH_PARK"],
        submarkets=[k for k, v in BOZEMAN_SUBMARKETS.items() if v.borough == "NORTH_PARK"],
        city_id="bozeman",
    ),
    "STORY_MILL": BoroughMeta(
        name="STORY_MILL",
        center_lat=45.6870,
        center_lng=-111.0280,
        zoom=13.5,
        bbox=BOZEMAN_DIVISION_BBOXES["STORY_MILL"],
        submarkets=[k for k, v in BOZEMAN_SUBMARKETS.items() if v.borough == "STORY_MILL"],
        city_id="bozeman",
    ),
    "SOUTH_TECH": BoroughMeta(
        name="SOUTH_TECH",
        center_lat=45.6695,
        center_lng=-111.0705,
        zoom=13.0,
        bbox=BOZEMAN_DIVISION_BBOXES["SOUTH_TECH"],
        submarkets=[k for k, v in BOZEMAN_SUBMARKETS.items() if v.borough == "SOUTH_TECH"],
        city_id="bozeman",
    ),
    "VALLEY_WEST": BoroughMeta(
        name="VALLEY_WEST",
        center_lat=45.6610,
        center_lng=-111.0770,
        zoom=13.0,
        bbox=BOZEMAN_DIVISION_BBOXES["VALLEY_WEST"],
        submarkets=[k for k, v in BOZEMAN_SUBMARKETS.items() if v.borough == "VALLEY_WEST"],
        city_id="bozeman",
    ),
    "BRIDGER_COLLEGE": BoroughMeta(
        name="BRIDGER_COLLEGE",
        center_lat=45.6699,
        center_lng=-111.0482,
        zoom=13.5,
        bbox=BOZEMAN_DIVISION_BBOXES["BRIDGER_COLLEGE"],
        submarkets=[k for k, v in BOZEMAN_SUBMARKETS.items() if v.borough == "BRIDGER_COLLEGE"],
        city_id="bozeman",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Do not register 311 (no bulk feed), SLA (no business
# license registry), or deeds (Gallatin County recorder not bulk-accessible).
# ---------------------------------------------------------------------------
BOZEMAN_PERMITS_ENDPOINT = (
    "https://services3.arcgis.com/f4hk1qcfxRJ0L2BU/arcgis/rest/services/"
    "BP_Comm_Dev_Report_Data_view/FeatureServer/0"
)

BOZEMAN_CFS_ENDPOINT = (
    "https://gisweb.bozeman.net/hosted/rest/services/"
    "BPD_CFS_Public_30_Days/FeatureServer/0"
)

BOZEMAN_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": BOZEMAN_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "PERMIT_ISSUE_DATE",
        "id_keys": ["PERMIT_NUMBER", "APPLICATION_NUMBER", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": BOZEMAN_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 1000,
            "order_by": "PERMIT_ISSUE_DATE DESC",
            "scope": (
                "BP_Comm_Dev_Report_Data_view — public AGOL FeatureServer view "
                "of Building Permits (24,338 rows, daily PERMIT_ISSUE_DATE "
                "watermark, 2026-08-27 newest). Native point geometry via "
                "outSR=4326; LATITUDE/LONGITUDE attribute columns are Montana "
                "State Plane (NAD83 26912) feet — mixed-CRS trap, NOT mapped. "
                "No PII. No neighborhood/zip column. LOCATION address fallback "
                "for null-geometry geocode. Internal/Building_Permits/MapServer "
                "companion NOT registered (PII, rolling 6-month window)."
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "crime": {
        "endpoint": BOZEMAN_CFS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "DATE",
        "id_keys": ["INCIDENT_NUMBER", "CASE_NUMBER", "OBJECTID"],
        "topic_key": "topic_crime",
        "interval_seconds": 300.0,
        "producer_key": "crime",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 20000,
            "order_by": "DATE DESC",
            "scope": (
                "BPD_CFS_Public_30_Days — hosted FeatureServer of Bozeman "
                "Police Department calls-for-service (5,202 rows, rolling "
                "30-day window, DATE watermark 2026-08-27 newest). Native "
                "point geometry WGS84 (store SR 102100/3857, outSR=4326). "
                "ADR 0004 satisfied: native coordinates on every captured "
                "row. 30-day rolling window — min(DATE) not staleness."
            ),
            "field_map": CRIME_FIELD_MAP,
        },
    },
}


def get_bozeman_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Bozeman feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in BOZEMAN_FEED_SPECS:
        available = ", ".join(sorted(BOZEMAN_FEED_SPECS))
        raise KeyError(
            f"'{BOZEMAN_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = BOZEMAN_FEED_SPECS[feed_name]
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
    metro_bbox=BOZEMAN_METRO_BBOX,
    division_bboxes=BOZEMAN_DIVISION_BBOXES,
    submarkets=BOZEMAN_SUBMARKETS,
    divisions=BOZEMAN_DIVISIONS,
    contains=is_in_bozeman_metro,
)

__all__ = [
    "BOZEMAN_CFS_ENDPOINT",
    "BOZEMAN_CITY_ID",
    "BOZEMAN_DIVISIONS",
    "BOZEMAN_DIVISION_BBOXES",
    "BOZEMAN_FEED_SPECS",
    "BOZEMAN_GEOCODE_CONTEXT",
    "BOZEMAN_METRO_BBOX",
    "BOZEMAN_PERMITS_ENDPOINT",
    "BOZEMAN_SUBMARKETS",
    "REGISTRATION",
    "get_bozeman_dataset",
    "is_in_bozeman_metro",
    "is_in_greater_bozeman_metro",
]