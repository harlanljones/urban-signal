"""US-363 §1.3 — Foursquare release-delta POI churn.

Network-free. The delta and places schemas are taken verbatim from
Foursquare's public schema documentation (fetched 2026-08-28); the release
listing fixture mirrors the live Hugging Face repo layout, which is public
even though the partitions themselves are gated.
"""

from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.producers.poi_diff_producer import (
    ACTION_ADD,
    ACTION_MERGE,
    ACTION_REMOVE,
    ACTION_UPDATE,
    DISQUALIFYING_FLAGS,
    NON_COMMERCIAL_CATEGORY_IDS,
    POI_CLOSED,
    POI_OPENED,
    PoiDiffProducer,
    PoiSourceError,
    Release,
    category_of,
    classify,
    parse_releases,
    select_latest_release,
)
from src.spatial.national_feeds import NationalFeed, get_national_feed

# Mirrors the live repo listing (21 releases; latest dt=2026-08-11 with 10
# delta partitions).
SIBLINGS = [
    ".gitattributes",
    "NOTICE.txt",
    "README.md",
    "release/dt=2026-07-09/places/parquet/places-00000.zstd.parquet",
    "release/dt=2026-07-09/deltas/parquet/deltas-00000.zstd.parquet",
    "release/dt=2026-07-09/categories/parquet/categories.zstd.parquet",
    "release/dt=2026-08-11/places/parquet/places-00000.zstd.parquet",
    "release/dt=2026-08-11/places/parquet/places-00001.zstd.parquet",
    "release/dt=2026-08-11/deltas/parquet/deltas-00000.zstd.parquet",
    "release/dt=2026-08-11/deltas/parquet/deltas-00001.zstd.parquet",
    "release/dt=2026-08-11/categories/parquet/categories.zstd.parquet",
    # The very first release has no deltas: nothing precedes it to diff.
    "release/dt=2024-12-03/places/parquet/places-00000.zstd.parquet",
]

RELEASE = Release(
    release_id="2026-08-11",
    delta_paths=["release/dt=2026-08-11/deltas/parquet/deltas-00000.zstd.parquet"],
    place_paths=["release/dt=2026-08-11/places/parquet/places-00000.zstd.parquet"],
    category_paths=[],
)


def row(**overrides):
    base = {
        "fsq_place_id": "4b0588f3f964a52012a022e3",
        "action": ACTION_ADD,
        "redirect": None,
        "name": "Corner Bistro",
        "latitude": 40.7387,
        "longitude": -74.0021,
        "address": "331 W 4th St",
        "locality": "New York",
        "region": "NY",
        "postcode": "10014",
        "date_closed": None,
        "fsq_category_ids": ["4bf58dd8d48988d116941735"],
        "fsq_category_labels": ["Dining and Drinking > Bar"],
        "unresolved_flags": [],
    }
    base.update(overrides)
    return base


@pytest.fixture
def producer():
    p = PoiDiffProducer.__new__(PoiDiffProducer)
    from src.config import settings
    from src.spatial.geography_crosswalk import default_crosswalk
    from src.spatial.h3_indexer import H3SpatialIndexer

    p.settings = settings
    p.producer = MagicMock()
    p.socrata = MagicMock()
    p.hf_parquet = p
    p.spatial_indexer = H3SpatialIndexer()
    p.strict_licensing = False
    p._crosswalk = default_crosswalk()
    return p


class TestReleaseDiscovery:
    def test_listing_groups_into_releases(self):
        releases = parse_releases(SIBLINGS)
        assert set(releases) == {"2024-12-03", "2026-07-09", "2026-08-11"}
        assert len(releases["2026-08-11"].delta_paths) == 2
        assert len(releases["2026-08-11"].place_paths) == 2

    def test_non_parquet_files_are_ignored(self):
        releases = parse_releases(SIBLINGS)
        for release in releases.values():
            for path in release.delta_paths + release.place_paths:
                assert path.endswith(".parquet")

    def test_latest_release_wins(self):
        latest = select_latest_release(parse_releases(SIBLINGS))
        assert latest.release_id == "2026-08-11"
        assert latest.release_date == date(2026, 8, 11)

    def test_already_processed_release_is_not_reprocessed(self):
        assert select_latest_release(parse_releases(SIBLINGS), after="2026-08-11") is None

    def test_only_newer_releases_are_selected(self):
        latest = select_latest_release(parse_releases(SIBLINGS), after="2026-07-09")
        assert latest.release_id == "2026-08-11"

    def test_a_release_without_deltas_is_skipped_not_treated_as_quiet(self):
        # The first release in the repo has no predecessor to diff against.
        # Treating it as "no churn" would silently publish a month of nothing.
        releases = parse_releases(
            ["release/dt=2024-12-03/places/parquet/places-00000.zstd.parquet"]
        )
        assert select_latest_release(releases) is None


class TestClassification:
    def test_add_is_an_opening(self):
        assert classify(ACTION_ADD) == (POI_OPENED, 1.0)

    def test_remove_is_a_closing(self):
        event_type, confidence = classify(ACTION_REMOVE)
        assert event_type == POI_CLOSED and confidence == pytest.approx(0.9)

    def test_merge_with_a_survivor_is_low_confidence(self):
        # A merge is a database operation — one record absorbed into another —
        # and only sometimes a real closing.
        event_type, confidence = classify(ACTION_MERGE, redirect="other-id")
        assert event_type == POI_CLOSED
        assert confidence < classify(ACTION_REMOVE)[1]

    def test_merge_without_a_survivor_is_really_a_removal(self):
        assert classify(ACTION_MERGE) == classify(ACTION_REMOVE)

    def test_a_plain_update_is_not_churn(self):
        # Most updates are an attribute refresh. Counting them would turn
        # GERS-matcher noise into a signal.
        assert classify(ACTION_UPDATE) == (None, 0.0)

    def test_update_with_date_closed_is_a_closing(self):
        event_type, confidence = classify(ACTION_UPDATE, date_closed="2026-07-01")
        assert event_type == POI_CLOSED and confidence == pytest.approx(0.6)

    def test_unresolved_closed_flag_is_a_weaker_closing(self):
        flagged = classify(ACTION_UPDATE, unresolved_flags=["closed"])
        dated = classify(ACTION_UPDATE, date_closed="2026-07-01")
        assert flagged[0] == POI_CLOSED
        assert flagged[1] < dated[1], "an uncorroborated flag outranked a recorded date"

    @pytest.mark.parametrize("flag", sorted(DISQUALIFYING_FLAGS))
    def test_disqualifying_flags_suppress_every_action(self, flag):
        # A duplicate, deleted, private or inappropriate record is not a venue
        # whose opening or closing says anything about a neighborhood.
        for action in (ACTION_ADD, ACTION_REMOVE, ACTION_MERGE, ACTION_UPDATE):
            assert classify(action, unresolved_flags=[flag]) == (None, 0.0)

    def test_unknown_action_is_not_churn(self):
        assert classify("teleported") == (None, 0.0)
        assert classify(None) == (None, 0.0)


class TestCategoryExtraction:
    def test_first_of_each_array(self):
        cid, label = category_of(row())
        assert cid == "4bf58dd8d48988d116941735"
        assert label == "Dining and Drinking > Bar"

    def test_empty_and_missing_arrays(self):
        assert category_of({"fsq_category_ids": [], "fsq_category_labels": None}) == (None, None)
        assert category_of({}) == (None, None)

    def test_scalar_is_tolerated(self):
        assert category_of({"fsq_category_ids": "abc"})[0] == "abc"


class TestLicensingGate:
    def test_strict_mode_refuses_while_the_exclusion_list_is_empty(self, producer):
        # Foursquare excludes 38 category ids from commercial use. Running
        # without that list is unlicensed, not degraded — so it fails closed.
        assert NON_COMMERCIAL_CATEGORY_IDS == frozenset()
        producer.strict_licensing = True
        with pytest.raises(PoiSourceError, match="38 category"):
            producer.check_licensing()

    def test_non_commercial_mode_is_allowed_to_proceed(self, producer):
        producer.strict_licensing = False
        producer.check_licensing()

    def test_excluded_categories_are_filtered(self, producer, monkeypatch):
        monkeypatch.setattr(
            "src.producers.poi_diff_producer.NON_COMMERCIAL_CATEGORY_IDS",
            frozenset({"4bf58dd8d48988d116941735"}),
        )
        assert producer.is_licensed("4bf58dd8d48988d116941735") is False
        assert producer.is_licensed("something-else") is True


class TestEventBuilding:
    def test_an_add_becomes_an_opening_in_the_right_city(self, producer):
        event = producer.build_event(row(), RELEASE)
        assert event.event_type == POI_OPENED
        assert event.city_id == "nyc"
        assert event.source == "fsq"
        assert event.poi_id == "4b0588f3f964a52012a022e3"
        assert event.h3_res7 and event.h3_res8 and event.h3_res9

    def test_event_date_is_the_release_date_not_date_closed(self, producer):
        # FSQ's own docs: date_closed is "the date the POI was marked as
        # closed in our database", which is not the day it closed. Using it
        # would dress a detection date as ground truth.
        event = producer.build_event(
            row(action=ACTION_UPDATE, date_closed="2019-01-01"), RELEASE
        )
        assert event.event_type == POI_CLOSED
        assert event.event_date == datetime(2026, 8, 11, tzinfo=UTC)
        assert event.release_id == "dt=2026-08-11"

    def test_confidence_rides_on_the_event(self, producer):
        merged = producer.build_event(row(action=ACTION_MERGE, redirect="x"), RELEASE)
        added = producer.build_event(row(), RELEASE)
        assert merged.confidence < added.confidence

    def test_rows_outside_every_registered_metro_are_dropped(self, producer):
        # A release covers the planet; only registered metros produce events.
        assert producer.build_event(row(latitude=45.5, longitude=-110.0), RELEASE) is None

    def test_missing_geometry_is_dropped(self, producer):
        assert producer.build_event(row(latitude=None, longitude=None), RELEASE) is None

    def test_null_island_is_dropped(self, producer):
        assert producer.build_event(row(latitude=0, longitude=0), RELEASE) is None

    def test_a_row_that_is_not_churn_produces_nothing(self, producer):
        assert producer.build_event(row(action=ACTION_UPDATE), RELEASE) is None

    def test_missing_id_produces_nothing(self, producer):
        assert producer.build_event(row(fsq_place_id="  "), RELEASE) is None

    def test_chicago_and_seattle_resolve_too(self, producer):
        chicago = producer.build_event(row(latitude=41.8781, longitude=-87.6298), RELEASE)
        seattle = producer.build_event(row(latitude=47.6062, longitude=-122.3321), RELEASE)
        assert chicago.city_id == "chicago"
        assert seattle.city_id == "seattle"


class TestDedup:
    def test_one_event_per_native_id(self, producer):
        a = producer.build_event(row(), RELEASE)
        b = producer.build_event(row(), RELEASE)
        assert len(producer.dedup([a, b])) == 1

    def test_source_precedence_fsq_beats_overture(self, producer):
        fsq = producer.build_event(row(), RELEASE)
        overture = producer.build_event(row(), RELEASE)
        overture.source = "overture"
        assert producer.dedup([overture, fsq])[0].source == "fsq"
        assert producer.dedup([fsq, overture])[0].source == "fsq"


class TestState:
    def test_release_marker_round_trips(self, producer, tmp_path, monkeypatch):
        monkeypatch.setattr(producer.settings, "poi_state_dir", str(tmp_path))
        assert producer.last_release() is None
        producer.record_release("2026-08-11", 1234)
        assert producer.last_release() == "2026-08-11"

    def test_corrupt_state_degrades_to_none(self, producer, tmp_path, monkeypatch):
        monkeypatch.setattr(producer.settings, "poi_state_dir", str(tmp_path))
        producer.state_path().parent.mkdir(parents=True, exist_ok=True)
        producer.state_path().write_text("{not json")
        assert producer.last_release() is None

    def test_no_partial_marker_is_left_behind(self, producer, tmp_path, monkeypatch):
        monkeypatch.setattr(producer.settings, "poi_state_dir", str(tmp_path))
        producer.record_release("2026-08-11", 1)
        assert not list(tmp_path.glob("*.tmp"))


class TestGatedSource:
    def test_download_without_a_token_fails_with_an_actionable_message(
        self, producer, tmp_path, monkeypatch
    ):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        with pytest.raises(PoiSourceError, match="HF_TOKEN"):
            producer.download("release/dt=2026-08-11/deltas/parquet/x.parquet", tmp_path)

    def test_registration_records_the_relocation_and_the_apache_notice(self):
        spec = get_national_feed(NationalFeed.POI_CHANGE)
        assert spec.auth_env == "HF_TOKEN"
        assert "RELOCATED" in spec.notes
        assert "NOTICE.txt" in (spec.attribution or "")

    def test_the_topic_is_poi_change_not_the_license_topic(self):
        from src.config import settings

        spec = get_national_feed(NationalFeed.POI_CHANGE)
        assert spec.topic == settings.topic_poi_change
        assert spec.topic != settings.topic_sla, (
            "POI churn must never ride the license topic — a vendor detection "
            "is not a government authorization"
        )
