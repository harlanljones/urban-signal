"""Content-addressed publication plans stay report-only and hash-stable."""

from __future__ import annotations

import json

import pytest

from src.export.publication import NonFiniteNumber, canonical_bytes, plan_publication


def _entry(key: str, payload: dict) -> dict[str, str]:
    return {"key": key, "value": json.dumps(payload)}


def _meta(**overrides: object) -> dict:
    metadata = {
        "as_of": "2026-10-10",
        "feature_schema_version": "features-v1",
        "model_id": "synthetic-default",
        "source_revisions": {"feed": "ipu4-2q9a"},
    }
    metadata.update(overrides)
    return metadata


def test_identical_inputs_reuse_every_object():
    entries = [
        _entry("grid/nyc", {"cells": [1, 2], "inference_latency_ms": 4.5}),
        _entry("manifest", {"generated_at": "2026-10-10T00:00:00+00:00", "cities": ["nyc"]}),
    ]
    first = plan_publication(entries, None, _meta())
    again = plan_publication(entries, None, _meta())
    second = plan_publication(entries, first.manifest, _meta())
    assert first.snapshot_id == again.snapshot_id
    assert len(first.snapshot_id) == 64
    assert set(second.reuse_candidates) == set(second.objects)
    stored = json.loads(second.objects[second.manifest["keys"]["grid/nyc"]["sha256"]].decode())
    assert stored["inference_latency_ms"] == 0.0
    assert "manifest" in second.manifest["keys"]
    assert second.manifest["snapshot_id"] not in second.manifest["keys"]


def test_model_feature_context_and_day_changes_move_the_release_id():
    entries = [_entry("grid/nyc", {"lims": 1})]
    base = plan_publication(entries, None, _meta())
    assert plan_publication(entries, None, _meta(model_id="other")).snapshot_id != base.snapshot_id
    assert (
        plan_publication(entries, None, _meta(feature_schema_version="features-v2")).snapshot_id
        != base.snapshot_id
    )
    changed_context = plan_publication(
        entries,
        None,
        _meta(source_revisions={"feed": "other"}),
    )
    assert changed_context.snapshot_id != base.snapshot_id
    assert plan_publication(entries, None, _meta(as_of="2026-10-11")).snapshot_id != base.snapshot_id
    reused = plan_publication(entries, base.manifest, _meta(model_id="other"))
    assert set(reused.reuse_candidates) == set(reused.objects)


def test_removed_keys_cannot_leak_from_the_previous_release():
    previous = plan_publication(
        [_entry("grid/nyc", {"lims": 1}), _entry("grid/la", {"lims": 2})],
        None,
        _meta(),
    )
    current = plan_publication([_entry("grid/nyc", {"lims": 1})], previous.manifest, _meta())
    assert "grid/la" not in current.manifest["keys"]
    assert previous.manifest["keys"]["grid/la"]["sha256"] not in {
        spec["sha256"] for spec in current.manifest["keys"].values()
    }


def test_non_finite_numbers_are_rejected():
    with pytest.raises(NonFiniteNumber):
        canonical_bytes({"lims": float("nan")})
    with pytest.raises(NonFiniteNumber):
        plan_publication([_entry("grid/nyc", {"lims": float("nan")})], None, _meta())


def test_a_city_change_that_moves_another_citys_percentile_is_visible():
    before = [
        _entry("grid/nyc", {"lims_national_pct": 10, "records_hash": "aaa"}),
        _entry("grid/la", {"lims_national_pct": 90, "records_hash": "bbb"}),
    ]
    after = [
        _entry("grid/nyc", {"lims_national_pct": 40, "records_hash": "aaa"}),
        _entry("grid/la", {"lims_national_pct": 60, "records_hash": "bbb"}),
    ]
    first = plan_publication(before, None, _meta())
    second = plan_publication(after, first.manifest, _meta())
    assert second.reuse_candidates == ()
    assert second.manifest["keys"]["grid/nyc"]["sha256"] != first.manifest["keys"]["grid/nyc"]["sha256"]
    assert second.manifest["keys"]["grid/la"]["sha256"] != first.manifest["keys"]["grid/la"]["sha256"]


def test_time_decay_is_not_hidden_by_a_stable_record_hash():
    earlier = _entry("cell/a", {"records_hash": "same", "as_of": "2026-10-01", "permit_count_60d": 4})
    later = _entry("cell/a", {"records_hash": "same", "as_of": "2026-10-02", "permit_count_60d": 1})
    first = plan_publication([earlier], None, _meta(as_of="2026-10-01"))
    second = plan_publication([later], first.manifest, _meta(as_of="2026-10-02"))
    assert second.reuse_candidates == ()
    assert second.snapshot_id != first.snapshot_id


def test_canonical_bytes_sort_keys_and_keep_array_order():
    assert canonical_bytes({"b": 1, "a": [2, 1]}) == b'{"a":[2,1],"b":1}'


def test_plan_publication_with_regions_emits_region_manifests_and_pointers():
    entries = [_entry("grid/nyc", {"lims": 1})]
    region_manifest = {
        "region_id": "metro/nyc",
        "generation": "gen-nyc-abc",
        "golden_count": 50,
        "chunks": {"grid/nyc": {"sha256": "abc", "bytes": 10}},
    }
    plan = plan_publication(entries, None, _meta(regions={"metro/nyc": region_manifest}))
    assert plan.regions == {"metro/nyc": "gen-nyc-abc"}
    assert "regions/metro/nyc/gen/gen-nyc-abc" in plan.region_manifests
    assert "regions/metro/nyc/current" in plan.region_pointers
    pointer = plan.region_pointers["regions/metro/nyc/current"]
    assert pointer["current"] == "gen-nyc-abc"
    assert pointer["golden_count"] == 50
    assert plan.manifest["regions"] == {"metro/nyc": "gen-nyc-abc"}


def test_plan_publication_overflowing_8mib_moves_region_index_to_object():
    entries = [_entry("grid/nyc", {"lims": 1})]
    # Create an oversized regions map (>8 MiB)
    large_regions = {f"metro/city_{i:06d}": f"gen_{'x' * 64}_{i:06d}" for i in range(100000)}
    plan = plan_publication(entries, None, _meta(regions=large_regions))
    assert "region_index_key" in plan.manifest
    assert plan.manifest["region_index_key"] == "manifest/regions"
    assert "manifest/regions" in plan.manifest["keys"]
    assert "regions" not in plan.manifest


def test_hash_entries_plus_build_manifest_matches_plan_publication():
    """The split must be a refactor, not a fork: the builder reuses the hashing
    pass to build Region chunk maps from the same `objects/<sha>` bytes."""
    from src.export.publication import build_manifest, hash_entries

    entries = [
        _entry("grid/nyc", {"lims": 1, "inference_latency_ms": 4.5}),
        _entry("manifest", {"generated_at": "2026-10-10T00:00:00+00:00", "cities": ["nyc"]}),
    ]
    metadata = _meta(regions={"metro/nyc": {"generation": "g1", "golden_count": 2}})
    composed = plan_publication(entries, None, metadata)
    objects, keys = hash_entries(entries)
    split = build_manifest(objects, keys, None, metadata)

    assert split.snapshot_id == composed.snapshot_id
    assert split.objects == composed.objects
    assert split.manifest == composed.manifest
    assert split.region_manifests == composed.region_manifests
    assert split.region_pointers == composed.region_pointers


def test_a_region_dict_emits_a_generation_key_and_a_pointer():
    entries = [_entry("grid/nyc", {"lims": 1})]
    plan = plan_publication(
        entries,
        None,
        _meta(regions={"metro/nyc": {"generation": "g-nyc-7", "golden_count": 42}}),
    )
    assert "regions/metro/nyc/gen/g-nyc-7" in plan.region_manifests
    pointer = plan.region_pointers["regions/metro/nyc/current"]
    assert pointer["current"] == "g-nyc-7"
    assert pointer["golden_count"] == 42
    assert plan.manifest["regions"] == {"metro/nyc": "g-nyc-7"}


def test_a_bare_generation_string_emits_no_generation_key():
    """A string region value is the pre-HX-C2 shape: the map is carried in the
    manifest but nothing else is published, so no pointer can dangle."""
    plan = plan_publication([_entry("grid/nyc", {"lims": 1})], None, _meta(regions={"metro/nyc": "g1"}))
    assert plan.manifest["regions"] == {"metro/nyc": "g1"}
    assert plan.region_manifests == {}
    assert plan.region_pointers == {}
