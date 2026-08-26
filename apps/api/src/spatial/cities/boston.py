"""Boston metro spatial registry and dashboard geometry."""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

BOSTON_METRO_BBOX: dict[str, float] = {
    "min_lat": 42.15,
    "max_lat": 42.55,
    "min_lng": -71.30,
    "max_lng": -70.75,
}

BOSTON_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "BOSTON_CORE": {"min_lat": 42.28, "max_lat": 42.40, "min_lng": -71.15, "max_lng": -70.95},
    "CAMBRIDGE_SOMERVILLE": {"min_lat": 42.34, "max_lat": 42.43, "min_lng": -71.18, "max_lng": -71.05},
    "INNER_NORTH": {"min_lat": 42.35, "max_lat": 42.52, "min_lng": -71.30, "max_lng": -70.85},
    "INNER_SOUTH": {"min_lat": 42.15, "max_lat": 42.35, "min_lng": -71.25, "max_lng": -70.80},
}


def is_in_boston_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Boston extent."""
    if lat is None or lng is None:
        return False
    return (
        BOSTON_METRO_BBOX["min_lat"] <= lat <= BOSTON_METRO_BBOX["max_lat"]
        and BOSTON_METRO_BBOX["min_lng"] <= lng <= BOSTON_METRO_BBOX["max_lng"]
    )


BOSTON_SUBMARKETS: dict[str, SubmarketMeta] = {
    "Downtown & Seaport": SubmarketMeta(
        name="Downtown & Seaport", borough="BOSTON_CORE", lat=42.355, lng=-71.055,
        zoom=13.8, pitch=48.0, base_lims=0.90, capex=10500000.0, permit_vel=52.0,
        shift_ratio=1.58, sla=68.0,
        description="Financial District, Downtown Crossing, and Seaport growth corridors.",
        city_id="boston",
    ),
    "Back Bay & Fenway": SubmarketMeta(
        name="Back Bay & Fenway", borough="BOSTON_CORE", lat=42.347, lng=-71.095,
        zoom=14.0, pitch=46.0, base_lims=0.86, capex=8800000.0, permit_vel=44.0,
        shift_ratio=1.48, sla=63.0,
        description="Dense institutional, residential, and hospitality redevelopment spine.",
        city_id="boston",
    ),
    "Harvard Square": SubmarketMeta(
        name="Harvard Square", borough="CAMBRIDGE_SOMERVILLE", lat=42.373, lng=-71.119,
        zoom=14.0, pitch=45.0, base_lims=0.88, capex=7600000.0, permit_vel=38.0,
        shift_ratio=1.45, sla=61.0,
        description="University, biotech, and mixed-use demand around Harvard Square.",
        city_id="boston",
    ),
    "Union Square": SubmarketMeta(
        name="Union Square", borough="CAMBRIDGE_SOMERVILLE", lat=42.379, lng=-71.095,
        zoom=14.0, pitch=45.0, base_lims=0.82, capex=6200000.0, permit_vel=35.0,
        shift_ratio=1.40, sla=57.0,
        description="Somerville transit-oriented infill and neighborhood commercial corridor.",
        city_id="boston",
    ),
    "Waltham Innovation District": SubmarketMeta(
        name="Waltham Innovation District", borough="INNER_NORTH", lat=42.376, lng=-71.236,
        zoom=13.2, pitch=42.0, base_lims=0.76, capex=5400000.0, permit_vel=29.0,
        shift_ratio=1.34, sla=54.0,
        description="Route 128 office, research, and adaptive-reuse corridor.",
        city_id="boston",
    ),
    "Quincy Center": SubmarketMeta(
        name="Quincy Center", borough="INNER_SOUTH", lat=42.252, lng=-71.003,
        zoom=13.4, pitch=43.0, base_lims=0.74, capex=4800000.0, permit_vel=31.0,
        shift_ratio=1.36, sla=52.0,
        description="South Shore transit hub with residential and civic redevelopment pressure.",
        city_id="boston",
    ),
}


BOSTON_DIVISIONS: dict[str, BoroughMeta] = {
    "BOSTON_CORE": BoroughMeta(
        name="Boston Core", center_lat=42.351, center_lng=-71.065, zoom=12.8,
        bbox=BOSTON_DIVISION_BBOXES["BOSTON_CORE"],
        submarkets=["Downtown & Seaport", "Back Bay & Fenway"], city_id="boston",
    ),
    "CAMBRIDGE_SOMERVILLE": BoroughMeta(
        name="Cambridge & Somerville", center_lat=42.376, center_lng=-71.107, zoom=12.8,
        bbox=BOSTON_DIVISION_BBOXES["CAMBRIDGE_SOMERVILLE"],
        submarkets=["Harvard Square", "Union Square"], city_id="boston",
    ),
    "INNER_NORTH": BoroughMeta(
        name="Inner North & Route 128", center_lat=42.425, center_lng=-71.075, zoom=11.8,
        bbox=BOSTON_DIVISION_BBOXES["INNER_NORTH"],
        submarkets=["Waltham Innovation District"], city_id="boston",
    ),
    "INNER_SOUTH": BoroughMeta(
        name="Inner South", center_lat=42.245, center_lng=-71.030, zoom=11.8,
        bbox=BOSTON_DIVISION_BBOXES["INNER_SOUTH"],
        submarkets=["Quincy Center"], city_id="boston",
    ),
}


# ---------------------------------------------------------------------------
# Boston Licensing Board feed (US-137) — leaf-side feed spec.
#
# The source CKAN resource (04dc653b-...) is the Boston Licensing Board's
# business-license register on data.boston.gov. Its only coordinate columns are
# gpsx/gpsy, expressed in Massachusetts State Plane meters (EPSG:26986), not
# WGS84 degrees — so ~99.6% of rows fail spatial parsing and the feed was
# historically excluded (fails G5 by construction).
#
# Resolution (ADR 0004 fork): the feed is ingested as an ADDRESS-ONLY SLA feed.
# gpsx/gpsy are deliberately NOT mapped to latitude/longitude below; rows are
# geocoded from the business address string at parse time (needs_geocode). The
# field map is re-exported by src/producers/field_maps_boston_licensing.py as
# FIELD_MAP so the orchestrator's spine registration can reference one source.
#
# Column spellings are PROPOSED pending a live probe of the CKAN resource
# (mirrors the Philadelphia field-map precedent) and are pinned by the unit
# test's equality assertion.
# ---------------------------------------------------------------------------

BOSTON_LICENSING_BOARD_FEED: dict[str, object] = {
    "platform": "ckan",
    "dataset_id": "04dc653b-1789-4374-9669-b07df7233344",
    "feed_type": "sla",
    "watermark_col": "licensetype_effective_date",
    "needs_geocode": True,
    "geocode_context": "Boston, MA",
    # gpsx/gpsy intentionally absent: State Plane meters would be mis-read as
    # WGS84 degrees if mapped to latitude/longitude.
    "field_map": {
        "license_id": ["license_id", "licenseno", "license_number"],
        "license_type": ["licensetype", "license_type", "licensecategory"],
        "effective_date": ["licensetype_effective_date", "license_effective_date", "effectivedate"],
        "expiration_date": [
            "licensetype_expiration_date",
            "license_expiration_date",
            "expirationdate",
        ],
        "address_street": ["business_address", "location_address", "address"],
        "dba": ["dba", "doing_business_as", "business_name"],
        "premises_name": ["business_name", "premises_name", "entity_name"],
        "status": ["license_status", "status", "licensestatus"],
        "borough": ["ward", "neighborhood"],
    },
}

