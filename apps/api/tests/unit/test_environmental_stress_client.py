"""Unit tests for the environmental-stress context clients (US-401).

Five thin clients: AirNow (keyed), USDM (GeoJSON → H3 areal intersection),
Storm Events (gzip CSV), USGS NWIS (bbox JSON), NOAA tide (per-station JSON).
All parse into ``EnvironmentalStressReading`` covariate records tagged to H3.

Tests are fixture-based and never hit the network. Live-probe tests are
marked ``@pytest.mark.live`` (excluded from normal CI runs).
"""

from __future__ import annotations

import gzip

import pytest

from src.producers.environmental_stress_client import (
    COASTAL_TIDE_STATIONS,
    AirNowClient,
    EnvironmentalStressReading,
    NwisClient,
    StormEvent,
    StormEventsClient,
    StreamGauge,
    TideGaugeClient,
    UsdmClient,
)

# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #

AIRNOW_OBS_FIXTURE = [
    {
        "DateObserved": "2026-08-30 ",
        "HourObserved": 14,
        "LocalTimeZone": "CDT",
        "ReportingArea": "Houston-Galveston-Brazoria",
        "StateCode": "TX",
        "Latitude": 29.751,
        "Longitude": -95.351,
        "ParameterName": "O3",
        "AQI": 105,
        "Category": {"Number": 4, "Name": "Unhealthy for Sensitive Groups"},
    },
    {
        "DateObserved": "2026-08-30 ",
        "HourObserved": 14,
        "LocalTimeZone": "CDT",
        "ReportingArea": "Houston-Galveston-Brazoria",
        "StateCode": "TX",
        "Latitude": 29.751,
        "Longitude": -95.351,
        "ParameterName": "PM2.5",
        "AQI": 22,
        "Category": {"Number": 1, "Name": "Good"},
    },
]

AIRNOW_FORECAST_FIXTURE = [
    {
        "DateIssue": "2026-08-30 ",
        "DateForecast": "2026-08-31 ",
        "ReportingArea": "Houston-Galveston-Brazoria",
        "StateCode": "TX",
        "Latitude": 29.751,
        "Longitude": -95.351,
        "ParameterName": "O3",
        "AQI": 90,
        "ActionDay": False,
        "Discussion": "Partly cloudy.",
        "Category": {"Number": 2, "Name": "Moderate"},
    }
]


def _usdm_geojson_nyc_square() -> dict:
    """A minimal GeoJSON FeatureCollection: one DM-2 feature around NYC."""
    # A rough square around the NYC metro (lng, lat) rings, CCW not required.
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"OBJECTID": 1, "DM": 2, "Shape_Length": 1.0, "Shape_Area": 0.25},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-74.25, 40.49],
                            [-73.70, 40.49],
                            [-73.70, 40.92],
                            [-74.25, 40.92],
                            [-74.25, 40.49],
                        ]
                    ],
                },
            }
        ],
    }


def _storm_csv_bytes() -> bytes:
    """A gzip-compressed CSV with two storm-event rows (full 51-col layout)."""
    header = [
        "BEGIN_YEARMONTH", "BEGIN_DAY", "BEGIN_TIME", "END_YEARMONTH", "END_DAY",
        "END_TIME", "EPISODE_ID", "EVENT_ID", "STATE", "STATE_FIPS", "YEAR",
        "MONTH_NAME", "EVENT_TYPE", "CZ_TYPE", "CZ_FIPS", "CZ_NAME", "WFO",
        "BEGIN_DATE_TIME", "CZ_TIMEZONE", "END_DATE_TIME", "INJURIES_DIRECT",
        "INJURIES_INDIRECT", "DEATHS_DIRECT", "DEATHS_INDIRECT", "DAMAGE_PROPERTY",
        "DAMAGE_CROPS", "SOURCE", "MAGNITUDE", "MAGNITUDE_TYPE", "FLOOD_CAUSE",
        "CATEGORY", "TOR_F_SCALE", "TOR_LENGTH", "TOR_WIDTH", "TOR_OTHER_WFO",
        "TOR_OTHER_CZ_STATE", "TOR_OTHER_CZ_FIPS", "TOR_OTHER_CZ_NAME",
        "BEGIN_RANGE", "BEGIN_AZIMUTH", "BEGIN_LOCATION", "END_RANGE",
        "END_AZIMUTH", "END_LOCATION", "BEGIN_LAT", "BEGIN_LON", "END_LAT",
        "END_LON", "EPISODE_NARRATIVE", "EVENT_NARRATIVE", "DATA_SOURCE",
    ]

    def _row(**overrides) -> dict:
        base = {
            "BEGIN_YEARMONTH": "202604", "BEGIN_DAY": "14", "BEGIN_TIME": "1910",
            "END_YEARMONTH": "202604", "END_DAY": "14", "END_TIME": "1910",
            "EPISODE_ID": "210980", "EVENT_ID": "1318061", "STATE": "MA",
            "STATE_FIPS": "25", "YEAR": "2026", "MONTH_NAME": "April",
            "EVENT_TYPE": "Thunderstorm Wind", "CZ_TYPE": "C", "CZ_FIPS": "27",
            "CZ_NAME": "WORCESTER", "WFO": "BOX",
            "BEGIN_DATE_TIME": "14-APR-26 19:10:00", "CZ_TIMEZONE": "EST",
            "END_DATE_TIME": "14-APR-26 19:10:00", "INJURIES_DIRECT": "0",
            "INJURIES_INDIRECT": "0", "DEATHS_DIRECT": "0", "DEATHS_INDIRECT": "0",
            "DAMAGE_PROPERTY": "10.00K", "DAMAGE_CROPS": "0.00K", "SOURCE": "EM",
            "MAGNITUDE": "65", "MAGNITUDE_TYPE": "EG", "FLOOD_CAUSE": "",
            "CATEGORY": "", "TOR_F_SCALE": "0", "TOR_LENGTH": "0",
            "TOR_WIDTH": "0", "TOR_OTHER_WFO": "", "TOR_OTHER_CZ_STATE": "",
            "TOR_OTHER_CZ_FIPS": "", "TOR_OTHER_CZ_NAME": "", "BEGIN_RANGE": "",
            "BEGIN_AZIMUTH": "", "BEGIN_LOCATION": "", "END_RANGE": "",
            "END_AZIMUTH": "", "END_LOCATION": "", "BEGIN_LAT": "42.44",
            "BEGIN_LON": "-71.69", "END_LAT": "42.44", "END_LON": "-71.69",
            "EPISODE_NARRATIVE": "", "EVENT_NARRATIVE": "", "DATA_SOURCE": "NWS",
        }
        base.update(overrides)
        return base

    r1 = _row()
    r2 = _row(
        EVENT_ID="1318062",
        EPISODE_ID="210981",
        EVENT_TYPE="Flash Flood",
        BEGIN_TIME="1920",
        END_TIME="1920",
        BEGIN_DATE_TIME="14-APR-26 19:20:00",
        END_DATE_TIME="14-APR-26 19:20:00",
        INJURIES_DIRECT="2",
        DEATHS_DIRECT="1",
        DAMAGE_PROPERTY="1.50M",
        FLOOD_CAUSE="Flash Flood",
        BEGIN_LAT="42.50",
        BEGIN_LON="-71.80",
        END_LAT="42.60",
        END_LON="-71.90",
    )
    text = ",".join(header) + "\n"
    for r in (r1, r2):
        text += ",".join(str(r[col]) for col in header) + "\n"
    return gzip.compress(text.encode("utf-8"))


_NWIS_PAYLOAD = {
    "value": {
        "timeSeries": [
            {
                "sourceInfo": {
                    "siteName": "BRONX RIVER AT NY BOTANICAL GARDEN AT BRONX NY",
                    "siteCode": [{"value": "01302020", "network": "NWIS", "agencyCode": "USGS"}],
                    "geoLocation": {
                        "geogLocation": {"srs": "EPSG:4326", "latitude": 40.86230556, "longitude": -73.87438889}
                    },
                },
                "variable": {
                    "variableCode": [{"value": "00060"}],
                    "variableName": "Streamflow, ft&#179;/s",
                    "unit": {"unitCode": "ft3/s"},
                },
                "values": [
                    {
                        "value": [{"value": "33.5", "qualifiers": ["P"], "dateTime": "2026-08-30T15:30:00.000-05:00"}],
                        "noDataValue": -999999.0,
                    }
                ],
            },
            {
                "sourceInfo": {
                    "siteName": "VALLEY STREAM AT VALLEY STREAM NY",
                    "siteCode": [{"value": "01311500", "network": "NWIS", "agencyCode": "USGS"}],
                    "geoLocation": {
                        "geogLocation": {"srs": "EPSG:4326", "latitude": 40.66380556, "longitude": -73.70452778}
                    },
                },
                "variable": {
                    "variableCode": [{"value": "00060"}],
                    "variableName": "Streamflow, ft&#179;/s",
                    "unit": {"unitCode": "ft3/s"},
                },
                "values": [
                    {
                        "value": [{"value": "-999999", "qualifiers": ["P"], "dateTime": "2026-08-30T15:00:00.000-05:00"}],
                        "noDataValue": -999999.0,
                    }
                ],
            },
        ]
    }
}

_TIDE_PAYLOAD = {
    "metadata": {
        "id": "9414290",
        "name": "San Francisco",
        "lat": "37.8063",
        "lon": "-122.4659",
    },
    "data": [
        {"t": "2026-08-30 20:48", "v": "0.889", "s": "0.058", "f": "1,0,0,0", "q": "p"}
    ],
}


# --------------------------------------------------------------------------- #
# AirNowClient                                                                 #
# --------------------------------------------------------------------------- #


class TestAirNow:
    def test_parse_observations(self):
        obs = AirNowClient.parse_observations(AIRNOW_OBS_FIXTURE)
        assert len(obs) == 2
        o0 = obs[0]
        assert o0.reporting_area == "Houston-Galveston-Brazoria"
        assert o0.state_code == "TX"
        assert o0.latitude == 29.751
        assert o0.longitude == -95.351
        assert o0.parameter_name == "O3"
        assert o0.aqi == 105
        assert o0.hour_observed == 14
        assert o0.category_number == 4
        assert o0.category_name == "Unhealthy for Sensitive Groups"

    def test_parse_forecasts(self):
        obs = AirNowClient.parse_forecasts(AIRNOW_FORECAST_FIXTURE)
        assert len(obs) == 1
        o = obs[0]
        assert o.aqi == 90
        assert o.action_day is False
        assert o.date_forecast == "2026-08-31"
        assert o.hour_observed is None
        assert o.discussion == "Partly cloudy."

    def test_parse_non_list_raises(self):
        with pytest.raises(TypeError):
            AirNowClient.parse_observations({"not": "a list"})

    def test_to_readings_tags_h3_and_shock(self):
        obs = AirNowClient.parse_observations(AIRNOW_OBS_FIXTURE)
        readings = AirNowClient.to_readings(obs)
        assert len(readings) == 2
        r = readings[0]
        assert isinstance(r, EnvironmentalStressReading)
        assert r.source == "airnow"
        assert r.metric == "aqi"
        assert r.value == 105.0
        assert r.h3_res9 and r.h3_res9.startswith("89")
        assert r.extra["shock"] == 0.4  # AQI 105 → Unhealthy for Sensitive Groups
        assert r.extra["parameter"] == "O3"

    def test_require_key_raises_without_key(self, monkeypatch):
        monkeypatch.delenv("AIRNOW_API_KEY", raising=False)
        client = AirNowClient(api_key=None)
        with pytest.raises(RuntimeError, match="AIRNOW_API_KEY"):
            client._require_key()

    def test_fetch_observations_sends_key(self, monkeypatch):
        calls = {}

        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                return AIRNOW_OBS_FIXTURE

        def fake_get(url, params=None):
            calls["url"] = url
            calls["params"] = params
            return FakeResp()

        client = AirNowClient(api_key="secret")
        client.http.get = fake_get
        obs = client.fetch_observations("77002")
        assert len(obs) == 2
        assert "observation/zipCode/current" in calls["url"]
        assert calls["params"]["API_KEY"] == "secret"
        assert calls["params"]["zipCode"] == "77002"


# --------------------------------------------------------------------------- #
# UsdmClient                                                                   #
# --------------------------------------------------------------------------- #


class TestUsdm:
    def test_parse_payload_areal_intersection(self):
        payload = _usdm_geojson_nyc_square()
        readings = UsdmClient.parse_payload(payload, resolution=7)
        assert len(readings) > 0
        r = readings[0]
        assert r.source == "usdm"
        assert r.metric == "dm_category"
        assert r.value == 2.0
        assert r.h3_res7 and r.h3_res7.startswith("87")
        # Every reading cell should lie within the NYC square.
        lat, lng = r.lat, r.lng
        assert 40.4 <= lat <= 41.0
        assert -74.3 <= lng <= -73.6

    def test_fold_max_dm_wins(self):
        # Same cell region under DM 1 and DM 3 → max (3) wins.
        base = _usdm_geojson_nyc_square()
        import copy

        feat2 = copy.deepcopy(base["features"][0])
        feat2["properties"]["DM"] = 3
        base["features"].append(feat2)
        readings = UsdmClient.parse_payload(base, resolution=7)
        assert all(r.value == 3.0 for r in readings)

    def test_non_featurecollection_raises(self):
        with pytest.raises(TypeError):
            UsdmClient.parse_payload({"type": "FeatureCollection"})
        with pytest.raises(TypeError):
            UsdmClient.parse_payload("not a dict")

    def test_parse_ignores_features_without_dm(self):
        payload = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": None}],
        }
        assert UsdmClient.parse_payload(payload, resolution=7) == []

    def test_polygon_with_hole(self):
        outer = [
            [-74.25, 40.49],
            [-73.70, 40.49],
            [-73.70, 40.92],
            [-74.25, 40.92],
            [-74.25, 40.49],
        ]
        hole = [
            [-74.10, 40.60],
            [-74.10, 40.80],
            [-73.90, 40.80],
            [-73.90, 40.60],
            [-74.10, 40.60],
        ]
        payload = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"DM": 1},
                    "geometry": {"type": "Polygon", "coordinates": [outer, hole]},
                }
            ],
        }
        readings = UsdmClient.parse_payload(payload, resolution=7)
        # The outer square still yields cells even with a hole.
        assert len(readings) > 0


# --------------------------------------------------------------------------- #
# StormEventsClient                                                             #
# --------------------------------------------------------------------------- #


class TestStormEvents:
    def test_parse_damage(self):
        assert StormEventsClient.parse_damage("10.00K") == 10000.0
        assert StormEventsClient.parse_damage("1.50M") == 1500000.0
        assert StormEventsClient.parse_damage("500") == 500.0
        assert StormEventsClient.parse_damage("") is None
        assert StormEventsClient.parse_damage(None) is None
        assert StormEventsClient.parse_damage("N/A") is None
        assert StormEventsClient.parse_damage("1,000.5") == 1000.5

    def test_parse_csv_bytes(self):
        evs = list(StormEventsClient.parse_csv_bytes(_storm_csv_bytes()))
        assert len(evs) == 2
        e0 = evs[0]
        assert e0.event_id == "1318061"
        assert e0.event_type == "Thunderstorm Wind"
        assert e0.begin_lat == 42.44
        assert e0.begin_lon == -71.69
        assert e0.damage_property == 10000.0
        assert e0.injuries_direct == 0
        e1 = evs[1]
        assert e1.damage_property == 1500000.0
        assert e1.injuries_direct == 2
        assert e1.deaths_direct == 1

    def test_parse_csv_bytes_max_records(self):
        evs = list(StormEventsClient.parse_csv_bytes(_storm_csv_bytes(), max_records=1))
        assert len(evs) == 1

    def test_to_readings_aggregates_by_cell(self):
        evs = list(StormEventsClient.parse_csv_bytes(_storm_csv_bytes()))
        readings = StormEventsClient.to_readings(evs)
        assert len(readings) >= 1
        for r in readings:
            assert r.source == "storm_events"
            assert r.metric == "storm_event_count"
            assert r.h3_res9
        # The two events are at different cells, so at least one cell has count 1.
        assert all(r.value == 1.0 for r in readings)

    def test_to_readings_skips_missing_coords(self):
        ev = StormEvent(event_id="1", begin_lat=None, begin_lon=None)
        assert StormEventsClient.to_readings([ev]) == []


# --------------------------------------------------------------------------- #
# NwisClient                                                                   #
# --------------------------------------------------------------------------- #


class TestNwis:
    def test_parse_response(self):
        gauges = NwisClient.parse_response(_NWIS_PAYLOAD)
        assert len(gauges) == 1  # second gauge is noDataValue → dropped
        g = gauges[0]
        assert g.site_id == "01302020"
        assert g.site_name.startswith("BRONX RIVER")
        assert g.value == 33.5
        assert g.value_time == "2026-08-30T15:30:00.000-05:00"
        assert g.unit == "ft3/s"

    def test_parse_response_empty(self):
        assert NwisClient.parse_response({}) == []
        assert NwisClient.parse_response("nope") == []

    def test_nearest_gauge(self):
        g1 = StreamGauge("A", "A", 40.86, -73.87, 33.5, None)
        g2 = StreamGauge("B", "B", 40.66, -73.70, 1.98, None)
        nearest, dist = NwisClient.nearest_gauge([g1, g2], 40.75, -73.99)
        assert nearest is g1
        assert dist > 0
        assert NwisClient.nearest_gauge([], 40.75, -73.99) is None

    def test_to_readings(self):
        gauges = NwisClient.parse_response(_NWIS_PAYLOAD)
        readings = NwisClient.to_readings(gauges, city_id="nyc")
        assert len(readings) == 1
        r = readings[0]
        assert r.source == "nwis"
        assert r.metric == "streamflow"
        assert r.value == 33.5
        assert r.city_id == "nyc"
        assert r.h3_res9


# --------------------------------------------------------------------------- #
# TideGaugeClient                                                              #
# --------------------------------------------------------------------------- #


class TestTideGauge:
    def test_parse_response(self):
        t = TideGaugeClient.parse_response(_TIDE_PAYLOAD)
        assert t.station_id == "9414290"
        assert t.station_name == "San Francisco"
        assert t.latitude == 37.8063
        assert t.longitude == -122.4659
        assert t.water_level_m == 0.889
        assert t.timestamp == "2026-08-30 20:48"
        assert t.flag == "p"

    def test_parse_response_no_data(self):
        payload = {"metadata": {"id": "x", "name": "X", "lat": "1", "lon": "2"}, "data": []}
        t = TideGaugeClient.parse_response(payload)
        assert t.water_level_m is None

    def test_parse_response_invalid(self):
        with pytest.raises(TypeError):
            TideGaugeClient.parse_response("nope")
        with pytest.raises(TypeError):
            TideGaugeClient.parse_response({})

    def test_coastal_station_map_covers_named_metros(self):
        for cid in ("nyc", "seattle", "san_francisco", "los_angeles", "norfolk"):
            assert cid in COASTAL_TIDE_STATIONS

    def test_to_readings(self):
        t = TideGaugeClient.parse_response(_TIDE_PAYLOAD)
        readings = TideGaugeClient.to_readings([("san_francisco", t)])
        assert len(readings) == 1
        r = readings[0]
        assert r.source == "tide"
        assert r.metric == "water_level"
        assert r.value == 0.889
        assert r.unit == "m"
        assert r.city_id == "san_francisco"
        assert r.h3_res9


# --------------------------------------------------------------------------- #
# Live probes (excluded from normal CI)                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.live
def test_live_nwis_nyc_bbox():
    client = NwisClient()
    bbox = {"min_lat": 40.480, "max_lat": 40.930, "min_lng": -74.280, "max_lng": -73.680}
    gauges = client.fetch_by_bbox(bbox)
    assert len(gauges) > 0
    assert all(g.value is not None for g in gauges)


@pytest.mark.live
def test_live_tide_san_francisco():
    client = TideGaugeClient()
    t = client.fetch_station("9414290")
    assert t.water_level_m is not None


@pytest.mark.live
def test_live_usdm_current():
    client = UsdmClient(resolution=6)
    readings = client.fetch()
    assert len(readings) > 0
    assert all(0.0 <= r.value <= 4.0 for r in readings)


@pytest.mark.live
def test_live_storm_events_2026():
    client = StormEventsClient()
    # The real annual file can carry rows with empty BEGIN_LAT; filter to those
    # with coordinates and assert the parse produced at least one.
    evs = [ev for ev in client.fetch(max_records=20) if ev.begin_lat is not None]
    assert len(evs) >= 1
