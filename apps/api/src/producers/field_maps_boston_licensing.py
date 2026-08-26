"""Field map for Boston's Licensing Board SLA feed (US-137).

The source CKAN resource (04dc653b-...) carries Massachusetts State Plane
meters in gpsx/gpsy and NO WGS84 columns, so the feed is registered as an
address-only SLA feed under ADR 0004: gpsx/gpsy are intentionally absent from
the map and rows geocode from the business address string at parse time.

The map mirrors ``BOSTON_LICENSING_BOARD_FEED["field_map"]`` in the Boston city
module so the spec stays single-sourced with src/spatial/cities/boston.py.
Imported (not copied) so the orchestrator's spine registration references one
contract.
"""

from src.spatial.cities.boston import BOSTON_LICENSING_BOARD_FEED

FIELD_MAP: dict[str, list[str]] = BOSTON_LICENSING_BOARD_FEED["field_map"]
