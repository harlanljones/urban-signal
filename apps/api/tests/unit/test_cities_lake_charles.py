"""Leaf-only containment tests for Lake Charles, LA geometry.

Verifies:
- every division bbox nests inside the metro bbox
-,and every submarket centroid lies inside its listed division bbox.
"""

from typing import Dict

from src.spatial.cities.lake_charles import (
    LAKE_CHARLES_DIVISION_BBOXES,
    LAKE_CHARLES_METRO_BBOX,
    LAKE_CHARLES_SUBMARKETS,
    is_in_lake_charles_metro,
)


def _bbox_contains(outer: Dict[str, float], inner: Dict[str, float]) -> bool:
    return (
        outer["min_lat"] <= inner["min_lat"] <= inner["max_lat"] <= outer["max_lat"]
        and outer["min_lng"] <= inner["min_lng"] <= inner["max_lng"] <= outer["max_lng"]
    )


def _point_inside(bbox: Dict[str, float], lat: float, lng: float) -> bool:
    return (
        bbox["min_lat"] <= lat <= bbox["max_lat"]
        and bbox["min_lng"] <= lng <= bbox["max_lng"]
    )


def test_divisions_inside_metro_bbox():
    for name, bbox in LAKE_CHARLES_DIVISION_BBOXES.items():
        assert _bbox_contains(LAKE_CHARLES_METRO_BBOX, bbox), f"division {name} escapes metro bbox"


def test_submarkets_inside_own_division_bbox():
    for name, meta in LAKE_CHARLES_SUBMARKETS.items():
        bbox = LAKE_CHARLES_DIVISION_BBOXES[meta.borough]
        assert _point_inside(bbox, meta.lat, meta.lng), f"submarket {name} escapes {meta.borough}"


def test_center_point_is_inside_metro_bbox():
    # Downtown centroid should be considered inside the metro bbox
    downtown = LAKE_CHARLES_SUBMARKETS["Downtown Lake Charles & Lakefront"]
    assert is_in_lake_charles_metro(downtown.lat, downtown.lng)

