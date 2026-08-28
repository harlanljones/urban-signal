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
