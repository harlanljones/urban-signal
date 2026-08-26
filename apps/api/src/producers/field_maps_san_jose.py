"""Per-city field maps for San Jose (US-147), imported by the shared parsers.

San Jose registers on **SanGIS Socrata Open Data** with spellings that the
generic parser chains cannot reach, so its column mappings live here as a leaf
module rather than grown into the shared fallbacks (src/producers/field_maps.py,
which stays untouched per the interlock spine rules).

The shared ``resolve_field_map`` reads ``DatasetSpec.extra["field_map"]``; the
spine registration pins these maps per feed. This module is the single-sourced
export so the registration and the unit test agree on one definition.

The 311 feed is address-string-located for a meaningful share of rows (its
``Y_COORD``/``X_COORD`` columns are absent / 0.0 / 0.0 on many rows), so the
spine additionally declares ``needs_geocode`` (ADR 0004) against this map's
``incident_address`` candidate.
"""

from typing import Dict, List

from src.spatial.cities.san_jose import (
    SAN_JOSE_FIELD_MAPS,
    SAN_JOSE_GEOCODE_CONTEXT,
)

# Single export consumed by the spine registration and the unit test. Keyed by
# FeedType value string so either feed can be wired independently.
FIELD_MAP: Dict[str, Dict[str, List[str]]] = SAN_JOSE_FIELD_MAPS

# Exposed for the spine's DatasetSpec.extra["geocode_context"] on the 311 feed.
GEOCODE_CONTEXT: str = SAN_JOSE_GEOCODE_CONTEXT

__all__ = ["FIELD_MAP", "GEOCODE_CONTEXT"]
