"""Anaheim / Orange County spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Anaheim, CA
and its Orange County fringe context (Garden Grove / Orange / Fullerton
edges ride the permissive bbox, Santa Ana / Los Angeles / Riverside are
rejected).

Anaheim is a TWO-FEED TIER-1 metro like Aurora: PERMITS
(``Accela_Building_Permits`` FeatureServer/0 on the city AGOL org) and SLA
(``ActiveBusinessLicenses`` FeatureServer/0). COMPLAINTS_311, DEEDS and
CRIME are unregistered (see the feed-rejection evidence below).

Live-probe evidence that defines this leaf (2026-08-28, US-249; city Hub
``anaheim.opendata.arcgis.com`` → city AGOL org
``services3.arcgis.com/hPs600I3X0RTaaaq``):

* PERMITS — 191,477 rows, point geometry, store SR **WKID 2230 (NAD83
  California zone 6, US survey feet)** with the host honoring ``outSR=4326``
  (live fixtures return degrees — server-side reprojection works). The layer
  has NO projected X/Y attribute columns, so no ``state_plane_*`` spec keys
  are declared; the geometry lift is the only coordinate path.
  ``permitissued`` (esri Date, epoch-ms → ISO on flatten): 14,113 nulls,
  0-fill ``applicationreceived``. Exactly ONE future-date sentinel
  (BLD2026-01741 @ 2026-09-13T00:00:00Z) — the spec carries
  ``where=permitissued <= CURRENT_TIMESTAMP`` so post-dated Accela issuances
  can never advance the watermark past live rows. Publishing lag ≈3 weeks
  (steady 400-570 permits/month through 2026-08-06, newest non-future
  watermark) → ``expected_cadence_days=21`` (NYC deeds style, alarm 2×N).
  ``jobvaluation`` is a string column ("25000", "-15536" — negative on ADU
  garage-conversion credits); the shared cost chain strips and floats it.
* SLA — the **Active snapshot** ``ActiveBusinessLicenses`` (15,263 rows =
  exactly the ``casestatus='Active'`` subset of the full-history layer,
  ``ingestion_mode='snapshot'``). 2,000-row live scan: 818 degree / 0 feet /
  1,182 null geometries — the lift is safe and null-geometry rows fall to
  the ADR-0004 geocode supplement on ``address`` (``needs_geocode=True``).
  Dates are ``esriFieldTypeDateOnly`` ("2026-06-02" strings); ISO string
  ``where`` comparisons verified live (no ANSI-date-literal host entry).
  Watermark ``applicationdate``: 0 nulls, 0 future sentinels, newest
  2026-06-02 (≈87-day publishing lag) → ``expected_cadence_days=90``.
  ``opendate`` carries year-3013/2204 sentinels and is NOT the effective-date
  candidate; ``expirationdate`` is mapped as-is and shares that sentinel
  family on a handful of rows.

Feed rejections (live evidence, same probe):

* COMPLAINTS_311 — no citizen-request surface exists (Hub search
  311/request/complaint: 0 matches). The only complaint-family feed is Code
  Enforcement Cases (171,255 rows, native 4326 points, fresh watermark
  2026-08-27) — code enforcement is a different family (Lynchburg TRAKiT
  discipline; Spartanburg rejects its CodeManagement the same way). Do not
  register.
* CRIME — ``Crime_Mapping_`` is a 7-day rolling TABLE (2026-08-11 →
  2026-08-18, 270 rows), ``geometryType: None``, intersection-only
  ``Location`` ("MAGNOLIA AV // CRIS AV"). Rolling views are not registered
  (Aurora L156/L157 precedent); the ADR-0004 address path would geocode
  intersections lossily. Do not register.
* SLA full history — ``Business_Licenses`` (82,636 rows) declares SR 4326
  while storing WKID 2230 state-plane feet and IGNORES ``outSR`` (x≈6.1e6 /
  y≈2.26e6 returned with outSR=4326; values match the permits layer's 2230
  extent). Live sample 200 @ offset 40000: 148 feet / 52 null / 0 degrees.
  ``ArcGISClient._flatten_feature`` lifts geometry x/y unconditionally and
  the SLA producer has no projected-coordinate guard (the permits producer
  does), so feet would emit as latitude/longitude on the wire. Mixed-CRS
  trap: not registered, not listed as a companion endpoint.
* DEEDS — Orange County publishes no bulk recorded-document/sales feed
  (AGOL/Hub searches: 0 datasets; the OC Clerk-Recorder is a search portal).
  Partial (permits + sla) is the honest shape.
"""


from src.producers.field_maps_anaheim import (
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

ANAHEIM_CITY_ID: str = "anaheim"
ANAHEIM_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# NAD83 California zone 6 state plane, US survey feet — native store SR of
# both probed layers (WKID 2230; permits extent 6.02e6..6.1e6 x
# 2.23e6..2.26e6 ft). Documentation constant only: neither spec declares
# state_plane_* keys because neither layer publishes projected X/Y
# *attribute* columns — coordinates ride the outSR=4326 geometry lift
# (honored by the permits and Active-license hosts) or the geocode
# supplement.
ANAHEIM_STATE_PLANE_CRS: str = "EPSG:2230"
ANAHEIM_STATE_PLANE_UNITS: str = "ftUS"

# City of Anaheim plus Orange County fringe context. Permissive enough to
# hold Downtown (33.835), the Resort District (33.812), Platinum Triangle
# (-117.884), Anaheim Canyon (-117.864), West Anaheim (-117.97), and the
# Anaheim Hills east edge (-117.745) while rejecting downtown Los Angeles
# (-118.2437), downtown Santa Ana (33.7456), Long Beach (-118.19), and
# Riverside (-117.3962).
ANAHEIM_METRO_BBOX: dict[str, float] = {
    "min_lat": 33.75,
    "max_lat": 33.91,
    "min_lng": -118.01,
    "max_lng": -117.69,
}

# 6 Anaheim / Orange County divisions. Hand-authored; borough resolution at
# ingest comes from coordinates via get_division_for_coordinate, so bboxes
# need only be sane, mutually non-overlapping, and contain their own
# submarket centers.
ANAHEIM_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_ANAHEIM": {
        "min_lat": 33.825,
        "max_lat": 33.852,
        "min_lng": -117.935,
        "max_lng": -117.900,
    },
    "RESORT_DISTRICT": {
        "min_lat": 33.795,
        "max_lat": 33.825,
        "min_lng": -117.935,
        "max_lng": -117.900,
    },
    "PLATINUM_TRIANGLE": {
        "min_lat": 33.788,
        "max_lat": 33.825,
        "min_lng": -117.900,
        "max_lng": -117.865,
    },
    "ANAHEIM_CANYON": {
        "min_lat": 33.838,
        "max_lat": 33.870,
        "min_lng": -117.900,
        "max_lng": -117.845,
    },
    "WEST_ANAHEIM": {
        "min_lat": 33.795,
        "max_lat": 33.852,
        "min_lng": -118.010,
        "max_lng": -117.935,
    },
    "ANAHEIM_HILLS": {
        "min_lat": 33.750,
        "max_lat": 33.910,
        "min_lng": -117.845,
        "max_lng": -117.690,
    },
}


def is_in_anaheim_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Anaheim / county-fringe bounds."""
    if lat is None or lng is None:
        return False
    return (
        ANAHEIM_METRO_BBOX["min_lat"] <= lat <= ANAHEIM_METRO_BBOX["max_lat"]
        and ANAHEIM_METRO_BBOX["min_lng"] <= lng <= ANAHEIM_METRO_BBOX["max_lng"]
    )


is_in_greater_anaheim_metro = is_in_anaheim_metro


ANAHEIM_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_ANAHEIM (2)
    # =======================================================================
    "Downtown Anaheim": SubmarketMeta(
        name="Downtown Anaheim",
        borough="DOWNTOWN_ANAHEIM",
        lat=33.8355,
        lng=-117.9140,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=34.0,
        shift_ratio=1.42,
        sla=56.0,
        description=(
            "Center City Promenade mixed-use core with facade grants, "
            "adaptive reuse of the 1920s packers corridor, and steady "
            "tenant-improvement permitting."
        ),
        city_id="anaheim",
    ),
    "The Colony": SubmarketMeta(
        name="The Colony",
        borough="DOWNTOWN_ANAHEIM",
        lat=33.8398,
        lng=-117.9253,
        zoom=14.5,
        pitch=46.0,
        base_lims=0.74,
        capex=4600000.0,
        permit_vel=26.0,
        shift_ratio=1.34,
        sla=48.0,
        description=(
            "Historic 1910s-20s residential grid with Craftsman "
            "restoration-led permitting and Mills-Act-adjacent churn."
        ),
        city_id="anaheim",
    ),
    # =======================================================================
    # RESORT_DISTRICT (2)
    # =======================================================================
    "Disneyland Resort & Convention Center": SubmarketMeta(
        name="Disneyland Resort & Convention Center",
        borough="RESORT_DISTRICT",
        lat=33.8106,
        lng=-117.9194,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.92,
        capex=12500000.0,
        permit_vel=48.0,
        shift_ratio=1.62,
        sla=68.0,
        description=(
            "Theme-park, hotel, and convention anchor with the metro's "
            "densest entertainment-adjacent licensing and continuous "
            "capital expansion."
        ),
        city_id="anaheim",
    ),
    "Harbor Boulevard Hotel Belt": SubmarketMeta(
        name="Harbor Boulevard Hotel Belt",
        borough="RESORT_DISTRICT",
        lat=33.8005,
        lng=-117.9280,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.84,
        capex=7200000.0,
        permit_vel=36.0,
        shift_ratio=1.48,
        sla=60.0,
        description=(
            "South Harbor motel-to-hotel repositioning strip with "
            "Transient-Occupancy-driven renovations and walkable "
            "park-gateway demand."
        ),
        city_id="anaheim",
    ),
    # =======================================================================
    # PLATINUM_TRIANGLE (1)
    # =======================================================================
    "Honda Center & Angel Stadium": SubmarketMeta(
        name="Honda Center & Angel Stadium",
        borough="PLATINUM_TRIANGLE",
        lat=33.8040,
        lng=-117.8845,
        zoom=13.5,
        pitch=48.0,
        base_lims=0.88,
        capex=9800000.0,
        permit_vel=44.0,
        shift_ratio=1.55,
        sla=62.0,
        description=(
            "Platinum Triangle arena-stadium district with high-rise "
            "entitlements, ARTIC-adjacent office, and the metro's "
            "largest planned-growth pipeline."
        ),
        city_id="anaheim",
    ),
    # =======================================================================
    # WEST_ANAHEIM (2)
    # =======================================================================
    "West Anaheim Magnolia Belt": SubmarketMeta(
        name="West Anaheim Magnolia Belt",
        borough="WEST_ANAHEIM",
        lat=33.8290,
        lng=-117.9650,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.38,
        sla=52.0,
        description=(
            "Post-war tract housing along the Magnolia/ Brookhurst retail "
            "spine with renovation-led permitting and small-business "
            "licensing churn."
        ),
        city_id="anaheim",
    ),
    "Brookhurst Southwest": SubmarketMeta(
        name="Brookhurst Southwest",
        borough="WEST_ANAHEIM",
        lat=33.8060,
        lng=-117.9480,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.74,
        capex=5000000.0,
        permit_vel=28.0,
        shift_ratio=1.36,
        sla=50.0,
        description=(
            "Little Arabia commercial corridor and surrounding "
            "garden-apartment stock with restaurant licensing turnover "
            "and duplex infill."
        ),
        city_id="anaheim",
    ),
    # =======================================================================
    # ANAHEIM_CANYON (1)
    # =======================================================================
    "Anaheim Canyon Industrial": SubmarketMeta(
        name="Anaheim Canyon Industrial",
        borough="ANAHEIM_CANYON",
        lat=33.8480,
        lng=-117.8640,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.82,
        capex=7600000.0,
        permit_vel=38.0,
        shift_ratio=1.46,
        sla=54.0,
        description=(
            "Northeast industrial and food-manufacturing district along "
            "the 91 with warehouse conversions, TTM industrial "
            "condos, and steady TI permitting."
        ),
        city_id="anaheim",
    ),
    # =======================================================================
    # ANAHEIM_HILLS (2)
    # =======================================================================
    "Nohl Ranch Hills": SubmarketMeta(
        name="Nohl Ranch Hills",
        borough="ANAHEIM_HILLS",
        lat=33.8380,
        lng=-117.7970,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.84,
        capex=7000000.0,
        permit_vel=32.0,
        shift_ratio=1.40,
        sla=50.0,
        description=(
            "Master-planned hillside subdivisions around Nohl Ranch Road "
            "with pool/deck auxiliary permits and high-valuation "
            "remodel cadence."
        ),
        city_id="anaheim",
    ),
    "Weir Canyon East": SubmarketMeta(
        name="Weir Canyon East",
        borough="ANAHEIM_HILLS",
        lat=33.8500,
        lng=-117.7550,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.80,
        capex=6400000.0,
        permit_vel=28.0,
        shift_ratio=1.36,
        sla=46.0,
        description=(
            "Eastern hillside edge toward Weir and Gypsum canyons with "
            "newer single-family stock, solar permitting volume, and "
            "wildland-adjacent rebuild cycles."
        ),
        city_id="anaheim",
    ),
}


ANAHEIM_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_ANAHEIM": BoroughMeta(
        name="DOWNTOWN_ANAHEIM",
        center_lat=33.8385,
        center_lng=-117.9175,
        zoom=14.0,
        bbox=ANAHEIM_DIVISION_BBOXES["DOWNTOWN_ANAHEIM"],
        submarkets=[k for k, v in ANAHEIM_SUBMARKETS.items() if v.borough == "DOWNTOWN_ANAHEIM"],
        city_id="anaheim",
    ),
    "RESORT_DISTRICT": BoroughMeta(
        name="RESORT_DISTRICT",
        center_lat=33.8100,
        center_lng=-117.9175,
        zoom=13.5,
        bbox=ANAHEIM_DIVISION_BBOXES["RESORT_DISTRICT"],
        submarkets=[k for k, v in ANAHEIM_SUBMARKETS.items() if v.borough == "RESORT_DISTRICT"],
        city_id="anaheim",
    ),
    "PLATINUM_TRIANGLE": BoroughMeta(
        name="PLATINUM_TRIANGLE",
        center_lat=33.8050,
        center_lng=-117.8825,
        zoom=13.5,
        bbox=ANAHEIM_DIVISION_BBOXES["PLATINUM_TRIANGLE"],
        submarkets=[k for k, v in ANAHEIM_SUBMARKETS.items() if v.borough == "PLATINUM_TRIANGLE"],
        city_id="anaheim",
    ),
    "ANAHEIM_CANYON": BoroughMeta(
        name="ANAHEIM_CANYON",
        center_lat=33.8540,
        center_lng=-117.8725,
        zoom=12.5,
        bbox=ANAHEIM_DIVISION_BBOXES["ANAHEIM_CANYON"],
        submarkets=[k for k, v in ANAHEIM_SUBMARKETS.items() if v.borough == "ANAHEIM_CANYON"],
        city_id="anaheim",
    ),
    "WEST_ANAHEIM": BoroughMeta(
        name="WEST_ANAHEIM",
        center_lat=33.8230,
        center_lng=-117.9725,
        zoom=13.0,
        bbox=ANAHEIM_DIVISION_BBOXES["WEST_ANAHEIM"],
        submarkets=[k for k, v in ANAHEIM_SUBMARKETS.items() if v.borough == "WEST_ANAHEIM"],
        city_id="anaheim",
    ),
    "ANAHEIM_HILLS": BoroughMeta(
        name="ANAHEIM_HILLS",
        center_lat=33.8300,
        center_lng=-117.7800,
        zoom=12.5,
        bbox=ANAHEIM_DIVISION_BBOXES["ANAHEIM_HILLS"],
        submarkets=[k for k, v in ANAHEIM_SUBMARKETS.items() if v.borough == "ANAHEIM_HILLS"],
        city_id="anaheim",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28 (US-249). Do not register 311 (code-enforcement family
# only), crime (rolling table), full-history Business_Licenses (mislabeled-SR
# feet trap), or deeds (no OC bulk feed).
# ---------------------------------------------------------------------------
ANAHEIM_PERMITS_ENDPOINT = (
    "https://services3.arcgis.com/hPs600I3X0RTaaaq/arcgis/rest/services/"
    "Accela_Building_Permits/FeatureServer/0"
)
ANAHEIM_SLA_ENDPOINT = (
    "https://services3.arcgis.com/hPs600I3X0RTaaaq/arcgis/rest/services/"
    "ActiveBusinessLicenses/FeatureServer/0"
)

ANAHEIM_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": ANAHEIM_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "permitissued",
        "id_keys": ["casenumber", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 21,
            "needs_geocode": True,
            "geocode_context": ANAHEIM_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "permitissued DESC",
            # Post-dated Accela issuances must never advance the watermark
            # past live rows (BLD2026-01741 @ 2026-09-13 on the probe).
            "where": "permitissued <= CURRENT_TIMESTAMP",
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": ANAHEIM_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "applicationdate",
        "id_keys": ["casenumber", "objectid"],
        "topic_key": "topic_sla",
        "interval_seconds": 300.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 90,
            "needs_geocode": True,
            "geocode_context": ANAHEIM_GEOCODE_CONTEXT,
            "ingestion_mode": "snapshot",
            "oid_field": "objectid",
            "max_record_count": 10000,
            "order_by": "applicationdate DESC",
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_anaheim_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a (pending-spine) Anaheim feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in ANAHEIM_FEED_SPECS:
        available = ", ".join(sorted(ANAHEIM_FEED_SPECS))
        raise KeyError(
            f"'{ANAHEIM_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = ANAHEIM_FEED_SPECS[feed_name]
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
    metro_bbox=ANAHEIM_METRO_BBOX,
    division_bboxes=ANAHEIM_DIVISION_BBOXES,
    submarkets=ANAHEIM_SUBMARKETS,
    divisions=ANAHEIM_DIVISIONS,
    contains=is_in_anaheim_metro,
)

__all__ = [
    "ANAHEIM_CITY_ID",
    "ANAHEIM_DIVISIONS",
    "ANAHEIM_DIVISION_BBOXES",
    "ANAHEIM_FEED_SPECS",
    "ANAHEIM_GEOCODE_CONTEXT",
    "ANAHEIM_METRO_BBOX",
    "ANAHEIM_PERMITS_ENDPOINT",
    "ANAHEIM_SLA_ENDPOINT",
    "ANAHEIM_STATE_PLANE_CRS",
    "ANAHEIM_STATE_PLANE_UNITS",
    "ANAHEIM_SUBMARKETS",
    "REGISTRATION",
    "get_anaheim_dataset",
    "is_in_anaheim_metro",
]
