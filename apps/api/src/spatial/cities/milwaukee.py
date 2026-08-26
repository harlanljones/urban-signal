"""Milwaukee, Wisconsin spatial registry and dashboard geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MILWAUKEE_METRO_BBOX: dict[str, float] = {
    "min_lat": 42.85,
    "max_lat": 43.20,
    "min_lng": -88.10,
    "max_lng": -87.80,
}

# Population corridor: the city proper within Milwaukee County, nested inside
# the metro bbox per the interlock containment invariant.
MILWAUKEE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "MILWAUKEE_CORE": {
        "min_lat": 42.90,
        "max_lat": 43.18,
        "min_lng": -88.08,
        "max_lng": -87.85,
    },
}


def is_in_milwaukee_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Milwaukee extent."""
    if lat is None or lng is None:
        return False
    return (
        MILWAUKEE_METRO_BBOX["min_lat"] <= lat <= MILWAUKEE_METRO_BBOX["max_lat"]
        and MILWAUKEE_METRO_BBOX["min_lng"] <= lng <= MILWAUKEE_METRO_BBOX["max_lng"]
    )


MILWAUKEE_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & East Town": SubmarketMeta(
        name="Downtown & East Town",
        borough="MILWAUKEE_CORE",
        lat=43.0389,
        lng=-87.9065,
        zoom=13.2,
        pitch=48.0,
        base_lims=0.81,
        capex=8200000.0,
        permit_vel=36.0,
        shift_ratio=1.40,
        sla=64.0,
        description="Lakefront central business district with the Deer District, arena-adjacent hospitality, and dense bar/restaurant license activity.",
        city_id="milwaukee",
    ),
    "Bay View": SubmarketMeta(
        name="Bay View",
        borough="MILWAUKEE_CORE",
        lat=42.9998,
        lng=-87.9057,
        zoom=13.0,
        pitch=46.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=30.0,
        shift_ratio=1.36,
        sla=58.0,
        description="South-side historic mill district with a strong independent tavern and restaurant corridor along Kinnickinnic Avenue.",
        city_id="milwaukee",
    ),
    "Walker's Point": SubmarketMeta(
        name="Walker's Point",
        borough="MILWAUKEE_CORE",
        lat=43.0220,
        lng=-87.9147,
        zoom=13.0,
        pitch=46.0,
        base_lims=0.79,
        capex=6100000.0,
        permit_vel=32.0,
        shift_ratio=1.37,
        sla=60.0,
        description="South-of-downtown food-and-beverage hub with concentrated liquor license turnover and adaptive reuse of industrial buildings.",
        city_id="milwaukee",
    ),
    "Riverwest & Brewers Hill": SubmarketMeta(
        name="Riverwest & Brewers Hill",
        borough="MILWAUKEE_CORE",
        lat=43.0604,
        lng=-87.9179,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.75,
        capex=4800000.0,
        permit_vel=27.0,
        shift_ratio=1.33,
        sla=56.0,
        description="North-side river neighborhoods with neighborhood taverns, music venues, and owner-operator license density.",
        city_id="milwaukee",
    ),
    "Westown & Washington Heights": SubmarketMeta(
        name="Westown & Washington Heights",
        borough="MILWAUKEE_CORE",
        lat=43.0520,
        lng=-87.9700,
        zoom=12.8,
        pitch=42.0,
        base_lims=0.74,
        capex=5200000.0,
        permit_vel=26.0,
        shift_ratio=1.32,
        sla=54.0,
        description="West-side corridor with mixed commercial-residential stock and steady service-sector license renewal activity.",
        city_id="milwaukee",
    ),
}

MILWAUKEE_DIVISIONS: dict[str, BoroughMeta] = {
    "MILWAUKEE_CORE": BoroughMeta(
        name="Milwaukee",
        center_lat=43.0389,
        center_lng=-87.9065,
        zoom=11.2,
        bbox=MILWAUKEE_DIVISION_BBOXES["MILWAUKEE_CORE"],
        submarkets=list(MILWAUKEE_SUBMARKETS),
        city_id="milwaukee",
    ),
}


# =============================================================================
# PERMITS + DEEDS feed specs (US-138 leaf — NOT yet in the spine REGISTRY).
#
# These are the proposed DatasetSpec payloads for CityId.MILWAUKEE PERMITS and
# DEEDS, held here as plain data so the interlock orchestrator can lift them
# into `apps/api/src/spatial/city_registry.py` verbatim (wrapping each dict in
# `DatasetSpec(...)` and binding `topic=settings.topic_permits` /
# `settings.topic_deeds`). They are intentionally NOT `DatasetSpec` instances
# because importing `DatasetSpec`/`FeedType` from `city_registry` here would
# create a circular import (`city_registry` already imports this module).
#
# Platform: both feeds follow the existing Milwaukee SLA — ArcGIS on
# `milwaukeemaps.milwaukee.gov`, an ANSI-date-literal server (see
# `watermark_comparison` / `ANSI_DATE_LITERAL_HOSTS` in
# `src/producers/watermarks.py`), so the incremental `where` renders as
# `col >= date 'YYYY-MM-DD'`.
#
# Two prior blockers are now cleared (US-138 unblocks them):
#   * PERMITS were "address-only coords" → now geocoded at parse time via
#     `extra["needs_geocode"]` (ADR-0004 Postgres replay-cache geocoder).
#   * DEEDS were "yearly archives" with text dates → now declared as a typed
#     text watermark (ADR-0005) with a declared `watermark_format`; any
#     discovered sentinel spellings are appended to `watermark_exclude` at
#     spine time (degradation, not corruption, per ADR-0005).
#
# Endpoints are PROPOSED pending live verification by the spine (the host is
# confirmed Milwaukee ArcGIS; the service-layer IDs must be confirmed against
# `milwaukeemaps.milwaukee.gov` before the registry edit lands).
# =============================================================================

MILWAUKEE_PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["PERMIT_NO", "PERMIT_NUMBER"],
    "address_street": ["ADDRESS", "SITE_ADDRESS", "PROP_ADDRESS"],
    "issuance_date": ["ISSUE_DATE"],
    "filing_date": ["APPLICATION_DATE", "PERMIT_APPLICATION_DATE"],
    "job_type": ["PERMIT_TYPE", "WORK_TYPE", "CONSTRUCTION_TYPE"],
    "cost": ["ESTIMATED_COST", "TOTAL_PROJECT_COST", "EST_COST"],
    "borough": ["NEIGHBORHOOD", "NBHD"],
    "zipcode": ["ZIP_CODE", "ZIP"],
}

MILWAUKEE_DEEDS_FIELD_MAP: dict[str, list[str]] = {
    "doc_id": ["DOCUMENT_NO", "DOC_NO", "INSTRUMENT_NO"],
    "bbl": ["PARCEL_NO", "PIN", "TAXKEY"],
    "document_amount": ["SALE_PRICE", "CONSIDERATION", "TOTAL_CONSIDERATION"],
    "recorded_date": ["RECORDING_DATE", "REC_DATE", "DATE_RECORDED"],
    "party1_grantor": ["GRANTOR", "SELLER", "FROM_PARTY"],
    "party2_grantee": ["GRANTEE", "BUYER", "TO_PARTY"],
    "borough": ["NEIGHBORHOOD", "NBHD"],
}

# PROPOSED endpoint — verify live at spine:
#   https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/permits/building/MapServer/0
MILWAUKEE_PERMITS_SPEC: dict = {
    "endpoint": (
        "https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/"
        "permits/building/MapServer/0"
    ),
    "platform": "arcgis",
    "watermark_col": "ISSUE_DATE",
    "id_keys": ["PERMIT_NO", "OBJECTID"],
    "interval_seconds": 300.0,
    "producer_key": "permits",
    "extra": {
        "expected_cadence_days": 7,
        "oid_field": "OBJECTID",
        "max_record_count": 1000,
        # ADR-0004: permits arrive address-only; geocode at parse time.
        "needs_geocode": True,
        "geocode_context": "Milwaukee, WI",
        "scope": "Milwaukee building permits (address-only coords; geocoded per ADR-0004)",
        "field_map": MILWAUKEE_PERMITS_FIELD_MAP,
    },
}

# PROPOSED endpoint — verify live at spine:
#   https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/assessor/property_sales/MapServer/0
MILWAUKEE_DEEDS_SPEC: dict = {
    "endpoint": (
        "https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/"
        "assessor/property_sales/MapServer/0"
    ),
    "platform": "arcgis",
    "watermark_col": "RECORDING_DATE",
    "id_keys": ["DOCUMENT_NO", "OBJECTID"],
    "interval_seconds": 600.0,
    "producer_key": "deeds",
    "extra": {
        "expected_cadence_days": 30,
        "oid_field": "OBJECTID",
        "max_record_count": 1000,
        # ADR-0005: yearly-archive text dates — declare the watermark type so
        # the scheduler tracks recency from the raw formatted string and can
        # exclude any sentinel spellings discovered live.
        "watermark_type": "text",
        "watermark_format": "%Y-%m-%d",
        "watermark_exclude": [],  # append discovered sentinels at spine (ADR-0005)
        "scope": "Milwaukee County recorded deeds / property sales (text watermark per ADR-0005)",
        "field_map": MILWAUKEE_DEEDS_FIELD_MAP,
    },
}