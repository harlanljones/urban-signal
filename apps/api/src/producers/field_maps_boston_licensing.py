"""Field map for Boston's Licensing Board SLA feed (US-137).

The source CKAN resource (04dc653b-...) carries Massachusetts State Plane
US survey feet in gpsx/gpsy and no WGS84 columns. Path A transforms those
columns from EPSG:2249 to WGS84 in the SLA producer.

The map mirrors ``BOSTON_LICENSING_BOARD_FEED["field_map"]`` in the Boston city
module so the spec stays single-sourced with src/spatial/cities/boston.py.
Imported (not copied) so the orchestrator's spine registration references one
contract.
"""

from src.spatial.cities.boston import BOSTON_LICENSING_BOARD_FEED

FIELD_MAP: dict[str, list[str]] = BOSTON_LICENSING_BOARD_FEED["field_map"]
