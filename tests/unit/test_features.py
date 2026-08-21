"""Unit tests for CapEx time-decay, 311 shift dynamics, LIMS score, and DuckDB analytical pipeline."""

import math
from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest
from src.features.lims_calculator import LIMSCalculator
from src.features.pipeline import SpatialFeaturePipeline
from src.features.shift_dynamics import ComplaintShiftDynamics
from src.features.time_decay import TimeDecayedCapExCalculator
from src.schemas.models import ComplaintCategory


def test_time_decay_capex():
    calc = TimeDecayedCapExCalculator(halflife_days=180.0)
    now = datetime.now(timezone.utc)

    # Event occurring right now: weight = 1.0
    w_now = calc.calculate_decay_weight(now, now)
    assert pytest.approx(w_now, rel=1e-3) == 1.0

    # Event occurring 180 days ago: weight = 0.5
    w_180d = calc.calculate_decay_weight(now, now - timedelta(days=180))
    assert pytest.approx(w_180d, rel=1e-3) == 0.5

    # Event occurring 360 days ago: weight = 0.25
    w_360d = calc.calculate_decay_weight(now, now - timedelta(days=360))
    assert pytest.approx(w_360d, rel=1e-3) == 0.25

    # Cell CapEx density calculation
    permits = [
        (1000000.0, now),
        (500000.0, now - timedelta(days=180)),
    ]
    # Expected decayed sum = 1,000,000 * 1.0 + 500,000 * 0.5 = 1,250,000
    # Density for area = 0.1053 km²
    density = calc.compute_cell_capex_density(permits, cell_area_km2=0.1053, as_of_date=now)
    assert pytest.approx(density, rel=1e-2) == 1250000.0 / 0.1053


def test_complaint_shift_dynamics():
    shift = ComplaintShiftDynamics(epsilon=1.0)

    # Classification
    assert shift.classify_complaint_type("HEAT/HOT WATER") == ComplaintCategory.NEGLECT
    assert shift.classify_complaint_type("Noise - Commercial") == ComplaintCategory.QOL
    assert shift.classify_complaint_type("Graffiti") == ComplaintCategory.OTHER

    # Shift ratio: 10 QoL complaints, 2 Neglect complaints
    # Ratio = (10 + 1) / (2 + 1) = 11 / 3 = 3.6667
    r = shift.calculate_ratio(count_qol=10, count_neglect=2)
    assert pytest.approx(r, rel=1e-3) == 11.0 / 3.0

    # Velocity / Acceleration
    r_recent, r_prior, delta = shift.calculate_ratio_delta(
        recent_qol=20, recent_neglect=2,
        prior_qol=5, prior_neglect=10,
    )
    assert delta > 0.0  # Demonstrates accelerating commercial/QoL momentum


def test_lims_calculator():
    lims = LIMSCalculator(alpha=0.35, beta=0.25, gamma=0.20, delta=0.20)

    # Average baseline metrics -> score near 50.0
    score_mid = lims.compute_scaled_lims(
        capex=50000.0,
        permit_velocity=0.05,
        shift_ratio_311=1.0,
        sla_activations=1.0,
    )
    assert 45.0 <= score_mid <= 55.0

    # High growth / catalyst metrics -> high score (>85.0)
    score_high = lims.compute_scaled_lims(
        capex=500000.0,
        permit_velocity=0.80,
        shift_ratio_311=4.5,
        sla_activations=8.0,
    )
    assert score_high >= 85.0


def test_duckdb_spatial_feature_pipeline(sample_permit_event, sample_complaint_event, sample_sla_event, sample_deed_event):
    pipeline = SpatialFeaturePipeline(db_path=":memory:")

    # Insert sample events
    pipeline.insert_permits(pd.DataFrame([sample_permit_event.model_dump()]))
    pipeline.insert_complaints(pd.DataFrame([sample_complaint_event.model_dump()]))
    pipeline.insert_sla(pd.DataFrame([sample_sla_event.model_dump()]))
    pipeline.insert_deeds(pd.DataFrame([sample_deed_event.model_dump()]))

    # Compute features
    feats = pipeline.compute_h3_cell_features(
        h3_index="892a1072893ffff",
        resolution=9,
        as_of_date=datetime.now(timezone.utc),
    )

    assert feats["h3_index"] == "892a1072893ffff"
    assert feats["h3_resolution"] == 9
    assert feats["permit_count_60d"] >= 1
    assert feats["capex_density_decayed"] > 0.0
    assert "lims_score" in feats
