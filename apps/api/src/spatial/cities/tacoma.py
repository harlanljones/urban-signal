PERMITS_FIELD_MAP = {
    "job_id": ["permit_number", "objectid"],
    "issuance_date": ["issued_date"],
    "filing_date": ["application_date"],
    "status": ["current_status"],
    "job_type": ["permit_type", "permit_subtype"],
    "description": ["description"],
    "address_street": ["address_line_1"],
    "zipcode": ["zip"],
}

SLA_FIELD_MAP = {
    "license_id": ["License_Number"],
    "dba": ["Business_Name", "Trade_Name"],
    "premises_name": ["Business_Name"],
    "license_type": ["NAICS_Code_Description"],
    "status": ["Map_Status"],
    "effective_date": ["Business_Open_Date"],
    "address_street": ["Site_Street"],
    "city": ["Site_City"],
    "zipcode": ["Site_Zip_Code"],
}

COMPLAINTS_311_FIELD_MAP = {
    "complaint_id": ["id", "globalid"],
    "status": ["status"],
    "category": ["category"],
    "filed_date": ["created_at"],
    "address_street": ["address"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "311": COMPLAINTS_311_FIELD_MAP,
}

GEOCODE_CONTEXT = "Tacoma, WA"

DROPPED_PII_COLUMNS = (
    "applicant_name",
    "Lic_Prof_Email",
    "Lic_Prof_Phone_Number",
)

"""Tacoma, WA spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Tacoma
(Pierce County, WA).

Tacoma is a THREE-FEED PARTIAL metro on the City of Tacoma's ArcGIS Online
org (``services3.arcgis.com/SCwJH1pD8WSn5T5y``, hosted under
``data.cityoftacoma.org``): PERMITS (``accela_permit_data`` FeatureServer/0,
Tier 1, ~111k rows), SLA (``Business_Licenses`` FeatureServer/0, Tier 1,
active business tax accounts), and 311 (``SeeClickFix_Requests``
FeatureServer/0, Tier 1, SeeClickFix public stream). DEEDS stays unregistered:
Pierce County publishes annual assessment rolls and an interactive auditor
index, no bulk deed-sales stream (probe 2026-08-30).

Live-probe caveats that define this leaf (2026-08-30, US-426):

* PERMITS is ``accela_permit_data`` FeatureServer/0 (Accela daily export,
  111,102 rows live), native point geometry, ``issued_date`` watermark
  (newest = 2026-08-29). ``current_status`` is the status column;
  ``permit_type``/``permit_subtype`` carry the work-class split; ``zip`` and
  ``address_line_1`` are the address fields.
* SLA is ``Business_Licenses`` FeatureServer/0 — the city's tax-and-license
  directory (Tier 1 in the probe). The layer is a non-spatial table
  (``geometryType`` None): coordinates resolve via the ADR-0004 geocoder
  from ``Site_Street`` + ``Site_City``/``Site_State``/``Site_Zip_Code``, so
  ``needs_geocode=True`` with context "Tacoma, WA". ``Business_Open_Date``
  is the watermark.
* 311 is ``SeeClickFix_Requests`` FeatureServer/0 — the public 311 request
  stream, native point geometry, ``created_at`` watermark. ``id`` is the
  SeeClickFix request id (dedup key); ``category`` maps to job_type.
* The ``Permit_Issued_Last_30_Days`` / ``Permit_New_Applications_Last_30_Days``
  layers (same org) are rolling 30-day dashboard views, NOT registered: they
  would collide with the permits job name and their rolling window makes
  watermarks unstable. The comprehensive ``accela_permit_data`` layer is the
  registration.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

TACOMA_CITY_ID: str = "tacoma"
TACOMA_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Tacoma. Permissive enough to hold the downtown core (47.2529,
# -122.4443), the Stadium District (47.255, -122.442), North End / Ruston
# (47.28, -122.47), the Sixth Avenue corridor (47.250, -122.490), Hilltop
# (47.245, -122.455), the Eastside / Lincoln District (47.255, -122.425), and
# South Tacoma (47.21, -122.49) — while excluding Puyallup (47.19, -122.29),
# Lakewood (47.17, -122.52 is borderline but kept in the southern belt), and
# Federal Way (47.31, -122.33).
TACOMA_METRO_BBOX: dict[str, float] = {
    "min_lat": 47.14,
    "max_lat": 47.32,
    "min_lng": -122.55,
    "max_lng": -122.38,
}

TACOMA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 47.240,
        "max_lat": 47.265,
        "min_lng": -122.460,
        "max_lng": -122.430,
    },
    "NORTH_END": {
        "min_lat": 47.260,
        "max_lat": 47.310,
        "min_lng": -122.505,
        "max_lng": -122.430,
    },
    "SIXTH_AVENUE": {
        "min_lat": 47.238,
        "max_lat": 47.262,
        "min_lng": -122.510,
        "max_lng": -122.460,
    },
    "HILLTOP": {
        "min_lat": 47.235,
        "max_lat": 47.250,
        "min_lng": -122.475,
        "max_lng": -122.445,
    },
    "EASTSIDE": {
        "min_lat": 47.240,
        "max_lat": 47.262,
        "min_lng": -122.432,
        "max_lng": -122.395,
    },
    "SOUTH_TACOMA": {
        "min_lat": 47.150,
        "max_lat": 47.240,
        "min_lng": -122.540,
        "max_lng": -122.420,
    },
}


def is_in_tacoma_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Tacoma metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        TACOMA_METRO_BBOX["min_lat"] <= lat <= TACOMA_METRO_BBOX["max_lat"]
        and TACOMA_METRO_BBOX["min_lng"] <= lng <= TACOMA_METRO_BBOX["max_lng"]
    )


is_in_greater_tacoma_metro = is_in_tacoma_metro


TACOMA_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (2)
    # =======================================================================
    "Downtown Tacoma": SubmarketMeta(
        name="Downtown Tacoma",
        borough="DOWNTOWN",
        lat=47.2529,
        lng=-122.4443,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.82,
        capex=8200000.0,
        permit_vel=34.0,
        shift_ratio=1.46,
        sla=56.0,
        description="Tacoma's civic and office core around Pacific Avenue with the UW Tacoma campus, the Tacoma Dome district, and steady mixed-use and institutional permitting.",
        city_id="tacoma",
    ),
    "Stadium District": SubmarketMeta(
        name="Stadium District",
        borough="DOWNTOWN",
        lat=47.2550,
        lng=-122.4420,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.80,
        capex=6800000.0,
        permit_vel=28.0,
        shift_ratio=1.42,
        sla=52.0,
        description="Historic Stadium High neighborhood with early-20th-century homes, the Wright Park corridor, and steady residential renovation permits.",
        city_id="tacoma",
    ),
    # =======================================================================
    # NORTH_END (2)
    # =======================================================================
    "North End": SubmarketMeta(
        name="North End",
        borough="NORTH_END",
        lat=47.2680,
        lng=-122.4550,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.84,
        capex=7200000.0,
        permit_vel=30.0,
        shift_ratio=1.45,
        sla=58.0,
        description="Established residential North End with Proctor Street retail, large-lot homes, and consistent high-value remodels.",
        city_id="tacoma",
    ),
    "Ruston / Point Ruston": SubmarketMeta(
        name="Ruston / Point Ruston",
        borough="NORTH_END",
        lat=47.2790,
        lng=-122.4730,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.86,
        capex=8400000.0,
        permit_vel=26.0,
        shift_ratio=1.48,
        sla=54.0,
        description="Waterfront mixed-use redevelopment on Commencement Bay with Point Ruston condos, the Ruston Way corridor, and premium residential construction.",
        city_id="tacoma",
    ),
    # =======================================================================
    # SIXTH_AVENUE (1)
    # =======================================================================
    "Sixth Avenue": SubmarketMeta(
        name="Sixth Avenue",
        borough="SIXTH_AVENUE",
        lat=47.2500,
        lng=-122.4900,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=27.0,
        shift_ratio=1.38,
        sla=60.0,
        description="Sixth Avenue commercial corridor with neighborhood retail, restaurants, taverns, and high business-license turnover.",
        city_id="tacoma",
    ),
    # =======================================================================
    # HILLTOP (1)
    # =======================================================================
    "Hilltop": SubmarketMeta(
        name="Hilltop",
        borough="HILLTOP",
        lat=47.2450,
        lng=-122.4550,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.76,
        capex=7200000.0,
        permit_vel=32.0,
        shift_ratio=1.40,
        sla=62.0,
        description="Rapidly revitalizing Hilltop corridor along Martin Luther King Jr Way with new mixed-use, the light-rail-adjacent development, and high 311-to-permit activity.",
        city_id="tacoma",
    ),
    # =======================================================================
    # EASTSIDE (2)
    # =======================================================================
    "Lincoln District": SubmarketMeta(
        name="Lincoln District",
        borough="EASTSIDE",
        lat=47.2550,
        lng=-122.4300,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.80,
        capex=6400000.0,
        permit_vel=29.0,
        shift_ratio=1.42,
        sla=58.0,
        description="Diverse Eastside commercial district along South 38th and the Lincoln Business District with dense small-business licensing.",
        city_id="tacoma",
    ),
    "Eastside / Salishan": SubmarketMeta(
        name="Eastside / Salishan",
        borough="EASTSIDE",
        lat=47.2480,
        lng=-122.4250,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.74,
        capex=5200000.0,
        permit_vel=25.0,
        shift_ratio=1.36,
        sla=56.0,
        description="Eastside neighborhoods from Portland Avenue to the Salishan redevelopment with infill housing and community-serving commercial.",
        city_id="tacoma",
    ),
    # =======================================================================
    # SOUTH_TACOMA (2)
    # =======================================================================
    "South Tacoma": SubmarketMeta(
        name="South Tacoma",
        borough="SOUTH_TACOMA",
        lat=47.2110,
        lng=-122.4900,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=5800000.0,
        permit_vel=26.0,
        shift_ratio=1.38,
        sla=54.0,
        description="South Tacoma's auto-row and light-industrial belt along South Tacoma Way with warehouse conversions and commercial permitting.",
        city_id="tacoma",
    ),
    "Wapato / South End": SubmarketMeta(
        name="Wapato / South End",
        borough="SOUTH_TACOMA",
        lat=47.1800,
        lng=-122.4600,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.72,
        capex=4600000.0,
        permit_vel=22.0,
        shift_ratio=1.34,
        sla=50.0,
        description="Southern residential belt around Wapato Lake and the South End with single-family infill and steady service permits.",
        city_id="tacoma",
    ),
}


TACOMA_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=47.2529,
        center_lng=-122.4443,
        zoom=14.0,
        bbox=TACOMA_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in TACOMA_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="tacoma",
    ),
    "NORTH_END": BoroughMeta(
        name="NORTH_END",
        center_lat=47.2700,
        center_lng=-122.4600,
        zoom=13.5,
        bbox=TACOMA_DIVISION_BBOXES["NORTH_END"],
        submarkets=[k for k, v in TACOMA_SUBMARKETS.items() if v.borough == "NORTH_END"],
        city_id="tacoma",
    ),
    "SIXTH_AVENUE": BoroughMeta(
        name="SIXTH_AVENUE",
        center_lat=47.2500,
        center_lng=-122.4900,
        zoom=13.5,
        bbox=TACOMA_DIVISION_BBOXES["SIXTH_AVENUE"],
        submarkets=[k for k, v in TACOMA_SUBMARKETS.items() if v.borough == "SIXTH_AVENUE"],
        city_id="tacoma",
    ),
    "HILLTOP": BoroughMeta(
        name="HILLTOP",
        center_lat=47.2440,
        center_lng=-122.4570,
        zoom=14.0,
        bbox=TACOMA_DIVISION_BBOXES["HILLTOP"],
        submarkets=[k for k, v in TACOMA_SUBMARKETS.items() if v.borough == "HILLTOP"],
        city_id="tacoma",
    ),
    "EASTSIDE": BoroughMeta(
        name="EASTSIDE",
        center_lat=47.2510,
        center_lng=-122.4220,
        zoom=13.5,
        bbox=TACOMA_DIVISION_BBOXES["EASTSIDE"],
        submarkets=[k for k, v in TACOMA_SUBMARKETS.items() if v.borough == "EASTSIDE"],
        city_id="tacoma",
    ),
    "SOUTH_TACOMA": BoroughMeta(
        name="SOUTH_TACOMA",
        center_lat=47.2000,
        center_lng=-122.4850,
        zoom=13.0,
        bbox=TACOMA_DIVISION_BBOXES["SOUTH_TACOMA"],
        submarkets=[k for k, v in TACOMA_SUBMARKETS.items() if v.borough == "SOUTH_TACOMA"],
        city_id="tacoma",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-30 (US-426). Do not register the rolling 30-day permit
# dashboard views (Permit_Issued_Last_30_Days / Permit_New_Applications),
# Pierce County annual assessment rolls (not a deed stream), or the
# rental-activity business-license variant.
# ---------------------------------------------------------------------------
TACOMA_PERMITS_ENDPOINT = (
    "https://services3.arcgis.com/SCwJH1pD8WSn5T5y/arcgis/rest/services/"
    "accela_permit_data/FeatureServer/0"
)
TACOMA_SLA_ENDPOINT = (
    "https://services3.arcgis.com/SCwJH1pD8WSn5T5y/arcgis/rest/services/"
    "Business_Licenses/FeatureServer/0"
)
TACOMA_311_ENDPOINT = (
    "https://services3.arcgis.com/SCwJH1pD8WSn5T5y/arcgis/rest/services/"
    "SeeClickFix_Requests/FeatureServer/0"
)

TACOMA_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": TACOMA_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "issued_date",
        "id_keys": ["permit_number", "objectid"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "objectid",
            "max_record_count": 2000,
            "order_by": "issued_date DESC",
            "scope": (
                "accela_permit_data (FeatureServer, 111,102 rows; native "
                "point geometry; issued_date watermark newest 2026-08-29; "
                "Accela daily export; current_status / permit_type / "
                "permit_subtype; address_line_1 + zip)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": TACOMA_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Business_Open_Date",
        "id_keys": ["License_Number"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 7,
            "needs_geocode": True,
            "geocode_context": TACOMA_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "Business_Open_Date DESC",
            "scope": (
                "Business_Licenses (FeatureServer table, active business "
                "tax-account directory; non-spatial table so coordinates "
                "resolve via ADR-0004 geocoder from Site_Street + "
                "Site_City/Site_State/Site_Zip_Code; Business_Open_Date "
                "watermark; NAICS_Code_Description for license_type)"
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
    "311": {
        "endpoint": TACOMA_311_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "created_at",
        "id_keys": ["id", "globalid"],
        "topic_key": "topic_311",
        "interval_seconds": 300.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "created_at DESC",
            "scope": (
                "SeeClickFix_Requests (FeatureServer, public 311 stream; "
                "native point geometry; created_at watermark; id = request "
                "id dedup key; category maps to job_type)"
            ),
            "field_map": COMPLAINTS_311_FIELD_MAP,
        },
    },
}


def get_tacoma_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Tacoma feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in TACOMA_FEED_SPECS:
        available = ", ".join(sorted(TACOMA_FEED_SPECS))
        raise KeyError(
            f"'{TACOMA_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = TACOMA_FEED_SPECS[feed_name]
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
    metro_bbox=TACOMA_METRO_BBOX,
    division_bboxes=TACOMA_DIVISION_BBOXES,
    submarkets=TACOMA_SUBMARKETS,
    divisions=TACOMA_DIVISIONS,
    contains=is_in_tacoma_metro,
)

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "REGISTRATION",
    "SLA_FIELD_MAP",
    "TACOMA_311_ENDPOINT",
    "TACOMA_CITY_ID",
    "TACOMA_DIVISIONS",
    "TACOMA_DIVISION_BBOXES",
    "TACOMA_FEED_SPECS",
    "TACOMA_GEOCODE_CONTEXT",
    "TACOMA_METRO_BBOX",
    "TACOMA_PERMITS_ENDPOINT",
    "TACOMA_SLA_ENDPOINT",
    "TACOMA_SUBMARKETS",
    "get_tacoma_dataset",
    "is_in_greater_tacoma_metro",
    "is_in_tacoma_metro",
]
