"""Per-city field maps for Topeka, KS (US-426), imported by the shared parsers.

Topeka is a ONE-FEED PARTIAL metro on the City of Topeka's ArcGIS server
(``maps.topeka.gov``): PERMITS — ``CityworksViews/BuildingPermits``
MapServer/0 (Commercial Building Permit, 4,180 rows).
"""

PERMITS_FIELD_MAP = {
    "job_id": ["case_number", "OBJECTID"],
    "issuance_date": ["date_issued"],
    "filing_date": ["date_entered"],
    "status": ["case_status"],
    "job_type": ["case_type", "case_type_desc"],
    "address_street": ["location"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT = "Topeka, KS"

DROPPED_PII_COLUMNS = ()

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]