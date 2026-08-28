"""Unit tests for ACS client helpers using offline fixtures (US-361)."""

from __future__ import annotations

import json
from pathlib import Path

from src.spatial.acs_client import rows_to_bgrows, variables_for_features


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "acs"


def test_rows_to_bgrows_parses_estimates_and_moes():
    rows = json.loads((FIXTURES / "sample_rows.json").read_text(encoding="utf-8"))
    header = rows[0]
    body = [dict(zip(header, r)) for r in rows[1:]]
    needed = variables_for_features(
        ["total_population", "median_household_income", "poverty_rate", "cost_burden_30pct_share", "median_travel_time"]
    )
    bgrows = rows_to_bgrows(body, needed)
    # two block groups in the fixture
    assert {r.bg_fips12 for r in bgrows} == {"220710001001", "220710001002"}
    # Check a couple of parsed values
    bg1 = next(r for r in bgrows if r.bg_fips12 == "220710001001")
    assert bg1.values["B01003_001E"] == (100.0, 10.0)
    assert bg1.values["B19013_001E"] == (50000.0, 4000.0)
