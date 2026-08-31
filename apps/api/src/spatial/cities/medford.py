PERMITS_FIELD_MAP = {
    "job_id": ["PERMIT_NO", "OBJECTID"],
    "issuance_date": ["ISSUED"],
    "filing_date": ["APPLIED"],
    "status": ["STATUS"],
    "job_type": ["PermitType"],
    "cost": ["JOBVALUE"],
    "address_street": ["SITE_ADDR"],
    "zipcode": ["SITE_ZIP"],
    "bbl": ["SITE_APN"],
    "borough": ["SITE_CITY"],
}

SLA_FIELD_MAP = {
    "license_id": ["LICENSE_NO"],
    "dba": ["COMPANY"],
    "premises_name": ["COMPANY"],
    "license_type": ["LICENSE_TYPE"],
    "status": ["STATUS"],
    "effective_date": ["ISSUED"],
    "expiration_date": ["EXPIRED"],
    "address_street": ["SITE_ADDR"],
    "zipcode": ["SITE_ZIP"],
    "borough": ["SITE_CITY"],
    "bbl": ["SITE_APN"],
}

CASE_FIELD_MAP = {
    "incident_id": ["CASE_NO"],
    "complaint_type": ["CaseType"],
    "status": ["STATUS"],
    "created_date": ["STARTED"],
    "closed_date": ["CLOSED"],
    "incident_address": ["SITE_ADDR"],
    "zipcode": ["SITE_ZIP"],
    "borough": ["SITE_CITY"],
    "bbl": ["SITE_APN"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "311": CASE_FIELD_MAP,
}

GEOCODE_CONTEXT = "Medford, OR"

DROPPED_PII_COLUMNS = (
    # Permits (FeatureServer/1)
    "Taxlots_FEEOWNER",
    "OWNER_NAME",
    "APPLICANT_NAME",
    "CONTRACTOR_NAME",
    "APPLIED_BY",
    "APPROVED_BY",
    "ISSUED_BY",
    "FINALED_BY",
    "EXPIRED_BY",
    "OTHER_BY1",
    "NOTES",
    # License2_Main (FeatureServer/14)
    "EMAIL",
    "EMERGENCY",
    "FAX",
    "PHONE",
    "PHONE_EXT",
    "LIAB_CARRIER",
    "LIAB_NO",
    "LIAB_ISS",
    "LIAB_EXP",
    "WRKR_COMP",
    "W_COMP_NO",
    "W_COMP_ISS",
    "W_COMP_EXP",
    "TAX_ID",
    "MAIL_ADDRESS1",
    "MAIL_ADDRESS2",
    "MAIL_CITY",
    "MAIL_STATE",
    "MAIL_ZIP",
    # Case_Main (FeatureServer/12)
    "COMPLAINANT_NAME",
    "RESIDENT_NAME",
    "RECEIVED_BY",
    "STARTED_BY",
    "CLOSED_BY",
    "LASTACTION_BY",
    "FOLLOWUP_BY",
    "ASSIGNED_TO",
    "REFERRED_TO",
)

"""Medford, OR spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the Medford metro area
(Jackson County, OR, ~220K population).

Medford is a THREE-FEED PARTIAL metro on the city's ArcGIS Server 12.1
(``maps.medfordmaps.org``), fed by the TRAKiT Community Development database:

* **PERMITS** — ``TRAKiTExport/TRAKiTPermits_service/FeatureServer/1``
  ("Permits from 2020 to Present", ~59k rows, daily). Native point geometry
  (store SR WKID 2270 OR State Plane North feet; client requests
  ``outSR=4326`` -> WGS84). Watermark ``ISSUED``.
* **SLA** — ``MLI2/MLI_TRAKiT_Service/FeatureServer/14`` (License2_Main,
  ~29.6k rows, 6,594 ACTIVE). Table — no geometry; ``needs_geocode=True``
  on ``SITE_ADDR``, context "Medford, OR". Watermark ``ISSUED``.
* **COMPLAINTS_311** — ``MLI2/MLI_TRAKiT_Service/FeatureServer/12``
  (Case_Main code-enforcement cases, ~83.7k rows). Table — no geometry;
  ``needs_geocode=True`` on ``SITE_ADDR``. Watermark ``STARTED``.

Host caveat: ``maps.medfordmaps.org`` is an **ANSI-date host** — ISO
date-string literals in ``where`` return 400 "Unable to complete operation";
only ANSI ``timestamp 'YYYY-MM-DD'`` and ``CURRENT_TIMESTAMP`` work. The
spine must add the host to ``ANSI_DATE_LITERAL_HOSTS`` (watermarks.py).

Future-date sentinels (Tucson discipline): ``LASTACTION`` on Case_Main
carries 2026-09-01/02 values on the 2026-08-28 probe. The watermark is
``STARTED`` (clean), so no ``where`` guard is needed for the base query.

DEEDS Tier 3: Jackson County recorder has no anonymous bulk API; city layers
only carry taxlot polygons (no transaction records). Police CADHistory is a
table without address/coordinate columns (only BEAT_OR_STATION) —
unregistrable per ADR-0004. The HTE_CodeEnforcement (Police folder) layer
has point geometry but is stale (newest real report 2019-03-02) with 2099
sentinels — not registered; Case_Main supersedes it.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MEDFORD_CITY_ID: str = "medford"
MEDFORD_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# Medford urban area (Jackson County, OR). Permissive enough to hold the
# downtown core (42.3266, -122.8756), the Crater Lake Hwy midtown belt, the
# East Medford / McAndrews corridor, the Bear Creek riverside, and the
# Central Point / Jacksonville edges — while excluding Talent / Phoenix to
# the south (42.2456) and White City / Eagle Point to the north (42.4367).
MEDFORD_METRO_BBOX: dict[str, float] = {
    "min_lat": 42.26,
    "max_lat": 42.41,
    "min_lng": -122.99,
    "max_lng": -122.78,
}

# 8 Medford divisions. Hand-authored; borough resolution at ingest comes
# from coordinates via get_division_for_coordinate, so bboxes need only be
# sane and contain their own submarket centers.
MEDFORD_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_MEDFORD": {
        "min_lat": 42.320,
        "max_lat": 42.336,
        "min_lng": -122.884,
        "max_lng": -122.866,
    },
    "MIDTOWN_MEDFORD_CENTER": {
        "min_lat": 42.334,
        "max_lat": 42.350,
        "min_lng": -122.888,
        "max_lng": -122.865,
    },
    "EAST_MEDFORD": {
        "min_lat": 42.318,
        "max_lat": 42.372,
        "min_lng": -122.862,
        "max_lng": -122.820,
    },
    "SOUTH_MEDFORD": {
        "min_lat": 42.278,
        "max_lat": 42.318,
        "min_lng": -122.888,
        "max_lng": -122.830,
    },
    "NORTH_MEDFORD": {
        "min_lat": 42.348,
        "max_lat": 42.390,
        "min_lng": -122.888,
        "max_lng": -122.828,
    },
    "RIVERSIDE_BEAR_CREEK": {
        "min_lat": 42.302,
        "max_lat": 42.338,
        "min_lng": -122.868,
        "max_lng": -122.845,
    },
    "CENTRAL_POINT_EDGE": {
        "min_lat": 42.368,
        "max_lat": 42.402,
        "min_lng": -122.940,
        "max_lng": -122.890,
    },
    "JACKSONVILLE_EDGE": {
        "min_lat": 42.300,
        "max_lat": 42.342,
        "min_lng": -122.985,
        "max_lng": -122.930,
    },
}


def is_in_medford_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Medford metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        MEDFORD_METRO_BBOX["min_lat"] <= lat <= MEDFORD_METRO_BBOX["max_lat"]
        and MEDFORD_METRO_BBOX["min_lng"] <= lng <= MEDFORD_METRO_BBOX["max_lng"]
    )


is_in_greater_medford_metro = is_in_medford_metro


MEDFORD_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_MEDFORD (1)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN_MEDFORD",
        lat=42.3266,
        lng=-122.8756,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.86,
        capex=6400000.0,
        permit_vel=29.0,
        shift_ratio=1.46,
        sla=52.0,
        description="Main Street core with the Medford City Hall, the Rogue Credit Union, and the mixed-use permitting corridor along Riverside Avenue.",
        city_id="medford",
    ),
    # =======================================================================
    # MIDTOWN_MEDFORD_CENTER (1)
    # =======================================================================
    "Medford Center": SubmarketMeta(
        name="Medford Center",
        borough="MIDTOWN_MEDFORD_CENTER",
        lat=42.3418,
        lng=-122.8786,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.84,
        capex=5900000.0,
        permit_vel=27.0,
        shift_ratio=1.44,
        sla=50.0,
        description="Crater Lake Highway midtown corridor with the Medford Center mall, big-box retail, and the city's highest commercial permit velocity.",
        city_id="medford",
    ),
    # =======================================================================
    # EAST_MEDFORD (2)
    # =======================================================================
    "East Medford": SubmarketMeta(
        name="East Medford",
        borough="EAST_MEDFORD",
        lat=42.3330,
        lng=-122.8480,
        zoom=13.5,
        pitch=48.0,
        base_lims=0.82,
        capex=7200000.0,
        permit_vel=31.0,
        shift_ratio=1.48,
        sla=54.0,
        description="East of I-5 along McAndrews Road with master-planned subdivisions, Blackthorn Drive residential infill, and the Rogue Valley Medical Center adjacency.",
        city_id="medford",
    ),
    "McAndrews Corridor": SubmarketMeta(
        name="McAndrews Corridor",
        borough="EAST_MEDFORD",
        lat=42.3430,
        lng=-122.8530,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.85,
        capex=6800000.0,
        permit_vel=30.0,
        shift_ratio=1.47,
        sla=53.0,
        description="E McAndrews Road commercial strip with tenant-improvement remodels, auto dealerships, and the Medford Town Center retail node.",
        city_id="medford",
    ),
    # =======================================================================
    # SOUTH_MEDFORD (2)
    # =======================================================================
    "South Medford": SubmarketMeta(
        name="South Medford",
        borough="SOUTH_MEDFORD",
        lat=42.3100,
        lng=-122.8700,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.81,
        capex=5500000.0,
        permit_vel=24.0,
        shift_ratio=1.42,
        sla=48.0,
        description="South Central Avenue corridor with post-war single-family stock, the Stewart Meadows golf community, and steady replacement-permit activity.",
        city_id="medford",
    ),
    "Stewart Meadows": SubmarketMeta(
        name="Stewart Meadows",
        borough="SOUTH_MEDFORD",
        lat=42.2940,
        lng=-122.8650,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.80,
        capex=6100000.0,
        permit_vel=22.0,
        shift_ratio=1.40,
        sla=46.0,
        description="Stewart Meadows / Roxy Ann Peak foothills edge with newer residential subdivisions, golf-course views, and the Foothills Christian Church node.",
        city_id="medford",
    ),
    # =======================================================================
    # NORTH_MEDFORD (2)
    # =======================================================================
    "North Medford": SubmarketMeta(
        name="North Medford",
        borough="NORTH_MEDFORD",
        lat=42.3583,
        lng=-122.8527,
        zoom=13.5,
        pitch=48.0,
        base_lims=0.83,
        capex=6300000.0,
        permit_vel=26.0,
        shift_ratio=1.45,
        sla=50.0,
        description="North Medford along N Keene Way Drive with CRATER LAKE AVE intersections, residential subdivisions, and the Rogue Valley International Airport edge.",
        city_id="medford",
    ),
    "Airport Edge": SubmarketMeta(
        name="Airport Edge",
        borough="NORTH_MEDFORD",
        lat=42.3720,
        lng=-122.8580,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.82,
        capex=5800000.0,
        permit_vel=24.0,
        shift_ratio=1.43,
        sla=48.0,
        description="Biddle Road industrial corridor and Rogue Valley International-Medford Airport perimeter with light-industrial and aviation-support permitting.",
        city_id="medford",
    ),
    # =======================================================================
    # RIVERSIDE_BEAR_CREEK (1)
    # =======================================================================
    "Riverside": SubmarketMeta(
        name="Riverside",
        borough="RIVERSIDE_BEAR_CREEK",
        lat=42.3237,
        lng=-122.8541,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=5200000.0,
        permit_vel=23.0,
        shift_ratio=1.41,
        sla=47.0,
        description="Bear Creek greenway corridor with the Riverside Park, Hawthorne Park, and the pre-war bungalow stock along the east-side streamside.",
        city_id="medford",
    ),
    # =======================================================================
    # CENTRAL_POINT_EDGE (1)
    # =======================================================================
    "Central Point": SubmarketMeta(
        name="Central Point",
        borough="CENTRAL_POINT_EDGE",
        lat=42.3759,
        lng=-122.9162,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.84,
        capex=6000000.0,
        permit_vel=25.0,
        shift_ratio=1.44,
        sla=49.0,
        description="Central Point town center at the junction of I-5 and OR-99 with the Jackson County Expo Park, the North Medford industrial edge, and Crater Rock Museum.",
        city_id="medford",
    ),
    # =======================================================================
    # JACKSONVILLE_EDGE (1)
    # =======================================================================
    "Jacksonville": SubmarketMeta(
        name="Jacksonville",
        borough="JACKSONVILLE_EDGE",
        lat=42.3134,
        lng=-122.9701,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.85,
        capex=5500000.0,
        permit_vel=22.0,
        shift_ratio=1.43,
        sla=51.0,
        description="Historic Jacksonville town west of Medford with the Britt Music & Arts Festival, Britta Road wine-tourism, and the Applegate Valley growth edge.",
        city_id="medford",
    ),
}


MEDFORD_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_MEDFORD": BoroughMeta(
        name="DOWNTOWN_MEDFORD",
        center_lat=42.3266,
        center_lng=-122.8756,
        zoom=14.0,
        bbox=MEDFORD_DIVISION_BBOXES["DOWNTOWN_MEDFORD"],
        submarkets=[k for k, v in MEDFORD_SUBMARKETS.items() if v.borough == "DOWNTOWN_MEDFORD"],
        city_id="medford",
    ),
    "MIDTOWN_MEDFORD_CENTER": BoroughMeta(
        name="MIDTOWN_MEDFORD_CENTER",
        center_lat=42.3418,
        center_lng=-122.8786,
        zoom=13.5,
        bbox=MEDFORD_DIVISION_BBOXES["MIDTOWN_MEDFORD_CENTER"],
        submarkets=[k for k, v in MEDFORD_SUBMARKETS.items() if v.borough == "MIDTOWN_MEDFORD_CENTER"],
        city_id="medford",
    ),
    "EAST_MEDFORD": BoroughMeta(
        name="EAST_MEDFORD",
        center_lat=42.3390,
        center_lng=-122.8500,
        zoom=13.0,
        bbox=MEDFORD_DIVISION_BBOXES["EAST_MEDFORD"],
        submarkets=[k for k, v in MEDFORD_SUBMARKETS.items() if v.borough == "EAST_MEDFORD"],
        city_id="medford",
    ),
    "SOUTH_MEDFORD": BoroughMeta(
        name="SOUTH_MEDFORD",
        center_lat=42.3000,
        center_lng=-122.8700,
        zoom=13.0,
        bbox=MEDFORD_DIVISION_BBOXES["SOUTH_MEDFORD"],
        submarkets=[k for k, v in MEDFORD_SUBMARKETS.items() if v.borough == "SOUTH_MEDFORD"],
        city_id="medford",
    ),
    "NORTH_MEDFORD": BoroughMeta(
        name="NORTH_MEDFORD",
        center_lat=42.3630,
        center_lng=-122.8550,
        zoom=13.0,
        bbox=MEDFORD_DIVISION_BBOXES["NORTH_MEDFORD"],
        submarkets=[k for k, v in MEDFORD_SUBMARKETS.items() if v.borough == "NORTH_MEDFORD"],
        city_id="medford",
    ),
    "RIVERSIDE_BEAR_CREEK": BoroughMeta(
        name="RIVERSIDE_BEAR_CREEK",
        center_lat=42.3237,
        center_lng=-122.8541,
        zoom=13.5,
        bbox=MEDFORD_DIVISION_BBOXES["RIVERSIDE_BEAR_CREEK"],
        submarkets=[k for k, v in MEDFORD_SUBMARKETS.items() if v.borough == "RIVERSIDE_BEAR_CREEK"],
        city_id="medford",
    ),
    "CENTRAL_POINT_EDGE": BoroughMeta(
        name="CENTRAL_POINT_EDGE",
        center_lat=42.3759,
        center_lng=-122.9162,
        zoom=12.5,
        bbox=MEDFORD_DIVISION_BBOXES["CENTRAL_POINT_EDGE"],
        submarkets=[k for k, v in MEDFORD_SUBMARKETS.items() if v.borough == "CENTRAL_POINT_EDGE"],
        city_id="medford",
    ),
    "JACKSONVILLE_EDGE": BoroughMeta(
        name="JACKSONVILLE_EDGE",
        center_lat=42.3134,
        center_lng=-122.9701,
        zoom=12.5,
        bbox=MEDFORD_DIVISION_BBOXES["JACKSONVILLE_EDGE"],
        submarkets=[k for k, v in MEDFORD_SUBMARKETS.items() if v.borough == "JACKSONVILLE_EDGE"],
        city_id="medford",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Do not register the stale HTE_CodeEnforcement (Police
# folder), Police CADHistory (no address/coords), or Jackson County deeds
# (no bulk API). Permit feed is a FeatureServer (not MapServer) — the
# ArcGISClient handles both.
# ---------------------------------------------------------------------------
MEDFORD_PERMITS_ENDPOINT = (
    "https://maps.medfordmaps.org/arcgis/rest/services/"
    "TRAKiTExport/TRAKiTPermits_service/FeatureServer/1"
)

MEDFORD_SLA_ENDPOINT = (
    "https://maps.medfordmaps.org/arcgis/rest/services/"
    "MLI2/MLI_TRAKiT_Service/FeatureServer/14"
)

MEDFORD_CASES_ENDPOINT = (
    "https://maps.medfordmaps.org/arcgis/rest/services/"
    "MLI2/MLI_TRAKiT_Service/FeatureServer/12"
)

MEDFORD_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": MEDFORD_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ISSUED",
        "id_keys": ["PERMIT_NO"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "geocode_context": MEDFORD_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "ISSUED DESC",
            "scope": (
                "TRAKiT permits from 2020 to present (FeatureServer on "
                "maps.medfordmaps.org ArcGIS 12.1; native point geometry "
                "store SR WKID 2270; outSR=4326 coordinate lift; "
                "ISSUED watermark daily; host is ANSI-date — spine must "
                "add maps.medfordmaps.org to ANSI_DATE_LITERAL_HOSTS; "
                "SITE_CITY in {MEDFORD, CENTRAL POINT, UNINCORPORATED})"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": MEDFORD_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ISSUED",
        "id_keys": ["LICENSE_NO", "RECORDID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": MEDFORD_GEOCODE_CONTEXT,
            "oid_field": "RowNum",
            "max_record_count": 2000,
            "order_by": "ISSUED DESC",
            "scope": (
                "License2_Main TRAKiT business licenses (29,576 rows; "
                "6,594 ACTIVE; Table — no geometry; geocode supplement "
                "on SITE_ADDR; ISSUED watermark daily; host is ANSI-date; "
                "LICENSE_TYPE in {COMMERCIAL, HOME BASED, LIQUOR, "
                "MARIJUANA, RENTAL REGISTRATION, PAWNBROKERS, ...})"
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
    "311": {
        "endpoint": MEDFORD_CASES_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "STARTED",
        "id_keys": ["CASE_NO", "RECORDID"],
        "topic_key": "topic_311",
        "interval_seconds": 300.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": MEDFORD_GEOCODE_CONTEXT,
            "oid_field": "RECORDID",
            "max_record_count": 2000,
            "order_by": "STARTED DESC",
            "scope": (
                "Case_Main TRAKiT code-enforcement cases (83,683 rows; "
                "Table — no geometry; geocode supplement on SITE_ADDR; "
                "STARTED watermark daily; LASTACTION has future-dated "
                "sentinels (2026-09-01/02) — NOT the watermark; host is "
                "ANSI-date; CaseType in {NUISANCE VIOLATION, WEED "
                "COMPLAINT, GRAFFITI, ...} — supersedes the stale "
                "HTE_CodeEnforcement layer)"
            ),
            "field_map": CASE_FIELD_MAP,
        },
    },
}


def get_medford_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Medford feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in MEDFORD_FEED_SPECS:
        available = ", ".join(sorted(MEDFORD_FEED_SPECS))
        raise KeyError(
            f"'{MEDFORD_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = MEDFORD_FEED_SPECS[feed_name]
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
    metro_bbox=MEDFORD_METRO_BBOX,
    division_bboxes=MEDFORD_DIVISION_BBOXES,
    submarkets=MEDFORD_SUBMARKETS,
    divisions=MEDFORD_DIVISIONS,
    contains=is_in_medford_metro,
)

__all__ = [
    "MEDFORD_CASES_ENDPOINT",
    "MEDFORD_CITY_ID",
    "MEDFORD_DIVISIONS",
    "MEDFORD_DIVISION_BBOXES",
    "MEDFORD_FEED_SPECS",
    "MEDFORD_GEOCODE_CONTEXT",
    "MEDFORD_METRO_BBOX",
    "MEDFORD_PERMITS_ENDPOINT",
    "MEDFORD_SLA_ENDPOINT",
    "MEDFORD_SUBMARKETS",
    "REGISTRATION",
    "get_medford_dataset",
    "is_in_greater_medford_metro",
    "is_in_medford_metro",
]