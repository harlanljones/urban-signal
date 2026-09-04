"""NHTSA FARS fatal crash signal — leaf module (US-422, NO spine edits).

Pure geometry/severity helpers that map one NHTSA FARS (Fatality Analysis
Reporting System) point-geocoded fatal crash record onto the repo's H3 res
7/8/9 spatial units. This is intentionally a *leaf* file: it imports ONLY
from `h3_indexer` (itself a leaf file), so it can land in the repo without
touching any spine file (config / city_registry / geo_utils / submarkets /
producers) — the same "Wave 1 point-event, zero spine risk" pattern used by
`epa_echo.py` and `hpms_context.py`. See
`docs/research/national-environmental-infrastructure-signals-2026-08-30.md`
§2.1 / §7 (Ticket Spec 1, US-410) for the source evaluation and phasing.

FARS is an annual census release (~12-month final validation lag) of every
fatal traffic crash in the U.S., point-geocoded (`LATITUDE`, `LONGITUD`).
The helpers here turn a raw FARS row into a res 7/8/9 hierarchy and fold
fatality/pedestrian counts into a rolling-window Micro-Spatial Vision Zero
density per cell — the reusable, spine-free building block a future
spine-bound registration (a producer + FeedType) would call.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict, Iterable

from src.spatial.h3_indexer import H3SpatialIndexer

# FARS `LGT_COND` (lighting condition at crash time). Dark-not-lighted is the
# single strongest correlate of pedestrian fatality risk in the FARS coding
# manual, so it carries the heaviest prior weight below.
class LightCondition(str, Enum):
    DAYLIGHT = "DAYLIGHT"
    DARK_LIGHTED = "DARK_LIGHTED"
    DARK_NOT_LIGHTED = "DARK_NOT_LIGHTED"
    DUSK = "DUSK"
    DAWN = "DAWN"
    UNKNOWN = "UNKNOWN"


# Relative pedestrian-risk prior per lighting condition. Tunable; NOT a
# scoring source until a FeedType is registered (spine change) — mirrors the
# disclaimer on `epa_echo.SEVERITY_WEIGHT`.
LIGHT_CONDITION_RISK_WEIGHT: Dict[LightCondition, float] = {
    LightCondition.DAYLIGHT: 0.5,
    LightCondition.DARK_LIGHTED: 1.0,
    LightCondition.DARK_NOT_LIGHTED: 1.8,
    LightCondition.DUSK: 1.2,
    LightCondition.DAWN: 1.1,
    LightCondition.UNKNOWN: 1.0,
}


@dataclass
class FarsCrash:
    """One FARS fatal-crash record, already geocoded (`LATITUDE`/`LONGITUD`)."""

    lat: float
    lng: float
    st_case: str
    crash_date: date
    fatals: int
    peds: int = 0
    drunk_dr: int = 0
    light_cond: LightCondition = LightCondition.UNKNOWN


def pedestrian_fatality_ratio(crash: FarsCrash) -> float:
    """Fraction of a crash's fatalities that were pedestrians.

    Returns 0.0 for a crash with zero total fatalities (data-entry guard;
    FARS by definition has `FATALS >= 1`, but callers may feed synthetic or
    malformed rows).
    """
    if crash.fatals <= 0:
        return 0.0
    return min(crash.peds, crash.fatals) / crash.fatals


def map_crash_to_h3(crash: FarsCrash) -> Dict[str, str]:
    """Resolve a crash's coordinates to the H3 res 7/8/9 hierarchy.

    Mirrors exactly how event feeds resolve a row to H3 in the repo (see
    `epa_echo.map_event_to_h3`), so a future FARS producer can reuse
    `H3SpatialIndexer.get_multi_res_hierarchy` without any new joiner. Raises
    on invalid coordinates (delegates to h3).
    """
    return H3SpatialIndexer.get_multi_res_hierarchy(crash.lat, crash.lng)


def accumulate_cell_fatal_stats(
    stats_by_cell: Dict[str, Dict[str, float]],
    h3_cell: str,
    crash: FarsCrash,
) -> None:
    """Fold one crash's fatality/pedestrian/light-risk counts into a cell tally.

    Callers aggregate per res-9 cell across all crashes in a window, then
    roll up via `H3SpatialIndexer.get_parent` to res 8 / res 7 for sparse-cell
    smoothing (same `dynamic_spatial_fallback` pattern used elsewhere).
    """
    bucket = stats_by_cell.setdefault(
        h3_cell,
        {"crash_count": 0.0, "fatal_count": 0.0, "ped_fatal_count": 0.0, "drunk_crash_count": 0.0},
    )
    bucket["crash_count"] += 1.0
    bucket["fatal_count"] += float(crash.fatals)
    bucket["ped_fatal_count"] += float(min(crash.peds, crash.fatals))
    if crash.drunk_dr > 0:
        bucket["drunk_crash_count"] += 1.0


def rolling_window_crashes(
    crashes: Iterable[FarsCrash],
    as_of: date,
    window_years: int = 3,
) -> list[FarsCrash]:
    """Filter to crashes within `[as_of - window_years, as_of]`, inclusive.

    Uses a 365.25-day-per-year approximation (FARS is annual-cadence data;
    exact calendar arithmetic is not load-bearing here). Future-dated crashes
    relative to `as_of` are excluded (data-entry noise guard, mirrors
    `epa_echo.event_severity`'s future-date handling).
    """
    window_days = int(window_years * 365.25)
    out = []
    for crash in crashes:
        age_days = (as_of - crash.crash_date).days
        if 0 <= age_days <= window_days:
            out.append(crash)
    return out


def vision_zero_density(
    cell_stats: Dict[str, float],
    resolution: int = 9,
) -> float:
    """Fatalities per km² for one cell's rolling-window tally.

    `cell_stats` is one bucket produced by `accumulate_cell_fatal_stats`
    (must carry `fatal_count`). `resolution` selects the H3 cell area used
    for normalization (7/8/9), matching whichever level the tally was rolled
    up to.
    """
    area_km2 = H3SpatialIndexer.get_cell_area_km2(resolution)
    if area_km2 <= 0:
        return 0.0
    return cell_stats.get("fatal_count", 0.0) / area_km2


def pedestrian_vulnerability_index(cell_stats: Dict[str, float]) -> float:
    """Micro-spatial pedestrian vulnerability prior for one cell's tally.

    Combines the pedestrian-fatality share of the cell's crashes with total
    crash volume: `ped_fatal_count / crash_count`, scaled by
    `log1p(crash_count)` so high-volume, high-pedestrian-share cells rank
    above low-volume cells with an identical ratio (avoids a single crash
    with one pedestrian fatality outranking a chronically dangerous corridor).
    Returns 0.0 for a cell with no recorded crashes.
    """
    import math

    crash_count = cell_stats.get("crash_count", 0.0)
    if crash_count <= 0:
        return 0.0
    ped_share = cell_stats.get("ped_fatal_count", 0.0) / crash_count
    return ped_share * math.log1p(crash_count)
