"""Unit tests for the Fort Collins, CO leaf (US-421): spatial geometry containment.

Fort Collins registers with live-verified ArcGIS "Current Building Permits"
(services1.arcgis.com/dLpFH5mwVvxSN4OE/.../Building_Permits/FeatureServer/0,
item e0964db1f10c491a872d5d0e7dbbe13a, 2,215 rows, native point geometry).
The southwest-expansion research probe claimed an APPLIED_DATE/ISSUED_DATE
watermark and a richer schema; the live schema carries neither — it is
PERMITNUM/PERMITTYPE/B1_APPL_STATUS/ADDRESS with no date column at all — so
the feed registers as a snapshot pull (watermark_col="") rather than
incremental. This test focuses on the spatial registration contract: metro
bbox sanity, division containment, and submarket placement inside their
declared division bbox.
"""

from src.spatial.cities.fort_collins import (
    FORT_COLLINS_CENTER,
    FORT_COLLINS_CITY_ID,
    FORT_COLLINS_DIVISION_BBOXES,
    FORT_COLLINS_DIVISIONS,
    FORT_COLLINS_METRO_BBOX,
    FORT_COLLINS_SUBMARKETS,
    REGISTRATION,
    is_in_fort_collins_metro,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType, get_dataset


class TestFortCollinsSpatial:
    def test_metro_bbox_sanity(self):
        assert FORT_COLLINS_METRO_BBOX["min_lat"] < FORT_COLLINS_METRO_BBOX["max_lat"]
        assert FORT_COLLINS_METRO_BBOX["min_lng"] < FORT_COLLINS_METRO_BBOX["max_lng"]

    def test_center_sits_inside_metro_bbox(self):
        assert (
            FORT_COLLINS_METRO_BBOX["min_lat"]
            <= FORT_COLLINS_CENTER["lat"]
            <= FORT_COLLINS_METRO_BBOX["max_lat"]
        )
        assert (
            FORT_COLLINS_METRO_BBOX["min_lng"]
            <= FORT_COLLINS_CENTER["lng"]
            <= FORT_COLLINS_METRO_BBOX["max_lng"]
        )

    def test_is_in_fort_collins_metro_rejects_missing_coordinates(self):
        assert is_in_fort_collins_metro(None, None) is False

    def test_is_in_fort_collins_metro_accepts_center(self):
        assert is_in_fort_collins_metro(
            FORT_COLLINS_CENTER["lat"], FORT_COLLINS_CENTER["lng"]
        )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in FORT_COLLINS_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= FORT_COLLINS_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= FORT_COLLINS_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= FORT_COLLINS_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= FORT_COLLINS_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in FORT_COLLINS_SUBMARKETS.items():
            bbox = FORT_COLLINS_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in FORT_COLLINS_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(FORT_COLLINS_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert FORT_COLLINS_CITY_ID == "fort_collins"
        assert REGISTRATION.metro_bbox is FORT_COLLINS_METRO_BBOX
        assert REGISTRATION.submarkets is FORT_COLLINS_SUBMARKETS
        assert 3 <= len(FORT_COLLINS_DIVISIONS) <= 8
        assert 6 <= len(FORT_COLLINS_SUBMARKETS) <= 10


class TestFortCollinsRegistry:
    def test_registered_in_city_id_enum(self):
        assert CityId.FORT_COLLINS.value == "fort_collins"

    def test_registered_in_registry_with_permits_feed(self):
        reg = REGISTRY[CityId.FORT_COLLINS]
        assert reg.name == "Fort Collins, CO"
        assert reg.state == "CO"
        assert FeedType.PERMITS in reg.datasets

    def test_permits_dataset_is_point_geometry_snapshot(self):
        spec = get_dataset(CityId.FORT_COLLINS, FeedType.PERMITS)
        assert "Building_Permits/FeatureServer/0" in spec.endpoint
        assert spec.platform == "arcgis"
        # Live schema carries no date column (PERMITNUM/PERMITTYPE/
        # B1_APPL_STATUS/ADDRESS only) despite the research probe's claimed
        # watermark, so this ingests as a snapshot pull.
        assert spec.watermark_col == ""
        assert spec.ingestion_mode == "snapshot"
        assert spec.needs_geocode is False
        assert "PERMITNUM" in spec.id_keys
