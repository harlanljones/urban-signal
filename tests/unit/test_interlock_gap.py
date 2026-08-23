"""Unit tests for the interlock gap metric script."""

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "interlock_gap.py"
_spec = importlib.util.spec_from_file_location("interlock_gap", _SCRIPT)
interlock_gap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(interlock_gap)


SPINE = {"src/config.py", "src/spatial/city_registry.py"}


def test_wide_gap_signature():
    rows = [
        (401, 0, "src/spatial/cities/seattle.py"),
        (23, 0, "src/config.py"),
        (18, 0, "src/spatial/city_registry.py"),
    ]
    gap = interlock_gap.compute_gap(rows, SPINE)
    assert gap.spine_files == 2 and gap.leaf_files == 1
    assert gap.file_share == 2 / 3
    assert abs(gap.line_share - 41 / 442) < 1e-9
    assert gap.reading.startswith("wide gap")


def test_high_both_axes_means_not_independent():
    rows = [(500, 0, "src/config.py"), (300, 0, "src/spatial/city_registry.py")]
    gap = interlock_gap.compute_gap(rows, SPINE)
    assert gap.file_share == 1.0 and gap.line_share == 1.0
    assert "not independent" in gap.reading


def test_empty_range_is_reported_not_crashed():
    gap = interlock_gap.compute_gap([], SPINE)
    assert gap.total_files == 0
    assert gap.file_share == 0.0
    assert gap.reading == "no changes in range"


def test_binary_rows_count_as_one_line():
    rows = [(0, 0, "docs/img.png"), (5, 0, "src/config.py")]
    gap = interlock_gap.compute_gap(rows, SPINE)
    assert gap.leaf_lines == 1
    assert gap.spine_lines == 5


def test_manifest_loader_skips_comments_and_blanks():
    manifest = Path(__file__).resolve().parents[2] / "docs" / "agents" / "spine-manifest.txt"
    paths = interlock_gap.load_manifest(str(manifest))
    assert "src/config.py" in paths
    assert all(not p.startswith("#") for p in paths)
