"""Unit tests for the Peoria, IL leaf (US-260).

Containment-only checks: metro bbox sanity, division containment, and
submarket placement inside their declared division bbox. Leaf tests run
without spine registration.
"""

from src.spatial.cities.peoria import (
    PEORIA_DIVISION_BBOXES,
    PEORIA_DIVISIONS,
    PEORIA_METRO_BBOX,
    PEORIA_SUBMARKETS,
    REGISTRATION,
    is_in_peoria_metro,
)


class TestPeoriaSpatial:
    def test_metro_bbox_sanity(self):
        assert PEORIA_METRO_BBOX["min_lat"] < PEORIA_METRO_BBOX["max_lat"]
        assert PEORIA_METRO_BBOX["min_lng"] < PEORIA_METRO_BBOX["max_lng"]

    def test_is_in_peoria_metro_rejects_missing_coordinates(self):
        assert is_in_peoria_metro(None, None) is False

    def test_is_in_peoria_metro_accepts_downtown(self):
        assert is_in_peoria_metro(40.6936, -89.5890) is True

    def test_is_in_peoria_metro_rejects_peoria_arizona(self):
        # US-260 trap: ArcGIS search surfaces a "City of Peoria AZ" layer.
        # Peoria, AZ sits at ~33.58, -112.24 and must not read as in-metro.
        assert is_in_peoria_metro(33.5806, -112.2374) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in PEORIA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= PEORIA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= PEORIA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= PEORIA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= PEORIA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in PEORIA_SUBMARKETS.items():
            bbox = PEORIA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in PEORIA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(PEORIA_SUBMARKETS)

    def test_every_submarket_falls_in_the_recorded_sales_envelope(self):
        # Sampled envelope of the Peoria County residential-sales feed
        # (lat 40.5581..40.9583, lng -89.9726..-89.4817). Submarkets outside it
        # would never receive a deed event.
        for name, meta in PEORIA_SUBMARKETS.items():
            assert 40.55 <= meta.lat <= 40.96, name
            assert -89.98 <= meta.lng <= -89.45, name

    def test_expected_registry_shape(self):
        # Two divisions split by the Illinois River; seven submarkets
        assert len(PEORIA_DIVISIONS) == 2
        assert len(PEORIA_SUBMARKETS) == 7
        assert REGISTRATION.metro_bbox is PEORIA_METRO_BBOX
        assert REGISTRATION.submarkets is PEORIA_SUBMARKETS
