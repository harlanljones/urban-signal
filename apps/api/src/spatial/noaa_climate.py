"""NOAA NCEI climate-observation context layer — leaf module (US-173, NO spine edits).

Pure station-selection / missingness / H3-mapping helpers for daily NOAA GHCND
observations (TMAX/TMIN/TAVG, PRCP, SNOW/SNWD, AWND). This is intentionally a
*leaf* file: it imports ONLY from `h3_indexer` (itself a leaf file), so it can
land in the repo without touching any spine file (config / city_registry /
geo_utils / submarkets / producers). Registering NOAA as a live `FeedType` would
be an interlock/spine change and is explicitly out of scope for this stream — see
`docs/research/noaa-climate-validation.md` (recommendation: ADOPT data, DEFER
integration). The helpers here are the reusable, spine-free building block a
future spine-bound registration would call.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass

from src.spatial.h3_indexer import H3SpatialIndexer

# GHCND quality flags that mean "do not trust this value" (S=suspect, H=estimated,
# and the failed/withheld set). Blank and numeric/ok codes pass.
BAD_QUALITY_FLAGS = {"S", "H", "D", "G", "I", "K", "L", "M", "N", "O", "R", "W", "X", "Z"}
# Trace precipitation/snow (documented GHCND encoding).
TRACE_FLAG = "T"


@dataclass(frozen=True)
class NoaaStation:
    """One GHCND station from `ghcnd-stations.txt` (id, lat, lon, elev, name)."""

    station_id: str
    lat: float
    lng: float
    elevation_m: float
    name: str


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometers between two WGS84 points."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def stations_within_bbox(
    stations: Iterable[NoaaStation],
    bbox: dict[str, float],
) -> list[NoaaStation]:
    """Filter a station inventory to a metro bbox (mirrors event-feed bbox gating)."""
    return [
        s
        for s in stations
        if bbox["min_lat"] <= s.lat <= bbox["max_lat"]
        and bbox["min_lng"] <= s.lng <= bbox["max_lng"]
    ]


def nearest_station(
    stations: Iterable[NoaaStation],
    lat: float,
    lng: float,
) -> NoaaStation | None:
    """Return the station closest to (lat, lng) by haversine distance, or None."""
    best: NoaaStation | None = None
    best_d = math.inf
    for s in stations:
        d = haversine_km(s.lat, s.lng, lat, lng)
        if d < best_d:
            best, best_d = s, d
    return best


def obs_quality_ok(value: float | None, attributes: str = "") -> bool:
    """Whether a parsed daily value is usable given its GHCND `_ATTRIBUTES` field.

    The attributes field encodes source/quality/obs-time codes. Values whose
    quality code is a known bad flag (or that are None/missing) are rejected so
    missing or suspect observations never silently become zero.
    """
    if value is None:
        return False
    flags = {c for c in attributes if c.isalpha()}
    return not (flags & BAD_QUALITY_FLAGS)


def daily_coverage(rows: Iterable[dict], variable: str) -> float:
    """Fraction of station-days with a quality-passing value for `variable`.

    `rows` are dicts with at least `{variable}` and `{variable}_ATTRIBUTES` keys.
    Returns 0.0 if no rows are supplied.
    """
    usable = 0
    total = 0
    for row in rows:
        total += 1
        if obs_quality_ok(row.get(variable), str(row.get(f"{variable}_ATTRIBUTES") or "")):
            usable += 1
    return (usable / total) if total else 0.0


def daily_anomaly(value: float, baseline: float) -> float:
    """Simple daily anomaly: deviation from a climatological baseline (Δ)."""
    return value - baseline


def map_station_to_h3(lat: float, lng: float) -> dict[str, str]:
    """Resolve a station point to the H3 res 7/8/9 hierarchy (same as event feeds)."""
    return H3SpatialIndexer.get_multi_res_hierarchy(lat, lng)
