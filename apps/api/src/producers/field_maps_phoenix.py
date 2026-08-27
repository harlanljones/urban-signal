"""Per-city field maps for Phoenix (US-197).

Phoenix is a PARTIAL metro on City of Phoenix ArcGIS Server 11.3:

* PERMITS primary — ``Public/Planning_Permit/MapServer/1`` (daily issued).
  Native point geometry via ``ArcGISClient`` ``outSR=4326``; no ``needs_geocode``.
  ShapePHX ``ShapePHXPermitsPoints_DL`` is a weekly Issued companion with a
  different column set; companion aliases are fallbacks on the same map.
* SLA — ShapePHX Short Term Rentals (STR **is** the SLA, not ``FeedType.STR``
  and not a companion). Native ``LATITUDE``/``LONGITUDE`` plus point geometry.

311, deeds, liquor ``LIQUOR_RACMap`` (no date column), and the frozen
non-``_DL`` ShapePHX permits layer are not registered.

This module is a leaf. The shared ``field_maps.py`` dispatch stays untouched.
Keyed by feed-value strings so the spine can pin ``FIELD_MAP["permits"]`` and
``FIELD_MAP["sla"]`` independently.
"""

from typing import Dict, List

# Planning_Permit layer 1 first; ShapePHX companion spellings as fallbacks so
# a later companion poll can reuse the same map. Do not map companion ``X``/``Y``
# (NAD83) or ``NAD83_X``/``NAD83_Y`` as WGS84 — geometry (or STR lat/lng) is
# the coordinate path.
PERMITS_FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["PER_NUM", "PERMIT_NUMBER", "PID", "OBJECTID"],
    "issuance_date": ["PER_ISSUE_DATE", "PERMIT_ISSUE_DATE"],
    "filing_date": ["PER_ENT_DATE"],
    "status": ["PERMIT_STAT", "STATUS"],
    "job_type": [
        "PER_TYPE_DESC",
        "SCOPE_DESC",
        "PER_TYPE",
        "PERMIT_TYPE",
        "PERMIT_NAME",
    ],
    "address_street": ["STREET_FULL_NAME", "ADDRESS"],
}

# ShapePHX STR operating permits. ``PROPERTY_ADDRESS`` carries a trailing
# `` (Active)`` suffix; leave it on the mapped street (native coords, so the
# ADR-0004 address path is unused). ``POW_NAME`` is the property-owner label.
SLA_FIELD_MAP: Dict[str, List[str]] = {
    "license_id": ["NAME", "ID", "OBJECTID"],
    "license_type": ["REGISTRATION_TYPE"],
    "premises_name": ["POW_NAME", "POW_COMPANY_NAME"],
    "dba": ["POW_NAME", "POW_COMPANY_NAME"],
    "effective_date": ["ISSUED_DATE"],
    "expiration_date": ["EXPIRATION_DATE"],
    "status": ["STATUS"],
    "latitude": ["LATITUDE"],
    "longitude": ["LONGITUDE"],
    "address_street": ["PROPERTY_ADDRESS"],
    "zipcode": ["PROPERTY_ZIP"],
    "borough": ["PROPERTY_CITY_STATE"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Phoenix, AZ"

__all__ = [
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]
