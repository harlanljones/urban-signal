"""AirNow reporting-area AQI → H3 leaf module (US-390, NO spine edits).

Pure parsing / mapping helpers that turn one row of AirNow's public,
credential-free ``reportingarea.dat`` file product (a pipe-delimited line:
current date, valid date, hour, timezone, offset, row type, action-day flag,
reporting area, state, lat, lng, parameter, AQI, category, forecast URL,
agency) into a typed observation, project the reporting area's point onto the
repo's H3 res 7/8/9 spatial units, and fold observed AQI into a per-cell shock
score.

This is intentionally a *leaf* file: it imports ONLY from `h3_indexer` (itself
a leaf file), so it can land in the repo without touching any spine file
(config / city_registry / geo_utils / submarkets / producers). Registering
AirNow/AQS as a live context `FeedType` would be an interlock/spine change and
is explicitly out of scope for this stream — see
`docs/research/airnow-aqs-validation.md` (recommendation: ADOPT the signal as a
context/anchor layer, DEFER the feed registration). The helpers here are the
reusable, spine-free building block a future spine-bound registration would call.
"""

from dataclasses import dataclass
from enum import Enum

from src.spatial.h3_indexer import H3SpatialIndexer

# EPA AQI category breakpoints (the AQI index itself, 0–500).
# Used to turn an AQI value into a 0–1 shock score.
AQI_CATEGORY_BREAKPOINTS: list[tuple[int, str, float]] = [
    (50, "Good", 0.0),
    (100, "Moderate", 0.2),
    (150, "Unhealthy for Sensitive Groups", 0.4),
    (200, "Unhealthy", 0.6),
    (300, "Very Unhealthy", 0.8),
    (500, "Hazardous", 1.0),
]


class AirNowRowType(str, Enum):
    """The 6th column of reportingarea.dat: what kind of row this is."""

    OBSERVED = "O"      # current-hour observed AQI
    FORECAST = "F"      # forecast AQI (future day, forecast URL present)
    YESTERDAY = "Y"     # yesterday's observation


@dataclass
class AirNowObservation:
    """One parsed reportingarea.dat row (observed or forecast)."""

    current_date: str
    valid_date: str
    hour: str | None
    timezone: str
    day_offset: int
    row_type: AirNowRowType
    action_day: bool
    area_name: str
    state: str
    lat: float
    lng: float
    parameter: str  # OZONE / PM2.5 / PM10 / ...
    aqi: float | None  # None for forecast rows
    category: str
    agency: str


def parse_reporting_area_row(line: str) -> AirNowObservation:
    """Parse one pipe-delimited reportingarea.dat row (17 columns)."""
    parts = line.rstrip("\n").split("|")
    if len(parts) < 17:
        raise ValueError(f"reportingarea.dat row has {len(parts)} fields, expected 17")
    hour = parts[2].strip() or None
    aqi_raw = parts[12].strip()
    aqi = float(aqi_raw) if aqi_raw else None
    return AirNowObservation(
        current_date=parts[0].strip(),
        valid_date=parts[1].strip(),
        hour=hour,
        timezone=parts[3].strip(),
        day_offset=int(parts[4].strip() or 0),
        row_type=AirNowRowType(parts[5].strip()),
        action_day=(parts[6].strip().upper() == "Y"),
        area_name=parts[7].strip(),
        state=parts[8].strip(),
        lat=float(parts[9].strip()),
        lng=float(parts[10].strip()),
        parameter=parts[11].strip(),
        aqi=aqi,
        category=parts[13].strip(),
        agency=parts[16].strip(),
    )


def aqi_shock_score(aqi: float | None) -> float:
    """Map an AQI value to a 0–1 short-lived environmental-stress score.

    Uses the EPA AQI category breakpoints on the AQI index itself:
    Good=0.0, Moderate=0.2, USG=0.4, Unhealthy=0.6, Very Unhealthy=0.8,
    Hazardous=1.0. A missing AQI (forecast row) scores 0.0 — never fabricate
    a shock from an absent measurement.
    """
    if aqi is None or aqi < 0:
        return 0.0
    for top, _name, score in AQI_CATEGORY_BREAKPOINTS:
        if aqi <= top:
            return score
    return 1.0


def map_reporting_area_to_h3(obs: AirNowObservation) -> dict[str, str]:
    """Resolve a reporting area's point coordinate to the H3 res 7/8/9 hierarchy.

    Mirrors exactly how event feeds resolve a row to H3 in the repo, so a
    future AirNow producer can reuse `H3SpatialIndexer.get_multi_res_hierarchy`
    without any new joiner.
    """
    return H3SpatialIndexer.get_multi_res_hierarchy(obs.lat, obs.lng)


def fold_observations_by_cell(
    observations: list[AirNowObservation],
) -> dict[str, dict[str, object]]:
    """Fold observed rows into a per-res-9-cell shock tally.

    Returns {h3_res9: {"max_aqi": float, "shock": float, "count": int}}
    considering only OBSERVED rows (forecast/yesterday rows are excluded so a
    preliminary read never masquerades as a current shock). Callers roll up via
    `H3SpatialIndexer.get_parent` to res 8 / res 7 for sparse-cell smoothing
    (same `dynamic_spatial_fallback` pattern the repo uses elsewhere).
    """
    tally: dict[str, dict[str, object]] = {}
    for obs in observations:
        if obs.row_type is not AirNowRowType.OBSERVED or obs.aqi is None:
            continue
        hierarchy = map_reporting_area_to_h3(obs)
        res9 = hierarchy["h3_res9"]
        entry = tally.setdefault(
            res9,
            {"max_aqi": 0.0, "shock": 0.0, "count": 0},
        )
        entry["max_aqi"] = max(float(entry["max_aqi"]), obs.aqi)
        entry["shock"] = max(float(entry["shock"]), aqi_shock_score(obs.aqi))
        entry["count"] = int(entry["count"]) + 1
    return tally
