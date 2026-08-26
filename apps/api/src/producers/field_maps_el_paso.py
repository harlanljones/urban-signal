"""Per-city field map for El Paso, TX 311 ingestion.

El Paso's Accela/Cityworks 311 layer spells its columns differently from the
shared 311 parser chains, so the spellings are declared here as data (the
ADR-0001-adjacent Wave-B mechanism) rather than grown into the shared
fallback chains in ``src/producers/complaints_311_producer.py``. The shared
producer resolves this map via ``resolve_field_map("el_paso",
FeedType.COMPLAINTS_311)`` once the city is registered; until then it degrades
to ``{}`` and rows parse through the bare chains.

This is a leaf module: it imports only from the sibling city geometry module
and never touches the spine ``src/producers/field_maps.py``.
"""

from src.spatial.cities.el_paso import EL_PASO_METRO_BBOX  # noqa: F401  (city context anchor)

# Canonical 311 fields -> ordered list of source-column candidates for El Paso.
# Order matters: the first present, truthy key wins (see
# ``src/producers/field_maps.first_mapped``).
FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["id", "request_id", "OBJECTID"],
    "created_date": ["created_at"],
    "status": ["status"],
    "complaint_type": ["request_type", "request_category"],
    "incident_address": ["address"],
    "borough": ["district"],
}
