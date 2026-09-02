"""Per-city field maps for Tacoma, WA (US-426), imported by the shared parsers.

Tacoma is a THREE-FEED PARTIAL metro on the City of Tacoma's ArcGIS Online
org (``services3.arcgis.com/SCwJH1pD8WSn5T5y``).
"""

PERMITS_FIELD_MAP = {
    "job_id": ["permit_number", "objectid"],
    "issuance_date": ["issued_date"],
    "filing_date": ["application_date"],
    "status": ["current_status"],
    "job_type": ["permit_type", "permit_subtype"],
    "description": ["description"],
    "address_street": ["address_line_1"],
    "zipcode": ["zip"],
}

SLA_FIELD_MAP = {
    "license_id": ["License_Number"],
    "dba": ["Business_Name", "Trade_Name"],
    "premises_name": ["Business_Name"],
    "license_type": ["NAICS_Code_Description"],
    "status": ["Map_Status"],
    "effective_date": ["Business_Open_Date"],
    "address_street": ["Site_Street"],
    "city": ["Site_City"],
    "zipcode": ["Site_Zip_Code"],
}

COMPLAINTS_311_FIELD_MAP = {
    "complaint_id": ["id", "globalid"],
    "status": ["status"],
    "category": ["category"],
    "filed_date": ["created_at"],
    "address_street": ["address"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "311": COMPLAINTS_311_FIELD_MAP,
}

GEOCODE_CONTEXT = "Tacoma, WA"

DROPPED_PII_COLUMNS = (
    "applicant_name",
)

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]