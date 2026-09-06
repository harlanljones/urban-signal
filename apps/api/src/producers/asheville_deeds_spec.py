"""DatasetSpec-shaped plain dicts for the Buncombe County (NC) property roll
as Asheville DEEDS supplement (US-399).

LEAF data — NOT registered anywhere. Field names mirror the ``DatasetSpec``
dataclass in ``src/spatial/city_registry.py`` exactly (``DatasetSpec(**spec)``
constructs from these dicts) so the spine can copy them mechanically during
the interlock hold; the per-city placement is documented in
``.streams/us399-asheville-deeds.md`` ("Spine delta").

Source: Buncombe County GIS Property layer (``FeatureServer/1``), 135,239
polygon parcels, ``geometryType: esriGeometryPolygon``, ``objectIdField:
"objectid"``, ``maxRecordCount: 2000``.  WGS84 geometry via ``outSR=4326``.

LABEL: Roll-grade (last sale per parcel), snapshot cadence, not an event
stream.  ``SalePrice`` is zeroed on every row; price is reconstructed client-
side as ``Stamps × 500`` (NC excise stamps, $1.00 per $500 or fraction).
``Instrument`` / ``Reason`` filter for non-arm's-length transactions is
documented in the field map module.

Native polygon → H3 direct via the ArcGIS client's centroid extraction.
"""

from src.config import settings

# Non-arm's-length instrument codes (from Buncombe County's documented
# exemption codes).  These transactions should not contribute price signals.
# Source: https://www.buncombecounty.org/apps/property-search/
NON_ARMS_INSTRUMENTS: set[str] = {
    "ADJ",  # Adjustment
    "CA",   # Court Action
    "DR",   # Deed of Release
    "GC",   # Gift / Certificate
    "GV",   # Government
    "PL",   # Plat
    "UX",   # Tax Exempt
    "VE",   # Vendee
}

# Non-arm's-length reason codes.
NON_ARMS_REASONS: set[str] = {
    "AL", "ATT", "BS", "CO", "CV", "ES", "FD", "FT",
    "GC", "GV", "LO", "NA", "OT", "SP", "TF", "TX", "VC",
}

# Standard arm's-length instrument codes for sales.
ARMS_INSTRUMENTS: set[str] = {
    "WDT",  # Warranty Deed
    "SWD",  # Special Warranty Deed
    "TR",   # Trustee's Deed
    "EXD",  # Executor's Deed
    "CWD",  # Covenant Warranty Deed
    "QD",   # Quitclaim Deed
    "TD",   # Tax Deed
}


def reconstruct_price(stamps: float | None) -> float:
    """Reconstruct sale price from NC excise stamps.

    NC excise stamps: $1.00 per $500 or fraction of consideration.
    Price ≈ ``stamps × 500``.

    Caveat: overstates small/fraction sales.  A $300 sale with $1 in stamps
    would reconstruct to $500.  Below $500, the reconstruction is an upper
    bound, not an exact price.
    """
    if stamps is None or stamps <= 0.0:
        return 0.0
    return stamps * 500.0


def is_arms_length(instrument: str | None, reason: str | None) -> bool:
    """Check whether a transaction is arm's length.

    Returns ``True`` for standard instrument codes with no disqualifying
    reason code.  ``None`` or empty strings pass through as arm's length
    (conservative: include rather than exclude).
    """
    inst = (instrument or "").strip().upper()
    reason = (reason or "").strip().upper()
    if inst in NON_ARMS_INSTRUMENTS:
        return False
    if reason in NON_ARMS_REASONS:
        return False
    if inst and inst not in ARMS_INSTRUMENTS and inst not in NON_ARMS_INSTRUMENTS:
        # Unknown instrument — pass through conservatively.
        pass
    return True


ASHEVILLE_DEEDS_FIELD_MAP: dict[str, list[str]] = {
    "doc_id": ["PIN", "objectid"],
    "bbl": ["PIN"],
    "document_amount": ["Stamps"],
    "recorded_date": ["DeedDate"],
    "party1_grantor": ["Owner"],
    "party2_grantee": ["Owner"],
    "doc_type": ["Instrument"],
    "borough": ["County", "City"],
}

FIELD_MAPS: dict[str, dict[str, list[str]]] = {
    "asheville_deeds": ASHEVILLE_DEEDS_FIELD_MAP,
}

ASHEVILLE_DEEDS_ENDPOINT = (
    "https://gis.buncombecounty.org/arcgis/rest/services/opendata/FeatureServer/1"
)

ASHEVILLE_DEEDS_SPEC: dict = {
    "endpoint": ASHEVILLE_DEEDS_ENDPOINT,
    "platform": "arcgis",
    "watermark_col": "DeedDate",
    "watermark_type": "text",
    "watermark_format": "%Y%m%d",
    "id_keys": ["PIN", "objectid"],
    "topic": settings.topic_deeds,
    "interval_seconds": 86400.0,
    "producer_key": "deeds",
    "expected_cadence_days": 7,
    "ingestion_mode": "snapshot",
    "oid_field": "objectid",
    "max_record_count": 2000,
    "needs_geocode": False,
    "field_map": ASHEVILLE_DEEDS_FIELD_MAP,
}