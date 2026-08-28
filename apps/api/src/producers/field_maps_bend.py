"""Per-city field maps for Bend, OR (US-237), imported by the shared parsers.

Bend is a FOUR-FEED metro on the city's ArcGIS Server at
``services5.arcgis.com/JisFYcK2mIVg9ueP``:

* PERMITS — ``Permit_Applications_Point/FeatureServer/0`` (165,354 rows,
  native point geometry, SR 2270 NAD83 Oregon North ft but outSR=4326
  returns WGS84 deg; ApplicationDate watermark, newest 2026-08-27; Address
  column for geocode fallback).
* SLA — ``License_Application_Points_(Business_Registrations)`` (5,942 rows,
  native point geometry, per-license snapshot; LicenseExpirationDate
  watermark spans annual license terms).
* COMPLAINTS_311 — ``Code_Enforcement_Cases_Polygon_(Public)`` (17,300 rows,
  polygon geometry → centroid via ArcGISClient; CaseReportedDate watermark
  newest 2026-08-28).
* CRIME — ``Public_Calls`` (451,275 rows, native point geometry;
  CreateDateTime watermark newest 2026-08-27T11:43:18; CallAddress +
  Neighborhood for ADR-0004 compliance).

Coordinate contract (pinned by tests):

* All four feeds use **store SR WKID 2270** (NAD83 Oregon North, ft) but
  every query requests ``outSR=4326``, so ``ArcGISClient._flatten_feature``
  lifts native WGS84 point geometry to ``latitude``/``longitude`` keys. No
  ``latitude``/``longitude`` attribute candidates are declared — the
  geometry lift is the sole coordinate source.
* ``Address`` / ``BusinessLocation`` / ``CallAddress`` strings carry the
  full street + city + zip (``"900 NW SKYLINE RANCH RD, BEND, OR 97703"``),
  so ``needs_geocode`` is declared for all feeds as a fallback for rows
  that arrive without geometry.
* Code Enforcement polygons are reduced to centroids by
  ``ArcGISClient._geometry_to_lng_lat`` (rings → centroid), matching the
  King County parcel precedent.
"""


PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["ApplicationNumber", "OBJECTID"],
    "issuance_date": ["IssueDate"],
    "filing_date": ["ApplicationDate"],
    "cost": ["ProjectValuation"],
    "status": ["ApplicationStatus", "StatusDesc", "OverallStatus"],
    "job_type": ["TypeDesc", "ApplicationType", "BldgUse"],
    "address_street": ["Address"],
    "proposed_units": ["Units"],
}

SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["LicenseNumber", "BusinessNumber", "OBJECTID"],
    "license_type": ["BusinessTypeDesc", "ClassDescription1", "BusinessTypeCode"],
    "dba": ["BusinessName"],
    "premises_name": ["BusinessName"],
    "effective_date": ["BR_BusinessOpenedDate"],
    "expiration_date": ["LicenseExpirationDate"],
    "status": ["BusinessStatusDesc", "LicenseStatusDesc"],
    "address_street": ["BusinessLocation"],
}

COMPLAINTS_311_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["CaseNumber", "OBJECTID"],
    "complaint_type": ["TypeDescription"],
    "created_date": ["CaseReportedDate"],
    "status": ["CaseStatus", "StatusDesc"],
    "incident_address": ["Address"],
}

CRIME_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["IncidentNumber", "OBJECTID"],
    "offense_type": ["CallType"],
    "reported_date": ["CreateDateTime"],
    "address": ["CallAddress"],
    "incident_address": ["CallAddress"],
    "borough": ["Neighborhood"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "311": COMPLAINTS_311_FIELD_MAP,
    "crime": CRIME_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Bend, OR"

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "CRIME_FIELD_MAP",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]