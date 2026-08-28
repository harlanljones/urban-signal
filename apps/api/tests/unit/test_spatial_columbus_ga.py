"""Containment tests for Columbus, GA spatial registry."""

from src.spatial.cities.columbus_ga import (
    COLUMBUS_GA_CENTER,
    COLUMBUS_GA_DIVISION_BBOXES,
    COLUMBUS_GA_DIVISIONS,
    COLUMBUS_GA_METRO_BBOX,
    COLUMBUS_GA_SUBMARKETS,
    REGISTRATION,
    is_in_columbus_ga_metro,
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


class TestColumbusGASpatial:
    def test_center_inside_metro(self):
        assert is_in_columbus_ga_metro(COLUMBUS_GA_CENTER["lat"], COLUMBUS_GA_CENTER["lng"])

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in COLUMBUS_GA_DIVISION_BBOXES.items():
            assert _bbox_contains(COLUMBUS_GA_METRO_BBOX, bbox), name

    def test_every_submarket_inside_its_division(self):
        for name, meta in COLUMBUS_GA_SUBMARKETS.items():
            bbox = COLUMBUS_GA_DIVISION_BBOXES[meta.borough]
            assert _point_inside(bbox, meta.lat, meta.lng), name

    def test_every_submarket_listed_exactly_once(self):
        listed = [s for d in COLUMBUS_GA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(listed) == sorted(COLUMBUS_GA_SUBMARKETS)

    def test_registration_bundles_leaf_constants(self):
        assert REGISTRATION.metro_bbox is COLUMBUS_GA_METRO_BBOX
        assert REGISTRATION.submarkets is COLUMBUS_GA_SUBMARKETS
        assert REGISTRATION.divisions is COLUMBUS_GA_DIVISIONS

