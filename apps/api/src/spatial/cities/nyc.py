"""NYC canonical spatial registration (US-176).

NYC's geometry lives in ``src.spatial.submarkets`` (not a cities leaf module),
so this module is a thin, identity-preserving bridge: it re-exports the exact
NYC objects from ``submarkets`` and binds them into the standard
``REGISTRATION`` shape used by every other Metro leaf.

Object identity is load-bearing: ``submarkets.NYC_METRO_BBOX is
REGISTRY[CityId.NYC].metro_bbox`` is an interlock invariant, so this module
references the same objects rather than copying them. ``NYC_DIVISION_BBOXES``
and ``NYC_DIVISIONS`` are declared as alias names of the borough objects so the
canonical leaf-constant scheme (US-175) holds for NYC as well.
"""

from src.spatial.geo_utils import is_in_nyc_metro
from src.spatial.registration import SpatialRegistration
from src.spatial.submarkets import (
    NYC_BOROUGHS,
    NYC_BOROUGH_BBOXES,
    NYC_METRO_BBOX,
    NYC_SUBMARKETS,
)

# Canonical leaf-constant names (US-175). These alias the borough objects that
# the registry actually uses, so identity with the registry is preserved.
NYC_DIVISION_BBOXES = NYC_BOROUGH_BBOXES
NYC_DIVISIONS = NYC_BOROUGHS

REGISTRATION = SpatialRegistration(
    metro_bbox=NYC_METRO_BBOX,
    division_bboxes=NYC_DIVISION_BBOXES,
    submarkets=NYC_SUBMARKETS,
    divisions=NYC_DIVISIONS,
    contains=is_in_nyc_metro,
)
