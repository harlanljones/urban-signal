"""Unit tests for the Lakeland registration (US-286) and its leaf wiring.

Leaf-only: imports the lakeland module directly and never touches the spine
REGISTRY. Ensures containment and a minimally-complete permits spec.
"""

from src.spatial.cities.lakeland import (
    LAKELAND_DIVISION_BBOXES,
    LAKELAND_DIVISIONS,
    LAKELAND_METRO_BBOX,
    LAKELAND_SUBMARKETS,
    get_lakeland_dataset,
    is_in_lakeland_metro,
)
from src.spatial.city_registry import FeedType


class TestLakelandRegistration:
    def test_center_inside_metro_bbox(self):
        # Downtown Lakeland near Munn Park
        assert is_in_lakeland_metro(28.0395, -81.9498)

    def test_is_in_lakeland_metro_rejects_missing_coordinates(self):
        assert is_in_lakeland_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in LAKELAND_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= LAKELAND_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= LAKELAND_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= LAKELAND_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= LAKELAND_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in LAKELAND_SUBMARKETS.items():
            bbox = LAKELAND_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in LAKELAND_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(LAKELAND_SUBMARKETS)

    def test_submarkets_carry_the_lakeland_city_id(self):
        assert {m.city_id for m in LAKELAND_SUBMARKETS.values()} == {"lakeland"}


class TestFeedRegistration:
    """Lakeland registers a verified ArcGIS permits feed; SLA falls back to SNAP in the spine."""

    def test_permits_spec_minimal_shape(self):
        spec = get_lakeland_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.producer_key == "permits"
        # For ArcGIS feeds, oid_field must be declared
        assert spec.oid_field is not None
        assert spec.interval_seconds > 0

