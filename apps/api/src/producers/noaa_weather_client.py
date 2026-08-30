"""NOAA weather context clients — GHCN-D daily + NWS forecast/alerts (US-400).

Leaf-only thin HTTP clients. No spine file is imported or edited: both clients
depend only on the leaf ``noaa_climate`` helpers (station selection,
missingness, H3 mapping) and ``httpx``. Their output is per-H3 context
covariates destined for the feature store — never new event schemas, never
Kafka events. The orchestrator owns the spine wiring; this module only fetches
and parses.

Two sources, both keyless:

1. **GHCN-D daily station summaries** (``GhcnDailyClient``) — NOAA NCEI
   ``access/services/data/v1?dataset=daily-summaries`` returns one JSON row per
   station-day with ``TMAX``/``TMIN``/``PRCP`` in metric tenths (0.1 °C /
   0.1 mm), padded-string cells that can be absent on a given day. The station
   list is the fixed-width ``ghcnd-stations.txt`` inventory (132,501 rows,
   ~129.6k real stations, no token), which the client can filter to a metro
   bbox and resolve to a nearest station; ``map_station_to_h3`` from the
   existing ``noaa_climate`` leaf maps the station point to the repo's H3
   res 7/8/9 hierarchy.
2. **NWS api.weather.gov** (``NwsWeatherClient``) — ``/points/{lat},{lon}``
   resolves a coordinate to a gridpoint whose ``forecast`` URL carries the
   7-day forecast, and ``/alerts/active?point=...`` carries live heat/cold/
   flood/tornado alerts. NWS asks clients to identify themselves via
   ``User-Agent``; this module sends a descriptive header.

Both clients follow the ``series_client`` politeness contract: one GET per
small payload, httpx with ``follow_redirects``, a readable ``WeatherFetchError``
on failure, and no pagination (each payload is <1 KB for GHCN-D, a few KB for
NWS). Cadence is the publisher's (daily for both); nothing here schedules.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from src.spatial.noaa_climate import (
    NoaaStation,
    nearest_station,
    obs_quality_ok,
    stations_within_bbox,
)

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Endpoints (public so tests and callers can point at a stub/mirror)           #
# --------------------------------------------------------------------------- #
GHCN_STATIONS_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"
GHCN_DAILY_URL = "https://www.ncei.noaa.gov/access/services/data/v1"
NWS_POINTS_URL = "https://api.weather.gov/points"
NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"

# NWS asks for an identifying User-Agent on every request.
NWS_USER_AGENT = "urban-signal/2.0 (feature-store weather context; contact: urban-signal-dev)"


class WeatherFetchError(RuntimeError):
    """Raised when a weather source is unreachable or returns unusable data."""


@dataclass(frozen=True)
class WeatherCovariate:
    """One per-H3 weather context covariate record.

    GHCN-D populates the ``tmax_c``/``tmin_c``/``prcp_mm`` side; NWS populates
    the forecast and alert side. Fields a source does not measure stay ``None``/
    ``0`` so the two folds merge additively downstream, mirroring the repo's
    covariate conventions.
    """

    city_id: str
    source: str  # "ghcn_d" | "nws"
    observed_date: date
    h3_res7: str
    h3_res8: str
    h3_res9: str
    station_id: str | None = None
    # GHCN-D daily (metric: °C, mm). None means the station did not report a
    # quality-passing value that day — never a false zero.
    tmax_c: float | None = None
    tmin_c: float | None = None
    prcp_mm: float | None = None
    # NWS forecast — summary over the 7-day forecast horizon.
    forecast_max_temp_f: float | None = None
    forecast_max_precip_pct: float | None = None
    forecast_periods: int = 0
    # NWS active alerts.
    alert_count: int = 0
    alert_max_severity: str | None = None
    alert_events: tuple[str, ...] = ()


# --------------------------------------------------------------------------- #
# shared parsing helpers                                                       #
# --------------------------------------------------------------------------- #
def _to_float(value: Any) -> float | None:
    """Normalize a padded-string numeric cell (``"  256"``) to float or None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text == "T":  # trace precipitation
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_ghcnd_station_line(line: str) -> NoaaStation | None:
    """Parse one fixed-width ``ghcnd-stations.txt`` row into a NoaaStation.

    Documented column layout (1-indexed): ID 1-11, LATITUDE 13-20, LONGITUDE
    22-30, ELEVATION 32-37, STATE 39-40, NAME 42-71. Rows with unparseable
    coordinates are skipped so a malformed row never poisons the inventory.
    """
    if len(line) < 41:
        return None
    station_id = line[0:11].strip()
    try:
        lat = float(line[12:20])
        lng = float(line[21:30])
        elev = float(line[31:37]) if line[31:37].strip() else 0.0
    except ValueError:
        return None
    if not station_id:
        return None
    name = line[41:71].strip()
    return NoaaStation(station_id=station_id, lat=lat, lng=lng, elevation_m=elev, name=name)


def parse_ghcnd_station_inventory(text: str) -> list[NoaaStation]:
    """Parse the full ``ghcnd-stations.txt`` body into a station list."""
    stations: list[NoaaStation] = []
    for line in text.splitlines():
        station = parse_ghcnd_station_line(line)
        if station is not None:
            stations.append(station)
    return stations


def _tenths_to_real(tenths: float | None) -> float | None:
    """Convert a GHCND tenths-of-unit cell (0.1 °C, 0.1 mm) to real units."""
    if tenths is None:
        return None
    return tenths / 10.0


def parse_daily_summary_row(
    row: dict,
    *,
    quality: bool = True,
) -> dict:
    """Normalize one daily-summaries JSON row into real-unit TMAX/TMIN/PRCP.

    Returns ``{"date": date, "tmax_c": float|None, "tmin_c": float|None,
    "prcp_mm": float|None}``. Cells are tenths-of-unit padded strings; a cell
    the station did not report (absent key or a quality/suspect flag when
    ``quality=True``) becomes ``None`` — never zero.
    """
    date_raw = row.get("DATE")
    if not date_raw:
        return {"date": None, "tmax_c": None, "tmin_c": None, "prcp_mm": None}
    try:
        obs_date = date.fromisoformat(str(date_raw)[:10])
    except ValueError:
        return {"date": None, "tmax_c": None, "tmin_c": None, "prcp_mm": None}

    def cell(key: str) -> float | None:
        value = _to_float(row.get(key))
        if value is None:
            return None
        if quality and not obs_quality_ok(value, str(row.get(f"{key}_ATTRIBUTES") or "")):
            return None
        return _tenths_to_real(value)

    return {
        "date": obs_date,
        "tmax_c": cell("TMAX"),
        "tmin_c": cell("TMIN"),
        "prcp_mm": cell("PRCP"),
    }


def parse_forecast_periods(periods: Iterable[dict]) -> dict:
    """Summarize NWS forecast periods into covariate fields.

    NWS forecast periods are 7 days of day/night (or hourly) windows with
    ``temperature`` (°F), ``probabilityOfPrecipitation.value`` (0-100 or None).
    Summarizes to the horizon max temperature and max precipitation chance, plus
    the period count — a per-H3 daily covariate, not 14 separate rows.
    """
    temps: list[float] = []
    pops: list[float] = []
    count = 0
    for period in periods:
        if not isinstance(period, dict):
            continue
        count += 1
        temp = _to_float(period.get("temperature"))
        if temp is not None:
            temps.append(temp)
        pop_value = (
            period.get("probabilityOfPrecipitation") or {}
        ).get("value")
        pop = _to_float(pop_value)
        if pop is not None:
            pops.append(pop)
    return {
        "forecast_max_temp_f": max(temps) if temps else None,
        "forecast_max_precip_pct": max(pops) if pops else None,
        "forecast_periods": count,
    }


def parse_active_alerts(alerts_json: Any) -> dict:
    """Summarize ``/alerts/active`` GeoJSON into covariate fields.

    Returns the active alert count, the highest severity present (None when no
    alerts are active), and the distinct event types (Severe Thunderstorm
    Warning, Excessive Heat Warning, ...) in the alerts' appearance order.
    """
    features = alerts_json.get("features") if isinstance(alerts_json, dict) else None
    if not isinstance(features, list):
        return {"alert_count": 0, "alert_max_severity": None, "alert_events": ()}
    severity_rank = {"Extreme": 4, "Severe": 3, "Moderate": 2, "Minor": 1}
    max_rank = 0
    max_sev: str | None = None
    events: list[str] = []
    seen: set[str] = set()
    for feature in features:
        props = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(props, dict):
            continue
        event = str(props.get("event") or "").strip()
        if event and event not in seen:
            seen.add(event)
            events.append(event)
        severity = str(props.get("severity") or "").strip()
        rank = severity_rank.get(severity, 0)
        if rank > max_rank:
            max_rank = rank
            max_sev = severity
    return {
        "alert_count": len(features),
        "alert_max_severity": max_sev,
        "alert_events": tuple(events),
    }


# --------------------------------------------------------------------------- #
# GHCN-D                                                                       #
# --------------------------------------------------------------------------- #
class GhcnDailyClient:
    """Fetches GHCN-D daily summaries and maps stations to H3 covariates."""

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        stations_url: str = GHCN_STATIONS_URL,
        daily_url: str = GHCN_DAILY_URL,
    ):
        self.timeout = timeout_seconds
        self.stations_url = stations_url
        self.daily_url = daily_url

    # -- transport ---------------------------------------------------------- #
    def _get_json(self, url: str) -> Any:
        import httpx

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            raise WeatherFetchError(f"{url}: {exc}") from exc

    def _get_text(self, url: str) -> str:
        import httpx

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.text
        except Exception as exc:
            raise WeatherFetchError(f"{url}: {exc}") from exc

    # -- inventory + crosswalk ---------------------------------------------- #
    def fetch_station_inventory(self) -> list[NoaaStation]:
        """Fetch and parse ``ghcnd-stations.txt`` (keyless, ~132k rows)."""
        return parse_ghcnd_station_inventory(self._get_text(self.stations_url))

    @staticmethod
    def stations_in_bbox(
        inventory: Iterable[NoaaStation],
        bbox: dict[str, float],
    ) -> list[NoaaStation]:
        """Filter the inventory to a metro bbox (mirrors event-feed bbox gating)."""
        return stations_within_bbox(inventory, bbox)

    @staticmethod
    def nearest(inventory: Iterable[NoaaStation], lat: float, lng: float) -> NoaaStation | None:
        """Nearest station to (lat, lng) by haversine distance, or None."""
        return nearest_station(inventory, lat, lng)

    def crosswalk_station_to_h3(self, station: NoaaStation) -> dict[str, str]:
        """Resolve a station point to the H3 res 7/8/9 hierarchy."""
        from src.spatial.noaa_climate import map_station_to_h3

        return map_station_to_h3(station.lat, station.lng)

    # -- daily observations -------------------------------------------------- #
    def fetch_daily(
        self,
        station_id: str,
        start_date: date,
        end_date: date,
        quality: bool = True,
    ) -> list[dict]:
        """Fetch GHCN-D daily summaries for one station over a date window.

        Returns one normalized dict per station-day via
        ``parse_daily_summary_row`` (real-unit TMAX/TMIN/PRCP, missing cells
        as None). The daily-summaries service is keyless and returns a
        sub-KB JSON list for a short window.
        """
        url = (
            f"{self.daily_url}?dataset=daily-summaries"
            f"&stations={station_id}"
            f"&startDate={start_date.isoformat()}"
            f"&endDate={end_date.isoformat()}"
            f"&format=json"
        )
        payload = self._get_json(url)
        if not isinstance(payload, list):
            # The service returns a JSON error object for unknown stations.
            message = payload.get("error") if isinstance(payload, dict) else payload
            raise WeatherFetchError(f"{station_id}: daily-summaries returned {message!r}")
        return [parse_daily_summary_row(row, quality=quality) for row in payload]

    def daily_covariates(
        self,
        station: NoaaStation,
        city_id: str,
        start_date: date,
        end_date: date,
        quality: bool = True,
    ) -> list[WeatherCovariate]:
        """Fetch one station's daily observations and tag each day to H3."""
        hierarchy = self.crosswalk_station_to_h3(station)
        covariates: list[WeatherCovariate] = []
        for row in self.fetch_daily(station.station_id, start_date, end_date, quality=quality):
            obs_date = row["date"]
            if obs_date is None:
                continue
            covariates.append(
                WeatherCovariate(
                    city_id=city_id,
                    source="ghcn_d",
                    observed_date=obs_date,
                    h3_res7=hierarchy["h3_res7"],
                    h3_res8=hierarchy["h3_res8"],
                    h3_res9=hierarchy["h3_res9"],
                    station_id=station.station_id,
                    tmax_c=row["tmax_c"],
                    tmin_c=row["tmin_c"],
                    prcp_mm=row["prcp_mm"],
                )
            )
        return covariates


# --------------------------------------------------------------------------- #
# NWS api.weather.gov                                                          #
# --------------------------------------------------------------------------- #
class NwsWeatherClient:
    """Fetches NWS forecast + active alerts for a lat/lon gridpoint."""

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        points_url: str = NWS_POINTS_URL,
        alerts_url: str = NWS_ALERTS_URL,
    ):
        self.timeout = timeout_seconds
        self.points_url = points_url
        self.alerts_url = alerts_url

    def _get_json(self, url: str) -> Any:
        import httpx

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": NWS_USER_AGENT})
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            raise WeatherFetchError(f"{url}: {exc}") from exc

    def gridpoint(self, lat: float, lng: float) -> dict:
        """Resolve a coordinate to a gridpoint; returns its forecast URL etc.

        ``/points/{lat},{lng}`` returns GeoJSON whose ``properties.forecast`` is
        the 7-day forecast URL and ``properties.relativeLocation`` names the
        nearest city. A point off NWS's domain (outside the US territories)
        returns 404 and surfaces as a ``WeatherFetchError``.
        """
        url = f"{self.points_url}/{lat:.4f},{lng:.4f}"
        payload = self._get_json(url)
        properties = payload.get("properties") if isinstance(payload, dict) else None
        if not isinstance(properties, dict):
            raise WeatherFetchError(f"{url}: unexpected points payload")
        return properties

    def fetch_forecast(self, lat: float, lng: float) -> dict:
        """Resolve gridpoint and summarize its 7-day forecast."""
        properties = self.gridpoint(lat, lng)
        forecast_url = properties.get("forecast")
        if not forecast_url:
            raise WeatherFetchError(f"gridpoint {lat},{lng}: no forecast URL")
        payload = self._get_json(forecast_url)
        periods = (
            payload.get("properties", {}).get("periods")
            if isinstance(payload, dict) and isinstance(payload.get("properties"), dict)
            else None
        )
        return parse_forecast_periods(periods or [])

    def fetch_active_alerts(self, lat: float, lng: float) -> dict:
        """Fetch and summarize active alerts for a point."""
        payload = self._get_json(f"{self.alerts_url}?point={lat:.4f},{lng:.4f}")
        return parse_active_alerts(payload)

    def weather_covariates(
        self,
        lat: float,
        lng: float,
        city_id: str,
        observed_date: date | None = None,
    ) -> list[WeatherCovariate]:
        """Fetch forecast + alerts for a point and tag to H3 covariates.

        Returns one covariate for the given date (defaults to today, UTC) — a
        single per-H3 daily record combining the 7-day forecast horizon summary
        and the live active-alert summary.
        """
        from src.spatial.noaa_climate import map_station_to_h3

        hierarchy = map_station_to_h3(lat, lng)
        forecast = self.fetch_forecast(lat, lng)
        alerts = self.fetch_active_alerts(lat, lng)
        covariate = WeatherCovariate(
            city_id=city_id,
            source="nws",
            observed_date=observed_date or datetime.now(UTC).date(),
            h3_res7=hierarchy["h3_res7"],
            h3_res8=hierarchy["h3_res8"],
            h3_res9=hierarchy["h3_res9"],
            forecast_max_temp_f=forecast["forecast_max_temp_f"],
            forecast_max_precip_pct=forecast["forecast_max_precip_pct"],
            forecast_periods=forecast["forecast_periods"],
            alert_count=alerts["alert_count"],
            alert_max_severity=alerts["alert_max_severity"],
            alert_events=alerts["alert_events"],
        )
        return [covariate]
