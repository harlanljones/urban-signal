PERMITS_FIELD_MAP = {
    "job_id": ["PermNo", "OBJECTID_1"],
    "issuance_date": ["Issued"],
    "filing_date": ["Applied"],
    "status": ["CurrStatus"],
    "job_type": ["PermType", "UseType"],
    "description": ["DescWork"],
    "address_street": ["FullAddress", "Address"],
    "city": ["CITY"],
    "zipcode": ["ZIP"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT = "Lincoln, NE"

DROPPED_PII_COLUMNS = ()

"""Lincoln, NE spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Lincoln
(Lancaster County, NE).

Lincoln is a ONE-FEED PARTIAL metro: PERMITS only, from the Lincoln Open Data
portal (``gis.lincoln.ne.gov``). The authoritative layer is the
``Residential_New_Construction_Permits`` MapServer layer 4 (Previous 3 Years)
on the city's public ArcGIS server. 311 / SLA / DEEDS stay Tier 3: Lincoln's
311 is form-based, the SLA is supplemented by the Nebraska SOS corporate
registry, and deeds are recorded through the Lancaster County Register of
Deeds with no public bulk sales feed (probe 2026-08-30).

Live-probe caveats that define this leaf (2026-08-30, US-426):

* PERMITS is ``Residential_New_Construction_Permits/MapServer/4`` (Previous
  3 Years - Residential Building Permits, 2,622 rows live). The layer is a
  rolling 3-year window so the watermark min(date) slides forward, but
  ``Issued`` (epoch ms) is a stable max-date watermark. The companion
  ``Commercial_New_Construction_Permits/MapServer/4`` (674 rows) is NOT
  registered as a separate endpoint (ADR-0007); the residential layer is the
  primary permit stream.
* Native point geometry (``outSR=4326`` lifts to WGS84), so
  ``needs_geocode=False``. Store SR is WKID 102704 (NAD83 Nebraska State
  Plane). ``X``/``Y`` attribute columns exist but are State Plane feet and
  never mapped.
* ``PermNo`` is the unique permit number; ``CurrStatus`` is the status;
  ``PermType`` / ``UseType`` split the work class; ``FullAddress`` is the
  preferred street address.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

LINCOLN_CITY_ID: str = "lincoln"
LINCOLN_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Lincoln. Permissive enough to hold the downtown core (40.8136,
# -96.7026), the University of Nebraska campus (40.820, -96.700), the South
# Lincoln / SouthPointe corridor (40.77, -96.68), the East Lincoln / 84th
# Street belt (40.82, -96.60), and the West Lincoln / Cornhusker Highway edge
# (40.84, -96.78) — while excluding Waverly (40.91, -96.53), Hickman
# (40.59, -96.63), and rural Lancaster County.
LINCOLN_METRO_BBOX: dict[str, float] = {
    "min_lat": 40.72,
    "max_lat": 40.90,
    "min_lng": -96.82,
    "max_lng": -96.58,
}

LINCOLN_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 40.798,
        "max_lat": 40.830,
        "min_lng": -96.720,
        "max_lng": -96.690,
    },
    "UNIVERSITY": {
        "min_lat": 40.803,
        "max_lat": 40.840,
        "min_lng": -96.710,
        "max_lng": -96.650,
    },
    "SOUTH_LINCOLN": {
        "min_lat": 40.720,
        "max_lat": 40.798,
        "min_lng": -96.750,
        "max_lng": -96.610,
    },
    "EAST_LINCOLN": {
        "min_lat": 40.760,
        "max_lat": 40.860,
        "min_lng": -96.660,
        "max_lng": -96.580,
    },
    "WEST_LINCOLN": {
        "min_lat": 40.780,
        "max_lat": 40.880,
        "min_lng": -96.820,
        "max_lng": -96.720,
    },
    "NORTH_LINCOLN": {
        "min_lat": 40.830,
        "max_lat": 40.900,
        "min_lng": -96.780,
        "max_lng": -96.660,
    },
}


def is_in_lincoln_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Lincoln metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        LINCOLN_METRO_BBOX["min_lat"] <= lat <= LINCOLN_METRO_BBOX["max_lat"]
        and LINCOLN_METRO_BBOX["min_lng"] <= lng <= LINCOLN_METRO_BBOX["max_lng"]
    )


is_in_greater_lincoln_metro = is_in_lincoln_metro


LINCOLN_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (2)
    # =======================================================================
    "Downtown Lincoln": SubmarketMeta(
        name="Downtown Lincoln",
        borough="DOWNTOWN",
        lat=40.8136,
        lng=-96.7026,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.84,
        capex=7800000.0,
        permit_vel=34.0,
        shift_ratio=1.46,
        sla=60.0,
        description="Downtown Lincoln civic and office core with the Capitol, the Railyard entertainment district, and active mixed-use and adaptive-reuse permitting.",
        city_id="lincoln",
    ),
    "Haymarket": SubmarketMeta(
        name="Haymarket",
        borough="DOWNTOWN",
        lat=40.8120,
        lng=-96.7080,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.82,
        capex=7200000.0,
        permit_vel=32.0,
        shift_ratio=1.44,
        sla=58.0,
        description="Historic Haymarket District with the Pinnacle Bank Arena adjacency, restaurant and retail build-outs, and strong commercial-to-residential conversion.",
        city_id="lincoln",
    ),
    # =======================================================================
    # UNIVERSITY (2)
    # =======================================================================
    "University of Nebraska": SubmarketMeta(
        name="University of Nebraska",
        borough="UNIVERSITY",
        lat=40.8200,
        lng=-96.7000,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.80,
        capex=6400000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=56.0,
        description="UNL campus corridor with University Place, student housing, institutional permitting, and the Innovation Campus redevelopment.",
        city_id="lincoln",
    ),
    "College View": SubmarketMeta(
        name="College View",
        borough="UNIVERSITY",
        lat=40.8100,
        lng=-96.6600,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=54.0,
        description="College View neighborhood east of the campus with student-oriented housing, small commercial, and steady renovation permits.",
        city_id="lincoln",
    ),
    # =======================================================================
    # SOUTH_LINCOLN (3)
    # =======================================================================
    "South Lincoln": SubmarketMeta(
        name="South Lincoln",
        borough="SOUTH_LINCOLN",
        lat=40.7800,
        lng=-96.6900,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.82,
        capex=6800000.0,
        permit_vel=32.0,
        shift_ratio=1.44,
        sla=58.0,
        description="South Lincoln residential corridor with SouthPointe Mall retail, master-planned subdivisions, and the city's strongest new-home permit volume.",
        city_id="lincoln",
    ),
    "South 48th Street": SubmarketMeta(
        name="South 48th Street",
        borough="SOUTH_LINCOLN",
        lat=40.7700,
        lng=-96.6990,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=6000000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=56.0,
        description="Major south-north commercial corridor with auto dealerships, strip retail, and steady commercial tenant-improvement permitting.",
        city_id="lincoln",
    ),
    "South 70th Street": SubmarketMeta(
        name="South 70th Street",
        borough="SOUTH_LINCOLN",
        lat=40.7600,
        lng=-96.6240,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.78,
        capex=5800000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=54.0,
        description="South 70th Street growth corridor with new subdivisions, big-box retail, and the Wilderness Hills development.",
        city_id="lincoln",
    ),
    # =======================================================================
    # EAST_LINCOLN (2)
    # =======================================================================
    "East Lincoln": SubmarketMeta(
        name="East Lincoln",
        borough="EAST_LINCOLN",
        lat=40.8200,
        lng=-96.6200,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=56.0,
        description="East Lincoln residential corridor along 84th and 70th Streets with new subdivisions, schools, and small-strip commercial.",
        city_id="lincoln",
    ),
    "Havelock": SubmarketMeta(
        name="Havelock",
        borough="EAST_LINCOLN",
        lat=40.8510,
        lng=-96.6300,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.76,
        capex=5200000.0,
        permit_vel=26.0,
        shift_ratio=1.38,
        sla=52.0,
        description="Historic Havelock neighborhood in northeast Lincoln with older housing stock, small commercial, and the Havelock Main Street district.",
        city_id="lincoln",
    ),
    # =======================================================================
    # WEST_LINCOLN (1)
    # =======================================================================
    "West Lincoln": SubmarketMeta(
        name="West Lincoln",
        borough="WEST_LINCOLN",
        lat=40.8400,
        lng=-96.7600,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=26.0,
        shift_ratio=1.38,
        sla=52.0,
        description="West Lincoln along Cornhusker Highway with industrial and warehouse permitting, auto-oriented commercial, and the airport adjacency.",
        city_id="lincoln",
    ),
    # =======================================================================
    # NORTH_LINCOLN (1)
    # =======================================================================
    "North Lincoln": SubmarketMeta(
        name="North Lincoln",
        borough="NORTH_LINCOLN",
        lat=40.8600,
        lng=-96.7100,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.74,
        capex=5000000.0,
        permit_vel=24.0,
        shift_ratio=1.36,
        sla=50.0,
        description="North Lincoln gateway corridor with the airpark, ag-industrial, and growing residential subdivision fringe.",
        city_id="lincoln",
    ),
}


LINCOLN_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=40.8136,
        center_lng=-96.7026,
        zoom=14.0,
        bbox=LINCOLN_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in LINCOLN_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="lincoln",
    ),
    "UNIVERSITY": BoroughMeta(
        name="UNIVERSITY",
        center_lat=40.8160,
        center_lng=-96.6850,
        zoom=14.0,
        bbox=LINCOLN_DIVISION_BBOXES["UNIVERSITY"],
        submarkets=[k for k, v in LINCOLN_SUBMARKETS.items() if v.borough == "UNIVERSITY"],
        city_id="lincoln",
    ),
    "SOUTH_LINCOLN": BoroughMeta(
        name="SOUTH_LINCOLN",
        center_lat=40.7700,
        center_lng=-96.6950,
        zoom=13.5,
        bbox=LINCOLN_DIVISION_BBOXES["SOUTH_LINCOLN"],
        submarkets=[k for k, v in LINCOLN_SUBMARKETS.items() if v.borough == "SOUTH_LINCOLN"],
        city_id="lincoln",
    ),
    "EAST_LINCOLN": BoroughMeta(
        name="EAST_LINCOLN",
        center_lat=40.8300,
        center_lng=-96.6200,
        zoom=13.5,
        bbox=LINCOLN_DIVISION_BBOXES["EAST_LINCOLN"],
        submarkets=[k for k, v in LINCOLN_SUBMARKETS.items() if v.borough == "EAST_LINCOLN"],
        city_id="lincoln",
    ),
    "WEST_LINCOLN": BoroughMeta(
        name="WEST_LINCOLN",
        center_lat=40.8400,
        center_lng=-96.7600,
        zoom=13.5,
        bbox=LINCOLN_DIVISION_BBOXES["WEST_LINCOLN"],
        submarkets=[k for k, v in LINCOLN_SUBMARKETS.items() if v.borough == "WEST_LINCOLN"],
        city_id="lincoln",
    ),
    "NORTH_LINCOLN": BoroughMeta(
        name="NORTH_LINCOLN",
        center_lat=40.8600,
        center_lng=-96.7200,
        zoom=13.5,
        bbox=LINCOLN_DIVISION_BBOXES["NORTH_LINCOLN"],
        submarkets=[k for k, v in LINCOLN_SUBMARKETS.items() if v.borough == "NORTH_LINCOLN"],
        city_id="lincoln",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-30 (US-426). Do not register the Lincoln 311 form-based
# interface, the Lincoln SOS or NE state-level feeds, or Lancaster County
# Register of Deeds (no bulk sales API).
# ---------------------------------------------------------------------------
LINCOLN_PERMITS_ENDPOINT = (
    "https://gis.lincoln.ne.gov/public/rest/services/Planning/"
    "Residential_New_Construction_Permits/MapServer/4"
)

LINCOLN_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": LINCOLN_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Issued",
        "id_keys": ["PermNo", "OBJECTID_1"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "OBJECTID_1",
            "max_record_count": 2000,
            "order_by": "Issued DESC",
            "scope": (
                "Residential_New_Construction_Permits MapServer/4 (Previous 3"
                " Years - Residential Building Permits, 2,622 rows; rolling"
                " 3-year window; native point geometry; Issued watermark;"
                " PermNo / CurrStatus / PermType+UseType / FullAddress;"
                " companion Commercial layer 674 rows not registered)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
}


def get_lincoln_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Lincoln feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in LINCOLN_FEED_SPECS:
        available = ", ".join(sorted(LINCOLN_FEED_SPECS))
        raise KeyError(
            f"'{LINCOLN_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = LINCOLN_FEED_SPECS[feed_name]
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
    metro_bbox=LINCOLN_METRO_BBOX,
    division_bboxes=LINCOLN_DIVISION_BBOXES,
    submarkets=LINCOLN_SUBMARKETS,
    divisions=LINCOLN_DIVISIONS,
    contains=is_in_lincoln_metro,
)

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "LINCOLN_CITY_ID",
    "LINCOLN_DIVISIONS",
    "LINCOLN_DIVISION_BBOXES",
    "LINCOLN_FEED_SPECS",
    "LINCOLN_GEOCODE_CONTEXT",
    "LINCOLN_METRO_BBOX",
    "LINCOLN_PERMITS_ENDPOINT",
    "LINCOLN_SUBMARKETS",
    "PERMITS_FIELD_MAP",
    "REGISTRATION",
    "get_lincoln_dataset",
    "is_in_greater_lincoln_metro",
    "is_in_lincoln_metro",
]