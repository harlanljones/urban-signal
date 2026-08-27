"""Typed holder for a city's canonical spatial registration.

Each Metro leaf module in ``src.spatial.cities`` bundles its existing canonical
constants into one ``REGISTRATION`` object of this shape so a later aggregator
(US-177) can derive the hand-written registry's geometry from the modules
instead of the other way around. The registry remains the source of truth for
now; this object only references (never copies) the module's constants.
"""

from typing import Callable, Dict, List

from src.spatial.submarkets import BoroughMeta, SubmarketMeta


def _default_contains(lat: float, lng: float) -> bool:  # pragma: no cover - unused
    raise NotImplementedError


class SpatialRegistration:
    """One canonical spatial registration for a Metro leaf module."""

    __slots__ = (
        "metro_bbox",
        "division_bboxes",
        "submarkets",
        "divisions",
        "contains",
    )

    def __init__(
        self,
        metro_bbox: Dict[str, float],
        division_bboxes: Dict[str, Dict[str, float]],
        submarkets: Dict[str, SubmarketMeta],
        divisions: Dict[str, BoroughMeta],
        contains: Callable[[float, float], bool],
    ) -> None:
        self.metro_bbox = metro_bbox
        self.division_bboxes = division_bboxes
        self.submarkets = submarkets
        self.divisions = divisions
        self.contains = contains
