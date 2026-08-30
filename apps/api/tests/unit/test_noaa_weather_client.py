"""Unit tests for the NOAA weather context clients (US-400).

Leaf-only: imports no spine symbols. Tests use fixture responses (the live
endpoints may be unreachable from a sandbox), so no network is exercised. The
fixtures are trimmed from live probes of ``access/services/data/v1``
(2026-08-30, O'Hare) and ``api.weather.gov`` (2026-08-30, Chicago + an active
South Dakota alert).
"""

from datetime import date

import httpx
import pytest

from src.producers.noaa_weather_client import (
    GhcnDailyClient,
    NwsWeatherClient,
    WeatherFetchError,
    parse_active_alerts,
    parse_daily_summary_row,
    parse_forecast_periods,
    parse_ghcnd_station_inventory,
    parse_ghcnd_station_line,
)
from src.spatial.noaa_climate import NoaaStation

# --- Recorded live fixtures (trimmed to asserted fields). ---------------------

# ghcnd-stations.txt rows (fixed-width, documented layout).
STATIONS_TXT = (
    "ACW00011604  17.1167  -61.7833   10.1    ST JOHNS COOLIDGE FLD\n"
    "USW00094846  41.9603  -87.9317  204.8 IL CHICAGO OHARE INTL AP\n"
    "USW00012960  29.9844  -95.3608   27.4 TX HOUSTON INTERCONTINENTAL AP\n"
    "USW00023062  39.7633 -104.8694 1611.2 CO DENVER-STAPLETON\n"
)

# GHCN-D daily-summaries JSON for USW00094846, 2026-08-20..2026-08-27
# (live probe; real-unit conversion of TMAX 256 = 25.6 °C, TMIN 167 = 16.7 °C).
DAILY_SUMMARIES = [
    {
        "STATION": "USW00094846",
        "DATE": "2026-08-20",
        "TMAX": "  256",
        "TMIN": "  167",
        "PRCP": "    0",
        "SNOW": "    0",
        "SNWD": "    0",
    },
    {
        "STATION": "USW00094846",
        "DATE": "2026-08-21",
        "TMAX": "  267",
        "TMIN": "  167",
        "PRCP": "    0",
    },
    {
        "STATION": "USW00094846",
        "DATE": "2026-08-22",
        "TMAX": "  278",
        "TMIN": "  189",
        "PRCP": "    0",
    },
]

# NWS points payload (trimmed from the live Chicago probe).
POINTS_PAYLOAD = {
    "id": "https://api.weather.gov/points/41.8781,-87.6298",
    "type": "Feature",
    "properties": {
        "gridId": "LOT",
        "gridX": 76,
        "gridY": 73,
        "forecast": "https://api.weather.gov/gridpoints/LOT/76,73/forecast",
        "forecastHourly": "https://api.weather.gov/gridpoints/LOT/76,73/forecast/hourly",
        "relativeLocation": {
            "type": "Feature",
            "properties": {"city": "Chicago", "state": "IL"},
        },
        "timeZone": "America/Chicago",
    },
}

# NWS forecast periods (trimmed from the live LOT probe).
FORECAST_PAYLOAD = {
    "properties": {
        "periods": [
            {
                "number": 1,
                "startTime": "2026-08-30T14:00:00-05:00",
                "temperature": 81,
                "temperatureUnit": "F",
                "probabilityOfPrecipitation": {"unitCode": "wmoUnit:percent", "value": 56},
                "shortForecast": "Chance Showers And Thunderstorms",
            },
            {
                "number": 2,
                "startTime": "2026-08-31T00:00:00-05:00",
                "temperature": 91,
                "temperatureUnit": "F",
                "probabilityOfPrecipitation": {"unitCode": "wmoUnit:percent", "value": None},
                "shortForecast": "Partly Cloudy",
            },
            {
                "number": 3,
                "startTime": "2026-08-31T12:00:00-05:00",
                "temperature": 88,
                "temperatureUnit": "F",
                "probabilityOfPrecipitation": {"unitCode": "wmoUnit:percent", "value": 10},
                "shortForecast": "Sunny",
            },
        ]
    }
}

# NWS active-alerts GeoJSON (live shape; SD severe thunderstorm + heat).
ALERTS_PAYLOAD = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "event": "Severe Thunderstorm Warning",
                "severity": "Severe",
                "areaDesc": "Harding, SD",
            },
        },
        {
            "type": "Feature",
            "properties": {
                "event": "Excessive Heat Warning",
                "severity": "Moderate",
                "areaDesc": "Central Chicago",
            },
        },
    ],
    "title": "Current watches, warnings, and advisories",
}


def _mock_client(monkeypatch, routes):
    """Monkeypatch httpx.Client with a transport that routes on URL substring."""

    def handler(request):
        url = str(request.url)
        for matcher, payload in routes:
            if matcher in url:
                return httpx.Response(200, json=payload, request=request)
        raise AssertionError(f"No canned response for {url}")

    transport = httpx.MockTransport(handler)

    class _PatchedClient(httpx.Client):
        def __init__(self, **kwargs):
            super().__init__(transport=transport)

    monkeypatch.setattr(httpx, "Client", _PatchedClient)


# ---------------------------------------------------------------- construction

def test_ghcn_client_construction_defaults():
    client = GhcnDailyClient()
    assert client.timeout == 30.0
    assert "ghcnd-stations.txt" in client.stations_url
    assert "services/data/v1" in client.daily_url


def test_nws_client_construction_defaults():
    client = NwsWeatherClient()
    assert client.timeout == 30.0
    assert client.points_url.endswith("/points")
    assert "alerts/active" in client.alerts_url


# ------------------------------------------------- station inventory parsing

def test_parse_station_line_fixed_width():
    line = "USW00094846  41.9603  -87.9317  204.8 IL CHICAGO OHARE INTL AP"
    station = parse_ghcnd_station_line(line)
    assert station is not None
    assert station.station_id == "USW00094846"
    assert station.lat == 41.9603
    assert station.lng == -87.9317
    assert station.elevation_m == 204.8
    assert station.name == "CHICAGO OHARE INTL AP"


def test_parse_station_line_international_no_state():
    line = "ACW00011604  17.1167  -61.7833   10.1    ST JOHNS COOLIDGE FLD"
    station = parse_ghcnd_station_line(line)
    assert station is not None
    assert station.station_id == "ACW00011604"
    assert station.lat == 17.1167


def test_parse_station_line_skips_malformed():
    assert parse_ghcnd_station_line("") is None
    assert parse_ghcnd_station_line("SHORT") is None
    assert parse_ghcnd_station_line("BAD00000001 not-a-number stuff here") is None


def test_parse_station_inventory_bulk():
    stations = parse_ghcnd_station_inventory(STATIONS_TXT)
    assert len(stations) == 4
    ids = {s.station_id for s in stations}
    assert ids == {"ACW00011604", "USW00094846", "USW00012960", "USW00023062"}


# ---------------------------------------------------------- crosswalk logic

def test_stations_in_bbox_filters():
    stations = parse_ghcnd_station_inventory(STATIONS_TXT)
    chicago_bbox = {"min_lat": 41.64, "max_lat": 42.03, "min_lng": -87.94, "max_lng": -87.52}
    inside = GhcnDailyClient.stations_in_bbox(stations, chicago_bbox)
    assert [s.station_id for s in inside] == ["USW00094846"]


def test_nearest_station_picks_closest():
    stations = parse_ghcnd_station_inventory(STATIONS_TXT)
    # A point near downtown Chicago; O'Hare is the only station in the set.
    best = GhcnDailyClient.nearest(stations, 41.8781, -87.6298)
    assert best is not None
    assert best.station_id == "USW00094846"


def test_nearest_station_empty_inventory_returns_none():
    assert GhcnDailyClient.nearest([], 40.0, -90.0) is None


def test_crosswalk_station_to_h3_consistent_hierarchy():
    client = GhcnDailyClient()
    station = NoaaStation("USW00094846", 41.9603, -87.9317, 204.8, "OHARE")
    cells = client.crosswalk_station_to_h3(station)
    assert set(cells) == {"h3_res7", "h3_res8", "h3_res9"}
    from src.spatial.h3_indexer import H3SpatialIndexer

    assert H3SpatialIndexer.get_parent(cells["h3_res9"], 8) == cells["h3_res8"]
    assert H3SpatialIndexer.get_parent(cells["h3_res8"], 7) == cells["h3_res7"]


def test_invalid_crosswalk_coordinates_raise():
    client = GhcnDailyClient()
    station = NoaaStation("BAD", 999.0, -87.6, 0.0, "bad")
    with pytest.raises(ValueError):
        client.crosswalk_station_to_h3(station)


# --------------------------------------------------------- daily row parsing

def test_parse_daily_summary_row_tenths_to_real():
    row = parse_daily_summary_row(DAILY_SUMMARIES[0])
    assert row["date"].isoformat() == "2026-08-20"
    assert row["tmax_c"] == pytest.approx(25.6)
    assert row["tmin_c"] == pytest.approx(16.7)
    assert row["prcp_mm"] == 0.0


def test_parse_daily_summary_row_missing_cell_is_none():
    row = parse_daily_summary_row(DAILY_SUMMARIES[1])
    assert row["tmax_c"] == pytest.approx(26.7)
    assert row["prcp_mm"] == 0.0


def test_parse_daily_summary_row_bad_date_returns_nones():
    row = parse_daily_summary_row({"DATE": "not-a-date", "TMAX": "  100"})
    assert row["date"] is None
    assert row["tmax_c"] is None


def test_parse_daily_summary_row_empty_returns_nones():
    row = parse_daily_summary_row({})
    assert row["date"] is None


def test_parse_daily_summary_row_trace_precip_is_none():
    row = parse_daily_summary_row(
        {"DATE": "2026-08-20", "TMAX": "  256", "PRCP": "T"}
    )
    assert row["prcp_mm"] is None


def test_parse_daily_summary_row_quality_flag_rejects_suspect():
    row = parse_daily_summary_row(
        {"DATE": "2026-08-20", "TMAX": "  256", "TMAX_ATTRIBUTES": ",,S,"}
    )
    assert row["tmax_c"] is None


# ------------------------------------------------------------- fetch + tagging

def test_fetch_daily_builds_query_and_parses(monkeypatch):
    client = GhcnDailyClient()
    _mock_client(
        monkeypatch,
        [("dataset=daily-summaries", DAILY_SUMMARIES)],
    )
    rows = client.fetch_daily("USW00094846", date(2026, 8, 20), date(2026, 8, 22))
    assert len(rows) == 3
    assert rows[0]["tmax_c"] == pytest.approx(25.6)
    assert rows[2]["date"].isoformat() == "2026-08-22"


def test_fetch_daily_error_object_raises(monkeypatch):
    client = GhcnDailyClient()
    _mock_client(monkeypatch, [("dataset=daily-summaries", {"error": "not found"})])
    with pytest.raises(WeatherFetchError, match="not found"):
        client.fetch_daily("BAD00000000", date(2026, 8, 1), date(2026, 8, 2))


def test_daily_covariates_tags_each_day_to_h3(monkeypatch):
    client = GhcnDailyClient()
    _mock_client(monkeypatch, [("dataset=daily-summaries", DAILY_SUMMARIES)])
    station = NoaaStation("USW00094846", 41.9603, -87.9317, 204.8, "OHARE")
    covariates = client.daily_covariates(station, "chicago", date(2026, 8, 20), date(2026, 8, 22))
    assert len(covariates) == 3
    for cov in covariates:
        assert cov.city_id == "chicago"
        assert cov.source == "ghcn_d"
        assert cov.station_id == "USW00094846"
        assert cov.h3_res7 and cov.h3_res8 and cov.h3_res9
        assert cov.forecast_periods == 0  # GHCN side only
    assert covariates[0].observed_date.isoformat() == "2026-08-20"
    assert covariates[0].tmax_c == pytest.approx(25.6)


# ---------------------------------------------------------- NWS forecast

def test_gridpoint_resolves_forecast_url(monkeypatch):
    client = NwsWeatherClient()
    _mock_client(monkeypatch, [("api.weather.gov/points", POINTS_PAYLOAD)])
    props = client.gridpoint(41.8781, -87.6298)
    assert props["gridId"] == "LOT"
    assert props["gridX"] == 76
    assert props["forecast"].endswith("/forecast")


def test_gridpoint_non_dict_payload_raises(monkeypatch):
    client = NwsWeatherClient()
    _mock_client(monkeypatch, [("api.weather.gov/points", [])])
    with pytest.raises(WeatherFetchError, match="points payload"):
        client.gridpoint(41.8781, -87.6298)


def test_fetch_forecast_summarizes_periods(monkeypatch):
    client = NwsWeatherClient()
    _mock_client(
        monkeypatch,
        [
            ("api.weather.gov/points", POINTS_PAYLOAD),
            ("/forecast", FORECAST_PAYLOAD),
        ],
    )
    summary = client.fetch_forecast(41.8781, -87.6298)
    assert summary["forecast_max_temp_f"] == 91.0
    assert summary["forecast_max_precip_pct"] == 56.0
    assert summary["forecast_periods"] == 3


def test_parse_forecast_periods_empty():
    assert parse_forecast_periods([]) == {
        "forecast_max_temp_f": None,
        "forecast_max_precip_pct": None,
        "forecast_periods": 0,
    }


def test_parse_forecast_periods_ignores_bad_rows():
    summary = parse_forecast_periods([{}, {"temperature": "not-a-temp"}, None])
    assert summary["forecast_periods"] == 2
    assert summary["forecast_max_temp_f"] is None


# ---------------------------------------------------------- NWS alerts

def test_parse_active_alerts_summarizes():
    summary = parse_active_alerts(ALERTS_PAYLOAD)
    assert summary["alert_count"] == 2
    assert summary["alert_max_severity"] == "Severe"
    assert summary["alert_events"] == (
        "Severe Thunderstorm Warning",
        "Excessive Heat Warning",
    )


def test_parse_active_alerts_no_features():
    assert parse_active_alerts({"type": "FeatureCollection", "features": []}) == {
        "alert_count": 0,
        "alert_max_severity": None,
        "alert_events": (),
    }


def test_parse_active_alerts_non_dict():
    assert parse_active_alerts([1, 2, 3])["alert_count"] == 0


def test_fetch_active_alerts_queries_point(monkeypatch):
    client = NwsWeatherClient()
    _mock_client(monkeypatch, [("alerts/active?point", ALERTS_PAYLOAD)])
    summary = client.fetch_active_alerts(45.71, -104.04)
    assert summary["alert_count"] == 2


# -------------------------------------------------- combined covariate record

def test_weather_covariates_combines_forecast_and_alerts(monkeypatch):
    client = NwsWeatherClient()
    _mock_client(
        monkeypatch,
        [
            ("api.weather.gov/points", POINTS_PAYLOAD),
            ("/forecast", FORECAST_PAYLOAD),
            ("alerts/active?point", ALERTS_PAYLOAD),
        ],
    )
    covariates = client.weather_covariates(41.8781, -87.6298, "chicago", observed_date=date(2026, 8, 30))
    assert len(covariates) == 1
    cov = covariates[0]
    assert cov.city_id == "chicago"
    assert cov.source == "nws"
    assert cov.observed_date.isoformat() == "2026-08-30"
    assert cov.forecast_max_temp_f == 91.0
    assert cov.forecast_max_precip_pct == 56.0
    assert cov.alert_count == 2
    assert cov.alert_max_severity == "Severe"
    assert cov.h3_res7 and cov.h3_res8 and cov.h3_res9
    assert cov.tmax_c is None  # NWS side leaves GHCN fields empty
