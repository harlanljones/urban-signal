"""Per-city field maps for Orlando SLA feeds (US-194).

Orlando is a PARTIAL metro on ``data.cityoforlando.net`` with two SLA-typed
layers that do **not** share a schema:

* Business Tax Receipts ``7388-4re5`` (primary SLA).
* Short Term Rental Licenses ``ssrj-rbua`` (SLA companion — not a new FeedType).

Both live windows are address-only (ADR 0004). The BTR archive carries a
Socrata ``geocoded_column`` Point that the shared SLA parser does not read;
recent rows omit it. STR has no coordinates at all.

This module is a leaf. The shared ``field_maps.py`` dispatch stays untouched.
Keyed by feed-value strings so the spine can pin ``FIELD_MAP["sla"]`` onto
``FeedType.SLA`` and keep the STR map for the companion endpoint.
"""

from typing import Dict, List

# Canonical SLA field -> BTR column spellings (first non-empty wins).
# No latitude/longitude: the live 60d window is address-only.
SLA_FIELD_MAP: Dict[str, List[str]] = {
    "license_id": ["case_number"],
    "license_type": ["license_type", "license_category"],
    "premises_name": ["business_name"],
    "dba": ["business_name", "business_owner_name"],
    "effective_date": [
        "last_licensed_issue_date",
        "received_date",
        "business_open_date",
    ],
    "status": ["license_status"],
    "address_street": ["business_address"],
    "borough": ["neighborhood_name", "commissioner_district"],
}

# STR licenses register as SLA (US-194). Street-only ``property_address``;
# city/state live on the owner block and are not part of the geocode input
# until ADR-0004 appends geocode_context.
STR_SLA_FIELD_MAP: Dict[str, List[str]] = {
    "license_id": ["license_number"],
    "license_type": ["license_milestone"],
    "premises_name": ["license_holder_name", "property_owner_name1"],
    "dba": ["property_owner_name1", "license_holder_name"],
    "effective_date": ["issued_date", "license_date", "last_action_date"],
    "expiration_date": ["expire_date", "next_renew_date"],
    "status": ["license_status", "license_milestone"],
    "address_street": ["property_address"],
    "zipcode": ["property_owner_zip"],
    "borough": ["property_owner_city"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "sla": SLA_FIELD_MAP,
    "sla_str": STR_SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Orlando, FL"

__all__ = ["FIELD_MAP", "GEOCODE_CONTEXT", "SLA_FIELD_MAP", "STR_SLA_FIELD_MAP"]
