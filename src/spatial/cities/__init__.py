"""City-specific spatial registry modules."""

from src.spatial.cities.chicago import (
    CHICAGO_DIVISION_BBOXES,
    CHICAGO_DIVISIONS,
    CHICAGO_METRO_BBOX,
    CHICAGO_SUBMARKETS,
    is_in_chicago_metro,
)
from src.spatial.cities.los_angeles import (
    LA_DIVISION_BBOXES,
    LA_DIVISIONS,
    LA_METRO_BBOX,
    LA_SUBMARKETS,
    is_in_la_metro,
    is_in_los_angeles_metro,
)
from src.spatial.cities.new_orleans import (
    NEW_ORLEANS_METRO_BBOX,
    NOLA_DIVISION_BBOXES,
    NOLA_DIVISIONS,
    NOLA_SUBMARKETS,
    is_in_new_orleans_metro,
)
from src.spatial.cities.norfolk import (
    NORFOLK_DIVISION_BBOXES,
    NORFOLK_DIVISIONS,
    NORFOLK_METRO_BBOX,
    NORFOLK_SUBMARKETS,
    is_in_norfolk_metro,
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
from src.spatial.cities.seattle import (
    SEATTLE_DIVISION_BBOXES,
    SEATTLE_DIVISIONS,
    SEATTLE_METRO_BBOX,
    SEATTLE_SUBMARKETS,
    is_in_seattle_metro,
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
    "SEATTLE_METRO_BBOX",
    "SEATTLE_DIVISION_BBOXES",
    "SEATTLE_DIVISIONS",
    "SEATTLE_SUBMARKETS",
    "is_in_seattle_metro",
    "LA_METRO_BBOX",
    "LA_DIVISION_BBOXES",
    "LA_DIVISIONS",
    "LA_SUBMARKETS",
    "is_in_la_metro",
    "is_in_los_angeles_metro",
    "NEW_ORLEANS_METRO_BBOX",
    "NOLA_DIVISION_BBOXES",
    "NOLA_DIVISIONS",
    "NOLA_SUBMARKETS",
    "is_in_new_orleans_metro",
    "NORFOLK_METRO_BBOX",
    "NORFOLK_DIVISION_BBOXES",
    "NORFOLK_DIVISIONS",
    "NORFOLK_SUBMARKETS",
    "is_in_norfolk_metro",
]
