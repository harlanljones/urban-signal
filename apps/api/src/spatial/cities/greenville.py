PERMITS_FIELD_MAP = {
    # OBJECTID is the OID fallback (Henderson precedent): live rows always
    # carry PERMIT_NUM (it is the id_keys head), but the OID keeps
    # coordinate-less/dedup edge rows addressable if a permit number is
    # ever missing client-side.
    "job_id": ["PERMIT_NUM", "OBJECTID"],
    "issuance_date": ["NewIssueDate"],
    "filing_date": ["APPLICDATE"],
    "status": ["BP_STATUS", "Status"],
    "job_type": ["PERMIT_TYPE"],
    "cost": ["PERMIT_VALUATION"],
    "address_street": ["STREETADDRESS"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT = "Greenville, SC"

DROPPED_PII_COLUMNS = (
    "OWNER_NAME",
    "OWNER_ADDR",
    "OWNER_ADDR2",
    "OWNER_ZIP",
    "CONTRACTOR_NAME",
    "CONT_ADDR",
    "CONT_ADDR2",
    "CONT_ZIP",
)

"""Greenville, SC spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Greenville
(upstate South Carolina, Greenville County).

Greenville is a ONE-FEED PARTIAL metro: PERMITS (``BuildingPermits_PriorTwoYears``
on the city's ArcGIS Server 10.81 at ``citygis.greenvillesc.gov``, Tier 1).
COMPLAINTS_311, SLA, and DEEDS are Tier 3 and stay unregistered: 311 backs an
internal-only ``.ads`` host, business licenses are a static 2021-2024 renewal
snapshot with no watermark column, and deeds are parcel CAMA attributes.

Live-probe caveats that define this leaf (original probe 2026-08-28,
``docs/research/probe-greenville.md``; resume re-probe 2026-08-28 UTC,
US-340):

* The ticket's ArcGIS Hub hint is the wrong door — the Hub placeholders are a
  private org (401) and no Socrata exists. The public door is the ArcGIS
  Server 10.81 REST endpoint. The layer is a **MapServer** (not a
  FeatureServer — same ``query`` contract; ``ArcGISClient`` handles both).
* PERMITS is **daily** and date-truncated: newest ``NewIssueDate`` on the
  resume re-probe was unchanged at ``1787803200000`` =
  2026-08-27T04:00:00+00:00 (2026-08-27 local EDT midnight; four co-newest
  rows). The layer holds a **rolling 2-year window** (rows older than that
  are purged — live oldest 2024-01-02), so ``min(date)`` is not staleness
  evidence. Resume re-probe windows: 3d=29, 7d=38, 60d=280, total 3,886
  (probe-day: 7d=17, 60d=264, total 3,874). Window counts must be computed
  client-side from the ordered fetch: the ``time=`` parameter is silently
  ignored (no time definition on the layer — it returns unfiltered counts).
* ``NewIssueDate`` is **not where-clause queryable** (any
  ``NewIssueDate >= ...`` comparison returns ArcGIS error 400 "Failed to
  execute query" while plain columns filter fine) — order with
  ``orderByFields=NewIssueDate DESC`` and filter client-side.
* Coordinates are **native geometry**: queries with ``outSR=4326`` return
  in-city WGS84 point geometry (resume re-probe: x=-82.338…/-82.377…,
  y=34.800…/34.856… on the three captured fixtures; all 3,886 live rows
  carried geometry), which ``ArcGISClient._flatten_feature`` lifts to
  ``latitude``/``longitude``. The ``X_COORD``/``Y_COORD`` *attributes* are
  **State Plane feet** (SC zone, values ≈ 1.58e6 / 1.08e6 — some rows carry
  0.0) — never mapped, never emitted as degrees; the producer's
  projected-coordinate guard is a second net behind that.
* ``STREETADDRESS`` is the address fallback (0 nulls live, resume re-probe
  included): rows arriving without geometry resolve through the ADR 0004
  geocode supplement with context "Greenville, SC". ``APPLICDATE`` is a
  numeric ``YYYYMMDD`` double (not an esri date) and does not ISO-normalize
  client-side — mapping kept for the spine to convert if desired;
  ``filing_date`` stays None until then.
* No neighborhood / district / parcel column exists on the layer, so no
  ``borough`` field-map candidate is declared (Omaha discipline): division
  resolution comes from coordinates at ingest, and ``source_neighborhood``
  passes through as None.
"""

from typing import Any

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

GREENVILLE_CITY_ID: str = "greenville"
GREENVILLE_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Greenville (upstate SC). Permissive enough to hold the Main Street
# downtown core (34.8497, -82.3992), the West End below the Reedy River, the
# Village of West Greenville arts district, the Augusta Road corridor, the
# Verdae/Woodruff growth belt, and the Paris Mountain north edge — plus the
# live re-probe sample down to 34.789, -82.340.
GREENVILLE_METRO_BBOX: dict[str, float] = {
    "min_lat": 34.76,
    "max_lat": 34.93,
    "min_lng": -82.48,
    "max_lng": -82.31,
}

# 6 Greenville divisions. Hand-authored; borough resolution at ingest
# comes from coordinates via get_division_for_coordinate, so bboxes need only
# be sane and contain their own submarket centers.
GREENVILLE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_MAIN_STREET": {
        "min_lat": 34.842,
        "max_lat": 34.860,
        "min_lng": -82.410,
        "max_lng": -82.388,
    },
    "WEST_END": {
        "min_lat": 34.830,
        "max_lat": 34.855,
        "min_lng": -82.435,
        "max_lng": -82.393,
    },
    "NORTH_MAIN": {
        "min_lat": 34.858,
        "max_lat": 34.880,
        "min_lng": -82.415,
        "max_lng": -82.390,
    },
    "AUGUSTA_ROAD": {
        "min_lat": 34.828,
        "max_lat": 34.845,
        "min_lng": -82.398,
        "max_lng": -82.378,
    },
    "EASTSIDE": {
        "min_lat": 34.822,
        "max_lat": 34.865,
        "min_lng": -82.380,
        "max_lng": -82.335,
    },
    "PARIS_MOUNTAIN": {
        "min_lat": 34.880,
        "max_lat": 34.925,
        "min_lng": -82.430,
        "max_lng": -82.370,
    },
}


def is_in_greenville_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Greenville city bounds."""
    if lat is None or lng is None:
        return False
    return (
        GREENVILLE_METRO_BBOX["min_lat"] <= lat <= GREENVILLE_METRO_BBOX["max_lat"]
        and GREENVILLE_METRO_BBOX["min_lng"] <= lng <= GREENVILLE_METRO_BBOX["max_lng"]
    )


is_in_greater_greenville_metro = is_in_greenville_metro


GREENVILLE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_MAIN_STREET (1)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN_MAIN_STREET",
        lat=34.8497,
        lng=-82.3992,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.86,
        capex=6400000.0,
        permit_vel=29.0,
        shift_ratio=1.46,
        sla=52.0,
        description="Main Street core with the Falls Park riverfront, hotel/office adaptive reuse, and the award-winning downtown mixed-use permitting corridor.",
        city_id="greenville",
    ),
    # =======================================================================
    # WEST_END (2)
    # =======================================================================
    "West End": SubmarketMeta(
        name="West End",
        borough="WEST_END",
        lat=34.8413,
        lng=-82.4030,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.88,
        capex=6900000.0,
        permit_vel=31.0,
        shift_ratio=1.50,
        sla=55.0,
        description="Historic warehouse district below the Reedy River with Fluor Field anchors, loft conversions, and the metro's strongest restaurant-row foot traffic.",
        city_id="greenville",
    ),
    "Village of West Greenville": SubmarketMeta(
        name="Village of West Greenville",
        borough="WEST_END",
        lat=34.8455,
        lng=-82.4235,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.84,
        capex=5800000.0,
        permit_vel=26.0,
        shift_ratio=1.44,
        sla=50.0,
        description="Pendleton Street arts district with mill-structure studios, cottage infill, and artist-led commercial rehabilitation permits.",
        city_id="greenville",
    ),
    # =======================================================================
    # NORTH_MAIN (1)
    # =======================================================================
    "North Main": SubmarketMeta(
        name="North Main",
        borough="NORTH_MAIN",
        lat=34.8670,
        lng=-82.4010,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=6100000.0,
        permit_vel=24.0,
        shift_ratio=1.42,
        sla=51.0,
        description="North Main Street corridor of bungalow stock and infill townhomes between downtown and the Paris Mountain slopes.",
        city_id="greenville",
    ),
    # =======================================================================
    # AUGUSTA_ROAD (1)
    # =======================================================================
    "Augusta Road": SubmarketMeta(
        name="Augusta Road",
        borough="AUGUSTA_ROAD",
        lat=34.8370,
        lng=-82.3860,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.89,
        capex=7200000.0,
        permit_vel=28.0,
        shift_ratio=1.51,
        sla=56.0,
        description="Augusta Street retail-residential spine with walkable shopfronts, pre-war renovation, and steady high-valuation alteration permits.",
        city_id="greenville",
    ),
    # =======================================================================
    # EASTSIDE (2)
    # =======================================================================
    "Overbrook": SubmarketMeta(
        name="Overbrook",
        borough="EASTSIDE",
        lat=34.8565,
        lng=-82.3670,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=5500000.0,
        permit_vel=23.0,
        shift_ratio=1.40,
        sla=49.0,
        description="Overbrook/Stone Avenue east side with starter-home turnover, duplex conversions, and Stone Ave mixed-use nodes.",
        city_id="greenville",
    ),
    "Verdae": SubmarketMeta(
        name="Verdae",
        borough="EASTSIDE",
        lat=34.8330,
        lng=-82.3460,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.82,
        capex=7800000.0,
        permit_vel=27.0,
        shift_ratio=1.47,
        sla=53.0,
        description="Verdae Boulevard and Woodruff Road growth belt with master-planned multifamily, office park expansion, and the metro's largest new-build valuations.",
        city_id="greenville",
    ),
    # =======================================================================
    # PARIS_MOUNTAIN (1)
    # =======================================================================
    "Paris Mountain Edge": SubmarketMeta(
        name="Paris Mountain Edge",
        borough="PARIS_MOUNTAIN",
        lat=34.9020,
        lng=-82.3960,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.81,
        capex=6600000.0,
        permit_vel=21.0,
        shift_ratio=1.38,
        sla=48.0,
        description="South slopes of Paris Mountain at the city's north edge with view-lot estate builds and state-park-adjacent low-density permitting.",
        city_id="greenville",
    ),
}


GREENVILLE_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_MAIN_STREET": BoroughMeta(
        name="DOWNTOWN_MAIN_STREET",
        center_lat=34.8497,
        center_lng=-82.3992,
        zoom=14.0,
        bbox=GREENVILLE_DIVISION_BBOXES["DOWNTOWN_MAIN_STREET"],
        submarkets=[k for k, v in GREENVILLE_SUBMARKETS.items() if v.borough == "DOWNTOWN_MAIN_STREET"],
        city_id="greenville",
    ),
    "WEST_END": BoroughMeta(
        name="WEST_END",
        center_lat=34.8413,
        center_lng=-82.4030,
        zoom=14.0,
        bbox=GREENVILLE_DIVISION_BBOXES["WEST_END"],
        submarkets=[k for k, v in GREENVILLE_SUBMARKETS.items() if v.borough == "WEST_END"],
        city_id="greenville",
    ),
    "NORTH_MAIN": BoroughMeta(
        name="NORTH_MAIN",
        center_lat=34.8670,
        center_lng=-82.4010,
        zoom=13.5,
        bbox=GREENVILLE_DIVISION_BBOXES["NORTH_MAIN"],
        submarkets=[k for k, v in GREENVILLE_SUBMARKETS.items() if v.borough == "NORTH_MAIN"],
        city_id="greenville",
    ),
    "AUGUSTA_ROAD": BoroughMeta(
        name="AUGUSTA_ROAD",
        center_lat=34.8370,
        center_lng=-82.3860,
        zoom=14.0,
        bbox=GREENVILLE_DIVISION_BBOXES["AUGUSTA_ROAD"],
        submarkets=[k for k, v in GREENVILLE_SUBMARKETS.items() if v.borough == "AUGUSTA_ROAD"],
        city_id="greenville",
    ),
    "EASTSIDE": BoroughMeta(
        name="EASTSIDE",
        center_lat=34.8565,
        center_lng=-82.3670,
        zoom=13.0,
        bbox=GREENVILLE_DIVISION_BBOXES["EASTSIDE"],
        submarkets=[k for k, v in GREENVILLE_SUBMARKETS.items() if v.borough == "EASTSIDE"],
        city_id="greenville",
    ),
    "PARIS_MOUNTAIN": BoroughMeta(
        name="PARIS_MOUNTAIN",
        center_lat=34.9020,
        center_lng=-82.3960,
        zoom=13.0,
        bbox=GREENVILLE_DIVISION_BBOXES["PARIS_MOUNTAIN"],
        submarkets=[k for k, v in GREENVILLE_SUBMARKETS.items() if v.borough == "PARIS_MOUNTAIN"],
        city_id="greenville",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28, re-probed 2026-08-28. Do not register 311 (internal-only
# .ads host), the BusinessLicensesForHUB_2025 snapshot, parcel CAMA, or the
# private Hub placeholders.
# ---------------------------------------------------------------------------
GREENVILLE_PERMITS_ENDPOINT = (
    "https://citygis.greenvillesc.gov/arcgis/rest/services/"
    "InfoHUB/BuildingPermits_PriorTwoYears/MapServer/0"
)

GREENVILLE_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": GREENVILLE_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "NewIssueDate",
        "id_keys": ["PERMIT_NUM"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": GREENVILLE_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 7000,
            "order_by": "NewIssueDate DESC",
            "scope": (
                "BuildingPermits_PriorTwoYears issued permits (MapServer on "
                "citygis ArcGIS Server 10.81 — same query contract, not a "
                "FeatureServer; rolling 2-year window so min(date) is not "
                "staleness; native outSR=4326 point geometry primary, "
                "State Plane X_COORD/Y_COORD attributes never mapped; "
                "NewIssueDate is not where-clause queryable (ArcGIS 400) — "
                "orderByFields only, filter at analytics; BP_STATUS 'IS' = "
                "issued)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
}


def get_greenville_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Greenville feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in GREENVILLE_FEED_SPECS:
        available = ", ".join(sorted(GREENVILLE_FEED_SPECS))
        raise KeyError(
            f"'{GREENVILLE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = GREENVILLE_FEED_SPECS[feed_name]
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
    metro_bbox=GREENVILLE_METRO_BBOX,
    division_bboxes=GREENVILLE_DIVISION_BBOXES,
    submarkets=GREENVILLE_SUBMARKETS,
    divisions=GREENVILLE_DIVISIONS,
    contains=is_in_greenville_metro,
)

__all__ = [
    "GREENVILLE_CITY_ID",
    "GREENVILLE_DIVISIONS",
    "GREENVILLE_DIVISION_BBOXES",
    "GREENVILLE_FEED_SPECS",
    "GREENVILLE_GEOCODE_CONTEXT",
    "GREENVILLE_METRO_BBOX",
    "GREENVILLE_PERMITS_ENDPOINT",
    "GREENVILLE_SUBMARKETS",
    "REGISTRATION",
    "get_greenville_dataset",
    "is_in_greater_greenville_metro",
    "is_in_greenville_metro",
]
