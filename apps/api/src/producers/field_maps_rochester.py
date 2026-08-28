"""Per-city field maps for Rochester, NY (US-351 leaf).

Rochester registers one feed: the DEEDS/sales Tier-1 extract of the city's
Tax Parcel Records layer (``Tax_Parcels_Open_Data/FeatureServer/0`` on the
on-prem ArcGIS server ``maps.cityofrochester.gov``). The layer carries native
parcel polygon geometry, so the feed is spatial and ``needs_geocode`` is NOT
declared — coordinates come from the ArcGIS flatten (``outSR=4326`` rings
reduced to a centroid), never from the geocoder.

Permits, SLA/licenses and COMPLAINTS_311 are deliberately absent: the probe
(2026-08-27) found no permit or license dataset on the Hub at all, and the
311 extract is a frozen 2022 archive (newest ``Request_Date`` 2022-02-07).

This module is a leaf. The shared ``field_maps.py`` dispatch stays untouched;
the spine pins each map onto the matching ``FeedType``.

Noise contract: ``DEED_TYPE='Q'`` $1 quitclaim transfers and ``SALE_PRICE``
as low as $1 are present on the live layer and are KEPT at ingest (the shared
producer has no per-city ``where``; VB zero-price precedent). The county's
arm's-length ``VALID`` flag is empty on 64,632/64,746 rows, so there is no
server-side signal to filter on — market-sale filtering is an analysis-side
concern, not an ingest one.
"""

from typing import Dict, List

# DEEDS — Tax_Parcels_Open_Data/FeatureServer/0 (parcel polygons; re-probed
# live 2026-08-28). SALE_DATE is TEXT MM/DD/YYYY — lexical ORDER BY sorts
# "12/31/2025" above "07/22/2026"; the scheduler must use the declared-format
# typed comparison, never a naive DESC first row (ADR 0005). There is no
# deed-document-number column: PRINTKEY (county print key, e.g.
# "090.40-2-19") is the effective doc_id with PARCELID (SBL) as fallback —
# the Columbus precedent (Instrument_Number null layer-wide). BOOK/PAGE
# identify the recorded deed but cannot be composed by the field map, so
# they ride the spec's id_keys instead. The layer exposes NO owner-name
# columns — party fields parse to None by design (no PII on the wire).
DEEDS_FIELD_MAP: Dict[str, List[str]] = {
    "doc_id": ["PRINTKEY", "PARCELID"],
    "bbl": ["PARCELID"],
    "doc_type": ["DEED_TYPE"],
    "document_amount": ["SALE_PRICE"],
    "recorded_date": ["SALE_DATE"],
    "address_street": ["SITEADDRESS"],
    "incident_address": ["SITEADDRESS"],
    "borough": ["CITY"],
    "zipcode": ["ZIP5"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "deeds": DEEDS_FIELD_MAP,
}

# Sale-bearing metadata columns that are deliberately NOT map candidates:
# ``VALID`` is the county arm's-length flag (empty on 64,632/64,746 rows —
# the filter did not survive the extract), ``MultiSale``/``PARCEL_SOURCE``
# are dedupe/provenance metadata, and ``BOOK``/``PAGE`` are recorded-deed
# references carried by the spec's id_keys, not the field map.
NON_CANDIDATE_METADATA_COLUMNS: tuple[str, ...] = (
    "VALID",
    "MultiSale",
    "PARCEL_SOURCE",
    "BOOK",
    "PAGE",
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "NON_CANDIDATE_METADATA_COLUMNS",
]
