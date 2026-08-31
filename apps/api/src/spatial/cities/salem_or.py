PERMITS_FIELD_MAP = {
    "job_id": ["FOLDERNUMBER"],
    "issuance_date": ["ISSUEDDATE"],
    "filing_date": ["CREATEDDATE"],
    "status": ["STATUS"],
    "job_type": ["SUBDESCRIPTION", "MAPDESCRIPTION"],
    "address_street": ["PROPERTYADDRESS"],
    "borough": ["NEIGHBORHOOD"],
}

SLA_FIELD_MAP = {
    "license_id": ["FOLDERNUMBER"],
    "dba": ["COMPLEXNAME"],
    "premises_name": ["COMPLEXNAME"],
    "license_type": ["SUBTYPE", "SUBDESC"],
    "status": ["STATUSDESC"],
    "effective_date": ["INDATE"],
    "expiration_date": ["EXPIRYDATE"],
    "address_street": ["FOLDERNAME"],
    "borough": ["NEIGHBORHOOD"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT = "Salem, OR"

DROPPED_PII_COLUMNS = (
    "OWNER",
    "ISSUEUSER",
    "GlobalID",
)

"""Salem, OR spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Salem
(Marion County, OR).

Salem is a TWO-FEED PARTIAL metro like Greenville/Tucson: PERMITS (``Structure_Permits``
at ``services.arcgis.com/kIA6yS9KDGqZL7U3/arcgis/rest/services/Structure_Permits/
FeatureServer/0``, Tier 1, ~802 rows, native WGS84 point geometry, 100% geometry
coverage, ``ISSUEDDATE`` watermark, rolling ~1 year window) and SLA (``Amanda
MultiFamily Licenses`` at the same org, Tier 2, ~1,111 rows, native WGS84 point
geometry, 100% geometry coverage, ``INDATE`` watermark). 311 (``311events``, 8
stale demo rows from 2017), deeds (no Marion County open bulk API), and Land_Use_Applications
(307 rows, no matching FeedType) are Tier 3 and stay unregistered.

Live-probe caveats that define this leaf (probed 2026-08-28, US-226;
ticket body pointed to ``salemoregon.opendata.arcgis.com`` which is 404 —
the real door is the City of Salem's ArcGIS Online org at
``salem.maps.arcgis.com``, org id ``kIA6yS9KDGqZL7U3``):

* PERMITS row count is **802 live** (rolling 1-year window: oldest ``ISSUEDDATE``
  = 2025-09-08, newest = 2026-08-27). ``ISSUEDDATE`` is the daily watermark.
  ``CREATEDDATE`` is also available as a filing-date candidate. No future-date
  sentinels (newest is 2026-08-27, yesterday at probe time). ISO date literals
  work in ``where`` clauses (not an ANSI-date host).
* SLA row count is **1,111 live**. ``INDATE`` (application in date) is the
  watermark; newest = 2026-08-26. ``EXPIRYDATE`` carries future-dated 2026-12-31
  values for all valid licenses — this is a normal annual expiry cycle, not a
  sentinel problem (the watermark is ``INDATE``, not ``EXPIRYDATE``). No
  future-date sentinel on the watermark column.
* Both layers have **100% native geometry coverage** (0 null-geometry rows
  live-probed), so ``needs_geocode=False``.
* Store SR is WKID 2913 (NAD83 Oregon State Plane South, feet). ``X``/``Y``
  (permits) and ``POINT_X``/``POINT_Y`` (licenses) are integer State Plane
  feet — never mapped as coordinates. Every query requests ``outSR=4326`` and
  ``ArcGISClient._flatten_feature`` lifts the returned WGS84 geometry to
  ``latitude``/``longitude``.
* ``NEIGHBORHOOD`` and ``WARD`` columns are present on both layers. ``NEIGHBORHOOD``
  maps to the ``borough`` field for source-neighborhood pass-through.
* SLA cadence: newest INDATE 2026-08-26, oldest INDATE 2025-09-03 (all 1,111
  rows). The layer is maintained (new INDATE rows appear regularly). Set
  ``expected_cadence_days=7`` with no alarm exemption — the cadence is
  typical for a permit-type feed.
* Land_Use_Applications (307 rows, companion layer) is not registered: no
  matching FeedType / producer, small size, and the permits feed already covers
  development activity. Marion County deeds — no open bulk API identified.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

SALEM_CITY_ID: str = "salem_or"
SALEM_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Salem + the urban-growth boundary. Permissive enough to hold the
# downtown core (44.9429, -123.0351), the Northgate NE belt (44.994, -122.994),
# West Salem across the Willamette (44.935, -123.065), the South Gateway /
# Sunnyslope south edge (44.876, -123.071), and the East Lancaster corridor
# (44.942, -122.967) — while excluding Keizer to the north (~45.00+) and
# rural Marion County.
SALEM_METRO_BBOX: dict[str, float] = {
    "min_lat": 44.84,
    "max_lat": 45.01,
    "min_lng": -123.13,
    "max_lng": -122.93,
}

# 6 Salem divisions. Hand-authored; borough resolution at ingest comes
# from coordinates via get_division_for_coordinate, so bboxes need only
# be sane and contain their own submarket centers.
SALEM_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 44.930,
        "max_lat": 44.955,
        "min_lng": -123.045,
        "max_lng": -123.028,
    },
    "NE_SALEM": {
        "min_lat": 44.955,
        "max_lat": 45.005,
        "min_lng": -123.045,
        "max_lng": -122.950,
    },
    "SE_MILL_CREEK": {
        "min_lat": 44.855,
        "max_lat": 44.920,
        "min_lng": -123.070,
        "max_lng": -122.970,
    },
    "WEST_SALEM": {
        "min_lat": 44.890,
        "max_lat": 44.960,
        "min_lng": -123.120,
        "max_lng": -123.045,
    },
    "SOUTH_SALEM": {
        "min_lat": 44.850,
        "max_lat": 44.930,
        "min_lng": -123.090,
        "max_lng": -123.010,
    },
    "EAST_LANCASTER": {
        "min_lat": 44.880,
        "max_lat": 44.965,
        "min_lng": -122.978,
        "max_lng": -122.930,
    },
}


def is_in_salem_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Salem metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        SALEM_METRO_BBOX["min_lat"] <= lat <= SALEM_METRO_BBOX["max_lat"]
        and SALEM_METRO_BBOX["min_lng"] <= lng <= SALEM_METRO_BBOX["max_lng"]
    )


is_in_greater_salem_metro = is_in_salem_metro


SALEM_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (1)
    # =======================================================================
    "Downtown Salem": SubmarketMeta(
        name="Downtown Salem",
        borough="DOWNTOWN",
        lat=44.9429,
        lng=-123.0351,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.84,
        capex=7200000.0,
        permit_vel=31.0,
        shift_ratio=1.48,
        sla=58.0,
        description="Liberty and Chemeketa core with the Riverfront Park, the Salem Convention Center, and the downtown retail and office corridor anchored by the Capitol Mall and Willamette University.",
        city_id="salem_or",
    ),
    # =======================================================================
    # NE_SALEM (2)
    # =======================================================================
    "Northgate": SubmarketMeta(
        name="Northgate",
        borough="NE_SALEM",
        lat=44.9944,
        lng=-122.9942,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.86,
        capex=6800000.0,
        permit_vel=33.0,
        shift_ratio=1.46,
        sla=54.0,
        description="Silverton Road and Northgate industrial-commercial corridor with warehousing, auto dealerships, and the city's heaviest commercial permit volume.",
        city_id="salem_or",
    ),
    "Grant-Highland": SubmarketMeta(
        name="Grant-Highland",
        borough="NE_SALEM",
        lat=44.9580,
        lng=-123.0350,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=6400000.0,
        permit_vel=28.0,
        shift_ratio=1.44,
        sla=52.0,
        description="Grant and Highland neighborhoods east of downtown with pre-war housing stock, farmland-residential transition, and the Fairview Cemetery area infill.",
        city_id="salem_or",
    ),
    # =======================================================================
    # SE_MILL_CREEK (2)
    # =======================================================================
    "Mill Creek": SubmarketMeta(
        name="Mill Creek",
        borough="SE_MILL_CREEK",
        lat=44.8885,
        lng=-123.0557,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.83,
        capex=5800000.0,
        permit_vel=26.0,
        shift_ratio=1.42,
        sla=50.0,
        description="Southeast Mill Creek corridor along Kuebler Boulevard with ranch-style subdivisions, solar-retrofit permits, and the Pringle Creek greenway.",
        city_id="salem_or",
    ),
    "Faye Wright": SubmarketMeta(
        name="Faye Wright",
        borough="SE_MILL_CREEK",
        lat=44.8960,
        lng=-123.0200,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.82,
        capex=5400000.0,
        permit_vel=24.0,
        shift_ratio=1.40,
        sla=48.0,
        description="Delta Highway and South Commercial corridor with apartment complexes, big-box retail, and the Faye Wright neighborhood's steady residential service permits.",
        city_id="salem_or",
    ),
    # =======================================================================
    # WEST_SALEM (1)
    # =======================================================================
    "West Salem": SubmarketMeta(
        name="West Salem",
        borough="WEST_SALEM",
        lat=44.9350,
        lng=-123.0650,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.87,
        capex=7000000.0,
        permit_vel=30.0,
        shift_ratio=1.47,
        sla=56.0,
        description="Edgewater Street and Wallace Marine Park neighborhood west of the Willamette with bridge-access downtown adjacency, river-view renovations, and steady commercial infill.",
        city_id="salem_or",
    ),
    # =======================================================================
    # SOUTH_SALEM (2)
    # =======================================================================
    "South Salem": SubmarketMeta(
        name="South Salem",
        borough="SOUTH_SALEM",
        lat=44.8760,
        lng=-123.0710,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=6200000.0,
        permit_vel=27.0,
        shift_ratio=1.43,
        sla=52.0,
        description="Liberty Road South and South Gateway corridor with orchard-retreat-to-subdivision infill, the Minto-Brown Island Park adjacency, and the city's south-edge residential growth.",
        city_id="salem_or",
    ),
    "Sunnyslope": SubmarketMeta(
        name="Sunnyslope",
        borough="SOUTH_SALEM",
        lat=44.9050,
        lng=-123.0550,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=5600000.0,
        permit_vel=25.0,
        shift_ratio=1.41,
        sla=50.0,
        description="Sunnyslope neighborhood south of Bush's Pasture Park with mid-century homes, ranch-style additions, and the Mission Street corridor's steady alterations.",
        city_id="salem_or",
    ),
    # =======================================================================
    # EAST_LANCASTER (1)
    # =======================================================================
    "East Lancaster": SubmarketMeta(
        name="East Lancaster",
        borough="EAST_LANCASTER",
        lat=44.9420,
        lng=-122.9670,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.84,
        capex=6000000.0,
        permit_vel=28.0,
        shift_ratio=1.44,
        sla=53.0,
        description="Lancaster Drive and I-5 commercial corridor with auto-oriented retail, motel-strip conversions, and the East Salem residential belt's steady apartment-license renewals.",
        city_id="salem_or",
    ),
}


SALEM_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=44.9429,
        center_lng=-123.0351,
        zoom=14.0,
        bbox=SALEM_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in SALEM_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="salem_or",
    ),
    "NE_SALEM": BoroughMeta(
        name="NE_SALEM",
        center_lat=44.9780,
        center_lng=-123.0020,
        zoom=13.0,
        bbox=SALEM_DIVISION_BBOXES["NE_SALEM"],
        submarkets=[k for k, v in SALEM_SUBMARKETS.items() if v.borough == "NE_SALEM"],
        city_id="salem_or",
    ),
    "SE_MILL_CREEK": BoroughMeta(
        name="SE_MILL_CREEK",
        center_lat=44.8900,
        center_lng=-123.0400,
        zoom=13.0,
        bbox=SALEM_DIVISION_BBOXES["SE_MILL_CREEK"],
        submarkets=[k for k, v in SALEM_SUBMARKETS.items() if v.borough == "SE_MILL_CREEK"],
        city_id="salem_or",
    ),
    "WEST_SALEM": BoroughMeta(
        name="WEST_SALEM",
        center_lat=44.9350,
        center_lng=-123.0650,
        zoom=13.5,
        bbox=SALEM_DIVISION_BBOXES["WEST_SALEM"],
        submarkets=[k for k, v in SALEM_SUBMARKETS.items() if v.borough == "WEST_SALEM"],
        city_id="salem_or",
    ),
    "SOUTH_SALEM": BoroughMeta(
        name="SOUTH_SALEM",
        center_lat=44.8900,
        center_lng=-123.0600,
        zoom=13.0,
        bbox=SALEM_DIVISION_BBOXES["SOUTH_SALEM"],
        submarkets=[k for k, v in SALEM_SUBMARKETS.items() if v.borough == "SOUTH_SALEM"],
        city_id="salem_or",
    ),
    "EAST_LANCASTER": BoroughMeta(
        name="EAST_LANCASTER",
        center_lat=44.9400,
        center_lng=-122.9500,
        zoom=13.0,
        bbox=SALEM_DIVISION_BBOXES["EAST_LANCASTER"],
        submarkets=[k for k, v in SALEM_SUBMARKETS.items() if v.borough == "EAST_LANCASTER"],
        city_id="salem_or",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Do not register the 311events stale demo, Land_Use_Applications
# (no matching FeedType), or Marion County deeds (no open bulk API).
# ---------------------------------------------------------------------------
SALEM_PERMITS_ENDPOINT = (
    "https://services.arcgis.com/kIA6yS9KDGqZL7U3/arcgis/rest/services/"
    "Structure_Permits/FeatureServer/0"
)

SALEM_SLA_ENDPOINT = (
    "https://services.arcgis.com/kIA6yS9KDGqZL7U3/arcgis/rest/services/"
    "Amanda_MultiFamily_Licenses_Data/FeatureServer/0"
)

SALEM_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": SALEM_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ISSUEDDATE",
        "id_keys": ["FOLDERNUMBER"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "ISSUEDDATE DESC",
            "scope": (
                "Structure_Permits issued permits (FeatureServer, ~802 rows; "
                "rolling 1-year window so min(date) is not staleness; native "
                "outSR=4326 point geometry; store SR WKID 2913 OR State Plane "
                "South feet; X/Y integer State Plane attributes never mapped; "
                "NEIGHBORHOOD + WARD columns for borough resolution; 100% "
                "geometry coverage; no future-date sentinels; ISO date "
                "literals work)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": SALEM_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "INDATE",
        "id_keys": ["FOLDERNUMBER"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 7,
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "INDATE DESC",
            "scope": (
                "Amanda MultiFamily Licenses (FeatureServer, ~1,111 rows; "
                "multifamily rental licenses + short-term rentals; native "
                "outSR=4326 point geometry; store SR WKID 2913; POINT_X/POINT_Y "
                "integer State Plane attributes never mapped; INDATE watermark "
                "(newest 2026-08-26); EXPIRYDATE 2026-12-31 future-dated expiry "
                "is normal annual cycle, not a sentinel — watermark is INDATE; "
                "NEIGHBORHOOD + WARD columns; 100% geometry coverage)"
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_salem_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Salem feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in SALEM_FEED_SPECS:
        available = ", ".join(sorted(SALEM_FEED_SPECS))
        raise KeyError(
            f"'{SALEM_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = SALEM_FEED_SPECS[feed_name]
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
    metro_bbox=SALEM_METRO_BBOX,
    division_bboxes=SALEM_DIVISION_BBOXES,
    submarkets=SALEM_SUBMARKETS,
    divisions=SALEM_DIVISIONS,
    contains=is_in_salem_metro,
)

# US-175 canonical-name aliases: the registry aggregator scans one predictable
# name per module (``<BASENAME>_METRO_BBOX`` etc.), so ``salem_or`` must export
# ``SALEM_OR_*`` alongside the ``SALEM_*`` spellings used above.
SALEM_OR_METRO_BBOX = SALEM_METRO_BBOX
SALEM_OR_DIVISION_BBOXES = SALEM_DIVISION_BBOXES
SALEM_OR_SUBMARKETS = SALEM_SUBMARKETS
SALEM_OR_DIVISIONS = SALEM_DIVISIONS

__all__ = [
    "REGISTRATION",
    "SALEM_CITY_ID",
    "SALEM_DIVISIONS",
    "SALEM_DIVISION_BBOXES",
    "SALEM_FEED_SPECS",
    "SALEM_GEOCODE_CONTEXT",
    "SALEM_METRO_BBOX",
    "SALEM_PERMITS_ENDPOINT",
    "SALEM_SLA_ENDPOINT",
    "SALEM_SUBMARKETS",
    "get_salem_dataset",
    "is_in_greater_salem_metro",
    "is_in_salem_metro",
]