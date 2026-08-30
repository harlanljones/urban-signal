"""Unit tests for the NOAA climate leaf module (US-173).

Leaf-only: imports no spine symbols (config / city_registry / geo_utils /
submarkets / producers). Pure geometry + missingness + H3-mapping logic, no
network.
"""

import math

from src.spatial.noaa_climate import (
    NoaaStation,
    daily_anomaly,
    daily_coverage,
    haversine_km,
    map_station_to_h3,
    nearest_station,
    obs_quality_ok,
    stations_within_bbox,
)


def test_haversine_km_same_point():
    assert haversine_km(41.8781, -87.6298, 41.8781, -87.6298) == 0.0


def test_haversine_km_chicago_to_nyc():
    d = haversine_km(41.8781, -87.6298, 40.7128, -74.0060)
    assert 1100 < d < 1200


def test_haversine_km_known_distance():
    # Chicago to LA ~ 2,800 km
    d = haversine_km(41.8781, -87.6298, 34.0522, -118.2437)
    assert 2700 < d < 3000


def test_stations_within_bbox_filters_correctly():
    chi = NoaaStation("USW00094846", 41.9603, -87.9317, 204.8, "CHICAGO O'HARE INTL AP")
    den = NoaaStation("USW00023062", 39.7633, -104.8694, 1611.2, "DENVER-STAPLETON")
    mia = NoaaStation("USW00012839", 25.7881, -80.3169, 1.5, "MIAMI INTL AP")
    chicago_bbox = {"min_lat": 41.64, "max_lat": 42.03, "min_lng": -87.94, "max_lng": -87.52}

    inside = stations_within_bbox([chi, den, mia], chicago_bbox)
    assert inside == [chi]


def test_nearest_station_picks_closest():
    center = (41.88, -87.63)
    stations = [
        NoaaStation("USW00094846", 41.9603, -87.9317, 204.8, "OHARE"),
        NoaaStation("USW00014819", 41.7867, -87.7524, 186.5, "MIDWAY"),
    ]
    best = nearest_station(stations, center[0], center[1])
    assert best is not None
    assert best.station_id == "USW00014819"


def test_nearest_station_empty_returns_none():
    assert nearest_station([], 40.0, -90.0) is None


def test_obs_quality_ok_accepts_clean():
    assert obs_quality_ok(150.0, ",,,") is True
    assert obs_quality_ok(0.0, ",,W,") is False


def test_obs_quality_ok_rejects_bad_flags():
    for flag in ("S", "H", "D", "G", "I", "K", "L", "M", "N", "O", "R", "W", "X", "Z"):
        assert obs_quality_ok(150.0, f",,{flag},") is False, f"flag {flag} should be rejected"


def test_obs_quality_ok_none_value():
    assert obs_quality_ok(None, ",,,") is False


def test_daily_coverage_all_ok():
    rows = [
        {"TMAX": 200, "TMAX_ATTRIBUTES": ",,,"},
        {"TMAX": 210, "TMAX_ATTRIBUTES": ",,,"},
        {"TMAX": 220, "TMAX_ATTRIBUTES": ",,,"},
    ]
    assert math.isclose(daily_coverage(rows, "TMAX"), 1.0)


def test_daily_coverage_partial():
    rows = [
        {"PRCP": 0, "PRCP_ATTRIBUTES": ",,,"},
        {"PRCP": None, "PRCP_ATTRIBUTES": ""},
        {"PRCP": 50, "PRCP_ATTRIBUTES": ",,1,"},
    ]
    assert math.isclose(daily_coverage(rows, "PRCP"), 2 / 3)


def test_daily_coverage_empty():
    assert daily_coverage([], "TMAX") == 0.0


def test_daily_anomaly_positive():
    assert daily_anomaly(300, 280) == 20.0


def test_daily_anomaly_negative():
    assert daily_anomaly(250, 280) == -30.0


def test_daily_anomaly_zero():
    assert daily_anomaly(280, 280) == 0.0


def test_map_station_to_h3_consistent_hierarchy():
    cells = map_station_to_h3(41.9603, -87.9317)
    assert set(cells) == {"h3_res7", "h3_res8", "h3_res9"}
    from src.spatial.h3_indexer import H3SpatialIndexer

    assert H3SpatialIndexer.get_parent(cells["h3_res9"], 8) == cells["h3_res8"]
    assert H3SpatialIndexer.get_parent(cells["h3_res8"], 7) == cells["h3_res7"]


def test_invalid_coordinates_raise():
    import pytest

    with pytest.raises(ValueError):
        map_station_to_h3(999.0, -87.6)