"""Contract tests for declarative city definitions (US-386)."""

import pytest

from src.spatial.city_data import aliases_from_definitions, build_registration, validate_definition
from src.spatial.city_registry import CityId, FeedType
from src.spatial import registry_derivation


DEMO = {
    "city_id": "nyc",
    "name": "New York",
    "state": "NY",
    "center": {"lat": 40.7, "lng": -74.0},
    "metro_bbox": {"min_lat": 40.4, "max_lat": 41.0, "min_lng": -74.4, "max_lng": -73.5},
    "division_bboxes": {},
    "submarkets": {},
    "divisions": {},
    "datasets": {
        "permits": {
            "endpoint_setting": "socrata_dob_endpoint",
            "platform": "socrata",
            "watermark_col": "updated_at",
            "topic": "raw.municipal.permits",
            "producer_key": "permits",
        }
    },
    "aliases": ["new york city"],
    "job_suffix": "nyc",
}


def test_definition_normalizes_geometry_and_rejects_missing_fields():
    normalized = validate_definition(DEMO)
    assert normalized["center"] == {"lat": 40.7, "lng": -74.0}
    with pytest.raises(ValueError, match="missing fields"):
        validate_definition({"city_id": "broken"})


def test_definition_builds_existing_runtime_objects_and_resolves_settings():
    registration = build_registration(
        DEMO,
        city_id_type=CityId,
        feed_type=FeedType,
        endpoint_resolver=lambda name: {"socrata_dob_endpoint": "https://example.test/dob"}[name],
    )
    assert registration.city_id is CityId.NYC
    assert registration.datasets[FeedType.PERMITS].endpoint == "https://example.test/dob"


def test_registry_factory_accepts_a_demo_city_without_city_registry_edits():
    registry = registry_derivation.build_registry_from_data(
        [{**DEMO, "city_id": "chicago", "aliases": []}]
    )
    assert set(registry) == {CityId.CHICAGO}
    assert registry[CityId.CHICAGO].datasets[FeedType.PERMITS].producer_key == "permits"


def test_aliases_are_normalized_and_collisions_are_rejected():
    assert aliases_from_definitions([DEMO], CityId)["new york city"] is CityId.NYC
    other = {**DEMO, "city_id": "chicago", "aliases": ["new york city"]}
    with pytest.raises(ValueError, match="both"):
        aliases_from_definitions([DEMO, other], CityId)
