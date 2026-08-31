"""Contract tests for declarative city definitions (US-386)."""

import shutil
from pathlib import Path

import pytest
import yaml

from src.spatial import city_data, registry_derivation
from src.spatial.city_data import aliases_from_definitions, build_registration, validate_definition
from src.spatial.city_registry import CityId, FeedType

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


def test_registry_factory_rejects_unsupported_city_as_one_atomic_build():
    unsupported = {**DEMO, "city_id": "atlantis", "aliases": []}

    with pytest.raises(ValueError, match="unknown city_id"):
        registry_derivation.build_registry_from_data([DEMO, unsupported])


def test_data_only_runtime_rejects_unsupported_city_id(monkeypatch):
    """US-428: the corpus is the single construction path — an unknown CityId
    is a loud failure, not a silent None fallback."""
    unsupported = {**DEMO, "city_id": "atlantis", "aliases": []}
    monkeypatch.setattr(
        city_data, "load_definitions", lambda directory, allow_unknown_city_ids=False: [DEMO, unsupported]
    )

    with pytest.raises(ValueError, match="unknown city_id"):
        registry_derivation.build_runtime_exports()


def test_temporary_corpus_accepts_all_existing_cities_plus_data_only_city(
    monkeypatch, tmp_path: Path
):
    for source in city_data.DATA_DIR.glob("*.yaml"):
        if source.name.startswith("_"):
            continue
        shutil.copy2(source, tmp_path / source.name)
    # The declarative corpus does not yet cover every CityId, and
    # build_runtime_exports refuses to take over unless it covers the whole
    # handwritten registry.  Stub the stragglers so this test exercises the
    # unknown-city_id path rather than the corpus gap.
    for city_id in sorted(
        {city.value for city in CityId} - {p.stem for p in tmp_path.glob("*.yaml")}
    ):
        (tmp_path / f"{city_id}.yaml").write_text(
            yaml.safe_dump({**DEMO, "city_id": city_id, "aliases": [f"{city_id} stub"]}),
            encoding="utf-8",
        )
    (tmp_path / "atlantis.yaml").write_text(
        yaml.safe_dump({**DEMO, "city_id": "atlantis", "aliases": ["atlantis"]}),
        encoding="utf-8",
    )
    monkeypatch.setattr("src.config.settings.city_data_dir", str(tmp_path))

    exports = registry_derivation.build_runtime_exports(allow_unknown_city_ids=True)

    assert exports is not None
    registry, aliases = exports
    assert set(CityId).issubset(registry)
    assert registry["atlantis"].city_id == "atlantis"
    assert aliases["atlantis"] == "atlantis"


def test_unknown_feed_keys_remain_string_compatible():
    definition = {**DEMO, "datasets": {"new_signal": DEMO["datasets"]["permits"]}}

    registration = build_registration(
        definition,
        city_id_type=CityId,
        feed_type=FeedType,
    )

    feed = next(iter(registration.datasets))
    assert feed == "new_signal"
    assert feed.value == "new_signal"


def test_aliases_are_normalized_and_collisions_are_rejected():
    assert aliases_from_definitions([DEMO], CityId)["new york city"] is CityId.NYC
    other = {**DEMO, "city_id": "chicago", "aliases": ["new york city"]}
    with pytest.raises(ValueError, match="both"):
        aliases_from_definitions([DEMO, other], CityId)
