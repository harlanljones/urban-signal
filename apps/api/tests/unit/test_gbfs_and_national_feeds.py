"""US-363 §1.2 GBFS registration + §1.3-§1.5 national feed registry.

Fixtures are trimmed from live payloads captured 2026-08-28. Network-free.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.producers.snapshot_client import (
    EmptySnapshotError,
    GbfsDialectError,
    SnapshotClient,
    StationRecord,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType, get_dataset
from src.spatial.geography_crosswalk import GeographyCrosswalk
from src.spatial.national_feeds import (
    FSQ_ATTRIBUTION,
    NATIONAL_FEEDS,
    NationalFeed,
    get_national_feed,
    schedulable_feeds,
)

# Lyft GBFS 2.3 discovery (Citi Bike), trimmed.
DISCOVERY_V23 = {
    "data": {
        "en": {
            "feeds": [
                {"name": "system_information", "url": "https://x/system_information.json"},
                {"name": "station_information", "url": "https://x/station_information.json"},
                {"name": "station_status", "url": "https://x/station_status.json"},
            ]
        }
    },
    "last_updated": 1787893795,
    "ttl": 60,
    "version": "2.3",
}

# GBFS 3.0 drops the language level.
DISCOVERY_V30 = {
    "data": {
        "feeds": [
            {"name": "station_information", "url": "https://x/station_information.json"},
            {"name": "station_status", "url": "https://x/station_status.json"},
        ]
    },
    "version": "3.0",
}

INFORMATION = {
    "data": {
        "stations": [
            {
                "station_id": "1822663031356509142",
                "name": "Matthews Ct & Coney Island Ave",
                "short_name": "3034.02",
                "lon": -73.96951,
                "lat": 40.64235,
                "capacity": 21,
            },
            {
                "station_id": "no-coords",
                "name": "Broken",
                "lat": None,
                "lon": None,
            },
            {
                "station_id": "null-island",
                "name": "Placeholder",
                "lat": 0,
                "lon": 0,
            },
            {
                "station_id": "sentinel-capacity",
                "name": "Sentinel",
                "lat": 40.7,
                "lon": -73.99,
                "capacity": 999999,
            },
        ]
    },
    "version": "2.3",
}

STATUS = {
    "data": {
        "stations": [
            {"station_id": "1822663031356509142", "is_installed": 1, "num_docks_available": 7},
            {"station_id": "sentinel-capacity", "is_installed": 0, "num_docks_available": 999999},
        ]
    }
}


class TestDiscovery:
    def test_v2_language_nesting(self):
        feeds = SnapshotClient.resolve_feeds(DISCOVERY_V23)
        assert feeds["station_information"].endswith("station_information.json")
        assert "station_status" in feeds

    def test_v3_flat_feeds(self):
        # v3.0 drops `data.<lang>`; pinning one dialect would break the moment
        # an operator upgrades.
        feeds = SnapshotClient.resolve_feeds(DISCOVERY_V30)
        assert "station_information" in feeds

    def test_a_system_without_station_information_is_an_error(self):
        payload = {"data": {"en": {"feeds": [{"name": "free_bike_status", "url": "https://x"}]}}}
        with pytest.raises(GbfsDialectError, match="station_information"):
            SnapshotClient.resolve_feeds(payload)

    def test_garbage_discovery_is_an_error(self):
        with pytest.raises(GbfsDialectError):
            SnapshotClient.resolve_feeds({"nope": 1})


class TestParsing:
    def parsed(self):
        return SnapshotClient.parse_stations(INFORMATION, STATUS, now="2026-08-28T00:00:00+00:00")

    def test_good_station_survives_with_its_attributes(self):
        stations, _ = self.parsed()
        rec = stations["1822663031356509142"]
        assert rec.name == "Matthews Ct & Coney Island Ave"
        assert rec.capacity == 21
        assert rec.lat == pytest.approx(40.64235)
        assert rec.is_installed == 1

    def test_missing_and_null_island_coordinates_go_to_the_dlq(self):
        stations, dlq = self.parsed()
        assert "no-coords" not in stations
        assert "null-island" not in stations
        reasons = {sid: reason for sid, reason in dlq}
        assert "no coordinate" in reasons["no-coords"]
        assert "null-island" in reasons["null-island"]

    def test_dock_sentinel_becomes_null_capacity_not_999999(self):
        stations, _ = self.parsed()
        assert stations["sentinel-capacity"].capacity is None

    def test_pre_activation_stations_are_kept_not_dropped(self):
        # is_installed=0 is the leading indicator this feed is registered for
        # (98 of Citi Bike's 2,508 stations on 2026-08-28). Dropping them
        # would discard exactly the signal we came for.
        stations, _ = self.parsed()
        assert stations["sentinel-capacity"].is_installed == 0


def rec(station_id: str, lat: float = 40.7, lon: float = -74.0) -> StationRecord:
    return StationRecord(station_id=station_id, name=station_id, lat=lat, lon=lon)


class TestDiff:
    def test_first_poll_emits_nothing(self):
        # With no prior state every station looks new. Emitting would stamp
        # thousands of installs on the day polling happened to start.
        diff = SnapshotClient.diff({}, {"a": rec("a"), "b": rec("b")})
        assert diff.added == [] and diff.removed == []
        assert diff.unchanged == 2

    def test_additions_and_removals(self):
        previous = {"a": rec("a"), "b": rec("b")}
        current = {"b": rec("b"), "c": rec("c")}
        diff = SnapshotClient.diff(previous, current)
        assert [r.station_id for r in diff.added] == ["c"]
        assert [r.station_id for r in diff.removed] == ["a"]
        assert diff.unchanged == 1

    def test_first_seen_carries_forward(self):
        previous = {"a": StationRecord(station_id="a", first_seen="2026-01-01", lat=1, lon=1)}
        current = {"a": StationRecord(station_id="a", first_seen="2026-08-28", lat=1, lon=1)}
        merged = SnapshotClient.merge_state(previous, current)
        assert merged["a"].first_seen == "2026-01-01"


class TestStateStore:
    def test_round_trip(self, tmp_path):
        client = SnapshotClient(state_dir=str(tmp_path))
        client.save_state("bkn", {"a": rec("a")})
        loaded = client.load_state("bkn")
        assert loaded["a"].station_id == "a"
        assert loaded["a"].lat == pytest.approx(40.7)

    def test_unknown_system_loads_empty(self, tmp_path):
        assert SnapshotClient(state_dir=str(tmp_path)).load_state("nope") == {}

    def test_corrupt_state_degrades_to_empty_rather_than_crashing(self, tmp_path):
        client = SnapshotClient(state_dir=str(tmp_path))
        path = client.state_path("bkn")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json")
        assert client.load_state("bkn") == {}

    def test_no_partial_file_is_left_behind(self, tmp_path):
        client = SnapshotClient(state_dir=str(tmp_path))
        client.save_state("bkn", {"a": rec("a")})
        assert not list(tmp_path.glob("*.tmp")), (
            "a torn state file would look like a system that lost every station"
        )


class TestEmptySnapshotGuard:
    def test_empty_station_list_raises_rather_than_seeding(self, monkeypatch, tmp_path):
        """Lyft's `dca` slug answers 200 with zero stations (verified live).

        Seeding from it and later polling a populated feed would emit an
        install event for all 866 Capital Bikeshare stations at once.
        """
        client = SnapshotClient(state_dir=str(tmp_path))
        payloads = {
            "discovery": DISCOVERY_V23,
            "https://x/station_information.json": {"data": {"stations": []}, "version": "2.3"},
            "https://x/station_status.json": {"data": {"stations": []}},
        }
        monkeypatch.setattr(
            client, "_get_json", lambda url: payloads.get(url, payloads["discovery"])
        )
        with pytest.raises(EmptySnapshotError, match="refusing to seed"):
            client.poll("dca", "https://x/gbfs.json")


class TestGbfsRegistration:
    @pytest.mark.parametrize(
        "city,system_id",
        [
            (CityId.NYC, "bkn"),
            (CityId.CHICAGO, "chi"),
            (CityId.SAN_FRANCISCO, "bay"),
            (CityId.WASHINGTON_DC, "dca-cabi"),
        ],
    )
    def test_registered_systems(self, city, system_id):
        spec = get_dataset(city, FeedType.GBFS)
        assert spec.companion_endpoints["system_id"] == system_id
        assert spec.platform == "gbfs"
        assert spec.producer_key == "gbfs"
        assert spec.ingestion_mode == "snapshot"
        assert spec.watermark_col == "", "GBFS has no watermark column by construction"

    def test_dc_points_at_the_operator_root_not_the_empty_lyft_stub(self):
        spec = get_dataset(CityId.WASHINGTON_DC, FeedType.GBFS)
        assert "capitalbikeshare.com" in spec.endpoint
        assert "/dca/" not in spec.endpoint, (
            "gbfs.lyft.com/.../dca/ is a live-but-empty stub — 200 with zero stations"
        )

    def test_only_licensed_operators_are_registered(self):
        # Lime/Bird/Spin/Bolt/Veo carry internal-non-commercial-only terms with
        # 10-minute retention and no-database-augmentation clauses.
        barred = ("lime", "bird", "spin", "bolt", "veo")
        for cid, reg in REGISTRY.items():
            spec = reg.datasets.get(FeedType.GBFS)
            if spec is None:
                continue
            assert spec.companion_endpoints.get("operator") == "lyft", cid.value
            assert not any(b in spec.endpoint.lower() for b in barred), cid.value

    def test_no_other_city_gained_gbfs(self):
        registered = {cid.value for cid, reg in REGISTRY.items() if FeedType.GBFS in reg.datasets}
        assert registered == {"nyc", "chicago", "san_francisco", "washington_dc"}


class TestNationalFeeds:
    def test_all_four_components_are_registered(self):
        assert set(NATIONAL_FEEDS) == {
            NationalFeed.POI_CHANGE,
            NationalFeed.NFIP_CLAIMS,
            NationalFeed.DISASTER_DECLARATIONS,
            NationalFeed.EV_CHARGING,
        }

    def test_nfip_uses_v3_and_declarations_stay_on_v2(self):
        # v2 FimaNfipClaims is frozen 2026-06-01 and removed 2026-10-15;
        # DisasterDeclarationsSummaries has no v3 at all (404).
        assert "/v3/NfipClaims" in get_national_feed(NationalFeed.NFIP_CLAIMS).endpoint
        assert "/v2/DisasterDeclarationsSummaries" in get_national_feed(
            NationalFeed.DISASTER_DECLARATIONS
        ).endpoint

    def test_fsq_carries_its_apache_notice(self):
        spec = get_national_feed(NationalFeed.POI_CHANGE)
        assert spec.attribution == FSQ_ATTRIBUTION
        assert "NOTICE" in spec.attribution

    def test_fsq_records_the_relocation(self):
        spec = get_national_feed(NationalFeed.POI_CHANGE)
        assert spec.auth == "bearer" and spec.auth_env == "HF_TOKEN"
        assert "RELOCATED" in spec.notes

    def test_nrel_is_marked_unverified(self):
        # developer.nrel.gov does not resolve from this network; nothing about
        # the feed has been confirmed live by anyone yet.
        spec = get_national_feed(NationalFeed.EV_CHARGING)
        assert spec.verified is False
        assert "UNVERIFIED" in spec.notes

    def test_unverified_and_credential_less_feeds_are_not_schedulable(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("NREL_API_KEY", raising=False)
        schedulable = {spec.feed for spec in schedulable_feeds()}
        assert NationalFeed.EV_CHARGING not in schedulable, "unverified source scheduled"
        assert NationalFeed.POI_CHANGE not in schedulable, "gated source scheduled without a token"
        assert NationalFeed.NFIP_CLAIMS in schedulable

    def test_unknown_feed_error_names_the_known_ones(self):
        with pytest.raises(KeyError, match="nfip_claims"):
            get_national_feed("nope")

    def test_no_national_feed_pretends_to_be_a_city_feed(self):
        # A national file covering 62 metros must not be registered 62 times.
        national_topics = {spec.topic for spec in NATIONAL_FEEDS.values()}
        for cid, reg in REGISTRY.items():
            for feed, spec in reg.datasets.items():
                if feed is FeedType.GBFS:
                    continue  # GBFS is genuinely one system per metro
                assert spec.topic not in (
                    national_topics - {get_national_feed(NationalFeed.DISASTER_DECLARATIONS).topic}
                ), f"{cid.value}/{feed.value} registers a national topic as a city feed"


class TestCrosswalkForFema:
    @pytest.fixture(scope="class")
    @classmethod
    def crosswalk(cls):
        return GeographyCrosswalk()

    def test_block_group_geoid_resolves_to_its_tract(self, crosswalk):
        # FEMA publishes a 12-character block-group id; the tract is the first
        # 11 characters.
        point = crosswalk.tract_point("360470193002")
        assert point is not None
        assert crosswalk.city_for_tract("360470193002") == "nyc"

    def test_split_tracts_still_resolve(self, crosswalk):
        # Harris County's 48201222700 became ...01 and ...02 in the 2020
        # tabulation; a claim filed under the old id matches neither exactly.
        point = crosswalk.tract_point("482012227001")
        assert point is not None
        assert point.geography_id.startswith("482012227")
        assert crosswalk.city_for_tract("482012227001") == "houston"

    def test_short_ids_resolve_to_nothing(self, crosswalk):
        assert crosswalk.tract_point("4820") is None
        assert crosswalk.tract_point("") is None

    def test_county_fips_resolves(self, crosswalk):
        assert crosswalk.city_for_county_fips("36061") == "nyc"
        assert crosswalk.city_for_county_fips("17031") == "chicago"

    def test_county_outside_every_metro_resolves_to_nothing(self, crosswalk):
        # Southeast Fairbanks Census Area, AK.
        assert crosswalk.city_for_county_fips("02240") is None

    def test_tract_centroid_beats_femas_truncated_coordinate(self, crosswalk):
        """FEMA truncates claim coordinates to 0.1 degrees (~11 km).

        The live Harris County example publishes (29.9, -95.4) while the
        tract centroid is (29.935, -95.305) — the truncated point is over 9 km
        away, which is wider than a res-7 hexagon.
        """
        point = crosswalk.tract_point("482012227001")
        assert abs(point.latitude - 29.9) > 0.01 or abs(point.longitude - (-95.4)) > 0.01
