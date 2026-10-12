"""Tests for region failure-domain drill (ADR-0010 Stage C, HX-C6)."""

from __future__ import annotations

import sys
from pathlib import Path

# Add repo root to path so scripts can be imported
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.region_failure_drill import run_drill


def test_region_failure_drill_retains_previous_generation_and_refuses_corrupted():
    summary = run_drill(verbose=False)
    assert summary["pointer_intact"] is True
    assert summary["retained_generation"] is not None
    assert summary["corrupted_generation_refused"] != summary["retained_generation"]
    assert summary["feed_outage_generation_refused"] != summary["retained_generation"]
