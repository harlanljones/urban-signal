PERMITS_FIELD_MAP = {
    "job_id": ["Permit_Number", "OBJECTID"],
    "issuance_date": ["Date_Issued"],
    "filing_date": ["Date_Entered"],
    "status": ["Permit_Status"],
    # Permit_Name reads "Residential Building Permit", "Electrical Permit".
    "job_type": ["Permit_Name", "Permit_Type"],
    "address_street": ["Address_1"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT = "Topeka, KS"

DROPPED_PII_COLUMNS = ()

"""Topeka, KS spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Topeka
(Shawnee County, KS).

Topeka's PERMITS come from the CityworksViews hosted service
``BuildingPermits/MapServer/0`` (Commercial Building Permit) on the City of
Topeka's ArcGIS server (``maps.topeka.gov``). The 2026-08-30 probe left 311,
SLA and DEEDS at Tier 3: it found 311 only as a Cityworks UI, business
licensing is handled by the Shawnee County clerks, and Kansas is a statutory
non-disclosure state (K.S.A. 79-1437e) — Real Estate Sales Validation
Questionnaires are confidential, so no deed-sales feed exists. The SLA and
311 notes below record what has registered since.

Live-probe caveats that define this leaf (2026-08-30, US-426):

* PERMITS is the ``Commercial Building Permit`` layer at
  ``CityworksViews/BuildingPermits/MapServer/0`` (4,180 rows live). A
  companion ``Residential Building Permit`` layer (MapServer/1, 7,052 rows)
  is NOT registered separately (ADR-0007) — the commercial layer is the
  primary permit stream.
* Native point geometry (``outSR=4326`` lifts to WGS84), so
  ``needs_geocode=False``.
* The layer renamed its columns since (2026-10-02: 816 rows, issued
  2024-03-28 to 2026-09-04). ``Date_Issued`` is the watermark and
  ``Date_Entered`` the filing date, both text written ``9/4/2026``, so the
  poll names the days since its watermark (``text_date_window``).
  ``Permit_Number`` is the permit; a permit spanning several parcels has a
  row per parcel (57 such rows), and the id keeps one. ``Permit_Name``
  ("Commercial Electrical", "Commercial Building New") is the work class,
  ``Permit_Status`` the status and ``Address_1`` the street address.
* No neighborhood/district column exists on the layer, so no ``borough``
  field-map candidate is declared: division resolution comes from coordinates
  at ingest.

SLA (2026-09-30): the USDA SNAP retailer slice inside the metro box, which
stands in for the licence register the metro lacks. The corpus builds it
with the shared ``snap_sla_spec``; the feed mirror below does not carry it.

311 (2026-10-02): the same CityworksViews folder serves
``SCF_E311_Requests``, the City's 311 requests as Cityworks holds them, one
point per request since 2013: 8,825 in the year to 2026-10-02, about 24 a
day, with no day missing. The poll follows ``datetimeinit``, which follows
the view's object ids without exception over that year, keys events on
``requestid``, and names its columns, so each request's description,
details, address, initiator and Cityworks link stay on the server. The view
rejects ISO date strings, so its path, not the host, is listed in
``ANSI_DATE_LITERAL_HOSTS``: the permits view on the same host reads ISO
strings. The corpus registers this feed; the feed mirror below carries
PERMITS only.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

TOPEKA_CITY_ID: str = "topeka"
TOPEKA_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Topeka. Permissive enough to hold the downtown core (39.0483,
# -95.6780), the NOTO arts district (39.055, -95.679), the Central Topeka
# corridor (39.04, -95.69), the East Topeka / Kansas Avenue belt (39.05,
# -95.62), the West Topeka / Wanamaker corridor (39.04, -95.76), and the
# South Topeka / Gage Park area (39.00, -95.70) — while excluding Auburn
# (38.91, -95.82), Silver Lake (39.10, -95.86), and rural Shawnee County.
TOPEKA_METRO_BBOX: dict[str, float] = {
    "min_lat": 38.96,
    "max_lat": 39.12,
    "min_lng": -95.82,
    "max_lng": -95.58,
}

TOPEKA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 39.035,
        "max_lat": 39.070,
        "min_lng": -95.690,
        "max_lng": -95.660,
    },
    "CENTRAL": {
        "min_lat": 39.020,
        "max_lat": 39.080,
        "min_lng": -95.720,
        "max_lng": -95.690,
    },
    "EAST_TOPEKA": {
        "min_lat": 39.010,
        "max_lat": 39.100,
        "min_lng": -95.640,
        "max_lng": -95.580,
    },
    "WEST_TOPEKA": {
        "min_lat": 39.000,
        "max_lat": 39.090,
        "min_lng": -95.800,
        "max_lng": -95.720,
    },
    "SOUTH_TOPEKA": {
        "min_lat": 38.960,
        "max_lat": 39.020,
        "min_lng": -95.770,
        "max_lng": -95.690,
    },
}


def is_in_topeka_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Topeka metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        TOPEKA_METRO_BBOX["min_lat"] <= lat <= TOPEKA_METRO_BBOX["max_lat"]
        and TOPEKA_METRO_BBOX["min_lng"] <= lng <= TOPEKA_METRO_BBOX["max_lng"]
    )


is_in_greater_topeka_metro = is_in_topeka_metro


TOPEKA_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (2)
    # =======================================================================
    "Downtown Topeka": SubmarketMeta(
        name="Downtown Topeka",
        borough="DOWNTOWN",
        lat=39.0483,
        lng=-95.6780,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.82,
        capex=7200000.0,
        permit_vel=32.0,
        shift_ratio=1.44,
        sla=60.0,
        description="Downtown Topeka civic core with the Capitol, the Evergy Plaza, and the Kansas Avenue commercial corridor's steady mixed-use and office permitting.",
        city_id="topeka",
    ),
    "NOTO Arts District": SubmarketMeta(
        name="NOTO Arts District",
        borough="DOWNTOWN",
        lat=39.0550,
        lng=-95.6790,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.80,
        capex=5800000.0,
        permit_vel=28.0,
        shift_ratio=1.42,
        sla=58.0,
        description="North Topeka Arts District with gallery and studio conversions, adaptive-reuse, and the Redbud and First Friday pedestrian traffic.",
        city_id="topeka",
    ),
    # =======================================================================
    # CENTRAL (2)
    # =======================================================================
    "Central Topeka": SubmarketMeta(
        name="Central Topeka",
        borough="CENTRAL",
        lat=39.0400,
        lng=-95.7000,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=56.0,
        description="Central Topeka corridor along 10th and 6th Avenues with older commercial stock, the Washburn University adjacency, and steady commercial renovation.",
        city_id="topeka",
    ),
    "Chesney Park": SubmarketMeta(
        name="Chesney Park",
        borough="CENTRAL",
        lat=39.0250,
        lng=-95.6990,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.78,
        capex=5400000.0,
        permit_vel=26.0,
        shift_ratio=1.40,
        sla=54.0,
        description="Established central residential neighborhood with pre-war housing stock, the Gage Park adjacency, and steady renovation permits.",
        city_id="topeka",
    ),
    # =======================================================================
    # EAST_TOPEKA (2)
    # =======================================================================
    "East Topeka": SubmarketMeta(
        name="East Topeka",
        borough="EAST_TOPEKA",
        lat=39.0500,
        lng=-95.6200,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.76,
        capex=5200000.0,
        permit_vel=26.0,
        shift_ratio=1.38,
        sla=52.0,
        description="East Topeka corridor along Kansas Avenue and 6th Street with older commercial and industrial permitting and the Forbes Field adjacency.",
        city_id="topeka",
    ),
    "Highland Park": SubmarketMeta(
        name="Highland Park",
        borough="EAST_TOPEKA",
        lat=39.0200,
        lng=-95.6100,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.74,
        capex=4800000.0,
        permit_vel=24.0,
        shift_ratio=1.36,
        sla=50.0,
        description="Highland Park neighborhood southeast of downtown with post-war single-family and small commercial permitting.",
        city_id="topeka",
    ),
    # =======================================================================
    # WEST_TOPEKA (2)
    # =======================================================================
    "West Topeka": SubmarketMeta(
        name="West Topeka",
        borough="WEST_TOPEKA",
        lat=39.0400,
        lng=-95.7600,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.82,
        capex=6800000.0,
        permit_vel=32.0,
        shift_ratio=1.44,
        sla=58.0,
        description="West Topeka growth corridor along Wanamaker Road with big-box retail, the West Ridge Mall, and strong commercial tenant-improvement volume.",
        city_id="topeka",
    ),
    "Huntoon / West 6th": SubmarketMeta(
        name="Huntoon / West 6th",
        borough="WEST_TOPEKA",
        lat=39.0300,
        lng=-95.7800,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.78,
        capex=5800000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=54.0,
        description="Huntoon and West 6th corridor with automotive and service commercial, new subdivisions, and residential infill.",
        city_id="topeka",
    ),
    # =======================================================================
    # SOUTH_TOPEKA (1)
    # =======================================================================
    "South Topeka": SubmarketMeta(
        name="South Topeka",
        borough="SOUTH_TOPEKA",
        lat=38.9900,
        lng=-95.7100,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=26.0,
        shift_ratio=1.38,
        sla=52.0,
        description="South Topeka residential belt with subdivision expansion, the Topeka High adjacency, and steady single-family permitting.",
        city_id="topeka",
    ),
}


TOPEKA_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=39.0483,
        center_lng=-95.6780,
        zoom=14.0,
        bbox=TOPEKA_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in TOPEKA_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="topeka",
    ),
    "CENTRAL": BoroughMeta(
        name="CENTRAL",
        center_lat=39.0350,
        center_lng=-95.7000,
        zoom=14.0,
        bbox=TOPEKA_DIVISION_BBOXES["CENTRAL"],
        submarkets=[k for k, v in TOPEKA_SUBMARKETS.items() if v.borough == "CENTRAL"],
        city_id="topeka",
    ),
    "EAST_TOPEKA": BoroughMeta(
        name="EAST_TOPEKA",
        center_lat=39.0400,
        center_lng=-95.6200,
        zoom=13.5,
        bbox=TOPEKA_DIVISION_BBOXES["EAST_TOPEKA"],
        submarkets=[k for k, v in TOPEKA_SUBMARKETS.items() if v.borough == "EAST_TOPEKA"],
        city_id="topeka",
    ),
    "WEST_TOPEKA": BoroughMeta(
        name="WEST_TOPEKA",
        center_lat=39.0350,
        center_lng=-95.7600,
        zoom=13.5,
        bbox=TOPEKA_DIVISION_BBOXES["WEST_TOPEKA"],
        submarkets=[k for k, v in TOPEKA_SUBMARKETS.items() if v.borough == "WEST_TOPEKA"],
        city_id="topeka",
    ),
    "SOUTH_TOPEKA": BoroughMeta(
        name="SOUTH_TOPEKA",
        center_lat=38.9900,
        center_lng=-95.7200,
        zoom=13.5,
        bbox=TOPEKA_DIVISION_BBOXES["SOUTH_TOPEKA"],
        submarkets=[k for k, v in TOPEKA_SUBMARKETS.items() if v.borough == "SOUTH_TOPEKA"],
        city_id="topeka",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-30 (US-426). Do not register the residential building-permit
# layer (MapServer/1, 7,052 rows — ADR-0007 one-endpoint-per-feedtype) or any
# Shawnee County deed feed (K.S.A. 79-1437e non-disclosure). 311 reads the
# CityworksViews request view, which the corpus registers.
# ---------------------------------------------------------------------------
TOPEKA_PERMITS_ENDPOINT = (
    "https://maps.topeka.gov/arcgis/rest/services/CityworksViews/"
    "BuildingPermits/MapServer/0"
)

TOPEKA_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": TOPEKA_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Date_Issued",
        "id_keys": ["Permit_Number", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            # Date_Issued is text ("9/4/2026"): sorted, it reads as text.
            "watermark_type": "text",
            "watermark_format": "%m/%d/%Y",
            "order_by": "OBJECTID DESC",
            "select": (
                "OBJECTID,Permit_Number,Date_Issued,Date_Entered,Permit_Name,"
                "Permit_Type,Permit_Status,Address_1"
            ),
            "scope": (
                "Commercial Building Permit (MapServer/0, 4,180 rows; "
                "native point geometry; Date_Issued watermark; companion "
                "Residential Building Permit layer MapServer/1 with 7,052 "
                "rows not registered — ADR-0007)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
}


def get_topeka_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Topeka feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in TOPEKA_FEED_SPECS:
        available = ", ".join(sorted(TOPEKA_FEED_SPECS))
        raise KeyError(
            f"'{TOPEKA_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = TOPEKA_FEED_SPECS[feed_name]
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
    metro_bbox=TOPEKA_METRO_BBOX,
    division_bboxes=TOPEKA_DIVISION_BBOXES,
    submarkets=TOPEKA_SUBMARKETS,
    divisions=TOPEKA_DIVISIONS,
    contains=is_in_topeka_metro,
)

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "REGISTRATION",
    "TOPEKA_CITY_ID",
    "TOPEKA_DIVISIONS",
    "TOPEKA_DIVISION_BBOXES",
    "TOPEKA_FEED_SPECS",
    "TOPEKA_GEOCODE_CONTEXT",
    "TOPEKA_METRO_BBOX",
    "TOPEKA_PERMITS_ENDPOINT",
    "TOPEKA_SUBMARKETS",
    "get_topeka_dataset",
    "is_in_greater_topeka_metro",
    "is_in_topeka_metro",
]