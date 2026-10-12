"""Region promotion gate: every refusal branch, atomicity, and the input hash (HX-C1)."""

import json
from pathlib import Path

import pytest

from src.export import regions
from src.export.regions import (
    MEASURED_FLOOR_RATIO,
    PromotionRefused,
    load_pointer,
    promote_region,
    region_input_hash,
    stage_region,
)

REGION = "metro/nyc"


def stage(out: Path, *, plan="plan-a", golden=100, measured=10, chunks=None, **kw):
    chunks = chunks or {"gridtiles_res9/a": b'{"a":1}', "gridtiles_res9/b": b'{"b":2}'}
    return stage_region(
        out, region_id=REGION, chunks=chunks, input_hash=kw.pop("input_hash", "in"),
        plan_hash=plan, golden_count=golden, measured_count=measured, **kw,
    )


def promote(out: Path, manifest, *, golden=100, plan="plan-a", **kw):
    return promote_region(out, REGION, manifest.generation, expected_golden=golden, expected_plan_hash=plan, **kw)


def refusal(out: Path, manifest, **kw) -> list[str]:
    with pytest.raises(PromotionRefused) as caught:
        promote(out, manifest, **kw)
    return caught.value.reasons


def test_first_promotion_makes_the_generation_current(tmp_path):
    manifest = stage(tmp_path)
    pointer = promote(tmp_path, manifest, now="2026-10-12T00:00:00Z")
    assert (pointer.current, pointer.previous, pointer.golden_count) == (manifest.generation, None, 100)
    assert load_pointer(tmp_path, REGION) == pointer


def test_second_promotion_keeps_the_old_generation_as_previous(tmp_path):
    first = stage(tmp_path)
    promote(tmp_path, first)
    second = stage(tmp_path, chunks={"gridtiles_res9/a": b'{"a":9}'})
    pointer = promote(tmp_path, second)
    assert (pointer.current, pointer.previous) == (second.generation, first.generation)


def test_repromoting_the_current_generation_is_idempotent(tmp_path):
    first = stage(tmp_path)
    promote(tmp_path, first)
    second = stage(tmp_path, chunks={"gridtiles_res9/a": b'{"a":9}'})
    promote(tmp_path, second)
    again = promote(tmp_path, second)
    assert (again.current, again.previous) == (second.generation, first.generation)


def test_a_tampered_chunk_is_refused_even_though_the_manifest_claims_it_verified(tmp_path):
    manifest = stage(tmp_path)
    digest = manifest.chunks["gridtiles_res9/a"]["sha256"]
    (tmp_path / "objects" / digest).write_bytes(b'{"a":"tampered"}')
    assert any("do not match" in r for r in refusal(tmp_path, manifest))
    assert load_pointer(tmp_path, REGION) is None


def test_a_missing_chunk_is_refused(tmp_path):
    manifest = stage(tmp_path)
    (tmp_path / "objects" / manifest.chunks["gridtiles_res9/b"]["sha256"]).unlink()
    assert any("missing" in r for r in refusal(tmp_path, manifest))


def test_a_truncated_chunk_with_a_valid_hash_name_is_refused_on_size(tmp_path):
    manifest = stage(tmp_path)
    spec = manifest.chunks["gridtiles_res9/a"]
    corrupted = tmp_path / "regions" / REGION / "gen" / f"{manifest.generation}.json"
    document = json.loads(corrupted.read_text())
    document["chunks"]["gridtiles_res9/a"]["bytes"] = spec["bytes"] + 5
    corrupted.write_text(json.dumps(document))
    assert any("size" in r for r in refusal(tmp_path, manifest))


def test_golden_count_must_equal_the_plan_exactly(tmp_path):
    manifest = stage(tmp_path, golden=99)
    assert any("golden count 99 != expected 100" in r for r in refusal(tmp_path, manifest, golden=100))


def test_a_manifest_built_from_another_plan_is_refused(tmp_path):
    manifest = stage(tmp_path, plan="plan-stale")
    assert any("different coverage plan" in r for r in refusal(tmp_path, manifest, plan="plan-a"))


def test_a_region_with_no_measured_cells_is_refused(tmp_path):
    manifest = stage(tmp_path, measured=0)
    assert any("no measured cells" in r for r in refusal(tmp_path, manifest))


def test_a_measured_drop_below_the_floor_keeps_the_previous_generation(tmp_path):
    first = stage(tmp_path, measured=100)
    promote(tmp_path, first)
    outage = stage(tmp_path, measured=int(100 * MEASURED_FLOOR_RATIO) - 1, chunks={"gridtiles_res9/a": b"{}"})
    assert any("feed outage" in r for r in refusal(tmp_path, outage))
    assert load_pointer(tmp_path, REGION).current == first.generation


def test_a_measured_drop_exactly_at_the_floor_is_allowed(tmp_path):
    first = stage(tmp_path, measured=100)
    promote(tmp_path, first)
    at_floor = stage(tmp_path, measured=int(100 * MEASURED_FLOOR_RATIO), chunks={"gridtiles_res9/a": b"{}"})
    assert promote(tmp_path, at_floor).current == at_floor.generation


def test_golden_drift_without_a_plan_change_is_refused(tmp_path):
    first = stage(tmp_path, golden=100)
    promote(tmp_path, first)
    drifted = stage(tmp_path, golden=90, chunks={"gridtiles_res9/a": b"{}"})
    assert any("without a plan change" in r for r in refusal(tmp_path, drifted, golden=90))


def test_a_coverage_edit_needs_an_announced_rebaseline(tmp_path):
    first = stage(tmp_path, golden=100, plan="plan-a")
    promote(tmp_path, first)
    edited = stage(tmp_path, golden=90, plan="plan-b", chunks={"gridtiles_res9/a": b"{}"})
    assert any("rebaseline" in r for r in refusal(tmp_path, edited, golden=90, plan="plan-b"))
    pointer = promote(tmp_path, edited, golden=90, plan="plan-b", rebaseline="anchor asset update")
    assert (pointer.current, pointer.golden_count) == (edited.generation, 90)


def test_every_failing_check_is_reported_together(tmp_path):
    manifest = stage(tmp_path, golden=1, measured=0, plan="plan-x")
    reasons = refusal(tmp_path, manifest, golden=100, plan="plan-a")
    assert len(reasons) == 3


def test_a_crash_while_swapping_the_pointer_leaves_the_old_generation_current(tmp_path, monkeypatch):
    first = stage(tmp_path)
    promote(tmp_path, first)
    second = stage(tmp_path, chunks={"gridtiles_res9/a": b'{"a":9}'})

    def explode(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(regions.os, "replace", explode)
    with pytest.raises(OSError):
        promote(tmp_path, second)
    monkeypatch.undo()
    assert load_pointer(tmp_path, REGION).current == first.generation
    assert not [p for p in (tmp_path / "regions" / REGION).iterdir() if p.name.startswith(".tmp-")]


def test_staging_alone_never_changes_current(tmp_path):
    first = stage(tmp_path)
    promote(tmp_path, first)
    stage(tmp_path, chunks={"gridtiles_res9/a": b'{"a":9}'})
    assert load_pointer(tmp_path, REGION).current == first.generation


def test_identical_chunks_share_one_object_and_one_generation(tmp_path):
    a = stage(tmp_path)
    b = stage(tmp_path)
    assert a.generation == b.generation
    assert len(list((tmp_path / "objects").iterdir())) == 2


def test_input_hash_ignores_feed_order_and_tracks_every_input():
    base = {"plan_hash": "p", "model_id": "m", "feed_watermarks": {"a": "1", "b": "2"}}
    assert region_input_hash(**base) == region_input_hash(**{**base, "feed_watermarks": {"b": "2", "a": "1"}})
    changed = [
        {"plan_hash": "q"}, {"model_id": "n"}, {"builder_revision": "2"},
        {"feed_watermarks": {"a": "1", "b": "3"}}, {"context_sha": "c"}, {"national_sha": "d"},
    ]
    hashes = {region_input_hash(**{**base, **c}) for c in changed} | {region_input_hash(**base)}
    assert len(hashes) == len(changed) + 1

