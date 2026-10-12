"""Urban Anchor asset: golden count, closure, containment, and size-class boundaries."""

import h3
import pytest
from shapely.geometry import Point, shape

from src.spatial import urban_anchors as ua
from src.spatial.urban_anchors import (
    ANCHOR_GOLDEN_COUNT,
    UrbanAnchor,
    anchor_cells,
    anchors_intersecting,
    detail_resolution,
    load_anchors,
)

NYC_BBOX = {"min_lat": 40.4, "max_lat": 40.95, "min_lng": -74.3, "max_lng": -73.65}


def _anchor_containing(lat: float, lng: float) -> UrbanAnchor | None:
    point = Point(lng, lat)
    for anchor in load_anchors().values():
        if shape(anchor.geometry).contains(point):
            return anchor
    return None


def test_asset_matches_golden_count_and_is_well_formed():
    anchors = load_anchors()
    assert len(anchors) == ANCHOR_GOLDEN_COUNT
    for anchor in anchors.values():
        assert anchor.geometry["type"] == "MultiPolygon"
        assert anchor.geometry["coordinates"]
        assert anchor.land_km2 > 0
        assert anchor.name


def test_golden_count_drift_fails_loudly(monkeypatch):
    monkeypatch.setattr(ua, "ANCHOR_GOLDEN_COUNT", ANCHOR_GOLDEN_COUNT + 1)
    ua.load_anchors.cache_clear()
    try:
        with pytest.raises(ValueError, match="rebaseline"):
            ua.load_anchors()
    finally:
        monkeypatch.undo()
        ua.load_anchors.cache_clear()


def test_cells_are_hierarchically_closed_with_exact_fanout():
    anchor_id = next(iter(load_anchors()))
    res7, res8, res9 = (anchor_cells(anchor_id, r) for r in (7, 8, 9))
    assert len(res8) == len(res7) * 7
    assert len(res9) == len(res8) * 7
    assert {h3.cell_to_parent(c, 7) for c in res9} == set(res7)
    assert list(res9) == sorted(set(res9))


def test_every_anchor_owns_at_least_one_cell_even_below_one_hex():
    smallest = min(load_anchors().values(), key=lambda a: a.land_km2)
    assert len(anchor_cells(smallest.anchor_id, 7)) >= 1


def test_unsupported_resolution_and_unknown_anchor_are_rejected():
    anchor_id = next(iter(load_anchors()))
    with pytest.raises(ValueError):
        anchor_cells(anchor_id, 6)
    with pytest.raises(KeyError):
        anchor_cells("00000", 7)


def test_times_square_is_covered_and_rural_kansas_is_not():
    nyc = _anchor_containing(40.758, -73.9855)
    assert nyc is not None and "New York" in nyc.name
    assert h3.latlng_to_cell(40.758, -73.9855, 9) in set(anchor_cells(nyc.anchor_id, 9))
    assert _anchor_containing(38.5, -99.5) is None
    kansas_cell = h3.latlng_to_cell(38.5, -99.5, 7)
    assert all(kansas_cell not in anchor_cells(a, 7) for a in anchors_intersecting(
        {"min_lat": 38.4, "max_lat": 38.6, "min_lng": -99.6, "max_lng": -99.4}
    ))


def test_anchors_intersecting_uses_geometry_not_just_bounding_boxes():
    nyc = _anchor_containing(40.758, -73.9855)
    assert nyc.anchor_id in anchors_intersecting(NYC_BBOX)
    assert anchors_intersecting({"min_lat": 38.4, "max_lat": 38.6, "min_lng": -99.6, "max_lng": -99.4}) == ()


@pytest.mark.parametrize(
    ("population", "land_km2", "expected"),
    [
        (ua.LARGE_POPULATION, 1.0, 9),
        (ua.LARGE_POPULATION - 1, 1.0, 8 if ua.LARGE_POPULATION - 1 >= ua.MID_POPULATION else 7),
        (None, ua.LARGE_LAND_KM2, 9),
        (None, ua.LARGE_LAND_KM2 - 0.001, 8),
        (None, ua.MID_LAND_KM2, 8),
        (None, ua.MID_LAND_KM2 - 0.001, 7),
        (ua.MID_POPULATION, 1.0, 8),
        (ua.MID_POPULATION - 1, 1.0, 7),
    ],
)
def test_detail_resolution_class_boundaries(population, land_km2, expected):
    anchor = UrbanAnchor("x", "x", land_km2, population, {"type": "MultiPolygon", "coordinates": []})
    assert detail_resolution(anchor) == expected
