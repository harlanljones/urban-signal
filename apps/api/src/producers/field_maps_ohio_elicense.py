"""Field maps for the US-425 Ohio eLicense statewide CSV.

LEAF module — NOT imported by the shared producers at runtime. The research
probe (2026-08-30) recorded this as a DataOhio eLicense CSV
(``data.ohio.gov`` "State of Ohio Licensure - Individual") with address columns
and date watermarks. The endpoint was NOT verifiable from this host on
2026-09-02 (data.ohio.gov returned 404 on all paths; ohio-data.hub.arcgis.com
returned 200 but contains no Licensure-Individual dataset), so the spec
carries ``verified=False`` and is not registered or scheduled.

Probe-recorded columns: ORIGINAL_ISSUE_DATE, EXPIRATION_DATE, EFFECTIVE_DATE,
ADDRESS_LINE_1, CITY, STATE, ZIP_CODE, COUNTY, LICENSE_TYPE, LICENSE_STATUS,
LICENSE_NUMBER, BUSINESS_NAME, INDIVIDUAL_NAME.

Filter partition: municipality (Akron, Canton, Youngstown, Cleveland, Dayton,
Toledo, Columbus, Cincinnati).
"""

OHIO_ELICENSE_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["license_number", "license_no"],
    "license_type": ["license_type", "license_category"],
    "effective_date": ["original_issue_date", "effective_date"],
    "expiration_date": ["expiration_date"],
    "premises_name": ["business_name", "individual_name"],
    "dba": ["business_name"],
    "address_street": ["address_line_1"],
    "borough": ["city"],
    "zipcode": ["zip_code"],
    "status": ["license_status"],
}