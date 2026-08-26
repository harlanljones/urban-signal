"""Louisville / Kentucky per-city field-map support (leaf module, US-148).

Louisville's two feeds — Louisville Metro 311 service requests and the Kentucky
Alcoholic Beverage Control liquor-license feed — spell their columns
differently from the shared municipal row parsers. This module exports the
canonical ``FIELD_MAP`` (one entry per registered feed, keyed by the
``FeedType`` string) so the interlock spine can fold each sub-map into the
matching ``DatasetSpec.extra["field_map"]`` in ``city_registry.py``.

The shared parsers consult the map BEFORE their generic fallback chains, so the
maps are purely additive overrides. Value semantics match the chains exactly:
falsy values fall through to the next candidate.

This module imports the spellings from the city module
(``src.spatial.cities.louisville``) so the field map and the spatial registry
share a single source of truth for the city.
"""

from src.spatial.cities.louisville import LOUISVILLE_FIELD_MAPS

# Keyed by FeedType string ("COMPLAINTS_311", "SLA") -> {canonical: [candidates]}.
FIELD_MAP: dict[str, dict[str, list[str]]] = LOUISVILLE_FIELD_MAPS
