"""Field maps for the US-425 Michigan LARA/MLCC statewide CSV rosters.

LEAF module — NOT imported by the shared producers at runtime. The research
probe (2026-08-30) recorded LARA License Lists & Reports (CSV/Excel) and MLCC
Active Liquor License Queries as Tier 2 Batch ETL candidates. The endpoint was
NOT verifiable from this host on 2026-09-02 (``michigan.gov/lara`` returned
403/302; ``mlcc.michigan.gov`` failed DNS), so the spec carries
``verified=False`` and is not registered or scheduled.

Probe-recorded columns: ISSUE_DATE, EXPIRATION_DATE, EFFECTIVE_DATE,
ADDRESS_LINE1, CITY, STATE, ZIP_CODE, LICENSE_TYPE, LICENSE_STATUS,
LICENSE_NUMBER, BUSINESS_NAME.

Filter partition: city (Lansing, East Lansing, Flint, Ann Arbor, Grand Rapids,
Detroit).
"""

MICHIGAN_LARA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["license_number", "license_no"],
    "license_type": ["license_type", "license_category"],
    "effective_date": ["issue_date", "effective_date"],
    "expiration_date": ["expiration_date", "exp_date"],
    "premises_name": ["business_name", "licensee_name"],
    "dba": ["business_name", "trade_name"],
    "address_street": ["address_line1", "address"],
    "borough": ["city"],
    "zipcode": ["zip_code", "zip"],
    "status": ["license_status"],
}