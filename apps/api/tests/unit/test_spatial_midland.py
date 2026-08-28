from src.spatial.cities.midland import (
    MIDLAND_DIVISION_BBOXES,
    MIDLAND_METRO_BBOX,
    MIDLAND_SUBMARKETS,
    is_in_midland_metro,
)


def _bbox_contains(outer: dict, inner: dict) -> bool:
    return (
        outer["min_lat"] <= inner["min_lat"]
        and inner["max_lat"] <= outer["max_lat"]
        and outer["min_lng"] <= inner["min_lng"]
        and inner["max_lng"] <= outer["max_lng"]
    )


def _point_inside(bbox: dict, lat: float, lng: float) -> bool:
    return bbox["min_lat"] <= lat <= bbox["max_lat"] and bbox["min_lng"] <= lng <= bbox["max_lng"]


class TestMidlandContainment:
    def test_center_inside_bbox(self):
        # Downtown Midland approx center should be inside
        assert is_in_midland_metro(31.9970, -102.0780)

    def test_divisions_inside_metro(self):
        for name, bbox in MIDLAND_DIVISION_BBOXES.items():
            assert _bbox_contains(MIDLAND_METRO_BBOX, bbox), f"division {name} escapes metro bbox"

    def test_submarkets_inside_own_division(self):
        for name, meta in MIDLAND_SUBMARKETS.items():
            bbox = MIDLAND_DIVISION_BBOXES[meta.borough]
            assert _point_inside(bbox, meta.lat, meta.lng), f"submarket {name} outside {meta.borough} bbox"

