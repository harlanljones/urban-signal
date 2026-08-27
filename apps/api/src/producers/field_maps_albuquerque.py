"""Per-city field maps for Albuquerque (US-205), imported by the shared parsers.

Albuquerque is a PARTIAL metro on the daily CABQ building-permits CSV dump.
CSVClient lowercases headers via ``_normalize_header`` (``IssueDate`` →
``issuedate``), so every candidate list carries BOTH the original catalog
spelling and the normalized form. Shared ``field_maps.py`` stays untouched.

Address is split across ``SiteNumber`` / ``SiteStreet`` / ``SiteStreetType`` /
``SiteStreetDirectional`` + ``SiteZip``. ``first_mapped`` returns the first
non-empty candidate, so a raw CSV row yields only the house number; the leaf
``compose_permit_address`` helper joins the parts. The spine producer must
call that helper (or equivalent) before geocoding — otherwise
``geocode_row_if_declared`` drops the row (address length < 6).
"""

from typing import Dict, List

# Canonical permit field -> CABQ CSV column spellings (original + normalized).
# No latitude/longitude: the dump is address-only (ADR 0004).
ALBUQUERQUE_PERMITS_FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["ApplicationPermitNumber", "applicationpermitnumber"],
    "issuance_date": ["IssueDate", "issuedate"],
    "job_type": ["TypeofWork", "typeofwork"],
    "cost": ["PlanCheckValuation", "plancheckvaluation"],
    "proposed_units": ["NumberOfUnits", "numberofunits"],
    "status": ["Status", "status"],
    # ``address_street`` is the composed slot tests / the spine producer fill.
    # Raw part keys follow so first_mapped still resolves on either spelling.
    "address_street": [
        "address_street",
        "SiteNumber",
        "sitenumber",
        "SiteStreet",
        "sitestreet",
        "SiteStreetType",
        "sitestreettype",
        "SiteStreetDirectional",
        "sitestreetdirectional",
    ],
    "zipcode": ["SiteZip", "sitezip"],
}

ALBUQUERQUE_GEOCODE_CONTEXT = "Albuquerque, NM"

# Single dispatch surface consumed by the spine DatasetSpec["field_map"].
# Keyed by FeedType value string so a later 311/SLA map can land independently.
ALBUQUERQUE_FIELD_MAPS: Dict[str, Dict[str, List[str]]] = {
    "permits": ALBUQUERQUE_PERMITS_FIELD_MAP,
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = ALBUQUERQUE_FIELD_MAPS
GEOCODE_CONTEXT: str = ALBUQUERQUE_GEOCODE_CONTEXT

__all__ = [
    "ALBUQUERQUE_FIELD_MAPS",
    "ALBUQUERQUE_GEOCODE_CONTEXT",
    "ALBUQUERQUE_PERMITS_FIELD_MAP",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
]
