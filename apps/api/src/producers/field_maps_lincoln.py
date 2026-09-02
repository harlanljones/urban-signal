"""Per-city field maps for Lincoln, NE (US-426), imported by the shared
parsers.

Lincoln is a ONE-FEED PARTIAL metro on the Lincoln Open Data portal
(``gis.lincoln.ne.gov``): PERMITS — ``Residential_New_Construction_Permits``
MapServer/4 (Previous 3 Years, 2,622 rows).
"""

PERMITS_FIELD_MAP = {
    "job_id": ["PermNo", "OBJECTID_1"],
    "issuance_date": ["Issued"],
    "filing_date": ["Applied"],
    "status": ["CurrStatus"],
    "job_type": ["PermType", "UseType"],
    "description": ["DescWork"],
    "address_street": ["FullAddress", "Address"],
    "city": ["CITY"],
    "zipcode": ["ZIP"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT = "Lincoln, NE"

DROPPED_PII_COLUMNS = ()

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]