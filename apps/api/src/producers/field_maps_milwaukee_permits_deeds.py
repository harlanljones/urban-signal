"""Milwaukee PERMITS + DEEDS field maps and feed specs (US-138 leaf).

Imports the canonical field maps from :mod:`src.spatial.cities.milwaukee` so
the single source of truth for Milwaukee's PERMITS/DEEDS column spellings stays
in the city module; this module re-exports them keyed by :class:`FeedType` for
the spine and for the contract tests.

This module does NOT edit the shared ``src/producers/field_maps.py`` — Milwaukee
parsing falls back to the generic chains for every column not named in
``FIELD_MAP``.
"""

from typing import Dict, List

from src.spatial.city_registry import FeedType
from src.spatial.cities.milwaukee import (
    MILWAUKEE_DEEDS_FIELD_MAP,
    MILWAUKEE_DEEDS_SPEC,
    MILWAUKEE_PERMITS_FIELD_MAP,
    MILWAUKEE_PERMITS_SPEC,
)

# Canonical field maps for the two new Milwaukee feeds, keyed by FeedType so the
# spine can embed them as `DatasetSpec["field_map"]` verbatim.
FIELD_MAP: Dict[FeedType, Dict[str, List[str]]] = {
    FeedType.PERMITS: MILWAUKEE_PERMITS_FIELD_MAP,
    FeedType.DEEDS: MILWAUKEE_DEEDS_FIELD_MAP,
}
