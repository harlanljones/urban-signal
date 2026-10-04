import hashlib
import json
from datetime import UTC, datetime

import pytest

from src.ingestion.runner import aggregate_features, commit_run, normalize_records, replay_committed
from src.ingestion.store import LocalObjectStore


class Contract:
    source_id = "nyc-permits"
    endpoint = "https://data.cityofnewyork.us/resource/ipu4-2q9a.json"
    dataset_id = "ipu4-2q9a"
    version = "v1"
    fields = (
        "permit_business_id",
        "city_id",
        "feed_id",
        "source_row_id",
        "issued_date",
        "updated_at",
        "latitude",
        "longitude",
        "job__",
    )
    identity_fields = ("permit_business_id",)
    source_row_id_field = "source_row_id"
    event_time_field = "issued_date"
    update_time_field = "updated_at"

    def to_dict(self):
        return {"source_id": self.source_id, "dataset_id": self.dataset_id, "version": self.version}


def row(
    row_id,
    issued,
    *,
    bid="A",
    city="nyc",
    feed="permits",
    lat="40.7",
    lon="-73.9",
    updated="2026-01-01T00:00:00Z",
):
    return {
        "permit_business_id": bid,
        "city_id": city,
        "feed_id": feed,
        "source_row_id": row_id,
        "issued_date": issued,
        "updated_at": updated,
        "latitude": lat,
        "longitude": lon,
        "job__": "Alteration",
    }


def test_normalize_scopes_business_identity_and_retains_future_rows():
    as_of = datetime(2026, 4, 1, tzinfo=UTC)
    rows = [
        row("1", "2026-03-01T00:00:00Z"),
        row("2", "2026-03-02T00:00:00Z", bid="B"),
        row("3", "2027-01-01T00:00:00Z", bid="C"),
    ]

    normalized = normalize_records(rows, Contract(), as_of)

    assert set(normalized) == {
        ("nyc", "permits", "A"),
        ("nyc", "permits", "B"),
        ("nyc", "permits", "C"),
    }
    assert normalized[("nyc", "permits", "A")]["source_row_id"] == "1"
    assert normalized[("nyc", "permits", "C")]["source_event_time"] == "2027-01-01T00:00:00+00:00"
    assert normalized[("nyc", "permits", "A")]["content_hash"]
    assert normalized[("nyc", "permits", "A")]["h3"]
    assert normalized[("nyc", "permits", "A")]["cost_status"] == "missing"


def test_normalize_accepts_socrata_calendar_dates():
    normalized = normalize_records(
        [row("1", "06/17/2020")], Contract(), datetime(2026, 4, 1, tzinfo=UTC)
    )
    assert normalized[("nyc", "permits", "A")]["source_event_time"] == "2020-06-17T00:00:00+00:00"


def test_normalize_rejects_ambiguous_duplicate_business_identity():
    rows = [row("1", "2026-03-01T00:00:00Z"), row("2", "2026-03-02T00:00:00Z")]

    with pytest.raises(ValueError, match="duplicate identity"):
        normalize_records(rows, Contract(), datetime(2026, 4, 1, tzinfo=UTC))


def test_features_use_inclusive_utc_windows_and_velocity_baseline():
    as_of = datetime(2026, 4, 1, tzinfo=UTC)
    records = normalize_records(
        [row("1", "2026-01-31T00:00:00Z"), row("2", "2026-04-02T00:00:00Z", bid="B")],
        Contract(),
        as_of,
    )

    features = aggregate_features(records, as_of)

    assert len(features) == 1
    cell = next(iter(features.values()))
    assert cell["permits_60d"] == 1
    assert cell["permits_90d"] == 1
    assert cell["permits_180d"] == 1
    assert cell["permits_360d"] == 1
    assert cell["permits_60d_velocity"] == pytest.approx(2.0)
    assert cell["cost_status"] == "unavailable_missing_cost_data"


def test_commit_replay_restores_manifest_lineage_and_separate_feature_pointer(tmp_path):
    store = LocalObjectStore(tmp_path)
    as_of = datetime(2026, 4, 1, tzinfo=UTC)

    receipt = commit_run(
        store,
        Contract(),
        [row("1", "2026-03-01T00:00:00Z")],
        as_of,
        complete=True,
        reconciliation=True,
        full_scope=True,
    )
    restored = replay_committed(store, Contract(), as_of)

    assert receipt["manifest_hash"]
    assert receipt["input_mode"] == "local_fixture"
    assert receipt["feature_manifest_hash"]
    assert restored["records"] == receipt["records"]
    assert restored["features"] == receipt["features"]
    assert restored["feature_manifest_hash"] == receipt["feature_manifest_hash"]
    json.dumps(receipt)
    json.dumps(restored)
    assert (
        store.read_checkpoint("checkpoints/features.json")[0]["manifest_key"]
        == receipt["feature_manifest_key"]
    )


def test_incomplete_run_does_not_advance_checkpoint(tmp_path):
    store = LocalObjectStore(tmp_path)

    with pytest.raises(ValueError, match="incomplete"):
        commit_run(
            store, Contract(), [row("1", "2026-03-01T00:00:00Z")], datetime(2026, 4, 1, tzinfo=UTC)
        )

    assert store.read_checkpoint("checkpoints/acquisition.json") == (None, None)


def test_daily_delta_replays_prior_rows_and_correction_replaces_content(tmp_path):
    store = LocalObjectStore(tmp_path)
    contract = Contract()
    as_of = datetime(2026, 4, 1, tzinfo=UTC)
    first = row("source-1", "2026-01-01T00:00:00Z")
    commit_run(store, contract, [first], as_of, complete=True, reconciliation=True, full_scope=True)
    corrected = {**first, "latitude": "40.8", "updated_at": "2026-03-30T00:00:00Z"}

    receipt = commit_run(store, contract, [corrected], as_of, complete=True)

    stored = next(record for record in receipt["records"] if record["identity"] == ["A"])
    original = normalize_records([first], contract, as_of)[("nyc", "permits", "A")]
    assert stored["latitude"] == 40.8
    assert stored["content_hash"] != original["content_hash"]
    assert len(receipt["records"]) == 1


def test_empty_delta_retains_history_and_recomputes_feature_as_of(tmp_path):
    store = LocalObjectStore(tmp_path)
    contract = Contract()
    first_as_of = datetime(2026, 4, 1, tzinfo=UTC)
    commit_run(
        store,
        contract,
        [row("1", "2026-03-01T00:00:00Z")],
        first_as_of,
        complete=True,
        reconciliation=True,
        full_scope=True,
    )

    later = commit_run(store, contract, [], datetime(2026, 8, 1, tzinfo=UTC), complete=True)

    assert len(later["records"]) == 1
    cell = next(iter(later["features"].values()))
    assert cell["permits_60d"] == 0
    assert later["as_of"] == datetime(2026, 8, 1, tzinfo=UTC).isoformat()


def test_deletions_are_applied_only_by_explicit_complete_reconciliation(tmp_path):
    store = LocalObjectStore(tmp_path)
    contract = Contract()
    as_of = datetime(2026, 4, 1, tzinfo=UTC)
    initial = [row("1", "2026-03-01T00:00:00Z"), row("2", "2026-03-02T00:00:00Z", bid="B")]
    commit_run(store, contract, initial, as_of, complete=True, reconciliation=True, full_scope=True)

    delta = commit_run(store, contract, [initial[0]], as_of, complete=True)
    rebuilt = commit_run(
        store, contract, [initial[0]], as_of, complete=True, reconciliation=True, full_scope=True
    )

    assert len(delta["records"]) == 2
    assert len(rebuilt["records"]) == 1


def test_corrupt_page_object_fails_closed_during_replay(tmp_path):
    from src.ingestion.store import IntegrityError

    store = LocalObjectStore(tmp_path)
    receipt = commit_run(
        store,
        Contract(),
        [row("1", "2026-03-01T00:00:00Z")],
        datetime(2026, 4, 1, tzinfo=UTC),
        complete=True,
        reconciliation=True,
        full_scope=True,
    )
    manifest = receipt["manifest_key"]
    raw = store.get_verified(manifest, receipt["manifest_hash"])
    body = json.loads(raw)
    page_key = body["pages"][0]["key"]
    (tmp_path / page_key).write_bytes(b"corrupted")

    with pytest.raises(IntegrityError):
        replay_committed(store, Contract())


def test_invalid_dates_and_coordinates_fail_closed():
    with pytest.raises(ValueError, match="event time"):
        normalize_records([row("1", "not-a-date")], Contract(), datetime(2026, 4, 1, tzinfo=UTC))
    with pytest.raises(ValueError, match="coordinate"):
        normalize_records(
            [row("1", "2026-03-01T00:00:00Z", lat="100")],
            Contract(),
            datetime(2026, 4, 1, tzinfo=UTC),
        )


def test_commit_requires_timezone_aware_as_of_before_writing(tmp_path):
    store = LocalObjectStore(tmp_path)

    with pytest.raises(ValueError, match="timezone-aware"):
        commit_run(
            store, Contract(), [row("1", "2026-03-01T00:00:00Z")], "2026-04-01", complete=True
        )

    assert store.read_checkpoint("checkpoints/acquisition.json") == (None, None)


def test_acquisition_time_is_distinct_and_stable_after_replay(tmp_path):
    store = LocalObjectStore(tmp_path)
    contract = Contract()
    as_of = datetime(2026, 4, 1, tzinfo=UTC)
    acquired_at = datetime(2026, 4, 1, 12, tzinfo=UTC)

    receipt = commit_run(
        store,
        contract,
        [row("1", "2026-03-01T00:00:00Z")],
        as_of,
        complete=True,
        acquired_at=acquired_at,
    )
    replay = replay_committed(store, contract)
    assert receipt["records"][0]["acquired_at"] == acquired_at.isoformat()
    assert replay["records"][0]["acquired_at"] == acquired_at.isoformat()


def test_identity_fields_reject_whitespace_only_values():
    invalid = row("1", "2026-03-01T00:00:00Z", bid="   ")

    with pytest.raises(ValueError, match="identity"):
        normalize_records([invalid], Contract(), datetime(2026, 4, 1, tzinfo=UTC))


def test_replay_rejects_changed_contract_semantics_even_with_same_version(tmp_path):
    store = LocalObjectStore(tmp_path)
    contract = Contract()
    as_of = datetime(2026, 4, 1, tzinfo=UTC)
    commit_run(store, contract, [row("1", "2026-03-01T00:00:00Z")], as_of, complete=True)
    changed = Contract()
    changed.event_time_field = "updated_at"

    from src.ingestion.store import IntegrityError

    with pytest.raises(IntegrityError, match="contract"):
        replay_committed(store, changed)


def test_concurrent_acquisition_after_restore_causes_old_checkpoint_conflict(tmp_path):
    from src.ingestion.store import CheckpointConflict

    backing = LocalObjectStore(tmp_path)
    contract = Contract()
    as_of = datetime(2026, 4, 1, tzinfo=UTC)
    original = row("1", "2026-03-01T00:00:00Z")
    commit_run(
        backing, contract, [original], as_of, complete=True, reconciliation=True, full_scope=True
    )

    class RacingStore:
        def __init__(self, inner):
            self.inner = inner
            self.race_once = True

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def get_verified(self, key, sha256):
            if self.race_once:
                self.race_once = False
                rival = row("2", "2026-03-02T00:00:00Z", bid="B")
                commit_run(self.inner, contract, [rival], as_of, complete=True)
            return self.inner.get_verified(key, sha256)

    contender = RacingStore(backing)
    with pytest.raises(CheckpointConflict):
        commit_run(
            contender, contract, [row("3", "2026-03-03T00:00:00Z", bid="C")], as_of, complete=True
        )

    replay = replay_committed(backing, contract)
    assert {record["identity"][0] for record in replay["records"]} == {"A", "B"}


def test_replay_reports_feature_pointer_stale_after_new_acquisition(tmp_path):
    store = LocalObjectStore(tmp_path)
    contract = Contract()
    as_of = datetime(2026, 4, 1, tzinfo=UTC)
    commit_run(
        store,
        contract,
        [row("1", "2026-03-01T00:00:00Z")],
        as_of,
        complete=True,
        reconciliation=True,
        full_scope=True,
    )
    acquisition, version = store.read_checkpoint("checkpoints/acquisition.json")
    old_bytes = store.get_verified(acquisition["manifest_key"], acquisition["manifest_hash"])
    manifest = json.loads(old_bytes)
    manifest["run_id"] = "acquisition-without-feature-publication"
    manifest["parent"] = {
        "manifest_key": acquisition["manifest_key"],
        "manifest_hash": acquisition["manifest_hash"],
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    manifest_key = f"manifests/{manifest_hash}.json"
    store.put_immutable(manifest_key, manifest_bytes, manifest_hash)
    store.compare_and_swap_checkpoint(
        "checkpoints/acquisition.json",
        version,
        {
            **acquisition,
            "manifest_key": manifest_key,
            "manifest_hash": manifest_hash,
            "generation": acquisition["generation"] + 1,
        },
    )

    receipt = replay_committed(store, contract)

    assert receipt["feature_pointer_current"] is False
    assert receipt["feature_manifest_key"] is None


def test_normalize_rejects_fields_outside_contract_projection():
    unexpected = {**row("1", "2026-03-01T00:00:00Z"), "applicant_phone": "555-0100"}

    with pytest.raises(ValueError, match="schema"):
        normalize_records([unexpected], Contract(), datetime(2026, 4, 1, tzinfo=UTC))


def test_replay_retains_future_history_but_excludes_future_window_counts(tmp_path):
    store = LocalObjectStore(tmp_path)
    as_of = datetime(2026, 4, 1, tzinfo=UTC)
    committed = commit_run(
        store, Contract(), [row("future", "2026-05-01T00:00:00Z")], as_of, complete=True
    )
    replayed = replay_committed(store, Contract(), as_of)
    assert replayed["records"] == committed["records"]
    assert replayed["record_count"] == 1
    assert replayed["features"] == committed["features"] == {}
