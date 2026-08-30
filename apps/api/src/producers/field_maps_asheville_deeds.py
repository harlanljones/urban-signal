"""Field maps for the Buncombe County (NC) property roll → Asheville DEEDS
supplement (US-399).

LEAF module — NOT imported by the shared producers at runtime. In production
each map is merged into the owning city's ``CityRegistration``
``datasets[FeedType.DEEDS].field_map`` in ``src/spatial/city_registry.py`` (the
spine) when the orchestrator applies the interlock; this file proves the
proposed spellings resolve through the ``DeedsACRISProducer`` row path and
hands the spine a copy-pasteable contract.

Source: Buncombe County GIS Property layer (live-verified 2026-08-30 from this
host):
https://gis.buncombecounty.org/arcgis/rest/services/opendata/FeatureServer/1

- 135,239 polygon parcels, ``objectIdField: "objectid"``, ``maxRecordCount:
  2000``, ``geometryType: esriGeometryPolygon``.
- ``PIN`` = parcel identifier (18-char text). ``DeedDate`` = YYYYMMDD text
  (watermark). ``Owner`` = current owner (last grantee). ``DeedBook`` /
  ``DeedPage`` = recording reference. ``Instrument`` = deed type (WDT = warranty
  deed, SWD = special warranty deed, ADJ = adjustment, etc.). ``Reason`` =
  transaction reason code. ``Stamps`` = NC excise stamps ($1.00 per $500 or
  fraction; populated on ~57% of parcels). ``TotalMarketValue`` = current
  assessed value. ``SalePrice`` = zeroed on every row. ``Improved`` = Y/N
  structure indicator.

PRICE RECONSTRUCTION: ``SalePrice`` is zeroed on the source.  NC excise stamps
are $1.00 per $500 or fraction of consideration.  Reconstructed price ≈
``Stamps × 500``.  This overstates small/fraction sales (a $300 sale with $1
stamps would reconstruct to $500).  The helper ``reconstruct_price`` documents
this caveat.

NON-ARM'S-LENGTH FILTER: Transactions with ``Instrument`` in {ADJ, CA, DR,
GC, GV, PL, UX, VE} and/or ``Reason`` in {AL, ATT, BS, CO, CV, ES, FD, FT,
GC, GV, LO, NA, OT, SP, TF, TX, VC} should be excluded from price signal
processing.  The ``is_arms_length`` helper identifies qualifying rows.

Canonical fields mirror the chains in ``DeedsACRISProducer`` /
``field_maps.first_mapped``: doc_id, bbl, document_amount, recorded_date,
party1_grantor, party2_grantee, borough, latitude, longitude, doc_type.
Keyed to ``FeedType.DEEDS`` semantics of ``field_maps.resolve_field_map``.
"""


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