"""City-specific spatial registry modules."""

from src.spatial.cities.chicago import (
    CHICAGO_DIVISION_BBOXES,
    CHICAGO_DIVISIONS,
    CHICAGO_METRO_BBOX,
    CHICAGO_SUBMARKETS,
    is_in_chicago_metro,
)
from src.spatial.cities.san_francisco import (
    SAN_FRANCISCO_DIVISION_BBOXES,
    SAN_FRANCISCO_DIVISIONS,
    SAN_FRANCISCO_METRO_BBOX,
    SAN_FRANCISCO_SUBMARKETS,
    SF_DIVISION_BBOXES,
    SF_DIVISIONS,
    SF_METRO_BBOX,
    SF_SUBMARKETS,
    is_in_san_francisco_metro,
    is_in_sf_metro,
)

__all__ = [
    "CHICAGO_METRO_BBOX",
    "CHICAGO_DIVISION_BBOXES",
    "CHICAGO_DIVISIONS",
    "CHICAGO_SUBMARKETS",
    "is_in_chicago_metro",
    "SF_METRO_BBOX",
    "SAN_FRANCISCO_METRO_BBOX",
    "SF_DIVISION_BBOXES",
    "SAN_FRANCISCO_DIVISION_BBOXES",
    "SF_DIVISIONS",
    "SAN_FRANCISCO_DIVISIONS",
    "SF_SUBMARKETS",
    "SAN_FRANCISCO_SUBMARKETS",
    "is_in_sf_metro",
    "is_in_san_francisco_metro",
]
