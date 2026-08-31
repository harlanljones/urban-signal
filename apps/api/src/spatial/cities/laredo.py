"""Laredo, TX — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the spine (city_registry) and
are currently scoped to the live CKAN permits datastore at data.openlaredo.com
(resource 61972510-7b8c-488a-9e88-b73b0112f496, PERMIT ISS. DATE watermark
2026-07-02, address-only STREET NBR + STREET, needs_geocode=true).

Center: Santa Maria & Matamoros vicinity (27.5306, -99.4803). Bboxes are
hand-authored to tightly contain the urbanized Webb County core while keeping
divisions as strict subsets of the metro envelope, consistent with the
south-central wave-4 leaf pattern (Beaumont / Waco / Amarillo).
"""


from src.spatial.registration import SpatialRegistration
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

LAREDO_CITY_ID: str = "laredo"

# Downtown Laredo is around (27.5306, -99.4803). Metro envelope is generous
# enough to cover the city proper plus immediate Webb County suburbs
# (Pueblo Nuevo, Del Mar, Mines Rd, South Laredo) without spanning the
# full county rural extent.
LAREDO_METRO_BBOX: dict[str, float] = {
    "min_lat": 27.40,
    "max_lat": 27.75,
    "min_lng": -99.65,
    "max_lng": -99.30,
}

# Registration-contract center (City Hall / San Agustin historic core).
LAREDO_CENTER: dict[str, float] = {"lat": 27.5306, "lng": -99.4803}

# Division bounding boxes — strict subsets of LAREDO_METRO_BBOX.
# Two divisions: core/south belt and north/Mines corridor, matching the
# I-35 / Loop 20 natural partition.
LAREDO_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    # Historic core, Heights/Del Mar, Zacate Creek, South Laredo
    "LAREDO_CORE": {
        "min_lat": 27.42,
        "max_lat": 27.58,
        "min_lng": -99.60,
        "max_lng": -99.38,
    },
    # North Laredo, Mines Rd, Del Mar extension, Winfield/Encanto corridor
    "LAREDO_NORTH": {
        "min_lat": 27.58,
        "max_lat": 27.72,
        "min_lng": -99.62,
        "max_lng": -99.32,
    },
}


def is_in_laredo_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Laredo metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        LAREDO_METRO_BBOX["min_lat"] <= lat <= LAREDO_METRO_BBOX["max_lat"]
        and LAREDO_METRO_BBOX["min_lng"] <= lng <= LAREDO_METRO_BBOX["max_lng"]
    )


# Backward compat alias used by some harnesses.
is_in_greater_laredo_metro = is_in_laredo_metro

# Keep is_in_laredo_metro as the canonical entry; also expose bare name for
# historical import compatibility.
is_in_laredo_metro_alias = is_in_laredo_metro


# Submarkets — 6 across the two divisions; coordinates must live inside their
# division boxes for interlock containment. Descriptions are grounded in live
# feed address clusters (e.g. PALOMA CT, SANTANDER DR, LONE STAR LOOP).
LAREDO_SUBMARKETS: dict[str, SubmarketMeta] = {
    # LAREDO_CORE
    "Downtown & San Agustin": SubmarketMeta(
        name="Downtown & San Agustin",
        borough="LAREDO_CORE",
        lat=27.5245,
        lng=-99.5075,
        zoom=14.2,
        pitch=48.0,
        base_lims=0.82,
        capex=6200000.0,
        permit_vel=34.0,
        shift_ratio=1.38,
        sla=55.0,
        description="Historic riverfront core around San Agustin Plaza and the international bridges with rehabilitation and hospitality infill.",
        city_id=LAREDO_CITY_ID,
    ),
    "Heights & Del Mar": SubmarketMeta(
        name="Heights & Del Mar",
        borough="LAREDO_CORE",
        lat=27.5450,
        lng=-99.5050,
        zoom=13.8,
        pitch=46.0,
        base_lims=0.80,
        capex=5800000.0,
        permit_vel=31.0,
        shift_ratio=1.34,
        sla=53.0,
        description="Established north-central residential grid and Del Mar retail corridor with steady alteration and addition permits.",
        city_id=LAREDO_CITY_ID,
    ),
    "Zacate Creek & Washington": SubmarketMeta(
        name="Zacate Creek & Washington",
        borough="LAREDO_CORE",
        lat=27.5400,
        lng=-99.4850,
        zoom=13.6,
        pitch=44.0,
        base_lims=0.79,
        capex=5400000.0,
        permit_vel=29.0,
        shift_ratio=1.32,
        sla=52.0,
        description="Washington Street corridor and Zacate Creek neighborhoods with infill housing and commercial upgrades.",
        city_id=LAREDO_CITY_ID,
    ),
    "South Laredo & Santa Rita": SubmarketMeta(
        name="South Laredo & Santa Rita",
        borough="LAREDO_CORE",
        lat=27.4650,
        lng=-99.4900,
        zoom=13.2,
        pitch=42.0,
        base_lims=0.77,
        capex=5100000.0,
        permit_vel=27.0,
        shift_ratio=1.30,
        sla=51.0,
        description="Southern growth belt toward Santa Rita and the World Trade Bridge with highway-oriented retail and services.",
        city_id=LAREDO_CITY_ID,
    ),
    # LAREDO_NORTH
    "Mines Road Corridor": SubmarketMeta(
        name="Mines Road Corridor",
        borough="LAREDO_NORTH",
        lat=27.6200,
        lng=-99.5600,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.76,
        capex=5600000.0,
        permit_vel=30.0,
        shift_ratio=1.33,
        sla=52.0,
        description="FM 1472 logistics and industrial spine with warehousing, workforce housing, and utility permits.",
        city_id=LAREDO_CITY_ID,
    ),
    "North Laredo & Winfield": SubmarketMeta(
        name="North Laredo & Winfield",
        borough="LAREDO_NORTH",
        lat=27.6500,
        lng=-99.5000,
        zoom=12.8,
        pitch=38.0,
        base_lims=0.75,
        capex=5300000.0,
        permit_vel=28.0,
        shift_ratio=1.31,
        sla=50.0,
        description="Loop 20 / Winfield and Encanto subdivisions with single-family production housing and solar-panel permits.",
        city_id=LAREDO_CITY_ID,
    ),
}


LAREDO_DIVISIONS: dict[str, BoroughMeta] = {
    "LAREDO_CORE": BoroughMeta(
        name="Laredo Core",
        center_lat=27.5200,
        center_lng=-99.4900,
        zoom=12.4,
        bbox=LAREDO_DIVISION_BBOXES["LAREDO_CORE"],
        submarkets=[k for k, v in LAREDO_SUBMARKETS.items() if v.borough == "LAREDO_CORE"],
        city_id=LAREDO_CITY_ID,
    ),
    "LAREDO_NORTH": BoroughMeta(
        name="North Laredo",
        center_lat=27.6350,
        center_lng=-99.5300,
        zoom=11.8,
        bbox=LAREDO_DIVISION_BBOXES["LAREDO_NORTH"],
        submarkets=[k for k, v in LAREDO_SUBMARKETS.items() if v.borough == "LAREDO_NORTH"],
        city_id=LAREDO_CITY_ID,
    ),
}

LAREDO_DIVISION_BBOXES_EXPORT = LAREDO_DIVISION_BBOXES
LAREDO_SUBMARKETS_EXPORT = LAREDO_SUBMARKETS
LAREDO_DIVISIONS_EXPORT = LAREDO_DIVISIONS

# Live probe pin — byte-verbatim watermark from the 2026-08-30 probe.
# CKAN resource 61972510-7b8c-488a-9e88-b73b0112f496, ORDER BY PERMIT ISS. DATE DESC.
LAREDO_PERMITS_WATERMARK_ISO = "2026-07-02T00:00:00"
LAREDO_PERMITS_RESOURCE_ID = "61972510-7b8c-488a-9e88-b73b0112f496"
LAREDO_PERMITS_ENDPOINT = (
    "https://data.openlaredo.com/api/3/action/datastore_search"
    f"?resource_id={LAREDO_PERMITS_RESOURCE_ID}"
)
# Minimal feed spec for the leaf (full spec lives in the spine city_registry).
LAREDO_FEED_SPECS = {
    "permits": {
        "platform": "ckan",
        "endpoint": LAREDO_PERMITS_ENDPOINT,
        "resource_id": LAREDO_PERMITS_RESOURCE_ID,
        "watermark_col": "PERMIT ISS. DATE",
        "needs_geocode": True,
        "geocode_context": "Laredo, TX",
    }
}

REGISTRATION = SpatialRegistration(
    metro_bbox=LAREDO_METRO_BBOX,
    division_bboxes=LAREDO_DIVISION_BBOXES,
    submarkets=LAREDO_SUBMARKETS,
    divisions=LAREDO_DIVISIONS,
    contains=is_in_laredo_metro,
)

__all__ = [
    "LAREDO_CENTER",
    "LAREDO_CITY_ID",
    "LAREDO_DIVISIONS",
    "LAREDO_DIVISIONS_EXPORT",
    "LAREDO_DIVISION_BBOXES",
    "LAREDO_DIVISION_BBOXES_EXPORT",
    "LAREDO_FEED_SPECS",
    "LAREDO_METRO_BBOX",
    "LAREDO_PERMITS_ENDPOINT",
    "LAREDO_PERMITS_RESOURCE_ID",
    "LAREDO_PERMITS_WATERMARK_ISO",
    "LAREDO_SUBMARKETS",
    "LAREDO_SUBMARKETS_EXPORT",
    "REGISTRATION",
    "is_in_greater_laredo_metro",
    "is_in_laredo_metro",
]

PERMITS_FIELD_MAP: dict[str, list[str]] = {
    # APP NBR (numeric) + APP YR composite key; _id is the CKAN row OID fallback.
    "job_id": ["APP_NBR", "APP_YR", "_id"],
    # Watermark column is timestamp; maps to both issuance and filing.
    "issuance_date": ["PERMIT_ISS_DATE"],
    "filing_date": ["PERMIT_ISS_DATE"],
    "status": ["PERMIT_STATUS_DESC", "PERMIT_STATUS", "APP_STAT_DESC", "APP_STATUS"],
    "job_type": ["APP_TYPE_DESC", "PERMIT_TYPE_DESC", "Permit_Group_Type", "Permit_Group_Tab"],
    "cost": ["VALUATION", "TOTAL_FEE", "PERMIT_FEE"],
    "valuation": ["VALUATION"],
    "total_fee": ["TOTAL_FEE"],
    # Split address — first_mapped picks the first truthy; the producer
    # concatenates STREET NBR + STREET when both present.
    "address_street": ["STREET", "STREET_NBR"],
    "street_number": ["STREET_NBR"],
    "street_name": ["STREET"],
    "description": ["APP_DESC", "Permit_Group_Type"],
    "permit_type": ["PERMIT_TYPE", "APP_TYPE"],
    "permit_sequence": ["PERMIT_SEQUENCE"],
    "borough": ["Permit_Group_Tab"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Laredo, TX"

DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "CONTRACTOR NAME",
)


def normalize_laredo_row(row: dict) -> dict:
    """Normalize a raw CKAN datastore row so its keys match PERMITS_FIELD_MAP.

    CKAN field ids contain dots and spaces (e.g. "PERMIT ISS. DATE"). The
    spine ``first_mapped`` treats dots as nesting, so the leaf normalizes
    by replacing dots/spaces with "_" and upper-casing to the map's
    sanitized keys. Both the original and normalized keys are kept so
    existing callers that pass raw rows keep working after the spine patch.
    """
    out: dict = dict(row)
    for k, v in list(row.items()):
        sanitized = k.replace(".", "").replace(" ", "_").replace("-", "_")
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        sanitized = sanitized.strip("_")
        if sanitized != k:
            out[sanitized] = v
            out[sanitized.upper()] = v
    return out

