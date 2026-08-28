"""Per-city field maps for Virginia Beach, VA (US-354 leaf).

Virginia Beach is an independent city (not a county) registering three
ArcGIS hosted tables on the city AGOL org ``CyVvlIiUfRBmMQuu``: PERMITS
(``Building_Permits_Applications_view``, text ``YYYY/MM/DD`` watermark),
SLA (``Business_Licenses_view``, text ``MM/DD/YYYY`` watermark,
annual-license cadence), and DEEDS (``Property_Sales_`` — a TABLE, not the
point layer sketched in the probe; address-only with ``GPIN`` as the T1
join key). COMPLAINTS_311 is deliberately absent: VB 311 is a phone/app
service with no CRM extract.

This module is a leaf. The shared ``field_maps.py`` dispatch stays
untouched; the spine pins each map onto the matching ``FeedType``.

All three feeds are address-only, so ``needs_geocode=True`` (ADR 0004)
with context "Virginia Beach, VA" is declared on every spec.
"""

from typing import Dict, List

GEOCODE_CONTEXT: str = "Virginia Beach, VA"

# PERMITS — Building_Permits_Applications_view/FeatureServer/0 (table).
# Probe + re-probe 2026-08-27: IssueDate/ApplicationDate are TEXT YYYY/MM/DD
# (ADR 0005 watermark_type="text", watermark_format="%Y/%m/%d"). No valuation
# column exists, so estimated_cost stays 0.0. Register the VIEW, not the
# monthly 202k-row joined point mirror `Building_Permits` (lags its source).
PERMITS_FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["PermitNumber", "OBJECTID"],
    "job_type": ["WorkType", "PermitType"],
    "issuance_date": ["IssueDate"],
    "filing_date": ["ApplicationDate"],
    "address_street": ["StreetAddress"],
    "bbl": ["GPIN"],
    "borough": ["City"],
    "zipcode": ["Zip"],
}

# SLA — Business_Licenses_view/FeatureServer/0 (table). No license-number
# column exists, so license_id falls back to Trade_Name then Owner_Name
# (Norfolk precedent). Watermark Begin_Date is TEXT MM/DD/YYYY — lexical
# ORDER BY sorts "12/31/2025" above "07/31/2026"; the scheduler must use
# the declared-format typed comparison, never a naive DESC first row.
SLA_FIELD_MAP: Dict[str, List[str]] = {
    "license_id": ["Trade_Name", "Owner_Name", "Business_Address"],
    "dba": ["Trade_Name"],
    "premises_name": ["Owner_Name"],
    "license_type": ["Business_Classification", "NAICS"],
    "effective_date": ["Begin_Date"],
    "address_street": ["Business_Address"],
    "borough": ["Business_City"],
    "zipcode": ["Business_ZipCode"],
}

# DEEDS — Property_Sales_/FeatureServer/0 (TABLE; no server-side geometry —
# verified live 2026-08-27). Sales_Date is date-typed (epoch ms on the wire,
# ISO after ArcGISClient flatten). Sale_Price 0 rows are non-arms-length
# transfers and are KEPT (probe precedent). Grantor/grantee columns do not
# exist on the live table. GPIN joins city parcels for the T1 upgrade path.
DEEDS_FIELD_MAP: Dict[str, List[str]] = {
    "doc_id": ["Document_Number", "OBJECTID"],
    "bbl": ["GPIN"],
    "document_amount": ["Sale_Price"],
    "recorded_date": ["Sales_Date"],
    "address_street": ["Street_Address"],
    "incident_address": ["Street_Address"],
    "borough": ["Neighborhood"],
    "zipcode": ["Zip_Code"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "deeds": DEEDS_FIELD_MAP,
}

# Columns that exist on the live SLA table and must never become map
# candidates (PII dropped at ingest per the probe contract).
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "Telephone",
    "Mailing_Address",
    "Mailing_City",
    "Mailing_State",
    "Mailing_Zip_Code",
    "Mailing_ZipCode_Ext",
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]
