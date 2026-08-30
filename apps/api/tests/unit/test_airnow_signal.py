"""Unit tests for the AirNow reporting-area → H3 leaf helpers (US-390)."""

import pytest

from src.spatial.airnow_signal import (
    AirNowObservation,
    AirNowRowType,
    aqi_shock_score,
    fold_observations_by_cell,
    map_reporting_area_to_h3,
    parse_reporting_area_row,
)


def test_parse_observed_row():
    line = "08/30/26|08/30/26|14:00|CDT|0|O|Y|Houston-Galveston-Brazoria|TX|29.7510|-95.3510|OZONE|105|Unhealthy for Sensitive Groups|No||Texas Commission on Environmental Quality"
    obs = parse_reporting_area_row(line)
    assert obs.area_name == "Houston-Galveston-Brazoria"
    assert obs.state == "TX"
    assert obs.lat == 29.7510
    assert obs.lng == -95.3510
    assert obs.parameter == "OZONE"
    assert obs.aqi == 105.0
    assert obs.category == "Unhealthy for Sensitive Groups"
    assert obs.row_type is AirNowRowType.OBSERVED
    assert obs.hour == "14:00"
    assert obs.action_day is True
    assert obs.agency == "Texas Commission on Environmental Quality"


def test_parse_forecast_row():
    line = "08/30/26|08/30/26||CDT|0|F|Y|Houston-Galveston-Brazoria|TX|29.7510|-95.3510|OZONE||Unhealthy for Sensitive Groups|No|https://example.com|TCEQ"
    obs = parse_reporting_area_row(line)
    assert obs.row_type is AirNowRowType.FORECAST
    assert obs.aqi is None
    assert obs.hour is None


def test_parse_yesterday_row():
    line = "08/30/26|08/29/26||CDT|-1|Y|Y|Aberdeen|SD|45.4680|-98.4940|PM10|16|Good|No||Agency"
    obs = parse_reporting_area_row(line)
    assert obs.row_type is AirNowRowType.YESTERDAY
    assert obs.day_offset == -1
    assert obs.aqi == 16.0


def test_parse_short_row_raises():
    with pytest.raises(ValueError, match="expected 17"):
        parse_reporting_area_row("a|b|c")


def test_aqi_shock_score_breakpoints():
    assert aqi_shock_score(None) == 0.0
    assert aqi_shock_score(-1) == 0.0
    assert aqi_shock_score(0) == 0.0  # Good
    assert aqi_shock_score(50) == 0.0  # Good (top edge)
    assert aqi_shock_score(51) == 0.2  # Moderate
    assert aqi_shock_score(100) == 0.2  # Moderate (top edge)
    assert aqi_shock_score(101) == 0.4  # USG
    assert aqi_shock_score(150) == 0.4  # USG (top edge)
    assert aqi_shock_score(151) == 0.6  # Unhealthy
    assert aqi_shock_score(200) == 0.6  # Unhealthy (top edge)
    assert aqi_shock_score(201) == 0.8  # Very Unhealthy
    assert aqi_shock_score(300) == 0.8  # Very Unhealthy (top edge)
    assert aqi_shock_score(301) == 1.0  # Hazardous
    assert aqi_shock_score(500) == 1.0  # Hazardous (top edge)
    assert aqi_shock_score(501) == 1.0  # Beyond max


def test_map_reporting_area_to_h3():
    obs = AirNowObservation(
        current_date="08/30/26",
        valid_date="08/30/26",
        hour="14:00",
        timezone="CDT",
        day_offset=0,
        row_type=AirNowRowType.OBSERVED,
        action_day=True,
        area_name="Houston-Galveston-Brazoria",
        state="TX",
        lat=29.7510,
        lng=-95.3510,
        parameter="OZONE",
        aqi=105.0,
        category="Unhealthy for Sensitive Groups",
        agency="TCEQ",
    )
    hierarchy = map_reporting_area_to_h3(obs)
    assert hierarchy["h3_res7"] and hierarchy["h3_res8"] and hierarchy["h3_res9"]
    # All three resolutions should be non-empty valid H3 strings
    assert hierarchy["h3_res7"].startswith("8")
    assert hierarchy["h3_res8"].startswith("8")
    assert hierarchy["h3_res9"].startswith("8")


def test_fold_observations_skips_forecast_and_yesterday():
    observed = AirNowObservation(
        current_date="08/30/26", valid_date="08/30/26", hour="14:00",
        timezone="CDT", day_offset=0, row_type=AirNowRowType.OBSERVED,
        action_day=True, area_name="Central LA CO", state="CA",
        lat=34.0663, lng=-118.2266, parameter="PM2.5",
        aqi=55, category="Moderate", agency="SCAQMD",
    )
    forecast = AirNowObservation(
        current_date="08/30/26", valid_date="08/31/26", hour=None,
        timezone="CDT", day_offset=1, row_type=AirNowRowType.FORECAST,
        action_day=True, area_name="Central LA CO", state="CA",
        lat=34.0663, lng=-118.2266, parameter="PM2.5",
        aqi=None, category="Moderate", agency="SCAQMD",
    )
    yesterday = AirNowObservation(
        current_date="08/30/26", valid_date="08/29/26", hour=None,
        timezone="CDT", day_offset=-1, row_type=AirNowRowType.YESTERDAY,
        action_day=True, area_name="Central LA CO", state="CA",
        lat=34.0663, lng=-118.2266, parameter="PM2.5",
        aqi=30, category="Good", agency="SCAQMD",
    )
    folded = fold_observations_by_cell([observed, forecast, yesterday])
    assert len(folded) == 1  # only the observed row counts
    cell = next(iter(folded.values()))
    assert cell["max_aqi"] == 55.0
    assert cell["shock"] == 0.2
    assert cell["count"] == 1


def test_fold_observations_aggregates_multiple():
    obs1 = AirNowObservation(
        current_date="08/30/26", valid_date="08/30/26", hour="14:00",
        timezone="CDT", day_offset=0, row_type=AirNowRowType.OBSERVED,
        action_day=True, area_name="Central LA CO", state="CA",
        lat=34.0663, lng=-118.2266, parameter="PM2.5",
        aqi=55, category="Moderate", agency="SCAQMD",
    )
    obs2 = AirNowObservation(
        current_date="08/30/26", valid_date="08/30/26", hour="14:00",
        timezone="CDT", day_offset=0, row_type=AirNowRowType.OBSERVED,
        action_day=True, area_name="Central LA CO", state="CA",
        lat=34.0663, lng=-118.2266, parameter="OZONE",
        aqi=120, category="Unhealthy for Sensitive Groups", agency="SCAQMD",
    )
    folded = fold_observations_by_cell([obs1, obs2])
    cell = next(iter(folded.values()))
    assert cell["max_aqi"] == 120.0
    assert cell["shock"] == 0.4
    assert cell["count"] == 2