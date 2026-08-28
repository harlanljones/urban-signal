"""Syracuse, NY spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Syracuse
(Onondaga County, NY).

Syracuse is a ONE-FEED PARTIAL metro: SLA via the **Syracuse Rental
Registry** (``Syracuse_Rental_Registry`` on the city's AGOL org
``services6.arcgis.com/bdPqSfflsdgFRVVM``, Tier 1). The ticket hint hostname
``data.cityofsyracuse.gov`` does not resolve — the live portal is the
ArcGIS Hub at ``data.syrgov.net``. PERMITS (``Permit_Requests``, 47,902
rows) is frozen at a 2025-08-16 max with weak geocode coverage and stays
unregistered; 311 is absent (CitizenServe, no open extract) and the
quarterly parcel maps carry assessment fields only — no sale/deed columns.

Live-probe caveats that define this leaf (probed 2026-08-27, US-352):

* SLA is **incremental and current**: watermark ``RR_app_received`` —
  newest 2026-08-26 on the probe/re-probe (13 in 7d, 196 in 60d, 1,254 in
  2026 YTD, 10,926 total). This is rental-property registration — the
  licenses family's strongest grain in Syracuse; there is no general
  business-license feed.
* Native WGS84 ``Latitude``/``Longitude`` attribute columns at 500/500
  completeness on the newest window (43.02–43.07, −76.15…−76.09) —
  ``needs_geocode`` stays False, no ADR 0004 dependency. Column spellings
  are capitalized, so ``SYRACUSE_SLA_FIELD_MAP`` is what reaches them
  (the generic chains only read lowercase keys).
* id_keys ``SBL``; renewals reappear as new applications (same
  multi-row-per-entity caveat as Buffalo licenses) — key on
  ``SBL`` + ``RR_app_received`` if row-level idempotency is ever needed.
* ESRI null-date placeholder epoch (−2208902400000 → ``1900-01-02``) rides
  ``completion_date``/``valid_until`` on fresh applications; granted rows
  carry real ``valid_until`` years out to 2029.
* PII dropped at the map: ``RR_contact_name``, ``pc_owner``.
"""

from typing import Any

from src.producers.field_maps_syracuse import SYRACUSE_SLA_FIELD_MAP
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

SYRACUSE_CITY_ID: str = "syracuse"

# City of Syracuse (Onondaga County, central NY). Permissive enough to hold
# the downtown core and Armory Square (43.048, -76.157), the SU / University
# hill, Eastwood, Strathmore, the North Side, and the Outer Comstock student
# belt (live registry sample at 43.0336, -76.1291).
SYRACUSE_METRO_BBOX: dict[str, float] = {
    "min_lat": 42.99,
    "max_lat": 43.13,
    "min_lng": -76.24,
    "max_lng": -76.05,
}

# 6 Syracuse divisions / 8 submarkets. Hand-authored; borough resolution at
# ingest comes from coordinates via get_division_for_coordinate, so bboxes
# need only be sane and contain their own submarket centers.
SYRACUSE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_CORE": {
        "min_lat": 43.042,
        "max_lat": 43.058,
        "min_lng": -76.166,
        "max_lng": -76.145,
    },
    "UNIVERSITY_EAST": {
        "min_lat": 43.034,
        "max_lat": 43.048,
        "min_lng": -76.136,
        "max_lng": -76.110,
    },
    "EASTWOOD": {
        "min_lat": 43.066,
        "max_lat": 43.084,
        "min_lng": -76.122,
        "max_lng": -76.092,
    },
    "STRATHMORE": {
        "min_lat": 43.018,
        "max_lat": 43.036,
        "min_lng": -76.198,
        "max_lng": -76.162,
    },
    "NORTH_SIDE": {
        "min_lat": 43.060,
        "max_lat": 43.082,
        "min_lng": -76.166,
        "max_lng": -76.138,
    },
    "OUTER_COMSTOCK": {
        "min_lat": 43.026,
        "max_lat": 43.040,
        "min_lng": -76.142,
        "max_lng": -76.114,
    },
}


def is_in_syracuse_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Syracuse city bounds."""
    if lat is None or lng is None:
        return False
    return (
        SYRACUSE_METRO_BBOX["min_lat"] <= lat <= SYRACUSE_METRO_BBOX["max_lat"]
        and SYRACUSE_METRO_BBOX["min_lng"] <= lng <= SYRACUSE_METRO_BBOX["max_lng"]
    )


SYRACUSE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CORE (2)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN_CORE",
        lat=43.0503,
        lng=-76.1525,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.78,
        capex=5200000.0,
        permit_vel=28.0,
        shift_ratio=1.42,
        sla=52.0,
        description="Civic and office core around Clinton Square and the Commons with conversion-condo activity and hotel-adjacent mixed-use interest.",
        city_id="syracuse",
    ),
    "Armory Square": SubmarketMeta(
        name="Armory Square",
        borough="DOWNTOWN_CORE",
        lat=43.0471,
        lng=-76.1572,
        zoom=15.0,
        pitch=55.0,
        base_lims=0.82,
        capex=5600000.0,
        permit_vel=26.0,
        shift_ratio=1.45,
        sla=54.0,
        description="Warehouse-district entertainment core with loft conversions, restaurant rows, and the strongest downtown rental demand.",
        city_id="syracuse",
    ),
    # =======================================================================
    # UNIVERSITY_EAST (2)
    # =======================================================================
    "University Area": SubmarketMeta(
        name="University Area",
        borough="UNIVERSITY_EAST",
        lat=43.0392,
        lng=-76.1271,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=6100000.0,
        permit_vel=30.0,
        shift_ratio=1.52,
        sla=58.0,
        description="SU hill and the Howard St corridor with perpetual student-rental churn, hospital-system adjacency, and the metro's tightest registration pressure.",
        city_id="syracuse",
    ),
    "Westcott": SubmarketMeta(
        name="Westcott",
        borough="UNIVERSITY_EAST",
        lat=43.0420,
        lng=-76.1180,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.84,
        capex=5400000.0,
        permit_vel=24.0,
        shift_ratio=1.46,
        sla=55.0,
        description="Westcott Street neighborhood of two- to four-family student and faculty housing with steady turnover and storefront revitalization.",
        city_id="syracuse",
    ),
    # =======================================================================
    # EASTWOOD (1)
    # =======================================================================
    "Eastwood": SubmarketMeta(
        name="Eastwood",
        borough="EASTWOOD",
        lat=43.0750,
        lng=-76.1060,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=4800000.0,
        permit_vel=22.0,
        shift_ratio=1.40,
        sla=50.0,
        description="Northeast village-in-the-city on James Street with duplex stock, Medley Centre adjacency, and value-priced rental conversions.",
        city_id="syracuse",
    ),
    # =======================================================================
    # STRATHMORE (1)
    # =======================================================================
    "Strathmore": SubmarketMeta(
        name="Strathmore",
        borough="STRATHMORE",
        lat=43.0270,
        lng=-76.1790,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.85,
        capex=5800000.0,
        permit_vel=20.0,
        shift_ratio=1.44,
        sla=56.0,
        description="Southwest hillside of 1920s singles and upper-flat conversions bordering the golf course with the metro's most stable owner-occupancy.",
        city_id="syracuse",
    ),
    # =======================================================================
    # NORTH_SIDE (1)
    # =======================================================================
    "North Side": SubmarketMeta(
        name="North Side",
        borough="NORTH_SIDE",
        lat=43.0710,
        lng=-76.1520,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.74,
        capex=4200000.0,
        permit_vel=26.0,
        shift_ratio=1.48,
        sla=46.0,
        description="Little Italy and the North Salina corridor with older multi-family stock, refugee-settlement rental demand, and heavy registry activity.",
        city_id="syracuse",
    ),
    # =======================================================================
    # OUTER_COMSTOCK (1)
    # =======================================================================
    "Outer Comstock": SubmarketMeta(
        name="Outer Comstock",
        borough="OUTER_COMSTOCK",
        lat=43.0336,
        lng=-76.1285,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=5700000.0,
        permit_vel=23.0,
        shift_ratio=1.43,
        sla=54.0,
        description="Comstock Avenue student-rental belt southeast of campus with large legacy houses cut into units and the highest per-property registrant churn.",
        city_id="syracuse",
    ),
}


SYRACUSE_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=43.0503,
        center_lng=-76.1525,
        zoom=14.5,
        bbox=SYRACUSE_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in SYRACUSE_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="syracuse",
    ),
    "UNIVERSITY_EAST": BoroughMeta(
        name="UNIVERSITY_EAST",
        center_lat=43.0392,
        center_lng=-76.1271,
        zoom=14.0,
        bbox=SYRACUSE_DIVISION_BBOXES["UNIVERSITY_EAST"],
        submarkets=[k for k, v in SYRACUSE_SUBMARKETS.items() if v.borough == "UNIVERSITY_EAST"],
        city_id="syracuse",
    ),
    "EASTWOOD": BoroughMeta(
        name="EASTWOOD",
        center_lat=43.0750,
        center_lng=-76.1060,
        zoom=14.0,
        bbox=SYRACUSE_DIVISION_BBOXES["EASTWOOD"],
        submarkets=[k for k, v in SYRACUSE_SUBMARKETS.items() if v.borough == "EASTWOOD"],
        city_id="syracuse",
    ),
    "STRATHMORE": BoroughMeta(
        name="STRATHMORE",
        center_lat=43.0270,
        center_lng=-76.1790,
        zoom=13.5,
        bbox=SYRACUSE_DIVISION_BBOXES["STRATHMORE"],
        submarkets=[k for k, v in SYRACUSE_SUBMARKETS.items() if v.borough == "STRATHMORE"],
        city_id="syracuse",
    ),
    "NORTH_SIDE": BoroughMeta(
        name="NORTH_SIDE",
        center_lat=43.0710,
        center_lng=-76.1520,
        zoom=14.0,
        bbox=SYRACUSE_DIVISION_BBOXES["NORTH_SIDE"],
        submarkets=[k for k, v in SYRACUSE_SUBMARKETS.items() if v.borough == "NORTH_SIDE"],
        city_id="syracuse",
    ),
    "OUTER_COMSTOCK": BoroughMeta(
        name="OUTER_COMSTOCK",
        center_lat=43.0336,
        center_lng=-76.1285,
        zoom=14.0,
        bbox=SYRACUSE_DIVISION_BBOXES["OUTER_COMSTOCK"],
        submarkets=[k for k, v in SYRACUSE_SUBMARKETS.items() if v.borough == "OUTER_COMSTOCK"],
        city_id="syracuse",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27 (US-352). Do not register permits (frozen 2025-08-16),
# 311 (absent), deeds (assessment-only parcel maps), or sibling Hub views.
# ---------------------------------------------------------------------------
SYRACUSE_SLA_ENDPOINT = (
    "https://services6.arcgis.com/bdPqSfflsdgFRVVM/arcgis/rest/services/"
    "Syracuse_Rental_Registry/FeatureServer/0"
)

SYRACUSE_FEED_SPECS: dict[str, dict[str, object]] = {
    "sla": {
        "endpoint": SYRACUSE_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "RR_app_received",
        "id_keys": ["SBL"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "ObjectId",
            "max_record_count": 1000,
            "order_by": "RR_app_received DESC",
            "scope": (
                "Syracuse Rental Registry — rental-property registrations "
                "(native WGS84 Latitude/Longitude 500/500, no ADR 0004 "
                "dependency; watermark RR_app_received is event-driven; "
                "renewals reappear as new applications per SBL; PII "
                "RR_contact_name/pc_owner dropped at the field map; frozen "
                "Permit_Requests and absent 311/deeds are NOT registered)"
            ),
            "field_map": SYRACUSE_SLA_FIELD_MAP,
        },
    },
}


def get_syracuse_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Syracuse feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in SYRACUSE_FEED_SPECS:
        available = ", ".join(sorted(SYRACUSE_FEED_SPECS))
        raise KeyError(
            f"'{SYRACUSE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = SYRACUSE_FEED_SPECS[feed_name]
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
    metro_bbox=SYRACUSE_METRO_BBOX,
    division_bboxes=SYRACUSE_DIVISION_BBOXES,
    submarkets=SYRACUSE_SUBMARKETS,
    divisions=SYRACUSE_DIVISIONS,
    contains=is_in_syracuse_metro,
)

__all__ = [
    "SYRACUSE_CITY_ID",
    "SYRACUSE_DIVISIONS",
    "SYRACUSE_DIVISION_BBOXES",
    "SYRACUSE_FEED_SPECS",
    "SYRACUSE_METRO_BBOX",
    "SYRACUSE_SLA_ENDPOINT",
    "SYRACUSE_SUBMARKETS",
    "REGISTRATION",
    "get_syracuse_dataset",
    "is_in_syracuse_metro",
]
