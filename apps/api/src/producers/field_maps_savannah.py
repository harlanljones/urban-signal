"""Per-city field maps for Savannah / Chatham County, GA (US-298 leaf REBUILD).

Savannah is a PARTIAL metro on the Chatham County SAGIS ArcGIS server
(``pub.sagis.org``): ``Savannah/BuildingPermit_FC/FeatureServer/1`` is the
Residential building-permit layer (PERMITS dataset) and
``FeatureServer/0`` is the Commercial layer, registered only as the spine-level
companion ``commercial_building_permits`` — not a separate FeedType. Both layers
share an identical schema, so a single PERMITS field map serves both.

Both layers are native-point (WKID 2239 GA State Plane E ft, served as WGS84 via
the client's ``outSR=4326``). The ArcGISClient flattens each feature's point
geometry onto ``latitude``/``longitude`` keys in the flattened record, so nearly
every row already carries native coordinates and the shared permits parser reads
them through its generic ``row.get("latitude")`` chain. The ADR-0004 address
geocode is the fallback for the residual coordinate-less rows — this map declares
NO latitude/longitude candidates on purpose, so the client-injected keys stay the
first-class path.

The watermark is ``IssuedDate_DATE`` (esriFieldTypeDate → the client flattens
epoch-ms to ISO, no ADR-0005 text declaration). The text mirror ``IssuedDate``
(``MM/DD/YYYY``) is left in the map as a secondary issuance candidate only; the
date-typed field is the primary.

Columns (live-verified 2026-08-28): ``PermitNumber``, ``OBJECTID``, ``Address``,
``District`` (planning-area/neighborhood), ``PermitStatus``, ``PermitType``,
``Permit_Value`` (declared job cost), ``WorkClass`` (job-type vocabulary: New /
Addition / Renovation / Demolition-Total / etc.), ``PIN`` (parcel id / bbl),
``ApplicantName`` (PII — deliberately NOT mapped).

This module is a leaf. The shared ``field_maps.py`` dispatch stays untouched; the
spine pins ``PERMITS_FIELD_MAP`` onto the savannah ``FeedType.PERMITS`` spec.
"""

from typing import Dict, List

GEOCODE_CONTEXT: str = "Savannah, GA"

# PERMITS — BuildingPermit_FC/FeatureServer/1 (Residential; /0 Commercial same
# schema). WorkClass carries the job-type vocabulary (e.g. "New", "Addition",
# "Demolition-Total", "Renovation"), PermitStatus the status (Issued / In Review /
# Approved). District is the neighborhood / planning-area name and passes through
# as the borough+source_neighborhood. IssuedDate_DATE is date-typed (ISO after
# client flatten); the text mirror IssuedDate is a secondary issuance candidate.
PERMITS_FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["PermitNumber", "OBJECTID"],
    "job_type": ["WorkClass"],
    "issuance_date": ["IssuedDate_DATE", "IssuedDate"],
    "address_street": ["Address"],
    "bbl": ["PIN"],
    "borough": ["District"],
    "cost": ["Permit_Value"],
    "status": ["PermitStatus"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "permits": PERMITS_FIELD_MAP,
}

__all__ = ["FIELD_MAP", "GEOCODE_CONTEXT", "PERMITS_FIELD_MAP"]
