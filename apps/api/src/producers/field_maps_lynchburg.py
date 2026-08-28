"""Per-city field maps for Lynchburg, VA (US-318 leaf).

Lynchburg is an independent city (not a county) registering three ArcGIS
layers on the city's single open-data MapServer
(``mapviewer.lynchburgva.gov`` ``OpenData/ODPDynamic`` — the SDE service
behind data.cityoflynchburg.opendata.arcgis.com): PERMITS (``/37`` Building
Permits — Tabluar [sic], the city's own layer-name typo), SLA (``/33``
Business Licenses — Tabular), and DEEDS (``/34`` Transfers — Tabular).
COMPLAINTS_311 is deliberately absent: Lynchburg has no municipal 311/CRM
extract (the TRAKiT Violation Cases layer is code enforcement, not 311).

All three tabular layers are non-spatial; their watermarks are true
esriFieldTypeDate columns, so ArcGISClient flattens epoch-ms to ISO and no
ADR-0005 text-watermark declaration is needed on any feed. Layer ``/34``
(Transfers) carries NO ``objectIdField`` in its layer JSON — its OID column
is ``ESRI_OID`` — so its spec must declare ``order_by="ESRI_OID"`` (verified
live: ``orderByFields=OBJECTID`` returns error code 400).

Geocoding paths per feed:
* PERMITS — address-only ``Address`` column on the tabular layer (ADR 0004);
  the native-point ``/18`` Locations layer (same ``RecordNo`` key) is the T1
  upgrade path.
* SLA — mail-address parts (``MailAddress1``…); the native-point ``/2``
  Locations layer (``ConcatenatedAddress``, same ``LicenseNumber`` key) is
  the T1 upgrade path.
* DEEDS — no address column at all. Coordinates arrive via the spec's
  ``parcel_join`` (``LRSN`` → the ``/41`` Parcel polygons, centroid
  source) applied by the deeds ``run_stream`` enrichment step, matching the
  probe's Path A; the ADR-0004 hook is the fallback and stays lossless when
  it yields nothing.

This module is a leaf. The shared ``field_maps.py`` dispatch stays
untouched; the spine pins each map onto the matching ``FeedType``.
"""

from typing import Dict, List

GEOCODE_CONTEXT: str = "Lynchburg, VA"

# PERMITS — Building Permits - Tabluar /MapServer/37 (TRAKiT export).
# StartDate is date-typed (ISO after client flatten). No application-date
# column exists, so filing_date stays unmapped. JobValue is the declared
# job cost. Neighborhood carries TRAKiT planning-area names (e.g.
# "WYNDHURST INDUSTRIAL CORRIDOR") and passes through as
# source_neighborhood. Status vocabulary includes APPROVED / FINALED /
# EXPIRED / IN REVIEW — no server-side filter is declared (the probe's
# registration sketch registers the table whole).
PERMITS_FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["RecordNo", "OBJECTID"],
    "job_type": ["SubType", "Type"],
    "issuance_date": ["StartDate"],
    "address_street": ["Address"],
    "bbl": ["ParcelID"],
    "borough": ["Neighborhood"],
    "cost": ["JobValue"],
    "status": ["Status"],
}

# SLA — Business Licenses - Tabular /MapServer/33. LicenseNumber is a
# zero-padded 6-digit string ("031386") — the producer's float-normalize
# branch is scoped to san_diego only, so leading zeros survive. TradeName
# is empty on most live rows; license_id/dba fall through to Company
# (first_mapped skips falsy candidates). The mailing block is the only
# address the tabular layer carries.
SLA_FIELD_MAP: Dict[str, List[str]] = {
    "license_id": ["LicenseNumber", "Company", "TradeName"],
    "dba": ["TradeName", "Company"],
    "premises_name": ["Company"],
    "license_type": ["BusinessType"],
    "effective_date": ["LicenseIssued"],
    "expiration_date": ["LicenseExpires"],
    "address_street": ["MailAddress1"],
    "zipcode": ["MailZip"],
    "status": ["Status"],
}

# DEEDS — Transfers - Tabular /MapServer/34. No address column exists
# (coordinates come from the parcel_join LRSN→Parcel-centroid enrichment,
# or stay null lossless). SaleAmount 0 rows are non-arms-length transfers
# (wills, timeshares between family) and are KEPT — probe precedent.
# ConveyanceForm/SaleType are space-padded fixed-width strings; leaving
# doc_type unmapped lets the producer default it to "DEED" instead of
# emitting a padded literal. ESRI_OID is the last-resort doc_id candidate
# because DocumentNo repeats across LRSN splits of the same instrument.
DEEDS_FIELD_MAP: Dict[str, List[str]] = {
    "doc_id": ["DocumentNo", "ESRI_OID"],
    "bbl": ["LRSN"],
    "document_amount": ["SaleAmount"],
    "recorded_date": ["SaleDate"],
    "party1_grantor": ["Seller"],
    "party2_grantee": ["Buyer"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "deeds": DEEDS_FIELD_MAP,
}

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]
