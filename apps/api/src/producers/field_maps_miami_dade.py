"""Per-city field maps for Miami-Dade County (US-199 leaf).

Miami-Dade is a PARTIAL county metro on ArcGIS: PERMITS (address-only Hub
table), SLA (Local Business Tax snapshot with native LAT/LON), and DEEDS
(PaGis last-sale points with a YYYYMMDD text watermark). COMPLAINTS_311 is
deliberately absent — public year-slices freeze at 2023; 2024 is token-gated.

This module is a leaf. The shared ``field_maps.py`` dispatch stays untouched.
Keyed by feed-value strings so the spine can pin each map onto the matching
``FeedType`` without growing generic parser chains.

Producer-canonical keys (``issuance_date``, ``address_street``) supersede the
probe sketch's NYC-flavored names (``issued_date``, ``incident_address``);
both spellings are kept so the registration contract and the parsers agree.
"""

from typing import Dict, List

GEOCODE_CONTEXT: str = "Miami-Dade County, FL"

# PERMITS — Hub table miamidade_permit_data/FeatureServer/0 (non-spatial).
# Probe 2026-08-27: PermitIssuedDate DateOnly, PropertyAddress 99.5%.
PERMITS_FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["PermitNumber", "ProcessNumber", "ObjectId"],
    "job_type": ["PermitType", "ApplicationTypeDescription"],
    "cost": ["EstimatedValue"],
    "issuance_date": ["PermitIssuedDate"],
    "issued_date": ["PermitIssuedDate"],
    "filing_date": ["ApplicationDate"],
    "address_street": ["PropertyAddress"],
    "incident_address": ["PropertyAddress"],
    "borough": ["City"],
    "bbl": ["FolioNumber"],
    "proposed_units": ["StructureUnits"],
    "proposed_stories": ["StructureFloors"],
}

# SLA — Local_Business_Tax_Feature_Layer_View/FeatureServer/0 snapshot.
# Native LAT/LON 100%. Companions (certificate_of_use, enterprise_twin) are
# metadata only; the scheduler does not poll them.
SLA_FIELD_MAP: Dict[str, List[str]] = {
    "license_id": ["ACCOUNTNO"],
    "dba": ["BUSNAME"],
    "premises_name": ["OWNERNAME"],
    "license_type": ["CLASSDESC", "CATGRYNAME", "OCCDESC"],
    "effective_date": ["BUSSDATE"],
    "address_street": ["BUSADDR"],
    "latitude": ["LAT"],
    "longitude": ["LON"],
    "status": ["ACCSTATUS", "PAIDSTATUS"],
    "borough": ["BUSCITY"],
    "zipcode": ["ZIPCODE"],
}

# DEEDS — MD_ComparableSales/MapServer/5 last-sale points.
# DOS_1 is text YYYYMMDD (ADR 0005). Geometry is native; ArcGISClient lifts
# it to latitude/longitude. Filter PRICE_1 >= 10000 at the spec, not here.
DEEDS_FIELD_MAP: Dict[str, List[str]] = {
    "doc_id": ["OR_BK_1", "OR_PG_1", "FOLIO", "OBJECTID"],
    "bbl": ["FOLIO"],
    "document_amount": ["PRICE_1"],
    "recorded_date": ["DOS_1"],
    "party1_grantor": ["GRANTOR_1"],
    "party2_grantee": ["GRANTEE_1"],
    "address_street": ["TRUE_SITE_ADDR"],
    "incident_address": ["TRUE_SITE_ADDR"],
    "zipcode": ["TRUE_SITE_ZIP_CODE"],
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
