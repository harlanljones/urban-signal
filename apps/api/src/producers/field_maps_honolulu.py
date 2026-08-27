"""Per-city field maps for Honolulu (US-193), imported by the shared parsers.

Honolulu registers on `data.honolulu.gov` (Socrata) with spellings that the
generic parser chains cannot reach (`request_type`, `date_created`,
`joblocation`, `buildingpermitno`, `tmk`), so its column mappings live here
as a leaf module rather than grown into the shared fallbacks
(`src/producers/field_maps.py`, which stays untouched per the interlock
spine rules).

The shared ``resolve_field_map`` reads ``DatasetSpec["field_map"]``; the
spine registration pins these maps per feed. This module is the single-sourced
export so the registration and the unit test agree on one definition.

Both feeds are address-only. 311 has no coordinate column in the current
rolling-30-day resource; permits `4vab-c87q` is a closed archive (through
2025-06-30) whose schema is still captured here for a live successor.
"""

from typing import Dict, List

from src.spatial.cities.honolulu import (
    HONOLULU_FIELD_MAPS,
    HONOLULU_GEOCODE_CONTEXT,
)

# Single export consumed by the spine registration and the unit test. Keyed by
# FeedType value string so either feed can be wired independently.
FIELD_MAP: Dict[str, Dict[str, List[str]]] = HONOLULU_FIELD_MAPS

# Exposed for the spine's DatasetSpec["geocode_context"] on both feeds.
GEOCODE_CONTEXT: str = HONOLULU_GEOCODE_CONTEXT

__all__ = ["FIELD_MAP", "GEOCODE_CONTEXT"]
