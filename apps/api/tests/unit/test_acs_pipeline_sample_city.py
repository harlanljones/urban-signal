"""End-to-end ACS pipeline using offline fixtures (US-361)."""

from __future__ import annotations

import json
from pathlib import Path

from src.spatial.acs_pipeline import (
    ACSPipelineConfig,
    ingest_city_from_rows,
    relative_moe_flags,
)
from src.spatial.acs_join import BGToH3Resolver
from src.spatial.acs_client import variables_for_features


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "acs"


def test_ingest_rows_to_h3_and_flag_moe():
    # Build a local BG→H3 resolver where both BGs fall into the same H3 cell.
    bg_to_h3 = BGToH3Resolver.from_local_xwalks([FIXTURES / "xwalk_sample.csv"], resolution=9)
    rows = json.loads((FIXTURES / "sample_rows.json").read_text(encoding="utf-8"))
    header = rows[0]
    body = [dict(zip(header, r)) for r in rows[1:]]
    feats = ["total_population", "poverty_rate", "median_travel_time"]
    cfg = ACSPipelineConfig(feature_names=feats, h3_resolution=9)
    baselines = ingest_city_from_rows(body, bg_to_h3, cfg)
    # Because all BG centroids are identical in the fixture, only one H3 cell is present.
    assert len(baselines) == 1
    cell = baselines[0]
    # total_population sums and MOE in quadrature
    pop_est, pop_moe = cell.features["total_population"]
    assert pop_est == 300.0
    assert abs(pop_moe - ((10.0**2 + 15.0**2) ** 0.5)) < 1e-9
    # poverty_rate over the two BGs: (20+40)/(80+160) = 0.25
    pov_est, pov_moe = cell.features["poverty_rate"]
    assert abs(pov_est - 0.25) < 1e-9
    # relative-MOE flags at default 50% threshold = both unflagged
    flags = relative_moe_flags(cell.features)
    assert flags["total_population"] is False
    assert flags["poverty_rate"] is False
