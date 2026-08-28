"""Per-city field maps for Aurora, CO (US-326).

Aurora is a Tier-1 two-feed metro on the city ArcGIS Server
(``ags.auroragov.org/aurora/rest/services/OpenData/MapServer``):

* PERMITS — ``Building Permits`` layer 44 (full history; the L156/L157
  rolling windows are NOT registered). ``IssueDate`` watermark;
  ``valuation`` is a string column.
* SLA — ``Businesses (All Non-Home)`` layer 77 with the liquor layer 34
  companion (plus all-businesses 36 / marijuana 4 metadata companions).
  Current-license snapshot grain; ``Issue_Date`` watermark.

CRS quirk (live-verified 2026-08-27): the SLA ``X``/``Y`` attribute pair
and the permits ``PropX``/``PropY`` pair are **NAD83 Colorado South state
plane, US survey feet (EPSG:2232)** — NOT WGS84 degrees. Mapping them as
coordinates would emit ~3.2e6-foot "longitudes" (and the SLA parser has no
out-of-range guard to catch it). The coordinate path is therefore the
``outSR=4326`` point-geometry lift that ``ArcGISClient`` flattens onto
``latitude``/``longitude``; the declared ``state_plane_*`` spec keys let the
spine wire a Boston-style ``_transform_state_plane`` fallback for
null-geometry rows.

This module is a leaf. The shared ``field_maps.py`` dispatch stays untouched.
Keyed by feed-value strings so the spine can pin ``FIELD_MAP["permits"]``
and ``FIELD_MAP["sla"]`` independently.
"""

from typing import Dict, List

# Layer 44. No ``latitude``/``longitude`` candidates: geometry (outSR=4326)
# is the coordinate path and PropX/PropY must stay unmapped (EPSG:2232 ft).
PERMITS_FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["Permit_", "FolderRSN", "OBJECTID"],
    "issuance_date": ["IssueDate"],
    "filing_date": ["InDate"],
    "job_type": ["FolderDesc", "FolderGroupDesc", "SubDesc"],
    "status": ["FolderCondition"],
    "cost": ["valuation"],
    "address_street": ["Address"],
}

# Layers 77 primary / 34 companion share the schema. TaxText is the most
# readable license-type label ("Liquor - Retail Liquor Store License");
# NAICS columns stay as fallbacks per the probe contract. No ``latitude``/
# ``longitude`` candidates — X/Y are EPSG:2232 feet, geometry is WGS84.
SLA_FIELD_MAP: Dict[str, List[str]] = {
    "license_id": ["License_Number", "TL_License_Number", "OBJECTID"],
    "dba": ["Business_Name"],
    "premises_name": ["Business_Owner"],
    "license_type": ["TaxText", "NAICS_Title", "NAICS_Sector"],
    "effective_date": ["Start_Date"],
    "expiration_date": ["End_Date"],
    "address_street": ["Business_Address", "BusinessAddress_DirSuf"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Aurora, CO"

__all__ = [
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]
