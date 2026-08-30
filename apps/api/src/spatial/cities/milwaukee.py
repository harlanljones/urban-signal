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
# PERMITS + DEEDS feed specs (US-138).
#
# These are plain data so the spine registry can wrap them in DatasetSpec
# instances without creating a circular import back into city_registry.
#
# Two prior blockers are now cleared (US-138 unblocks them):
#   * PERMITS were "address-only coords" → now geocoded at parse time via
#     `extra["needs_geocode"]` (ADR-0004 Postgres replay-cache geocoder).
#   * DEEDS were "yearly archives" with text dates → now declared as a typed
#     text watermark (ADR-0005) with a declared `watermark_format`; any
#     discovered sentinel spellings are appended to `watermark_exclude` at
#     spine time (degradation, not corruption, per ADR-0005).
#
# =============================================================================

MILWAUKEE_PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["record_id"],
    "address_street": ["address"],
    "issuance_date": ["date_issued"],
    "filing_date": ["date_opened"],
    "job_type": ["permit_type"],
    "cost": ["construction_total_cost"],
}

MILWAUKEE_DEEDS_FIELD_MAP: dict[str, list[str]] = {
    "doc_id": ["propertyid"],
    "bbl": ["taxkey"],
    "address_street": ["address"],
    "document_amount": ["sale_price"],
    "recorded_date": ["sale_date"],
    "doc_type": ["proptype"],
    "borough": ["district", "nbhd"],
}

MILWAUKEE_PERMITS_SPEC: dict = {
    "endpoint": "https://data.milwaukee.gov/dataset/9bada2e0-fad5-4545-8674-1b2c8c4e9f2f/resource/828e9630-d7cb-42e4-960e-964eae916397/download/buildingpermits.csv",
    "platform": "csv",
    "watermark_col": "date_issued",
    "id_keys": ["record_id"],
    "interval_seconds": 300.0,
    "producer_key": "permits",
    "extra": {
        "expected_cadence_days": 90,
        "order_by": "date_issued ASC",
        "id_col": "record_id",
        # ADR-0004: permits arrive address-only; geocode at parse time.
        "needs_geocode": True,
        "geocode_context": "Milwaukee, WI",
        "scope": "Milwaukee building permits (CKAN CSV, address-only coords; geocoded per ADR-0004)",
        "field_map": MILWAUKEE_PERMITS_FIELD_MAP,
    },
}

MILWAUKEE_DEEDS_SPEC: dict = {
    "endpoint": "https://data.milwaukee.gov/dataset/7a8b81f6-d750-4f62-aee8-30ffce1c64ce/resource/1f2dbf65-3ff9-49a2-a9ef-eb0b6c503017/download/armslengthsales_2025_valid_20260417.csv",
    "platform": "csv",
    "watermark_col": "sale_date",
    "id_keys": ["propertyid"],
    "interval_seconds": 600.0,
    "producer_key": "deeds",
    "extra": {
        "expected_cadence_days": 365,
        "order_by": "sale_date ASC",
        "id_col": "propertyid",
        "endpoint_by_year": {
            "2024": "https://data.milwaukee.gov/dataset/7a8b81f6-d750-4f62-aee8-30ffce1c64ce/resource/01651dab-2be7-40c6-a9d6-31254fe02e29/download/armslengthsales_2024_valid_20250917.csv",
            "2025": "https://data.milwaukee.gov/dataset/7a8b81f6-d750-4f62-aee8-30ffce1c64ce/resource/1f2dbf65-3ff9-49a2-a9ef-eb0b6c503017/download/armslengthsales_2025_valid_20260417.csv",
        },
        "ingestion_mode": "snapshot",
        # ADR-0005: yearly-archive text dates — declare the watermark type so
        # the scheduler tracks recency from the raw formatted string and can
        # exclude any sentinel spellings discovered live.
        "watermark_type": "text",
        "watermark_format": "%m/%d/%Y",
        "watermark_exclude": [],  # append discovered sentinels at spine (ADR-0005)
        "scope": "Milwaukee property sales (yearly CKAN CSV snapshots; text watermark per ADR-0005)",
        "field_map": MILWAUKEE_DEEDS_FIELD_MAP,
    },
}


# =============================================================================
# CKAN supplementation candidates (US-220).
#
# These plain dictionaries are intentionally leaf-owned.  The serial spine
# hold can bind a candidate to an existing FeedType/topic after reviewing the
# event-family fit.  Empty or non-machine-readable candidates stay documented
# here rather than being registered as if they were live feeds.
# =============================================================================

MILWAUKEE_SUPPLEMENTAL_FEED_SPECS: dict[str, dict] = {
    "fire_calls": {
        "endpoint": "ckan://data.milwaukee.gov/cdf51c45-5fe3-415e-a08c-14ed134dcb64",
        "platform": "ckan",
        "watermark_col": "IncidentStarted",
        "id_keys": ["IncidentNumber"],
        "interval_seconds": 300.0,
        "producer_key": "fire_calls",
        "extra": {
            "expected_cadence_days": 7,
            "scope": "Milwaukee Fire Department calls for service (fire and EMS dispatch)",
            "coordinate_columns": ["latitude", "longitude"],
        },
    },
    "ems_calls": {
        "endpoint": "ckan://data.milwaukee.gov/06fd2a64-4348-461a-bda4-5e09b2500615",
        "platform": "ckan",
        "watermark_col": "IncidentAdded",
        "id_keys": ["_id"],
        "interval_seconds": 300.0,
        "producer_key": "ems_calls",
        "extra": {
            "expected_cadence_days": 7,
            "scope": "Milwaukee EMS call-type summary (no coordinates in source)",
        },
    },
    "vacant_buildings": {
        "endpoint": "ckan://data.milwaukee.gov/46dca88b-fec0-48f1-bda6-7296249ea61f",
        "platform": "ckan",
        "watermark_col": "DATEOPENED",
        "id_keys": ["PARCELNBR", "_id"],
        "interval_seconds": 86400.0,
        "producer_key": "vacant_buildings",
        "extra": {
            "expected_cadence_days": 30,
            "needs_geocode": True,
            "geocode_context": "Milwaukee, WI",
            "scope": "Milwaukee vacant/abandoned building register",
        },
    },
    "liquor_licenses": {
        "endpoint": "ckan://data.milwaukee.gov/45c027b5-fa66-4de2-aa7e-d9314292093d",
        "platform": "ckan",
        "watermark_col": "EFF_DATE",
        "id_keys": ["TAXKEY", "TAXKEY_NUMBER"],
        "interval_seconds": 86400.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 365,
            "needs_geocode": True,
            "geocode_context": "Milwaukee, WI",
            "scope": "Milwaukee liquor-license snapshot (address split across HOUSE_NR/STREET/STTYPE)",
        },
    },
    "delinquent_tax_accounts": {
        "endpoint": "ckan://data.milwaukee.gov/8f1367e1-6f8f-44cc-8ed6-2eecd8267ec7",
        "platform": "ckan",
        "watermark_col": "Levy Year",
        "id_keys": ["Tax Key #", "Levy Year"],
        "interval_seconds": 86400.0,
        "producer_key": "tax_delinquency",
        "extra": {
            "expected_cadence_days": 365,
            "needs_geocode": True,
            "geocode_context": "Milwaukee, WI",
            "scope": "Milwaukee delinquent real-estate tax accounts",
        },
    },
}

MILWAUKEE_SUPPLEMENTAL_NOT_VIABLE: dict[str, str] = {
    "traffic_crashes": "live CKAN datastore has schema but zero records",
    "zoning": "researched resource ID is not present in the live CKAN datastore",
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=MILWAUKEE_METRO_BBOX,
    division_bboxes=MILWAUKEE_DIVISION_BBOXES,
    submarkets=MILWAUKEE_SUBMARKETS,
    divisions=MILWAUKEE_DIVISIONS,
    contains=is_in_milwaukee_metro,
)
