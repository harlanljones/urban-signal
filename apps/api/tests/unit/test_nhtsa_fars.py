"""Unit tests for the NHTSA FARS leaf module (US-422).

Leaf-only: imports no spine symbols (config / city_registry / geo_utils /
submarkets / producers). Pure geometry + severity logic, no network.
"""

from datetime import date

import pytest

from src.spatial.h3_indexer import H3SpatialIndexer
from src.spatial.nhtsa_fars import (
    FarsCrash,
    LightCondition,
    accumulate_cell_fatal_stats,
    map_crash_to_h3,
    pedestrian_fatality_ratio,
    pedestrian_vulnerability_index,
    rolling_window_crashes,
    vision_zero_density,
)


def _crash(**overrides) -> FarsCrash:
    defaults = dict(
        lat=41.8781,
        lng=-87.6298,
        st_case="171234",
        crash_date=date(2024, 6, 1),
        fatals=1,
        peds=0,
        drunk_dr=0,
        light_cond=LightCondition.DAYLIGHT,
    )
    defaults.update(overrides)
    return FarsCrash(**defaults)


def test_map_crash_to_h3_returns_consistent_hierarchy():
    crash = _crash()
    cells = map_crash_to_h3(crash)
    assert set(cells) == {"h3_res7", "h3_res8", "h3_res9"}
    assert H3SpatialIndexer.get_parent(cells["h3_res9"], 8) == cells["h3_res8"]
    assert H3SpatialIndexer.get_parent(cells["h3_res8"], 7) == cells["h3_res7"]


def test_invalid_coordinates_raise():
    with pytest.raises(ValueError):
        map_crash_to_h3(_crash(lat=999.0))


def test_pedestrian_fatality_ratio_basic():
    assert pedestrian_fatality_ratio(_crash(fatals=2, peds=1)) == 0.5


def test_pedestrian_fatality_ratio_zero_fatals_guard():
    assert pedestrian_fatality_ratio(_crash(fatals=0, peds=0)) == 0.0


def test_pedestrian_fatality_ratio_clamps_peds_to_fatals():
    # Malformed row: more pedestrian fatalities recorded than total fatals.
    assert pedestrian_fatality_ratio(_crash(fatals=1, peds=3)) == 1.0


def test_accumulate_cell_fatal_stats_folds_multiple_crashes():
    stats: dict[str, dict[str, float]] = {}
    accumulate_cell_fatal_stats(stats, "cellA", _crash(fatals=1, peds=1, drunk_dr=1))
    accumulate_cell_fatal_stats(stats, "cellA", _crash(fatals=2, peds=0, drunk_dr=0))
    accumulate_cell_fatal_stats(stats, "cellB", _crash(fatals=1, peds=1))

    assert stats["cellA"] == {
        "crash_count": 2.0,
        "fatal_count": 3.0,
        "ped_fatal_count": 1.0,
        "drunk_crash_count": 1.0,
    }
    assert stats["cellB"]["fatal_count"] == 1.0


def test_rolling_window_crashes_filters_by_age():
    as_of = date(2026, 9, 1)
    in_window = _crash(crash_date=date(2024, 9, 2))  # ~2 years old
    out_of_window = _crash(crash_date=date(2020, 1, 1))  # ~6.5 years old
    future = _crash(crash_date=date(2026, 12, 1))  # data-entry noise
    result = rolling_window_crashes([in_window, out_of_window, future], as_of, window_years=3)
    assert result == [in_window]


def test_rolling_window_crashes_includes_boundary():
    as_of = date(2026, 9, 1)
    boundary = _crash(crash_date=as_of)
    assert rolling_window_crashes([boundary], as_of, window_years=3) == [boundary]


def test_vision_zero_density_scales_with_fatal_count():
    low = vision_zero_density({"fatal_count": 1.0}, resolution=9)
    high = vision_zero_density({"fatal_count": 4.0}, resolution=9)
    assert high == pytest.approx(low * 4.0)


def test_vision_zero_density_empty_cell_is_zero():
    assert vision_zero_density({}, resolution=9) == 0.0


def test_pedestrian_vulnerability_index_zero_crashes():
    assert pedestrian_vulnerability_index({"crash_count": 0.0}) == 0.0


def test_pedestrian_vulnerability_index_rewards_volume_at_equal_ratio():
    low_volume = pedestrian_vulnerability_index({"crash_count": 1.0, "ped_fatal_count": 1.0})
    high_volume = pedestrian_vulnerability_index({"crash_count": 10.0, "ped_fatal_count": 10.0})
    # Same ped-fatality ratio (1.0) in both cells, but the higher-volume
    # corridor must rank above the single-crash cell.
    assert high_volume > low_volume
