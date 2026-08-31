PERMITS_FIELD_MAP = {
    "job_id": ["PER_NUM", "PERMIT_NUMBER", "PID", "OBJECTID"],
    "issuance_date": ["PER_ISSUE_DATE", "PERMIT_ISSUE_DATE"],
    "filing_date": ["PER_ENT_DATE"],
    "status": ["PERMIT_STAT", "STATUS"],
    "job_type": [
        "PER_TYPE_DESC",
        "SCOPE_DESC",
        "PER_TYPE",
        "PERMIT_TYPE",
        "PERMIT_NAME",
    ],
    "address_street": ["STREET_FULL_NAME", "ADDRESS"],
}

SLA_FIELD_MAP = {
    "license_id": ["NAME", "ID", "OBJECTID"],
    "license_type": ["REGISTRATION_TYPE"],
    "premises_name": ["POW_NAME", "POW_COMPANY_NAME"],
    "dba": ["POW_NAME", "POW_COMPANY_NAME"],
    "effective_date": ["ISSUED_DATE"],
    "expiration_date": ["EXPIRATION_DATE"],
    "status": ["STATUS"],
    "latitude": ["LATITUDE"],
    "longitude": ["LONGITUDE"],
    "address_street": ["PROPERTY_ADDRESS"],
    "zipcode": ["PROPERTY_ZIP"],
    "borough": ["PROPERTY_CITY_STATE"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT = "Phoenix, AZ"

"""Phoenix / Maricopa County spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Phoenix, AZ.

Phoenix is a TWO-FEED PARTIAL metro like Honolulu/Austin: PERMITS
(``Public/Planning_Permit/MapServer/1`` plus ShapePHX ``_DL`` companion) and
SLA (ShapePHX Short Term Rentals). STR **is** the SLA registration — there is
no broader business-tax feed, and ``FeedType.STR`` is not used. 311 and DEEDS
are absent; ``get_phoenix_dataset`` raises for them.

Live-probe caveats that define this leaf (2026-08-27):

* Permits are native ArcGIS points (WKID 3857 → WGS84 via ``outSR=4326``).
  ``needs_geocode`` is false. Companion ``ShapePHXPermitsPoints_DL`` is weekly
  Issued-only; ``ADDRESS`` is null on every row. Do not register the frozen
  non-``_DL`` twin (newest ``PERMIT_ISSUE_DATE`` 2022-06-29).
* SLA is ShapePHX STR with native ``LATITUDE``/``LONGITUDE`` plus point
  geometry. ``PROPERTY_ADDRESS`` carries a trailing `` (Active)`` suffix.
  Weekly cadence (``expected_cadence_days: 7``).
* myPHX311 is a Dynamics 365 portal with no bulk REST. Liquor ``LIQUOR_RACMap``
  has no date column. Deeds have no queryable watermark.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

PHOENIX_CITY_ID: str = "phoenix"
PHOENIX_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Phoenix proper. Permissive enough to keep every live Planning_Permit
# / ShapePHX sample inside (downtown 33.4484, -112.0740; west 75th Ave
# ~-112.22; Ahwatukee south; North Gateway ~33.80; Desert Ridge east ~-111.93).
PHOENIX_METRO_BBOX: Dict[str, float] = {
    "min_lat": 33.28,
    "max_lat": 33.86,
    "min_lng": -112.36,
    "max_lng": -111.92,
}

PHOENIX_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_CENTRAL": {
        "min_lat": 33.42,
        "max_lat": 33.51,
        "min_lng": -112.13,
        "max_lng": -112.02,
    },
    "SOUTH_MOUNTAIN": {
        "min_lat": 33.29,
        "max_lat": 33.42,
        "min_lng": -112.18,
        "max_lng": -111.93,
    },
    "WEST_VILLAGES": {
        "min_lat": 33.36,
        "max_lat": 33.54,
        "min_lng": -112.36,
        "max_lng": -112.10,
    },
    "NORTH_CENTRAL": {
        "min_lat": 33.51,
        "max_lat": 33.64,
        "min_lng": -112.16,
        "max_lng": -111.99,
    },
    "NORTHEAST_PARADISE": {
        "min_lat": 33.48,
        "max_lat": 33.76,
        "min_lng": -112.02,
        "max_lng": -111.92,
    },
    "NORTHWEST_DEER_VALLEY": {
        "min_lat": 33.61,
        "max_lat": 33.86,
        "min_lng": -112.28,
        "max_lng": -112.00,
    },
}


def is_in_phoenix_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the City of Phoenix metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        PHOENIX_METRO_BBOX["min_lat"] <= lat <= PHOENIX_METRO_BBOX["max_lat"]
        and PHOENIX_METRO_BBOX["min_lng"] <= lng <= PHOENIX_METRO_BBOX["max_lng"]
    )


is_in_greater_phoenix_metro = is_in_phoenix_metro


PHOENIX_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CENTRAL (3)
    # =======================================================================
    "Downtown Phoenix": SubmarketMeta(
        name="Downtown Phoenix",
        borough="DOWNTOWN_CENTRAL",
        lat=33.4484,
        lng=-112.0740,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.91,
        capex=12500000.0,
        permit_vel=52.0,
        shift_ratio=1.62,
        sla=72.0,
        description="Washington/Central civic and sports core with office-to-residential conversions and the densest Planning & Development pipeline.",
        city_id="phoenix",
    ),
    "Midtown / Uptown": SubmarketMeta(
        name="Midtown / Uptown",
        borough="DOWNTOWN_CENTRAL",
        lat=33.4942,
        lng=-112.0740,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.88,
        capex=9800000.0,
        permit_vel=44.0,
        shift_ratio=1.54,
        sla=66.0,
        description="Central Avenue mid-rise corridor between McDowell and Indian School with mixed-use infill and renovation permits.",
        city_id="phoenix",
    ),
    "Encanto": SubmarketMeta(
        name="Encanto",
        borough="DOWNTOWN_CENTRAL",
        lat=33.4738,
        lng=-112.0990,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.84,
        capex=7600000.0,
        permit_vel=36.0,
        shift_ratio=1.46,
        sla=60.0,
        description="Historic bungalow grid around Encanto Park with renovation-led permitting and neighborhood conservation overlays.",
        city_id="phoenix",
    ),
    # =======================================================================
    # SOUTH_MOUNTAIN (3)
    # =======================================================================
    "South Mountain Village": SubmarketMeta(
        name="South Mountain Village",
        borough="SOUTH_MOUNTAIN",
        lat=33.4060,
        lng=-112.0730,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=32.0,
        shift_ratio=1.38,
        sla=52.0,
        description="South-central grid along Broadway and Central with industrial-adjacent infill and steady structural/MEP permitting.",
        city_id="phoenix",
    ),
    "Ahwatukee Foothills": SubmarketMeta(
        name="Ahwatukee Foothills",
        borough="SOUTH_MOUNTAIN",
        lat=33.3417,
        lng=-111.9833,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.82,
        capex=6800000.0,
        permit_vel=34.0,
        shift_ratio=1.42,
        sla=58.0,
        description="Master-planned south-Phoenix foothills community with solar OTC, residential additions, and constrained mountain-preserve edges.",
        city_id="phoenix",
    ),
    "Laveen": SubmarketMeta(
        name="Laveen",
        borough="SOUTH_MOUNTAIN",
        lat=33.3628,
        lng=-112.1690,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.74,
        capex=4900000.0,
        permit_vel=30.0,
        shift_ratio=1.36,
        sla=50.0,
        description="Southwest growth edge with new-construction tract permitting along Baseline and the Loop 202.",
        city_id="phoenix",
    ),
    # =======================================================================
    # WEST_VILLAGES (3)
    # =======================================================================
    "Maryvale": SubmarketMeta(
        name="Maryvale",
        borough="WEST_VILLAGES",
        lat=33.4917,
        lng=-112.1628,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.72,
        capex=4200000.0,
        permit_vel=38.0,
        shift_ratio=1.40,
        sla=54.0,
        description="Post-war west-side grid with high permit volume in solar, fire-sprinkler, and small-lot renovation work.",
        city_id="phoenix",
    ),
    "Alhambra": SubmarketMeta(
        name="Alhambra",
        borough="WEST_VILLAGES",
        lat=33.5095,
        lng=-112.1160,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.75,
        capex=4800000.0,
        permit_vel=33.0,
        shift_ratio=1.38,
        sla=53.0,
        description="Camelback west-of-Central corridor with commercial miscellaneous and residential alteration permits.",
        city_id="phoenix",
    ),
    "Estrella": SubmarketMeta(
        name="Estrella",
        borough="WEST_VILLAGES",
        lat=33.4045,
        lng=-112.2480,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.70,
        capex=3900000.0,
        permit_vel=28.0,
        shift_ratio=1.32,
        sla=46.0,
        description="Far-west village along the Estrella foothills with sparse new construction and industrial-edge permitting.",
        city_id="phoenix",
    ),
    # =======================================================================
    # NORTH_CENTRAL (3)
    # =======================================================================
    "Sunnyslope": SubmarketMeta(
        name="Sunnyslope",
        borough="NORTH_CENTRAL",
        lat=33.5678,
        lng=-112.0885,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.80,
        capex=6100000.0,
        permit_vel=36.0,
        shift_ratio=1.44,
        sla=58.0,
        description="North-central hillside grid with renovation-led permitting and ShapePHX Issued density around Dunlap.",
        city_id="phoenix",
    ),
    "North Mountain": SubmarketMeta(
        name="North Mountain",
        borough="NORTH_CENTRAL",
        lat=33.5800,
        lng=-112.0500,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=31.0,
        shift_ratio=1.40,
        sla=55.0,
        description="Preserve-adjacent north-central neighborhoods with residential additions and trailhead-constrained infill.",
        city_id="phoenix",
    ),
    "Moon Valley": SubmarketMeta(
        name="Moon Valley",
        borough="NORTH_CENTRAL",
        lat=33.6214,
        lng=-112.0769,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.83,
        capex=7200000.0,
        permit_vel=29.0,
        shift_ratio=1.48,
        sla=64.0,
        description="North-central estate lots with the densest ShapePHX short-term rental operating-permit cluster.",
        city_id="phoenix",
    ),
    # =======================================================================
    # NORTHEAST_PARADISE (3)
    # =======================================================================
    "Arcadia": SubmarketMeta(
        name="Arcadia",
        borough="NORTHEAST_PARADISE",
        lat=33.5040,
        lng=-111.9790,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.89,
        capex=11000000.0,
        permit_vel=40.0,
        shift_ratio=1.52,
        sla=68.0,
        description="Camelback-east citrus-lot estates with high-value renovation permits and strict lot-coverage overlays.",
        city_id="phoenix",
    ),
    "Paradise Valley Village": SubmarketMeta(
        name="Paradise Valley Village",
        borough="NORTHEAST_PARADISE",
        lat=33.5825,
        lng=-111.9778,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.86,
        capex=9200000.0,
        permit_vel=37.0,
        shift_ratio=1.50,
        sla=65.0,
        description="Tatum/Shea northeast village with mixed-use infill and professional-office permitting (not the Town of Paradise Valley).",
        city_id="phoenix",
    ),
    "Desert Ridge": SubmarketMeta(
        name="Desert Ridge",
        borough="NORTHEAST_PARADISE",
        lat=33.6760,
        lng=-111.9300,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.87,
        capex=10500000.0,
        permit_vel=42.0,
        shift_ratio=1.56,
        sla=67.0,
        description="Loop 101 / Tatum mixed-use node with hotel, retail, and multifamily permitting at the city's northeast edge.",
        city_id="phoenix",
    ),
    # =======================================================================
    # NORTHWEST_DEER_VALLEY (3)
    # =======================================================================
    "Deer Valley": SubmarketMeta(
        name="Deer Valley",
        borough="NORTHWEST_DEER_VALLEY",
        lat=33.6830,
        lng=-112.1150,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=6400000.0,
        permit_vel=39.0,
        shift_ratio=1.46,
        sla=59.0,
        description="I-17 / Loop 101 employment and airport-adjacent village with industrial and residential permit velocity.",
        city_id="phoenix",
    ),
    "Norterra": SubmarketMeta(
        name="Norterra",
        borough="NORTHWEST_DEER_VALLEY",
        lat=33.7140,
        lng=-112.1160,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.85,
        capex=7800000.0,
        permit_vel=41.0,
        shift_ratio=1.50,
        sla=62.0,
        description="North I-17 mixed-use town center with new-construction residential and commercial miscellaneous permits.",
        city_id="phoenix",
    ),
    "North Gateway": SubmarketMeta(
        name="North Gateway",
        borough="NORTHWEST_DEER_VALLEY",
        lat=33.7967,
        lng=-112.1180,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.79,
        capex=5800000.0,
        permit_vel=35.0,
        shift_ratio=1.44,
        sla=56.0,
        description="Far-north Carefree Highway growth edge with master-planned residential permitting at the city limit.",
        city_id="phoenix",
    ),
}


PHOENIX_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_CENTRAL": BoroughMeta(
        name="DOWNTOWN_CENTRAL",
        center_lat=33.47,
        center_lng=-112.08,
        zoom=13.5,
        bbox=PHOENIX_DIVISION_BBOXES["DOWNTOWN_CENTRAL"],
        submarkets=[k for k, v in PHOENIX_SUBMARKETS.items() if v.borough == "DOWNTOWN_CENTRAL"],
        city_id="phoenix",
    ),
    "SOUTH_MOUNTAIN": BoroughMeta(
        name="SOUTH_MOUNTAIN",
        center_lat=33.36,
        center_lng=-112.06,
        zoom=12.5,
        bbox=PHOENIX_DIVISION_BBOXES["SOUTH_MOUNTAIN"],
        submarkets=[k for k, v in PHOENIX_SUBMARKETS.items() if v.borough == "SOUTH_MOUNTAIN"],
        city_id="phoenix",
    ),
    "WEST_VILLAGES": BoroughMeta(
        name="WEST_VILLAGES",
        center_lat=33.45,
        center_lng=-112.22,
        zoom=12.5,
        bbox=PHOENIX_DIVISION_BBOXES["WEST_VILLAGES"],
        submarkets=[k for k, v in PHOENIX_SUBMARKETS.items() if v.borough == "WEST_VILLAGES"],
        city_id="phoenix",
    ),
    "NORTH_CENTRAL": BoroughMeta(
        name="NORTH_CENTRAL",
        center_lat=33.575,
        center_lng=-112.07,
        zoom=13.0,
        bbox=PHOENIX_DIVISION_BBOXES["NORTH_CENTRAL"],
        submarkets=[k for k, v in PHOENIX_SUBMARKETS.items() if v.borough == "NORTH_CENTRAL"],
        city_id="phoenix",
    ),
    "NORTHEAST_PARADISE": BoroughMeta(
        name="NORTHEAST_PARADISE",
        center_lat=33.59,
        center_lng=-111.96,
        zoom=12.5,
        bbox=PHOENIX_DIVISION_BBOXES["NORTHEAST_PARADISE"],
        submarkets=[k for k, v in PHOENIX_SUBMARKETS.items() if v.borough == "NORTHEAST_PARADISE"],
        city_id="phoenix",
    ),
    "NORTHWEST_DEER_VALLEY": BoroughMeta(
        name="NORTHWEST_DEER_VALLEY",
        center_lat=33.73,
        center_lng=-112.12,
        zoom=12.0,
        bbox=PHOENIX_DIVISION_BBOXES["NORTHWEST_DEER_VALLEY"],
        submarkets=[k for k, v in PHOENIX_SUBMARKETS.items() if v.borough == "NORTHWEST_DEER_VALLEY"],
        city_id="phoenix",
    ),
}

GREATER_PHOENIX_METRO_BBOX = PHOENIX_METRO_BBOX
PHX_DIVISION_BBOXES = PHOENIX_DIVISION_BBOXES
PHX_SUBMARKETS = PHOENIX_SUBMARKETS
PHX_DIVISIONS = PHOENIX_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27 against maps.phoenix.gov/pub and mapportal.phoenix.gov/pds.
# ---------------------------------------------------------------------------
PHOENIX_PERMITS_ENDPOINT = (
    "https://maps.phoenix.gov/pub/rest/services/Public/Planning_Permit/MapServer/1"
)
PHOENIX_SHAPEPHX_PERMITS_ENDPOINT = (
    "https://mapportal.phoenix.gov/pds/rest/services/ShapePHX/"
    "ShapePHXPermitsPoints_DL/MapServer/0"
)
PHOENIX_SLA_ENDPOINT = (
    "https://mapportal.phoenix.gov/pds/rest/services/ShapePHX/"
    "ShapePHX_Short_Term_Rentals/MapServer/0"
)

# Frozen twin — recorded so tests can pin that it is NOT registered.
PHOENIX_FROZEN_SHAPEPHX_PERMITS = (
    "https://mapportal.phoenix.gov/pds/rest/services/ShapePHX/"
    "ShapePHXPermitsPoints/MapServer/0"
)

PHOENIX_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": PHOENIX_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "PER_ISSUE_DATE",
        "id_keys": ["PER_NUM", "PID", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "PER_ISSUE_DATE DESC",
            "needs_geocode": False,
            "companion_endpoints": {
                "shapephx_issued": PHOENIX_SHAPEPHX_PERMITS_ENDPOINT,
            },
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": PHOENIX_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ISSUED_DATE",
        "id_keys": ["NAME", "ID", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 7,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "ISSUED_DATE DESC",
            "needs_geocode": False,
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_phoenix_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Phoenix feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (311, deeds,
    ``FeedType.STR``, liquor).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in PHOENIX_FEED_SPECS:
        available = ", ".join(sorted(PHOENIX_FEED_SPECS))
        raise KeyError(
            f"'{PHOENIX_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = PHOENIX_FEED_SPECS[feed_name]
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
    metro_bbox=PHOENIX_METRO_BBOX,
    division_bboxes=PHOENIX_DIVISION_BBOXES,
    submarkets=PHOENIX_SUBMARKETS,
    divisions=PHOENIX_DIVISIONS,
    contains=is_in_phoenix_metro,
)
