PERMITS_FIELD_MAP = {
    "job_id": ["ApplicationNumber", "OBJECTID"],
    "issuance_date": ["IssueDate"],
    "filing_date": ["ApplicationDate"],
    "cost": ["ProjectValuation"],
    "status": ["ApplicationStatus", "StatusDesc", "OverallStatus"],
    "job_type": ["TypeDesc", "ApplicationType", "BldgUse"],
    "address_street": ["Address"],
    "proposed_units": ["Units"],
}

SLA_FIELD_MAP = {
    "license_id": ["LicenseNumber", "BusinessNumber", "OBJECTID"],
    "license_type": ["BusinessTypeDesc", "ClassDescription1", "BusinessTypeCode"],
    "dba": ["BusinessName"],
    "premises_name": ["BusinessName"],
    "effective_date": ["BR_BusinessOpenedDate"],
    "expiration_date": ["LicenseExpirationDate"],
    "status": ["BusinessStatusDesc", "LicenseStatusDesc"],
    "address_street": ["BusinessLocation"],
}

COMPLAINTS_311_FIELD_MAP = {
    "incident_id": ["CaseNumber", "OBJECTID"],
    "complaint_type": ["TypeDescription"],
    "created_date": ["CaseReportedDate"],
    "status": ["CaseStatus", "StatusDesc"],
    "incident_address": ["Address"],
}

CRIME_FIELD_MAP = {
    "incident_id": ["IncidentNumber", "OBJECTID"],
    "offense_type": ["CallType"],
    "reported_date": ["CreateDateTime"],
    "address": ["CallAddress"],
    "incident_address": ["CallAddress"],
    "borough": ["Neighborhood"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "311": COMPLAINTS_311_FIELD_MAP,
    "crime": CRIME_FIELD_MAP,
}

GEOCODE_CONTEXT = "Bend, OR"

"""Bend, OR spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Bend
(Deschutes County, Central Oregon).

Bend is a **FOUR-FEED metro** on the city's ArcGIS Server at
``services5.arcgis.com/JisFYcK2mIVg9ueP`` (CityofBendOR org):

* PERMITS — ``Permit_Applications_Point/FeatureServer/0`` (165,354 rows,
  native point geometry, ApplicationDate watermark, newest 2026-08-27).
* SLA — ``License_Application_Points_(Business_Registrations)`` (5,942 rows,
  per-license snapshot, LicenseExpirationDate watermark).
* COMPLAINTS_311 — ``Code_Enforcement_Cases_Polygon_(Public)`` (17,300 rows,
  polygon geometry → centroid, CaseReportedDate watermark, newest 2026-08-28).
* CRIME — ``Public_Calls`` (451,275 rows, native point geometry,
  CreateDateTime watermark, newest 2026-08-27T11:43:18).

DEEDS is deliberately **absent**: Deschutes County publishes no bulk
recorded-deeds/sales endpoint (the county's ArcGIS surface exposes assessor
parcel layers only, no recorder/sales table). Partial without deeds per the
US-237 ticket.

Live-probe caveats that define this leaf (probed 2026-08-28, US-237):

* The ticket's "ArcGIS Hub" hint (``cityofbend.hub.arcgis.com``) is a
  **private org** (all ``/api/*`` routes 401) — the public door is the
  ``services5.arcgis.com/JisFYcK2mIVg9ueP`` FeatureServer surface the Hub
  publishes against.
* All four layers are **FeatureServers** (not MapServers) with
  ``maxRecordCount=2000`` and OBJECTID OID — the same ``query`` contract
  ``ArcGISClient`` already handles. Store SR is **WKID 2270** (NAD83 Oregon
  North, ft) but every query requests ``outSR=4326``, so coordinates are
  native WGS84 and never need a State-Plane transform.
* No future-dated sentinels at probe: newest ApplicationDate/CreateDateTime
  rows are all at-or-before 2026-08-27/28. No ``where`` guard is needed.
* All four feeds are on a **nightly** update cadence (the Calls for Service
  description says "updated nightly ... reflects calls received as of 6 PM
  the previous day").
* ``Address``/``BusinessLocation``/``CallAddress`` strings carry the full
  street + city + zip; ``needs_geocode`` is declared for every feed as an
  ADR-0004 fallback for rows that arrive without geometry.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

BEND_CITY_ID: str = "bend"
BEND_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Bend proper plus the immediately adjacent urban fringe. Permissive
# enough to hold downtown (44.0575, -121.3150), the Old Mill District
# (44.0480, -121.3270), Northwest Crossing (44.0720, -121.3450), the Orchard
# District (44.0690, -121.3030), Southeast Bend (44.0320, -121.3130), and the
# south fringe (Sawtooth Mtn Ln at 44.0098, -121.3199) — while rejecting
# Redmond (44.27, -121.17), Sisters (44.29, -121.55), and La Pine (43.67,
# -121.50).
BEND_METRO_BBOX: dict[str, float] = {
    "min_lat": 43.98,
    "max_lat": 44.12,
    "min_lng": -121.38,
    "max_lng": -121.23,
}

# 6 Bend divisions. Hand-authored; borough resolution at ingest comes from
# coordinates via get_division_for_coordinate, so bboxes need only be sane
# and contain their own submarket centers.
BEND_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_CORE": {
        "min_lat": 44.040,
        "max_lat": 44.060,
        "min_lng": -121.335,
        "max_lng": -121.305,
    },
    "WESTSIDE": {
        "min_lat": 44.015,
        "max_lat": 44.045,
        "min_lng": -121.375,
        "max_lng": -121.335,
    },
    "NORTHWEST_CROSSING": {
        "min_lat": 44.055,
        "max_lat": 44.095,
        "min_lng": -121.370,
        "max_lng": -121.325,
    },
    "EAST_BEND": {
        "min_lat": 44.055,
        "max_lat": 44.095,
        "min_lng": -121.310,
        "max_lng": -121.250,
    },
    "SOUTHEAST_BEND": {
        "min_lat": 44.000,
        "max_lat": 44.055,
        "min_lng": -121.335,
        "max_lng": -121.290,
    },
    "SOUTH_BEND": {
        "min_lat": 43.980,
        "max_lat": 44.010,
        "min_lng": -121.330,
        "max_lng": -121.250,
    },
}


def is_in_bend_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Bend metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        BEND_METRO_BBOX["min_lat"] <= lat <= BEND_METRO_BBOX["max_lat"]
        and BEND_METRO_BBOX["min_lng"] <= lng <= BEND_METRO_BBOX["max_lng"]
    )


is_in_greater_bend_metro = is_in_bend_metro


BEND_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CORE (2)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN_CORE",
        lat=44.0575,
        lng=-121.3150,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.88,
        capex=9800000.0,
        permit_vel=38.0,
        shift_ratio=1.52,
        sla=61.0,
        description="Wall Street and Bond Street core with hotel/adaptive-reuse projects, the pedestrian riverfront, and the metro's densest mixed-use permitting corridor.",
        city_id="bend",
    ),
    "Old Mill District": SubmarketMeta(
        name="Old Mill District",
        borough="DOWNTOWN_CORE",
        lat=44.0480,
        lng=-121.3270,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.90,
        capex=10500000.0,
        permit_vel=32.0,
        shift_ratio=1.48,
        sla=66.0,
        description="Redeveloped lumber-mill campus on the Deschutes River with destination retail, amphitheater, offices, and riverfront multifamily infill.",
        city_id="bend",
    ),
    # =======================================================================
    # WESTSIDE (1)
    # =======================================================================
    "Westside & Century Drive": SubmarketMeta(
        name="Westside & Century Drive",
        borough="WESTSIDE",
        lat=44.0300,
        lng=-121.3520,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=7400000.0,
        permit_vel=28.0,
        shift_ratio=1.44,
        sla=55.0,
        description="Century Drive corridor and southwest residential hills with strip-center retail, medical offices, and steady residential renovation permits.",
        city_id="bend",
    ),
    # =======================================================================
    # NORTHWEST_CROSSING (2)
    # =======================================================================
    "Northwest Crossing": SubmarketMeta(
        name="Northwest Crossing",
        borough="NORTHWEST_CROSSING",
        lat=44.0720,
        lng=-121.3450,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.87,
        capex=9200000.0,
        permit_vel=33.0,
        shift_ratio=1.50,
        sla=58.0,
        description="New-urbanist planned community with mixed-use Main Street, alley-loaded cottages, and the metro's strongest new-build permit pipeline.",
        city_id="bend",
    ),
    "Awbrey Butte": SubmarketMeta(
        name="Awbrey Butte",
        borough="NORTHWEST_CROSSING",
        lat=44.0650,
        lng=-121.3600,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.84,
        capex=8500000.0,
        permit_vel=26.0,
        shift_ratio=1.45,
        sla=53.0,
        description="Upper-west hillside with view-lot estate builds, Skyline Ranch Road development, and top-end residential construction permits.",
        city_id="bend",
    ),
    # =======================================================================
    # EAST_BEND (2)
    # =======================================================================
    "Orchard District": SubmarketMeta(
        name="Orchard District",
        borough="EAST_BEND",
        lat=44.0690,
        lng=-121.3030,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=29.0,
        shift_ratio=1.38,
        sla=50.0,
        description="Northeast historic orchard neighborhood with Craftsman-era housing, NE 3rd Street retail spine, and moderate renovation and ADU permits.",
        city_id="bend",
    ),
    "River West": SubmarketMeta(
        name="River West",
        borough="EAST_BEND",
        lat=44.0760,
        lng=-121.3050,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=24.0,
        shift_ratio=1.33,
        sla=47.0,
        description="North riverfront corridor along the Deschutes with park-adjacent residential and light industrial-to-residential conversions.",
        city_id="bend",
    ),
    # =======================================================================
    # SOUTHEAST_BEND (2)
    # =======================================================================
    "Old Farm District": SubmarketMeta(
        name="Old Farm District",
        borough="SOUTHEAST_BEND",
        lat=44.0320,
        lng=-121.3130,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.79,
        capex=5800000.0,
        permit_vel=27.0,
        shift_ratio=1.36,
        sla=49.0,
        description="Historic southeast farm settlement around Reed Market Road with mid-century ranch stock and steady infill and redevelopment permits.",
        city_id="bend",
    ),
    "Southern Crossing": SubmarketMeta(
        name="Southern Crossing",
        borough="SOUTHEAST_BEND",
        lat=44.0420,
        lng=-121.3140,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.83,
        capex=7000000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=52.0,
        description="South-central neighborhood around SE 3rd and Reed Market with a densifying mixed-use node and growing multifamily development.",
        city_id="bend",
    ),
    # =======================================================================
    # SOUTH_BEND (1)
    # =======================================================================
    "Larkspur": SubmarketMeta(
        name="Larkspur",
        borough="SOUTH_BEND",
        lat=43.9970,
        lng=-121.2780,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=5200000.0,
        permit_vel=22.0,
        shift_ratio=1.30,
        sla=45.0,
        description="Southern Bend residential fringe with Larkspur Trail Park, recent master-planned tracts, and family-oriented new construction.",
        city_id="bend",
    ),
}


BEND_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=44.0530,
        center_lng=-121.3200,
        zoom=14.0,
        bbox=BEND_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in BEND_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="bend",
    ),
    "WESTSIDE": BoroughMeta(
        name="WESTSIDE",
        center_lat=44.0300,
        center_lng=-121.3550,
        zoom=13.5,
        bbox=BEND_DIVISION_BBOXES["WESTSIDE"],
        submarkets=[k for k, v in BEND_SUBMARKETS.items() if v.borough == "WESTSIDE"],
        city_id="bend",
    ),
    "NORTHWEST_CROSSING": BoroughMeta(
        name="NORTHWEST_CROSSING",
        center_lat=44.0700,
        center_lng=-121.3480,
        zoom=13.5,
        bbox=BEND_DIVISION_BBOXES["NORTHWEST_CROSSING"],
        submarkets=[k for k, v in BEND_SUBMARKETS.items() if v.borough == "NORTHWEST_CROSSING"],
        city_id="bend",
    ),
    "EAST_BEND": BoroughMeta(
        name="EAST_BEND",
        center_lat=44.0750,
        center_lng=-121.2950,
        zoom=13.5,
        bbox=BEND_DIVISION_BBOXES["EAST_BEND"],
        submarkets=[k for k, v in BEND_SUBMARKETS.items() if v.borough == "EAST_BEND"],
        city_id="bend",
    ),
    "SOUTHEAST_BEND": BoroughMeta(
        name="SOUTHEAST_BEND",
        center_lat=44.0300,
        center_lng=-121.3100,
        zoom=13.5,
        bbox=BEND_DIVISION_BBOXES["SOUTHEAST_BEND"],
        submarkets=[k for k, v in BEND_SUBMARKETS.items() if v.borough == "SOUTHEAST_BEND"],
        city_id="bend",
    ),
    "SOUTH_BEND": BoroughMeta(
        name="SOUTH_BEND",
        center_lat=43.9970,
        center_lng=-121.2850,
        zoom=13.0,
        bbox=BEND_DIVISION_BBOXES["SOUTH_BEND"],
        submarkets=[k for k, v in BEND_SUBMARKETS.items() if v.borough == "SOUTH_BEND"],
        city_id="bend",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28 (US-237). All four feeds are ArcGIS FeatureServers on
# services5.arcgis.com/JisFYcK2mIVg9ueP. DEEDS unregistered (Deschutes County
# publishes no bulk recorder/sales API).
# ---------------------------------------------------------------------------
BEND_PERMITS_ENDPOINT = (
    "https://services5.arcgis.com/JisFYcK2mIVg9ueP/arcgis/rest/services/"
    "Permit_Applications_Point/FeatureServer/0"
)
BEND_SLA_ENDPOINT = (
    "https://services5.arcgis.com/JisFYcK2mIVg9ueP/arcgis/rest/services/"
    "License_Application_Points_(Business_Registrations)/FeatureServer/0"
)
BEND_COMPLAINTS_311_ENDPOINT = (
    "https://services5.arcgis.com/JisFYcK2mIVg9ueP/arcgis/rest/services/"
    "Code_Enforcement_Cases_Polygon_(Public)/FeatureServer/0"
)
BEND_CRIME_ENDPOINT = (
    "https://services5.arcgis.com/JisFYcK2mIVg9ueP/arcgis/rest/services/"
    "Public_Calls/FeatureServer/0"
)

BEND_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": BEND_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ApplicationDate",
        "id_keys": ["ApplicationNumber", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": BEND_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "ApplicationDate DESC",
            "scope": (
                "Permit_Applications_Point (165,354 rows; store SR 2270 "
                "NAD83 Oregon North ft but outSR=4326 geometry lift is "
                "native WGS84; ApplicationDate watermark newest 2026-08-27; "
                "Address carries full street+city+zip; nightly cadence)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": BEND_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "LicenseExpirationDate",
        "id_keys": ["LicenseNumber", "BusinessNumber", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 7,
            "ingestion_mode": "snapshot",
            "needs_geocode": True,
            "geocode_context": BEND_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "LicenseExpirationDate DESC",
            "scope": (
                "License_Application_Points (5,942 rows; per-license "
                "current-registrations snapshot, LicenseExpirationDate "
                "spans annual license terms; outSR=4326 native geometry; "
                "BusinessLocation full address; nightly republication)"
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
    "311": {
        "endpoint": BEND_COMPLAINTS_311_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "CaseReportedDate",
        "id_keys": ["CaseNumber", "OBJECTID"],
        "topic_key": "topic_311",
        "interval_seconds": 300.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": BEND_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "CaseReportedDate DESC",
            "scope": (
                "Code_Enforcement_Cases_Polygon (17,300 rows; polygon "
                "geometry reduced to centroid; CaseReportedDate watermark "
                "newest 2026-08-28; Address full street+city+zip; nightly)"
            ),
            "field_map": COMPLAINTS_311_FIELD_MAP,
        },
    },
    "crime": {
        "endpoint": BEND_CRIME_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "CreateDateTime",
        "id_keys": ["IncidentNumber", "OBJECTID"],
        "topic_key": "topic_crime",
        "interval_seconds": 300.0,
        "producer_key": "crime",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": BEND_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "CreateDateTime DESC",
            "scope": (
                "Public_Calls / Calls for Service (451,275 rows; native "
                "point geometry outSR=4326; CreateDateTime watermark newest "
                "2026-08-27T11:43; CallAddress block ranges + Neighborhood; "
                "ADR-0004 compliant - geometry + address; updated nightly)"
            ),
            "field_map": CRIME_FIELD_MAP,
        },
    },
}


def get_bend_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a (pending-spine) Bend feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in BEND_FEED_SPECS:
        available = ", ".join(sorted(BEND_FEED_SPECS))
        raise KeyError(
            f"'{BEND_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = BEND_FEED_SPECS[feed_name]
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
    metro_bbox=BEND_METRO_BBOX,
    division_bboxes=BEND_DIVISION_BBOXES,
    submarkets=BEND_SUBMARKETS,
    divisions=BEND_DIVISIONS,
    contains=is_in_bend_metro,
)

__all__ = [
    "BEND_CITY_ID",
    "BEND_COMPLAINTS_311_ENDPOINT",
    "BEND_CRIME_ENDPOINT",
    "BEND_DIVISIONS",
    "BEND_DIVISION_BBOXES",
    "BEND_FEED_SPECS",
    "BEND_GEOCODE_CONTEXT",
    "BEND_METRO_BBOX",
    "BEND_PERMITS_ENDPOINT",
    "BEND_SLA_ENDPOINT",
    "BEND_SUBMARKETS",
    "REGISTRATION",
    "get_bend_dataset",
    "is_in_bend_metro",
    "is_in_greater_bend_metro",
]