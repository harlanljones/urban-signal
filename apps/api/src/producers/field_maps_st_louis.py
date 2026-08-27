"""Per-city field maps for St. Louis (US-200), imported by the shared parsers.

St. Louis registers three CSV feeds from the City of St. Louis ColdFusion
catalog. Column mappings live here as a leaf module rather than grown into the
shared fallbacks (``src/producers/field_maps.py`` stays untouched per the
interlock spine rules).

CSVClient lowercases headers, so maps prefer the normalized names
(``datetimeinit``, ``requestid``, ``issuedate``, ``case_number``) with the
original title-case spellings as fallbacks.

311 ``SRX``/``SRY`` are EPSG:3857 Web Mercator — they are intentionally
absent from the latitude/longitude slots (Boston-SLA lesson). The city-module
helper ``mercator_xy_to_wgs84`` converts them; wiring that into
``complaints_311_producer.py`` is a later spine hold.
"""

from typing import Dict, List

from src.spatial.cities.st_louis import (
    ST_LOUIS_FIELD_MAPS,
    ST_LOUIS_GEOCODE_CONTEXT,
)

FIELD_MAP: Dict[str, Dict[str, List[str]]] = ST_LOUIS_FIELD_MAPS

GEOCODE_CONTEXT: str = ST_LOUIS_GEOCODE_CONTEXT

__all__ = ["FIELD_MAP", "GEOCODE_CONTEXT"]
