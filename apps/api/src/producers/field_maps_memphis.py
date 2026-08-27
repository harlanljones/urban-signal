"""Per-city field maps for Memphis (US-201), imported by the shared parsers.

Memphis is a PARTIAL ArcGIS metro: DPD Building Permits on MEMEGIS AGOL and
citywide 311 on ``311.memphistn.gov``. Spellings do not match the shared
Socrata/NYC chains, so the maps live here as a leaf rather than growing
``src/producers/field_maps.py`` (spine).

Coordinate contract (pinned by tests):

* PERMITS — native WGS84 ``Latitude``/``Longitude`` attributes. Prefer those
  over geometry; the layer has no X/Y columns. ``needs_geocode=True`` is a
  supplement for the ~5% coordinate gap (Address is complete).
* 311 — do **not** map ``X``/``Y``. Those attributes mix WGS84 degrees and
  EPSG:2274 State Plane feet. Prefer ArcGISClient ``outSR=4326`` geometry
  (flattened to ``latitude``/``longitude``). ``Location_Address`` is the
  ADR-0004 fallback.

PII is dropped at the map: CONTACT_*, owner-name/address block, and MLGW
contact fields are never candidates.
"""

from typing import Dict, List

# Canonical permit event field -> DPD_Building_Permits column spellings.
# Live layer (2026-08-27): ObjectId is the OID (not OBJECTID).
PERMITS_FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["Record_ID", "ObjectId", "OBJECTID"],
    "issuance_date": ["Issued_Date"],
    "job_type": ["Construction_Type", "Sub_Type", "Description"],
    "cost": ["Valuation"],
    "address_street": ["Address"],
    "zipcode": ["ZIP_Code"],
    "borough": ["City"],
    "latitude": ["Latitude"],
    "longitude": ["Longitude"],
}

# Canonical 311 event field -> 311_Request_Map_PROD layer-0 spellings.
# Watermark is REPORTED_DATE (Closed_Date has future scheduled closes).
# No X/Y. No CONTACT_*/MLGW_*/Owner_* PII.
COMPLAINTS_311_FIELD_MAP: Dict[str, List[str]] = {
    "incident_id": ["INCIDENT_NUMBER", "INCIDENT_ID", "OBJECTID"],
    "complaint_type": ["REQUEST_TYPE", "DEPARTMENT"],
    "created_date": ["REPORTED_DATE"],
    "closed_date": ["RESOLVED_DATE"],
    "status": ["REQUEST_STATUS"],
    "incident_address": ["Location_Address"],
    "zipcode": ["ZipCode"],
    "descriptor": ["REQUEST_SUMMARY", "REQUEST_TYPE"],
    "borough": ["neigh_desc", "cd_desc", "DEPARTMENT"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "311": COMPLAINTS_311_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Memphis, TN"

# Columns that exist on the live 311 layer and must never become map candidates.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "CONTACT_NAME",
    "CONTACT_EMAIL",
    "CONTACT_PHONE",
    "CONTACT_NAME_FIRST",
    "Owner_Name",
    "Owner_Joint_Name",
    "Owner_Location_Address",
    "Owner_Unit_Address",
    "MLGW_CUSTOMER",
    "MLGW_CONTACT1",
    "MLGW_CONTACT2",
    "MLGW_EMAIL",
)

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]
