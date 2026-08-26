"""Unit tests for the EPA ECHO leaf module (US-170).

Leaf-only: imports no spine symbols (config / city_registry / geo_utils /
submarkets / producers). Pure geometry + severity logic, no network.
"""

from datetime import date

from src.spatial.epa_echo import (
    EchoEvent,
    EchoEventClass,
    EchoProgram,
    accumulate_cell_weight,
    event_severity,
    map_event_to_h3,
)


def test_map_event_to_h3_returns_consistent_hierarchy():
    evt = EchoEvent(
        lat=41.8781,
        lng=-87.6298,
        program=EchoProgram.CAA,
        event_class=EchoEventClass.VIOLATION,
        event_date=date(2024, 1, 1),
        facility_id="IL00000000",
    )
    cells = map_event_to_h3(evt)
    assert set(cells) == {"h3_res7", "h3_res8", "h3_res9"}
    # Parent chain must be consistent: res9 parent is res8, res8 parent is res7.
    from src.spatial.h3_indexer import H3SpatialIndexer

    assert H3SpatialIndexer.get_parent(cells["h3_res9"], 8) == cells["h3_res8"]
    assert H3SpatialIndexer.get_parent(cells["h3_res8"], 7) == cells["h3_res7"]


def test_severity_weights_ordered():
    assert (
        event_severity(
            EchoEvent(0.0, 0.0, EchoProgram.RCRA, EchoEventClass.INSPECTION, date(2024, 1, 1), "x")
        )
        < event_severity(
            EchoEvent(0.0, 0.0, EchoProgram.RCRA, EchoEventClass.VIOLATION, date(2024, 1, 1), "x")
        )
        < event_severity(
            EchoEvent(0.0, 0.0, EchoProgram.RCRA, EchoEventClass.ENFORCEMENT, date(2024, 1, 1), "x")
        )
        < event_severity(
            EchoEvent(0.0, 0.0, EchoProgram.RCRA, EchoEventClass.PENALTY, date(2024, 1, 1), "x")
        )
    )


def test_recency_decay_reduces_older_events():
    as_of = date(2025, 1, 1)
    fresh = event_severity(
        EchoEvent(0.0, 0.0, EchoProgram.CWA, EchoEventClass.VIOLATION, date(2025, 1, 1), "x"),
        as_of=as_of,
    )
    old = event_severity(
        EchoEvent(
            0.0,
            0.0,
            EchoProgram.CWA,
            EchoEventClass.VIOLATION,
            date(2000, 1, 1),
            "x",
        ),
        as_of=as_of,
    )
    assert old < fresh
    assert fresh == 1.0  # event dated at as_of => no decay, equals base weight


def test_future_dated_event_has_zero_severity():
    future = event_severity(
        EchoEvent(
            0.0,
            0.0,
            EchoProgram.SDWA,
            EchoEventClass.PENALTY,
            date(2099, 1, 1),
            "x",
        )
    )
    assert future == 0.0


def test_accumulate_cell_weight_folds_into_tally():
    tally: dict[str, float] = {}
    accumulate_cell_weight(tally, "cellA", 1.5)
    accumulate_cell_weight(tally, "cellA", 0.5)
    accumulate_cell_weight(tally, "cellB", 2.0)
    assert tally == {"cellA": 2.0, "cellB": 2.0}


def test_invalid_coordinates_raise():
    import pytest

    with pytest.raises(ValueError):
        map_event_to_h3(
            EchoEvent(999.0, -87.6, EchoProgram.CAA, EchoEventClass.VIOLATION, date(2024, 1, 1), "x")
        )
