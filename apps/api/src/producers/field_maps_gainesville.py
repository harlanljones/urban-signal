"""Per-city field-mapping support for Gainesville (leaf module).

Gainesville's Socrata permits dataset `p798-x3nx` exposes native latitude/longitude
and a `location_1` point object, plus `permit` (id), `issue` (issuance date), and
`address` (street). The shared parser chains already cover common Socrata keys; this
map pins exact spellings so parser dispatch is stable across cities.
"""

from typing import Dict, List

FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["permit"],
    "issuance_date": ["issue"],
    "address_street": ["address"],
    "latitude": ["latitude", "location_1.latitude"],
    "longitude": ["longitude", "location_1.longitude"],
    "status": ["status"],
}


def city_id() -> str:
    """Return the canonical Gainesville city id this field map belongs to."""
    from src.spatial.cities.gainesville import GAINESVILLE_CITY_ID

    return GAINESVILLE_CITY_ID

