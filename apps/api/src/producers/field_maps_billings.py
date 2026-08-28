"""Per-city field maps for Billings, MT (US-234), imported by the shared parsers.

Billings is a TWO-FEED PARTIAL metro on the City of Billings ArcGIS Server
(billingsgis.com) and ArcGIS Online (services6.arcgis.com/rCC3yWJa2mjYtKDP):

PERMITS — ``BuildingPermits_CodeViolations_EXT`` (MapServer/0, Tier 1, daily).
   81,016 rows; native WGS84 geometry (outSR=4326) AND native Latitude/Longitude
   attribute columns — both are native degrees, but the leaf relies on the
   geometry lift only (Greenville discipline). Issue_Date is NOT where-clause
   queryable (ArcGIS 400) — orderByFields only, filter at analytics. Duplicate
   Building_Permit_Num rows exist (contractor-to-permit join) — OBJECTID is the
   true unique key. PII: Owner, Owner_Address, Owner_City/State/Zip, Contractor,
   Contractor_Num, Entered_By columns are dropped.

311 — ``Requests_public`` (FeatureServer/0, Tier 1, daily). 245 rows; native
   WGS84 point geometry. Watermark created_date is esriFieldTypeDate. PII:
   pocfirstname, poclastname, created_user are dropped.

Crime feeds (bpd_offenses, tfoffenses_rolling_6months_online) both carry
WGS84 coordinates/address but are stale (newest 2024-08, 2023-12) — not
registered. No SLA or deeds feeds found (Yellowstone County recorder site
unreachable).
"""


PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["Building_Permit_Num", "OBJECTID"],
    "issuance_date": ["Issue_Date"],
    "filing_date": ["Date_Entered"],
    "status": ["Permit_Status"],
    "job_type": ["Permit_Type"],
    "address_street": ["Property_Address"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
}

BILLINGS_311_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["reqid", "OBJECTID"],
    "created_date": ["created_date"],
    "closed_date": ["resolutiondt"],
    "status": ["status"],
    "complaint_type": ["reqtype"],
    "incident_address": ["locdesc"],
}

GEOCODE_CONTEXT: str = "Billings, MT"

DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "Owner",
    "Owner_Address",
    "Owner_City",
    "Owner_State",
    "Owner_Zip",
    "Contractor",
    "Contractor_Num",
    "Entered_By",
    "pocfirstname",
    "poclastname",
    "created_user",
)

__all__ = [
    "BILLINGS_311_FIELD_MAP",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]