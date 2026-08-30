"""Thin clients for five environmental-stress context sources (US-401).

Leaf module — no spine edits. Each client fetches and parses one live source into
typed ``EnvironmentalStressReading`` records tagged to H3 res 7/8/9 — covariate
material for ``EnrichedH3Feature``, never new event schemas.

Sources
-------
1. EPA AirNow AQI (keyed REST, hourly — AIRNOW_API_KEY env var)
2. USDM U.S. Drought Monitor (weekly GeoJSON, DM category 0–4)
3. NOAA NCEI Storm Events (annual gzip CSV, 51 cols)
4. USGS NWIS stream gauges (keyless bbox, parameter 00060)
5. NOAA tide gauges (coastal-metro stations, 6-min water level)
"""

from __future__ import annotations

import csv
import gzip
import io
import math
import os
import re
from collections.abc import Generator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import h3  # needed for areal intersection (USDM)
import httpx

from src.producers.csv_client import _normalize_header
from src.spatial.airnow_signal import aqi_shock_score
from src.spatial.h3_indexer import H3SpatialIndexer

# --------------------------------------------------------------------------- #
# Constants                                                                   #
# --------------------------------------------------------------------------- #

AIRNOW_BASE = "https://www.airnowapi.org/aq"
AIRNOW_API_KEY_ENV = "AIRNOW_API_KEY"

USDM_CURRENT_URL = "https://droughtmonitor.unl.edu/data/json/usdm_current.json"

STORM_EVENTS_TEMPLATE = (
    "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
    "StormEvents_details-ftp_v1.0_d{year}_c{created}.csv.gz"
)
DEFAULT_STORM_EVENTS_URL = STORM_EVENTS_TEMPLATE.format(year=2026, created=20260819)

NWIS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"

TIDE_DATAGETTER_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

COASTAL_TIDE_STATIONS: dict[str, list[str]] = {
    "nyc": ["8518750"],
    "seattle": ["9447130"],
    "san_francisco": ["9414290"],
    "los_angeles": ["9410660"],
    "norfolk": ["8638610"],
    "new_orleans": ["8761927"],
    "honolulu": ["1612340"],
    "miami_dade": ["8724580"],
    "boston": ["8443970"],
    "san_diego": ["9410170"],
    "tampa": ["8726667"],
    "virginia_beach": ["8638863"],
}

# --------------------------------------------------------------------------- #
# Shared output dataclass                                                     #
# --------------------------------------------------------------------------- #


@dataclass
class EnvironmentalStressReading:
    """One covariate record destined for ``EnrichedH3Feature`` context.

    Leaf-local shadow of ``ContextObservationEvent`` so a future spine-bound
    producer can fold these into the feature store without adding a new schema.
    """

    source: str  # airnow | usdm | storm_events | nwis | tide
    metric: str
    value: float
    unit: str | None = None
    asset_id: str | None = None
    period_start: str | None = None
    city_id: str | None = None
    lat: float | None = None
    lng: float | None = None
    h3_res7: str | None = None
    h3_res8: str | None = None
    h3_res9: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def _tag_h3(lat: float, lng: float) -> dict[str, str | None]:
    """Map a point to the H3 res 7/8/9 hierarchy."""
    try:
        return H3SpatialIndexer.get_multi_res_hierarchy(lat, lng)
    except (ValueError, TypeError):
        return {"h3_res7": None, "h3_res8": None, "h3_res9": None}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km between two coordinates."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# --------------------------------------------------------------------------- #
# 1. AirNowClient                                                              #
# --------------------------------------------------------------------------- #


@dataclass
class AirNowObservation:
    """One parsed AirNow API observation or forecast row."""

    date_observed: str
    hour_observed: int | None
    local_time_zone: str
    reporting_area: str
    state_code: str
    latitude: float
    longitude: float
    parameter_name: str
    aqi: float | None
    category_number: int | None
    category_name: str | None
    action_day: bool | None = None
    date_forecast: str | None = None
    discussion: str | None = None


class AirNowClient:
    """Keyed AirNow REST API client for AQI observations and forecasts.

    Requires an API key set via the ``AIRNOW_API_KEY`` environment variable
    or passed to the constructor.
    """

    def __init__(
        self,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
    ):
        self.api_key = api_key or os.environ.get(AIRNOW_API_KEY_ENV)
        self.http = http_client or httpx.Client(timeout=60.0, follow_redirects=True)

    def _require_key(self) -> str:
        key = self.api_key
        if not key:
            raise RuntimeError(
                "AirNow API key required. Set AIRNOW_API_KEY in the environment "
                "or pass api_key= to the constructor."
            )
        return key

    @staticmethod
    def parse_observations(payload: Any) -> list[AirNowObservation]:
        """Parse a JSON array from ``/observation/zipCode/current/``."""
        if not isinstance(payload, list):
            raise TypeError("AirNow observation payload must be a JSON array")
        results: list[AirNowObservation] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            cat = item.get("Category") or {}
            results.append(
                AirNowObservation(
                    date_observed=str(item.get("DateObserved", "")).strip(),
                    hour_observed=item.get("HourObserved"),
                    local_time_zone=str(item.get("LocalTimeZone", "")),
                    reporting_area=str(item.get("ReportingArea", "")),
                    state_code=str(item.get("StateCode", "")),
                    latitude=float(item.get("Latitude", 0) or 0),
                    longitude=float(item.get("Longitude", 0) or 0),
                    parameter_name=str(item.get("ParameterName", "")),
                    aqi=float(item["AQI"]) if item.get("AQI") is not None else None,
                    category_number=cat.get("Number"),
                    category_name=cat.get("Name"),
                )
            )
        return results

    @staticmethod
    def parse_forecasts(payload: Any) -> list[AirNowObservation]:
        """Parse a JSON array from ``/forecast/zipCode/``."""
        if not isinstance(payload, list):
            raise TypeError("AirNow forecast payload must be a JSON array")
        results: list[AirNowObservation] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            cat = item.get("Category") or {}
            results.append(
                AirNowObservation(
                    date_observed=str(item.get("DateIssue", "")).strip(),
                    hour_observed=None,
                    local_time_zone=str(item.get("LocalTimeZone", "")),
                    reporting_area=str(item.get("ReportingArea", "")),
                    state_code=str(item.get("StateCode", "")),
                    latitude=float(item.get("Latitude", 0) or 0),
                    longitude=float(item.get("Longitude", 0) or 0),
                    parameter_name=str(item.get("ParameterName", "")),
                    aqi=float(item["AQI"]) if item.get("AQI") is not None else None,
                    category_number=cat.get("Number"),
                    category_name=cat.get("Name"),
                    action_day=bool(item.get("ActionDay", False)),
                    date_forecast=str(item.get("DateForecast", "")).strip() or None,
                    discussion=str(item.get("Discussion", "")).strip() or None,
                )
            )
        return results

    def fetch_observations(
        self,
        zip_code: str,
        distance: int = 25,
    ) -> list[AirNowObservation]:
        """Fetch current hourly observations for a ZIP code."""
        key = self._require_key()
        resp = self.http.get(
            f"{AIRNOW_BASE}/observation/zipCode/current/",
            params={
                "format": "application/json",
                "zipCode": zip_code,
                "distance": distance,
                "API_KEY": key,
            },
        )
        resp.raise_for_status()
        return self.parse_observations(resp.json())

    def fetch_forecast(
        self,
        zip_code: str,
        date: str | None = None,
        distance: int = 25,
    ) -> list[AirNowObservation]:
        """Fetch forecast for a ZIP code."""
        key = self._require_key()
        params: dict[str, Any] = {
            "format": "application/json",
            "zipCode": zip_code,
            "distance": distance,
            "API_KEY": key,
        }
        if date:
            params["date"] = date
        resp = self.http.get(
            f"{AIRNOW_BASE}/forecast/zipCode/",
            params=params,
        )
        resp.raise_for_status()
        return self.parse_forecasts(resp.json())

    @staticmethod
    def to_readings(
        observations: list[AirNowObservation],
    ) -> list[EnvironmentalStressReading]:
        """Convert parsed observations to stress readings."""
        readings: list[EnvironmentalStressReading] = []
        for obs in observations:
            h3_tags = _tag_h3(obs.latitude, obs.longitude)
            period = obs.date_observed
            if obs.hour_observed is not None and obs.date_observed and len(obs.date_observed) <= 12:
                period = f"{obs.date_observed[:10]} {obs.hour_observed:02d}:00:00"
            readings.append(
                EnvironmentalStressReading(
                    source="airnow",
                    metric="aqi",
                    value=float(obs.aqi) if obs.aqi is not None else 0.0,
                    unit="AQI",
                    asset_id=f"{obs.reporting_area}|{obs.state_code}|{obs.parameter_name}",
                    period_start=period,
                    lat=obs.latitude,
                    lng=obs.longitude,
                    h3_res7=h3_tags["h3_res7"],
                    h3_res8=h3_tags["h3_res8"],
                    h3_res9=h3_tags["h3_res9"],
                    extra={
                        "parameter": obs.parameter_name,
                        "category": obs.category_name,
                        "shock": aqi_shock_score(obs.aqi),
                        "reporting_area": obs.reporting_area,
                        "state_code": obs.state_code,
                    },
                )
            )
        return readings


# --------------------------------------------------------------------------- #
# 2. UsdmClient                                                                #
# --------------------------------------------------------------------------- #


def _signed_area(ring: Sequence[tuple[float, float]]) -> float:
    """Signed planar area of a lat/lng ring. Positive = CCW."""
    n = len(ring)
    if n < 3:
        return 0.0
    return sum(
        (ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1])
        for i in range(n - 1)
    )


def _as_latlng_poly(coords: list[Any]) -> h3.LatLngPoly | None:
    """Convert a GeoJSON polygon coordinate list to a LatLngPoly.

    ``coords`` is the first element of a GeoJSON Polygon coordinate array:
    a list of ``[lng, lat]`` rings. The first ring is the outer boundary;
    subsequent rings are holes.
    """
    if not coords or not isinstance(coords, list):
        return None
    outer_raw = coords[0]
    if not outer_raw or len(outer_raw) < 3:
        return None
    outer = [(p[1], p[0]) for p in outer_raw if isinstance(p, (list, tuple)) and len(p) >= 2]
    if len(outer) < 3:
        return None
    if _signed_area(outer) < 0:
        outer = outer[::-1]
    holes: list[list[tuple[float, float]]] = []
    for hole_raw in coords[1:]:
        if not hole_raw or len(hole_raw) < 3:
            continue
        hole = [(p[1], p[0]) for p in hole_raw if isinstance(p, (list, tuple)) and len(p) >= 2]
        if len(hole) < 3:
            continue
        if _signed_area(hole) > 0:
            hole = hole[::-1]
        holes.append(hole)
    return h3.LatLngPoly(outer, *holes) if holes else h3.LatLngPoly(outer)


def _polygons_from_geometry(geometry: dict[str, Any]) -> list[h3.LatLngPoly]:
    """Extract LatLngPoly objects from a GeoJSON geometry dict."""
    polys: list[h3.LatLngPoly] = []
    gtype = geometry.get("type", "")
    coords = geometry.get("coordinates", [])
    if gtype == "Polygon":
        p = _as_latlng_poly(coords)
        if p is not None:
            polys.append(p)
    elif gtype == "MultiPolygon":
        for poly_coords in coords:
            p = _as_latlng_poly(poly_coords)
            if p is not None:
                polys.append(p)
    return polys


def _cells_for_polygon(poly: h3.LatLngPoly, resolution: int) -> set[str]:
    """Return the set of H3 cells intersecting a polygon (areal intersection)."""
    try:
        return set(h3.h3shape_to_cells(poly, resolution))
    except (ValueError, TypeError):
        return set()


def _fold_dm_cells(
    cells_by_dm: dict[int, set[str]],
    resolution: int,
) -> dict[str, int]:
    """Fold cells by DM severity: if a cell appears under multiple DM, keep max.

    Returns ``{h3_cell: max_dm}``.
    """
    folded: dict[str, int] = {}
    for dm, cells in cells_by_dm.items():
        for cell in cells:
            existing = folded.get(cell)
            if existing is None or dm > existing:
                folded[cell] = dm
    return folded


class UsdmClient:
    """Client for the USDM drought-monitor GeoJSON.

    The live ``usdm_current.json`` is a GeoJSON FeatureCollection where each
    feature carries a ``DM`` property (0–4 drought severity) and a MultiPolygon
    geometry. This client does H3 *areal intersection* over the polygons
    (``h3.h3shape_to_cells``) — zero new raster machinery.
    """

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        resolution: int = 8,
    ):
        self.http = http_client or httpx.Client(timeout=60.0, follow_redirects=True)
        self.resolution = resolution

    def fetch(
        self,
        url: str = USDM_CURRENT_URL,
    ) -> list[EnvironmentalStressReading]:
        """Fetch the current USDM GeoJSON and return per-cell readings."""
        resp = self.http.get(url)
        resp.raise_for_status()
        return self.parse_payload(resp.json(), self.resolution)

    @staticmethod
    def parse_payload(
        payload: Any,
        resolution: int = 8,
    ) -> list[EnvironmentalStressReading]:
        """Parse a USDM GeoJSON FeatureCollection into stress readings."""
        if not isinstance(payload, dict):
            raise TypeError("USDM payload must be a GeoJSON object")
        features = payload.get("features")
        if not isinstance(features, list):
            raise TypeError("USDM payload missing 'features' array")

        cells_by_dm: dict[int, set[str]] = {}
        for feature in features:
            props = feature.get("properties", {}) if isinstance(feature, dict) else {}
            dm = props.get("DM")
            if dm is None or not isinstance(dm, (int, float)):
                continue
            dm_int = int(dm)
            if dm_int < 0 or dm_int > 4:
                continue
            geometry = feature.get("geometry") if isinstance(feature, dict) else None
            if not isinstance(geometry, dict):
                continue
            polys = _polygons_from_geometry(geometry)
            for poly in polys:
                cells = _cells_for_polygon(poly, resolution)
                cells_by_dm.setdefault(dm_int, set()).update(cells)

        folded = _fold_dm_cells(cells_by_dm, resolution)
        readings: list[EnvironmentalStressReading] = []
        for cell, dm in folded.items():
            h3_center = h3.cell_to_latlng(cell)
            h3_res7 = h3.cell_to_parent(cell, 7) if resolution >= 7 else None
            h3_res8 = (
                cell
                if resolution == 8
                else (h3.cell_to_parent(cell, 8) if resolution > 8 else None)
            )
            h3_res9 = cell if resolution == 9 else None
            readings.append(
                EnvironmentalStressReading(
                    source="usdm",
                    metric="dm_category",
                    value=float(dm),
                    unit="category",
                    asset_id=cell,
                    period_start=str(datetime.now(UTC).date()),
                    lat=h3_center[0],
                    lng=h3_center[1],
                    h3_res7=h3_res7,
                    h3_res8=h3_res8,
                    h3_res9=h3_res9,
                    extra={"dm": dm, "resolution": resolution},
                )
            )
        return readings


# --------------------------------------------------------------------------- #
# 3. StormEventsClient                                                         #
# --------------------------------------------------------------------------- #

_DAMAGE_RE = re.compile(
    r"^(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>[KMBkmb])?$"
)


@dataclass
class StormEvent:
    """One parsed row from the NCEI Storm Events CSV."""

    event_id: str
    episode_id: str | None = None
    state: str | None = None
    event_type: str | None = None
    begin_date_time: str | None = None
    begin_lat: float | None = None
    begin_lon: float | None = None
    damage_property: float | None = None
    damage_crops: float | None = None
    injuries_direct: int = 0
    deaths_direct: int = 0
    cz_fips: str | None = None
    cz_name: str | None = None


class StormEventsClient:
    """Downloads and parses the annual NCEI Storm Events gzip CSV.

    Reuses the ``_ByteStream`` streaming pattern from ``sba_client.py``
    adapted for in-memory gzip decompression. The CSV has 51 columns
    verified live (``d2026_c20260819``, 2.9 MB gzip).
    """

    def __init__(self, http_client: httpx.Client | None = None):
        self.http = http_client or httpx.Client(timeout=300.0, follow_redirects=True)

    @staticmethod
    def parse_damage(raw: Any) -> float | None:
        """Parse a ``DAMAGE_PROPERTY`` or ``DAMAGE_CROPS`` value.

        "10.00K" → 10000.0, "1.50M" → 1500000.0, "500" → 500.0,
        empty/None → None.
        """
        if raw is None:
            return None
        text = str(raw).strip()
        if not text or text in (".", "-", "NA", "N/A", "null", "None"):
            return None
        text = text.replace(",", "")
        m = _DAMAGE_RE.match(text)
        if not m:
            return None
        val = float(m.group("val"))
        unit = m.group("unit")
        if unit:
            unit = unit.upper()
            if unit == "K":
                val *= 1_000
            elif unit == "M":
                val *= 1_000_000
            elif unit == "B":
                val *= 1_000_000_000
        return val

    @staticmethod
    def parse_csv_bytes(
        raw: bytes,
        max_records: int | None = None,
    ) -> Generator[StormEvent, None, None]:
        """Parse gzip-compressed CSV bytes into StormEvent records."""
        _buf = io.BytesIO(raw)
        with gzip.GzipFile(fileobj=_buf, mode="rb") as gz:
            text = io.TextIOWrapper(gz, encoding="utf-8", errors="replace")
            reader = csv.DictReader(text)
            if reader.fieldnames:
                reader.fieldnames = [_normalize_header(h) for h in reader.fieldnames]
            for count, row in enumerate(reader):
                if max_records is not None and count >= max_records:
                    return
                lat_raw = row.get("begin_lat")
                lon_raw = row.get("begin_lon")
                begin_lat = float(lat_raw) if lat_raw else None
                begin_lon = float(lon_raw) if lon_raw else None
                yield StormEvent(
                    event_id=str(row.get("event_id", "")).strip(),
                    episode_id=str(row.get("episode_id", "")).strip() or None,
                    state=str(row.get("state", "")).strip() or None,
                    event_type=str(row.get("event_type", "")).strip() or None,
                    begin_date_time=str(row.get("begin_date_time", "")).strip() or None,
                    begin_lat=begin_lat,
                    begin_lon=begin_lon,
                    damage_property=StormEventsClient.parse_damage(row.get("damage_property")),
                    damage_crops=StormEventsClient.parse_damage(row.get("damage_crops")),
                    injuries_direct=int(float(row.get("injuries_direct", 0) or 0)),
                    deaths_direct=int(float(row.get("deaths_direct", 0) or 0)),
                    cz_fips=str(row.get("cz_fips", "")).strip() or None,
                    cz_name=str(row.get("cz_name", "")).strip() or None,
                )

    def fetch(
        self,
        url: str = DEFAULT_STORM_EVENTS_URL,
        max_records: int | None = None,
    ) -> Generator[StormEvent, None, None]:
        """Download and parse the gzip CSV from the given URL."""
        with self.http.stream("GET", url) as resp:
            resp.raise_for_status()
            raw = resp.read()
            yield from self.parse_csv_bytes(raw, max_records=max_records)

    @staticmethod
    def to_readings(
        events: list[StormEvent],
    ) -> list[EnvironmentalStressReading]:
        """Convert storm events to per-cell aggregated readings.

        Per H3 cell: max event count, max damage, max injuries/deaths.
        """
        cell_data: dict[str, dict[str, Any]] = {}
        for ev in events:
            if ev.begin_lat is None or ev.begin_lon is None:
                continue
            h3_tags = _tag_h3(ev.begin_lat, ev.begin_lon)
            cell = h3_tags.get("h3_res9") or h3_tags.get("h3_res8") or h3_tags.get("h3_res7")
            if not cell:
                continue
            entry = cell_data.setdefault(
                cell,
                {
                    "count": 0,
                    "max_damage": 0.0,
                    "max_injuries": 0,
                    "max_deaths": 0,
                    "h3_res7": h3_tags.get("h3_res7"),
                    "h3_res8": h3_tags.get("h3_res8"),
                    "h3_res9": h3_tags.get("h3_res9"),
                    "first_lat": ev.begin_lat,
                    "first_lon": ev.begin_lon,
                },
            )
            entry["count"] += 1
            if ev.damage_property is not None and ev.damage_property > entry["max_damage"]:
                entry["max_damage"] = ev.damage_property
            entry["max_injuries"] = max(entry["max_injuries"], ev.injuries_direct)
            entry["max_deaths"] = max(entry["max_deaths"], ev.deaths_direct)

        readings: list[EnvironmentalStressReading] = []
        for cell, data in cell_data.items():
            readings.append(
                EnvironmentalStressReading(
                    source="storm_events",
                    metric="storm_event_count",
                    value=float(data["count"]),
                    unit="events",
                    asset_id=cell,
                    lat=data["first_lat"],
                    lng=data["first_lon"],
                    h3_res7=data["h3_res7"],
                    h3_res8=data["h3_res8"],
                    h3_res9=data["h3_res9"],
                    extra={
                        "max_damage_property": data["max_damage"],
                        "max_injuries": data["max_injuries"],
                        "max_deaths": data["max_deaths"],
                    },
                )
            )
        return readings


# --------------------------------------------------------------------------- #
# 4. NwisClient                                                                #
# --------------------------------------------------------------------------- #


@dataclass
class StreamGauge:
    """One USGS stream gauge observation."""

    site_id: str
    site_name: str
    latitude: float
    longitude: float
    value: float | None
    value_time: str | None
    parameter_code: str = "00060"
    unit: str | None = "ft3/s"


class NwisClient:
    """Keyless USGS NWIS Instantaneous Values client.

    Queries by metro bbox (parameter 00060 = streamflow, ft³/s).
    Verified live: ``bBox`` is ``west,south,east,north`` (min_lng,min_lat,
    max_lng,max_lat).
    """

    def __init__(self, http_client: httpx.Client | None = None):
        self.http = http_client or httpx.Client(timeout=60.0, follow_redirects=True)

    @staticmethod
    def parse_response(payload: Any) -> list[StreamGauge]:
        """Parse the NWIS JSON time-series response."""
        gauges: list[StreamGauge] = []
        if not isinstance(payload, dict):
            return gauges
        value = payload.get("value")
        if not isinstance(value, dict):
            return gauges
        time_series = value.get("timeSeries")
        if not isinstance(time_series, list):
            return gauges
        for ts in time_series:
            if not isinstance(ts, dict):
                continue
            source_info = ts.get("sourceInfo")
            if not isinstance(source_info, dict):
                continue
            site_codes = source_info.get("siteCode")
            site_id = ""
            if isinstance(site_codes, list) and site_codes:
                sc = site_codes[0]
                if isinstance(sc, dict):
                    site_id = str(sc.get("value", ""))
            site_name = str(source_info.get("siteName", "")).strip()
            geo = source_info.get("geoLocation", {})
            gl = geo.get("geogLocation", {}) if isinstance(geo, dict) else {}
            lat = float(gl.get("latitude", 0) or 0)
            lng = float(gl.get("longitude", 0) or 0)
            if not lat and not lng:
                continue
            var = ts.get("variable")
            unit = "ft3/s"
            param_cd = "00060"
            if isinstance(var, dict):
                unit = ((var.get("unit") or {}) if isinstance(var.get("unit"), dict) else {}).get("unitCode", "ft3/s")
                vc = var.get("variableCode")
                if isinstance(vc, list) and vc:
                    param_cd = str(vc[0].get("value", "00060")) if isinstance(vc[0], dict) else "00060"
            values_list = ts.get("values")
            value = None
            value_time = None
            if isinstance(values_list, list) and values_list:
                vs = values_list[0]
                if isinstance(vs, dict):
                    vlist = vs.get("value")
                    if isinstance(vlist, list) and vlist:
                        latest = vlist[-1]
                        if isinstance(latest, dict):
                            raw = latest.get("value")
                            value = float(raw) if raw else None
                            value_time = str(latest.get("dateTime", "")) or None
                    no_data = vs.get("noDataValue") if isinstance(vs, dict) else None
                    if no_data is not None and value is not None:
                        nd = float(no_data)
                        if abs(value - nd) < 0.001:
                            value = None
            if value is not None:
                gauges.append(
                    StreamGauge(
                        site_id=site_id,
                        site_name=site_name,
                        latitude=lat,
                        longitude=lng,
                        value=value,
                        value_time=value_time,
                        parameter_code=param_cd,
                        unit=unit,
                    )
                )
        return gauges

    def fetch_by_bbox(
        self,
        bbox: dict[str, float],
        parameter_cd: str = "00060",
    ) -> list[StreamGauge]:
        """Fetch stream gauges within a metro bbox.

        ``bbox`` must have keys ``min_lat``, ``max_lat``, ``min_lng``, ``max_lng``
        (the repo's ``metro_bbox`` convention). USGS ``bBox`` is
        ``west,south,east,north``.
        """
        bbox_str = f"{bbox['min_lng']},{bbox['min_lat']},{bbox['max_lng']},{bbox['max_lat']}"
        resp = self.http.get(
            NWIS_IV_URL,
            params={
                "format": "json",
                "bBox": bbox_str,
                "parameterCd": parameter_cd,
                "siteStatus": "active",
            },
        )
        resp.raise_for_status()
        return self.parse_response(resp.json())

    @staticmethod
    def nearest_gauge(
        gauges: list[StreamGauge],
        lat: float,
        lng: float,
    ) -> tuple[StreamGauge, float] | None:
        """Return the gauge closest to (lat, lng) and the distance in km."""
        if not gauges:
            return None
        best: tuple[StreamGauge, float] | None = None
        for g in gauges:
            d = _haversine_km(lat, lng, g.latitude, g.longitude)
            if best is None or d < best[1]:
                best = (g, d)
        return best

    @staticmethod
    def to_readings(
        gauges: list[StreamGauge],
        city_id: str | None = None,
    ) -> list[EnvironmentalStressReading]:
        """Convert stream gauges to stress readings."""
        readings: list[EnvironmentalStressReading] = []
        for g in gauges:
            h3_tags = _tag_h3(g.latitude, g.longitude)
            readings.append(
                EnvironmentalStressReading(
                    source="nwis",
                    metric="streamflow",
                    value=g.value if g.value is not None else 0.0,
                    unit=g.unit,
                    asset_id=g.site_id,
                    period_start=g.value_time,
                    city_id=city_id,
                    lat=g.latitude,
                    lng=g.longitude,
                    h3_res7=h3_tags["h3_res7"],
                    h3_res8=h3_tags["h3_res8"],
                    h3_res9=h3_tags["h3_res9"],
                    extra={"site_name": g.site_name},
                )
            )
        return readings


# --------------------------------------------------------------------------- #
# 5. TideGaugeClient                                                            #
# --------------------------------------------------------------------------- #


@dataclass
class TideReading:
    """One parsed NOAA tide datagetter response."""

    station_id: str
    station_name: str
    latitude: float
    longitude: float
    water_level_m: float | None
    timestamp: str | None
    sigma: float | None = None
    flag: str | None = None


class TideGaugeClient:
    """Per-station NOAA tide gauge client (coastal metros only).

    Uses the ``datagetter`` API with ``product=water_level``, ``datum=MSL``,
    ``units=metric``, ``time_zone=gmt``. Verified live on station 9414290
    (San Francisco).
    """

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        station_map: dict[str, list[str]] | None = None,
    ):
        self.http = http_client or httpx.Client(timeout=60.0, follow_redirects=True)
        self.station_map = station_map or COASTAL_TIDE_STATIONS

    @staticmethod
    def parse_response(payload: Any) -> TideReading:
        """Parse the datagetter JSON response."""
        if not isinstance(payload, dict):
            raise TypeError("Tide datagetter payload must be a JSON object")
        meta = payload.get("metadata")
        if not isinstance(meta, dict):
            raise TypeError("Tide datagetter response missing 'metadata'")
        station_id = str(meta.get("id", ""))
        station_name = str(meta.get("name", ""))
        lat = float(meta.get("lat", 0) or 0)
        lon = float(meta.get("lon", 0) or 0)
        data = payload.get("data")
        if not isinstance(data, list) or not data:
            return TideReading(
                station_id=station_id,
                station_name=station_name,
                latitude=lat,
                longitude=lon,
                water_level_m=None,
                timestamp=None,
            )
        latest = data[0]
        if not isinstance(latest, dict):
            return TideReading(
                station_id=station_id,
                station_name=station_name,
                latitude=lat,
                longitude=lon,
                water_level_m=None,
                timestamp=None,
            )
        wl = float(latest["v"]) if latest.get("v") is not None else None
        return TideReading(
            station_id=station_id,
            station_name=station_name,
            latitude=lat,
            longitude=lon,
            water_level_m=wl,
            timestamp=str(latest.get("t", "")).strip() or None,
            sigma=float(latest["s"]) if latest.get("s") is not None else None,
            flag=str(latest.get("q", "")).strip() or None,
        )

    def fetch_station(
        self,
        station_id: str,
        datum: str = "MSL",
        units: str = "metric",
        time_zone: str = "gmt",
    ) -> TideReading:
        """Fetch current water level for a single station."""
        resp = self.http.get(
            TIDE_DATAGETTER_URL,
            params={
                "station": station_id,
                "product": "water_level",
                "datum": datum,
                "units": units,
                "time_zone": time_zone,
                "format": "json",
                "date": "latest",
            },
        )
        resp.raise_for_status()
        return self.parse_response(resp.json())

    def fetch_coastal_metros(
        self,
        city_ids: list[str] | None = None,
    ) -> Generator[tuple[str, TideReading], None, None]:
        """Fetch all tide stations for the given (or all known) coastal metros.

        Yields ``(city_id, TideReading)`` pairs.
        """
        targets = {}
        if city_ids:
            for cid in city_ids:
                stations = self.station_map.get(cid)
                if stations:
                    targets[cid] = stations
        else:
            targets = dict(self.station_map)
        for cid, stations in targets.items():
            for sid in stations:
                try:
                    reading = self.fetch_station(sid)
                    yield (cid, reading)
                except httpx.HTTPError:
                    continue

    @staticmethod
    def to_readings(
        readings: list[tuple[str, TideReading]],
    ) -> list[EnvironmentalStressReading]:
        """Convert tide readings to stress readings."""
        result: list[EnvironmentalStressReading] = []
        for city_id, r in readings:
            h3_tags = _tag_h3(r.latitude, r.longitude)
            val = r.water_level_m if r.water_level_m is not None else 0.0
            result.append(
                EnvironmentalStressReading(
                    source="tide",
                    metric="water_level",
                    value=val,
                    unit="m",
                    asset_id=r.station_id,
                    period_start=r.timestamp,
                    city_id=city_id,
                    lat=r.latitude,
                    lng=r.longitude,
                    h3_res7=h3_tags["h3_res7"],
                    h3_res8=h3_tags["h3_res8"],
                    h3_res9=h3_tags["h3_res9"],
                    extra={"station_name": r.station_name},
                )
            )
        return result