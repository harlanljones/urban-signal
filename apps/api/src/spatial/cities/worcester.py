"""Worcester, MA spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Worcester
(Worcester County, central MA — the "Heart of the Commonwealth").

Worcester is a TWO-FEED PARTIAL metro on the city's ArcGIS Hub
(``opendata.worcesterma.gov``, AGOL org
``services1.arcgis.com/j8dqo2DJE7mVUBU1``): PERMITS (Building Permits) and
SLA (Food Establishment Licenses). Both are **non-spatial Tables** (address-
only) with **text M/D/YYYY date columns** (no zero-padding). COMPLAINTS_311
and DEEDS are absent from the Hub (no open extract) and stay unregistered.

Live-probe caveats that define this leaf (probed live 2026-08-30, US-419):

* Both layers are ``type: Table`` (no geometry) — ``needs_geocode=True`` with
  ``geocode_context="Worcester, MA"``, and there are NO native lat/lng columns.
* PERMITS watermark ``Permit_License_Issued_Date`` and SLA watermark
  ``Issued_Date`` are TEXT ``M/D/YYYY`` (no zero-padding, e.g. "8/9/2026").
  The city portal itself documents "Date fields ... sort as text". Text
  ``ORDER BY DESC`` LIES across month/day boundaries ("8/9/2026" sorts above
  "8/19/2026" and "12/31/2025"), so ADR-0005 typed comparison is mandatory
  (``watermark_type="text"``, ``watermark_format="%m/%d/%Y"`` — Rochester
  precedent).
* ``ObjectId`` is NON-MONOTONIC vs date: the newest 8/2026 rows carry ObjectId
  2–315 while 2015 rows carry 52725+. ``order_by`` MUST be the text watermark
  column, never ObjectId (else the default OID sort reads the 2015 tail first).
* TRUE calendar-newest at the probe (parsed, not lexical): permits
  ``Permit_License_Issued_Date`` = 8/21/2026 (2,896 rows in 2026), SLA
  ``Issued_Date`` = 8/21/2026 (430 rows in 2026). Both event-driven with
  near-daily distinct dates through 8/21 and a ~9-day publishing lag at the
  2026-08-30 probe → ``expected_cadence_days=14``.
* PERMITS has NO cost column and NO lat/lng; ``Record_Type`` is constant
  "Building Permit" and the newest rows carry ``Permit_For="N/A"``.
* SLA has NO business-name column — ``dba``/``premises_name`` stay unmapped.
* Richer sibling exists but is out of scope for this ticket:
  ``Business_Certificates_1963_to_Present/FeatureServer/0`` carries
  ``Business_Name`` + ``File_Date`` (zero-padded "08/27/2026", newest
  08/27/2026) and could back a general-business-license SLA feed later. The
  ticket pins SLA to ``Food_Establishment_Licenses``.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

WORCESTER_CITY_ID: str = "worcester"

# City of Worcester. Permissive enough to hold the downtown core (42.2626,
# -71.8023), the Quinsigamond Village lakeside edge (42.24), Greendale and
# the Indian Lake / Burncoat north edge (42.29), Tatnuck west of Route 122
# (-71.84), and the Shrewsbury line east of the lake (-71.78).
WORCESTER_METRO_BBOX: dict[str, float] = {
    "min_lat": 42.22,
    "max_lat": 42.31,
    "min_lng": -71.90,
    "max_lng": -71.76,
}

# 6 Worcester divisions. Hand-authored; borough resolution at ingest comes
# from coordinates via get_division_for_coordinate, so bboxes need only be
# sane and contain their own submarket centers.
WORCESTER_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_CORE": {
        "min_lat": 42.250,
        "max_lat": 42.270,
        "min_lng": -71.812,
        "max_lng": -71.792,
    },
    "EAST_SIDE": {
        "min_lat": 42.260,
        "max_lat": 42.276,
        "min_lng": -71.794,
        "max_lng": -71.778,
    },
    "SOUTH_SIDE": {
        "min_lat": 42.244,
        "max_lat": 42.256,
        "min_lng": -71.832,
        "max_lng": -71.802,
    },
    "QUINSIGAMOND": {
        "min_lat": 42.234,
        "max_lat": 42.248,
        "min_lng": -71.788,
        "max_lng": -71.768,
    },
    "WEST_SIDE": {
        "min_lat": 42.258,
        "max_lat": 42.286,
        "min_lng": -71.862,
        "max_lng": -71.830,
    },
    "NORTH_SIDE": {
        "min_lat": 42.280,
        "max_lat": 42.300,
        "min_lng": -71.826,
        "max_lng": -71.792,
    },
}

def is_in_worcester_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Worcester city bounds."""
    if lat is None or lng is None:
        return False
    return (
        WORCESTER_METRO_BBOX["min_lat"] <= lat <= WORCESTER_METRO_BBOX["max_lat"]
        and WORCESTER_METRO_BBOX["min_lng"] <= lng <= WORCESTER_METRO_BBOX["max_lng"]
    )

is_in_greater_worcester_metro = is_in_worcester_metro

WORCESTER_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CORE (2)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN_CORE",
        lat=42.2626,
        lng=-71.8023,
        zoom=15.0,
        pitch=55.0,
        base_lims=0.80,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.44,
        sla=55.0,
        description="Civic and office core around Worcester Common and the DCU-tethered Main Street spine with conversion-condo activity and the city's densest commercial pipeline.",
        city_id="worcester",
    ),
    "Canal District": SubmarketMeta(
        name="Canal District",
        borough="DOWNTOWN_CORE",
        lat=42.2570,
        lng=-71.7990,
        zoom=15.0,
        pitch=52.0,
        base_lims=0.83,
        capex=5800000.0,
        permit_vel=28.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The Blackstone Canal-era warehouse district around Kelley Square and the PawSox ballpark with loft conversions, restaurant rows, and the city's highest-energy storefront renewal.",
        city_id="worcester",
    ),
    # =======================================================================
    # EAST_SIDE (2)
    # =======================================================================
    "Shrewsbury Street": SubmarketMeta(
        name="Shrewsbury Street",
        borough="EAST_SIDE",
        lat=42.2689,
        lng=-71.7890,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=6200000.0,
        permit_vel=26.0,
        shift_ratio=1.50,
        sla=57.0,
        description="Shrewsbury Street's Restaurant Row and the Union Station edge with triple-decker conversions, Belmont Hill spillover, and the metro's most restaurant-led licensing churn.",
        city_id="worcester",
    ),
    "Grafton Hill": SubmarketMeta(
        name="Grafton Hill",
        borough="EAST_SIDE",
        lat=42.2660,
        lng=-71.7870,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.79,
        capex=4700000.0,
        permit_vel=22.0,
        shift_ratio=1.40,
        sla=49.0,
        description="Lake Quinsigamond-adjacent east side of Grafton Hill with historic single-family stock, Hamilton Street commercial, and steady duplex-to-condo reinvestment.",
        city_id="worcester",
    ),
    # =======================================================================
    # SOUTH_SIDE (2)
    # =======================================================================
    "Main South": SubmarketMeta(
        name="Main South",
        borough="SOUTH_SIDE",
        lat=42.2505,
        lng=-71.8090,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.74,
        capex=4200000.0,
        permit_vel=25.0,
        shift_ratio=1.43,
        sla=46.0,
        description="Clark University-anchored Main South corridor with triple-decker rental stock, the Main Street storefront row, and campus-driven renovation flow.",
        city_id="worcester",
    ),
    "Webster Square": SubmarketMeta(
        name="Webster Square",
        borough="SOUTH_SIDE",
        lat=42.2500,
        lng=-71.8260,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.72,
        capex=4000000.0,
        permit_vel=21.0,
        shift_ratio=1.38,
        sla=44.0,
        description="Webster Square's southwest retail plaza and the Mill Street / Route 122 edge with value-priced multi-family stock and block-by-block reinvestment.",
        city_id="worcester",
    ),
    # =======================================================================
    # QUINSIGAMOND (1)
    # =======================================================================
    "Quinsigamond Village": SubmarketMeta(
        name="Quinsigamond Village",
        borough="QUINSIGAMOND",
        lat=42.2400,
        lng=-71.7770,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.70,
        capex=3800000.0,
        permit_vel=19.0,
        shift_ratio=1.34,
        sla=42.0,
        description="The historic mill village at the Blackstone River / Lake Quinsigamond confluence with Quinsigamond Avenue commercial and early-stage waterfront reinvestment.",
        city_id="worcester",
    ),
    # =======================================================================
    # WEST_SIDE (1)
    # =======================================================================
    "Tatnuck": SubmarketMeta(
        name="Tatnuck",
        borough="WEST_SIDE",
        lat=42.2720,
        lng=-71.8400,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.84,
        capex=5600000.0,
        permit_vel=20.0,
        shift_ratio=1.42,
        sla=52.0,
        description="The West Side's Tatnuck Square around the Route 122 / Pleasant Street fork with 1920s bungalow stock, stable owner-occupancy, and the metro's most conservation-minded renovation flow.",
        city_id="worcester",
    ),
    # =======================================================================
    # NORTH_SIDE (1)
    # =======================================================================
    "Greendale": SubmarketMeta(
        name="Greendale",
        borough="NORTH_SIDE",
        lat=42.2900,
        lng=-71.8100,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.73,
        capex=4300000.0,
        permit_vel=18.0,
        shift_ratio=1.33,
        sla=45.0,
        description="The Greendale / Indian Lake north side with Salisbury Street and West Boylston Street commercial, Burncoat spillover, and value-priced family-housing reinvestment.",
        city_id="worcester",
    ),
}

WORCESTER_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=42.2600,
        center_lng=-71.8010,
        zoom=14.5,
        bbox=WORCESTER_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in WORCESTER_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="worcester",
    ),
    "EAST_SIDE": BoroughMeta(
        name="EAST_SIDE",
        center_lat=42.2675,
        center_lng=-71.7880,
        zoom=14.0,
        bbox=WORCESTER_DIVISION_BBOXES["EAST_SIDE"],
        submarkets=[k for k, v in WORCESTER_SUBMARKETS.items() if v.borough == "EAST_SIDE"],
        city_id="worcester",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=42.2500,
        center_lng=-71.8175,
        zoom=14.0,
        bbox=WORCESTER_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in WORCESTER_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="worcester",
    ),
    "QUINSIGAMOND": BoroughMeta(
        name="QUINSIGAMOND",
        center_lat=42.2400,
        center_lng=-71.7770,
        zoom=14.0,
        bbox=WORCESTER_DIVISION_BBOXES["QUINSIGAMOND"],
        submarkets=[k for k, v in WORCESTER_SUBMARKETS.items() if v.borough == "QUINSIGAMOND"],
        city_id="worcester",
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=42.2720,
        center_lng=-71.8400,
        zoom=14.0,
        bbox=WORCESTER_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in WORCESTER_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id="worcester",
    ),
    "NORTH_SIDE": BoroughMeta(
        name="NORTH_SIDE",
        center_lat=42.2900,
        center_lng=-71.8100,
        zoom=14.0,
        bbox=WORCESTER_DIVISION_BBOXES["NORTH_SIDE"],
        submarkets=[k for k, v in WORCESTER_SUBMARKETS.items() if v.borough == "NORTH_SIDE"],
        city_id="worcester",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed live 2026-08-30 (US-419). Register PERMITS and SLA only — both are
# non-spatial address-only Tables with text M/D/YYYY watermarks. Do not
# register the sibling Business_Certificates layer (out of scope) or any
# absent 311/deeds extract.
# ---------------------------------------------------------------------------
WORCESTER_PERMITS_ENDPOINT = (
    "https://services1.arcgis.com/j8dqo2DJE7mVUBU1/arcgis/rest/services/"
    "Building_Permits/FeatureServer/0"
)
WORCESTER_SLA_ENDPOINT = (
    "https://services1.arcgis.com/j8dqo2DJE7mVUBU1/arcgis/rest/services/"
    "Food_Establishment_Licenses/FeatureServer/0"
)

WORCESTER_PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["Record__", "ObjectId"],
    "issuance_date": ["Permit_License_Issued_Date"],
    "filing_date": ["Date_Submitted"],
    "job_type": ["Record_Type", "Permit_For"],
    "status": ["Record_Status"],
    "address_street": ["Address"],
    "bbl": ["MBL"],
}

WORCESTER_SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["Record__", "ObjectId"],
    "license_type": ["Type"],
    "effective_date": ["Issued_Date"],
    "expiration_date": ["Expiration_Date"],
    "address_street": ["Address"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": WORCESTER_PERMITS_FIELD_MAP,
    "sla": WORCESTER_SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Worcester, MA"

NEVER_CANDIDATE_COLUMNS: tuple[str, ...] = (
    "Occupancy_Type",
    "Contractor_Name",
    "Total_of_Fees",
)

WORCESTER_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": WORCESTER_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Permit_License_Issued_Date",
        "id_keys": ["Record__", "ObjectId"],
        "topic_key": "topic_permits",
        "interval_seconds": 600.0,
        "producer_key": "permits",
        "extra": {
            "needs_geocode": True,
            "geocode_context": GEOCODE_CONTEXT,
            "watermark_type": "text",
            "watermark_format": "%m/%d/%Y",
            "oid_field": "ObjectId",
            "max_record_count": 1000,
            "order_by": "Permit_License_Issued_Date DESC",
            "expected_cadence_days": 14,
            "non_spatial": True,
            "scope": (
                "Worcester Building Permits — non-spatial address-only Table "
                "(ADR-0004 geocode, context Worcester MA). TEXT M/D/YYYY "
                "watermark (ADR-0005): Permit_License_Issued_Date sorts "
                "lexically AND ObjectId is non-monotonic (newest 8/2026 rows "
                "carry ObjectId 2-315; 2015 rows carry 52725+), so order_by "
                "must be the text watermark column. No cost and no lat/lng "
                "columns; Record_Type is constant 'Building Permit'. Newest "
                "2026-08-21 (2,896 rows in 2026) at the 2026-08-30 probe."
            ),
            "field_map": WORCESTER_PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": WORCESTER_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Issued_Date",
        "id_keys": ["Record__", "ObjectId"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "needs_geocode": True,
            "geocode_context": GEOCODE_CONTEXT,
            "watermark_type": "text",
            "watermark_format": "%m/%d/%Y",
            "oid_field": "ObjectId",
            "max_record_count": 1000,
            "order_by": "Issued_Date DESC",
            "expected_cadence_days": 14,
            "non_spatial": True,
            "scope": (
                "Worcester Food Establishment Licenses — non-spatial "
                "address-only Table (ADR-0004 geocode, context Worcester MA). "
                "TEXT M/D/YYYY watermark (ADR-0005): Issued_Date sorts "
                "lexically AND ObjectId is non-monotonic, so order_by must be "
                "the text watermark column. NO business-name column — "
                "dba/premises_name stay unmapped (a richer sibling, "
                "Business_Certificates_1963_to_Present, carries Business_Name "
                "and is out of scope for this ticket). Newest 2026-08-21 "
                "(430 rows in 2026) at the 2026-08-30 probe."
            ),
            "field_map": WORCESTER_SLA_FIELD_MAP,
        },
    },
}

def get_worcester_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Worcester feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (311/deeds
    are absent from the Hub).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in WORCESTER_FEED_SPECS:
        available = ", ".join(sorted(WORCESTER_FEED_SPECS))
        raise KeyError(
            f"'{WORCESTER_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = WORCESTER_FEED_SPECS[feed_name]
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
    metro_bbox=WORCESTER_METRO_BBOX,
    division_bboxes=WORCESTER_DIVISION_BBOXES,
    submarkets=WORCESTER_SUBMARKETS,
    divisions=WORCESTER_DIVISIONS,
    contains=is_in_worcester_metro,
)

__all__ = [
    "GEOCODE_CONTEXT",
    "REGISTRATION",
    "WORCESTER_CITY_ID",
    "WORCESTER_DIVISIONS",
    "WORCESTER_DIVISION_BBOXES",
    "WORCESTER_FEED_SPECS",
    "WORCESTER_METRO_BBOX",
    "WORCESTER_PERMITS_ENDPOINT",
    "WORCESTER_SLA_ENDPOINT",
    "WORCESTER_SUBMARKETS",
    "get_worcester_dataset",
    "is_in_greater_worcester_metro",
    "is_in_worcester_metro",
]

