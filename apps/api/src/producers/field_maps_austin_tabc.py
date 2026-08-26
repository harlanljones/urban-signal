"""Per-city field map for Austin's TABC liquor-license (SLA) feed.

This is a LEAF module — it is NOT imported by the shared producers at runtime.
In production the field map below is merged into the Austin ``CityRegistration``
``datasets[FeedType.SLA].extra["field_map"]`` entry in
``src/spatial/city_registry.py`` (the spine) when the orchestrator applies the
interlock. The registry is the single source of truth; this file exists so the
leaf can (a) prove the proposed spellings resolve through the unmodified
``sla_licenses_producer`` and (b) hand the spine a copy-pasteable map.

Source of column spellings: live data.texas.gov view ``7hf9-qc9f``
("TABC License Information", pulled 2026-08-26). That dataset locates a license
with a STREET ``address`` string (no latitude/longitude columns), so the feed
registers with ``needs_geocode: True`` and resolves coordinates via the ADR 0004
Postgres-replay geocoder at parse time (see ``src/spatial/geocoder.py``).

Keyed by the FeedType *value* string ("sla") rather than the enum, so this data
module can be imported by ``src/spatial/cities/austin.py`` without creating a
circular import through ``city_registry`` (which in turn imports austin).
"""

from typing import Dict, List

# Canonical SLA field -> ordered TABC column spellings (first non-empty wins).
# Mirrors the canonical field names the shared sla_licenses_producer reads via
# first_mapped(): license_id, license_type, effective_date, expiration_date,
# premises_name, dba, address_street, status. latitude/longitude are intentionally
# absent — they carry no geocode columns and are recovered by geocoding the
# address below.
TABC_SLA_FIELD_MAP: Dict[str, List[str]] = {
    "license_id": ["license_id"],
    "license_type": ["license_type"],
    "effective_date": ["current_issued_date"],
    "expiration_date": ["expiration_date"],
    "premises_name": ["owner"],
    "dba": ["trade_name"],
    "address_street": ["address"],
    "status": ["license_status"],
}

# Outer map keyed by FeedType value, so an orchestrator can merge it directly
# into the central registry with `FeedType(key)`.
FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "sla": TABC_SLA_FIELD_MAP,
}
