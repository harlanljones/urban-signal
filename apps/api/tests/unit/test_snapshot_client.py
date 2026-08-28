from pathlib import Path

import pytest

from src.producers.snapshot_client import (
    EmptySnapshotError,
    SnapshotClient,
    StationRecord,
)


def test_resolve_feeds_supports_language_nested_and_v3_shapes():
    nested = {"data": {"en": {"feeds": [{"name": "station_information", "url": "info"}]}}}
    flat = {"data": {"feeds": [{"name": "station_information", "url": "info"}]}}
    assert SnapshotClient.resolve_feeds(nested) == {"station_information": "info"}
    assert SnapshotClient.resolve_feeds(flat) == {"station_information": "info"}


def test_discovery_prefers_supported_gbfs_version_and_resolves_relative_urls(monkeypatch):
    root_url = "https://example.test/gbfs.json"
    versions_url = "https://example.test/versions.json"
    v23_url = "https://example.test/v2.3/gbfs.json"
    payloads = {
        root_url: {
            "data": {"en": {"feeds": [{"name": "gbfs_versions", "url": "versions.json"}]}},
        },
        versions_url: {
            "data": {
                "versions": [
                    {"version": "2.3", "url": "v2.3/gbfs.json"},
                    {"version": "4.0", "url": "v4/gbfs.json"},
                ]
            }
        },
        v23_url: {
            "version": "2.3",
            "data": {"en": {"feeds": [{"name": "station_information", "url": "station_information.json"}]}},
        },
    }
    client = SnapshotClient(state_dir="/tmp/urban-signal-gbfs-test")
    monkeypatch.setattr(client, "_get_json", lambda url: payloads[url])
    feeds, version = client.discover(root_url)
    assert version == "2.3"
    assert feeds["station_information"] == "https://example.test/v2.3/station_information.json"


def test_parse_stations_rejects_bad_coordinates_and_sentinel_capacity():
    info = {"data": {"stations": [
        {"station_id": "ok", "name": "A", "lat": "40.7", "lon": "-74.0", "capacity": 20},
        {"station_id": "zero", "lat": 0, "lon": 0},
        {"station_id": "bad", "lat": None, "lon": -74},
        {"station_id": "sentinel", "lat": 40, "lon": -74, "capacity": 999999},
    ]}}
    stations, dlq = SnapshotClient.parse_stations(info, now="2026-08-28T00:00:00+00:00")
    assert stations["ok"].capacity == 20
    assert stations["sentinel"].capacity is None
    assert {sid for sid, _ in dlq} == {"zero", "bad"}


def test_parse_status_normalizes_sentinels_and_adds_h3_tags():
    stations = {"a": StationRecord("a", lat=40.7, lon=-74.0)}
    stamp, rows = SnapshotClient.parse_status(
        {"last_updated": 1787893795, "data": {"stations": [{
            "station_id": "a",
            "num_bikes_available": 7,
            "num_docks_available": 999999,
            "last_reported": 86400,
        }, {"station_id": "unknown", "num_bikes_available": 2}]}},
        stations,
    )
    assert stamp == "2026-08-28T05:09:55+00:00"
    assert len(rows) == 1
    assert rows[0]["num_bikes_available"] == 7
    assert rows[0]["num_docks_available"] is None
    assert rows[0]["last_reported"] is None
    assert rows[0]["h3_res7"] and rows[0]["h3_res8"] and rows[0]["h3_res9"]


def test_first_poll_seeds_without_mass_install_events_and_merge_preserves_first_seen():
    old = StationRecord("a", first_seen="2026-01-01", last_seen="2026-08-27")
    current = {"a": StationRecord("a", last_seen="2026-08-28"), "b": StationRecord("b")}
    assert SnapshotClient.diff({}, current).added == []
    merged = SnapshotClient.merge_state({"a": old}, current)
    assert merged["a"].first_seen == "2026-01-01"
    assert [record.station_id for record in SnapshotClient.diff({"a": old}, current).added] == ["b"]


def test_state_store_round_trips_and_empty_poll_does_not_overwrite(tmp_path: Path, monkeypatch):
    client = SnapshotClient(state_dir=str(tmp_path))
    client.save_state("bkn", {"a": StationRecord("a", lat=40.7, lon=-74)})
    assert client.load_state("bkn")["a"].lon == -74

    responses = iter([
        {"data": {"feeds": [{"name": "station_information", "url": "info"}]}},
        {"data": {"stations": []}},
    ])
    monkeypatch.setattr(client, "_get_json", lambda _url: next(responses))
    with pytest.raises(EmptySnapshotError):
        client.poll("bkn", "discovery")
    assert client.load_state("bkn")["a"].station_id == "a"


def test_status_archive_is_idempotent_and_retains_feed_snapshot(tmp_path: Path):
    client = SnapshotClient(state_dir=str(tmp_path))
    stations = {"a": StationRecord("a", lat=40.7, lon=-74.0)}
    snapshot = client.parse_status(
        {
            "last_updated": 1787893795,
            "data": {"stations": [{"station_id": "a", "num_bikes_available": 4}]},
        },
        stations,
    )
    client.save_state("bkn", stations, status_snapshot=snapshot)
    client.save_state("bkn", stations, status_snapshot=snapshot)
    archive = client.load_status_snapshots("bkn")
    assert len(archive) == 1
    assert archive[0]["feed"] == "station_status"
    assert archive[0]["rows"][0]["num_bikes_available"] == 4
    assert archive[0]["rows"][0]["h3_res9"]
