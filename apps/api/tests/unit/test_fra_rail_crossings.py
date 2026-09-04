"""Unit tests for the FRA rail crossing leaf module (US-422).

Leaf-only: imports no spine symbols (config / city_registry / geo_utils /
submarkets / producers). Pure geometry + severity logic, no network.
"""

from datetime import date

import pytest

from src.spatial.fra_rail_crossings import (
    CrossingType,
    RailCrossing,
    RailIncident,
    WarningDeviceClass,
    accumulate_cell_weight,
    daily_train_movements,
    incident_severity,
    map_crossing_to_h3,
    map_incident_to_h3,
    rail_severance_index,
)
from src.spatial.h3_indexer import H3SpatialIndexer


def _crossing(**overrides) -> RailCrossing:
    defaults = dict(
        lat=41.8781,
        lng=-87.6298,
        crossing_id="123456A",
        warning_device=WarningDeviceClass.PASSIVE,
        crossing_type=CrossingType.PUBLIC,
        total_tracks=1,
        day_thru=10,
        night_thru=5,
        max_train_speed=40.0,
    )
    defaults.update(overrides)
    return RailCrossing(**defaults)


def _incident(**overrides) -> RailIncident:
    defaults = dict(
        lat=41.8781,
        lng=-87.6298,
        crossing_id="123456A",
        incident_date=date(2024, 6, 1),
        fatalities=0,
        injuries=1,
    )
    defaults.update(overrides)
    return RailIncident(**defaults)


def test_map_crossing_to_h3_returns_consistent_hierarchy():
    cells = map_crossing_to_h3(_crossing())
    assert set(cells) == {"h3_res7", "h3_res8", "h3_res9"}
    assert H3SpatialIndexer.get_parent(cells["h3_res9"], 8) == cells["h3_res8"]
    assert H3SpatialIndexer.get_parent(cells["h3_res8"], 7) == cells["h3_res7"]


def test_map_incident_to_h3_returns_consistent_hierarchy():
    cells = map_incident_to_h3(_incident())
    assert set(cells) == {"h3_res7", "h3_res8", "h3_res9"}


def test_invalid_crossing_coordinates_raise():
    with pytest.raises(ValueError):
        map_crossing_to_h3(_crossing(lat=999.0))


def test_daily_train_movements_sums_day_and_night():
    assert daily_train_movements(_crossing(day_thru=10, night_thru=5)) == 15


def test_daily_train_movements_ignores_negative_inputs():
    assert daily_train_movements(_crossing(day_thru=-3, night_thru=5)) == 5


def test_rail_severance_index_passive_exceeds_gated():
    passive = rail_severance_index(_crossing(warning_device=WarningDeviceClass.PASSIVE))
    gated = rail_severance_index(_crossing(warning_device=WarningDeviceClass.ACTIVE_GATES))
    assert passive > gated


def test_rail_severance_index_scales_with_tracks_and_movements():
    base = rail_severance_index(_crossing(total_tracks=1, day_thru=10, night_thru=0))
    doubled_tracks = rail_severance_index(_crossing(total_tracks=2, day_thru=10, night_thru=0))
    assert doubled_tracks == pytest.approx(base * 2.0)


def test_rail_severance_index_private_crossing_scaled_down():
    public = rail_severance_index(_crossing(crossing_type=CrossingType.PUBLIC))
    private = rail_severance_index(_crossing(crossing_type=CrossingType.PRIVATE))
    assert private == pytest.approx(public * 0.4)


def test_rail_severance_index_zero_movements_is_zero():
    assert rail_severance_index(_crossing(day_thru=0, night_thru=0)) == 0.0


def test_incident_severity_fatalities_outweigh_injuries():
    fatal = incident_severity(_incident(fatalities=1, injuries=0), as_of=date(2024, 6, 1))
    injury_only = incident_severity(_incident(fatalities=0, injuries=1), as_of=date(2024, 6, 1))
    assert fatal == pytest.approx(injury_only * 5.0)


def test_incident_severity_no_harm_is_zero():
    assert incident_severity(_incident(fatalities=0, injuries=0)) == 0.0


def test_incident_severity_future_dated_is_zero():
    assert incident_severity(_incident(incident_date=date(2099, 1, 1))) == 0.0


def test_incident_severity_recency_decay():
    as_of = date(2026, 1, 1)
    fresh = incident_severity(_incident(incident_date=as_of, fatalities=1, injuries=0), as_of=as_of)
    old = incident_severity(_incident(incident_date=date(2000, 1, 1), fatalities=1, injuries=0), as_of=as_of)
    assert old < fresh
    assert fresh == 5.0  # no decay at as_of


def test_accumulate_cell_weight_folds_into_tally():
    tally: dict[str, float] = {}
    accumulate_cell_weight(tally, "cellA", 3.0)
    accumulate_cell_weight(tally, "cellA", 2.0)
    accumulate_cell_weight(tally, "cellB", 1.0)
    assert tally == {"cellA": 5.0, "cellB": 1.0}
