"""Unit tests for the FMCSA fleet-density leaf module (US-423).

Leaf-only: imports no spine symbols (config / city_registry / geo_utils /
submarkets / producers). Pure geometry + weighting logic, no network.
"""

from src.spatial.fmcsa_fleet_density import (
    HAZMAT_WEIGHT_MULTIPLIER,
    MAX_POWER_UNITS_CONTRIBUTION,
    CarrierFleetRecord,
    accumulate_fleet_density,
    carrier_freight_weight,
    hazmat_share,
    map_carrier_to_h3,
)
from src.spatial.h3_indexer import H3SpatialIndexer


def _carrier(**overrides):
    base = dict(
        dot_number="123456",
        lat=41.8781,
        lng=-87.6298,
        total_power_units=10,
        hazmat_flag=False,
    )
    base.update(overrides)
    return CarrierFleetRecord(**base)


def test_carrier_freight_weight_basic():
    rec = _carrier(total_power_units=20)
    assert carrier_freight_weight(rec) == 20.0


def test_carrier_freight_weight_floor_for_zero_units():
    rec = _carrier(total_power_units=0)
    assert carrier_freight_weight(rec) == 1.0


def test_carrier_freight_weight_negative_units_floors_to_one():
    rec = _carrier(total_power_units=-5)
    assert carrier_freight_weight(rec) == 1.0


def test_carrier_freight_weight_hazmat_multiplier():
    plain = _carrier(total_power_units=20, hazmat_flag=False)
    hazmat = _carrier(total_power_units=20, hazmat_flag=True)
    assert carrier_freight_weight(hazmat) == carrier_freight_weight(plain) * HAZMAT_WEIGHT_MULTIPLIER


def test_carrier_freight_weight_clamps_mega_fleet():
    rec = _carrier(total_power_units=1_000_000)
    assert carrier_freight_weight(rec) == float(MAX_POWER_UNITS_CONTRIBUTION)


def test_map_carrier_to_h3_matches_indexer_hierarchy():
    rec = _carrier(lat=41.8781, lng=-87.6298)
    cells = map_carrier_to_h3(rec)
    assert set(cells) == {"h3_res7", "h3_res8", "h3_res9"}
    assert H3SpatialIndexer.get_parent(cells["h3_res9"], 8) == cells["h3_res8"]
    assert H3SpatialIndexer.get_parent(cells["h3_res8"], 7) == cells["h3_res7"]


def test_map_carrier_to_h3_invalid_coordinates_raise():
    import pytest

    rec = _carrier(lat=999.0, lng=-87.6298)
    with pytest.raises(ValueError):
        map_carrier_to_h3(rec)


def test_accumulate_fleet_density_sums_multiple_carriers():
    tally: dict = {}
    accumulate_fleet_density(tally, "cellA", _carrier(total_power_units=10))
    accumulate_fleet_density(tally, "cellA", _carrier(total_power_units=15, hazmat_flag=True))
    accumulate_fleet_density(tally, "cellB", _carrier(total_power_units=5))
    assert tally["cellA"] == 10.0 + 15.0 * HAZMAT_WEIGHT_MULTIPLIER
    assert tally["cellB"] == 5.0


def test_hazmat_share_basic():
    records = [
        _carrier(hazmat_flag=True),
        _carrier(hazmat_flag=True),
        _carrier(hazmat_flag=False),
        _carrier(hazmat_flag=False),
    ]
    assert hazmat_share(records) == 0.5


def test_hazmat_share_empty_batch():
    assert hazmat_share([]) == 0.0


def test_hazmat_share_all_hazmat():
    records = [_carrier(hazmat_flag=True) for _ in range(3)]
    assert hazmat_share(records) == 1.0
