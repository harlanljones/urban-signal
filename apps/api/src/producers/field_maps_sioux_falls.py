"""Per-city field maps for Sioux Falls, SD (US-426), imported by the shared
parsers.

Sioux Falls is a ONE-FEED PARTIAL metro on the DataWorks portal
(``gis.siouxfalls.gov``): PERMITS — ``Building Permits`` at
``Data/Community/MapServer/3`` (180,676 rows).
"""

PERMITS_FIELD_MAP = {
    "job_id": ["PERMITNUMBER", "OBJECTID"],
    "issuance_date": ["ISSUEDATE"],
    "filing_date": ["APPLYDATE"],
    "status": ["PERMITSTATUS"],
    "job_type": ["PERMITTYPE", "WORKCLASS"],
    "address_street": ["MAINADDRESS"],
    "proposed_units": ["DwellingUnits"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT = "Sioux Falls, SD"

DROPPED_PII_COLUMNS = ()

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]