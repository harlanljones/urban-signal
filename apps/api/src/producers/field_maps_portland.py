"""Per-feed field maps for Portland, OR (leaf module — do NOT edit shared field_maps.py).

Exports ``FIELD_MAP`` keyed by feed name ("permits" / "sla"). The shared
``resolve_field_map`` reads a city's map off the registered ``DatasetSpec``
["field_map"], so the spine folds these into ``city_registry``'s Portland
``REGISTRY`` entry (it does NOT mutate the shared ``field_maps.py``). Keeping
Portland's maps here means the leaf is testable in isolation and the spine edit
is a single additive import + reference.

Canonical field names match the shared parsers' ``first_mapped`` calls: see
``dob_permits_producer`` (job_id, latitude, longitude, cost, issuance_date,
filing_date, job_type, status, zipcode, borough, address_street, proposed_units,
proposed_stories) and ``sla_licenses_producer`` (license_id, license_type, dba,
premises_name, effective_date, expiration_date, status, address_street,
latitude, longitude, borough).
"""

from src.spatial.cities.portland import (
    PORTLAND_PERMITS_FIELD_MAP,
    PORTLAND_SLA_FIELD_MAP,
)

# Feed-name -> canonical -> [candidate source columns] (matches first_mapped).
FIELD_MAP: dict[str, dict[str, list]] = {
    "permits": PORTLAND_PERMITS_FIELD_MAP,
    "sla": PORTLAND_SLA_FIELD_MAP,
}
